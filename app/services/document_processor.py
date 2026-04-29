"""
Document processor for PetroQuery O&G technical documents.
Handles PDF extraction, table detection, and specialized chunking.
"""

import asyncio
import io
import json
import logging
from typing import Any

import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

OG_SEPARATORS = [
    "\nCAPÍTULO ",
    "\nSECCIÓN ",
    "\nARTÍCULO ",
    "\n\nPROCEDIMIENTO ",
    "\n\nPASO ",
    "\n\nTABLA ",
    "\n\nFIGURA ",
    "\n\n",
    "\n",
    " ",
]


def extract_text_and_tables_from_pdf(file_bytes: bytes) -> list[tuple[int, str, list[dict]]]:
    """
    Extract text and tables from PDF bytes.

    Returns list of tuples: (page_num, page_text, tables)
    where tables is a list of dicts with keys: rows, is_complex, row_count, col_count
    """
    pages = []
    try:
        file_stream = io.BytesIO(file_bytes)
        with pdfplumber.open(file_stream) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                page_text = page_text.strip()

                raw_tables = page.extract_tables() or []
                tables = []
                for table in raw_tables:
                    if not table:
                        continue
                    rows = []
                    for row in table:
                        if row:
                            cleaned = [str(cell).strip() if cell is not None else "" for cell in row]
                            rows.append(cleaned)
                    if not rows:
                        continue
                    row_count = len(rows)
                    col_count = max(len(r) for r in rows)
                    is_complex = row_count > 6 or col_count > 4
                    tables.append({
                        "rows": rows,
                        "is_complex": is_complex,
                        "row_count": row_count,
                        "col_count": col_count,
                    })

                pages.append((page_num, page_text, tables))
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise ValueError(f"Failed to extract text from PDF: {e}") from e

    return pages


def extract_table_as_text(table: list) -> str:
    """Convert table rows to ' | ' separated lines with header markers."""
    if not table or not table[0]:
        return ""

    lines = []
    for i, row in enumerate(table):
        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
        row_text = " | ".join(cleaned_row)
        if row_text.strip():
            if i == 0:
                lines.append("TABLA HEADER: " + row_text)
            else:
                lines.append(row_text)

    if lines:
        return "\n".join(lines)
    return ""


def extract_table_summary(table: list) -> str:
    """
    For complex tables, generate a structured summary for embedding.
    Includes headers, first 3 data rows, and row/column counts.
    """
    if not table or not table[0]:
        return ""

    rows = []
    for row in table:
        if row:
            cleaned = [str(cell).strip() if cell is not None else "" for cell in row]
            rows.append(cleaned)

    if not rows:
        return ""

    header = " | ".join(rows[0])
    data_rows = rows[1:4]
    data_examples = "\n".join(["  - " + " | ".join(r) for r in data_rows])

    summary = (
        f"[TABLA COMPLEJA]\n"
        f"Encabezados: {header}\n"
        f"Ejemplos de filas:\n{data_examples}\n"
        f"Total filas: {len(rows)}, Total columnas: {max(len(r) for r in rows)}"
    )
    return summary


def _detect_section(page_text: str) -> str:
    """Heuristic to detect section/capítulo from page text."""
    lines = page_text.splitlines()
    for line in lines[:10]:
        upper = line.strip().upper()
        if upper.startswith("CAPÍTULO") or upper.startswith("SECCIÓN") or upper.startswith("ARTÍCULO"):
            return line.strip()
    return "General"


def _brief_context(chunk_text: str) -> str:
    """Generate a brief context description for the chunk header."""
    first_line = chunk_text.splitlines()[0] if chunk_text else ""
    first_words = " ".join((chunk_text or "").split()[:12])
    return first_words if len(first_words) < 120 else first_words[:117] + "..."


