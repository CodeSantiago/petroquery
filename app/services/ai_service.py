"""Shared AI service used by the chat pipeline.

The service is intentionally split in two layers:

* **Always available** (Groq LLM client, structured generation, number
  validation helpers, prompt-injection guard, HSE protocol) — these are
  pure-Python and do not require the optional ML stack.
* **Lazily loaded** (sentence-transformers embedding model, cross-encoder
  reranker) — the heavy ML packages are only imported the first time an
  embedding/rerank call is made. If the ML stack is not installed the
  service still boots; calls to ``get_*_embedding`` or ``rerank_chunks``
  raise :class:`MLRuntimeUnavailable` with a clear remediation message
  instead of crashing the process.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

# NOTE: ``groq`` and ``instructor`` are imported lazily so the API process
# can boot on hosts that do not have the ML stack installed (CI runners,
# smoke tests, health-only deployments, or any host that only exercises
# the auth/CRUD surface). Native crashes on Windows during the import
# of ``instructor`` (which pulls in pandas -> pyarrow) used to kill the
# whole process at startup; lazy imports keep the heavy stack out of the
# request path until an actual RAG call needs it.
from app.config import get_settings
from app.prompts.system_prompts import (
    SYSTEM_PROMPT_OG,
    PROMPT_OPERACIONAL,
    PROMPT_NORMATIVA,
    PROMPT_SEGURIDAD,
    PROMPT_EQUIPOS,
    CLASSIFY_QUERY_PROMPT,
)
from app.schemas.og_schemas import OGTechnicalAnswer
from app.services.pii_masker import PIIMasker
from app.services.number_validator import extract_technical_numbers, validate_numbers_against_chunks
from app.services.hse_protocol import is_hse_query, hse_hard_stop

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0


class MLRuntimeUnavailable(RuntimeError):
    """Raised when an AI call needs the optional ML stack and it is missing.

    The error message always points to ``requirements-ml.txt`` so the
    operator can fix the host without reading the stack trace.
    """


async def _retry_on_rate_limit(coro, max_retries: int = MAX_RETRIES):
    # Imported lazily so the API process can boot on hosts that do not
    # have the ``groq`` SDK installed (CI, health-only deployments).
    from groq import RateLimitError as GroqRateLimitError

    for attempt in range(max_retries):
        try:
            return await coro()
        except GroqRateLimitError:
            if attempt == max_retries - 1:
                raise
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"[RATE_LIMIT] Rate limit alcanzado, reintentando en {delay}s (intento {attempt + 1}/{max_retries})")
            await asyncio.sleep(delay)


class AIService:
    """Lazy, fault-tolerant AI service.

    Heavy ML models (sentence-transformers, cross-encoders) are loaded
    on first use. If the import fails — typically because
    ``requirements-ml.txt`` has not been installed on this host — the
    failure is recorded on the instance and surfaced as a clear
    :class:`MLRuntimeUnavailable` error so the API can answer with an
    HTTP 503 instead of crashing with a native access violation.
    """

    def __init__(self) -> None:
        settings = get_settings()
        # The Groq client is the only eagerly constructed collaborator.
        # ``groq`` is a small pure-Python HTTP client and does not pull
        # in any heavy native stack at import time.
        import groq
        self._groq_client = groq.AsyncGroq(api_key=settings.groq_api_key)

        # ``instructor`` is lazy: it transitively imports pandas /
        # pyarrow which can crash the process on Windows hosts that do
        # not have a working pyarrow wheel. The client is created the
        # first time ``ask_og_structured`` is called and the failure is
        # recorded on the instance so the second call surfaces the same
        # 503 with a clear remediation message.
        self._instructor_client: Optional[Any] = None
        self._instructor_error: Optional[str] = None

        # Heavy ML collaborators — populated on first use.
        self._embedding_model: Optional[Any] = None
        self._cross_encoder: Optional[Any] = None
        self._embedding_error: Optional[str] = None
        self._cross_encoder_error: Optional[str] = None

    # ------------------------------------------------------------------
    # ML loading
    # ------------------------------------------------------------------
    def _load_instructor_client(self) -> Any:
        """Return the instructor-wrapped Groq client, building it on first use.

        Raises :class:`MLRuntimeUnavailable` with a clear remediation
        message when the optional ML stack is not installed. The failure
        is cached on the instance so subsequent calls return the same
        503 instead of re-importing the broken stack.
        """
        if self._instructor_client is not None:
            return self._instructor_client
        if self._instructor_error is not None:
            raise MLRuntimeUnavailable(self._instructor_error)
        try:
            import instructor
            self._instructor_client = instructor.from_groq(self._groq_client)
            return self._instructor_client
        except Exception as exc:  # ImportError or native load failure
            self._instructor_error = (
                "instructor unavailable. Structured generation requires "
                "the optional ML stack. Install it with "
                "`pip install -r requirements-ml.txt` (or "
                "`pip install -r requirements-windows.txt` on Windows). "
                f"Root cause: {type(exc).__name__}: {exc}"
            )
            logger.error(self._instructor_error)
            raise MLRuntimeUnavailable(self._instructor_error) from exc

    def _load_embedding_model(self) -> Any:
        """Import and instantiate the embedding model.

        Returns the cached model on subsequent calls. Raises
        :class:`MLRuntimeUnavailable` with a clear remediation message
        when the ML stack is not installed.
        """
        if self._embedding_model is not None:
            return self._embedding_model
        if self._embedding_error is not None:
            raise MLRuntimeUnavailable(self._embedding_error)
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:  # ImportError or native load failure
            self._embedding_error = (
                "Embedding model unavailable: sentence-transformers could "
                "not be imported. Install the optional ML stack with "
                "`pip install -r requirements-ml.txt`. Root cause: "
                f"{type(exc).__name__}: {exc}"
            )
            logger.error(self._embedding_error)
            raise MLRuntimeUnavailable(self._embedding_error) from exc

        try:
            settings = get_settings()
            self._embedding_model = SentenceTransformer(
                "intfloat/multilingual-e5-large",
                use_auth_token=settings.huggingface_token or None,
            )
            return self._embedding_model
        except Exception as exc:
            self._embedding_error = (
                "Embedding model failed to load (corrupt cache, OOM, or "
                "missing native deps). Try `pip install -r requirements-ml.txt` "
                "and clear the Hugging Face cache. Root cause: "
                f"{type(exc).__name__}: {exc}"
            )
            logger.error(self._embedding_error)
            raise MLRuntimeUnavailable(self._embedding_error) from exc

    def _load_cross_encoder(self) -> Any:
        """Import and instantiate the cross-encoder reranker."""
        if self._cross_encoder is not None:
            return self._cross_encoder
        if self._cross_encoder_error is not None:
            raise MLRuntimeUnavailable(self._cross_encoder_error)
        try:
            from sentence_transformers import CrossEncoder
        except Exception as exc:
            self._cross_encoder_error = (
                "Cross-encoder unavailable: sentence-transformers could not "
                "be imported. Install the optional ML stack with "
                "`pip install -r requirements-ml.txt`. Root cause: "
                f"{type(exc).__name__}: {exc}"
            )
            logger.error(self._cross_encoder_error)
            raise MLRuntimeUnavailable(self._cross_encoder_error) from exc

        try:
            settings = get_settings()
            import huggingface_hub
            hf_token = settings.huggingface_token or None
            if hf_token:
                huggingface_hub.login(hf_token)
            self._cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            return self._cross_encoder
        except Exception as exc:
            self._cross_encoder_error = (
                "Cross-encoder failed to load. Install the optional ML stack "
                "with `pip install -r requirements-ml.txt` and clear the "
                "Hugging Face cache. Root cause: "
                f"{type(exc).__name__}: {exc}"
            )
            logger.error(self._cross_encoder_error)
            raise MLRuntimeUnavailable(self._cross_encoder_error) from exc

    @property
    def embedding_model(self) -> Any:
        return self._load_embedding_model()

    @property
    def cross_encoder(self) -> Any:
        return self._load_cross_encoder()

    def prewarm(self) -> None:
        """Pre-load the embedding model to avoid cold-start delays during evaluation.

        When the ML stack is missing, this logs a warning and returns
        instead of crashing the process.
        """
        try:
            print("[WARMUP] Pre-cargando modelo E5 (primera carga puede tomar 30-60s)...")
            _ = self.embedding_model
            print("[WARMUP] Modelo E5 cargado.")
        except MLRuntimeUnavailable as exc:
            print(f"[WARMUP] Modelo no disponible, prewarm omitido: {exc}")

    # ------------------------------------------------------------------
    # Embeddings (E5 with prefixes)
    # ------------------------------------------------------------------
    async def get_document_embedding(self, text: str) -> list[float]:
        model = self._load_embedding_model()
        prefixed = f"passage: {text}"
        # sentence-transformers .encode is a blocking call; run it in a
        # worker thread so we do not stall the event loop.
        #
        # NOTE: the ``normalize_embeddings`` flag MUST be passed as a
        # keyword argument. The encode() signature in sentence-transformers
        # >= 5.0 is ``encode(inputs, prompt_name=None, prompt=None, ...)``,
        # so a positional dict would be interpreted as ``prompt_name`` and
        # raise ``TypeError: unhashable type: 'dict'`` from inside the
        # model's ``_resolve_prompt`` helper.
        embedding = await asyncio.to_thread(
            model.encode, [prefixed], normalize_embeddings=True
        )
        return embedding[0].tolist()

    async def get_query_embedding(self, text: str) -> list[float]:
        model = self._load_embedding_model()
        prefixed = f"query: {text}"
        embedding = await asyncio.to_thread(
            model.encode, [prefixed], normalize_embeddings=True
        )
        return embedding[0].tolist()

    # Backward-compatible alias
    async def get_embedding(self, text: str) -> list[float]:
        return await self.get_document_embedding(text)

    # ------------------------------------------------------------------
    # Reranking
    # ------------------------------------------------------------------
    async def rerank_chunks(
        self, query: str, chunks: list[dict], top_k: int = 4
    ) -> list[dict]:
        if not chunks:
            return []

        model = self._load_cross_encoder()
        pairs = [(query, chunk.get("content", chunk.get("text", ""))) for chunk in chunks]
        scores = await asyncio.to_thread(model.predict, pairs)

        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = float(scores[i])

        sorted_chunks = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
        return sorted_chunks[:top_k]

    # ------------------------------------------------------------------
    # Query classification
    # ------------------------------------------------------------------
    async def classify_query_type(self, question: str) -> str:
        if is_hse_query(question):
            return "seguridad"

        prompt = CLASSIFY_QUERY_PROMPT.format(question=question)

        async def _call():
            return await self._groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=20,
            )

        chat_completion = await _retry_on_rate_limit(_call)
        result = (chat_completion.choices[0].message.content or "").strip().lower()
        valid = {"operacional", "normativa", "seguridad", "equipos", "general"}
        for v in valid:
            if v in result:
                return v
        return "general"

    # ------------------------------------------------------------------
    # Structured output via Instructor
    # ------------------------------------------------------------------
    def _select_system_prompt(self, query_type: str) -> str:
        if query_type == "operacional":
            return PROMPT_OPERACIONAL
        if query_type == "normativa":
            return PROMPT_NORMATIVA
        if query_type == "seguridad":
            return PROMPT_SEGURIDAD
        if query_type == "equipos":
            return PROMPT_EQUIPOS
        return SYSTEM_PROMPT_OG

    async def ask_og_structured(
        self,
        context: str,
        question: str,
        history: str = "",
        query_type: str = "general",
    ) -> OGTechnicalAnswer:
        system_prompt = self._select_system_prompt(query_type)

        # Mask PII before sending to LLM
        safe_context = PIIMasker.mask(context)
        safe_history = PIIMasker.mask(history) if history else history

        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
        ]
        if safe_history:
            messages.append({
                "role": "system",
                "content": f"Historial de conversación previa:\n{safe_history}",
            })

        messages.append({
            "role": "user",
            "content": (
                f"Contexto proporcionado:\n{safe_context}\n\n"
                f"Pregunta técnica: {question}\n\n"
                "Responde en español siguiendo el formato estructurado requerido."
            ),
        })

        async def _call_groq():
            client = self._load_instructor_client()
            return await client.create(
                response_model=OGTechnicalAnswer,
                messages=messages,
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_retries=2,
            )

        answer = await _retry_on_rate_limit(_call_groq)
        print("[AI] Usando Groq Llama 3.3 70B Versatile")

        # Apply HSE hard-stop rules
        answer_dict = answer.model_dump()
        answer_dict["tipo_consulta"] = query_type
        answer_dict = hse_hard_stop(answer_dict)

        return OGTechnicalAnswer(**answer_dict)

    # ------------------------------------------------------------------
    # Number validation
    # ------------------------------------------------------------------
    def validate_answer_numbers(self, answer: OGTechnicalAnswer, context_chunks: list[str]) -> dict:
        """Extract technical numbers from answer and validate against source chunks."""
        numbers = extract_technical_numbers(answer.respuesta_tecnica or "")
        if not numbers:
            return {"all_verified": True, "details": [], "verified_count": 0, "total_count": 0}
        return validate_numbers_against_chunks(numbers, context_chunks)

    # ------------------------------------------------------------------
    # Legacy methods (kept for backward compatibility)
    # ------------------------------------------------------------------
    async def generate_hypothetical_answer(self, question: str) -> str:
        prompt = f"""Genera una respuesta BREVE y DIRECTA (máximo 2 párrafos) a la siguiente pregunta.
