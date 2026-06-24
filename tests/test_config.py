"""Tests for application configuration: secret handling, CORS, env defaults."""
from __future__ import annotations

import secrets

import pytest

from app.config import Settings, get_settings


def test_secret_key_generated_when_missing_in_development(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "development")

    settings = Settings()

    # In development an ephemeral key is generated when none is provided.
    assert settings.secret_key
    assert len(settings.secret_key) >= 32
    assert settings.app_env == "development"


def test_secret_key_must_be_set_in_production(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")

    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings()


def test_secret_key_must_be_long_enough_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "short")  # 5 chars, way below threshold
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")

    with pytest.raises(ValueError, match="32 characters"):
        Settings()


def test_secret_key_accepted_in_production(monkeypatch):
    real_key = secrets.token_urlsafe(48)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", real_key)
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")

    settings = Settings()
    assert settings.secret_key == real_key


def test_cors_wildcard_rejected_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")

    with pytest.raises(ValueError, match="Wildcard"):
        Settings()


def test_cors_origins_parsed(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://a.com, https://b.com ,")

    settings = Settings()
    assert settings.cors_origins_list == ["https://a.com", "https://b.com"]
    assert settings.cors_allow_all is False


def test_cors_wildcard_explicitly_allowed_in_dev(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")

    settings = Settings()
    assert settings.cors_allow_all is True


def test_cors_must_be_non_empty_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")

    with pytest.raises(ValueError, match="CORS_ALLOWED_ORIGINS"):
        Settings()


def test_database_url_required_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="DATABASE_URL"):
        Settings()


def test_get_settings_is_cached():
    a = get_settings()
    b = get_settings()
    assert a is b
