"""Tests for the auth cookie and /logout endpoint.

The cookie is HttpOnly + SameSite=Lax by default and Secure in
production. /auth/login sets it; /auth/logout clears it. /auth/me and
the rest of the API should authenticate from EITHER the Authorization
header OR the cookie, with the header taking precedence.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from jose import jwt

from app.api.v1.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.main import app
from app.services.security import ALGORITHM


def _override_db_with_user(user):
    """Build a get_db override that returns the given user from .execute()."""
    db = MagicMock()
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=user))
    )
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.add_all = MagicMock()
    db.flush = AsyncMock()

    async def _override():
        yield db

    return db, _override


def test_login_sets_httpony_cookie():
    user = MagicMock(
        id=1,
        is_active=True,
        is_superuser=False,
        role="engineer",
        hashed_password="argon2-stub",
    )
    db, override_db = _override_db_with_user(user)
    # Stub verify_password so we do not need a real argon2 hash.
    from app.api.v1 import auth as auth_module

    original_verify = auth_module.verify_password
    auth_module.verify_password = lambda plain, hashed: True
    try:
        app.dependency_overrides[get_db] = override_db
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "anyone", "password": "anything"},
        )
        assert response.status_code == 200, response.text
        cookies = response.cookies
        cookie_name = get_settings().auth_cookie_name
        assert cookie_name in cookies, dict(cookies)
        # TestClient returns plain strings here; the value is the JWT.
        assert cookies[cookie_name]
        # HttpOnly flag is set on the response Set-Cookie header.
        set_cookie = response.headers.get("set-cookie", "")
        assert "HttpOnly" in set_cookie, set_cookie
    finally:
        auth_module.verify_password = original_verify
        app.dependency_overrides.clear()


def test_logout_clears_cookie():
    client = TestClient(app)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    cookie_name = get_settings().auth_cookie_name
    assert cookie_name in set_cookie, set_cookie
    # Starlette emits a past-expiry Set-Cookie to clear the cookie.
    assert "expires=" in set_cookie.lower() or "max-age=0" in set_cookie.lower()


def test_get_current_user_accepts_cookie_when_header_missing():
    """`get_current_user` should resolve a User from the cookie alone."""
    settings = get_settings()
    user = MagicMock(id=42, is_active=True)
    db, override_db = _override_db_with_user(user)

    token = jwt.encode(
        {"sub": "42", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    client = TestClient(app, cookies={settings.auth_cookie_name: token})
    app.dependency_overrides[get_db] = override_db
    try:
        # Hit a route that uses get_current_user. /documents is the
        # simplest authenticated endpoint.
        response = client.get("/documents")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text


def test_get_current_user_header_takes_precedence_over_cookie():
    settings = get_settings()
    user = MagicMock(id=99, is_active=True)
    db, override_db = _override_db_with_user(user)

    # Cookie is for user 42, header is for user 99 — header must win.
    cookie_token = jwt.encode(
        {"sub": "42", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    header_token = jwt.encode(
        {"sub": "99", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    client = TestClient(
        app,
        cookies={settings.auth_cookie_name: cookie_token},
    )
    app.dependency_overrides[get_db] = override_db
    try:
        response = client.get(
            "/documents", headers={"Authorization": f"Bearer {header_token}"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    # Inspect the FIRST query: it must be the user lookup, and it must
    # use the header's user_id (99), not the cookie's (42). The
    # ``Select`` object uses bind placeholders (``id_1``) by default,
    # so we recompile it with ``literal_binds=True`` to inline the
    # Python value and check the WHERE clause directly.
    from sqlalchemy import select as sa_select

    user_queries = [
        call
        for call in db.execute.await_args_list
        if "users" in str(call.args[0])
    ]
    assert user_queries, "Expected at least one SELECT against users"
    first_select = user_queries[0].args[0]
    compiled = str(
        first_select.compile(compile_kwargs={"literal_binds": True})
    )
    assert "users.id" in compiled or "FROM users" in compiled
    assert "= 99" in compiled, compiled
    assert "= 42" not in compiled, compiled


def test_get_current_user_without_header_and_without_cookie_is_401():
    client = TestClient(app)
    response = client.get("/documents")
    assert response.status_code == 401
