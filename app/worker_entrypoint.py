"""Entry point for the isolated ML worker subprocess.

The worker reads a single JSON task from stdin, performs the work, and
writes a single JSON document to stdout. The process exit code is
zero on success and non-zero on any failure. Stderr is captured by the
parent process so the failure reason is available even when stdout is
empty.

The parent process that spawns this worker is :func:`app.services.ml_subprocess.run_in_subprocess`.

The worker only depends on the lazy-loaded ML stack; on hosts without
that stack it returns a clean ``{"ok": false, "error": "..."}`` JSON
response with exit code 1 instead of crashing, so the parent process
can stay alive.
"""
from __future__ import annotations

import asyncio
import json
import sys
import traceback
from typing import Any


def _emit(result: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(result, ensure_ascii=False, default=str))
    sys.stdout.flush()


def _run_embeddings(task: dict[str, Any]) -> list[list[float]]:
    from app.services.ai_service import get_ai_service

    texts = task.get("texts") or []
    if not isinstance(texts, list):
        raise ValueError("`texts` must be a list of strings")

    async def _run() -> list[list[float]]:
        ai = get_ai_service()
        return [await ai.get_document_embedding(str(t)) for t in texts]

    return asyncio.run(_run())


def _run_process_pdf(task: dict[str, Any]) -> dict[str, Any]:
    from app.services.document_processor import (
        create_chunks_from_page,
        extract_text_and_tables_from_pdf,
        validate_and_merge_small_chunks,
    )

    pdf_hex = task.get("pdf_hex")
    if not pdf_hex:
        raise ValueError("`pdf_hex` is required for process_pdf tasks")
    pdf_bytes = bytes.fromhex(pdf_hex)

    pages = extract_text_and_tables_from_pdf(pdf_bytes)
    all_chunks: list[dict] = []
    for page_num, page_text, tables in pages:
        page_chunks = create_chunks_from_page(
            page_num=page_num,
            page_text=page_text,
            tables=tables,
            source=str(task.get("filename", "unknown.pdf")),
            doc_metadata=dict(task.get("metadata") or {}),
        )
        all_chunks.extend(page_chunks)

    final = validate_and_merge_small_chunks(all_chunks)
    return {"chunks": final, "page_count": len(pages)}


def main() -> int:
    try:
        task = json.loads(sys.stdin.read() or "{}")
    except Exception as exc:
        sys.stderr.write(f"Invalid task JSON: {type(exc).__name__}: {exc}\n")
        return 2

    if not isinstance(task, dict):
        sys.stderr.write("Task must be a JSON object\n")
        return 2

    task_type = task.get("type")
    try:
        if task_type == "embeddings":
            result = _run_embeddings(task)
        elif task_type == "process_pdf":
            result = _run_process_pdf(task)
        else:
            sys.stderr.write(f"Unknown task type: {task_type!r}\n")
            return 3

        _emit({"ok": True, "result": result})
        return 0
    except Exception as exc:
        sys.stderr.write(
            f"Worker task failed: {type(exc).__name__}: {exc}\n"
        )
        sys.stderr.write(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
