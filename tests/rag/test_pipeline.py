"""Tests for the RAG pipeline orchestrator.

These tests fake the heavy collaborators (AI service, hybrid search)
so we can verify the orchestration logic and the ``no-results`` short
circuit without touching the network or a real database.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.og_schemas import OGTechnicalAnswer
from app.services.rag import NO_RESULTS_ANSWER_TEXT, run_rag_pipeline
from app.services.rag.types import RagRequest


class _FakeAIService:
    def __init__(self, *, classification: str = "operacional") -> None:
        self.classification = classification

    async def classify_query_type(self, question: str) -> str:
        return self.classification

    async def generate_hypothetical_answer(self, question: str) -> str:
        return "Respuesta hipotética"

    async def get_query_embedding(self, text: str) -> list[float]:
        return [0.0] * 4

    async def rerank_chunks(self, query, chunks, top_k):
        # Mirror the real AI service contract: mutate the dicts in place
        # with a ``rerank_score`` and return the top_k.
        for c in chunks:
            c["rerank_score"] = 0.9
        return chunks[:top_k]

    async def ask_og_structured(
        self, *, context, question, history="", query_type="general"
    ):
        from app.schemas.og_schemas import OGTechnicalAnswer
        return OGTechnicalAnswer(
            respuesta_tecnica="Prueba a 5000 psi.",
            fuentes=[],
            score_global_confianza=0.9,
            necesita_revision_humana=False,
            tipo_consulta=query_type,
        )


class _FakeDB:
    """Minimal async DB stand-in. The pipeline only calls
    ``hybrid_search_filtered`` (patched away) and ``Document.extra_data``
    (also patched away), so we never need a real session.
    """

    async def execute(self, *args, **kwargs):  # pragma: no cover - never used
        raise AssertionError("FakeDB.execute should not be called in these tests")


def _install_fakes(monkeypatch, rows: list[dict]):
    """Patch the network/database collaborators used by the pipeline."""

    async def fake_hybrid_search(**kwargs):
        return list(rows)

    monkeypatch.setattr(
        "app.services.rag.retrieval.hybrid_search_filtered", fake_hybrid_search
    )

    async def fake_load_extra_data(*args, **kwargs):
        return {}

    monkeypatch.setattr(
        "app.services.rag.reranking._load_extra_data", fake_load_extra_data
    )


@pytest.mark.asyncio
async def test_pipeline_returns_no_results_answer_when_chunks_empty(
    monkeypatch,
):
    _install_fakes(monkeypatch, rows=[])
    ai = _FakeAIService(classification="operacional")
    request = RagRequest(question="¿Algo?", user_id=1)

    response = await run_rag_pipeline(
        db=_FakeDB(),  # type: ignore[arg-type]
        ai_service=ai,  # type: ignore[arg-type]
        request=request,
        history="",
    )
    assert response.answer.respuesta_tecnica == NO_RESULTS_ANSWER_TEXT
    assert response.answer.necesita_revision_humana is True
    assert response.answer.tipo_consulta == "operacional"
    assert response.chunks == []
    assert response.llm_time_ms == 0


@pytest.mark.asyncio
async def test_pipeline_threads_classified_query_type_to_generation(
    monkeypatch,
):
    chunk_row = {
        "id": 1,
        "title": "Manual BOP",
        "content": "El BOP se prueba a 5000 psi.",
        "cuenca": "Neuquina",
        "tipo_documento": "manual",
        "tipo_equipo": "BOP",
        "normativa_aplicable": "API 16A",
        "vector_score": 0.9,
        "fts_rank": 0.1,
        "rrf_score": 0.8,
    }
    _install_fakes(monkeypatch, rows=[chunk_row])
    ai = _FakeAIService(classification="equipos")
    request = RagRequest(question="¿BOP?", user_id=1)

    response = await run_rag_pipeline(
        db=_FakeDB(),  # type: ignore[arg-type]
        ai_service=ai,  # type: ignore[arg-type]
        request=request,
        history="",
    )
    # The classifier's decision must reach the generation stage.
    assert response.answer.tipo_consulta == "equipos"
    assert response.answer.respuesta_tecnica == "Prueba a 5000 psi."
    assert response.retrieval_time_ms >= 0
    assert response.llm_time_ms >= 0
    assert response.total_time_ms >= 0
    # The answer contains "5000 psi" so the number validator should
    # pick it up. The chunk also contains the same value, so the
    # validation should pass.
    assert response.validation is not None
    assert response.validation.all_verified is True
    assert len(response.chunks) == 1
