"""Project access helpers."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProjectMember, User


async def assert_project_access(
    db: AsyncSession,
    current_user: User,
    project_id: int | None,
) -> None:
    """Raise 403 when ``project_id`` is set and the user is not a member.

    When ``project_id`` is ``None`` this is a no-op: the request simply
    doesn't restrict by project.
    """
    if project_id is None:
        return

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


__all__ = ["assert_project_access"]
