"""Regression test for the /auth/register handler.

The router used to call :func:`get_password_hash` but forget to attach
the result to the new ``User`` instance, so the INSERT failed with a
``NotNullViolation`` on the ``hashed_password`` column. This test
verifies the happy path end-to-end with the real password hashing
helper so the bug cannot come back.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


def _override_db_with_empty_users():
    """Build a get_db override that returns no existing user and stores
    any inserted object so we can assert on it after the request.
    """
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    created: dict[str, object] = {}

    async def _refresh(obj):
        # ``refresh`` is where SQLAlchemy would normally populate the
        # autoincrement id and the default columns. We mimic the
        # minimum needed for ``UserResponse`` to serialise.
        from datetime import datetime, timezone

        obj.id = 1
        obj.role = getattr(obj, "role", None) or "engineer"
        obj.is_active = True
        obj.is_superuser = False
        obj.created_at = datetime.now(timezone.utc)
        created["user"] = obj
        return obj

    db.refresh = AsyncMock(side_effect=_refresh)

    async def _override():
        yield db

    return db, _override, created


def test_register_hashes_and_persists_password():
    db, override_db, created = _override_db_with_empty_users()
    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "new.user@example.com",
                "username": "new.user",
                "password": "longenoughpassword",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201, response.text
    user = created["user"]
    # The hashed password must be attached to the User instance and
    # must be a real argon2 hash, not the raw plaintext.
    assert user.hashed_password is not None
    assert user.hashed_password != "longenoughpassword"
    assert user.hashed_password.startswith("$argon2")
