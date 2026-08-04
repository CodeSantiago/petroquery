from typing import Annotated, Optional
import logging
import io
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, BackgroundTasks
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import Chat, Document, ProjectMember, User
from app.schemas import OGTMetadata
from app.services.ai_service import get_ai_service, AIService
from app.services.ml_subprocess import (
    is_process_worker_enabled,
    run_in_subprocess,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


async def _process_pdf_background(
    document_id: int,
    file_bytes: bytes,
    user_id: int,
    chat_id: int,
    project_id: int,
    doc_title: str,
    filename: str,
    metadata: dict,
) -> None:
    """Background task to process PDF and store chunks.

    Two execution modes are supported:

    * **in-process** (default): the heavy work runs in this FastAPI
      worker. This is the historical behaviour and is fine on Linux
      hosts where the ML stack does not have native crash hazards.
    * **subprocess** (opt-in via ``PETROQUERY_ML_WORKER=process``):
      the PDF parsing and chunking run in a separate Python process so
      that a Windows access violation inside ``pdfplumber``,
      ``sentence-transformers`` or ``torch`` cannot take down the API.
      The parent process keeps serving requests; the affected document
      is marked as ``processing_status='failed'`` with the worker's
      stderr surfaced in the server log.
    """
    import asyncio
    from app.database import AsyncSessionLocal
    from app.services.ai_service import get_ai_service
    from app.services.document_processor import (
        extract_text_and_tables_from_pdf,
        create_chunks_from_page,
        validate_and_merge_small_chunks,
        generate_document_insights,
    )

    ai_service = get_ai_service()
    db = AsyncSessionLocal()

    use_subprocess = is_process_worker_enabled()
    all_chunks: list[dict] = []
    failure_message: Optional[str] = None

    try:
        if use_subprocess:
            logger.info(
                "Background PDF processing for document %s: using subprocess worker",
                document_id,
            )
            worker_result = await run_in_subprocess(
                {
                    "type": "process_pdf",
                    "pdf_hex": file_bytes.hex(),
                    "filename": filename,
                    "metadata": {"user_id": user_id, **(metadata or {})},
                }
            )
            if not worker_result.get("ok"):
                failure_message = worker_result.get("error", "ML worker failed")
                stderr = worker_result.get("stderr") or ""
                if stderr:
                    logger.error(
                        "Subprocess ML worker stderr for document %s:\n%s",
                        document_id, stderr,
                    )
                raise RuntimeError(failure_message)
            all_chunks = (worker_result.get("result") or {}).get("chunks") or []
            total_pages = int(
                (worker_result.get("result") or {}).get("page_count", 0)
            ) or max((c.get("page", 0) for c in all_chunks), default=0)

            # Update progress in coarse steps (we don't have per-page
            # granularity from the worker; mark as 50% after parsing).
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(processing_progress=50)
            )
            await db.commit()
        else:
            pages = extract_text_and_tables_from_pdf(file_bytes)
            total_pages = len(pages)
            doc_metadata = {"user_id": user_id, **metadata}
            for page_num, page_text, tables in pages:
                page_chunks = create_chunks_from_page(
                    page_num=page_num,
                    page_text=page_text,
                    tables=tables,
                    source=filename,
                    doc_metadata=doc_metadata,
                )
                all_chunks.extend(page_chunks)
                progress = int((page_num / total_pages) * 50) if total_pages else 50
                await db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(processing_progress=progress)
                )
                await db.commit()

        all_chunks = validate_and_merge_small_chunks(all_chunks)
        total_chunks = len(all_chunks)

        # Create chunk documents (embeddings are always computed in the
        # API process; if the embedding model crashes the parent catches
        # the failure and marks the document as failed below).
        for i, chunk in enumerate(all_chunks):
            try:
                embedding = await ai_service.get_document_embedding(chunk["text"])
            except Exception as emb_exc:
                logger.error(
                    "Embedding failed for document %s chunk %s: %s",
                    document_id, i, emb_exc,
                )
                failure_message = f"embedding failed: {emb_exc}"
                raise
            chunk_doc = Document(
                user_id=user_id,
                chat_id=chat_id,
                project_id=project_id,
                title=doc_title,
                content=chunk["text"],
                embedding=embedding,
                extra_data={
                    "source": chunk["source"],
                    "page": chunk["page"],
                    "chunk_number": i + 1,
                    "total_chunks": total_chunks,
                    "seccion": chunk.get("seccion"),
                    "is_table": chunk.get("is_table", False),
                    "table_summary": chunk.get("table_summary"),
                    **metadata,
                },
                cuenca=metadata.get("cuenca"),
                tipo_documento=metadata.get("tipo_documento"),
                tipo_equipo=metadata.get("tipo_equipo"),
                normativa_aplicable=metadata.get("normativa_aplicable"),
                pozo_referencia=metadata.get("pozo_referencia"),
                processing_status="completed",
                processing_progress=100,
            )
            db.add(chunk_doc)

        # Mark parent document as completed
        await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(processing_status="completed", processing_progress=100)
        )
        await db.commit()

        # After marking parent as completed, generate insights
        try:
            groq_client = getattr(ai_service, "_groq_client", None)
            if groq_client and all_chunks:
                chunk_texts = [{"text": c["text"]} for c in all_chunks]
                insights = await generate_document_insights(
                    chunk_texts,
                    groq_client,
                )

                # Store insights in the parent document's extra_data
                await db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(
                        extra_data={
                            "filename": filename,
                            **metadata,
                            "insights": insights,
                        }
                    )
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"Could not generate document insights: {e}")

        logger.info(f"Background PDF processing completed for document {document_id}")

    except Exception as e:
        logger.error(
            "Background PDF processing failed for document %s: %s",
            document_id, e,
        )
        await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(processing_status="failed")
        )
        await db.commit()
    finally:
        await db.close()


