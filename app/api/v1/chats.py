"""Chat management routes (list, get messages, outline, deletes).

These routes manage the lifecycle of a chat session and its
attachments. The actual RAG question lives in :mod:`chat`. All
persistence happens through helpers in
:mod:`app.services.persistence` so the routes stay declarative.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models import Document, User
from app.schemas import MessageResponse
from app.services.persistence import (
    delete_chat_cascade,
    delete_chat_documents,
    delete_chat_messages,
    get_chat_documents,
    list_user_chats,
)

router = APIRouter(prefix="/chats", tags=["messages"])


@router.get("", response_model=list[dict])
async def list_chats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    return await list_user_chats(db, current_user)


@router.get("/{chat_id}/messages", response_model=list[MessageResponse])
async def get_chat_messages(
    chat_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[MessageResponse]:
    from sqlalchemy import select

    from app.models import Chat, Message

    result = await db.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == current_user.id,
        )
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")

    messages_result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
    )
    return list(messages_result.scalars().all())


@router.get("/{chat_id}/outline", status_code=status.HTTP_200_OK)
async def get_chat_outline(
    chat_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Return document outline (sections/chapters) for a chat's associated document."""
    from sqlalchemy import select

    from app.models import Chat

    result = await db.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == current_user.id,
        )
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")

    # Find the primary document for this chat.
    docs = await get_chat_documents(db, chat_id, current_user)
    if not docs:
        return {"title": chat.title or "Sin título", "sections": [], "insights": None}

    primary = docs[0]
    chunks = [d for d in docs if d.processing_status == "completed"] or docs

    sections: list[dict] = []
    seen: set[str] = set()
    for chunk in chunks:
        seccion = chunk.extra_data.get("seccion") if chunk.extra_data else None
        if seccion and seccion not in seen:
            sections.append(
                {
                    "name": seccion,
                    "page": chunk.extra_data.get("page") if chunk.extra_data else None,
                }
            )
            seen.add(seccion)

    insights = primary.extra_data.get("insights") if primary.extra_data else None

    if insights and "sections" in insights:
        return {
            "title": primary.title,
            "summary": insights.get("summary", ""),
            "global_topics": insights.get("global_topics", []),
            "global_questions": insights.get("global_questions", []),
            "sections": insights["sections"],
        }

    return {
        "title": primary.title,
        "summary": insights.get("summary", "") if insights else "",
        "global_topics": insights.get("global_topics", []) if insights else [],
        "global_questions": insights.get("global_questions", []) if insights else [],
        "sections": sections,
    }


@router.delete("/{chat_id}", status_code=status.HTTP_200_OK)
async def delete_chat(
    chat_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    await delete_chat_cascade(db, chat_id, current_user)
    return {"message": f"Chat {chat_id} eliminado"}


@router.delete("/{chat_id}/messages", status_code=status.HTTP_200_OK)
async def clear_chat_messages(
    chat_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    await delete_chat_messages(db, chat_id, current_user)
    return {"message": f"Mensajes del chat {chat_id} eliminados"}


@router.delete("/{chat_id}/documents", status_code=status.HTTP_200_OK)
async def delete_chat_documents_route(
    chat_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    await delete_chat_documents(db, chat_id, current_user)
    return {"message": f"Documentos del chat {chat_id} eliminados"}


__all__ = ["router"]
