"""Retrieval orchestration.

This stage runs the "first hop" of the RAG pipeline: it generates a
hypothetical answer, embeds it, runs the hybrid (vector + FTS) search,
applies the HSE document boost, and returns the resulting chunks.

The goal of separating this stage is to make it obvious *what* the
retrieval does and to allow it to be tested or swapped (e.g. for a
mocked search in unit tests) without touching the rest of the pipeline.
"""
from __future__ import annotations

import time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.og_schemas import OGTMetadata
from app.services.ai_service import AIService
from app.services.hse_protocol import boost_hse_documents, is_hse_query
from app.services.hybrid_search import TOP_K as HYBRID_TOP_K
from app.services.hybrid_search import hybrid_search_filtered
from app.services.rag.types import RetrievedChunk, RetrievalResult


# ----------------------------------------------------------------------
# Hybrid-search filter kwargs
# ----------------------------------------------------------------------
_FILTER_FIELDS = ("cuenca", "tipo_documento", "tipo_equipo", "normativa_aplicable")


def _filter_kwargs(filters: OGTMetadata) -> dict[str, str]:
    """Translate the public ``OGTMetadata`` schema into the keyword
    arguments expected by ``hybrid_search_filtered``.

    Centralising this here keeps the router and the rest of the pipeline
    free of Pydantic introspection.
    """
    kwargs: dict[str, str] = {}
    for field in _FILTER_FIELDS:
        value = getattr(filters, field, None)
        if value:
            kwargs[field] = value
    return kwargs


def _row_to_chunk(row: dict) -> RetrievedChunk:
    """Normalise a raw hybrid-search row into a ``RetrievedChunk``."""
    return RetrievedChunk(
        id=row["id"],
        title=row.get("title") or "",
        content=row.get("content") or "",
        cuenca=row.get("cuenca"),
        tipo_documento=row.get("tipo_documento"),
        tipo_equipo=row.get("tipo_equipo"),
        normativa_aplicable=row.get("normativa_aplicable"),
        vector_score=float(row.get("vector_score", 0.0) or 0.0),
        fts_rank=float(row.get("fts_rank", 0.0) or 0.0),
        rrf_score=float(row.get("rrf_score", 0.0) or 0.0),
    )


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
async def retrieve(
    db: AsyncSession,
    ai_service: AIService,
    question: str,
    user_id: int,
    project_id: Optional[int],
    chat_id: Optional[int],
    filters: OGTMetadata,
    *,
    top_k: int = HYBRID_TOP_K,
) -> RetrievalResult:
    """Run the retrieval stage.

    Returns a :class:`RetrievalResult` with the raw chunks and a
    ``retrieval_time_ms`` measurement. The caller is responsible for
    further processing (reranking, generation).
    """
    start = time.time()

    # 1. Hypothetical answer embedding (HyDE-style trick): the LLM is
    #    asked to imagine a plausible answer and we embed *that* instead
    #    of the raw user question. This usually surfaces chunks that
    #    are phrased like a manual rather than a question.
    hypothetical = await ai_service.generate_hypothetical_answer(question)
    embedding = await ai_service.get_query_embedding(hypothetical)

    # 2. Hybrid vector + FTS search with metadata filters.
    rows = await hybrid_search_filtered(
        db=db,
        query=question,
        query_embedding=embedding,
        user_id=user_id,
        project_id=project_id,
        chat_id=chat_id,
        top_k=top_k,
        **_filter_kwargs(filters),
    )

    # 3. HSE boost: when the user asked a safety-critical question,
    #    promote manual/normative HSE chunks to the top of the list.
    if is_hse_query(question):
        rows = boost_hse_documents(rows)

    chunks = [_row_to_chunk(row) for row in rows]
    elapsed_ms = int((time.time() - start) * 1000)
    return RetrievalResult(chunks=chunks, retrieval_time_ms=elapsed_ms)


__all__ = ["retrieve"]
