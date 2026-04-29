"""Detection and prevention of prompt injection attacks."""
import re

INJECTION_PATTERNS = [
    r"olvida\s+(todo|las\s+reglas|las\s+instrucciones)",
    r"ignora\s+(todo|las\s+reglas)",
    r"actúa\s+como\s+(?!un\s+ingeniero)",
    r"ahora\s+eres\s+",
    r"system\s*:\s*",
    r"prompt\s*:\s*",
    r"new\s+instructions?",
    r"bypass",
    r"saltar\s+(protocolos?|reglas?|normas?)",
]


def detect_prompt_injection(question: str) -> tuple[bool, str]:
    question_lower = question.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, question_lower):
            return True, "Detección de intento de manipulación del sistema. Consulta marcada para revisión humana obligatoria."
    return False, ""
