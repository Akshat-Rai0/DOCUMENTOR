from typing import Any

from sentence_transformers import CrossEncoder

_RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_RERANKER_MODEL: CrossEncoder | None = None


def _get_reranker_model() -> CrossEncoder:
    global _RERANKER_MODEL
    if _RERANKER_MODEL is None:
        _RERANKER_MODEL = CrossEncoder(_RERANKER_MODEL_NAME)
    return _RERANKER_MODEL


def rerank_candidates(
    query: str,
    candidates: list[dict[str, Any]],
    top_k: int = 3,
    enabled: bool = True,
) -> list[dict[str, Any]]:
    if not candidates:
        return []

    if not enabled:
        return candidates[:top_k]

    try:
        reranker = _get_reranker_model()
        pairs = [(query, candidate.get("text", "")) for candidate in candidates]
        scores = reranker.predict(pairs)
    except Exception:
        return candidates[:top_k]

    reranked: list[dict[str, Any]] = []
    for candidate, score in zip(candidates, scores):
        enriched = dict(candidate)
        enriched["reranker_score"] = float(score)
        reranked.append(enriched)

    reranked.sort(key=lambda x: x.get("reranker_score", 0.0), reverse=True)
    return reranked[:top_k]
