import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional

import httpx

from prompts import SYSTEM_GROUNDING_PROMPT, build_user_prompt
from parser import _detect_injection

logger = logging.getLogger(__name__)

_ALLOWED_INTENTS = {"function_search", "error_fix", "concept_explain"}

# Issue #12 — query failure / low-confidence logging. One JSON line per
# query, appended to a local file. This is deliberately append-only and
# best-effort: a logging failure should never break the actual answer path,
# so every write is wrapped and swallowed on error.
_LOW_CONFIDENCE_THRESHOLD = 0.4

try:
    from vector_store import DATA_DIR
    _QUERY_LOG_PATH = Path(DATA_DIR) / "query_log.jsonl"
except Exception:
    # Fallback if vector_store isn't importable in this context (e.g. tests) —
    # log next to this file instead of failing query logging entirely.
    _QUERY_LOG_PATH = Path(__file__).resolve().parent / "query_log.jsonl"


def _log_query_result(
    *,
    query: str,
    intent: str,
    confidence: float,
    fallback_used: bool,
    chunk_count: int,
    library: Optional[str] = None,
) -> None:
    """
    Append one JSON line describing how a query was answered. This is what
    feeds the eval-harness / retrieval-quality work later — without this,
    there is no record of which queries got low-confidence or fallback
    answers, so failure patterns are invisible until someone manually
    stumbles onto a bad response.
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "intent": intent,
        "library": library,
        "confidence": confidence,
        "low_confidence": confidence < _LOW_CONFIDENCE_THRESHOLD,
        "fallback_used": fallback_used,
        "chunk_count": chunk_count,
    }
    try:
        _QUERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _QUERY_LOG_PATH.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        # Never let logging failures break the actual query path.
        logger.warning("Failed to write query log entry", exc_info=True)

    if entry["low_confidence"] or fallback_used:
        logger.warning(
            f"low_confidence_or_fallback query={query!r} intent={intent} "
            f"confidence={confidence} fallback_used={fallback_used} "
            f"chunk_count={chunk_count} library={library}"
        )


def _local_model_name() -> str:
    return os.getenv("OLLAMA_MODEL", "gamma4")


def _local_model_url() -> str:
    return os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")


def _call_local_model(
    *,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    json_mode: bool,
) -> str:
    payload: dict[str, Any] = {
        "model": _local_model_name(),
        "system": system_prompt,
        "prompt": user_prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": max_tokens,
        },
    }
    if json_mode:
        payload["format"] = "json"

    response = httpx.post(_local_model_url(), json=payload, timeout=180)
    response.raise_for_status()
    data = response.json()
    text = (data.get("response") or "").strip()
    if not text:
        raise ValueError("Local model returned an empty response")
    return text


def _stream_local_model(
    *,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    json_mode: bool,
) -> Generator[str, None, None]:
    """Yield text tokens from Ollama with stream=True."""
    payload: dict[str, Any] = {
        "model": _local_model_name(),
        "system": system_prompt,
        "prompt": user_prompt,
        "stream": True,
        "options": {
            "temperature": 0,
            "num_predict": max_tokens,
        },
    }
    if json_mode:
        payload["format"] = "json"

    with httpx.stream("POST", _local_model_url(), json=payload, timeout=180) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
                token = data.get("response", "")
                if token:
                    yield token
                if data.get("done", False):
                    return
            except json.JSONDecodeError:
                continue


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON object in model response")
    return json.loads(match.group(0))


def _to_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _safe_confidence(value: Any, default: float = 0.0) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = default

    if confidence > 1.0 and confidence <= 100.0:
        confidence = confidence / 100.0
    confidence = max(0.0, min(confidence, 1.0))
    return confidence


def _extract_example(text: str) -> str:
    marker = "Example:"
    if marker in text:
        return text.split(marker, 1)[1].strip()[:900]
    return ""


def _fallback_answer(intent: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    if not chunks:
        return {
            "recommended_functions": [],
            "use_when": [],
            "avoid_when": [],
            "code_snippet": "",
            "source_url": "",
            "confidence": 0.0,
            "explanation": "The answer is not in the retrieved documentation chunks.",
            "fixes": [],
        }

    top_chunk = chunks[0]
    top_text = top_chunk.get("text", "")
    function_name = top_chunk.get("function_name")
    source_url = top_chunk.get("source_url") or ""
    snippet = _extract_example(top_text)
    first_sentence = top_text.split("\n")[0][:220]

    if intent == "error_fix":
        return {
            "recommended_functions": [function_name] if function_name else [],
            "use_when": [],
            "avoid_when": [],
            "code_snippet": snippet,
            "source_url": source_url,
            "confidence": 0.35,
            "explanation": (
                f"Based on the indexed docs: {first_sentence}. "
                "Exact root-cause wording could not be generated from local model output."
            ),
            "fixes": [
                "Match your call with the documented parameter names and accepted value types.",
                "Use the documented example pattern from the retrieved chunk.",
            ],
        }

    if intent == "concept_explain":
        return {
            "recommended_functions": [function_name] if function_name else [],
            "use_when": [],
            "avoid_when": [],
            "code_snippet": snippet,
            "source_url": source_url,
            "confidence": 0.35,
            "explanation": first_sentence or "The concept is not clearly described in the retrieved chunks.",
            "fixes": [],
        }

    return {
        "recommended_functions": [function_name] if function_name else [],
        "use_when": [first_sentence] if first_sentence else [],
        "avoid_when": [
            "Avoid this recommendation when your use-case does not match the retrieved documentation section."
        ],
        "code_snippet": snippet,
        "source_url": source_url,
        "confidence": 0.35,
        "explanation": "Recommendation generated from retrieved docs.",
        "fixes": [],
    }


def _normalize_answer(
    payload: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    top_source = chunks[0].get("source_url") if chunks else ""
    normalized = {
        "recommended_functions": _to_string_list(payload.get("recommended_functions")),
        "use_when": _to_string_list(payload.get("use_when")),
        "avoid_when": _to_string_list(payload.get("avoid_when")),
        "code_snippet": str(payload.get("code_snippet") or ""),
        "source_url": str(payload.get("source_url") or top_source or ""),
        "confidence": _safe_confidence(payload.get("confidence"), default=0.0),
        "explanation": str(payload.get("explanation") or ""),
        "fixes": _to_string_list(payload.get("fixes")),
    }
    return normalized


def disambiguate_intent_with_local_llm(query: str) -> Optional[str]:
    prompt = (
        "Classify this developer query into exactly one intent label and return strict JSON.\n"
        "Allowed labels: function_search, error_fix, concept_explain.\n"
        "JSON format: {\"intent\": \"<label>\"}\n\n"
        f"Query: {query}"
    )

    try:
        text = _call_local_model(
            system_prompt="You are a strict query intent classifier.",
            user_prompt=prompt,
            max_tokens=40,
            json_mode=True,
        )
        parsed = _extract_json_object(text)
        intent = str(parsed.get("intent", "")).strip().lower()
        if intent in _ALLOWED_INTENTS:
            return intent
    except Exception:
        return None

    return None


def generate_grounded_answer(
    query: str,
    intent: str,
    chunks: list[dict[str, Any]],
    library: Optional[str] = None,
) -> dict[str, Any]:
    if not chunks:
        result = _fallback_answer(intent=intent, chunks=chunks)
        _log_query_result(
            query=query, intent=intent, confidence=result["confidence"],
            fallback_used=True, chunk_count=0, library=library,
        )
        return result

    user_prompt = build_user_prompt(intent=intent, query=query, chunks=chunks)

    try:
        text = _call_local_model(
            system_prompt=SYSTEM_GROUNDING_PROMPT,
            user_prompt=user_prompt,
            max_tokens=1000,
            json_mode=True,
        )
        parsed = _extract_json_object(text)
        result = _normalize_answer(parsed, chunks=chunks)
        _log_query_result(
            query=query, intent=intent, confidence=result["confidence"],
            fallback_used=False, chunk_count=len(chunks), library=library,
        )
        return result
    except Exception:
        result = _fallback_answer(intent=intent, chunks=chunks)
        _log_query_result(
            query=query, intent=intent, confidence=result["confidence"],
            fallback_used=True, chunk_count=len(chunks), library=library,
        )
        return result


def _sanitize_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out chunks with potential injection patterns."""
    from parser import _detect_injection
    import re
    safe_chunks = []
    for chunk in chunks:
        text = chunk.get("text", "")
        source_url = chunk.get("source_url", "unknown")
        if not _detect_injection(text):
            safe_chunks.append(chunk)
        else:
            # Log the flag hit for observability
            logger.warning(
                f"Injection pattern detected in chunk from {source_url}. "
                f"Chunk text preview: {text[:200]}..."
            )
    return safe_chunks



