import json
import os
import sys
from datetime import datetime
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


EVAL_QUESTIONS = [
    {
        "question": "¿Qué es la inteligencia artificial?",
        "ground_truth": "La inteligencia artificial es un campo de la informática que busca crear sistemas capaces de realizar tareas que requieren inteligencia humana.",
    },
    {
        "question": "¿Cuáles son los principales tipos de aprendizaje automático?",
        "ground_truth": "Los principales tipos son aprendizaje supervisado, aprendizaje no supervisado y aprendizaje por refuerzo.",
    },
    {
        "question": "¿Cómo funciona el modelo transformer en NLP?",
        "ground_truth": "Los transformers utilizan mecanismos de atención para procesar secuencias completas simultáneamente, permitiendo capturar dependencias a larga distancia.",
    },
    {
        "question": "¿Qué es RAG en el contexto de LLMs?",
        "ground_truth": "RAG (Retrieval-Augmented Generation) es una técnica que combina recuperación de documentos con generación de texto para mejorar la precisión de las respuestas.",
    },
    {
        "question": "¿Cuáles son las ventajas de usar embeddings vectoriales?",
        "ground_truth": "Los embeddings vectoriales permiten representar texto como vectores numéricos que capturan significado semántico, facilitando búsqueda por similitud.",
    },
]


async def run_evaluation():
    from app.services.ai_service import get_ai_service
    from app.services.hybrid_search import hybrid_search, TOP_K as HYBRID_TOP_K

    ai_service = get_ai_service()
    user_id = 1

    eval_data = []
    
    print("Running RAG evaluation...")
    for i, q in enumerate(EVAL_QUESTIONS):
        print(f"  [{i+1}/{len(EVAL_QUESTIONS)}] Processing: {q['question']}")
        
        hyp_answer = await ai_service.generate_hypothetical_answer(q["question"])
        hyp_embedding = await ai_service.get_embedding(hyp_answer)

        results = await hybrid_search(
            db=None,
            query=q["question"],
            query_embedding=hyp_embedding,
            user_id=user_id,
            top_k=HYBRID_TOP_K,
        )

        if not results:
            eval_data.append({
                "question": q["question"],
                "answer": "No se encontró información relevante.",
                "contexts": [],
                "ground_truth": q["ground_truth"],
            })
            continue

        reranked = await ai_service.rerank_chunks(
            query=q["question"],
            chunks=results,
            top_k=4,
        )

        context = "\n\n".join([chunk["content"] for chunk in reranked])
        answer = await ai_service.ask_groq(context, q["question"])

        eval_data.append({
            "question": q["question"],
            "answer": answer,
            "contexts": [chunk["content"] for chunk in reranked],
            "ground_truth": q["ground_truth"],
        })

    print("Calculating metrics...")
    output = await calculate_metrics(eval_data)
    return output


async def calculate_metrics(eval_data: list[dict]) -> dict[str, Any]:
    from app.services.ai_service import get_ai_service
    
    ai_service = get_ai_service()
    metrics_results = []
    
    for item in eval_data:
        question = item["question"]
        answer = item["answer"]
        contexts = item["contexts"]
        ground_truth = item["ground_truth"]
        
        context_text = " ".join(contexts) if contexts else ""
        
        faithfulness_prompt = f"""Evalúa si la respuesta está respaldada por el contexto.
Responde solo con un número entre 0 y 1.

Contexto: {context_text[:1000]}
Respuesta: {answer}

Score (0-1):"""

        faith_score = await ai_service.ask_groq_no_context(faithfulness_prompt)
        
        relevancy_prompt = f"""Evalúa qué tan relevante es la respuesta para la pregunta.
Responde solo con un número entre 0 y 1.

Pregunta: {question}
Respuesta: {answer}

Score (0-1):"""

        relevancy_score = await ai_service.ask_groq_no_context(relevancy_prompt)
        
        try:
            faith_val = float(faith_score.strip().split()[-1].replace(".", "").replace(",", "."))
            faith_val = max(0.0, min(1.0, faith_val))
        except:
            faith_val = 0.5
        
        try:
            relevancy_val = float(relevancy_score.strip().split()[-1].replace(".", "").replace(",", "."))
            relevancy_val = max(0.0, min(1.0, relevancy_val))
        except:
            relevancy_val = 0.5
        
        metrics_results.append({
            "question": question,
            "answer": answer,
            "faithfulness": faith_val,
            "answer_relevancy": relevancy_val,
        })

    faith_scores = [m["faithfulness"] for m in metrics_results]
    relevancy_scores = [m["answer_relevancy"] for m in metrics_results]

    output = {
        "timestamp": datetime.now().isoformat(),
        "total_questions": len(EVAL_QUESTIONS),
        "metrics": {
            "faithfulness": {
                "mean": sum(faith_scores) / len(faith_scores) if faith_scores else 0,
                "std": (sum((x - sum(faith_scores)/len(faith_scores))**2 for x in faith_scores) / len(faith_scores))**0.5 if faith_scores else 0,
            },
            "answer_relevancy": {
                "mean": sum(relevancy_scores) / len(relevancy_scores) if relevancy_scores else 0,
                "std": (sum((x - sum(relevancy_scores)/len(relevancy_scores))**2 for x in relevancy_scores) / len(relevancy_scores))**0.5 if relevancy_scores else 0,
            },
        },
        "per_question": metrics_results,
    }

    return output


async def main():
    print("=" * 50)
    print("RAG Evaluation")
    print("=" * 50)

    results = await run_evaluation()

    output_file = f"rag_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    print(f"Faithfulness:     {results['metrics']['faithfulness']['mean']:.4f} ± {results['metrics']['faithfulness']['std']:.4f}")
    print(f"Answer Relevancy: {results['metrics']['answer_relevancy']['mean']:.4f} ± {results['metrics']['answer_relevancy']['std']:.4f}")
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()