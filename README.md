# PetroQuery — Industrial RAG for Oil & Gas

**A production-shaped Retrieval-Augmented Generation system that answers
technical questions about upstream operations in the Vaca Muerta basin from
real engineering manuals — with citations, numeric validation, and a
reviewable pipeline.**

> Built to show that an RAG system for a safety-critical industry is not a
> chatbot with a vector store. It is a typed pipeline with hybrid retrieval,
> cross-encoder reranking, structured generation, number validation, PII
> masking, and a query audit trail.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-000?logo=nextdotjs)](https://nextjs.org)
[![pgvector](https://img.shields.io/badge/pgvector-336791?logo=postgresql)](https://github.com/pgvector/pgvector)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)

---

## What it does

PetroQuery ingests dense technical PDFs — drilling procedures, well
completion reports, HSE protocols, API / IAPG specs, equipment datasheets —
and turns them into a question-answering system a field engineer or an
operations manager can actually trust.

A user asks in natural Spanish; the system returns a structured technical
answer with:

- a **technical response** grounded in the retrieved context,
- a **safety warning** when the topic implies operational risk,
- **source citations** that point back to the exact manual and chunk,
- a **global confidence score** in `[0, 1]`,
- a **human-review flag** raised when evidence is weak or numeric claims
  cannot be verified against the source.

Every interaction writes a `QueryAudit` row — retrieval time, LLM time,
chunk IDs, validation outcome — so a reviewer can trace any answer back
to the evidence that produced it.

## What makes it different

Most "RAG demos" stop at *embed → retrieve → prompt*. PetroQuery is wired
the way a real industrial RAG system has to be:

- **Hybrid retrieval** (semantic + lexical) fused with **Reciprocal Rank
  Fusion** — catches both paraphrased intent and exact technical terms
  (BOP pressures, casing grades, normativa numbers).
- **Cross-encoder reranking** of the top candidates before generation.
- **Typed, modular pipeline** with one stage per file under
  `app/services/rag/` — easy to test, swap, and review.
- **Structured generation** via `instructor` + Pydantic — the LLM cannot
  return malformed JSON, so the UI never has to guess the shape of an
  answer.
- **Safety overlays** on every request: prompt-injection guard, PII masker
  that preserves O&G proper nouns (well names, operators, basins), and a
  numeric validator that cross-checks every figure in the answer against
  the retrieved chunks.
- **HSE-aware responses**: when the query is classified as safety-critical,
  the prompt forces a non-empty `advertencia_seguridad` field.
- **Query audit trail** persisted for every interaction.

## Architecture at a glance

```
                ┌──────────────────────────────┐
   User ──▶     │  Next.js (App Router)        │
                │  chat · admin · manual ·     │
                │  projects · auth             │
                └──────────────┬───────────────┘
                               │ HTTPS / JWT
                ┌──────────────▼───────────────┐
                │  FastAPI  (app/main.py)      │
                │  routers: auth · chat ·      │
                │  ingest · projects · admin   │
                └──────────────┬───────────────┘
                               │
              ┌────────────────▼────────────────┐
              │  RAG pipeline                   │
              │  (app/services/rag/pipeline)   │
              │  classify → retrieve → rerank   │
              │   → assemble → generate →       │
              │   validate                      │
              └──┬───────────┬───────────┬──────┘
                 │           │           │
        ┌────────▼──┐  ┌─────▼─────┐  ┌──▼──────────────┐
        │ PostgreSQL│  │ Groq LLM  │  │ Safety overlays │
        │ + pgvector│  │ (Llama 3) │  │ · injection grd │
        │ 1024-d    │  │           │  │ · PII masker    │
        │ embeddings│  │           │  │ · HSE protocol  │
        └───────────┘  └───────────┘  │ · number valid. │
                                      └─────────────────┘
```

## The RAG pipeline (in order)

The chat router never assembles a prompt by hand. It calls a single
function — `run_rag_pipeline(...)` — and the pipeline does the rest in
six typed stages, each one its own module under `app/services/rag/`:

| Stage | Module | Responsibility |
|-------|--------|----------------|
| **1. Classify** | `classification.py` | Tag the question as `operacional` / `normativa` / `seguridad` / `equipos` / `general` so downstream prompts can adapt. |
| **2. Retrieve** | `retrieval.py` | Hybrid search: vector similarity over `multilingual-e5-large` (1024-d) + PostgreSQL FTS, fused with RRF. |
| **3. Rerank** | `reranking.py` | Cross-encoder reranks the top candidates; trimmed context is assembled. |
| **4. Generate** | `generation.py` | `instructor` + Pydantic enforce the `OGTechnicalAnswer` schema; the LLM cannot return malformed output. |
| **5. Validate** | `validation.py` | Numeric claims in the answer are cross-checked against the retrieved chunks. Unverified numbers raise the human-review flag. |

Each stage returns a small dataclass declared in `app/services/rag/types.py`
(`RagRequest`, `RetrievedChunk`, `RetrievalResult`, `AssembledContext`,
`NumberValidation`, `RagResponse`). That is what makes the stages testable
in isolation — see `tests/rag/`.

Persistence (chat history, messages, audit rows) lives in a separate
package, `app/services/persistence/`, and is the router's responsibility
— the pipeline itself does not write to the DB.

## Quick start

```bash
# 1. Configure secrets (NEVER commit your real .env)
cp .env.example .env
# Edit .env and set SECRET_KEY, GROQ_API_KEY, DATABASE_URL.
# Generate SECRET_KEY with:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"

# 2. Bring up PostgreSQL + pgvector
docker compose up -d db

# 3. Install + initialize
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python scripts/init_petroquery_db.py     # see warning below

# 4. Run
uvicorn app.main:app --reload            # API on :8000
cd frontend && npm run dev               # UI on :3000
```

Open http://localhost:3000 for the chat UI and
http://localhost:8000/docs for the interactive OpenAPI.

> **Heads-up — `init_petroquery_db.py` is destructive.** It drops every
> existing `users`, `companies`, `projects`, `chats`, `messages`,
> `documents`, and `query_audits` table before recreating the schema.
> Use it for first-time setup or a clean reset, not against a populated
> DB.

### Production-mode guardrails

When `APP_ENV=production`, the application refuses to start if
`SECRET_KEY`, `DATABASE_URL`, or `CORS_ALLOWED_ORIGINS` are missing or
still set to the placeholder values shipped in `.env.example`. In
development, a fresh ephemeral `SECRET_KEY` is generated per process and a
warning is logged.

### Useful Make targets

| Target | What it does |
|--------|--------------|
| `make install` | Create venv and install runtime dependencies. |
| `make dev-install` | Add development / test dependencies. |
| `make run-db` | Start the PostgreSQL + pgvector container. |
| `make init-db` | Initialize the schema (destructive — see above). |
| `make run` | Start the API on `0.0.0.0:8000`. |
| `make test` | Run the full pytest suite. |
| `make test-fast` | Run the suite excluding `slow` markers. |
| `make eval` | Run the O&G evaluation script (requires the API up). |
| `make clean` | Remove `__pycache__/`, `.pytest_cache/`, build artefacts. |

## Running the O&G evaluation

`eval/og_eval_dataset.json` contains 5 hand-curated technical questions
spanning safety, operations, regulation, and equipment. The eval script
hits the live API as an authenticated user and reports:

- **Faithfulness** — LLM-as-judge via Groq (does the answer stick to the
  context?).
- **Answer Accuracy** — embedding cosine similarity between the answer
  and the ground truth.
- **Citation Precision** — fraction of cited documents that actually
  exist in the database.
- **Context Precision** — best semantic similarity between retrieved
  chunks and the ground truth.
- **Structure heuristics** — has `respuesta_tecnica`, non-empty
  `fuentes`, `score_global_confianza` in `[0, 1]`, and a correct
  `necesita_revision_humana` flag.

```bash
export PETROQUERY_API_URL=http://localhost:8000
export EVAL_USERNAME=evaluator
export EVAL_PASSWORD=evaluator123
export EVAL_EMAIL=evaluator@petroquery.local
make eval
# or: python scripts/evaluate_petroquery.py
```

A timestamped JSON report is written to `eval/results_YYYYMMDD_HHMMSS.json`.

## Testing

```bash
make test          # full suite
make test-fast     # skip the slow markers
```

The suite covers the seams that matter:

- `test_config.py` — `SECRET_KEY` handling, CORS parsing, env validation.
- `test_auth.py` — JWT issuing, password hashing (argon2), role checks.
- `test_hybrid_search.py` — RRF score fusion and ranking.
- `test_number_validator.py` — regression cases on numeric substrings.
- `test_pii_masker.py` — masking that preserves O&G proper nouns.
- `test_prompt_injection_guard.py` — guard triggers.
- `test_hse_protocol.py` — safety-warning emission.
- `tests/rag/` — pipeline stages and shared types, exercised in isolation.
- `tests/persistence/` — repository layer.

## Project layout

```
petroquery/
├── app/
│   ├── api/v1/              # Routers: auth, chat, chats, ingest,
│   │                        #          projects, admin, audits
│   ├── config.py            # Pydantic settings + production guards
│   ├── database.py          # Async SQLAlchemy engine
│   ├── models.py            # SQLAlchemy + pgvector (1024-d)
│   ├── prompts/             # O&G-specialized system prompts
│   ├── schemas/             # Pydantic schemas (OGTechnicalAnswer, …)
│   └── services/
│       ├── rag/             # Modular RAG pipeline
│       │   ├── pipeline.py          # ← single entry point
│       │   ├── classification.py    # stage 1
│       │   ├── retrieval.py         # stage 2 (hybrid + RRF)
│       │   ├── reranking.py         # stage 3 (cross-encoder)
│       │   ├── context.py           # stage 3b (assemble trimmed context)
│       │   ├── generation.py        # stage 4 (instructor + Pydantic)
│       │   ├── validation.py        # stage 5 (numeric + structure)
│       │   └── types.py             # shared dataclasses
│       ├── persistence/     # Repositories: chat, audit, project
│       ├── ai_service.py    # Shared AIService (Groq, embeddings, …)
│       ├── hybrid_search.py # Hybrid search + RRF primitive
│       ├── document_processor.py  # PDF ingestion, table-aware chunking
│       ├── number_validator.py
│       ├── pii_masker.py
│       ├── prompt_injection_guard.py
│       └── hse_protocol.py
├── eval/
│   └── og_eval_dataset.json # 5 curated O&G questions + ground truth
├── scripts/
│   ├── init_petroquery_db.py        # Destructive schema init
│   ├── evaluate_petroquery.py       # Eval runner
│   ├── run_full_evaluation.py
│   ├── generate_test_pdfs.py
│   └── monitor.py
├── tests/                   # pytest (config, auth, services, rag, persistence)
├── frontend/                # Next.js 16 App Router
│   └── app/                 # chat · admin · manual · projects · auth
├── docs/
│   ├── ARCHITECTURE.md
│   └── OG_SPECIALIZATION.md
├── docker-compose.yml       # PostgreSQL + pgvector
├── Makefile
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## Deep dives

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — full system architecture.
- [`docs/OG_SPECIALIZATION.md`](docs/OG_SPECIALIZATION.md) — how generic
  RAG was adapted to O&G (chunking, schema, prompt design).

## Roadmap

- **Multi-document cross-citations** — one answer citing several manuals
  with per-source relevance ranking.
- **SCADA / live well data** — enrich answers with real-time well
  readings over OPC-UA or MQTT.
- **Local models** — Llama 3.3 70B via vLLM for offline camp operations.
- **SOC 2 / ISO 27001** — stronger auth, query auditing, encryption
  in transit and at rest.
- **Extended multilingual support** — Portuguese for Pre-Sal operations.

## Contributing & contact

PetroQuery is a portfolio project aimed at hiring managers and operations
engineers in the Vaca Muerta ecosystem (YPF, Tecpetrol, PAE, and the
surrounding service companies). For technical questions or collaboration
proposals, open an issue.

## License

Technical demonstration project. Released under the MIT license.
