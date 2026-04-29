#!/usr/bin/env python3
"""
PetroQuery Evaluation Script
============================
Evaluates the PetroQuery RAG system against an O&G specialized dataset.

Metrics
-------
- Faithfulness       : LLM-as-judge via Groq (does answer stick to context?)
- Answer Accuracy    : Embedding cosine similarity (answer vs ground_truth)
- Citation Precision : Fraction of cited documents that exist in the DB
- Context Precision  : Best semantic similarity between retrieved chunks and ground_truth
- Structure Heuristics:
    * has_respuesta_tecnica
    * fuentes_non_empty (when chunks were retrieved)
    * score_in_range [0,1]
    * revision_flag_correct

Environment
-----------
    export PETROQUERY_API_URL=http://localhost:8000
    export EVAL_USERNAME=evaluator
    export EVAL_PASSWORD=evaluator123
    export EVAL_EMAIL=evaluator@petroquery.local

Run
---
    python scripts/evaluate_petroquery.py
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import sys
from datetime import datetime
from typing import Any

import httpx

# Allow imports from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import groq
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import engine
from app.models import Document
from app.services.ai_service import get_ai_service

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("PETROQUERY_API_URL", "http://localhost:8000")
EVAL_USERNAME = os.getenv("EVAL_USERNAME", "evaluator")
EVAL_PASSWORD = os.getenv("EVAL_PASSWORD", "evaluator123")
EVAL_EMAIL = os.getenv("EVAL_EMAIL", "evaluator@petroquery.local")

DATASET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "eval",
    "og_eval_dataset.json",
)

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "eval")

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BASE_URL, timeout=120.0)


async def ensure_user() -> None:
    """Register the eval user if it does not exist, then confirm login works."""
    async with _client() as client:
        # Try login first
        try:
            r = await client.post(
                "/api/v1/auth/login",
                data={"username": EVAL_USERNAME, "password": EVAL_PASSWORD},
            )
            if r.status_code == 200:
                return
        except Exception:
            pass

        # Attempt registration
        try:
            r = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": EVAL_EMAIL,
                    "username": EVAL_USERNAME,
                    "password": EVAL_PASSWORD,
                    "full_name": "PetroQuery Evaluator",
                },
            )
            if r.status_code in (200, 201):
                print(f"[SETUP] Registered eval user: {EVAL_USERNAME}")
                return
        except Exception as exc:
            print(f"[WARN] Could not register eval user: {exc}")

    raise RuntimeError(
        f"Unable to authenticate as '{EVAL_USERNAME}'. "
        "Please create the user manually or verify that the API is running."
    )


async def get_token() -> str:
    async with _client() as client:
        r = await client.post(
            "/api/v1/auth/login",
            data={"username": EVAL_USERNAME, "password": EVAL_PASSWORD},
        )
        r.raise_for_status()
        return r.json()["access_token"]


async def ask_question(token: str, question: str, project_id: int = 1) -> dict[str, Any]:
    async with _client() as client:
        r = await client.post(
            "/api/v1/ask",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": question, "project_id": project_id},
        )
        r.raise_for_status()
        return r.json()


async def ask_question_with_retry(
    token: str, question: str, project_id: int = 1, max_retries: int = 3, base_delay: float = 5.0
) -> dict[str, Any]:
    """Ask with exponential backoff retry on 500 errors (embedding model reload)."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            return await ask_question(token, question, project_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 500 and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"    [RETRY] 500 error, reintentando en {delay:.0f}s (intento {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                continue
            raise
        except httpx.TransportError as exc:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"    [RETRY] Connection error, reintentando en {delay:.0f}s (intento {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                continue
            raise
    raise last_exc


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

async def compute_faithfulness(
    answer: str, contexts: list[str], groq_client: groq.AsyncGroq
) -> float:
    """LLM-as-judge: does the answer stick strictly to the retrieved context?"""
    if not contexts:
        return 0.0

    context_block = "\n\n---\n\n".join(contexts)[:3000]
    prompt = (
        "Evalúa si la respuesta técnica está completamente respaldada por el contexto recuperado. "
        "Responde ÚNICAMENTE con un número entre 0.0 y 1.0, donde:\n"
        "- 1.0 = La respuesta usa exclusivamente información del contexto, sin inventar datos.\n"
        "- 0.5 = Usa parcialmente el contexto pero introduce información externa o inferencias no soportadas.\n"
        "- 0.0 = La respuesta contradice el contexto o inventa datos técnicos.\n\n"
        f"Contexto recuperado:\n{context_block}\n\n"
        f"Respuesta generada:\n{answer}\n\n"
        "Score (0-1):"
    )

    try:
        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres un evaluador estricto. Responde SOLO con un numero decimal entre 0.0 y 1.0. NUNCA escribas texto, explicaciones, oraciones ni palabras. Solo el numero."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_tokens=10,
        )
        score_text = chat_completion.choices[0].message.content or "0.5"
        # Extract first numeric token
        import re
        match = re.search(r"\d+\.?\d*", score_text.replace(",", "."))
        if match:
            val = float(match.group())
            return max(0.0, min(1.0, val))
        return 0.5
    except Exception as exc:
        print(f"    [WARN] Faithfulness parsing failed: {exc}")
        return 0.5


async def compute_answer_accuracy(
    answer: str, ground_truth: str, ai_service
) -> float:
    """Semantic similarity between generated answer and ground truth via embeddings."""
    if not answer or not ground_truth:
        return 0.0

    ans_emb = await ai_service.get_embedding(answer)
    gt_emb = await ai_service.get_embedding(ground_truth)

    dot = sum(a * b for a, b in zip(ans_emb, gt_emb))
    norm_a = math.sqrt(sum(a * a for a in ans_emb))
    norm_b = math.sqrt(sum(b * b for b in gt_emb))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


async def compute_citation_precision(
    sources: list[dict], db: AsyncSession
) -> float:
    """Fraction of unique cited document titles that exist in the database."""
    if not sources:
        return 0.0

    # Normalize titles: remove .pdf extension since DB stores without it
    cited_titles = list({
        s.get("documento", "").replace(".pdf", "").strip()
        for s in sources if s.get("documento")
    })
    if not cited_titles:
        return 0.0

    result = await db.execute(
        select(func.count(func.distinct(Document.title))).where(
            Document.title.in_(cited_titles)
        )
    )
    found = result.scalar() or 0
    return found / len(cited_titles)


async def compute_context_precision(
    retrieved_contents: list[str], ground_truth: str, ai_service
) -> float:
    """
    Heuristic for 'were the right chunks retrieved?'.
    Returns the highest embedding similarity between any retrieved chunk and the ground truth.
    """
    if not retrieved_contents or not ground_truth:
        return 0.0

    gt_emb = await ai_service.get_embedding(ground_truth)
    best_sim = 0.0

    for content in retrieved_contents:
        if not content or len(content) < 10:
            continue
        c_emb = await ai_service.get_embedding(content)
        dot = sum(a * b for a, b in zip(c_emb, gt_emb))
        norm_c = math.sqrt(sum(a * a for a in c_emb))
        norm_g = math.sqrt(sum(b * b for b in gt_emb))
        if norm_c > 0.0 and norm_g > 0.0:
            sim = dot / (norm_c * norm_g)
            if sim > best_sim:
                best_sim = sim

    return best_sim


def compute_structure_heuristics(
    response: dict[str, Any], retrieved_contents: list[str]
) -> dict[str, Any]:
    """Validate structural fields of the OGTechnicalAnswer response."""
    heuristics: dict[str, Any] = {}

    # 1. Response contains respuesta_tecnica
    respuesta = response.get("respuesta_tecnica", "")
    heuristics["has_respuesta_tecnica"] = bool(respuesta) and len(respuesta) > 20

    # 2. fuentes is non-empty when context exists
    sources = response.get("fuentes", [])
    has_context = len(retrieved_contents) > 0
    heuristics["fuentes_non_empty"] = bool(sources) if has_context else True

    # 3. score_global_confianza in [0,1]
    score = response.get("score_global_confianza")
    heuristics["score_in_range"] = (
        isinstance(score, (int, float)) and 0.0 <= float(score) <= 1.0
    )

    # 4. necesita_revision_humana set correctly
    # Logic: should be True if confidence < 0.7 OR query_type == "seguridad"
    query_type = response.get("tipo_consulta", "")
    needs_review = response.get("necesita_revision_humana")
    expected_review = (float(score) < 0.7) if isinstance(score, (int, float)) else False
    if query_type == "seguridad":
        expected_review = True
    heuristics["revision_flag_correct"] = bool(needs_review) == expected_review

    # Overall structure score
    heuristics["structure_score"] = sum(
        1
        for v in [
            heuristics["has_respuesta_tecnica"],
            heuristics["fuentes_non_empty"],
            heuristics["score_in_range"],
            heuristics["revision_flag_correct"],
        ]
        if v
    ) / 4.0

    return heuristics


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    m = _mean(values)
    if not values:
        return 0.0
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    print("=" * 70)
    print(" PetroQuery — O&G RAG Evaluation")
    print("=" * 70)

    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"Loaded {len(dataset)} evaluation questions.")
    print(f"API endpoint: {BASE_URL}")
    print("-" * 70)

    # Ensure API is up and user exists
    try:
        await ensure_user()
        token = await get_token()
    except Exception as exc:
        print(f"[ERROR] Authentication failed: {exc}")
        sys.exit(1)

    ai_service = get_ai_service()
    groq_client = groq.AsyncGroq(api_key=get_settings().groq_api_key)

    per_question: list[dict[str, Any]] = []

    async with AsyncSession(engine) as db:
        for i, item in enumerate(dataset, start=1):
            question = item["question"]
            ground_truth = item["ground_truth"]
            category = item.get("category", "general")

            print(f"[{i:02d}/{len(dataset)}] {question[:65]}...")

            # Delay between questions to avoid rate limiting
            if i > 1:
                await asyncio.sleep(2)

            try:
                response = await ask_question_with_retry(token, question)
            except Exception as exc:
                print(f"    [ERROR] API call failed: {exc}")
                continue

            answer = response.get("respuesta_tecnica", "")
            sources = response.get("fuentes", [])
            retrieved_contents = [
                s.get("contenido_citado", "") for s in sources if s.get("contenido_citado")
            ]

            # Compute metrics
            faith = await compute_faithfulness(answer, retrieved_contents, groq_client)
            acc = await compute_answer_accuracy(answer, ground_truth, ai_service)
            cit = await compute_citation_precision(sources, db)
            ctx = await compute_context_precision(
                retrieved_contents, ground_truth, ai_service
            )
            struct = compute_structure_heuristics(response, retrieved_contents)

            per_question.append(
                {
                    "question": question,
                    "category": category,
                    "answer": answer,
                    "ground_truth": ground_truth,
                    "faithfulness": round(faith, 4),
                    "answer_accuracy": round(acc, 4),
                    "citation_precision": round(cit, 4),
                    "context_precision": round(ctx, 4),
                    "structure_heuristics": struct,
                    "sources": sources,
                    "raw_response": response,
                }
            )

            print(
                f"    faith={faith:.3f} | acc={acc:.3f} | cit={cit:.3f} | ctx={ctx:.3f} | struct={struct['structure_score']:.2f}"
            )

    # -----------------------------------------------------------------------
    # Aggregation & reporting
    # -----------------------------------------------------------------------
    targets = {
        "faithfulness": 0.90,
        "answer_accuracy": 0.85,
        "citation_precision": 1.00,
    }

    report: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "total_questions": len(per_question),
        "targets": targets,
        "aggregate": {},
        "per_question": per_question,
    }

    for metric in [
        "faithfulness",
        "answer_accuracy",
        "citation_precision",
        "context_precision",
    ]:
        values = [p[metric] for p in per_question]
        report["aggregate"][metric] = {
            "mean": round(_mean(values), 4),
            "std": round(_std(values), 4),
            "min": round(min(values), 4) if values else 0.0,
            "max": round(max(values), 4) if values else 0.0,
        }

    # Structure heuristics aggregation
    struct_keys = [
        "has_respuesta_tecnica",
        "fuentes_non_empty",
        "score_in_range",
        "revision_flag_correct",
        "structure_score",
    ]
    report["aggregate"]["structure_heuristics"] = {}
    for key in struct_keys:
        vals = [p["structure_heuristics"][key] for p in per_question]
        if isinstance(vals[0], bool):
            report["aggregate"]["structure_heuristics"][key] = {
                "pass_rate": round(sum(1 for v in vals if v) / len(vals), 4) if vals else 0.0,
                "pass_count": sum(1 for v in vals if v),
                "total": len(vals),
            }
        else:
            report["aggregate"]["structure_heuristics"][key] = {
                "mean": round(_mean(vals), 4),
                "std": round(_std(vals), 4),
                "min": round(min(vals), 4) if vals else 0.0,
                "max": round(max(vals), 4) if vals else 0.0,
            }

    out_filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path = os.path.join(RESULTS_DIR, out_filename)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # -----------------------------------------------------------------------
    # Console summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(" Evaluation Complete")
    print("=" * 70)

    for metric, target in targets.items():
        mean_val = report["aggregate"][metric]["mean"]
        status = "PASS" if mean_val >= target else "FAIL"
        print(f"[{status}] {metric:20s}: {mean_val:.4f}  (target >= {target})")

    ctx_mean = report["aggregate"]["context_precision"]["mean"]
    print(f"[     ] {'context_precision':20s}: {ctx_mean:.4f}")

    print("-" * 70)
    print("Structure Heuristics")
    print("-" * 70)
    for key, val in report["aggregate"]["structure_heuristics"].items():
        if "pass_rate" in val:
            print(f"[{ 'PASS' if val['pass_rate'] >= 0.95 else 'WARN' }] {key:25s}: {val['pass_rate']:.2%} ({val['pass_count']}/{val['total']})")
        else:
            print(f"[     ] {key:25s}: {val['mean']:.4f}")

    print(f"\nDetailed report saved to: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
