from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


TOP_K = 6
RRF_K = 80


async def hybrid_search(
    db: Optional[AsyncSession],
    query: str,
    query_embedding: list[float],
    user_id: int,
    chat_id: Optional[int] = None,
    top_k: int = TOP_K,
    k: int = RRF_K,
) -> list[dict]:
    if db is None:
        return []

    vector_limit = top_k * 3
    fts_limit = top_k * 3

    if chat_id is not None:
        vector_query = text("""
            SELECT id, title, content, cuenca, tipo_documento, tipo_equipo, normativa_aplicable,
                   1 - (embedding <=> cast(:embedding as vector)) as similarity
            FROM documents
            WHERE chat_id = :chat_id AND embedding IS NOT NULL
            ORDER BY embedding <=> cast(:embedding as vector)
            LIMIT :limit
        """)

        fts_query = text("""
            SELECT id, title, content, cuenca, tipo_documento, tipo_equipo, normativa_aplicable,
                   ts_rank(to_tsvector('spanish', content), plainto_tsquery('spanish', :query)) as rank
            FROM documents
            WHERE chat_id = :chat_id
              AND to_tsvector('spanish', content) @@ plainto_tsquery('spanish', :query)
            ORDER BY rank DESC
            LIMIT :limit
        """)

        vector_params = {"embedding": str(query_embedding), "chat_id": chat_id, "limit": vector_limit}
        fts_params = {"query": query, "chat_id": chat_id, "limit": fts_limit}
    else:
        vector_query = text("""
            SELECT id, title, content, cuenca, tipo_documento, tipo_equipo, normativa_aplicable,
                   1 - (embedding <=> cast(:embedding as vector)) as similarity
            FROM documents
            WHERE user_id = :user_id AND embedding IS NOT NULL
            ORDER BY embedding <=> cast(:embedding as vector)
            LIMIT :limit
        """)

        fts_query = text("""
            SELECT id, title, content, cuenca, tipo_documento, tipo_equipo, normativa_aplicable,
                   ts_rank(to_tsvector('spanish', content), plainto_tsquery('spanish', :query)) as rank
            FROM documents
            WHERE user_id = :user_id
              AND to_tsvector('spanish', content) @@ plainto_tsquery('spanish', :query)
            ORDER BY rank DESC
            LIMIT :limit
        """)

        vector_params = {"embedding": str(query_embedding), "user_id": user_id, "limit": vector_limit}
        fts_params = {"query": query, "user_id": user_id, "limit": fts_limit}

    vector_result = await db.execute(vector_query, vector_params)
    vector_rows = vector_result.fetchall()

    fts_result = await db.execute(fts_query, fts_params)
    fts_rows = fts_result.fetchall()

    max_vector_sim = max((float(row[7]) for row in vector_rows if row[7]), default=1.0)
    max_fts_rank = max((float(row[7]) for row in fts_rows if row[7]), default=1.0)

    vector_scores = {}
    for rank, row in enumerate(vector_rows, start=1):
        doc_id = row[0]
        similarity = float(row[7]) if row[7] else 0
        normalized_sim = similarity / max_vector_sim if max_vector_sim > 0 else 0
        vector_scores[doc_id] = {
            "id": doc_id,
            "title": row[1],
            "content": row[2],
            "cuenca": row[3],
            "tipo_documento": row[4],
            "tipo_equipo": row[5],
            "normativa_aplicable": row[6],
            "vector_score": normalized_sim,
        }

    fts_scores = {}
    for rank, row in enumerate(fts_rows, start=1):
        doc_id = row[0]
        rank_score = float(row[7]) if row[7] else 0
        normalized_rank = rank_score / max_fts_rank if max_fts_rank > 0 else 0
        fts_scores[doc_id] = {
            "id": doc_id,
            "title": row[1],
            "content": row[2],
            "cuenca": row[3],
            "tipo_documento": row[4],
            "tipo_equipo": row[5],
            "normativa_aplicable": row[6],
            "fts_score": normalized_rank,
        }

    all_doc_ids = set(vector_scores.keys()) | set(fts_scores.keys())

    rrf_scores = {}
    for doc_id in all_doc_ids:
        rrf_score = 0.0
        if doc_id in vector_scores:
            rank = list(vector_scores.keys()).index(doc_id) + 1
            rrf_score += (0.6 * k) / (k + rank)
        if doc_id in fts_scores:
            rank = list(fts_scores.keys()).index(doc_id) + 1
            rrf_score += (0.4 * k) / (k + rank)
        rrf_scores[doc_id] = rrf_score

    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    final_results = []
    for doc_id, rrf_score in sorted_docs[:top_k]:
        doc_info = vector_scores.get(doc_id) or fts_scores.get(doc_id)
        doc_info["rrf_score"] = rrf_score
        doc_info["vector_similarity"] = vector_scores.get(doc_id, {}).get("vector_score", 0)
        doc_info["fts_rank"] = fts_scores.get(doc_id, {}).get("fts_score", 0)
        final_results.append(doc_info)

    return final_results


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
    if db is None:
        return []

    vector_limit = top_k * 3
    fts_limit = top_k * 3

    # Build dynamic WHERE clauses for metadata filters
    filter_clauses = []
    filter_params: dict = {}
    if cuenca is not None:
        filter_clauses.append("cuenca = :cuenca")
        filter_params["cuenca"] = cuenca
    if tipo_documento is not None:
        filter_clauses.append("tipo_documento = :tipo_documento")
        filter_params["tipo_documento"] = tipo_documento
    if tipo_equipo is not None:
        filter_clauses.append("tipo_equipo = :tipo_equipo")
        filter_params["tipo_equipo"] = tipo_equipo
    if normativa_aplicable is not None:
        filter_clauses.append("normativa_aplicable = :normativa_aplicable")
        filter_params["normativa_aplicable"] = normativa_aplicable

    extra_where = " AND " + " AND ".join(filter_clauses) if filter_clauses else ""

    # Build base WHERE depending on project_id / chat_id / user_id
    if project_id is not None:
        if chat_id is not None:
            base_where = "project_id = :project_id AND chat_id = :chat_id"
            base_params = {"project_id": project_id, "chat_id": chat_id}
        else:
            base_where = "project_id = :project_id"
            base_params = {"project_id": project_id}
    elif chat_id is not None:
        base_where = "chat_id = :chat_id"
        base_params = {"chat_id": chat_id}
    else:
        base_where = "user_id = :user_id"
        base_params = {"user_id": user_id}

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

    vector_params = {**base_params, "embedding": str(query_embedding), "limit": vector_limit, **filter_params}
    fts_params = {**base_params, "query": query, "limit": fts_limit, **filter_params}

    vector_query = text(vector_sql)
    fts_query = text(fts_sql)

    vector_result = await db.execute(vector_query, vector_params)
    vector_rows = vector_result.fetchall()

    fts_result = await db.execute(fts_query, fts_params)
    fts_rows = fts_result.fetchall()

    max_vector_sim = max((float(row[7]) for row in vector_rows if row[7]), default=1.0)
    max_fts_rank = max((float(row[7]) for row in fts_rows if row[7]), default=1.0)

    vector_scores = {}
    for rank, row in enumerate(vector_rows, start=1):
        doc_id = row[0]
        similarity = float(row[7]) if row[7] else 0
        normalized_sim = similarity / max_vector_sim if max_vector_sim > 0 else 0
        vector_scores[doc_id] = {
            "id": doc_id,
            "title": row[1],
            "content": row[2],
            "cuenca": row[3],
            "tipo_documento": row[4],
            "tipo_equipo": row[5],
            "normativa_aplicable": row[6],
            "vector_score": normalized_sim,
        }

    fts_scores = {}
    for rank, row in enumerate(fts_rows, start=1):
        doc_id = row[0]
        rank_score = float(row[7]) if row[7] else 0
        normalized_rank = rank_score / max_fts_rank if max_fts_rank > 0 else 0
        fts_scores[doc_id] = {
            "id": doc_id,
            "title": row[1],
            "content": row[2],
            "cuenca": row[3],
            "tipo_documento": row[4],
            "tipo_equipo": row[5],
            "normativa_aplicable": row[6],
            "fts_score": normalized_rank,
        }

    all_doc_ids = set(vector_scores.keys()) | set(fts_scores.keys())

    rrf_scores = {}
    for doc_id in all_doc_ids:
        rrf_score = 0.0
        if doc_id in vector_scores:
            rank = list(vector_scores.keys()).index(doc_id) + 1
            rrf_score += (0.6 * k) / (k + rank)
        if doc_id in fts_scores:
            rank = list(fts_scores.keys()).index(doc_id) + 1
            rrf_score += (0.4 * k) / (k + rank)
        rrf_scores[doc_id] = rrf_score

    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    final_results = []
    for doc_id, rrf_score in sorted_docs[:top_k]:
        doc_info = vector_scores.get(doc_id) or fts_scores.get(doc_id)
        doc_info["rrf_score"] = rrf_score
        doc_info["vector_similarity"] = vector_scores.get(doc_id, {}).get("vector_score", 0)
        doc_info["fts_rank"] = fts_scores.get(doc_id, {}).get("fts_score", 0)
        final_results.append(doc_info)

    return final_results
