"""HSE Priority Protocol for safety-critical queries."""
import re

HSE_KEYWORDS = [
    "H2S", "sulfhídrico", "gas toxico", "evacuación", "emergencia",
    "blowout", "control de pozo", "killing", "pressure testing",
    "PPE", "SCBA", "EEBA", "muster point", "rescue", "fuga",
    "incendio", "explosión", "venteo", "purga", "confinado",
    "accidente", "lesión", "muerte", "fatalidad", "peligro",
]


def is_hse_query(question: str) -> bool:
    question_lower = question.lower()
    return any(kw.lower() in question_lower for kw in HSE_KEYWORDS)


def boost_hse_documents(results: list[dict]) -> list[dict]:
    for doc in results:
        if doc.get("tipo_documento") in ["manual", "normativa"]:
            normativa = str(doc.get("normativa_aplicable", "")).lower()
            title = str(doc.get("title", "")).lower()
            if "h2s" in normativa or "seguridad" in normativa or "seguridad" in title:
                doc["rrf_score"] = doc.get("rrf_score", 0) * 1.5
    return sorted(results, key=lambda x: x.get("rrf_score", 0), reverse=True)


def hse_hard_stop(answer: dict) -> dict:
    """If safety query and low confidence, force human review."""
    if answer.get("tipo_consulta") == "seguridad":
        if answer.get("score_global_confianza", 0) < 0.8:
            answer["necesita_revision_humana"] = True
        if not answer.get("advertencia_seguridad"):
            answer["advertencia_seguridad"] = (
                "Toda operación de seguridad debe ser validada por un Oficial de HSE "
                "antes de su ejecución. Esta respuesta es orientativa."
            )
    return answer
