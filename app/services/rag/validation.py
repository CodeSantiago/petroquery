"""Post-generation validation and finalisation.

The previous implementation performed three things in the chat router
right after the LLM call:

1. Number validation: extract technical numbers from the answer and
   verify they appear in the source chunks. When verification fails we
   lower the global confidence and force human review.
2. Confidence-based human review: anything below 0.7 (or any safety
   query) is flagged for human review.
3. HSE hard-stop (already applied in :mod:`generation`).

This module wraps the first two in a single function so the router
does not have to know which magic numbers live where.
"""
from __future__ import annotations

from app.schemas.og_schemas import OGTechnicalAnswer
from app.services.number_validator import (
    extract_technical_numbers,
    validate_numbers_against_chunks,
)
from app.services.rag.types import NumberValidation, RetrievedChunk


# Confidence threshold below which we always require a human reviewer.
REVIEW_THRESHOLD = 0.7

# Multiplier applied to the global score when number validation fails.
NUMBER_MISMATCH_PENALTY = 0.7


def validate_answer_numbers(
    answer: OGTechnicalAnswer,
    chunks: list[RetrievedChunk],
) -> NumberValidation | None:
    """Return number-validation diagnostics for ``answer``.

    Returns ``None`` when the answer has no technical numbers to check.
    """
    raw_answer = answer.respuesta_tecnica or ""
    extracted = extract_technical_numbers(raw_answer)
    if not extracted:
        return None

    chunk_texts = [c.content for c in chunks]
    result = validate_numbers_against_chunks(extracted, chunk_texts)
    return NumberValidation(
        total_count=result["total_count"],
        verified_count=result["verified_count"],
        all_verified=result["all_verified"],
        details=result["details"],
    )


def apply_validation_to_answer(
    answer: OGTechnicalAnswer,
    validation: NumberValidation | None,
) -> OGTechnicalAnswer:
    """Apply validation side-effects to the answer in-place and return it."""
    if validation is not None and not validation.all_verified:
        answer.score_global_confianza = round(
            answer.score_global_confianza * NUMBER_MISMATCH_PENALTY, 4
        )
        answer.necesita_revision_humana = True
    return answer


def should_require_human_review(answer: OGTechnicalAnswer) -> bool:
    """Return True when the answer must be flagged for human review.

    The rule is: any safety query, or any answer with global confidence
    below :data:`REVIEW_THRESHOLD`.
    """
    if answer.tipo_consulta == "seguridad":
        return True
    return answer.score_global_confianza < REVIEW_THRESHOLD


def finalize_answer(
    answer: OGTechnicalAnswer,
    chunks: list[RetrievedChunk],
) -> tuple[OGTechnicalAnswer, NumberValidation | None]:
    """Run the full post-generation pass: number validation + human
    review flag.
    """
    validation = validate_answer_numbers(answer, chunks)
    answer = apply_validation_to_answer(answer, validation)
    if should_require_human_review(answer):
        answer.necesita_revision_humana = True
    return answer, validation


__all__ = [
    "validate_answer_numbers",
    "apply_validation_to_answer",
    "should_require_human_review",
    "finalize_answer",
    "REVIEW_THRESHOLD",
    "NUMBER_MISMATCH_PENALTY",
]
