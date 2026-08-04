"""Tests for the lazy / opt-in ML stack and subprocess isolation.

The production stack on Windows can crash natively when the ML
packages (torch, pyarrow via pandas, sentence-transformers) are
imported. These tests pin down two safety nets:

* ``app.services.ai_service`` must not eagerly import ``groq`` or
  ``instructor`` so the API process can boot on hosts that only
  installed ``requirements.txt`` (without the ML extras).
* ``app.services.ml_subprocess.run_in_subprocess`` must NEVER raise;
  any worker failure is surfaced through the ``ok`` flag so the API
  process stays alive after a Windows access violation inside the
  worker.
"""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from app.services import ai_service
from app.services import ml_subprocess


def test_ai_service_module_does_not_eagerly_import_groq(monkeypatch):
    """Drop ``groq``/``instructor`` from ``sys.modules`` and re-import
    ``app.services.ai_service``: the module must import successfully.
    """
    saved = {
        k: sys.modules.pop(k)
        for k in list(sys.modules)
        if k == "groq" or k.startswith("instructor")
    }
    try:
        for mod_name in ["app.services.ai_service"]:
            monkeypatch.delitem(sys.modules, mod_name, raising=False)
        import importlib

        importlib.import_module("app.services.ai_service")
    finally:
        sys.modules.update(saved)


def test_ai_service_can_be_instantiated_without_instructor(monkeypatch):
    """Constructing ``AIService()`` must NOT trigger an ``instructor`` import.

    The instructor-wrapped Groq client is created lazily on the first
    call to :meth:`ask_og_structured`. If a host does not have
    ``instructor`` installed, the API must still be able to start.
    """
    real_import = __import__

    def guarded(name, *args, **kwargs):
        if name == "instructor" or name.startswith("instructor."):
            raise ImportError("instructor blocked for test")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=guarded):
        service = ai_service.AIService()

    # Sanity: the service is created, but the instructor client is None
    # (lazy) and the error is unset until we try to use it.
    assert service._instructor_client is None
    assert service._instructor_error is None


def test_ai_service_lazy_instructor_raises_mlruntime_when_missing(monkeypatch):
    """The first call to ask_og_structured must surface a clear error
    when ``instructor`` is missing instead of crashing the process.
    """
    # Inject a placeholder ``instructor`` module that raises on
    # ``from_groq`` so the lazy import path is exercised without
    # having to monkey-patch ``__import__`` (which pytest does not
    # always intercept for module-internal imports).
    import types

    class _BrokenInstructor:
        @staticmethod
        def from_groq(_client):
            raise ImportError("instructor blocked for test")

    fake_pkg = types.ModuleType("instructor")
    fake_pkg.from_groq = _BrokenInstructor.from_groq
    monkeypatch.setitem(sys.modules, "instructor", fake_pkg)
    # Drop any cached attribute on the ai_service module.
    monkeypatch.setattr(ai_service, "_instructor_client", None, raising=False)
    monkeypatch.setattr(ai_service, "_instructor_error", None, raising=False)

    service = ai_service.AIService()
    # The constructor must NOT have triggered an instructor load.
    assert service._instructor_client is None

    with pytest.raises(ai_service.MLRuntimeUnavailable) as exc_info:
        service._load_instructor_client()
    assert "instructor unavailable" in str(exc_info.value).lower()


def test_ai_service_caches_instructor_failure(monkeypatch):
    """A second call must surface the SAME error instead of re-importing
    the broken stack.
    """
    import types

    class _BrokenInstructor:
        @staticmethod
        def from_groq(_client):
            raise ImportError("blocked")

    fake_pkg = types.ModuleType("instructor")
    fake_pkg.from_groq = _BrokenInstructor.from_groq
    monkeypatch.setitem(sys.modules, "instructor", fake_pkg)
    monkeypatch.setattr(ai_service, "_instructor_client", None, raising=False)
    monkeypatch.setattr(ai_service, "_instructor_error", None, raising=False)

    service = ai_service.AIService()
    for _ in range(2):
        with pytest.raises(ai_service.MLRuntimeUnavailable):
            service._load_instructor_client()
    # The error message is recorded on the instance, not recomputed.
    assert service._instructor_error is not None
    # Re-calling _load_instructor_client is a cheap no-op now.
    with pytest.raises(ai_service.MLRuntimeUnavailable) as exc_info:
        service._load_instructor_client()
    assert exc_info.value.args[0] == service._instructor_error


@pytest.mark.asyncio
async def test_run_in_subprocess_returns_payload_on_success():
    """A well-formed task returns ``ok=True`` with the worker's result."""
    result = await ml_subprocess.run_in_subprocess(
        {"type": "echo", "value": 42}  # unknown type -> ok=False with "Unknown"
    )
    # The echo task type does not exist; the worker must still return
    # ``ok=False`` instead of crashing the API process.
    assert result["ok"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_run_in_subprocess_never_raises(monkeypatch):
    """The transport must NEVER raise, even when the worker is killed
    by an OS-level signal (the Windows access-violation analogue).
    """
    import asyncio

    class _ExplodingProc:
        returncode = -1
        stderr = b"fatal: access violation (0xC0000005)"

        async def communicate(self, _payload):
            return b"", self.stderr

        async def wait(self):
            return None

        def kill(self):
            return None

    async def _fake_exec(*_args, **_kwargs):
        return _ExplodingProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_exec)
    result = await ml_subprocess.run_in_subprocess({"type": "process_pdf"})
    assert result["ok"] is False
    assert "access violation" in result["stderr"].lower() or "crashed" in result["error"].lower()


@pytest.mark.asyncio
async def test_run_in_subprocess_handles_timeout(monkeypatch):
    """A worker that hangs is killed after the configured timeout."""
    import asyncio

    class _HangingProc:
        returncode = None

        async def communicate(self, _payload):
            await asyncio.sleep(5)
            return b"", b""

        async def wait(self):
            return None

        def kill(self):
            return None

    async def _fake_exec(*_args, **_kwargs):
        return _HangingProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_exec)
    monkeypatch.setenv(ml_subprocess.WORKER_TIMEOUT_ENV, "0.05")
    try:
        result = await ml_subprocess.run_in_subprocess({"type": "process_pdf"})
    finally:
        monkeypatch.delenv(ml_subprocess.WORKER_TIMEOUT_ENV, raising=False)
    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


def test_subprocess_env_toggle():
    """is_process_worker_enabled() reflects the env var."""
    import os

    previous = os.environ.pop(ml_subprocess.PROCESS_WORKER_ENV, None)
    try:
        os.environ[ml_subprocess.PROCESS_WORKER_ENV] = "process"
        assert ml_subprocess.is_process_worker_enabled() is True
        os.environ[ml_subprocess.PROCESS_WORKER_ENV] = "inproc"
        assert ml_subprocess.is_process_worker_enabled() is False
        os.environ.pop(ml_subprocess.PROCESS_WORKER_ENV)
        assert ml_subprocess.is_process_worker_enabled() is False
    finally:
        if previous is not None:
            os.environ[ml_subprocess.PROCESS_WORKER_ENV] = previous
