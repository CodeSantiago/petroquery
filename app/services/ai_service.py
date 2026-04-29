from typing import Optional

import asyncio

import groq
from groq import RateLimitError as GroqRateLimitError
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder
import instructor

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

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0


async def _retry_on_rate_limit(coro, max_retries: int = MAX_RETRIES):
    for attempt in range(max_retries):
        try:
            return await coro()
        except GroqRateLimitError as e:
            if attempt == max_retries - 1:
                raise
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"[RATE_LIMIT] Rate limit alcanzado, reintentando en {delay}s (intento {attempt + 1}/{max_retries})")
            await asyncio.sleep(delay)


class AIService:
    def __init__(self) -> None:
        settings = get_settings()
        self._embedding_model: Optional[SentenceTransformer] = None
        self._cross_encoder: Optional[CrossEncoder] = None
        self._groq_client = groq.AsyncGroq(api_key=settings.groq_api_key)
        self._instructor_client = instructor.from_groq(self._groq_client)

    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            settings = get_settings()
            self._embedding_model = SentenceTransformer(
                "intfloat/multilingual-e5-large",
                use_auth_token=settings.huggingface_token or None,
            )
        return self._embedding_model

    @property
    def cross_encoder(self) -> CrossEncoder:
        if self._cross_encoder is None:
            settings = get_settings()
            import huggingface_hub
            hf_token = settings.huggingface_token or None
            if hf_token:
                huggingface_hub.login(hf_token)
            self._cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        return self._cross_encoder

    def prewarm(self) -> None:
        """Pre-load the embedding model to avoid cold-start delays during evaluation."""
        print("[WARMUP] Pre-cargando modelo E5 (primera carga puede tomar 30-60s)...")
        _ = self.embedding_model
        print("[WARMUP] Modelo E5 cargado.")

    # ------------------------------------------------------------------
    # Embeddings (E5 with prefixes)
    # ------------------------------------------------------------------
    async def get_document_embedding(self, text: str) -> list[float]:
        prefixed = f"passage: {text}"
        embedding = self.embedding_model.encode(prefixed, normalize_embeddings=True)
        return embedding.tolist()

    async def get_query_embedding(self, text: str) -> list[float]:
        prefixed = f"query: {text}"
        embedding = self.embedding_model.encode(prefixed, normalize_embeddings=True)
        return embedding.tolist()

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

        pairs = [(query, chunk.get("content", chunk.get("text", ""))) for chunk in chunks]
        scores = self.cross_encoder.predict(pairs)

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
            return await self._instructor_client.create(
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
