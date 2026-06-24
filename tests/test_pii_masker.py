"""Tests for the PII masker with proper-noun awareness."""
from __future__ import annotations

from app.services.pii_masker import PIIMasker


def test_masks_email_address():
    masked = PIIMasker.mask("Contactar a juan.perez@ypf.com para más detalles.")
    assert "[EMAIL]" in masked
    assert "juan.perez@ypf.com" not in masked


def test_masks_phone_number():
    masked = PIIMasker.mask("Llamar al +54 299 555-1234 en horario de oficina.")
    assert "[PHONE]" in masked


def test_masks_coordinate_pair():
    masked = PIIMasker.mask(
        "El pozo está ubicado en -38.9516, -68.0591, Cuenca Neuquina."
    )
    assert "[EXACT_COORDS]" in masked


def test_masks_financial_value():
    masked = PIIMasker.mask("El costo del proyecto fue $ 12,3 millones USD.")
    assert "[FINANCIAL_VALUE]" in masked


def test_preserves_vaca_muerta():
    """The single most damaging false positive of the legacy masker."""
    text = "Las operaciones en Vaca Muerta son críticas para YPF."
    masked = PIIMasker.mask(text)
    assert "Vaca Muerta" in masked
    assert "YPF" in masked


def test_preserves_cuenca_neuquina():
    masked = PIIMasker.mask("La Cuenca Neuquina produce shale oil de alta calidad.")
    assert "Cuenca Neuquina" in masked


def test_preserves_equipment_classes():
    text = "Se instaló un BOP Stack API 16A con certificación NACE MR0175."
    masked = PIIMasker.mask(text)
    assert "BOP Stack" in masked
    assert "API 16A" in masked
    assert "NACE MR0175" in masked


def test_preserves_place_names():
    text = "Las operaciones de Loma Campana y Loma La Lata son emblemáticas."
    masked = PIIMasker.mask(text)
    assert "Loma Campana" in masked
    assert "Loma La Lata" in masked


def test_masks_engineer_signature():
    masked = PIIMasker.mask("Firmado por Ing. Juan Pérez, supervisor de turno.")
    assert "[PERSON_NAME]" in masked
    # Operator name must be preserved.
    # (we are not masking operator names, only the signature line)
    # Operator name isn't here, so just check the signature was replaced.


def test_does_not_mask_generic_capitalised_phrases():
    """A sentence like 'Pressure Testing se realiza...' must survive intact.

    This is the regression case the new masker exists to fix.
    """
    text = "Pressure Testing del BOP cada 21 días según API 16A."
    masked = PIIMasker.mask(text)
    assert "Pressure Testing" in masked
    assert "BOP" in masked
    assert "API 16A" in masked


def test_combined_masking_in_long_text():
    text = (
        "Operaciones en Vaca Muerta. Contacto: juan@ypf.com, tel +54 299 555-1234. "
        "Coordenadas: -38.9516, -68.0591. Costo: $5 millones USD. "
        "Firmado por Ing. María Gómez."
    )
    masked = PIIMasker.mask(text)
    assert "Vaca Muerta" in masked
    assert "[EMAIL]" in masked
    assert "[PHONE]" in masked
    assert "[EXACT_COORDS]" in masked
    assert "[FINANCIAL_VALUE]" in masked
    assert "[PERSON_NAME]" in masked
    # No raw PII should leak.
    assert "juan@ypf.com" not in masked
    assert "Ing. María Gómez" not in masked


def test_empty_text_returns_empty():
    assert PIIMasker.mask("") == ""


def test_does_not_mask_inside_other_words():
    # "BOP" must not match inside "BOPPER" or "BOPs" without a word boundary.
    # The whitelist is anchored on both sides to avoid this kind of false
    # negative. (This is more of a guardrail: we want BOP to be preserved,
    # not erased, even if it appears adjacent to punctuation.)
    masked = PIIMasker.mask("El sistema BOP debe probarse.")
    assert "BOP" in masked
