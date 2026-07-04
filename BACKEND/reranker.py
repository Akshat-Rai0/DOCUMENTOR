import math
from typing import Any, Optional

from sentence_transformers import CrossEncoder

_RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_RERANKER_MODEL: Optional[CrossEncoder] = None


def _get_reranker_model() -> CrossEncoder:
    global _RERANKER_MODEL
    if _RERANKER_MODEL is None:
        _RERANKER_MODEL = CrossEncoder(_RERANKER_MODEL_NAME)
    return _RERANKER_MODEL


def _sigmoid(x: float) -> float:
    """
    Squash a raw CrossEncoder logit into [0, 1].

    ms-marco-MiniLM-L-6-v2 (like most CrossEncoder rerankers) outputs an
    unbounded logit, not a probability — it can be strongly negative for a
    bad match or well above 1 for a great one. Storing that raw value as
    "reranker_score" and later multiplying by 100 for a "%" display is what
    produced nonsensical values like "score -1126%" or "score 772%" in the
    UI. Passing it through a sigmoid first gives a proper [0, 1] relevance
    score that a "%" label actually means something for.
    """
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        # exp(-x) overflows for very large |x| — the sigmoid limit is 0 or 1
        # depending on the sign, so just return that directly.
        return 0.0 if x < 0 else 1.0


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
        raw_scores = reranker.predict(pairs)
    except Exception:
        return candidates[:top_k]

    reranked: list[dict[str, Any]] = []
    for candidate, raw_score in zip(candidates, raw_scores):
        enriched = dict(candidate)
        # Keep the raw logit around under its own name in case it's useful
        # for debugging/eval later, but reranker_score — the field consumed
        # for display and sorting — is now a normalized [0, 1] value.
        enriched["reranker_score_raw"] = float(raw_score)
        enriched["reranker_score"] = _sigmoid(float(raw_score))
        reranked.append(enriched)

    # Sorting order is unaffected by the sigmoid (it's monotonic), so
    # ranking quality is identical to before — only the displayed
    # magnitude changes.
    reranked.sort(key=lambda x: x.get("reranker_score", 0.0), reverse=True)
    return reranked[:top_k]