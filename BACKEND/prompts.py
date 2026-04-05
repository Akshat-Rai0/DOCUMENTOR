import json
from typing import Any

SYSTEM_GROUNDING_PROMPT = (
    "Answer ONLY using the provided documentation chunks. "
    "If the answer is not in the chunks, say so. "
    "Do not use general knowledge."
)

INTENT_TEMPLATES = {
    "function_search": (
        "From the docs below, recommend which function(s) solve this. "
        "Include: function name, when to use, when NOT to use, trade-offs, code snippet."
    ),
    "error_fix": (
        "From the docs below, explain the root cause of this error and provide 1–3 fixes with working code."
    ),
    "concept_explain": (
        "From the docs below, explain this concept in simple terms with an example."
    ),
}

RESPONSE_JSON_SHAPE = {
    "recommended_functions": [],
    "use_when": [],
    "avoid_when": [],
    "code_snippet": "",
    "source_url": "",
    "confidence": 0.0,
    "explanation": "",
    "fixes": [],
}


def _format_chunks(chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return "No documentation chunks were retrieved."

    sections: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        sections.append(
            "\n".join(
                [
                    f"[Chunk {index}]",
                    f"id: {chunk.get('chunk_id', '')}",
                    f"source_url: {chunk.get('source_url') or ''}",
                    f"function_name: {chunk.get('function_name') or ''}",
                    f"text:\n{chunk.get('text', '')}",
                ]
            )
        )
    return "\n\n".join(sections)


def build_user_prompt(intent: str, query: str, chunks: list[dict[str, Any]]) -> str:
    template = INTENT_TEMPLATES.get(intent, INTENT_TEMPLATES["function_search"])
    formatted_chunks = _format_chunks(chunks)
    return (
        f"{template}\n\n"
        f"User query:\n{query}\n\n"
        f"Documentation chunks:\n{formatted_chunks}\n\n"
        "Return ONLY valid JSON matching this shape exactly:\n"
        f"{json.dumps(RESPONSE_JSON_SHAPE, indent=2)}"
    )
