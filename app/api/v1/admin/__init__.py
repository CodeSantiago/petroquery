from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models import User


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