"""Tests for the typed structures that flow through the RAG pipeline."""
from __future__ import annotations

import dataclasses

from app.schemas.og_schemas import OGTMetadata
from app.services.rag.types import (
    AssembledContext,
    ClassifiedQuery,
    NumberValidation,
    RagRequest,
    RetrievedChunk,
)


def test_rag_request_is_frozen():
    """RagRequest is frozen so callers cannot accidentally mutate it."""
    request = RagRequest(question="hola", user_id=1)
    # ``frozen=True`` dataclasses raise FrozenInstanceError on assignment.
    try:
        request.user_id = 99  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("RagRequest should be frozen")


def test_rag_request_holds_filters():
    filters = OGTMetadata(cuenca="Vaca Muerta", tipo_equipo="BOP")
    request = RagRequest(
        question="¿BOP?",
        user_id=1,
        project_id=2,
        chat_id=3,
        filters=filters,
    )
    assert request.user_id == 1
    assert request.project_id == 2
    assert request.chat_id == 3
    assert request.filters.cuenca == "Vaca Muerta"


def test_retrieved_chunk_round_trip_dict():
    chunk = RetrievedChunk(
        id=7,
        title="doc",
        content="texto",
        cuenca="Neuquina",
        tipo_documento="manual",
        vector_score=0.5,
        fts_rank=0.1,
        rrf_score=0.7,
        rerank_score=0.9,
    )
    as_dict = chunk.to_dict()
    assert as_dict["id"] == 7
    assert as_dict["cuenca"] == "Neuquina"
    assert as_dict["rerank_score"] == 0.9

    rebuilt = RetrievedChunk(**as_dict)
    assert rebuilt == chunk


def test_classified_query_round_trip():
    classified = ClassifiedQuery(question="hola", query_type="seguridad")
    assert classified.question == "hola"
    assert classified.query_type == "seguridad"


def test_number_validation_to_dict():
    validation = NumberValidation(
        total_count=2,
        verified_count=1,
        all_verified=False,
        details=[{"value": "12", "unit": "bar", "verified_in_source": True}],
    )
    out = validation.to_dict()
    assert out == {
        "all_verified": False,
        "verified_count": 1,
        "total_count": 2,
        "details": [{"value": "12", "unit": "bar", "verified_in_source": True}],
    }


def test_assembled_context_carries_sources_and_chunks():
    chunk = RetrievedChunk(id=1, title="t", content="c", rerank_score=0.5)
    from app.schemas.og_schemas import SourceReference
    source = SourceReference(
        documento="t",
        pagina=1,
        score_confianza=0.5,
        contenido_citado="c",
    )
    ctx = AssembledContext(context="c", sources=[source], chunks=[chunk])
    assert ctx.context == "c"
    assert ctx.sources[0].documento == "t"
    assert ctx.chunks[0] == chunk
