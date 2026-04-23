from typing import Annotated, Optional
import logging
import io
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models import Chat, Document, User
from app.services.ai_service import get_ai_service, AIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


def clean_filename(filename: str) -> str:
    filename = re.sub(r"\.pdf\.pdf$", ".pdf", filename, flags=re.IGNORECASE)
    filename = re.sub(r"\.pdf$", "", filename, flags=re.IGNORECASE)
    return filename


def extract_text_from_pdf(file_bytes: bytes) -> list[tuple[int, str]]:
    try:
        file_stream = io.BytesIO(file_bytes)
        reader = PdfReader(file_stream)
        
        pages = []
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text.strip():
                pages.append((page_num, text))
        return pages
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def split_into_chunks(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    source: str = "",
    page: int = 1,
    user_id: int = 0,
) -> list[dict]:
    if not text:
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " "],
        length_function=len,
        keep_separator=True,
    )

    chunks = text_splitter.split_text(text)

    return [
        {
            "text": chunk,
            "source": source,
            "page": page,
            "user_id": user_id,
            "chunk_number": i + 1,
            "total_chunks": len(chunks),
        }
        for i, chunk in enumerate(chunks)
    ]


@router.post("/pdf", status_code=status.HTTP_201_CREATED)
async def ingest_pdf(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    title: Annotated[str, Form()] = "",
) -> dict:
    if not file.filename.endswith(".pdf"):
        logger.warning(f"Invalid file type: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    doc_title = title.strip() if title.strip() else clean_filename(file.filename)
    user_id = current_user.id
    
    # Crear un nuevo chat para este documento
    chat = Chat(user_id=user_id, title=doc_title)
    db.add(chat)
    await db.flush()
    # No hacemos commit aún - necesitamos el chat.id después
    logger.info(f"Created new chat with id: {chat.id}")
    
    try:
        logger.info(f"Starting PDF ingestion: {file.filename}")
        
        file_bytes = await file.read()
        logger.info(f"File read successfully, size: {len(file_bytes)} bytes")
        
        pages = extract_text_from_pdf(file_bytes)
        
        if not pages:
            logger.warning(f"Empty text extracted from PDF: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from PDF"
            )
        
        all_chunks = []
        for page_num, page_text in pages:
            page_chunks = split_into_chunks(
                page_text,
                chunk_size=1000,
                chunk_overlap=200,
                source=file.filename,
                page=page_num,
                user_id=user_id,
            )
            all_chunks.extend(page_chunks)
        
        total_chunks = len(all_chunks)
        logger.info(f"Text split into {total_chunks} chunks across {len(pages)} pages")
        
        documents_created = 0
        for i, chunk in enumerate(all_chunks):
            try:
                embedding = await ai_service.get_embedding(chunk["text"])
                
                document = Document(
                    user_id=chunk["user_id"],
                    chat_id=chat.id,
                    title=doc_title,
                    content=chunk["text"],
                    embedding=embedding,
                    extra_data={
                        "source": chunk["source"],
                        "page": chunk["page"],
                        "chunk_number": i + 1,
                        "total_chunks": total_chunks,
                    },
                )
                
                db.add(document)
                documents_created += 1
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {str(e)}")
                raise
        
        await db.commit()
        
        logger.info(f"PDF ingested successfully: {documents_created} chunks created")
        
        return {
            "message": "PDF ingested successfully",
            "title": doc_title,
            "filename": file.filename,
            "chunks_created": documents_created,
            "total_text_length": sum(len(p) for _, p in pages),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process PDF: {str(e)}", exc_info=True)
        await db.rollback()
        print(f"[ERROR] PDF upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}"
        )


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