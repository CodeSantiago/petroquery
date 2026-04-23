from typing import Optional

import groq
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder

from app.config import get_settings


class AIService:
    def __init__(self) -> None:
        settings = get_settings()
        self._embedding_model: Optional[SentenceTransformer] = None
        self._cross_encoder: Optional[CrossEncoder] = None
        self._groq_client = groq.AsyncGroq(api_key=settings.groq_api_key)

    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return self._embedding_model

    @property
    def cross_encoder(self) -> CrossEncoder:
        if self._cross_encoder is None:
            self._cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        return self._cross_encoder

    async def get_embedding(self, text: str) -> list[float]:
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    async def rerank_chunks(
        self, query: str, chunks: list[dict], top_k: int = 4
    ) -> list[dict]:
        if not chunks:
            return []
        
        pairs = [(query, chunk["content"]) for chunk in chunks]
        
        scores = self.cross_encoder.predict(pairs)
        
        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = float(scores[i])
        
        sorted_chunks = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
        
        return sorted_chunks[:top_k]

    async def generate_hypothetical_answer(self, question: str) -> str:
        prompt = f"""Genera una respuesta BREVE y DIRECTA (máximo 2 párrafos) a la siguiente pregunta.
No necesitas ser perfecto, solo genera una respuesta plausible que podría estar en un documento.

Pregunta: {question}

Respuesta hipotética:"""

        chat_completion = await self._groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
            max_tokens=300,
        )

        return chat_completion.choices[0].message.content or ""

    async def ask_groq(self, context: str, question: str) -> str:
        prompt = f"""Eres un asistente que responde preguntas basándote EXCLUSIVAMENTE en el contexto proporcionado.
- Sé conciso y directo en tu respuesta.
- Si no tienes información suficiente, indica que no puedes responder.

Contexto:
{context}

Pregunta: {question}

Respuesta:"""

        chat_completion = await self._groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=500,
        )

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

        chat_completion = await self._groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=500,
        )

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


_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service