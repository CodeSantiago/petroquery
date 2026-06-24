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

.PHONY: help install dev-install test test-fast run-db init-db run eval clean

help:
	@echo "PetroQuery — make targets"
	@echo "  install        Create venv and install runtime dependencies"
	@echo "  dev-install    Also install development/test dependencies"
	@echo "  test           Run the full test suite"
	@echo "  test-fast      Run the suite without slow markers"
	@echo "  run-db         Start the PostgreSQL + pgvector container"
	@echo "  init-db        Initialise the schema (requires running API or DB)"
	@echo "  run            Start the API on http://localhost:8000"
	@echo "  eval           Run the O&G evaluation script (requires API up)"
	@echo "  clean          Remove __pycache__/, .pytest_cache/, build artefacts"

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

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

eval:
	$(VENV_BIN)/python scripts/evaluate_petroquery.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage
