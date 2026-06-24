"""Tests for technical-number extraction and validation."""
from __future__ import annotations

import pytest

from app.services.number_validator import (
    extract_technical_numbers,
    validate_numbers_against_chunks,
)


def test_extracts_basic_pressure_value():
    text = "La presión de trabajo es 5000 psi en el BOP stack."
    numbers = extract_technical_numbers(text)
    assert any(n["value"] == "5000" and n["unit"] == "psi" for n in numbers)


def test_extracts_temperature():
    text = "La temperatura de fondo es 90 °C según el manual."
    numbers = extract_technical_numbers(text)
    assert any(n["value"] == "90" and n["unit"] == "°c" for n in numbers)


def test_does_not_match_substring_units():
    # 12 m is a real measurement, but the naive regex used to match the
    # digit-pair "12" inside the unrelated word "1200psi". The new matcher
    # should only return the legitimate "12 m" capture.
    text = "Bomba instalada a 12 m de profundidad, sistema a 1200 psi."
    numbers = extract_technical_numbers(text)
    unit_values = {(n["value"], n["unit"]) for n in numbers}
    assert ("12", "m") in unit_values
    # The pressure reading with a space is the real measurement.
    assert ("1200", "psi") in unit_values
    # The "1200 m" combination was the historical false positive: the unit
    # boundary guard now prevents capturing it when no "1200 m" exists.
    assert ("1200", "m") not in unit_values


def test_glued_unit_is_rejected():
    # "1200psi" with no space is too ambiguous (could be 1200 psi or
    # 1200-psi). The matcher must refuse to capture it because the unit
    # is glued to the digits. This is stricter than the legacy matcher
    # and avoids extracting junk measurements.
    text = "El sistema opera a 1200psi de presión máxima."
    numbers = extract_technical_numbers(text)
    unit_values = {(n["value"], n["unit"]) for n in numbers}
    assert ("1200", "psi") not in unit_values


def test_validate_when_chunk_contains_exact_value_and_unit():
    answer = "La presión es 3500 psi."
    chunk = "La presión máxima de operación es 3500 psi según el manual."
    result = validate_numbers_against_chunks(
        extract_technical_numbers(answer), [chunk]
    )
    assert result["all_verified"] is True
    assert result["verified_count"] == 1
    assert result["total_count"] == 1


def test_validate_rejects_substring_match():
    """A real bug from the previous implementation.

    Old code: ``"350" in chunk and "psi" in chunk.lower()`` would return
    True even when the chunk only mentioned "3500 psi". The new validator
    must not be fooled.
    """
    answer = "La presión es 350 psi."
    chunk = "El sistema está tarado a 3500 psi según API 16A."
    result = validate_numbers_against_chunks(
        extract_technical_numbers(answer), [chunk]
    )
    assert result["all_verified"] is False
    assert result["verified_count"] == 0
    assert result["total_count"] == 1


def test_validate_handles_decimal_comma_format():
    answer = "La densidad es 1,5 g/cm³."
    chunk = "La densidad típica del lodo es 1,5 g/cm³."
    result = validate_numbers_against_chunks(
        extract_technical_numbers(answer), [chunk]
    )
    assert result["all_verified"] is True


def test_validate_handles_unit_standalone_token():
    # The unit "psi" must be a standalone token, not glued to letters.
    answer = "La presión es 5000 psi."
    chunk = "Las siglas PSI hacen referencia al sistema métrico."  # no real value
    result = validate_numbers_against_chunks(
        extract_technical_numbers(answer), [chunk]
    )
    assert result["all_verified"] is False


def test_validate_no_numbers_in_answer():
    result = validate_numbers_against_chunks([], ["cualquier chunk"])
    assert result == {
        "all_verified": True,
        "details": [],
        "verified_count": 0,
        "total_count": 0,
    }


def test_validate_partial_match_reports_correct_count():
    answer = "Se observan 350 psi y 9999 bar."
    chunk_with_first = "El set point es 350 psi."
    # Second chunk intentionally lacks 9999 bar.
    chunk_without_second = "El sistema se mantuvo estable durante la prueba."
    result = validate_numbers_against_chunks(
        extract_technical_numbers(answer),
        [chunk_with_first, chunk_without_second],
    )
    assert result["all_verified"] is False
    assert result["verified_count"] == 1
    assert result["total_count"] == 2
