"""Response templates and JSON schema instructions for structured outputs."""

MARKDOWN_TEMPLATE_OG = """## Resumen Ejecutivo
{resumen_ejecutivo}

---

## Detalle Técnico
{detalle_tecnico}

---

## Fuentes Consultadas
{fuentes}

---

## Advertencias / Consideraciones
{advertencias}

---

*Confianza global: {score_global_confianza}/1.0 | Unidades de referencia: {unidades_referencia}*
"""

JSON_SCHEMA_INSTRUCTIONS = """Debes responder EXACTAMENTE con un objeto JSON que cumpla el siguiente esquema. No incluyas texto fuera del JSON.

{
  "resumen_ejecutivo": "string (1-2 oraciones)",
  "detalle_tecnico": "string (respuesta técnica detallada)",
  "fuentes": [
    {
      "documento": "string (nombre del documento)",
      "pagina": "integer (número de página)",
      "seccion": "string | null (sección o capítulo)",
      "relevancia": "number 0.0-1.0"
    }
  ],
  "advertencias": ["string (lista de advertencias de seguridad o consideraciones)"],
  "score_global_confianza": "number 0.0-1.0",
  "unidades_referencia": ["string (unidades mencionadas en la respuesta)"],
  "recomendacion_continuacion": "string | null (siguiente paso recomendado o consulta adicional)"
}"""

FUENTE_TEMPLATE_MD = "{idx}. **{documento}** — Pág. {pagina}{seccion_str} (relevancia: {relevancia:.2f})"

ADVERTENCIA_TEMPLATE_MD = "- ⚠️ {texto}"
