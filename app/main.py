from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base, engine, get_db
from app.models import Chat, Document, Message, User
from app.schemas import DocumentCreate, DocumentResponse
from app.api.v1.chat import router as chat_router, messages_router as messages_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.auth import router as auth_router, get_current_user
from app.api.v1.admin import router as admin_router
from app.services.ai_service import AIService, get_ai_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    ai_service = get_ai_service()
    await ai_service.get_embedding("warmup")

    print("✅ Startup complete")

    yield

    await engine.dispose()
    print("✅ Shutdown complete")


app = FastAPI(title="Brain-API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(messages_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.delete("/documents/clear", status_code=status.HTTP_200_OK)
async def clear_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        await db.execute(text("DELETE FROM documents"))
        await db.commit()
        return {"message": "All documents deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear documents: {str(e)}"
        )


@app.post("/ingest", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    document_data: DocumentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentResponse:
    from app.api.v1.ingest import split_into_chunks
    
    # Crear un nuevo chat para este documento
    chat = Chat(user_id=current_user.id, title=document_data.title)
    db.add(chat)
    await db.flush()
    
    try:
        chunks = split_into_chunks(document_data.content, chunk_size=1000, overlap=200)
        
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No content to ingest"
            )
        
        first_chunk = chunks[0]
        embedding = await ai_service.get_embedding(first_chunk)
        
        print(f"Embedding generated: {embedding[:5]}...")
        
        document = Document(
            user_id=current_user.id,
            chat_id=chat.id,
            title=document_data.title,
            content=first_chunk,
            extra_data={**document_data.metadata, "total_chunks": len(chunks)},
            embedding=embedding,
        )
        
        db.add(document)
        
        for i, chunk in enumerate(chunks[1:], start=1):
            chunk_embedding = await ai_service.get_embedding(chunk)
            chunk_doc = Document(
                user_id=current_user.id,
                chat_id=chat.id,
                title=document_data.title,
                content=chunk,
                extra_data={**document_data.metadata, "chunk_number": i + 1, "total_chunks": len(chunks)},
                embedding=chunk_embedding,
            )
            db.add(chunk_doc)
        
        await db.commit()
        await db.refresh(document)
        
        return DocumentResponse.model_validate(document)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document: {str(e)}"
        )


@app.get("/documents", status_code=status.HTTP_200_OK)
async def list_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentResponse]:
    result = await db.execute(select(Document).order_by(Document.id.desc()))
    documents = result.scalars().all()
    return [DocumentResponse.model_validate(doc) for doc in documents]


@app.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    try:
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id {document_id} not found"
            )
        
        return DocumentResponse.model_validate(document)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document: {str(e)}"
        )