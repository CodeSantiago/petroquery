"""Reranking and context assembly.

The previous implementation reranked chunks via the cross-encoder,
turned the top-K into :class:`SourceReference` objects, joined their
text into a single string, and trimmed it. We keep that exact behaviour
behind a single function so the router can stay declarative.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document
from app.schemas.og_schemas import SourceReference
from app.services.ai_service import AIService
from app.services.rag.context import trim_context
from app.services.rag.types import AssembledContext, RetrievedChunk


# Number of reranked chunks that are actually used for the answer.
RERANK_TOP_K = 3


@dataclass(frozen=True)
class RerankConfig:
    """Tunables for the rerank + assembly stage."""

    top_k: int = RERANK_TOP_K
    max_context_chars: int = 4000


async def _load_extra_data(db: AsyncSession, doc_id: int) -> dict:
    """Fetch ``Document.extra_data`` for a single doc id.

    The original implementation issued one query per chunk. We keep that
    behaviour here (the reranked set is at most ``top_k`` chunks) so we
    do not introduce a new SQL access pattern.
    """
    result = await db.execute(
        select(Document.extra_data).where(Document.id == doc_id)
    )
    return result.scalar() or {}


def _to_source(chunk: RetrievedChunk, extra_data: dict) -> SourceReference:
    """Build a :class:`SourceReference` from a chunk + its extra_data."""
    raw_score = chunk.rerank_score
    normalized_score = 1.0 / (1.0 + pow(2.718281828459045, -raw_score))
    clamped_score = max(0.0, min(1.0, normalized_score))
    return SourceReference(
        documento=chunk.title,
        pagina=extra_data.get("page", 0) or 0,
        seccion=extra_data.get("seccion") or extra_data.get("section"),
        tabla_referencia=extra_data.get("tabla_referencia"),
        figura_referencia=extra_data.get("figura_referencia"),
        score_confianza=round(clamped_score, 4),
        contenido_citado=chunk.content[:500],
        cuenca=chunk.cuenca,
        normativa_aplicable=chunk.normativa_aplicable,
    )


def _apply_rerank_scores(
    chunks: list[RetrievedChunk], reranked_dicts: list[dict]
) -> list[RetrievedChunk]:
    """Overlay the cross-encoder scores from ``reranked_dicts`` onto our
    typed chunks. The AI service mutates the dict in place, so we read
    ``rerank_score`` back by matching on ``id``.
    """
    rerank_by_id: dict[int, float] = {
        int(r.get("id")): float(r.get("rerank_score", 0.0) or 0.0)
        for r in reranked_dicts
        if r.get("id") is not None
    }
    return [
        RetrievedChunk(
            id=chunk.id,
            title=chunk.title,
            content=chunk.content,
            cuenca=chunk.cuenca,
            tipo_documento=chunk.tipo_documento,
            tipo_equipo=chunk.tipo_equipo,
            normativa_aplicable=chunk.normativa_aplicable,
            vector_score=chunk.vector_score,
            fts_rank=chunk.fts_rank,
            rrf_score=chunk.rrf_score,
            rerank_score=rerank_by_id.get(chunk.id, chunk.rerank_score),
        )
        for chunk in chunks
    ]


async def rerank_and_assemble(
    db: AsyncSession,
    ai_service: AIService,
    question: str,
    chunks: list[RetrievedChunk],
    config: RerankConfig | None = None,
) -> AssembledContext:
    """Rerank the candidate chunks, build ``SourceReference``s and a
    trimmed context string.
    """
    cfg = config or RerankConfig()

    if not chunks:
        return AssembledContext(context="", sources=[], chunks=[])

    # The AI service expects a list of dicts with a ``content`` field.
    dict_chunks = [chunk.to_dict() for chunk in chunks]
    reranked_dicts = await ai_service.rerank_chunks(
        query=question,
        chunks=dict_chunks,
        top_k=cfg.top_k,
    )

    merged = _apply_rerank_scores(chunks, reranked_dicts)

    # Build sources, fetching extra_data per chunk. The number of
    # reranked chunks is bounded by ``cfg.top_k`` so the N+1 is
    # acceptable here and matches the original implementation.
    sources: list[SourceReference] = []
    for chunk in merged:
        extra = await _load_extra_data(db, chunk.id)
        sources.append(_to_source(chunk, extra))

    context = "\n\n".join(c.content for c in merged)
    context = trim_context(context, cfg.max_context_chars)

    return AssembledContext(context=context, sources=sources, chunks=merged)


__all__ = ["rerank_and_assemble", "RerankConfig", "RERANK_TOP_K"]
