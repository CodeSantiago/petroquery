"""PII Masking for Oil & Gas documents before sending to LLM."""
import re


class PIIMasker:
    PATTERNS = {
        "person_name": r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',
        "exact_coords": r'-?\d{2}\.\d{4,},\s*-?\d{2,3}\.\d{4,}',
        "financial_value": r'\$\s*\d[\d,\.]*\s*(millones|miles|USD|ARS)?',
        "phone": r'\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
        "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    }

    @classmethod
    def mask(cls, text: str) -> str:
        for label, pattern in cls.PATTERNS.items():
            text = re.sub(pattern, f"[{label.upper()}]", text)
        return text
