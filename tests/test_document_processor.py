"""Tests for the document processor's chunk helpers.

These tests intentionally avoid hitting pdfplumber, which requires
heavy optional dependencies. They focus on the pure-Python helpers
(extract_table_as_text, _detect_section, validate_and_merge_small_chunks).
"""
from __future__ import annotations

import pytest

from app.services.document_processor import (
    _detect_section,
    extract_table_as_text,
    extract_table_summary,
    validate_and_merge_small_chunks,
)


def test_detect_section_finds_capitulo():
    text = (
        "CAPÍTULO 4: PROCEDIMIENTOS DE PERFORACIÓN\n\n"
        "Este capítulo describe los pasos principales..."
    )
    assert _detect_section(text) == "CAPÍTULO 4: PROCEDIMIENTOS DE PERFORACIÓN"


def test_detect_section_finds_seccion():
    text = "SECCIÓN 2.3 — Equipos de superficie\nDetalle..."
    assert "SECCIÓN 2.3" in _detect_section(text)


def test_detect_section_returns_general_when_no_marker():
    assert _detect_section("texto sin marcadores") == "General"


def test_extract_table_as_text_marks_header():
    rows = [
        ["Parámetro", "Valor", "Unidad"],
        ["Presión", "3500", "psi"],
        ["Temperatura", "90", "°C"],
    ]
    text = extract_table_as_text(rows)
    assert "TABLA HEADER: Parámetro | Valor | Unidad" in text
    assert "Presión | 3500 | psi" in text
    assert "Temperatura | 90 | °C" in text


def test_extract_table_as_text_empty_input():
    assert extract_table_as_text([]) == ""
    assert extract_table_as_text([[]]) == ""


def test_extract_table_summary_contains_metadata():
    rows = [
        ["A", "B", "C", "D", "E"],
        ["1", "2", "3", "4", "5"],
        ["6", "7", "8", "9", "10"],
        ["11", "12", "13", "14", "15"],
    ]
    summary = extract_table_summary(rows)
    assert "A | B | C | D | E" in summary
    assert "Total filas" in summary
    assert "Total columnas: 5" in summary


def test_validate_and_merge_small_chunks_merges_tiny_chunk():
    chunks = [
        {"text": "A" * 100, "is_table": False, "table_summary": None},
        {"text": "tiny", "is_table": False, "table_summary": None},
    ]
    merged = validate_and_merge_small_chunks(chunks)
    assert len(merged) == 1
    assert "A" * 100 in merged[0]["text"]
    assert "tiny" in merged[0]["text"]


def test_validate_and_merge_small_chunks_keeps_large_chunks():
    chunks = [
        {"text": "A" * 200, "is_table": False, "table_summary": None},
        {"text": "B" * 200, "is_table": False, "table_summary": None},
    ]
    merged = validate_and_merge_small_chunks(chunks)
    assert len(merged) == 2


def test_validate_and_merge_small_chunks_splits_oversized():
    # Multiple paragraphs separated by \n\n so the splitter can break the
    # chunk at paragraph boundaries. The input is intentionally above
    # the 4000-char threshold.
    paragraphs = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 30,
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. " * 30,
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco. " * 30,
        "Duis aute irure dolor in reprehenderit in voluptate velit esse. " * 30,
        "Excepteur sint occaecat cupidatat non proident, sunt in culpa. " * 30,
    ]
    big = "\n\n".join(paragraphs)
    assert len(big) > 4000, "test fixture must exceed the split threshold"
    chunks = [{"text": big, "is_table": False, "table_summary": None}]
    final = validate_and_merge_small_chunks(chunks)
    assert len(final) > 1
    for chunk in final:
        assert len(chunk["text"]) <= 4000


def test_validate_and_merge_renumbers_chunks():
    chunks = [
        {"text": "A" * 100, "is_table": False, "table_summary": None},
        {"text": "B" * 100, "is_table": False, "table_summary": None},
        {"text": "C" * 100, "is_table": False, "table_summary": None},
    ]
    final = validate_and_merge_small_chunks(chunks)
    for i, chunk in enumerate(final, start=1):
        assert chunk["chunk_number"] == i
        assert chunk["total_chunks"] == len(final)


def test_validate_and_merge_empty_input():
    assert validate_and_merge_small_chunks([]) == []
