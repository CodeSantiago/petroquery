"""Query audit persistence helpers.

The chat router writes one :class:`QueryAudit` row per request. The
helper functions in this module encapsulate the construction and the
post-processing of those rows so the router does not have to remember
which fields are set when vs. updated after the pipeline runs.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chat, QueryAudit, User
from app.schemas.og_schemas import OGTechnicalAnswer, OGTMetadata
from app.services.rag.types import NumberValidation, RagResponse


def _client_ip(http_request: Request) -> Optional[str]:
    """Extract the most useful client IP from a FastAPI request.

    Honours the ``X-Forwarded-For`` header for proxied deployments and
    falls back to the direct client host.
    """
    forwarded = http_request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if http_request.client is not None:
        return http_request.client.host
    return None


async def create_audit(
    db: AsyncSession,
    *,
    current_user: User,
    project_id: Optional[int],
    chat: Optional[Chat],
    question: str,
    query_type: str,
    filters: OGTMetadata,
    http_request: Request,
) -> QueryAudit:
    """Build and persist the initial :class:`QueryAudit` row.

    The row is created with placeholder values for the fields that
    will be filled in by :func:`update_audit` after the pipeline runs.
    """
    audit = QueryAudit(
        user_id=current_user.id,
        project_id=project_id,
        chat_id=chat.id if chat else None,
        question=question,
        query_type=query_type,
        filters_applied=filters.model_dump(),
        answer_text="",
        structured_response=None,
        score_global_confianza=0.0,
        necesita_revision_humana=False,
        sources_retrieved=None,
        numbers_validated=None,
        validation_passed=None,
        retrieval_time_ms=0,
        llm_time_ms=0,
        total_time_ms=0,
        tokens_input=0,
        tokens_output=0,
        ip_address=_client_ip(http_request),
        user_agent=http_request.headers.get("user-agent"),
    )
    db.add(audit)
    await db.flush()
    return audit


def update_audit(
    audit: QueryAudit,
    *,
    response: RagResponse,
    validation: Optional[NumberValidation] = None,
) -> None:
    """Populate the success-side fields of an audit row in place."""
    answer: OGTechnicalAnswer = response.answer
    audit.answer_text = answer.respuesta_tecnica
    audit.structured_response = answer.model_dump()
    audit.score_global_confianza = answer.score_global_confianza
    audit.necesita_revision_humana = answer.necesita_revision_humana
    audit.sources_retrieved = [s.model_dump() for s in answer.fuentes]
    audit.numbers_validated = validation.to_dict() if validation else None
    audit.validation_passed = bool(validation.all_verified) if validation else None
    audit.retrieval_time_ms = response.retrieval_time_ms
    audit.llm_time_ms = response.llm_time_ms
    audit.total_time_ms = response.total_time_ms
    # The classification happens inside the pipeline, so we update the
    # query_type here from the final answer rather than from the
    # placeholder value passed to ``create_audit``.
    audit.query_type = answer.tipo_consulta


def mark_audit_error(
    audit: QueryAudit,
    *,
    error_message: str,
    total_time_ms: int,
) -> None:
    """Record a failed run on an audit row."""
    audit.answer_text = f"Error: {error_message}"
    audit.necesita_revision_humana = True
    audit.total_time_ms = total_time_ms


__all__ = [
    "create_audit",
    "update_audit",
    "mark_audit_error",
]
