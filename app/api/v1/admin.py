import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models import Project, ProjectMember, QueryAudit, User
from app.schemas.base_schemas import UserInvite, UserResponse
from app.services.security import get_password_hash

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_superuser and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.post("/prewarm", status_code=status.HTTP_200_OK)
async def prewarm_model(
    admin: Annotated[User, Depends(require_admin)],
) -> dict:
    """Pre-load the E5 embedding model to avoid cold-start delays."""
    ai_service = get_ai_service()
    ai_service.prewarm()
    return {"status": "warmed", "model": "multilingual-e5-large"}


@router.get("/audits", response_model=list[dict])
async def list_audits(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    result = await db.execute(
        select(QueryAudit)
        .order_by(QueryAudit.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    audits = result.scalars().all()
    return [
        {
            "id": audit.id,
            "user_id": audit.user_id,
            "project_id": audit.project_id,
            "chat_id": audit.chat_id,
            "question": audit.question,
            "query_type": audit.query_type,
            "answer_text": audit.answer_text[:500] if audit.answer_text else None,
            "score_global_confianza": audit.score_global_confianza,
            "necesita_revision_humana": audit.necesita_revision_humana,
            "retrieval_time_ms": audit.retrieval_time_ms,
            "llm_time_ms": audit.llm_time_ms,
            "total_time_ms": audit.total_time_ms,
            "tokens_input": audit.tokens_input,
            "tokens_output": audit.tokens_output,
            "created_at": audit.created_at.isoformat() if audit.created_at else None,
        }
        for audit in audits
    ]


@router.get("/audits/stats", response_model=dict)
async def get_audit_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> dict:
    total_queries_result = await db.execute(select(func.count(QueryAudit.id)))
    total_queries = total_queries_result.scalar() or 0

    avg_score_result = await db.execute(select(func.avg(QueryAudit.score_global_confianza)))
    avg_score = avg_score_result.scalar() or 0.0

    human_review_result = await db.execute(
        select(func.count(QueryAudit.id)).where(QueryAudit.necesita_revision_humana == True)
    )
    human_review_count = human_review_result.scalar() or 0

    avg_total_time_result = await db.execute(select(func.avg(QueryAudit.total_time_ms)))
    avg_total_time = avg_total_time_result.scalar() or 0.0

    query_type_result = await db.execute(
        select(QueryAudit.query_type, func.count(QueryAudit.id))
        .group_by(QueryAudit.query_type)
    )
    query_types = {row[0]: row[1] for row in query_type_result.fetchall()}

    return {
        "total_queries": total_queries,
        "average_confidence_score": round(float(avg_score), 4),
        "human_review_required": human_review_count,
        "average_total_time_ms": round(float(avg_total_time), 2) if avg_total_time else 0.0,
        "queries_by_type": query_types,
    }


@router.post("/invite", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    data: UserInvite,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> User:
    # 1. Check if email already exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Check if username already exists
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    # 3. Check if project exists
    result = await db.execute(select(Project).where(Project.id == data.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 4. Generate a random temporary password
    temp_password = secrets.token_urlsafe(12)
    hashed_password = get_password_hash(temp_password)

    # 5. Create user
    new_user = User(
        email=data.email,
        username=data.username,
        hashed_password=hashed_password,
        role=data.role,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # 6. Add to project as member
    member = ProjectMember(
        user_id=new_user.id,
        project_id=data.project_id,
        role="viewer" if data.role == "operator" else "editor",
    )
    db.add(member)

    await db.commit()
    await db.refresh(new_user)

    # Log the temp password (in production, you'd email it)
    print(f"[INVITE] User {new_user.username} invited to project {data.project_id}. Temp password: {temp_password}")

    return new_user
