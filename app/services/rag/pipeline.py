"""RAG pipeline orchestrator.

The pipeline is the single entry point used by the chat router. It
chains the individual stages together (``classify`` -> ``retrieve`` ->
``rerank`` -> ``generate`` -> ``validate``) and returns a
:class:`RagResponse` with all the diagnostic fields the router needs to
write a ``QueryAudit`` row.

The pipeline deliberately does not touch the database beyond the
hybrid-search call inside :mod:`retrieval` and the ``Document``
lookups inside :mod:`reranking`. Persistence (chats, messages, audit
rows) is the router's responsibility and lives in
:mod:`app.services.persistence`.
"""
from __future__ import annotations

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.og_schemas import OGTechnicalAnswer
from app.services.ai_service import AIService
from app.services.rag.classification import classify_query
from app.services.rag.generation import generate_answer
from app.services.rag.retrieval import retrieve
from app.services.rag.reranking import rerank_and_assemble
from app.services.rag.types import RagRequest, RagResponse
from app.services.rag.validation import finalize_answer


# Public answer returned when no chunks are found. Kept as a constant so
# the test suite and the router agree on the exact wording.
NO_RESULTS_ANSWER_TEXT = (
    "No se encontró contexto relacionado con tu pregunta en la base de datos. "
    "Se requiere cargar documentos técnicos relevantes o consultar al "
    "departamento de ingeniería."
)


async def _build_no_results_response(
    request: RagRequest,
    query_type: str,
    retrieval_time_ms: int,
    start: float,
) -> RagResponse:
    """Build the standardised "no results" response."""
    answer = OGTechnicalAnswer(
        respuesta_tecnica=NO_RESULTS_ANSWER_TEXT,
        advertencia_seguridad=None,
        fuentes=[],
        score_global_confianza=0.0,
        necesita_revision_humana=True,
        tipo_consulta=query_type,
    )
    return RagResponse(
        answer=answer,
        context="",
        chunks=[],
        validation=None,
        retrieval_time_ms=retrieval_time_ms,
        llm_time_ms=0,
        total_time_ms=int((time.time() - start) * 1000),
    )


async def run_rag_pipeline(
    db: AsyncSession,
    ai_service: AIService,
    request: RagRequest,
    history: str = "",
) -> RagResponse:
    """Execute the full RAG pipeline for ``request`` and return the
    final :class:`RagResponse`.

    Parameters
    ----------
    db:
        Database session. Used by the retrieval and reranking stages.
    ai_service:
        The shared :class:`AIService` instance.
    request:
        Immutable request payload (see :class:`RagRequest`).
    history:
        Pre-formatted chat history (already trimmed and serialised by
        the router).
    """
    start = time.time()

    # 1. Classify
    classified = await classify_query(ai_service, request.question)

    # 2. Retrieve
    retrieval = await retrieve(
        db=db,
        ai_service=ai_service,
        question=request.question,
        user_id=request.user_id,
        project_id=request.project_id,
        chat_id=request.chat_id,
        filters=request.filters,
    )

    # 3. No-results short-circuit
    if not retrieval.chunks:
        return await _build_no_results_response(
            request=request,
            query_type=classified.query_type,
            retrieval_time_ms=retrieval.retrieval_time_ms,
            start=start,
        )

    # 4. Rerank + assemble
    assembled = await rerank_and_assemble(
        db=db,
        ai_service=ai_service,
        question=request.question,
        chunks=retrieval.chunks,
    )

    # 5. Generate
    answer, llm_time_ms = await generate_answer(
        ai_service,
        question=request.question,
        history=history,
        query_type=classified.query_type,
        assembled=assembled,
    )

    # 6. Validate + post-process
    answer, validation = finalize_answer(answer, assembled.chunks)

    total_time_ms = int((time.time() - start) * 1000)
    return RagResponse(
        answer=answer,
        context=assembled.context,
        chunks=assembled.chunks,
        validation=validation,
        retrieval_time_ms=retrieval.retrieval_time_ms,
        llm_time_ms=llm_time_ms,
        total_time_ms=total_time_ms,
    )


__all__ = ["run_rag_pipeline", "RagRequest", "RagResponse"]