def generate_grounded_answer_stream(
    query: str,
    intent: str,
    chunks: list[dict[str, Any]],
    library: Optional[str] = None,
) -> Generator[str, None, None]:
    """Streaming version — yields raw tokens from the LLM."""
    safe_chunks = _sanitize_chunks(chunks)
    if not safe_chunks:
        fallback = _fallback_answer(intent=intent, chunks=chunks)
        _log_query_result(
            query=query, intent=intent, confidence=fallback["confidence"],
            fallback_used=True, chunk_count=0, library=library,
        )
        yield json.dumps(fallback)
        return

    user_prompt = build_user_prompt(intent=intent, query=query, chunks=safe_chunks)

    accumulated = ""
    try:
        for token in _stream_local_model(
            system_prompt=SYSTEM_GROUNDING_PROMPT,
            user_prompt=user_prompt,
            max_tokens=1000,
            json_mode=True,
        ):
            accumulated += token
            yield token

        # Streamed successfully — parse what we accumulated to log the
        # final confidence, same as the non-streaming path does. This is
        # best-effort: if parsing fails here we still log a fallback-shaped
        # entry rather than silently skipping the log for this query.
        try:
            parsed = _extract_json_object(accumulated)
            result = _normalize_answer(parsed, chunks=safe_chunks)
            _log_query_result(
                query=query, intent=intent, confidence=result["confidence"],
                fallback_used=False, chunk_count=len(safe_chunks), library=library,
            )
        except Exception:
            _log_query_result(
                query=query, intent=intent, confidence=0.0,
                fallback_used=True, chunk_count=len(safe_chunks), library=library,
            )
    except Exception:
        fallback = _fallback_answer(intent=intent, chunks=chunks)
        _log_query_result(
            query=query, intent=intent, confidence=fallback["confidence"],
            fallback_used=True, chunk_count=len(chunks), library=library,
        )
        yield json.dumps(fallback)