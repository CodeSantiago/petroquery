"""Real PostgreSQL harness for the E2E smoke test.

The project's ``scripts/e2e_smoke.py`` is designed to run against a
live PostgreSQL instance (typically the one started by
``docker compose up -d db``). On hosts where Docker is not available
or not running, this script falls back to :mod:`pgserver`, a portable
real PostgreSQL binary that ships with the pgvector extension. The
fallback exists so the smoke test is still runnable in developer
sandboxes, CI runners without Docker, and clean laptops.

The script is intentionally simple: it starts a PostgreSQL on a
free port, exports ``DATABASE_URL`` so the API picks it up, runs the
existing ``scripts/e2e_smoke.py``, and tears the database down. No
volumes or external data are touched.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
E2E_SMOKE = REPO_ROOT / "scripts" / "e2e_smoke.py"


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        try:
            sock.connect(("127.0.0.1", port))
        except OSError:
            return False
        return True


def _wait_for_http(url: str, timeout_s: float = 60.0) -> None:
    """Poll the health endpoint until the API responds or the timeout hits."""
    import httpx

    deadline = time.time() + timeout_s
    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                return
        except Exception as exc:  # noqa: BLE001 - we just retry
            last_exc = exc
        time.sleep(0.5)
    raise RuntimeError(
        f"API did not become healthy within {timeout_s}s ({url}); last error: {last_exc}"
    )


def start_local_pg() -> tuple[str, object]:
    """Start a real PostgreSQL via ``pgserver`` and return the DSN.

    The returned object has a ``.cleanup()`` method the caller MUST
    invoke when done.
    """
    import pgserver  # local-only dependency for the harness

    root = Path(tempfile.gettempdir()) / "pq_e2e_harness"
    root.mkdir(parents=True, exist_ok=True)
    server = pgserver.get_server(str(root))
    uri = server.get_uri()
    # Sanity-check the connection so the API does not start against a
    # database that is still warming up.
    server.psql("SELECT 1;")
    # Convert the URI from the sync libpq form (postgresql://user:pass@host:port/db)
    # into the asyncpg form the API expects.
    assert uri.startswith("postgresql://"), uri
    async_dsn = "postgresql+asyncpg://" + uri[len("postgresql://"):]
    return async_dsn, server


def run_api(database_url: str, host: str = "127.0.0.1", port: int = 8000) -> subprocess.Popen:
    """Launch uvicorn in a subprocess and return the handle."""
    env = os.environ.copy()
    env["APP_ENV"] = "development"
    env["DATABASE_URL"] = database_url
    env["SECRET_KEY"] = env.get("SECRET_KEY") or "harness-only-secret-not-for-prod"
    env["RATE_LIMIT_ENABLED"] = "false"  # the smoke does not exercise rate-limit
    env["AUTH_COOKIE_SECURE"] = "false"
    env["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000"
    # ``app.main`` prints ✅ / ❌ to stdout during startup. On a Windows
    # host the default console encoding is cp1252, which makes the
    # print() raise UnicodeEncodeError and aborts the FastAPI lifespan.
    # The harness forces UTF-8 here so the smoke can run end-to-end on
    # the same Windows developer machines the rest of the project
    # already targets.
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    # Ensure the API does not try to load the heavy ML stack for this
    # smoke run — the request path does not touch it.
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    return subprocess.Popen(cmd, cwd=str(REPO_ROOT), env=env)


def main() -> int:
    if _port_in_use(8000):
        print("port 8000 already in use; refusing to run the harness.")
        return 2

    print("[harness] starting local PostgreSQL via pgserver...")
    dsn, server = start_local_pg()
    print(f"[harness] PostgreSQL ready: {dsn}")

    print("[harness] launching uvicorn against the local DB...")
    api = run_api(dsn)
    try:
        try:
            _wait_for_http("http://127.0.0.1:8000/health", timeout_s=60.0)
        except Exception as exc:
            print(f"[harness] API never became healthy: {exc}")
            return 3

        print("[harness] running scripts/e2e_smoke.py against the live API...")
        result = subprocess.run(
            [sys.executable, str(E2E_SMOKE)],
            cwd=str(REPO_ROOT),
            env={
                **os.environ,
                "PETROQUERY_API_URL": "http://127.0.0.1:8000",
            },
        )
        return result.returncode
    finally:
        print("[harness] stopping uvicorn...")
        api.terminate()
        try:
            api.wait(timeout=10)
        except subprocess.TimeoutExpired:
            api.kill()
            api.wait()
        print("[harness] cleaning up PostgreSQL...")
        try:
            server.cleanup()
        except Exception as exc:  # noqa: BLE001 - cleanup is best-effort
            print(f"[harness] (cleanup warning) {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
