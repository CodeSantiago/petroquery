"""Context-window management for the LLM.

The previous implementation hard-coded a single ``trim_context`` helper
inside ``chat.py`` and the cap (4000 chars) as a module-level constant.
Promoting it to its own module makes the heuristic testable, easy to
swap, and easy to tune without touching the router.
"""
from __future__ import annotations

MAX_CONTEXT_CHARS = 4000


def trim_context(context: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """Trim a context string to ``max_chars`` while preferring paragraph
    boundaries over hard cuts.

    Behaviour preserved from the previous implementation:

    * If the context already fits, return it as-is.
    * Otherwise cut at ``max_chars`` and look backwards for a paragraph
      break (``\\n\\n``) past the halfway mark. If found, stop there.
    * Otherwise append a trailing marker so the LLM can see it was
      truncated.
    """
    if len(context) <= max_chars:
        return context

    trimmed = context[:max_chars]
    last_newline = trimmed.rfind("\n\n")
    if last_newline > max_chars * 0.5:
        return trimmed[:last_newline].strip()
    return trimmed.strip() + "\n\n[Contexto truncado...]"


__all__ = ["trim_context", "MAX_CONTEXT_CHARS"]
