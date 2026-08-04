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
def _reset_settings_cache(monkeypatch):
    """Reset the ``get_settings`` LRU cache between tests."""
    from app import config as app_config

    # Tests must not inherit real local secrets from the developer's .env.
    monkeypatch.setitem(app_config.Settings.model_config, "env_file", None)
    app_config.get_settings.cache_clear()
    yield
    app_config.get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _disable_rate_limit_by_default():
    """Disable the global slowapi limiter for the test suite.

    Most tests do not exercise the rate-limit logic and would be
    brittle if a previous test left the limiter enabled. Tests that
    DO want to exercise it (see ``tests/test_rate_limit.py``) opt
    back in via the helper defined in that module.
    """
    from app.config import get_settings
    from app.rate_limit import limiter

    previous_enabled = get_settings().rate_limit_enabled
    get_settings().rate_limit_enabled = False
    limiter.enabled = False
    try:
        # Clear any in-memory counters left by earlier tests.
        try:
            limiter.reset()
        except AttributeError:
            pass
        yield
    finally:
        get_settings().rate_limit_enabled = previous_enabled
        limiter.enabled = previous_enabled


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
