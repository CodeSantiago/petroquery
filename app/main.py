from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base, engine, get_db
from app.models import Document, Message, User
from app.schemas import DocumentResponse
from app.api.v1.chat import router as chat_router, messages_router as messages_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.auth import router as auth_router, get_current_user
from app.api.v1.admin import router as admin_router
from app.api.v1.audits import router as audits_router
from app.api.v1.projects import router as projects_router
from app.services.ai_service import AIService, get_ai_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    ai_service = get_ai_service()
    await ai_service.get_embedding("warmup")

    print("✅ PetroQuery startup complete")

    yield

    await engine.dispose()
    print("✅ PetroQuery shutdown complete")


app = FastAPI(
    title="PetroQuery",
    description="RAG Industrial para Oil & Gas — Especializado en operaciones de Vaca Muerta, Argentina",
    version="2.0.0",
    lifespan=lifespan,
)

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
app.include_router(audits_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "system": "PetroQuery"}


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
