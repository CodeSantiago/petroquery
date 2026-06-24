"""Hybrid search (vector + FTS) with metadata filtering for PetroQuery.

The original module exposed two near-identical helpers, ``hybrid_search``
(legacy, no metadata filters) and ``hybrid_search_filtered`` (the
feature-complete version actually used by the chat pipeline). The legacy
helper was never called by any router, so it was removed to eliminate the
duplicated SQL string, normalisation, and RRF scoring code paths.

This module now exposes a single, well-documented public surface:

* :func:`hybrid_search_filtered` - the only public entrypoint. It accepts
  arbitrary metadata filters and chooses the right access scope
  (project > chat > user) automatically.
* :data:`TOP_K` and :data:`RRF_K` - shared tunables.

Reciprocal Rank Fusion (RRF) is used to combine vector and FTS rankings
with weights (0.6 / 0.4) calibrated to favour semantic similarity over
lexical matches — appropriate for technical manuals where synonyms and
paraphrases are common.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


TOP_K = 6
RRF_K = 80

# Weights for the two retrieval legs. Tuned for technical O&G manuals,
# where semantic similarity is more reliable than keyword overlap.
VECTOR_WEIGHT = 0.6
FTS_WEIGHT = 0.4


def _build_filter_clauses(
    cuenca: Optional[str],
    tipo_documento: Optional[str],
    tipo_equipo: Optional[str],
    normativa_aplicable: Optional[str],
) -> tuple[list[str], dict]:
    """Translate optional metadata filters into SQL WHERE fragments.

    Returns a tuple of (clauses, params) so the caller can splice the
    clauses into the vector and FTS templates without duplicating logic.
    """
    clauses: list[str] = []
    params: dict = {}
    if cuenca is not None:
        clauses.append("cuenca = :cuenca")
        params["cuenca"] = cuenca
    if tipo_documento is not None:
        clauses.append("tipo_documento = :tipo_documento")
        params["tipo_documento"] = tipo_documento
    if tipo_equipo is not None:
        clauses.append("tipo_equipo = :tipo_equipo")
        params["tipo_equipo"] = tipo_equipo
    if normativa_aplicable is not None:
        clauses.append("normativa_aplicable = :normativa_aplicable")
        params["normativa_aplicable"] = normativa_aplicable
    return clauses, params


def _resolve_access_scope(
    project_id: Optional[int],
    chat_id: Optional[int],
    user_id: int,
) -> tuple[str, dict]:
    """Pick the most restrictive scope available.

    Priority: ``project_id`` > ``chat_id`` > ``user_id``. This mirrors the
    legal access model: a project includes all its chats, a chat only its
    own messages, and the user fallback is the broadest tenant scope.
    """
    if project_id is not None:
        if chat_id is not None:
            return (
                "project_id = :project_id AND chat_id = :chat_id",
                {"project_id": project_id, "chat_id": chat_id},
            )
        return "project_id = :project_id", {"project_id": project_id}
    if chat_id is not None:
        return "chat_id = :chat_id", {"chat_id": chat_id}
    return "user_id = :user_id", {"user_id": user_id}


async def hybrid_search_filtered(
    db: Optional[AsyncSession],
    query: str,
    query_embedding: list[float],
    user_id: int,
    project_id: Optional[int] = None,
    cuenca: Optional[str] = None,
    tipo_documento: Optional[str] = None,
    tipo_equipo: Optional[str] = None,
    normativa_aplicable: Optional[str] = None,
    chat_id: Optional[int] = None,
    top_k: int = TOP_K,
    k: int = RRF_K,
) -> list[dict]:
    """Combine vector (pgvector) and full-text (Postgres FTS) rankings with RRF.

    Parameters mirror the call sites in ``app/api/v1/chat.py``. Optional
    metadata filters are AND-ed into the WHERE clause of both retrieval
    legs so the fused set stays consistent.
    """
    if db is None:
        return []

    vector_limit = top_k * 3
    fts_limit = top_k * 3

    filter_clauses, filter_params = _build_filter_clauses(
        cuenca, tipo_documento, tipo_equipo, normativa_aplicable
    )
    extra_where = (" AND " + " AND ".join(filter_clauses)) if filter_clauses else ""

    base_where, base_params = _resolve_access_scope(project_id, chat_id, user_id)

    vector_sql = f"""
        SELECT id, title, content, cuenca, tipo_documento, tipo_equipo, normativa_aplicable,
               1 - (embedding <=> cast(:embedding as vector)) as similarity
        FROM documents
        WHERE {base_where} AND embedding IS NOT NULL{extra_where}
        ORDER BY embedding <=> cast(:embedding as vector)
        LIMIT :limit
    """
    fts_sql = f"""
        SELECT id, title, content, cuenca, tipo_documento, tipo_equipo, normativa_aplicable,
               ts_rank(to_tsvector('spanish', content), plainto_tsquery('spanish', :query)) as rank
        FROM documents
        WHERE {base_where}
          AND to_tsvector('spanish', content) @@ plainto_tsquery('spanish', :query){extra_where}
        ORDER BY rank DESC
        LIMIT :limit
    """

    vector_params = {
        **base_params,
        "embedding": str(query_embedding),
        "limit": vector_limit,
        **filter_params,
    }
    fts_params = {
        **base_params,
        "query": query,
        "limit": fts_limit,
        **filter_params,
    }

    vector_result = await db.execute(text(vector_sql), vector_params)
    vector_rows = vector_result.fetchall()

    fts_result = await db.execute(text(fts_sql), fts_params)
    fts_rows = fts_result.fetchall()

    # Build per-leg score maps. We normalise each leg by its own max so
    # that the two signals are on the same scale before RRF.
    max_vector_sim = max(
        (float(row[7]) for row in vector_rows if row[7]), default=1.0
    ) or 1.0
    max_fts_rank = max(
        (float(row[7]) for row in fts_rows if row[7]), default=1.0
    ) or 1.0

    vector_scores: dict[int, dict] = {}
    for row in vector_rows:
        doc_id = row[0]
        similarity = float(row[7]) if row[7] else 0.0
        vector_scores[doc_id] = {
            "id": doc_id,
            "title": row[1],
            "content": row[2],
            "cuenca": row[3],
            "tipo_documento": row[4],
            "tipo_equipo": row[5],
            "normativa_aplicable": row[6],
            "vector_score": similarity / max_vector_sim,
        }

    fts_scores: dict[int, dict] = {}
    for row in fts_rows:
        doc_id = row[0]
        rank_score = float(row[7]) if row[7] else 0.0
        fts_scores[doc_id] = {
            "id": doc_id,
            "title": row[1],
            "content": row[2],
            "cuenca": row[3],
            "tipo_documento": row[4],
            "tipo_equipo": row[5],
            "normativa_aplicable": row[6],
            "fts_score": rank_score / max_fts_rank,
        }

    # RRF scoring: rank-based fusion that ignores absolute score magnitude.
    rrf_scores: dict[int, float] = {}
    for doc_id in set(vector_scores) | set(fts_scores):
        score = 0.0
        if doc_id in vector_scores:
            rank = list(vector_scores).index(doc_id) + 1
            score += (VECTOR_WEIGHT * k) / (k + rank)
        if doc_id in fts_scores:
            rank = list(fts_scores).index(doc_id) + 1
            score += (FTS_WEIGHT * k) / (k + rank)
        rrf_scores[doc_id] = score

    sorted_docs = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)

    final_results: list[dict] = []
    for doc_id, rrf_score in sorted_docs[:top_k]:
        doc_info = vector_scores.get(doc_id) or fts_scores.get(doc_id)
        # doc_info is guaranteed to be present here, but keep a defensive
        # fallback for the type checker.
        if doc_info is None:
            continue
        doc_info["rrf_score"] = rrf_score
        doc_info["vector_similarity"] = vector_scores.get(doc_id, {}).get(
            "vector_score", 0.0
        )
        doc_info["fts_rank"] = fts_scores.get(doc_id, {}).get("fts_score", 0.0)
        final_results.append(doc_info)

    return final_results