No necesitas ser perfecto, solo genera una respuesta plausible que podría estar en un documento.

Pregunta: {question}

Respuesta hipotética:"""

        async def _call():
            return await self._groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.7,
            )

        chat_completion = await _retry_on_rate_limit(_call)
        return chat_completion.choices[0].message.content or ""

    async def ask_groq(self, context: str, question: str) -> str:
        prompt = f"""Eres un asistente de trivia. Responde PRECISAMENTE a la pregunta usando la información del contexto.
- Usa solo la información del contexto
- Si la respuesta está en el contexto, respóndela directamente
- NO digas "no puedo" o "no tengo información" si hay datos relacionados

Contexto:
{context}

Pregunta: {question}

Respuesta:"""

        async def _call():
            return await self._groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.3,
            )

        chat_completion = await _retry_on_rate_limit(_call)
        return chat_completion.choices[0].message.content or "No se pudo generar una respuesta."

    async def ask_groq_with_history(self, context: str, question: str, history: str = "") -> str:
        messages = [
            {
                "role": "system",
                "content": "Eres un asistente que responde preguntas basándote EXCLUSIVAMENTE en el contexto proporcionado. Sé conciso y directo. Si no tienes información suficiente, indica que no puedes responder."
            }
        ]
        if history:
            messages.append({
                "role": "system",
                "content": f"Historial de conversación previa:\n{history}"
            })
        messages.append({
            "role": "user",
            "content": f"Contexto:\n{context}\n\nPregunta: {question}"
        })

        chat_completion = await self._groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=500,
        )
        return chat_completion.choices[0].message.content or "No se pudo generar una respuesta."

    async def ask_groq_with_history_tokens(self, context: str, question: str, history: str = "") -> tuple[str, int, int]:
        messages = [
            {
                "role": "system",
                "content": "Eres un asistente que responde preguntas basándote EXCLUSIVAMENTE en el contexto proporcionado. Sé conciso y directo. Si no tienes información suficiente, indica que no puedes responder."
            }
        ]
        if history:
            messages.append({
                "role": "system",
                "content": f"Historial de conversación previa:\n{history}"
            })
        messages.append({
            "role": "user",
            "content": f"Contexto:\n{context}\n\nPregunta: {question}"
        })

        async def _call():
            return await self._groq_client.chat.completions.create(
                messages=messages,
                model="llama-3.1-8b-instant",
                temperature=0.3,
            )

        chat_completion = await _retry_on_rate_limit(_call)
        usage = chat_completion.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        return chat_completion.choices[0].message.content or "No se pudo generar una respuesta.", input_tokens, output_tokens

    async def ask_groq_no_context(self, prompt: str) -> str:
        chat_completion = await self._groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=50,
        )
        return chat_completion.choices[0].message.content or ""

    async def evaluate_need_for_retrieval(self, question: str) -> str:
        prompt = f"""Determina si necesitas buscar información externa para responder esta pregunta.
