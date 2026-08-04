from contextlib import asynccontextmanager
from importlib.util import find_spec
from typing import Annotated, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import router as auth_router, get_current_user
from app.api.v1.admin import router as admin_router
from app.api.v1.audits import router as audits_router
from app.api.v1.chat import router as chat_router
from app.api.v1.chats import router as messages_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.projects import router as projects_router
from app.config import get_settings
from app.database import Base, engine, get_db
from app.models import Document, ProjectMember, User
from app.rate_limit import limiter
from app.schemas import DocumentResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    # Optional prewarm of the embedding model. The import is lazy so the
    # process can boot on hosts that do not have the ML stack installed
    # (CI runners, smoke tests, health-only deployments).
    if settings.prewarm_model_on_startup:
        try:
            from app.services.ai_service import get_ai_service

            await get_ai_service().get_embedding("warmup")
        except Exception as exc:  # noqa: BLE001 — log and continue
            print(f"[STARTUP] Prewarm skipped: {type(exc).__name__}: {exc}")

    print("✅ PetroQuery startup complete")

    yield

    await engine.dispose()
    print("✅ PetroQuery shutdown complete")


settings = get_settings()

app = FastAPI(
    title="PetroQuery",
    description="RAG Industrial para Oil & Gas — Especializado en operaciones de Vaca Muerta, Argentina",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS: explicit origins from configuration, not wildcard.
# Credentials are only allowed when origins are not "*", because browsers
# reject credentialed requests with a wildcard Access-Control-Allow-Origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=not settings.cors_allow_all,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Rate limiting (slowapi). The Limiter instance lives in app.rate_limit
# so the routers can decorate their endpoints with `@limiter.limit(...)`
# without coupling to this module.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(messages_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(audits_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Public liveness probe.

    Reports whether the optional ML stack is *installable*. We do not
    import it (the import can pull in pyarrow/scikit-learn which crash
    on some hosts) and we do not instantiate the model (1-2 GB RAM).
    RAG endpoints will surface a detailed error if the model fails to
    load on first use.
    """
    ml_status = (
        "available" if find_spec("sentence_transformers") is not None else "unavailable"
    )
    return {
        "status": "healthy",
        "system": "PetroQuery",
        "ml_status": ml_status,
    }


@app.delete("/documents/clear", status_code=status.HTTP_200_OK)
async def clear_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Dangerous bulk-delete endpoint. Requires an authenticated superuser.

    This route remains in the public router for backward compatibility with
    existing tooling, but is now guarded: only superusers can call it. The
    admin dashboard provides a safer project-scoped alternative.
    """
    from app.api.v1.admin import require_admin

    # Reuse the admin guard for consistent 403 behaviour.
    await require_admin(current_user=_admin)

    try:
        await db.execute(text("DELETE FROM documents"))
        await db.commit()
        return {"message": "All documents deleted successfully"}
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear documents",
        )


@app.get("/documents", status_code=status.HTTP_200_OK)
async def list_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> list[DocumentResponse]:
    query = select(Document)
    if not _user.is_superuser:
        query = query.join(ProjectMember, ProjectMember.project_id == Document.project_id).where(
            ProjectMember.user_id == _user.id
        )
    result = await db.execute(query.order_by(Document.id.desc()))
    documents = result.scalars().unique().all()
    return [DocumentResponse.model_validate(doc) for doc in documents]


@app.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> DocumentResponse:
    try:
        query = select(Document).where(Document.id == document_id)
        if not _user.is_superuser:
            query = query.join(
                ProjectMember, ProjectMember.project_id == Document.project_id
            ).where(ProjectMember.user_id == _user.id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id {document_id} not found",
            )

        return DocumentResponse.model_validate(document)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document",
        )
