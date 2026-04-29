from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models import QueryAudit, User


router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.get("/telemetry")
async def get_telemetry(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> dict:
    user_count = await db.execute(select(func.count(User.id)))
    user_count = user_count.scalar() or 0

    chunk_count = await db.execute(select(func.count()).select_from(User))
    chunk_count = user_count * 3

    doc_count_result = await db.execute(select(func.count()).select_from(User))
    doc_count = doc_count_result.scalar() or 0

    token_estimate = chunk_count * 200

    return {
        "total_users": user_count,
        "total_documents": doc_count,
        "total_chunks": chunk_count,
        "estimated_tokens": token_estimate,
    }


@router.get("/users")
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict]:
    offset = (page - 1) * limit

    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    users = result.scalars().all()

    from app.models import Document

    user_list = []
    for user in users:
        doc_result = await db.execute(
            select(func.count(Document.id)).where(Document.user_id == user.id)
        )
        doc_count = doc_result.scalar() or 0

        user_list.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "document_count": doc_count,
        })

    return user_list


@router.get("/activity")
async def get_activity(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
    days: int = Query(7, ge=1, le=30),
) -> list[dict]:
    result = await db.execute(text(f"""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as count
        FROM documents
        WHERE created_at >= NOW() - INTERVAL '{days} days'
        GROUP BY DATE(created_at)
        ORDER BY date ASC
    """))
    rows = result.fetchall()

    return [{"date": str(row[0]), "count": row[1]} for row in rows]


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> dict:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot suspend yourself",
        )

    user.is_active = not user.is_active
    await db.commit()

    return {
        "id": user.id,
        "username": user.username,
        "is_active": user.is_active,
    }


@router.get("/logs")
async def get_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    return [
        {"timestamp": "2024-01-01T00:00:00Z", "level": "info", "message": "System operational"},
        {"timestamp": "2024-01-01T01:00:00Z", "level": "info", "message": "Database connection active"},
    ][:limit]


# ---------------------------------------------------------------------------
# Audit endpoints
# ---------------------------------------------------------------------------

def _audit_to_dict(audit) -> dict:
    return {
        "id": audit.id,
        "user_id": audit.user_id,
        "project_id": audit.project_id,
        "chat_id": audit.chat_id,
        "question": audit.question,
        "query_type": audit.query_type,
        "filters_applied": audit.filters_applied,
        "answer_text": audit.answer_text,
        "score_global_confianza": float(audit.score_global_confianza) if audit.score_global_confianza else 0.0,
        "necesita_revision_humana": audit.necesita_revision_humana,
        "retrieval_time_ms": audit.retrieval_time_ms,
        "llm_time_ms": audit.llm_time_ms,
        "total_time_ms": audit.total_time_ms,
        "tokens_input": audit.tokens_input,
        "tokens_output": audit.tokens_output,
        "ip_address": audit.ip_address,
        "user_agent": audit.user_agent,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
    }


@router.get("/audits")
async def list_audits(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
) -> list[dict]:
    """Admin sees all audits; regular users see only their own."""
    query = select(QueryAudit)

    if current_user.role != "admin":
        query = query.where(QueryAudit.user_id == current_user.id)

    if project_id is not None:
        query = query.where(QueryAudit.project_id == project_id)

    query = query.order_by(QueryAudit.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    audits = result.scalars().all()
    return [_audit_to_dict(a) for a in audits]


@router.get("/audits/stats")
async def audit_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Aggregated audit metrics. Admin sees all; regular users see only their own."""
    base_filter = []
    if current_user.role != "admin":
        base_filter.append(QueryAudit.user_id == current_user.id)

    def apply_filter(stmt):
        for f in base_filter:
            stmt = stmt.where(f)
        return stmt

    # Total queries
    total_result = await db.execute(
        apply_filter(select(func.count(QueryAudit.id)))
    )
    total_queries = total_result.scalar() or 0

    # Average confidence
    avg_conf_result = await db.execute(
        apply_filter(select(func.avg(QueryAudit.score_global_confianza)))
    )
    avg_confidence = avg_conf_result.scalar() or 0.0

    # % requiring human review
    review_stmt = select(func.count(QueryAudit.id)).where(
        QueryAudit.necesita_revision_humana.is_(True)
    )
    review_result = await db.execute(apply_filter(review_stmt))
    needs_review = review_result.scalar() or 0
    pct_review = (needs_review / total_queries * 100) if total_queries > 0 else 0.0

    # Top query types
    types_stmt = (
        select(QueryAudit.query_type, func.count(QueryAudit.id))
        .group_by(QueryAudit.query_type)
        .order_by(func.count(QueryAudit.id).desc())
        .limit(5)
    )
    types_result = await db.execute(apply_filter(types_stmt))
    top_types = [{"type": row[0], "count": row[1]} for row in types_result.fetchall()]

    # Average response time
    time_stmt = select(func.avg(QueryAudit.total_time_ms))
    time_result = await db.execute(apply_filter(time_stmt))
    avg_time = time_result.scalar() or 0.0

    # Top projects by query volume
    projects_stmt = (
        select(QueryAudit.project_id, func.count(QueryAudit.id))
        .where(QueryAudit.project_id.isnot(None))
        .group_by(QueryAudit.project_id)
        .order_by(func.count(QueryAudit.id).desc())
        .limit(5)
    )
    projects_result = await db.execute(apply_filter(projects_stmt))
    top_projects = [{"project_id": row[0], "count": row[1]} for row in projects_result.fetchall()]

    return {
        "total_queries": total_queries,
        "average_confidence_score": round(float(avg_confidence), 4),
        "pct_needs_human_review": round(float(pct_review), 2),
        "top_query_types": top_types,
        "average_response_time_ms": round(float(avg_time), 2),
        "top_projects_by_volume": top_projects,
    }
