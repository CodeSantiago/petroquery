"""Answer generation.

The generation stage takes the assembled context and the chat history
and produces a structured :class:`OGTechnicalAnswer`. It also applies
the HSE hard-stop rules and, when the LLM returned an empty
``fuentes`` list, falls back to the sources assembled by the previous
stage.
"""
from __future__ import annotations

import time

from app.schemas.og_schemas import OGTechnicalAnswer
from app.services.ai_service import AIService
from app.services.hse_protocol import hse_hard_stop
from app.services.rag.types import AssembledContext


async def generate_answer(
    ai_service: AIService,
    *,
    question: str,
    history: str,
    query_type: str,
    assembled: AssembledContext,
) -> tuple[OGTechnicalAnswer, int]:
    """Run the LLM and post-process its structured output.

    Returns the final :class:`OGTechnicalAnswer` plus the measured
    ``llm_time_ms``.
    """
    start = time.time()
    answer = await ai_service.ask_og_structured(
        context=assembled.context,
        question=question,
        history=history,
        query_type=query_type,
    )
    llm_time_ms = int((time.time() - start) * 1000)

    # If the LLM didn't return any sources, fall back to the ones we
    # built during the assembly stage.
    if not answer.fuentes and assembled.sources:
        answer.fuentes = list(assembled.sources)

    # Override the global confidence with the average rerank score when
    # we actually have sources. This matches the previous behaviour.
    if answer.fuentes:
        avg_score = sum(f.score_confianza for f in answer.fuentes) / len(answer.fuentes)
        answer.score_global_confianza = round(avg_score, 4)

    # Apply HSE hard-stop rules (forces human review for low-confidence
    # safety queries and injects the mandatory disclaimer).
    answer_dict = answer.model_dump()
    answer_dict = hse_hard_stop(answer_dict)
    final = OGTechnicalAnswer(**answer_dict)
    return final, llm_time_ms


__all__ = ["generate_answer"]
