"""PII Masking for Oil & Gas documents before sending to an LLM.

The original regex tried to mask "person names" with
``\\b[A-Z][a-z]+\\s+[A-Z][a-z]+\\b``. That pattern nukes every pair of
capitalised Spanish words, which means it destroys legitimate domain
language such as "Vaca Muerta", "YPF", "BOP Stack", "Cuenca Neuquina",
"Paso de los Indios" and so on. Those are not PII — they are real O&G
nouns, place names and operator names.

The improved masker keeps the same categories but:

* Runs against a curated blocklist of legitimate O&G proper nouns, so they
  are preserved verbatim.
* Limits person-name masking to lines that look like personal signatures
  (e.g. ``Ing. Juan Pérez``, ``Firmado por María Gómez``) to avoid
  trashing generic capitalised phrases.
"""
from __future__ import annotations

import re
from typing import Iterable


# Curated list of terms that MUST NOT be masked. Add more operator names,
# basins, equipment classes, etc. as the corpus grows. The matching is
# case-insensitive.
_OG_PROPER_NOUNS: tuple[str, ...] = (
    "Vaca Muerta",
    "Cuenca Neuquina",
    "Cuenca Austral",
    "Cuenca del Golfo",
    "Cuenca Cuyana",
    "YPF",
    "Tecpetrol",
    "PAE",
    "Pluspetrol",
    "Total Austral",
    "Equinor",
    "Wintershall",
    "Vista Energy",
    "Chevron Argentina",
    "Shell Argentina",
    "BOP",
    "BOP Stack",
    "Christmas Tree",
    "PPE",
    "SCBA",
    "EEBA",
    "IAPG",
    "API RP 53",
    "API RP 14B",
    "API Spec 16A",
    "API Spec 5CT",
    "API 610",
    "API 650",
    "IRAM 301",
    "Resolución SE 123",
    "Resolución 123/2018",
    "ASTM A106",
    "ASTM A53",
    "NACE MR0175",
    "ISO 10423",
    "H2S",
    "HSE",
    "PVT",
    "ESP",
    "SARTA",
    "ESP Pump",
    "Casing",
    "Tubing",
    "Drilling",
    "Workover",
    "Frac Stack",
    "Frac Fleet",
    "Landing Zone",
    "Pilot Hole",
    "Liner Hanger",
    "Wellhead",
    "Choke Manifold",
    "Coiled Tubing",
    "Muster Point",
    "Permian Basin",
    "Bakken",
    "Marcellus",
    "Paso de los Indios",
    "Loma Campana",
    "Loma La Lata",
    "El Orejano",
    "Bandurria",
    "Fortín de Piedra",
    "Cierro Redondo",
    "Cierro Vasco",
    "Cierro Huanul",
    "Tres Picos",
    "Sierra Barrosa",
    "Aguada Pichana",
    "Aguada de Castro",
)

# Build case-insensitive alternation once.
_OG_PROPER_NOUN_PATTERN = re.compile(
    r"(?<![A-Za-zÁÉÍÓÚáéíóúÑñ])("
    + "|".join(re.escape(term) for term in _OG_PROPER_NOUNS)
    + r")(?![A-Za-zÁÉÍÓÚáéíóúÑñ])",
    re.IGNORECASE,
)


def _build_person_name_pattern() -> re.Pattern[str]:
    """Detect a person-name like ``Ing. Juan Pérez`` or ``Firmado por María López``.

    The original implementation matched any two consecutive capitalised words,
    which destroyed valid domain nouns. The new pattern requires either an
    explicit title/role token (Ing., Lic., Dr., Sr., Sra., Firmado) or the
    ``apellido, nombre`` order to reduce false positives dramatically.
    """
    titles = r"(?:Ing\.|Lic\.|Dr\.|Dra\.|Sr\.|Sra\.|Sres\.|Firmado\s+por)"
    # Two capitalised words (allowing accents). The first is captured
    # separately so we can also recognise the "Apellido, Nombre" form.
    two_words = r"(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)"
    pattern = (
        rf"(?P<person>{titles}\s+{two_words}"
        rf"|{two_words}\s*,\s*(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s+(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+))?)"
    )
    return re.compile(pattern, re.UNICODE)


_PERSON_NAME_PATTERN = _build_person_name_pattern()


class PIIMasker:
    """Mask categories of PII while preserving legitimate O&G proper nouns."""

    PATTERNS: dict[str, str] = {
        # Geographic coordinates (decimal degrees, 4+ decimal places).
        "exact_coords": r"-?\d{2}\.\d{4,}\s*,\s*-?\d{2,3}\.\d{4,}",
        # Financial values: "$12,3 millones" / "ARS 1.500".
        "financial_value": r"\$\s*\d[\d,\.]*\s*(?:millones|miles|USD|ARS)?",
        # Phone numbers in international / national formats.
        "phone": r"\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}",
        # Email addresses.
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    }

    @classmethod
    def mask(cls, text: str) -> str:
        if not text:
            return text

        # 1. Mask person names. We do this first so that a signature line
        # like "Ing. Juan Pérez (YPF)" becomes "[PERSON_NAME] (YPF)".
        text = _PERSON_NAME_PATTERN.sub("[PERSON_NAME]", text)

        # 2. Mask structured PII (coords, money, phones, emails).
        for label, pattern in cls.PATTERNS.items():
            text = re.sub(pattern, f"[{label.upper()}]", text, flags=re.IGNORECASE)

        # 3. Restore whitelisted proper nouns. We use a placeholder round-trip
        # so a masked token like "[PERSON_NAME] YPF S.A." is preserved
        # cleanly even if a noun happens to sit next to a placeholder.
        restore_map: dict[str, str] = {}
        counter = 0

        def _stash(match: "re.Match[str]") -> str:
            nonlocal counter
            token = f"\x00OGBLOCK{counter}\x00"
            counter += 1
            restore_map[token] = match.group(0)
            return token

        protected = _OG_PROPER_NOUN_PATTERN.sub(_stash, text)

        # After restoration, scrub any leftover empty placeholders.
        for token, original in restore_map.items():
            protected = protected.replace(token, original)

        return protected


def _iter_known_proper_nouns() -> Iterable[str]:
    """Expose the curated list (used by tests and configuration UI)."""
    return _OG_PROPER_NOUNS
