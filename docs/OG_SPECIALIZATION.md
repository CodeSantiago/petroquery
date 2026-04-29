# Especialización de PetroQuery en Oil & Gas

> Documento de adaptación de dominio: de RAG genérico a sistema especializado para operaciones de Oil & Gas en Vaca Muerta, Argentina.

---

## 1. Adaptación de Dominio: De RAG Genérico a O&G

### 1.1 El Problema del RAG Genérico en O&G

Un sistema RAG estándar (ej. basado en OpenAI + Pinecone) falla en entornos Oil & Gas por:

- **Terminología híbrida**: Los manuales técnicos mezclan español, inglés técnico y siglas ("BOP", "SCBA", "H2S", "SIDPP").
- **Datos tabulares críticos**: Tablas de presiones, especificaciones de casing y rangos operacionales pierden sentido si se fragmentan incorrectamente.
- **Riesgo de alucinaciones**: Una respuesta inventada sobre presiones de formación o procedimientos de H2S puede poner vidas en riesgo.
- **Trazabilidad obligatoria**: Las normativas IAPG y API exigen citar documento, página y sección exacta.

### 1.2 Adaptaciones Implementadas en PetroQuery

| Problema | Solución en PetroQuery |
|---|---|
| Terminología técnica | Embeddings `multilingual-e5-large` + prefijos `query:` / `passage:` optimizados para español técnico |
| Tablas fragmentadas | Chunking consciente de tablas: preserva headers, filas y unidades; resumen de tabla compleja en metadata |
| Alucinaciones de seguridad | Instructor + Pydantic estricto; system prompt con penalización explícita por inventar datos |
| Trazabilidad | Schema `SourceReference` obliga documento, página, sección, tabla/figura y score de confianza |
| Normativa específica | Filtros por `normativa_aplicable`, `cuenca` y `tipo_equipo` para restringir contexto |

### 1.3 Ingesta de Documentos Técnicos

El procesador de documentos PDF está optimizado para manuales O&G:

1. **Extracción con `pdfplumber`**: Preserva layout de tablas (gridlines, celdas mergeadas).
2. **Detección de tablas**: Si una página contiene >3 filas con datos numéricos, se marca como tabla.
3. **Chunking semántico**:
   - Separadores prioritarios: `"\n## "`, `"\n### "`, `"\nTabla "`, `"\nFigura "`
   - Tamaño de chunk: 1000 tokens con overlap de 200 tokens
   - Las tablas se mantienen intactas si caben en el chunk; si no, se genera un resumen textual en `extra_data`
4. **Enriquecimiento de metadata**:
   - `page`: número de página del PDF
   - `seccion`: título de sección detectado por heurística de mayúsculas/tamaño de fuente
   - `tabla_referencia`: "Tabla 3.2", "Table 5-1"
   - `figura_referencia`: "Figura 4.1", "Figure 2-3"
   - `normativa_aplicable`: extraído por regex de menciones a IAPG, API, ISO, NACE

---

## 2. System Prompt Engineering: Persona Senior Field Engineer

### 2.1 Diseño de la Persona

El system prompt no es un asistente genérico. Adopta la identidad de un **Senior Field Engineer** con 20+ años de experiencia en Vaca Muerta:

```text
Eres un Ingeniero de Campo Senior especializado en operaciones de Oil & Gas 
en la Cuenca Neuquina (Vaca Muerta), Argentina. Tienes 20+ años de experiencia 
en perforación, completions y producción en ambientes de alta presión y H2S.

REGLAS INQUEBRANTABLES:
1. NUNCA inventes valores numéricos (presiones, densidades, especificaciones).
2. NUNCA cites documentos que no estén en el contexto proporcionado.
3. Si la información es insuficiente, indica explícitamente que se requiere revisión humana.
4. Para consultas de seguridad (H2S, PPE, evacuación), SIEMPRE incluye una advertencia 
   de seguridad explícita y activa la bandera necesita_revision_humana.
5. Usa terminología técnica en español con siglas en inglés cuando sea estándar de la industria.
6. Estructura la respuesta en markdown con secciones claras: Resumen, Detalle Técnico, 
   Advertencias (si aplica), Referencias.
```

### 2.2 Por qué esta Persona Funciona

- **Autoridad técnica**: El modelo adopta un tono preciso, cauteloso y basado en evidencia.
- **Penalización de alucinaciones**: Las reglas explícitas reducen drásticamente la generación de datos falsos.
- **Priorización de seguridad**: Las consultas de seguridad siempre disparan la advertencia y la bandera de revisión.
- **Formato consistente**: La estructura markdown facilita el parsing por el frontend y la lectura por ingenieros de campo.

### 2.3 Variantes de Prompt por Tipo de Consulta

El clasificador de intención detecta el tipo de consulta y enriquece el prompt:

| Tipo de Consulta | Enriquecimiento del Prompt |
|---|---|
| `seguridad` | "Esta es una consulta de SEGURIDAD CRÍTICA. Verifica cada dato contra el contexto. Activa advertencia_seguridad." |
| `normativa` | "Cita la normativa exacta (IAPG, API, Resolución SE) con artículo o sección cuando sea posible." |
| `equipos` | "Incluye especificaciones técnicas completas: dimensiones, presiones, materiales, estándares." |
| `procedimiento` | "Presenta los pasos en orden cronológico numerado. Incluye puntos de verificación (checkpoints)." |
| `comparacion` | "Usa una tabla comparativa. Destaca diferencias críticas para operaciones." |

