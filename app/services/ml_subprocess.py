"""Subprocess isolation for heavy ML work.

On Windows hosts, native crashes inside the ML stack (torch,
sentence-transformers, pyarrow via pandas, pdfplumber's image
dependencies) cannot be caught by Python ``try/except``: a Windows
access violation that lands in a thread of the API process takes the
whole process down. Running the heavy work in a separate Python
process isolates the crash to that subprocess — the API stays up and
the affected document is simply marked as failed.

The subprocess mode is **opt-in** via the ``PETROQUERY_ML_WORKER``
environment variable. The default behaviour is unchanged (in-process
execution) so existing deployments and tests are not affected.

Environment variables
---------------------
``PETROQUERY_ML_WORKER``
    Set to ``"process"`` to run heavy ML work in a subprocess. The
    default (``""`` or ``"inproc"``) keeps the legacy in-process
    behaviour. The variable is read once at import time; restart the
    API to change the mode.

``PETROQUERY_ML_WORKER_TIMEOUT``
    Wall-clock timeout in seconds for a single worker invocation.
    Defaults to 600 (10 minutes) which is enough for a multi-page
    technical PDF with embedding generation.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public configuration
# ---------------------------------------------------------------------------
PROCESS_WORKER_ENV = "PETROQUERY_ML_WORKER"
WORKER_TIMEOUT_ENV = "PETROQUERY_ML_WORKER_TIMEOUT"
DEFAULT_TIMEOUT_S = 600.0


def is_process_worker_enabled() -> bool:
    """Return True when the heavy ML work should run in a subprocess.

    Reads the env var lazily so tests can toggle the mode at runtime.
    """
    return os.environ.get(PROCESS_WORKER_ENV, "").strip().lower() == "process"


def get_worker_timeout() -> float:
    """Return the wall-clock timeout for a worker invocation."""
    raw = os.environ.get(WORKER_TIMEOUT_ENV, "").strip()
    if not raw:
        return DEFAULT_TIMEOUT_S
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "Invalid %s=%r, falling back to %ss",
            WORKER_TIMEOUT_ENV, raw, DEFAULT_TIMEOUT_S,
        )
        return DEFAULT_TIMEOUT_S


# ---------------------------------------------------------------------------
# Subprocess transport
# ---------------------------------------------------------------------------
def _project_root() -> Path:
    """Return the repo root (parent of ``app/``)."""
    return Path(__file__).resolve().parent.parent.parent


async def run_in_subprocess(task: Mapping[str, Any]) -> dict[str, Any]:
    """Run ``task`` in a fresh Python subprocess and return its result.

    Parameters
    ----------
    task:
        JSON-serialisable mapping. The worker reads it from stdin and
        writes a single JSON document to stdout: either
        ``{"ok": true, "result": ...}`` or ``{"ok": false, "error": "..."}``.

    Returns
    -------
    dict
        ``{"ok": True, "result": ...}`` on success, or
        ``{"ok": False, "error": "...", "stderr": "..."}`` on failure.
        The function NEVER raises — failures are surfaced through the
        ``ok`` flag so the caller can keep the API process alive.
    """
    root = _project_root()
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "app.worker_entrypoint",
        cwd=str(root),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    timeout_s = get_worker_timeout()
    try:
        payload = json.dumps(dict(task)).encode("utf-8")
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(payload), timeout=timeout_s
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            finally:
                await proc.wait()
            return {
                "ok": False,
                "error": f"ML worker timed out after {timeout_s}s",
                "stderr": "",
            }
    except Exception as exc:  # pragma: no cover - defensive
        try:
            proc.kill()
        finally:
            await proc.wait()
        return {
            "ok": False,
            "error": f"Failed to launch ML worker: {type(exc).__name__}: {exc}",
            "stderr": "",
        }

    if proc.returncode != 0:
        return {
            "ok": False,
            "error": (
                f"ML worker crashed (exit code {proc.returncode}). "
                "The API process is unaffected; the document was marked "
                "as failed. See worker stderr for details."
            ),
            "stderr": stderr.decode("utf-8", errors="replace")[:4000],
        }

    try:
        result = json.loads(stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "error": f"ML worker returned invalid JSON: {exc}",
            "stderr": stderr.decode("utf-8", errors="replace")[:2000],
        }

    if not isinstance(result, dict) or "ok" not in result:
        return {
            "ok": False,
            "error": f"ML worker returned unexpected payload: {result!r}",
        }
    return result


__all__ = [
    "PROCESS_WORKER_ENV",
    "WORKER_TIMEOUT_ENV",
    "DEFAULT_TIMEOUT_S",
    "is_process_worker_enabled",
    "get_worker_timeout",
    "run_in_subprocess",
]
