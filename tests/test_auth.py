"""Tests for auth helpers: token creation, expiry handling, secret-key wiring."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.api.v1.auth import create_access_token
from app.config import get_settings
from app.services.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    get_password_hash,
    verify_password,
)


def test_create_access_token_has_tz_aware_expiry():
    token = create_access_token({"sub": 1, "role": "engineer"})
    payload = jwt.decode(
        token,
        get_settings().secret_key,
        algorithms=[ALGORITHM],
    )
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    issued = datetime.now(timezone.utc)
    # Expiry should be roughly ACCESS_TOKEN_EXPIRE_MINUTES in the future.
    delta = exp - issued
    expected = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Tolerance: 5 seconds to account for execution latency.
    assert abs((delta - expected).total_seconds()) < 5


def test_create_access_token_sub_is_string():
    token = create_access_token({"sub": 42, "role": "engineer"})
    payload = jwt.decode(
        token,
        get_settings().secret_key,
        algorithms=[ALGORITHM],
    )
    assert payload["sub"] == "42"
    assert isinstance(payload["sub"], str)


def test_create_access_token_preserves_extra_claims():
    token = create_access_token({"sub": 1, "role": "admin", "tenant": "acme"})
    payload = jwt.decode(
        token,
        get_settings().secret_key,
        algorithms=[ALGORITHM],
    )
    assert payload["role"] == "admin"
    assert payload["tenant"] == "acme"


def test_password_hashing_roundtrip():
    plain = "P@ssw0rd!seguro-2026"
    hashed = get_password_hash(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_password_hash_uses_argon2():
    hashed = get_password_hash("any-password")
    # Argon2 hashes always start with "$argon2"
    assert hashed.startswith("$argon2")


def test_token_round_trip_with_real_signature():
    """End-to-end: encode + decode via the same secret."""
    settings = get_settings()
    token = create_access_token({"sub": "7", "role": "engineer"})
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    assert payload["sub"] == "7"
    assert payload["role"] == "engineer"