def create_chunks_from_page(
    page_num: int,
    page_text: str,
    tables: list[dict],
    source: str,
    doc_metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Create chunks from a single page, handling tables specially.
    Returns list of chunk dicts with enriched metadata.
    """
    chunks: list[dict[str, Any]] = []
    section = _detect_section(page_text)
    user_id = doc_metadata.get("user_id", 0)

    # Process regular text
    if page_text and len(page_text) > 20:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=300,
            separators=OG_SEPARATORS,
            length_function=len,
            keep_separator=True,
        )
        text_chunks = text_splitter.split_text(page_text)
        for tc in text_chunks:
            tc = tc.strip()
            if len(tc) < 20:
                continue
            brief = _brief_context(tc)
            header = (
                f"[FUENTE: {source} | SECCIÓN: {section} | PÁGINA: {page_num}]\n"
                f"[CONTEXTO: Este fragmento describe {brief}]\n---"
            )
            chunks.append({
                "text": f"{header}\n{tc}",
                "source": source,
                "page": page_num,
                "chunk_number": 0,  # placeholder
                "total_chunks": 0,
                "is_table": False,
                "table_summary": None,
                "seccion": section,
                "user_id": user_id,
            })

    # Process tables
    for table_info in tables:
        table_text = extract_table_as_text(table_info["rows"])
        if not table_text:
            continue
        summary = extract_table_summary(table_info["rows"]) if table_info["is_complex"] else table_text
        header = (
            f"[FUENTE: {source} | SECCIÓN: {section} | PÁGINA: {page_num}]\n"
            f"[CONTEXTO: Este fragmento contiene datos tabulados técnicos]\n---"
        )
        chunks.append({
            "text": f"{header}\n{table_text}",
            "source": source,
            "page": page_num,
            "chunk_number": 0,
            "total_chunks": 0,
            "is_table": True,
            "table_summary": summary,
            "seccion": section,
            "user_id": user_id,
        })

    return chunks


def validate_and_merge_small_chunks(chunks: list[dict]) -> list[dict]:
    """
    Validate chunk sizes:
    - Merge chunks <50 chars with previous chunk.
    - Split chunks >4000 chars at nearest paragraph boundary.
    """
    if not chunks:
        return []

    # First pass: merge small chunks
    merged: list[dict] = []
    for chunk in chunks:
        text_len = len(chunk.get("text", ""))
        if text_len < 50 and merged:
            merged[-1]["text"] += "\n" + chunk["text"]
            merged[-1]["is_table"] = merged[-1].get("is_table") or chunk.get("is_table")
            if chunk.get("table_summary"):
                existing = merged[-1].get("table_summary") or ""
                merged[-1]["table_summary"] = existing + "\n" + chunk["table_summary"]
        else:
            merged.append(chunk.copy())

    # Second pass: split oversized chunks
    final: list[dict] = []
    for chunk in merged:
        text = chunk.get("text", "")
        if len(text) <= 4000:
            final.append(chunk)
            continue

        # Split at paragraph boundaries
        paragraphs = text.split("\n\n")
        current_text = ""
        current_is_table = False
        current_summary = ""

        for para in paragraphs:
            if len(current_text) + len(para) + 2 > 4000 and current_text:
                final.append({
                    **chunk,
                    "text": current_text.strip(),
                    "is_table": current_is_table,
                    "table_summary": current_summary or None,
                })
                current_text = para
                current_is_table = chunk.get("is_table", False)
                current_summary = chunk.get("table_summary", "") or ""
            else:
                current_text = (current_text + "\n\n" + para).strip() if current_text else para
                current_is_table = current_is_table or chunk.get("is_table", False)
                if chunk.get("table_summary"):
                    current_summary = (current_summary + "\n" + chunk["table_summary"]).strip()

        if current_text:
            final.append({
                **chunk,
                "text": current_text.strip(),
                "is_table": current_is_table,
                "table_summary": current_summary or None,
            })

    # Renumber chunks
    for i, chunk in enumerate(final, start=1):
        chunk["chunk_number"] = i
        chunk["total_chunks"] = len(final)

    return final


async def generate_document_insights(
    chunks: list[dict],
    openai_client,
) -> dict:
    """Generate technical summary, detected sections, and suggested questions.

    Uses the first 10 chunks (~3000 tokens) for analysis.
    Makes a single LLM call with a cheap model.
    Also generates per-section insights (topics, important points, questions).
    """
    if not chunks:
        return {"summary": "", "global_topics": [], "global_questions": [], "sections": []}

    combined = "\n\n".join(c["text"][:500] for c in chunks[:10])
    combined = combined[:4000]

    prompt = f"""Analiza el siguiente documento técnico Oil & Gas y genera:

1. Un resumen técnico de 3 párrafos en español
2. Los temas globales del documento (ej: Seguridad, Especificaciones, Normativa, Procedimiento)
3. 5 preguntas sugeridas que un ingeniero podría hacerle a este documento

Formato de respuesta (JSON):
{{"summary": "...", "global_topics": ["Seguridad", "..."], "global_questions": ["¿Cuál es...?", "..."]}}

Documento:
{combined}

Responde SOLO con el JSON, sin markdown ni explicaciones."""

    try:
        chat_completion = await openai_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=800,
        )
        content = chat_completion.choices[0].message.content or "{}"
        insights = json.loads(content)
    except Exception as e:
        logger.error(f"Failed to generate document insights: {e}")
        insights = {"summary": "", "global_topics": [], "global_questions": []}

    sections_data = await _generate_sections_insights(chunks, openai_client)
    insights["sections"] = sections_data

    return insights


async def _generate_sections_insights(chunks: list[dict], openai_client) -> list[dict]:
    """Generate insights per section by detecting actual document structure."""
    import re

    all_texts = [c["text"][:800] for c in chunks]
    combined_preview = "\n\n".join(all_texts[:20])[:5000]

    detect_prompt = f"""Analiza el siguiente documento técnico y detecta su estructura de capítulos/secciones.

Devuelve un JSON con una lista de secciones detectadas, cada una con:
- "name": nombre del capítulo/sección
- "start_marker": una frase o palabra única que indique el inicio de esa sección (ej: "CAPÍTULO 1", "4. DESCRIPCIÓN", "Artículo 5")

El documento tiene aproximadamente {len(chunks)} fragmentos.

Formato de respuesta:
{{"sections": [{{"name": "Nombre", "start_marker": "marcador"}}, ...]}}

Documento:
{combined_preview}

Responde SOLO con el JSON."""

    try:
        detect_response = await openai_client.chat.completions.create(
            messages=[{"role": "user", "content": detect_prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=800,
        )
        detected = json.loads(detect_response.choices[0].message.content or "{}")
        section_defs = detected.get("sections", [])
    except Exception as e:
        logger.error(f"Failed to detect sections: {e}")
        section_defs = []

    if not section_defs:
        section_defs = [{"name": "Contenido general", "start_marker": ""}]

    sections_insights = []
    for section_def in section_defs:
        sec_name = section_def.get("name", "Sin nombre")
        start_marker = section_def.get("start_marker", "")

        if start_marker:
            pattern = re.compile(re.escape(start_marker), re.IGNORECASE)
            relevant_texts = []
            for c in chunks:
                if pattern.search(c["text"][:200]) or pattern.search(c.get("seccion", "") or ""):
                    relevant_texts.append(c["text"][:1000])
        else:
            relevant_texts = [c["text"][:1000] for c in chunks]

        if not relevant_texts:
            relevant_texts = [c["text"][:1000] for c in chunks[:5]]

        combined = "\n\n".join(relevant_texts)[:3000]

        insight_prompt = f"""Analiza la sección "{sec_name}" y genera:

1. Temas específicos de esta sección
2. 3-5 puntos importantes técnicos
3. 3 preguntas sugeridas sobre esta sección

Formato JSON:
{{"topics": ["Tema A", "..."], "important_points": ["Punto 1", "..."], "questions": ["¿Qué...?", "..."]}}

Contenido:
{combined}

Responde SOLO con el JSON."""

        try:
            chat_completion = await openai_client.chat.completions.create(
                messages=[{"role": "user", "content": insight_prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=600,
            )
            content = chat_completion.choices[0].message.content or "{}"
            section_insight = json.loads(content)
        except Exception as e:
            logger.error(f"Failed to generate insights for section {sec_name}: {e}")
            section_insight = {"topics": [], "important_points": [], "questions": []}

        sections_insights.append({
            "name": sec_name,
            "topics": section_insight.get("topics", []),
            "important_points": section_insight.get("important_points", []),
            "questions": section_insight.get("questions", []),
        })

    return sections_insights
