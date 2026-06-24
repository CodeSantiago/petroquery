"""Database access helpers for the chat area.

These helpers hide the SQL behind small, intent-revealing functions
so the chat router does not need to know about table layouts. The
functions are thin on purpose: any real business logic should live in
the RAG pipeline, not here.

Splitting persistence from the router is what makes the chat flow
readable as a sequence of named steps:

* :func:`resolve_or_create_chat`  - chat lookup / create
* :func:`fetch_chat_history`      - serialise recent messages
* :func:`save_messages`           - persist user + assistant messages
* :func:`delete_chat_cascade`     - delete a chat and its data
* :func:`delete_chat_messages`    - clear a chat's history
* :func:`delete_chat_documents`   - clear a chat's documents
* :func:`list_user_chats`         - lightweight list of the user's chats
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chat, Document, Message, User

# Maximum number of recent messages we feed back into the prompt.
HISTORY_LIMIT = 10

# Default title for a freshly-created chat.
DEFAULT_CHAT_TITLE = "Nueva consulta"


async def resolve_or_create_chat(
    db: AsyncSession,
    current_user: User,
    chat_id: Optional[int],
) -> Chat:
    """Return the chat identified by ``chat_id`` or create a new one.

    Raises ``HTTPException(404)`` when the chat does not exist or does
    not belong to the current user.
    """
    if chat_id is not None:
        result = await db.execute(
            select(Chat).where(
                Chat.id == chat_id,
                Chat.user_id == current_user.id,
            )
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat no encontrado",
            )
        return chat

    chat = Chat(user_id=current_user.id, title=DEFAULT_CHAT_TITLE)
    db.add(chat)
    await db.flush()
    return chat


async def fetch_chat_history(db: AsyncSession, chat_id: int) -> list[Message]:
    """Return the most recent :data:`HISTORY_LIMIT` messages for a chat.

    Messages are returned in chronological order (oldest first) so the
    caller can serialise them directly.
    """
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    return list(reversed(result.scalars().all()))


def format_history(messages: list[Message]) -> str:
    """Render a list of messages into the prompt-history block.

    Returns an empty string when there are no messages so the caller can
    pass the result unconditionally.
    """
    if not messages:
        return ""

    block = "\n".join(
        f"{'Usuario' if m.role == 'user' else 'Asistente'}: {m.content}"
        for m in messages
    )
    return "\n--- Historial de conversación ---\n" + block


async def _get_user_chat(
    db: AsyncSession, chat_id: int, current_user: User
) -> Chat:
    """Internal helper: fetch a chat owned by ``current_user`` or 404."""
    result = await db.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == current_user.id,
        )
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat no encontrado",
        )
    return chat


async def save_messages(
    db: AsyncSession,
    chat: Chat,
    *,
    user_content: str,
    assistant_content: str,
    assistant_structured: Optional[dict] = None,
) -> tuple[Message, Message]:
    """Persist the user prompt and the assistant answer for ``chat``.

    The messages are added to the session but not committed; the router
    controls the transaction so it can roll back on errors.
    """
    user_msg = Message(chat_id=chat.id, role="user", content=user_content)
    assistant_msg = Message(
        chat_id=chat.id,
        role="assistant",
        content=assistant_content,
        structured_response=assistant_structured,
    )
    db.add_all([user_msg, assistant_msg])
    await db.flush()
    return user_msg, assistant_msg


async def delete_chat_cascade(
    db: AsyncSession, chat_id: int, current_user: User
) -> Chat:
    """Delete a chat and everything attached to it (audits, messages,
    documents). Returns the deleted :class:`Chat` so the router can
    confirm the operation.
    """
    chat = await _get_user_chat(db, chat_id, current_user)
    await db.execute(
        text("DELETE FROM query_audits WHERE chat_id = :chat_id"),
        {"chat_id": chat_id},
    )
    await db.execute(
        text("DELETE FROM messages WHERE chat_id = :chat_id"),
        {"chat_id": chat_id},
    )
    await db.execute(
        text("DELETE FROM documents WHERE chat_id = :chat_id"),
        {"chat_id": chat_id},
    )
    await db.execute(
        text("DELETE FROM chats WHERE id = :chat_id"),
        {"chat_id": chat_id},
    )
    await db.commit()
    return chat


async def delete_chat_messages(
    db: AsyncSession, chat_id: int, current_user: User
) -> Chat:
    """Delete every message attached to a chat, keeping the chat itself."""
    chat = await _get_user_chat(db, chat_id, current_user)
    await db.execute(
        text("DELETE FROM messages WHERE chat_id = :chat_id"),
        {"chat_id": chat_id},
    )
    await db.commit()
    return chat


async def delete_chat_documents(
    db: AsyncSession, chat_id: int, current_user: User
) -> Chat:
    """Delete every document attached to a chat, keeping the chat itself."""
    chat = await _get_user_chat(db, chat_id, current_user)
    await db.execute(
        text("DELETE FROM documents WHERE chat_id = :chat_id"),
        {"chat_id": chat_id},
    )
    await db.commit()
    return chat


async def list_user_chats(
    db: AsyncSession, current_user: User
) -> list[dict]:
    """Return the lightweight chat list used by the front-end sidebar."""
    result = await db.execute(
        select(Chat)
        .where(Chat.user_id == current_user.id)
        .order_by(Chat.created_at.desc())
    )
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat(),
        }
        for c in result.scalars().all()
    ]


async def get_chat_documents(
    db: AsyncSession, chat_id: int, current_user: User
) -> list[Document]:
    """Return all documents owned by ``current_user`` and attached to the chat.

    Used by the outline endpoint to extract sections and insights.
    """
    result = await db.execute(
        select(Document).where(
            Document.chat_id == chat_id,
            Document.user_id == current_user.id,
        )
    )
    return list(result.scalars().all())


__all__ = [
    "HISTORY_LIMIT",
    "DEFAULT_CHAT_TITLE",
    "resolve_or_create_chat",
    "fetch_chat_history",
    "format_history",
    "save_messages",
    "delete_chat_cascade",
    "delete_chat_messages",
    "delete_chat_documents",
    "list_user_chats",
    "get_chat_documents",
]
