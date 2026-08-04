"""Shared rate-limit configuration.

The :data:`limiter` is created at import time from
:func:`app.config.get_settings`. Routers import it directly so the
limit is consistent across the API and easy to override in tests.

Storage
-------
The default storage URI is ``memory://`` (process-local). Production
deployments should set ``RATE_LIMIT_STORAGE_URI`` to a Redis URL
(``redis://host:6379/0``) so the limit is shared across workers.

Testing
-------
Set ``RATE_LIMIT_ENABLED=false`` in the test environment to make the
limiter a no-op so E2E and load tests can drive many requests.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings


def build_limiter() -> Limiter:
    """Build a fresh :class:`Limiter` from the current settings."""
    settings = get_settings()
    return Limiter(
        key_func=get_remote_address,
        storage_uri=settings.rate_limit_storage_uri,
        enabled=settings.rate_limit_enabled,
    )


# Eager instance — routers import this directly. ``build_limiter()`` is
# available for tests that need to rebuild the limiter with a different
# storage URI without re-importing this module.
limiter: Limiter = build_limiter()


__all__ = ["limiter", "build_limiter"]
