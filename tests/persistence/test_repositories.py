"""Tests for the chat and audit persistence helpers."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chat, Message, User
from app.services.persistence import (
    DEFAULT_CHAT_TITLE,
    HISTORY_LIMIT,
    assert_project_access,
    fetch_chat_history,
    format_history,
    save_messages,
)
from app.services.persistence.audit_repository import (
    create_audit,
    mark_audit_error,
    update_audit,
)
from app.services.persistence.chat_repository import (
    delete_chat_cascade,
    delete_chat_messages,
    list_user_chats,
    resolve_or_create_chat,
)
from app.services.rag.types import NumberValidation, RagResponse, RetrievedChunk


# ----------------------------------------------------------------------
# resolve_or_create_chat
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_resolve_or_create_returns_existing_chat_for_owner():
    db = MagicMock(spec=AsyncSession)
    user = User(id=1, email="x@x", username="u", hashed_password="h")
    existing = Chat(id=10, user_id=1, title="previo")

    result_scalars = MagicMock()
    result_scalars.scalar_one_or_none = MagicMock(return_value=existing)
    db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=result_scalars), scalar_one_or_none=MagicMock(return_value=existing)))

    chat = await resolve_or_create_chat(db, user, chat_id=10)
    assert chat is existing
    # We must NOT have created a new chat.
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_or_create_404_when_chat_not_found():
    db = MagicMock(spec=AsyncSession)
    user = User(id=1, email="x@x", username="u", hashed_password="h")
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    with pytest.raises(HTTPException) as excinfo:
        await resolve_or_create_chat(db, user, chat_id=999)
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_or_create_creates_new_chat_when_no_id():
    db = MagicMock(spec=AsyncSession)
    user = User(id=1, email="x@x", username="u", hashed_password="h")
    db.flush = AsyncMock()
    db.add = MagicMock()

    chat = await resolve_or_create_chat(db, user, chat_id=None)
    assert chat.user_id == 1
    assert chat.title == DEFAULT_CHAT_TITLE
    db.add.assert_called_once_with(chat)
    db.flush.assert_awaited_once()


# ----------------------------------------------------------------------
# History serialisation
# ----------------------------------------------------------------------
def test_format_history_returns_empty_string_when_no_messages():
    assert format_history([]) == ""


def test_format_history_uses_role_labels():
    messages = [
        Message(id=1, chat_id=1, role="user", content="hola"),
        Message(id=2, chat_id=1, role="assistant", content="buenas"),
    ]
    out = format_history(messages)
    assert "Usuario: hola" in out
    assert "Asistente: buenas" in out
    assert "Historial de conversación" in out


def test_history_limit_is_bounded():
    # Snapshot test so we know when the cap changes.
    assert HISTORY_LIMIT == 10


# ----------------------------------------------------------------------
# save_messages
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_save_messages_attaches_both_to_session():
    db = MagicMock(spec=AsyncSession)
    db.flush = AsyncMock()
    db.add_all = MagicMock()
    chat = Chat(id=1, user_id=1, title="t")

    user_msg, assistant_msg = await save_messages(
        db,
        chat,
        user_content="q",
        assistant_content="a",
        assistant_structured={"fuentes": []},
    )
    assert user_msg.role == "user"
    assert assistant_msg.role == "assistant"
    assert assistant_msg.structured_response == {"fuentes": []}
    db.add_all.assert_called_once()


# ----------------------------------------------------------------------
# assert_project_access
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_assert_project_access_is_noop_when_none():
    db = MagicMock(spec=AsyncSession)
    user = User(id=1, email="x@x", username="u", hashed_password="h")
    # No exception even when db is never used.
    await assert_project_access(db, user, None)


@pytest.mark.asyncio
async def test_assert_project_access_403_for_non_member():
    db = MagicMock(spec=AsyncSession)
    user = User(id=1, email="x@x", username="u", hashed_password="h")
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    with pytest.raises(HTTPException) as excinfo:
        await assert_project_access(db, user, 42)
    assert excinfo.value.status_code == 403


# ----------------------------------------------------------------------
# Audit helpers
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_audit_builds_placeholder_row():
    db = MagicMock(spec=AsyncSession)
    db.flush = AsyncMock()
    user = User(id=1, email="x@x", username="u", hashed_password="h")
    chat = Chat(id=5, user_id=1, title="t")
    request = MagicMock()
    request.headers = {"user-agent": "ua/1.0"}
    request.client.host = "127.0.0.1"

    audit = await create_audit(
        db,
        current_user=user,
        project_id=None,
        chat=chat,
        question="q",
        query_type="general",
        filters=MagicMock(model_dump=MagicMock(return_value={"cuenca": "VM"})),
        http_request=request,
    )
    assert audit.user_id == 1
    assert audit.chat_id == 5
    assert audit.answer_text == ""
    assert audit.query_type == "general"
    assert audit.user_agent == "ua/1.0"
    assert audit.ip_address == "127.0.0.1"
    db.add.assert_called_once_with(audit)
    db.flush.assert_awaited_once()


def test_update_audit_overwrites_success_fields():
    from app.schemas.og_schemas import OGTechnicalAnswer

    audit = MagicMock()
    response = RagResponse(
        answer=OGTechnicalAnswer(
            respuesta_tecnica="texto",
            fuentes=[],
            score_global_confianza=0.42,
            tipo_consulta="operacional",
        ),
        context="ctx",
        chunks=[RetrievedChunk(id=1, title="t", content="c")],
        validation=NumberValidation(total_count=1, verified_count=1, all_verified=True),
        retrieval_time_ms=10,
        llm_time_ms=20,
        total_time_ms=30,
    )
    update_audit(audit, response=response, validation=response.validation)
    assert audit.answer_text == "texto"
    assert audit.score_global_confianza == 0.42
    assert audit.query_type == "operacional"
    assert audit.validation_passed is True
    assert audit.retrieval_time_ms == 10
    assert audit.llm_time_ms == 20
    assert audit.total_time_ms == 30


def test_update_audit_handles_missing_validation():
    from app.schemas.og_schemas import OGTechnicalAnswer

    audit = MagicMock()
    response = RagResponse(
        answer=OGTechnicalAnswer(
            respuesta_tecnica="x",
            fuentes=[],
            score_global_confianza=0.9,
            tipo_consulta="general",
        ),
        context="",
        chunks=[],
        validation=None,
    )
    update_audit(audit, response=response, validation=None)
    assert audit.validation_passed is None
    assert audit.numbers_validated is None


def test_mark_audit_error_records_failure():
    audit = MagicMock()
    mark_audit_error(audit, error_message="boom", total_time_ms=99)
    assert "Error: boom" in audit.answer_text
    assert audit.necesita_revision_humana is True
    assert audit.total_time_ms == 99
