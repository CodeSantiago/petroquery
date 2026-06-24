"""Shared pytest fixtures and configuration for the PetroQuery test suite.

The application loads its settings eagerly at import time (it caches them
in ``app.config.get_settings``), so each test that wants a clean
configuration must reset the LRU cache before the settings are
re-instantiated. The fixtures below do exactly that.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make the project root importable when tests are run from anywhere.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure the config module does not see a real .env when we test.
os.environ.setdefault("APP_ENV", "development")


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Reset the ``get_settings`` LRU cache between tests."""
    from app import config as app_config

    app_config.get_settings.cache_clear()
    yield
    app_config.get_settings.cache_clear()


@pytest.fixture
def production_env(monkeypatch):
    """Helper to flip the environment to production for a single test.

    The fixture also clears the settings cache so the next call to
    ``get_settings()`` re-reads the env vars.
    """
    for var in (
        "APP_ENV",
        "SECRET_KEY",
        "DATABASE_URL",
        "CORS_ALLOWED_ORIGINS",
        "GROQ_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    yield
