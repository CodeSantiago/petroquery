"""Chat (RAG) router.

The router is intentionally thin: it orchestrates the RAG pipeline and
the persistence layer, but does not contain any classification,
retrieval, generation or validation logic of its own. Each step has a
named helper that a reviewer can read top-to-bottom to follow the
flow.

Pipeline stages (see :mod:`app.services.rag`):

1. Authorize project access.
2. Resolve or create the chat.
3. Guard against prompt injection.
4. Build chat history.
5. Run the RAG pipeline.
6. Persist messages + audit.
"""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models import Chat, User
from app.schemas import OGTMetadata, OGTechnicalAnswer
from app.services.ai_service import AIService, get_ai_service
from app.services.persistence import (
    assert_project_access,
    create_audit,
    fetch_chat_history,
    format_history,
    mark_audit_error,
    resolve_or_create_chat,
    save_messages,
    update_audit,
)
from app.services.prompt_injection_guard import detect_prompt_injection
from app.services.rag import (
    NO_RESULTS_ANSWER_TEXT,
    RagRequest,
    run_rag_pipeline,
)
from app.services.rag.types import RagResponse

router = APIRouter(prefix="/ask", tags=["chat"])


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    chat_id: int | None = None
    project_id: int | None = None
    filters: OGTMetadata = Field(default_factory=OGTMetadata)


# ----------------------------------------------------------------------
# Small, named steps
# ----------------------------------------------------------------------
def _log_request(current_user: User, body: QuestionRequest) -> None:
    """Log a single banner with the request metadata."""
    print("\n" + "=" * 60)
    print(f"[RAG] Usuario: {current_user.username} (id={current_user.id})")
    print(f"[RAG] Pregunta: {body.question[:100]}...")
    if body.project_id:
        print(f"[RAG] Proyecto: {body.project_id}")
    print("=" * 60)


def _build_injection_answer(message: str) -> OGTechnicalAnswer:
    """Return the canned answer for a detected prompt-injection attempt."""
    return OGTechnicalAnswer(
        respuesta_tecnica=message,
        advertencia_seguridad=(
            "Intento de manipulación del sistema detectado. "
            "Consulta bloqueada."
        ),
        fuentes=[],
        score_global_confianza=0.0,
        necesita_revision_humana=True,
        tipo_consulta="seguridad",
    )


def _build_request(body: QuestionRequest, current_user: User) -> RagRequest:
    """Translate the HTTP body into the immutable pipeline request."""
    return RagRequest(
        question=body.question,
        user_id=current_user.id,
        project_id=body.project_id,
        chat_id=body.chat_id,
        filters=body.filters,
    )


async def _build_history(db: AsyncSession, chat: Chat) -> str:
    """Load and serialise the recent chat history."""
    messages = await fetch_chat_history(db, chat.id)
    print(f"[RAG] Historial mensajes: {len(messages)}")
    return format_history(messages)


# ----------------------------------------------------------------------
# Route
# ----------------------------------------------------------------------
@router.post("", response_model=OGTechnicalAnswer)
async def ask_question(
    body: QuestionRequest,
    http_request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OGTechnicalAnswer:
    start_time = time.time()
    _log_request(current_user, body)

    # 1. Authorize project access (403 if not a member).
    await assert_project_access(db, current_user, body.project_id)

    # 2. Resolve or create the chat so we always have a place to log.
    chat = await resolve_or_create_chat(db, current_user, body.chat_id)
    if chat.id and not body.chat_id:
        print(f"[DB] Nuevo chat creado: {chat.id}")

    # 3. Prompt-injection guard. When triggered we return immediately
    #    and persist a security-flavoured pair of messages.
    injection_detected, injection_message = detect_prompt_injection(body.question)
    if injection_detected:
        print(f"[SAFETY] Prompt injection detectado: {injection_message}")
        return await _handle_injection(
            db=db, chat=chat, body=body, message=injection_message
        )

    # 4. Build the chat history context.
    history = await _build_history(db, chat)

    # 5. Create the audit row BEFORE running the pipeline so that even
    #    crashes are recorded.
    audit = create_audit(
        db,
        current_user=current_user,
        project_id=body.project_id,
        chat=chat,
        question=body.question,
        query_type="general",  # updated below once classification runs
        filters=body.filters,
        http_request=http_request,
    )

    # 6. Run the RAG pipeline.
    rag_request = _build_request(body, current_user)
    try:
        response: RagResponse = await run_rag_pipeline(
            db=db,
            ai_service=ai_service,
            request=rag_request,
            history=history,
        )
    except Exception as exc:
        await _handle_pipeline_error(
            db=db, audit=audit, error=exc, start_time=start_time
        )
        raise

    # 7. Persist messages + finalise the audit row.
    return await _finalise_success(
        db=db,
        chat=chat,
        body=body,
        response=response,
        audit=audit,
        start_time=start_time,
    )


# ----------------------------------------------------------------------
# Step handlers
# ----------------------------------------------------------------------
async def _handle_injection(
    *,
    db: AsyncSession,
    chat: Chat,
    body: QuestionRequest,
    message: str,
) -> OGTechnicalAnswer:
    """Persist a blocked-by-injection answer and return it."""
    answer = _build_injection_answer(message)
    await save_messages(
        db,
        chat,
        user_content=body.question,
        assistant_content=answer.respuesta_tecnica,
        assistant_structured=answer.model_dump(),
    )
    await db.commit()
    return answer


async def _handle_pipeline_error(
    *,
    db: AsyncSession,
    audit,
    error: Exception,
    start_time: float,
) -> None:
    """Record a failed run on the audit row and persist."""
    mark_audit_error(
        audit,
        error_message=str(error),
        total_time_ms=int((time.time() - start_time) * 1000),
    )
    await db.commit()


async def _finalise_success(
    *,
    db: AsyncSession,
    chat: Chat,
    body: QuestionRequest,
    response: RagResponse,
    audit,
    start_time: float,
) -> OGTechnicalAnswer:
    """Persist messages, update the audit row, and return the answer."""
    answer = response.answer
    print(f"[RAG] LLM time: {response.llm_time_ms}ms")
    print(f"[RAG] Total time: {response.total_time_ms}ms")
    print("=" * 60 + "\n")

    await save_messages(
        db,
        chat,
        user_content=body.question,
        assistant_content=answer.respuesta_tecnica,
        assistant_structured=answer.model_dump(),
    )
    update_audit(audit, response=response, validation=response.validation)
    await db.commit()
    return answer


__all__ = ["router", "QuestionRequest"]
