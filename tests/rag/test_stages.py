"""Unit tests for the RAG pipeline stages.

These tests focus on the contract of each stage in isolation. Heavy
collaborators (the AI service, the hybrid search, the database) are
replaced with lightweight fakes so we can pin down the data flow
without spinning up the full stack.
"""
from __future__ import annotations

import pytest

from app.schemas.og_schemas import OGTechnicalAnswer, OGTMetadata, SourceReference
from app.services.rag import (
    AssembledContext,
    ClassifiedQuery,
    NumberValidation,
    RetrievedChunk,
    REVIEW_THRESHOLD,
    classify_query,
    finalize_answer,
    generate_answer,
    rerank_and_assemble,
    retrieve,
    trim_context,
    should_require_human_review,
    apply_validation_to_answer,
)
from app.services.rag.context import MAX_CONTEXT_CHARS
from app.services.rag.reranking import RERANK_TOP_K, RerankConfig
from app.services.rag.types import RagRequest
from app.services.rag.validation import validate_answer_numbers


# ----------------------------------------------------------------------
# Fakes
# ----------------------------------------------------------------------
class _FakeAIService:
    """A stand-in for ``AIService`` covering the methods the stages use."""

    def __init__(
        self,
        *,
        classification: str = "operacional",
        hypothetical: str = "hipotética",
        reranked: list[dict] | None = None,
        structured: OGTechnicalAnswer | None = None,
    ) -> None:
        self.classification = classification
        self.hypothetical = hypothetical
        self.reranked = reranked
        self.structured = structured
        self.calls: list[tuple[str, dict]] = []

    async def classify_query_type(self, question: str) -> str:  # noqa: D401
        self.calls.append(("classify", {"question": question}))
        return self.classification

    async def generate_hypothetical_answer(self, question: str) -> str:
        self.calls.append(("hypo", {"question": question}))
        return self.hypothetical

    async def get_query_embedding(self, text: str) -> list[float]:
        self.calls.append(("embed", {"text": text}))
        return [0.0] * 4

    async def rerank_chunks(self, query: str, chunks: list[dict], top_k: int) -> list[dict]:
        self.calls.append(("rerank", {"query": query, "top_k": top_k}))
        if self.reranked is not None:
            return self.reranked
        # Default behaviour: mutate each chunk with a deterministic
        # score so the assembly stage can verify the data flow.
        scored = [
            {**chunk, "rerank_score": 1.0 - (0.1 * idx)}
            for idx, chunk in enumerate(chunks)
        ]
        return scored[:top_k]

    async def ask_og_structured(
        self,
        *,
        context: str,
        question: str,
        history: str = "",
        query_type: str = "general",
    ) -> OGTechnicalAnswer:
        self.calls.append(
            ("generate", {"query_type": query_type, "len_context": len(context)})
        )
        if self.structured is not None:
            return self.structured
        return OGTechnicalAnswer(
            respuesta_tecnica="Respuesta de prueba",
            fuentes=[],
            score_global_confianza=0.9,
            necesita_revision_humana=False,
            tipo_consulta=query_type,
        )


# ----------------------------------------------------------------------
# trim_context
# ----------------------------------------------------------------------
def test_trim_context_keeps_short_text_verbatim():
    assert trim_context("hola mundo") == "hola mundo"


def test_trim_context_breaks_on_paragraph_when_possible():
    text = ("a" * 100 + "\n\n" + "b" * 100)
    trimmed = trim_context(text, max_chars=120)
    # The paragraph break past the halfway mark (60) means we should
    # cut before the second paragraph.
    assert "a" * 100 in trimmed
    assert "b" not in trimmed


def test_trim_context_appends_marker_when_no_break_available():
    text = "x" * 5000
    trimmed = trim_context(text, max_chars=100)
    assert trimmed.endswith("[Contexto truncado...]")


# ----------------------------------------------------------------------
# Classification
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_classify_query_uses_hse_short_circuit():
    fake = _FakeAIService(classification="operacional")
    result = await classify_query(fake, "Procedimiento ante H2S en superficie")
    # HSE keyword wins, so we never call the LLM classifier.
    assert result.query_type == "seguridad"
    assert not any(call[0] == "classify" for call in fake.calls)


@pytest.mark.asyncio
async def test_classify_query_uses_llm_for_normal_questions():
    fake = _FakeAIService(classification="normativa")
    result = await classify_query(fake, "¿Qué dice la API 16A?")
    assert result.query_type == "normativa"
    assert any(call[0] == "classify" for call in fake.calls)


# ----------------------------------------------------------------------
# Number validation
# ----------------------------------------------------------------------
def _make_chunk(text: str, chunk_id: int = 1) -> RetrievedChunk:
    return RetrievedChunk(
        id=chunk_id,
        title="Manual",
        content=text,
        rerank_score=0.9,
    )


def test_validate_answer_numbers_returns_none_when_no_numbers():
    answer = OGTechnicalAnswer(
        respuesta_tecnica="Texto sin números técnicos relevantes.",
        fuentes=[],
        score_global_confianza=0.9,
        tipo_consulta="operacional",
    )
    assert validate_answer_numbers(answer, [_make_chunk("foo bar")]) is None


def test_validate_answer_numbers_detects_mismatches():
    answer = OGTechnicalAnswer(
        respuesta_tecnica="La presión de operación es 9999 bar.",
        fuentes=[],
        score_global_confianza=0.9,
        tipo_consulta="operacional",
    )
    validation = validate_answer_numbers(answer, [_make_chunk("Presión: 1500 psi")])
    assert validation is not None
    assert validation.total_count == 1
    assert validation.verified_count == 0
    assert validation.all_verified is False


def test_validate_answer_numbers_passes_when_value_present():
    answer = OGTechnicalAnswer(
        respuesta_tecnica="La presión de operación es 1500 psi.",
        fuentes=[],
        score_global_confianza=0.9,
        tipo_consulta="operacional",
    )
    validation = validate_answer_numbers(answer, [_make_chunk("Presión: 1500 psi")])
    assert validation is not None
    assert validation.all_verified is True
    assert validation.verified_count == 1


def test_apply_validation_lowers_score_on_mismatch():
    answer = OGTechnicalAnswer(
        respuesta_tecnica="x",
        fuentes=[],
        score_global_confianza=0.9,
        tipo_consulta="operacional",
    )
    validation = NumberValidation(
        total_count=1, verified_count=0, all_verified=False, details=[]
    )
    apply_validation_to_answer(answer, validation)
    assert answer.score_global_confianza < 0.9
    assert answer.necesita_revision_humana is True


def test_should_require_human_review_below_threshold():
    answer = OGTechnicalAnswer(
        respuesta_tecnica="x",
        fuentes=[],
        score_global_confianza=REVIEW_THRESHOLD - 0.1,
        tipo_consulta="operacional",
    )
    assert should_require_human_review(answer) is True


def test_should_require_human_review_always_for_safety():
    answer = OGTechnicalAnswer(
        respuesta_tecnica="x",
        fuentes=[],
        score_global_confianza=0.99,
        tipo_consulta="seguridad",
    )
    assert should_require_human_review(answer) is True


def test_finalize_answer_marks_safety_for_review_even_with_perfect_score():
    answer = OGTechnicalAnswer(
        respuesta_tecnica="Usar SCBA ante H2S.",
        fuentes=[],
        score_global_confianza=0.99,
        tipo_consulta="seguridad",
    )
    finalized, validation = finalize_answer(answer, [])
    assert finalized.necesita_revision_humana is True
    assert validation is None
