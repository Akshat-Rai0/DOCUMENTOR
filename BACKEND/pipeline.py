from typing import Any, Optional

from intent_classifier import classify_intent
from llm import disambiguate_intent_with_local_llm, generate_grounded_answer
from reranker import rerank_candidates
from retriever import hybrid_retrieve


def _serialize_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for rank, chunk in enumerate(chunks, start=1):
        score = (
            chunk.get("reranker_score")
            if chunk.get("reranker_score") is not None
            else chunk.get("rrf_score", 0.0)
        )
        serialized.append(
            {
                "chunk_id": str(chunk.get("chunk_id", "")),
                "score": float(score),
                "text": chunk.get("text", ""),
                "source_url": chunk.get("source_url"),
                "function_name": chunk.get("function_name"),
                "rank": rank,
            }
        )
    return serialized


def run_rag_pipeline(
    query: str,
    source_url: Optional[str] = None,
    use_reranker: bool = True,
) -> dict[str, Any]:
    query_text = query.strip()
    if not query_text:
        raise ValueError("Query cannot be empty.")

    intent_result = classify_intent(
        query_text,
        llm_disambiguator=disambiguate_intent_with_local_llm,
    )

    retrieval_payload = hybrid_retrieve(
        query=query_text,
        source_url=source_url,
        semantic_top_k=10,
        bm25_top_k=10,
        fused_top_k=5,
        rrf_k=60,
    )
    fused_chunks = retrieval_payload.get("fused_results", [])

    final_chunks = rerank_candidates(
        query=query_text,
        candidates=fused_chunks,
        top_k=3,
        enabled=use_reranker,
    )

    llm_answer = generate_grounded_answer(
        query=query_text,
        intent=intent_result.intent,
        chunks=final_chunks,
    )

    explanation = llm_answer.get("explanation") or "The answer is not in the retrieved documentation chunks."
    response_payload: dict[str, Any] = {
        "status": "success",
        "intent": intent_result.intent,
        "processed_content": explanation,
        "recommended_functions": llm_answer.get("recommended_functions", []),
        "use_when": llm_answer.get("use_when", []),
        "avoid_when": llm_answer.get("avoid_when", []),
        "code_snippet": llm_answer.get("code_snippet", ""),
        "source_url": llm_answer.get("source_url") or source_url,
        "confidence": float(llm_answer.get("confidence", 0.0)),
        "explanation": explanation,
        "fixes": llm_answer.get("fixes", []),
        "retrieved_chunks": _serialize_chunks(final_chunks),
    }
    return response_payload
