from typing import Annotated

import asyncio
import time
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models import Chat, Document, Message, ProjectMember, QueryAudit, User
from app.schemas import (
    AnswerResponse,
    ChatResponse,
    MessageResponse,
    OGTechnicalAnswer,
    OGTMetadata,
)
from app.services.ai_service import get_ai_service, AIService
from app.services.hybrid_search import hybrid_search_filtered, TOP_K as HYBRID_TOP_K
from app.services.prompt_injection_guard import detect_prompt_injection
from app.services.hse_protocol import is_hse_query, boost_hse_documents, hse_hard_stop
from app.services.number_validator import validate_numbers_against_chunks, extract_technical_numbers
from app.services.pii_masker import PIIMasker
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ask", tags=["chat"])

MAX_CONTEXT_CHARS = 4000
TOP_K = 3
HISTORY_LIMIT = 10


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    chat_id: int | None = None
    project_id: int | None = None
    filters: OGTMetadata = Field(default_factory=OGTMetadata)


def trim_context(context: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    if len(context) <= max_chars:
        return context
    trimmed = context[:max_chars]
    last_newline = trimmed.rfind("\n\n")
    if last_newline > max_chars * 0.5:
        return trimmed[:last_newline].strip()
    return trimmed.strip() + "\n\n[Contexto truncado...]"


@router.post("", response_model=OGTechnicalAnswer)
async def ask_question(
    body: QuestionRequest,
    http_request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OGTechnicalAnswer:
    start_time = time.time()
    user_id_filter = current_user.id
    project_id = body.project_id
    chat_id = body.chat_id

    print("\n" + "=" * 60)
    print(f"[RAG] Usuario: {current_user.username} (id={user_id_filter})")
    print(f"[RAG] Pregunta: {body.question[:100]}...")
    if project_id:
        print(f"[RAG] Proyecto: {project_id}")
    print("=" * 60)

    # Verify project access if project_id provided
    if project_id is not None:
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.user_id == current_user.id,
                ProjectMember.project_id == project_id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a este proyecto",
            )

    # Resolve or create chat first so we always have a chat object for logging
    search_chat_id = None
    if chat_id:
        result = await db.execute(
            select(Chat).where(
                Chat.id == chat_id,
                Chat.user_id == current_user.id
            )
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat no encontrado")
        search_chat_id = chat.id
    else:
        chat = Chat(user_id=current_user.id, title="Nueva consulta")
        db.add(chat)
        await db.flush()
        print(f"[DB] Nuevo chat creado: {chat.id}")
        search_chat_id = None

    # Prompt injection guard
    injection_detected, injection_message = detect_prompt_injection(body.question)
    if injection_detected:
        print(f"[SAFETY] Prompt injection detectado: {injection_message}")
        og_answer = OGTechnicalAnswer(
            respuesta_tecnica=injection_message,
            advertencia_seguridad="Intento de manipulación del sistema detectado. Consulta bloqueada.",
            fuentes=[],
            score_global_confianza=0.0,
            necesita_revision_humana=True,
            tipo_consulta="seguridad",
        )
        user_msg = Message(chat_id=chat.id, role="user", content=body.question)
        assistant_msg = Message(
            chat_id=chat.id,
            role="assistant",
            content=og_answer.respuesta_tecnica,
            structured_response=og_answer.model_dump(),
        )
        db.add_all([user_msg, assistant_msg])
        await db.flush()
        return og_answer

    # Build history context
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

    # Classify query type
    query_type = await ai_service.classify_query_type(body.question)
    print(f"[RAG] Tipo de consulta detectado: {query_type}")

    # Build metadata filters if any provided
    filters = body.filters
    filter_kwargs = {}
    if filters.cuenca:
        filter_kwargs["cuenca"] = filters.cuenca
    if filters.tipo_documento:
        filter_kwargs["tipo_documento"] = filters.tipo_documento
    if filters.tipo_equipo:
        filter_kwargs["tipo_equipo"] = filters.tipo_equipo
    if filters.normativa_aplicable:
        filter_kwargs["normativa_aplicable"] = filters.normativa_aplicable

    # Create audit entry BEFORE processing
    audit = QueryAudit(
        user_id=current_user.id,
        project_id=project_id,
        chat_id=chat.id if chat else None,
        question=body.question,
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
        ip_address=http_request.headers.get("x-forwarded-for") or http_request.client.host,
        user_agent=http_request.headers.get("user-agent"),
    )
    db.add(audit)
    await db.flush()

    try:
        # Retrieval with hypothetical answer embedding
        retrieval_start = time.time()
        hypothetical_answer = await ai_service.generate_hypothetical_answer(body.question)
        hyp_embedding = await ai_service.get_query_embedding(hypothetical_answer)

        results = await hybrid_search_filtered(
            db=db,
            query=body.question,
            query_embedding=hyp_embedding,
            user_id=current_user.id,
            project_id=project_id,
            chat_id=search_chat_id,
            top_k=HYBRID_TOP_K,
            **filter_kwargs,
        )
        retrieval_time = (time.time() - retrieval_start) * 1000

        print(f"[RAG] Retrieval time: {retrieval_time:.2f}ms")
        print(f"[RAG] Chunks encontrados: {len(results)}")

        # Boost HSE documents for safety-critical queries
        if is_hse_query(body.question):
            results = boost_hse_documents(results)
            print(f"[SAFETY] HSE boost aplicado. Top chunks reordenados por prioridad de seguridad.")

        for i, row in enumerate(results[:5], 1):
            chunk_preview = row["content"][:100].replace("\n", " ")
            score = row.get("vector_score", 0)
            print(f"  Chunk {i}: score={score:.4f} | \"{chunk_preview}...\"")

        if not results:
            print("[RAG] No se encontraron resultados en la búsqueda")
            og_answer = OGTechnicalAnswer(
                respuesta_tecnica="No se encontró contexto relacionado con tu pregunta en la base de datos. "
                                "Se requiere cargar documentos técnicos relevantes o consultar al departamento de ingeniería.",
                advertencia_seguridad=None,
                fuentes=[],
                score_global_confianza=0.0,
                necesita_revision_humana=True,
                tipo_consulta=query_type,
            )
            user_msg = Message(chat_id=chat.id, role="user", content=body.question)
            assistant_msg = Message(
                chat_id=chat.id,
                role="assistant",
                content=og_answer.respuesta_tecnica,
                structured_response=og_answer.model_dump(),
            )
            db.add_all([user_msg, assistant_msg])
            audit.answer_text = og_answer.respuesta_tecnica
            audit.structured_response = og_answer.model_dump()
            audit.score_global_confianza = og_answer.score_global_confianza
            audit.necesita_revision_humana = og_answer.necesita_revision_humana
            audit.retrieval_time_ms = int(retrieval_time)
            audit.total_time_ms = int((time.time() - start_time) * 1000)
            await db.commit()
            return og_answer

        # Rerank
        reranked_results = await ai_service.rerank_chunks(
            query=body.question,
            chunks=results,
            top_k=TOP_K,
        )

        # Build context and sources
        context_parts = []
        sources = []

        for row in reranked_results:
            context_parts.append(row["content"])
            # Try to get extra metadata from DB
            doc_id = row["id"]
            doc_result = await db.execute(
                select(Document.extra_data).where(Document.id == doc_id)
            )
            extra_data = doc_result.scalar() or {}

            source_ref = {
                "documento": row["title"],
                "pagina": extra_data.get("page", 0),
                "seccion": extra_data.get("seccion") or extra_data.get("section"),
                "tabla_referencia": extra_data.get("tabla_referencia"),
                "figura_referencia": extra_data.get("figura_referencia"),
                "score_confianza": round(row.get("rerank_score", 0), 4),
                "contenido_citado": row["content"][:500],
                "cuenca": row.get("cuenca"),
                "normativa_aplicable": row.get("normativa_aplicable"),
            }
            sources.append(source_ref)

        context = "\n\n".join(context_parts)
        context = trim_context(context, MAX_CONTEXT_CHARS)

        # Structured LLM call
        llm_start = time.time()
        og_answer = await ai_service.ask_og_structured(
            context=context,
            question=body.question,
            history=history_context,
            query_type=query_type,
        )
        llm_time = (time.time() - llm_start) * 1000

        # Enrich answer with our sources if LLM didn't provide them
        if not og_answer.fuentes and sources:
            from app.schemas.og_schemas import SourceReference
            og_answer.fuentes = [SourceReference(**s) for s in sources]

        # Override score with rerank confidence average
        if og_answer.fuentes:
            avg_score = sum(f.score_confianza for f in og_answer.fuentes) / len(og_answer.fuentes)
            og_answer.score_global_confianza = round(avg_score, 4)

        # Validate technical numbers against source chunks
        answer_numbers = extract_technical_numbers(og_answer.respuesta_tecnica or "")
        if answer_numbers:
            validation_result = validate_numbers_against_chunks(answer_numbers, context_parts)
            print(f"[SAFETY] Number validation: {validation_result['verified_count']}/{validation_result['total_count']} verified")
            if not validation_result["all_verified"]:
                og_answer.score_global_confianza = round(og_answer.score_global_confianza * 0.7, 4)
                og_answer.necesita_revision_humana = True

        # Determine if human review needed
        if og_answer.score_global_confianza < 0.7 or query_type == "seguridad":
            og_answer.necesita_revision_humana = True

        # Apply HSE hard-stop before returning
        answer_dict = og_answer.model_dump()
        answer_dict = hse_hard_stop(answer_dict)
        og_answer = OGTechnicalAnswer(**answer_dict)

        total_time = (time.time() - start_time) * 1000
        print(f"[RAG] LLM time: {llm_time:.2f}ms")
        print(f"[RAG] Total time: {total_time:.2f}ms")
        print("=" * 60 + "\n")

        # Save messages
        user_msg = Message(chat_id=chat.id, role="user", content=body.question)
        assistant_msg = Message(
            chat_id=chat.id,
            role="assistant",
            content=og_answer.respuesta_tecnica,
            structured_response=og_answer.model_dump(),
        )
        db.add_all([user_msg, assistant_msg])

        # Update audit with success data
        audit.answer_text = og_answer.respuesta_tecnica
        audit.structured_response = og_answer.model_dump()
        audit.score_global_confianza = og_answer.score_global_confianza
        audit.necesita_revision_humana = og_answer.necesita_revision_humana
        audit.sources_retrieved = [s.model_dump() for s in og_answer.fuentes]
        audit.retrieval_time_ms = int(retrieval_time)
        audit.llm_time_ms = int(llm_time)
        audit.total_time_ms = int(total_time)
        # tokens_input / tokens_output should be populated by AI service when available
        await db.commit()

        return og_answer

    except Exception as e:
        audit.answer_text = f"Error: {str(e)}"
        audit.necesita_revision_humana = True
        audit.total_time_ms = int((time.time() - start_time) * 1000)
        await db.commit()
        raise


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


@messages_router.get("/{chat_id}/outline", status_code=status.HTTP_200_OK)
async def get_chat_outline(
    chat_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Return document outline (sections/chapters) for a chat's associated document."""
    result = await db.execute(
        select(Chat).where(
            Chat.id == chat_id,
            Chat.user_id == current_user.id
        )
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")

    # Find the primary document for this chat
    doc_result = await db.execute(
        select(Document).where(
            Document.chat_id == chat_id,
            Document.user_id == current_user.id,
        ).order_by(Document.id.asc()).limit(1)
    )
    doc = doc_result.scalar_one_or_none()

    if not doc:
        return {"title": chat.title or "Sin título", "sections": [], "insights": None}

    # Extract unique sections from chunks
    chunk_result = await db.execute(
        select(Document).where(
            Document.chat_id == chat_id,
            Document.user_id == current_user.id,
            Document.processing_status == "completed",
        )
    )
    chunks = chunk_result.scalars().all()

    sections = []
    seen = set()
    for chunk in chunks:
        seccion = chunk.extra_data.get("seccion") if chunk.extra_data else None
        if seccion and seccion not in seen:
            sections.append({
                "name": seccion,
                "page": chunk.extra_data.get("page") if chunk.extra_data else None,
            })
            seen.add(seccion)

    insights = doc.extra_data.get("insights") if doc.extra_data else None

    if insights and "sections" in insights:
        return {
            "title": doc.title,
            "summary": insights.get("summary", ""),
            "global_topics": insights.get("global_topics", []),
            "global_questions": insights.get("global_questions", []),
            "sections": insights["sections"],
        }

    return {
        "title": doc.title,
        "summary": insights.get("summary", "") if insights else "",
        "global_topics": insights.get("global_topics", []) if insights else [],
        "global_questions": insights.get("global_questions", []) if insights else [],
        "sections": sections,
    }


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

    await db.execute(text("DELETE FROM query_audits WHERE chat_id = :chat_id"), {"chat_id": chat_id})
    await db.execute(text("DELETE FROM messages WHERE chat_id = :chat_id"), {"chat_id": chat_id})
    await db.execute(text("DELETE FROM documents WHERE chat_id = :chat_id"), {"chat_id": chat_id})
    await db.execute(text("DELETE FROM chats WHERE id = :chat_id"), {"chat_id": chat_id})
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

    await db.execute(text("DELETE FROM messages WHERE chat_id = :chat_id"), {"chat_id": chat_id})
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

    await db.execute(text("DELETE FROM documents WHERE chat_id = :chat_id"), {"chat_id": chat_id})
    await db.commit()
    return {"message": f"Documentos del chat {chat_id} eliminados"}
