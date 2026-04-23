from typing import Annotated

import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models import Chat, Message, User
from app.schemas import AnswerResponse, MessageResponse
from app.services.ai_service import get_ai_service, AIService
from app.services.hybrid_search import hybrid_search, TOP_K as HYBRID_TOP_K
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ask", tags=["chat"])

MAX_CONTEXT_CHARS = 15000
TOP_K = 4
HISTORY_LIMIT = 10


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    chat_id: int | None = None


class AnswerResponse(BaseModel):
    answer: str
    sources: list[dict]
    chat_id: int


def trim_context(context: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    if len(context) <= max_chars:
        return context
    
    trimmed = context[:max_chars]
    last_newline = trimmed.rfind("\n\n")
    if last_newline > max_chars * 0.5:
        return trimmed[:last_newline].strip()
    
    return trimmed.strip() + "\n\n[Contexto truncado...]"


@router.post("", response_model=AnswerResponse)
async def ask_question(
    request: QuestionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AnswerResponse:
    start_time = time.time()
    user_id_filter = current_user.id
    
    print("\n" + "="*60)
    print(f"[RAG] Usuario: {current_user.username} (id={user_id_filter})")
    print(f"[RAG] Pregunta: {request.question[:100]}...")
    print("="*60)
    
    if request.chat_id:
        result = await db.execute(
            select(Chat).where(
                Chat.id == request.chat_id,
                Chat.user_id == current_user.id
            )
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat no encontrado")
    else:
        chat = Chat(user_id=current_user.id, title=request.question[:50])
        db.add(chat)
        await db.flush()
        print(f"[DB] Nuevo chat creado: {chat.id}")
    
    history_result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat.id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    history_messages = history_result.scalars().all()
    history_messages = list(reversed(history_messages))
    
    history_context = ""
    for msg in history_messages:
        role_label = "Usuario" if msg.role == "user" else "Asistente"
        history_context += f"{role_label}: {msg.content}\n"
    
    if history_context:
        history_context = "\n--- Historial de conversación ---\n" + history_context

    print(f"[RAG] Historial mensajes: {len(history_messages)}")
    
    retrieval_start = time.time()
    hypothetical_answer = await ai_service.generate_hypothetical_answer(request.question)
    hyp_embedding = await ai_service.get_embedding(hypothetical_answer)
    
    results = await hybrid_search(
        db=db,
        query=request.question,
        query_embedding=hyp_embedding,
        user_id=current_user.id,
        chat_id=chat.id,
        top_k=HYBRID_TOP_K,
    )
    retrieval_time = (time.time() - retrieval_start) * 1000
    
    print(f"[RAG] Retrieval time: {retrieval_time:.2f}ms")
    print(f"[RAG]Chunks encontrados: {len(results)}")
    
    for i, row in enumerate(results[:5], 1):
        chunk_preview = row["content"][:100].replace("\n", " ")
        score = row.get("rerank_score", row.get("vector_score", 0))
        print(f"  Chunk {i}: score={score:.4f} | \"{chunk_preview}...\"")
    
    if not results:
        print(f"[RAG] No se encontraron resultados en la búsqueda")
        answer = "No se encontró contexto relacionado con tu pregunta en la base de datos."
        answer_response = AnswerResponse(answer=answer, sources=[], chat_id=chat.id)
        
        user_msg = Message(chat_id=chat.id, role="user", content=request.question)
        assistant_msg = Message(chat_id=chat.id, role="assistant", content=answer)
        db.add_all([user_msg, assistant_msg])
        await db.flush()
        
        print(f"[DB] Mensaje guardado en DB para el chat {chat.id}")
        
        return answer_response
    
    reranked_results = await ai_service.rerank_chunks(
        query=request.question,
        chunks=results,
        top_k=TOP_K,
    )
    
    context_parts = []
    sources = []
    
    for row in reranked_results:
        context_parts.append(row["content"])
        sources.append({
            "id": row["id"],
            "title": row["title"],
            "score": round(row.get("rerank_score", 0), 4),
        })
    
    context = "\n\n".join(context_parts)
    context = trim_context(context, MAX_CONTEXT_CHARS)
    
    llm_start = time.time()
    answer, input_tokens, output_tokens = await ai_service.ask_groq_with_history_tokens(context, request.question, history_context)
    llm_time = (time.time() - llm_start) * 1000
    
    print(f"[RAG] LLM time: {llm_time:.2f}ms")
    print(f"[RAG] Tokens: input={input_tokens}, output={output_tokens}")
    print(f"[RAG] Total time: {(time.time() - start_time)*1000:.2f}ms")
    print("="*60 + "\n")
    
    user_msg = Message(chat_id=chat.id, role="user", content=request.question)
    assistant_msg = Message(chat_id=chat.id, role="assistant", content=answer)
    db.add_all([user_msg, assistant_msg])
    await db.flush()
    
    print(f"[DB] Mensaje guardado en DB para el chat {chat.id}")
    
    return AnswerResponse(answer=answer, sources=sources, chat_id=chat.id)


messages_router = APIRouter(prefix="/chats", tags=["messages"])


@messages_router.get("", response_model=list[dict])
async def list_chats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    result = await db.execute(
        select(Chat)
        .where(Chat.user_id == current_user.id)
        .order_by(Chat.created_at.desc())
    )
    chats = result.scalars().all()
    
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()}
        for c in chats
    ]


@messages_router.get("/{chat_id}/messages", response_model=list[MessageResponse])
async def get_chat_messages(
    chat_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[MessageResponse]:
    result = await db.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == current_user.id
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
    messages = messages_result.scalars().all()
    
    return messages


@messages_router.delete("/{chat_id}", status_code=status.HTTP_200_OK)
async def delete_chat(
    chat_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    result = await db.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == current_user.id
        )
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    
    await db.execute(
        text("DELETE FROM messages WHERE chat_id = :chat_id"),
        {"chat_id": chat_id}
    )
    await db.execute(
        text("DELETE FROM documents WHERE chat_id = :chat_id"),
        {"chat_id": chat_id}
    )
    await db.execute(
        text("DELETE FROM chats WHERE id = :chat_id"),
        {"chat_id": chat_id}
    )
    await db.commit()
    
    return {"message": f"Chat {chat_id} eliminado"}


@messages_router.delete("/{chat_id}/messages", status_code=status.HTTP_200_OK)
async def clear_chat_messages(
    chat_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    result = await db.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == current_user.id
        )
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    
    await db.execute(
        text("DELETE FROM messages WHERE chat_id = :chat_id"),
        {"chat_id": chat_id}
    )
    await db.commit()
    
    return {"message": f"Mensajes del chat {chat_id} eliminados"}


@messages_router.delete("/{chat_id}/documents", status_code=status.HTTP_200_OK)
async def delete_chat_documents(
    chat_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    result = await db.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == current_user.id
        )
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    
    await db.execute(
        text("DELETE FROM documents WHERE chat_id = :chat_id"),
        {"chat_id": chat_id}
    )
    await db.commit()
    
    return {"message": f"Documentos del chat {chat_id} eliminados"}