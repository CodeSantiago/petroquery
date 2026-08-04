"""Rate-limit regression tests for the auth flow.

The smoke tests for /health and /documents do not exercise login or
register, so they are unaffected by the limiter. These tests pin down
the contract so future changes cannot silently disable rate limiting.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.rate_limit import limiter


@pytest.fixture(autouse=True)
def _toggle_rate_limit():
    """Toggle the rate limiter around each test in this module.

    The limiter is a process-wide singleton; most tests need it OFF.
    Each test in this module opts in by calling ``_enable_rate_limit()``
    and the fixture turns it OFF again on teardown.
    """
    from app.config import get_settings

    previous = get_settings().rate_limit_enabled
    get_settings().rate_limit_enabled = False
    limiter.enabled = False
    yield
    get_settings().rate_limit_enabled = previous
    limiter.enabled = previous


def _enable_rate_limit():
    from app.config import get_settings

    get_settings().rate_limit_enabled = True
    limiter.enabled = True
    try:
        limiter.reset()
    except AttributeError:  # older slowapi versions
        pass


def _build_db_override():
    """Return a get_db override that mimics an empty users table.

    ``db.refresh`` is given a side effect that populates the new user
    with an id, role, is_active, is_superuser and created_at so the
    /auth/register response (UserResponse) can serialise without a
    ResponseValidationError. The endpoint still returns a valid 201
    after the limiter kicks in.
    """
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    db.commit = AsyncMock()

    async def _refresh(obj):
        from datetime import datetime, timezone

        obj.id = 1
        # ``role`` may exist on the model with a default of "engineer",
        # but the dataclass-style assignment made in /auth/register can
        # leave it as None. Force a sane value either way.
        obj.role = obj.role or "engineer"
        obj.is_active = True
        obj.is_superuser = False
        obj.created_at = datetime.now(timezone.utc)
        return obj

    db.refresh = AsyncMock(side_effect=_refresh)
    db.add = MagicMock()
    db.add_all = MagicMock()
    db.flush = AsyncMock()

    async def _override():
        yield db

    return db, _override


def test_login_endpoint_is_rate_limited():
    """After the configured number of failed logins, the next one is 429."""
    _enable_rate_limit()
    db, override_db = _build_db_override()
    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        for _ in range(50):
            response = client.post(
                "/api/v1/auth/login",
                data={"username": "ghost", "password": "nope"},
            )
            if response.status_code == 429:
                break
        else:  # pragma: no cover - sanity guard
            pytest.fail("Expected /auth/login to eventually 429")
        assert response.status_code == 429
    finally:
        app.dependency_overrides.clear()


def test_register_endpoint_is_rate_limited():
    _enable_rate_limit()
    db, override_db = _build_db_override()
    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        for i in range(50):
            payload = {
                "email": f"x{i}@example.com",
                "username": f"x{i}",
                "password": "longenoughpw",
            }
            response = client.post("/api/v1/auth/register", json=payload)
            if response.status_code == 429:
                break
        else:  # pragma: no cover
            pytest.fail("Expected /auth/register to eventually 429")
        assert response.status_code == 429
    finally:
        app.dependency_overrides.clear()
