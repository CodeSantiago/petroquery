"""Persistence helpers for the chat area.

This package contains the thin database access layer used by the chat
router. The goal is to keep the router free of SQL: every ``select``,
``insert`` or ``delete`` for the chat area lives behind one of the
helpers in this package.

The package is split by concern:

* :mod:`chat_repository`    - chat + message CRUD
* :mod:`audit_repository`   - query audit lifecycle
* :mod:`project_repository` - project membership checks

Anything that combines persistence with business logic (number
validation, HSE handling, etc.) belongs in the RAG pipeline, not here.
"""
from app.services.persistence.audit_repository import (
    create_audit,
    mark_audit_error,
    update_audit,
)
from app.services.persistence.chat_repository import (
    DEFAULT_CHAT_TITLE,
    HISTORY_LIMIT,
    delete_chat_cascade,
    delete_chat_documents,
    delete_chat_messages,
    fetch_chat_history,
    format_history,
    get_chat_documents,
    list_user_chats,
    resolve_or_create_chat,
    save_messages,
)
from app.services.persistence.project_repository import assert_project_access

__all__ = [
    # chat
    "resolve_or_create_chat",
    "fetch_chat_history",
    "format_history",
    "save_messages",
    "delete_chat_cascade",
    "delete_chat_messages",
    "delete_chat_documents",
    "list_user_chats",
    "get_chat_documents",
    "HISTORY_LIMIT",
    "DEFAULT_CHAT_TITLE",
    # audit
    "create_audit",
    "update_audit",
    "mark_audit_error",
    # projects
    "assert_project_access",
]
