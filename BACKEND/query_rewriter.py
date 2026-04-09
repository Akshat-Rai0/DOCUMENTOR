"""
query_rewriter.py — Query expansion for improved retrieval recall.

Fixes Issue #7: before retrieval, expands a user query into 3 search-friendly
variants using the local LLM, then retrieves for all variants and merges results.
"""

import json
from typing import List

from llm import _call_local_model, _extract_json_object


def expand_query(query: str, max_variants: int = 3) -> List[str]:
    """
    Expand a user query into multiple search-friendly variants.

    Returns the original query plus up to `max_variants` rephrased versions.
    On failure, returns just the original query.
    """
    prompt = (
        f"Rewrite the following developer query into {max_variants} different search-friendly variants.\n"
        "Each variant should emphasise different keywords or phrasings.\n"
        "Return strict JSON: {\"variants\": [\"variant1\", \"variant2\", \"variant3\"]}\n\n"
        f"Query: {query}"
    )

    try:
        text = _call_local_model(
            system_prompt="You are a query expansion assistant. Return only JSON.",
            user_prompt=prompt,
            max_tokens=200,
            json_mode=True,
        )
        parsed = _extract_json_object(text)
        variants = parsed.get("variants", [])
        if isinstance(variants, list) and variants:
            # Always include original query first
            result = [query]
            for v in variants[:max_variants]:
                v_str = str(v).strip()
                if v_str and v_str != query:
                    result.append(v_str)
            return result
    except Exception:
        pass

    return [query]
