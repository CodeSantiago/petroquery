"""Regression tests for the security hardening work."""
from __future__ import annotations

import secrets

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock

from app.config import Settings
from app.models import User
from app.services.persistence.project_repository import assert_project_access
from app.schemas.base_schemas import UserInvite


def test_project_admin_cannot_be_created_by_invite_schema():
    with pytest.raises(ValueError):
        UserInvite(
            email="admin@example.com",
            username="new-admin",
            role="admin",
            project_id=1,
        )


def test_production_rejects_temporary_password_logging(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db/app")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("INVITE_LOG_TEMP_PASSWORD", "true")

    with pytest.raises(ValueError, match="INVITE_LOG_TEMP_PASSWORD"):
        Settings()


@pytest.mark.asyncio
async def test_superuser_project_access_does_not_query_membership():
    db = MagicMock(spec=AsyncSession)
    user = User(
        id=1,
        email="root@example.com",
        username="root",
        hashed_password="h",
        is_superuser=True,
    )

    await assert_project_access(db, user, 999)

    assert not hasattr(db, "execute") or not db.execute.called


@pytest.mark.asyncio
async def test_non_member_project_access_is_forbidden():
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    user = User(id=1, email="u@example.com", username="user", hashed_password="h")

    with pytest.raises(HTTPException) as exc_info:
        await assert_project_access(db, user, 999)

    assert exc_info.value.status_code == 403
