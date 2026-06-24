"""Shared typed structures passed between RAG pipeline stages.

The pipeline is intentionally broken into small, single-purpose stages
(``classify`` -> ``retrieve`` -> ``rerank`` -> ``assemble`` -> ``generate`` ->
``validate``). Each stage accepts and returns one of the dataclasses
declared here so we can test the stages in isolation and so a reviewer can
follow the RAG flow by reading the type signatures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.schemas.og_schemas import OGTechnicalAnswer, OGTMetadata, SourceReference


# ----------------------------------------------------------------------
# Inputs
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class RagRequest:
    """The immutable inputs for a single RAG pipeline run.

    Keeping this frozen prevents downstream stages from accidentally
    mutating the caller's request and makes the data flow explicit.
    """

    question: str
    user_id: int
    project_id: Optional[int] = None
    chat_id: Optional[int] = None
    filters: OGTMetadata = field(default_factory=OGTMetadata)


# ----------------------------------------------------------------------
# Pipeline stage artifacts
# ----------------------------------------------------------------------
@dataclass
class ClassifiedQuery:
    """The outcome of the classification stage."""

    question: str
    query_type: str  # "operacional" | "normativa" | "seguridad" | "equipos" | "general"


@dataclass
class RetrievedChunk:
    """A document chunk produced by the retrieval stage.

    This is the only shape that downstream stages should depend on. The
    raw SQL row from the hybrid search is normalised into this dataclass
    right after the database query so the rest of the pipeline is
    decoupled from the row layout.
    """

    id: int
    title: str
    content: str
    cuenca: Optional[str] = None
    tipo_documento: Optional[str] = None
    tipo_equipo: Optional[str] = None
    normativa_aplicable: Optional[str] = None
    vector_score: float = 0.0
    fts_rank: float = 0.0
    rrf_score: float = 0.0
    rerank_score: float = 0.0

    def to_dict(self) -> dict:
        """Render the chunk as a plain dict for the AI service and audit log."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "cuenca": self.cuenca,
            "tipo_documento": self.tipo_documento,
            "tipo_equipo": self.tipo_equipo,
            "normativa_aplicable": self.normativa_aplicable,
            "vector_score": self.vector_score,
            "fts_rank": self.fts_rank,
            "rrf_score": self.rrf_score,
            "rerank_score": self.rerank_score,
        }


@dataclass
class RetrievalResult:
    """Chunks + diagnostics returned by the retrieval stage."""

    chunks: list[RetrievedChunk]
    retrieval_time_ms: int = 0


@dataclass
class AssembledContext:
    """The trimmed context string and the sources that produced it.

    The sources are kept alongside the context because the generation
    stage may need to fall back to them when the LLM returns an empty
    ``fuentes`` list.
    """

    context: str
    sources: list[SourceReference]
    chunks: list[RetrievedChunk]


@dataclass
class NumberValidation:
    """Result of cross-checking answer numbers against the source chunks."""

    total_count: int
    verified_count: int
    all_verified: bool
    details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "all_verified": self.all_verified,
            "verified_count": self.verified_count,
            "total_count": self.total_count,
            "details": self.details,
        }


@dataclass
class RagResponse:
    """The final, audited response that the pipeline returns to the router."""

    answer: OGTechnicalAnswer
    context: str
    chunks: list[RetrievedChunk]
    validation: Optional[NumberValidation] = None
    retrieval_time_ms: int = 0
    llm_time_ms: int = 0
    total_time_ms: int = 0


__all__ = [
    "RagRequest",
    "ClassifiedQuery",
    "RetrievedChunk",
    "RetrievalResult",
    "AssembledContext",
    "NumberValidation",
    "RagResponse",
]