Responde EXACTAMENTE con una de estas palabras:
- "RETRIEVE" si la pregunta requiere información específica de documentos o datos externos
- "NO_RETRIEVE" si puedes responder con conocimiento general

Pregunta: {question}

Respuesta:"""

        async def _call():
            return await self._groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=10,
            )

        chat_completion = await _retry_on_rate_limit(_call)
        result = chat_completion.choices[0].message.content or ""
        return "RETRIEVE" if "RETRIEVE" in result.upper() else "NO_RETRIEVE"

    async def evaluate_context_relevance(self, context: str, question: str) -> float:
        prompt = f"""Evalúa si el contexto proporcionado es RELEVANTE para responder la pregunta.
Responde solo con un número entre 0 y 1:
- 1.0 = El contexto es muy relevante y responde la pregunta
- 0.5 = El contexto es parcialmente relevante
- 0.0 = El contexto no es relevante

Contexto: {context[:1500]}
Pregunta: {question}

Responde solo con el número:"""

        async def _call():
            return await self._groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=10,
            )

        chat_completion = await _retry_on_rate_limit(_call)
        result = chat_completion.choices[0].message.content or "0"
        try:
            return float(result.strip())
        except Exception:
            return 0.0

    async def is_answer_supported(self, answer: str, context: str) -> bool:
        prompt = f"""Determina si la respuesta está soportada por el contexto proporcionado.
