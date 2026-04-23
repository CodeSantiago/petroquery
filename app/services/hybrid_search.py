from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


TOP_K = 10
RRF_K = 60


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
    
    from pgvector.sqlalchemy import Vector
    
    # Filtrar por chat_id si se proporciona, sino por user_id
    if chat_id is not None:
        vector_query = text("""
            SELECT id, title, content,
                   1 - (embedding <=> cast(:embedding as vector)) as similarity
            FROM documents
            WHERE chat_id = :chat_id AND embedding IS NOT NULL
            ORDER BY embedding <=> cast(:embedding as vector)
            LIMIT :limit
        """)
        
        fts_query = text("""
            SELECT id, title, content,
                   ts_rank(to_tsvector('spanish', content), plainto_tsquery('spanish', :query)) as rank
            FROM documents
            WHERE chat_id = :chat_id 
              AND to_tsvector('spanish', content) @@ plainto_tsquery('spanish', :query)
            ORDER BY rank DESC
            LIMIT :limit
        """)
        
        vector_params = {"embedding": str(query_embedding), "chat_id": chat_id, "limit": top_k * 2}
        fts_params = {"query": query, "chat_id": chat_id, "limit": top_k * 2}
    else:
        vector_query = text("""
            SELECT id, title, content,
                   1 - (embedding <=> cast(:embedding as vector)) as similarity
            FROM documents
            WHERE user_id = :user_id AND embedding IS NOT NULL
            ORDER BY embedding <=> cast(:embedding as vector)
            LIMIT :limit
        """)
        
        fts_query = text("""
            SELECT id, title, content,
                   ts_rank(to_tsvector('spanish', content), plainto_tsquery('spanish', :query)) as rank
            FROM documents
            WHERE user_id = :user_id 
              AND to_tsvector('spanish', content) @@ plainto_tsquery('spanish', :query)
            ORDER BY rank DESC
            LIMIT :limit
        """)
        
        vector_params = {"embedding": str(query_embedding), "user_id": user_id, "limit": top_k * 2}
        fts_params = {"query": query, "user_id": user_id, "limit": top_k * 2}
    
    vector_result = await db.execute(
        vector_query,
        vector_params
    )
    vector_rows = vector_result.fetchall()
    
    fts_result = await db.execute(
        fts_query,
        fts_params
    )
    fts_rows = fts_result.fetchall()
    
    vector_scores = {}
    for rank, row in enumerate(vector_rows, start=1):
        doc_id = row[0]
        similarity = float(row[3]) if row[3] else 0
        vector_scores[doc_id] = {
            "id": doc_id,
            "title": row[1],
            "content": row[2],
            "vector_score": similarity,
        }
    
    fts_scores = {}
    for rank, row in enumerate(fts_rows, start=1):
        doc_id = row[0]
        rank_score = float(row[3]) if row[3] else 0
        fts_scores[doc_id] = {
            "id": doc_id,
            "title": row[1],
            "content": row[2],
            "fts_score": rank_score,
        }
    
    all_doc_ids = set(vector_scores.keys()) | set(fts_scores.keys())
    
    rrf_scores = {}
    for doc_id in all_doc_ids:
        rrf_score = 0.0
        
        if doc_id in vector_scores:
            rank = list(vector_scores.keys()).index(doc_id) + 1
            rrf_score += k / (k + rank)
        
        if doc_id in fts_scores:
            rank = list(fts_scores.keys()).index(doc_id) + 1
            rrf_score += k / (k + rank)
        
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