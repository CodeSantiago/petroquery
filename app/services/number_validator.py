"""Cross-validation of technical numbers against source chunks.

The original implementation used naive substring matching, which produced
false positives when an answer mentioned, for example, ``12`` and the
context happened to contain ``1200`` in a totally different unit. The
implementation below anchors the value on a word boundary and requires the
unit token to appear as a standalone token (not glued to digits, letters or
other punctuation that would form a different compound).
"""
from __future__ import annotations

import re
from typing import Iterable


# Units are grouped so we can build a single, case-insensitive alternation.
_UNIT_PATTERNS: list[str] = [
    # Pressure
    r"bar", r"psi", r"kpa", r"mpa", r"atm",
    # Temperature
    r"°c", r"°f",
    # Length
    r"m", r"ft", r"km",
    # Density
    r"ppg", r"g/cm3", r"g/cm³", r"kg/m3", r"kg/m³",
    # Concentration
    r"ppm", r"ppb", r"%",
    # Volume / rate (handy extras used across O&G manuals)
    r"bbl", r"bpd", r"m3/d", r"m³/d", r"gpm", r"l/min", r"l/min",
]

_UNIT_ALT = "|".join(_UNIT_PATTERNS)
_VALUE_GROUP = r"(\d+(?:[.,]\d+)?)"

# A unit must be a standalone token: not glued to another digit, word char
# or "°" sign that would form a different number. We allow optional
# whitespace between the value and the unit so the matcher works for
# inputs like "12 bar" or "12bar".
_UNIT_BOUNDARY = (
    r"(?<![A-Za-z0-9_°])"  # not preceded by another token character
    r"(?P<unit>" + _UNIT_ALT + r")"
    r"(?![A-Za-z0-9_])"  # not followed by another token character
)

_NUMBER_PATTERN = re.compile(
    rf"{_VALUE_GROUP}\s*{_UNIT_BOUNDARY}",
    re.IGNORECASE | re.UNICODE,
)


def extract_technical_numbers(text: str) -> list[dict]:
    """Extract numbers with technical units from a free-form string.

    The matcher is intentionally conservative: it only captures tokens that
    look like a real engineering measurement (digits followed by a known
    unit token), and avoids matching things like "1" in "100 psi" or
    "12" in "1200psi" because of the word-boundary guard around the unit.
    """
    if not text:
        return []

    numbers: list[dict] = []
    for match in _NUMBER_PATTERN.finditer(text):
        raw_value = match.group(1)
        # Keep the original decimal separator so callers can reason about
        # the form actually used in the source. Validation handles the
        # dot/comma equivalence explicitly.
        unit = (match.group("unit") or "").lower()
        numbers.append(
            {
                "value": raw_value,
                "unit": unit,
                "context": text[max(0, match.start() - 20):match.end() + 20],
            }
        )
    return numbers


def _value_variants(value: str) -> Iterable[str]:
    """Yield the textual variants in which a numeric value may appear.

    For example, ``12`` is also written as ``12.0`` in the same source.
    ``1.5`` may also appear as ``1,5`` in Spanish documents.
    """
    yield value
    if "." in value:
        # Allow comma-form for European Spanish decimals.
        yield value.replace(".", ",")
    if "," in value:
        yield value.replace(",", ".")
    if value.isdigit():
        # Allow the trailing-zero form some manuals use.
        yield f"{value}.0"
    return


def _contains_value_and_unit(chunk: str, value: str, unit: str) -> bool:
    """Return True when the chunk actually contains the (value, unit) pair.

    We require the unit to appear as a standalone token, otherwise the
    substring "12 ppm" would match a chunk that only mentions "1200 ppm",
    and the substring "12 m" would match "120 m" — both classic substring
    false positives.
    """
    chunk_lower = chunk.lower()
    unit_pattern = re.compile(
        r"(?<![A-Za-z0-9_°])" + re.escape(unit) + r"(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )
    if not unit_pattern.search(chunk_lower):
        return False

    for variant in _value_variants(value):
        # Word boundary on each side of the value avoids matching "12" inside
        # "120", "1234" or "1.2.3".
        value_pattern = re.compile(
            rf"(?<![0-9.,]){re.escape(variant)}(?![0-9])",
        )
        if value_pattern.search(chunk):
            return True
    return False


def validate_numbers_against_chunks(
    answer_numbers: list[dict], chunks: list[str]
) -> dict:
    """Check each (value, unit) pair extracted from the answer against the
    supplied context chunks.
    """
    if not answer_numbers:
        return {
            "all_verified": True,
            "details": [],
            "verified_count": 0,
            "total_count": 0,
        }

    validations: list[dict] = []
    for num in answer_numbers:
        found = any(
            _contains_value_and_unit(chunk, num["value"], num["unit"])
            for chunk in chunks
        )
        validations.append({**num, "verified_in_source": found})

    verified = sum(1 for v in validations if v["verified_in_source"])
    return {
        "all_verified": verified == len(validations),
        "details": validations,
        "verified_count": verified,
        "total_count": len(validations),
    }
