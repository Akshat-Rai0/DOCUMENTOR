import re
from dataclasses import dataclass
from typing import Callable, Optional

INTENT_FUNCTION_SEARCH = "function_search"
INTENT_ERROR_FIX = "error_fix"
INTENT_CONCEPT_EXPLAIN = "concept_explain"
ALLOWED_INTENTS = {
    INTENT_FUNCTION_SEARCH,
    INTENT_ERROR_FIX,
    INTENT_CONCEPT_EXPLAIN,
}

_ERROR_NAME_RE = re.compile(
    r"^\s*[A-Z][A-Za-z0-9_]*(Error|Exception|Warning|Fault)\b"
)
_TRACEBACK_RE = re.compile(
    r"(traceback \(most recent call last\)|\bfile\s+\".+?\",\s+line\s+\d+|\bexception\b|\berror:)",
    re.IGNORECASE,
)
_CONCEPT_PREFIX_RE = re.compile(
    r"^\s*(how|why|what|when|explain|difference|compare|concept|meaning)\b",
    re.IGNORECASE,
)

_CONCEPT_HINTS = {
    "difference",
    "trade-off",
    "tradeoff",
    "concept",
    "internals",
    "architecture",
    "why",
    "how does",
    "when should",
}
_FUNCTION_HINTS = {
    "(",
    ")",
    "parameter",
    "arguments",
    "api",
    "method",
    "function",
    "which function",
    "best way",
}


@dataclass
class IntentClassification:
    intent: str
    reason: str
    used_llm: bool = False


def _contains_traceback(query: str) -> bool:
    return bool(_TRACEBACK_RE.search(query))


def _starts_with_capital_error_name(query: str) -> bool:
    return bool(_ERROR_NAME_RE.search(query))


def _looks_like_concept_query(query: str) -> bool:
    lowered = query.lower()
    if _CONCEPT_PREFIX_RE.search(query):
        return True
    return any(token in lowered for token in _CONCEPT_HINTS)


def _looks_like_function_query(query: str) -> bool:
    lowered = query.lower()
    return any(token in lowered for token in _FUNCTION_HINTS)


def _is_ambiguous(query: str) -> bool:
    return _looks_like_concept_query(query) and _looks_like_function_query(query)


def classify_intent(
    query: str,
    llm_disambiguator: Optional[Callable[[str], Optional[str]]] = None,
) -> IntentClassification:
    text = query.strip()
    if not text:
        return IntentClassification(
            intent=INTENT_FUNCTION_SEARCH,
            reason="Empty query fallback to function search.",
        )

    if _contains_traceback(text):
        return IntentClassification(
            intent=INTENT_ERROR_FIX,
            reason="Traceback/error pattern detected.",
        )

    if _starts_with_capital_error_name(text):
        return IntentClassification(
            intent=INTENT_ERROR_FIX,
            reason="Query starts with a capitalized error name.",
        )

    if _is_ambiguous(text) and llm_disambiguator:
        llm_intent = llm_disambiguator(text)
        if llm_intent in ALLOWED_INTENTS:
            return IntentClassification(
                intent=llm_intent,
                reason="Ambiguous query resolved with local LLM.",
                used_llm=True,
            )

    if _looks_like_concept_query(text):
        return IntentClassification(
            intent=INTENT_CONCEPT_EXPLAIN,
            reason="Concept-style phrasing detected.",
        )

    return IntentClassification(
        intent=INTENT_FUNCTION_SEARCH,
        reason="Default fallback to function search.",
    )
