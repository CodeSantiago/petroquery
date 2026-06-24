"""Query classification.

This is the first stage of the RAG pipeline. It receives the user
question and produces a ``ClassifiedQuery`` that downstream stages use
to pick the right system prompt and to short-circuit safety checks.

The behaviour is intentionally identical to the inline logic that used
to live in ``chat.py``:

1. If the question matches any HSE keyword it is immediately classified
   as ``"seguridad"``. We do this BEFORE calling the LLM so safety
   critical queries do not have to wait for a network round-trip.
2. Otherwise the small classifier LLM is asked to choose one of the
   five known categories.
"""
from __future__ import annotations

from app.services.ai_service import AIService
from app.services.hse_protocol import is_hse_query
from app.services.rag.types import ClassifiedQuery


# Default query type when the classifier returns an unrecognised label.
DEFAULT_QUERY_TYPE = "general"


async def classify_query(ai_service: AIService, question: str) -> ClassifiedQuery:
    """Return the query type for ``question``.

    The returned ``ClassifiedQuery`` always carries the original
    question so the rest of the pipeline can use it without re-deriving
    it.
    """
    if is_hse_query(question):
        return ClassifiedQuery(question=question, query_type="seguridad")

    query_type = await ai_service.classify_query_type(question)
    return ClassifiedQuery(question=question, query_type=query_type)


__all__ = ["classify_query", "DEFAULT_QUERY_TYPE"]
