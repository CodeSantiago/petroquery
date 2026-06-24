"""Tests for the HSE protocol helpers."""
from __future__ import annotations

from app.services.hse_protocol import (
    boost_hse_documents,
    hse_hard_stop,
    is_hse_query,
)


def test_detects_h2s_query():
    assert is_hse_query("¿Qué hacer ante presencia de H2S?") is True


def test_detects_blowout_query():
    assert is_hse_query("Procedimiento ante un blowout en superficie") is True


def test_does_not_flag_purely_normative_query():
    assert (
        is_hse_query("¿Qué establece la Resolución SE 123/2018 sobre fractura?")
        is False
    )


def test_boost_promotes_hse_documents_to_top():
    results = [
        {
            "id": 1,
            "title": "Manual general",
            "tipo_documento": "manual",
            "normativa_aplicable": "API 16A",
            "rrf_score": 0.5,
        },
        {
            "id": 2,
            "title": "Manual de seguridad H2S",
            "tipo_documento": "manual",
            "normativa_aplicable": "IAPG H2S",
            "rrf_score": 0.4,
        },
    ]
    boosted = boost_hse_documents(results)
    assert boosted[0]["id"] == 2
    # HSE doc got a 1.5x boost; the other stays at the same score.
    assert boosted[0]["rrf_score"] > boosted[1]["rrf_score"]


def test_hse_hard_stop_sets_warning_for_safety_query():
    answer = {
        "tipo_consulta": "seguridad",
        "score_global_confianza": 0.4,
        "necesita_revision_humana": False,
    }
    fixed = hse_hard_stop(answer)
    assert fixed["necesita_revision_humana"] is True
    assert fixed["advertencia_seguridad"]


def test_hse_hard_stop_does_not_force_warning_for_non_safety_query():
    answer = {
        "tipo_consulta": "operacional",
        "score_global_confianza": 0.95,
        "necesita_revision_humana": False,
    }
    fixed = hse_hard_stop(answer)
    assert fixed["necesita_revision_humana"] is False
    assert "advertencia_seguridad" not in fixed