@router.post("/pdf", status_code=status.HTTP_202_ACCEPTED)
async def ingest_pdf(
    file: Annotated[UploadFile, File(...)],
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Annotated[int, Form()],
    title: Annotated[str, Form()] = "",
    og_metadata: Annotated[str, Form()] = "{}",
) -> dict:
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        logger.warning("Invalid file type: %s", filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )

    # Verify user is member of project
    membership = None
    if not current_user.is_superuser:
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.user_id == current_user.id,
                ProjectMember.project_id == project_id,
            )
        )
        membership = result.scalar_one_or_none()
    if not membership:
        if current_user.is_superuser:
            membership = ProjectMember(role="admin")
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a este proyecto",
            )

    if membership.role not in {"admin", "editor"} and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project editors can ingest documents",
        )

    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    file_bytes = await file.read(max_bytes + 1)
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"PDF exceeds the {settings.max_upload_size_mb} MB limit",
        )
    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content is not a valid PDF",
        )

    doc_title = title.strip() if title.strip() else filename.rsplit(".", 1)[0]
    user_id = current_user.id

    # Parse metadata
    try:
        metadata_dict = json.loads(og_metadata)
        metadata = OGTMetadata(**metadata_dict)
    except Exception:
        metadata = OGTMetadata()

    # Create chat for this document
    chat = Chat(user_id=user_id, title=doc_title)
    db.add(chat)
    await db.flush()

    # Create parent document record (processing)
    parent_doc = Document(
        user_id=user_id,
        chat_id=chat.id,
        project_id=project_id,
        title=doc_title,
        content="[Processing...]",
        extra_data={"filename": filename, **metadata.model_dump()},
        cuenca=metadata.cuenca,
        tipo_documento=metadata.tipo_documento,
        tipo_equipo=metadata.tipo_equipo,
        normativa_aplicable=metadata.normativa_aplicable,
        pozo_referencia=metadata.pozo_referencia,
        processing_status="processing",
        processing_progress=0,
    )
    db.add(parent_doc)
    await db.flush()
    await db.commit()  # Commit so background task can see the document

    # Launch background processing
    background_tasks.add_task(
        _process_pdf_background,
        document_id=parent_doc.id,
        file_bytes=file_bytes,
        user_id=user_id,
        chat_id=chat.id,
        project_id=project_id,
        doc_title=doc_title,
        filename=filename,
        metadata=metadata.model_dump(exclude_none=True),
    )

    logger.info(f"PDF upload accepted, background processing started: {parent_doc.id}")

    return {
        "status": "processing",
        "document_id": parent_doc.id,
        "chat_id": chat.id,
        "project_id": project_id,
        "title": doc_title,
        "filename": filename,
        "message": "PDF is being processed in the background",
    }


@router.get("/status/{document_id}", status_code=status.HTTP_200_OK)
async def get_ingest_status(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    return {
        "document_id": doc.id,
        "title": doc.title,
        "status": doc.processing_status,
        "progress": doc.processing_progress or 0,
        "chat_id": doc.chat_id,
        "project_id": getattr(doc, "project_id", None),
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "insights": doc.extra_data.get("insights") if doc.extra_data else None,
    }


@router.get("/documents", status_code=status.HTTP_200_OK)
async def list_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    from sqlalchemy import func, select as sel
    from app.models import Chat

    chat_docs = (
        sel(
            Chat.id.label("chat_id"),
            Chat.title,
            Chat.created_at,
        )
        .where(Chat.user_id == current_user.id)
    )

    result = await db.execute(chat_docs)
    rows = result.fetchall()

    documents = []
    for row in rows:
        documents.append({
            "id": row[0],
            "title": row[1] or "Sin título",
            "chat_id": row[0],
            "created_at": row[2].isoformat() if row[2] else None,
        })

    return documents
