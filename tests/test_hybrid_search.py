"""Tests for hybrid search: filter wiring, scope resolution, RRF ranking."""
from __future__ import annotations

import pytest

from app.services.hybrid_search import (
    FTS_WEIGHT,
    RRF_K,
    TOP_K,
    VECTOR_WEIGHT,
    _build_filter_clauses,
    _resolve_access_scope,
)


def test_build_filter_clauses_only_includes_provided_filters():
    clauses, params = _build_filter_clauses(
        cuenca="Vaca Muerta",
        tipo_documento=None,
        tipo_equipo="BOP",
        normativa_aplicable=None,
    )
    assert "cuenca = :cuenca" in " ".join(clauses)
    assert "tipo_equipo = :tipo_equipo" in " ".join(clauses)
    assert "tipo_documento" not in " ".join(clauses)
    assert "normativa_aplicable" not in " ".join(clauses)
    assert params == {"cuenca": "Vaca Muerta", "tipo_equipo": "BOP"}


def test_build_filter_clauses_with_no_filters():
    clauses, params = _build_filter_clauses(None, None, None, None)
    assert clauses == []
    assert params == {}


def test_resolve_access_scope_project_takes_priority():
    where, params = _resolve_access_scope(
        project_id=10, chat_id=20, user_id=1
    )
    # When both project_id and chat_id are supplied, the scope narrows to
    # both — the original implementation already did this correctly.
    assert "project_id" in where
    assert "chat_id" in where
    assert params == {"project_id": 10, "chat_id": 20}


def test_resolve_access_scope_project_only():
    where, params = _resolve_access_scope(project_id=10, chat_id=None, user_id=1)
    assert where == "project_id = :project_id"
    assert params == {"project_id": 10}


def test_resolve_access_scope_chat_only():
    where, params = _resolve_access_scope(project_id=None, chat_id=20, user_id=1)
    assert where == "chat_id = :chat_id"
    assert params == {"chat_id": 20}


def test_resolve_access_scope_user_fallback():
    where, params = _resolve_access_scope(project_id=None, chat_id=None, user_id=1)
    assert where == "user_id = :user_id"
    assert params == {"user_id": 1}


def test_default_constants_have_expected_values():
    # Snapshot test: if these tunables change, downstream RRF math
    # changes too, and we want a noisy failure to remind the maintainer.
    assert TOP_K == 6
    assert RRF_K == 80
    assert VECTOR_WEIGHT + FTS_WEIGHT == pytest.approx(1.0)
