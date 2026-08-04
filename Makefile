# ============================================================================
# PetroQuery — developer convenience targets
# ============================================================================
# Run `make help` for a summary of available targets.
# ============================================================================

PYTHON ?= python3
VENV ?= venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip
PYTEST := $(VENV_BIN)/pytest
UVICORN := $(VENV_BIN)/uvicorn

# Dependency install strategy
#
#   requirements.txt          - cross-platform CPU-only safe deps (no torch,
#                               no CUDA). Use this as the minimum install.
#   requirements-ml.txt       - adds the optional ML stack on top of
#                               requirements.txt (torch, sentence-transformers,
#                               pdfplumber). Use this on Linux/Mac hosts that
#                               need to serve real RAG requests.
#   requirements-windows.txt  - the exact pinned set that the team uses on
#                               Windows + Python 3.12 (CPU wheels for torch,
#                               pyarrow pinned to a working version). Use
#                               this in place of requirements-ml.txt on
#                               Windows to avoid the access-violation
#                               crashes that come from a stale pyarrow wheel.
#   requirements-dev.txt      - pytest + pytest-asyncio, on top of
#                               requirements.txt.
#
# Default install uses requirements.txt only. CI does the same; the heavy
# ML stack is opt-in via the ``install-ml`` and ``install-windows`` targets
# below.
.PHONY: help install install-ml install-windows dev-install test test-fast \
        run-db init-db run run-ml-worker eval e2e clean

help:
	@echo "PetroQuery — make targets"
	@echo "  install         Create venv and install cross-platform deps (requirements.txt)"
	@echo "  install-ml      Also install the optional ML stack (Linux/Mac) on top of install"
	@echo "  install-windows Also install the pinned Windows ML set on top of install"
	@echo "  dev-install     Also install development/test dependencies"
	@echo "  test            Run the full test suite"
	@echo "  test-fast       Run the suite without slow markers"
	@echo "  run-db          Start the PostgreSQL + pgvector container"
	@echo "  init-db         Initialise the schema (requires running API or DB)"
	@echo "  run             Start the API on http://localhost:8000"
	@echo "  run-ml-worker   Start the API with PETROQUERY_ML_WORKER=process (subprocess isolation)"
	@echo "  e2e             Run scripts/e2e_smoke.py against a real PostgreSQL"
	@echo "  e2e-local       Run scripts/e2e_smoke_pgserver.py (spins up pgserver locally)"
	@echo "  eval            Run the O&G evaluation script (requires API up)"
	@echo "  clean           Remove __pycache__/, .pytest_cache/, build artefacts"

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-ml: install
	$(PIP) install -r requirements-ml.txt

install-windows: install
	$(PIP) install -r requirements-windows.txt

dev-install: install
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTEST)

test-fast:
	$(PYTEST) -m "not slow"

run-db:
	docker compose up -d db

init-db:
	$(VENV_BIN)/python scripts/init_petroquery_db.py

run:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

run-ml-worker:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

e2e:
	$(VENV_BIN)/python scripts/e2e_smoke.py

e2e-local:
	$(VENV_BIN)/python scripts/e2e_smoke_pgserver.py

eval:
	$(VENV_BIN)/python scripts/evaluate_petroquery.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage
