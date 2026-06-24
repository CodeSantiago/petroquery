"""RAG pipeline for PetroQuery.

This package contains the modular Retrieval-Augmented Generation
pipeline used by the chat router. The package is laid out as a
sequence of small, single-purpose stages so a reviewer can follow the
flow by reading the type signatures:

* :mod:`classification` - turn a question into a query type
* :mod:`retrieval`      - hybrid vector + FTS search with HSE boost
* :mod:`reranking`      - cross-encoder rerank + source assembly
* :mod:`generation`     - structured LLM call with HSE hard-stop
* :mod:`validation`     - number cross-check + human review flag
* :mod:`pipeline`       - orchestrator that runs the full chain

Each stage takes and returns one of the typed dataclasses defined in
:mod:`types`, which is what makes them individually testable.
"""
from app.services.rag.classification import classify_query
from app.services.rag.context import MAX_CONTEXT_CHARS, trim_context
from app.services.rag.generation import generate_answer
from app.services.rag.pipeline import NO_RESULTS_ANSWER_TEXT, run_rag_pipeline
from app.services.rag.reranking import RERANK_TOP_K, rerank_and_assemble
from app.services.rag.retrieval import retrieve
from app.services.rag.types import (
    AssembledContext,
    ClassifiedQuery,
    NumberValidation,
    RagRequest,
    RagResponse,
    RetrievedChunk,
    RetrievalResult,
)
from app.services.rag.validation import (
    NUMBER_MISMATCH_PENALTY,
    REVIEW_THRESHOLD,
    apply_validation_to_answer,
    finalize_answer,
    should_require_human_review,
    validate_answer_numbers,
)

__all__ = [
    # pipeline
    "run_rag_pipeline",
    "NO_RESULTS_ANSWER_TEXT",
    # stages
    "classify_query",
    "retrieve",
    "rerank_and_assemble",
    "generate_answer",
    "finalize_answer",
    # validation helpers
    "validate_answer_numbers",
    "apply_validation_to_answer",
    "should_require_human_review",
    # utilities
    "trim_context",
    "MAX_CONTEXT_CHARS",
    "RERANK_TOP_K",
    "REVIEW_THRESHOLD",
    "NUMBER_MISMATCH_PENALTY",
    # types
    "RagRequest",
    "RagResponse",
    "ClassifiedQuery",
    "RetrievedChunk",
    "RetrievalResult",
    "AssembledContext",
    "NumberValidation",
]
