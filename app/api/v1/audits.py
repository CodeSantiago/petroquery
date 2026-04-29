from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models import QueryAudit, User

router = APIRouter(prefix="/audits", tags=["audits"])


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


@router.get("/my")
async def list_my_audits(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    result = await db.execute(
        select(QueryAudit)
        .where(QueryAudit.user_id == current_user.id)
        .order_by(QueryAudit.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    audits = result.scalars().all()
    return [_audit_to_dict(a) for a in audits]


@router.get("/my/{audit_id}")
async def get_my_audit(
    audit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    result = await db.execute(
        select(QueryAudit)
        .where(
            QueryAudit.id == audit_id,
            QueryAudit.user_id == current_user.id,
        )
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    return _audit_to_dict(audit)