---

## 3. Safety-First Design

### 3.1 Principios de Diseño Orientados a Seguridad

PetroQuery fue diseñado bajo la premisa de que **una respuesta incorrecta en seguridad puede causar fatalidades**. Los principios son:

1. **Fail-safe**: Si hay duda, siempre activar `necesita_revision_humana`.
2. **Advertencias explícitas**: Todo output relacionado con H2S, PPE, evacuación o procedimientos de emergencia incluye `advertencia_seguridad`.
3. **Sin inventiva en seguridad**: El prompt prohíbe estrictamente inventar protocolos, umbrales de ppm o procedimientos de evacuación.
4. **Trazabilidad total**: Cada recomendación de seguridad debe estar anclada a un documento normativo o manual de procedimiento.

### 3.2 Mecanismos de Seguridad Implementados

#### a) Clasificador de Seguridad

```python
async def classify_query_type(self, question: str) -> str:
    # Palabras clave de seguridad
    safety_keywords = ["h2s", "evacuacion", "ppe", "blowout", "emergencia", 
                       "seguridad", "respirador", "muster point"]
    if any(k in question.lower() for k in safety_keywords):
        return "seguridad"
    # ... otros tipos
```

#### b) Forzado de Bandera de Revisión

```python
if og_answer.score_global_confianza < 0.7 or query_type == "seguridad":
    og_answer.necesita_revision_humana = True
```

#### c) Validación de Advertencia

En la generación estructurada, si `tipo_consulta == "seguridad"` y `advertencia_seguridad` es `None`, el schema validation de Pydantic puede rechazar la respuesta o el frontend mostrará una advertencia genérica.

### 3.3 Casos de Uso Críticos

| Escenario | Comportamiento Esperado |
|---|---|
| "Protocolo de evacuación por H2S a 20 ppm" | Respuesta con pasos exactos + advertencia de seguridad + revisión humana obligatoria |
| "¿Puedo usar este casing en H2S?" | Respuesta técnica con referencia a NACE MR0175 + revisión humana si no hay contexto suficiente |
| "Pasos para killing the well" | Procedimiento paso a paso con checkpoints + advertencia + revisión humana |

---

## 4. Requisitos de Trazabilidad

### 4.1 Niveles de Trazabilidad

PetroQuery implementa trazabilidad en 4 niveles, exigidos por operadores como YPF y reguladores como IAPG:

```
Nivel 1: Documento     → "Manual de Operaciones BOP Cameron"
Nivel 2: Página        → "Página 47"
Nivel 3: Sección       → "Sección 3.2: Pressure Testing"
Nivel 4: Tabla/Figura  → "Tabla 3.4", "Figura 2-1"
```

### 4.2 Implementación en el Schema

```python
class SourceReference(BaseModel):
    documento: str          # Nivel 1
    pagina: int             # Nivel 2
    seccion: Optional[str]  # Nivel 3
    tabla_referencia: Optional[str]   # Nivel 4a
    figura_referencia: Optional[str]  # Nivel 4b
    score_confianza: float  # Confianza del retrieval
    contenido_citado: str   # Literal del chunk usado
```

### 4.3 Frontend: Visualización de Trazabilidad

La interfaz Next.js renderiza cada fuente como una tarjeta expansible:

- **Documento**: Título clickable que abre el PDF en la página indicada.
- **Página**: Badge con número de página.
- **Sección**: Subtítulo en gris.
- **Tabla/Figura**: Icono de tabla o imagen con tooltip.
- **Contenido citado**: Bloque de texto con scroll si excede 500 caracteres.

### 4.4 Auditoría y Compliance

Cada consulta y respuesta se almacena en la tabla `messages` con:

- `content`: Texto plano de la respuesta
- `structured_response`: JSON completo con fuentes y scores
- `created_at`: Timestamp UTC para auditoría

Esto permite:
- Reconstruir qué documentos respaldaron una decisión operacional.
- Demostrar compliance ante auditorías de IAPG o Secretaría de Energía.
- Identificar gaps documentales cuando el sistema no encuentra contexto.

---

## 5. Métricas de Adaptación de Dominio

| Métrica | RAG Genérico | PetroQuery (Objetivo) |
|---|---|---|
| Faithfulness en manuales técnicos | ~0.65 | **>0.90** |
| Precisión en tablas numéricas | ~0.40 | **>0.85** |
| Trazabilidad documental | Inexistente | **100%** |
| Detección de consultas de seguridad | ~0.50 | **>0.95** |
| Tiempo de respuesta (end-to-end) | ~5-10s | **<3s** |

---

## 6. Lecciones Aprendidas

1. **Los embeddings genéricos no entienden "10M"**: Los modelos como OpenAI text-embedding-ada-002 tratan "10M" como texto común, mientras que E5 con prefijo `passage:` entiende que es una clasificación de presión.
2. **El chunking destruye tablas**: Un chunk de 1000 tokens que corta una tabla a la mitad genera respuestas sin sentido. El chunking debe detectar límites de tabla.
3. **Los ingenieros no confían en respuestas sin fuente**: Incluso si la respuesta es correcta, si no cita el manual, el usuario la descarta. La trazabilidad es un requisito de usabilidad, no solo de compliance.
4. **La seguridad no puede ser opt-in**: El sistema debe asumir que toda consulta sobre H2S, presión o PPE es crítica hasta demostrar lo contrario.

---

*Documento de especialización de dominio para PetroQuery — Sistema RAG industrial para Oil & Gas en Argentina.*