Responde solo con "SI" o "NO".

Contexto: {context[:2000]}
Respuesta: {answer}

¿La respuesta usa información del contexto?:"""

        async def _call():
            return await self._groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=10,
            )

        chat_completion = await _retry_on_rate_limit(_call)
        result = chat_completion.choices[0].message.content or ""
        return "SI" in result.upper() or "YES" in result.upper()

    async def self_rag_answer(
        self,
        question: str,
        retrieved_contexts: list[str],
        original_chunks: list[dict],
    ) -> tuple[str, list[dict], dict]:
        contexts_text = "\n\n".join(retrieved_contexts)
        need_retrieval = await self.evaluate_need_for_retrieval(question)

        if need_retrieval == "NO_RETRIEVE" or not retrieved_contexts:
            answer = await self.ask_groq(contexts_text, question)
            return answer, [], {"need_retrieval": False, "context_relevance": 1.0, "is_supported": True}

        relevant_chunks = []
        relevances = []
        for ctx, chunk in zip(retrieved_contexts, original_chunks):
            relevance = await self.evaluate_context_relevance(ctx, question)
            relevances.append(relevance)
            if relevance >= 0.3:
                relevant_chunks.append(chunk)

        if not relevant_chunks:
            best_chunk = original_chunks[0] if original_chunks else {"content": ""}
            answer = await self.ask_groq(best_chunk["content"], question)
            return answer, relevant_chunks, {
                "need_retrieval": True,
                "context_relevance": max(relevances) if relevances else 0,
                "is_supported": True,
            }

        final_context = "\n\n".join([c["content"] for c in relevant_chunks])
        answer = await self.ask_groq(final_context, question)
        is_supported = await self.is_answer_supported(answer, final_context)

        if not is_supported and len(original_chunks) > len(relevant_chunks):
            additional_chunks = [c for c in original_chunks if c not in relevant_chunks][:3]
            for chunk in additional_chunks:
                relevance = await self.evaluate_context_relevance(chunk["content"], question)
                if relevance >= 0.4:
                    relevant_chunks.append(chunk)
            if len(relevant_chunks) > len(original_chunks[:len(relevant_chunks)]):
                final_context = "\n\n".join([c["content"] for c in relevant_chunks])
                answer = await self.ask_groq(final_context, question)

        metadata = {
            "need_retrieval": True,
            "context_relevance": max(relevances) if relevances else 0,
            "is_supported": is_supported,
            "chunks_used": len(relevant_chunks),
            "total_chunks": len(original_chunks),
        }
        return answer, relevant_chunks, metadata


_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


def reset_ai_service() -> None:
    """Drop the cached service. Intended for tests that swap the API key."""
    global _ai_service
    _ai_service = None


__all__ = [
    "AIService",
    "MLRuntimeUnavailable",
    "get_ai_service",
    "reset_ai_service",
]
