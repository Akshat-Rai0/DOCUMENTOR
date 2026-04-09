"""
parser.py — Phase 2 core pipeline (v5)

v5 changes:
  - Issue #3: Uses shared extract_library_name from url_utils
  - Issue #5: Adds adapters for Sphinx, Read the Docs, JSDoc, and NumPy-style
    docstrings alongside the existing MkDocs/FastAPI patterns.

Strategy:
  1. clean_page()    — strip nav/sponsor noise from the plain text
  2. extract_items() — match dotted API names using plain-text patterns
     + Sphinx adapter  (`:py:func:`, `.. function::`, `dl.describe`)
     + RTD adapter      (readthedocs layout markers)
     + JSDoc adapter    (`@param`, `@returns`)
     + NumPy adapter    (`Parameters\n----------`)
  3. For each match, extract params, description, example
  4. map_to_schema() — validate into FunctionSchema
"""

import re
from typing import Optional
from schemas.function import FunctionSchema
from url_utils import extract_library_name


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_JUNK_NAMES = {
    "directly", "decorator", "func", "self", "cls", "args", "kwargs",
    "return", "import", "from", "class", "def", "none", "true", "false",
    "default", "example", "type", "value", "result", "data", "item",
    "response", "request", "handler", "callback", "wrapper", "inner",
    "outer", "helper", "utils", "base", "mixin", "abstract", "bases",
    "source", "note", "read", "more", "about", "skip", "content",
}

# English words that can appear as "params" due to text bleeding
_STOPWORDS = {
    "in", "the", "for", "and", "or", "not", "is", "to", "of", "at",
    "by", "an", "as", "be", "if", "on", "up", "it", "no", "so", "do",
    "my", "we", "us", "vs", "via", "etc", "its", "has", "was", "can",
    "may", "use", "used", "uses", "more", "all", "are", "you", "this",
    "that", "with", "from", "into", "than", "then", "when", "also",
    "will", "have", "been", "they", "http", "str", "int", "bool",
    "none", "true", "false", "list", "dict", "any", "seq",
}


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------

def _is_valid_name(name: str) -> bool:
    if not name or len(name) < 2:
        return False
    if not name[0].isalpha():
        return False
    if name.lower() in _JUNK_NAMES:
        return False
    if "." not in name and name.islower() and len(name) < 5:
        return False
    return True


# ---------------------------------------------------------------------------
# Stage 1 — clean plain text
# ---------------------------------------------------------------------------

_NOISE_LINE_RE = re.compile(
    r"^(sponsor|skip to content|follow\s|join the|subscribe|"
    r"fastapi cloud|newsletter|@fastapi|linkedin|twitter|"
    r"initializing search|back to top|\s*$)",
    re.IGNORECASE,
)

_PUNCT_LINE_RE = re.compile(r"^[¶\-=~\.\,\:\;\|\s]{1,5}$")


def clean_page(plain_text: str) -> tuple[str, list[str]]:
    """
    Clean up plain text from scrape_static().
    Returns (cleaned_text, code_blocks).
    """
    lines = plain_text.splitlines()
    cleaned: list[str] = []
    code_blocks: list[str] = []
    current_code: list[str] = []
    in_code = False

    for line in lines:
        if line.strip().startswith("```"):
            if in_code:
                block = "\n".join(current_code).strip()
                if block:
                    code_blocks.append(block)
                    cleaned.append("__CODE_BLOCK__")
                current_code = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            current_code.append(line)
            continue

        if _NOISE_LINE_RE.match(line.strip()):
            continue
        if _PUNCT_LINE_RE.match(line):
            continue

        cleaned.append(line)

    if current_code:
        block = "\n".join(current_code).strip()
        if block:
            code_blocks.append(block)
            cleaned.append("__CODE_BLOCK__")

    return "\n".join(cleaned), code_blocks


# ---------------------------------------------------------------------------
# Stage 2 — extract items from plain text
# ---------------------------------------------------------------------------

# Pattern A: dotted API name on its own line, optionally followed by ¶
_DOTTED_NAME_RE = re.compile(
    r"^(?P<n>[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*){1,})\s*¶?\s*$",
    re.MULTILINE,
)

# Pattern B: Python def/class (appears in source-code sections)
_DEF_CLASS_RE = re.compile(
    r"^(?P<type>async def|def|class)\s+(?P<n>[a-zA-Z_]\w*)\s*(?P<params>\([^)]{0,400}\))?",
    re.MULTILINE,
)

# -- Issue #5 — Additional adapter patterns -----------------------------------

# Sphinx: .. function:: name(params)  /  .. method::  /  .. class::
_SPHINX_DIRECTIVE_RE = re.compile(
    r"^\.\.\s+(?:py:)?(?:function|method|class|staticmethod|classmethod|module|attribute|data)::\s*"
    r"(?P<n>[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)\s*(?P<params>\([^)]{0,400}\))?",
    re.MULTILINE,
)

# Sphinx cross-references in text: :py:func:`name`, :func:`name`, :meth:`name`
_SPHINX_ROLE_RE = re.compile(
    r":(?:py:)?(?:func|meth|class|attr|data|obj):`~?(?P<n>[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)`",
)

# JSDoc: @param {type} name - description  /  function name(params)
_JSDOC_FUNC_RE = re.compile(
    r"^(?:export\s+)?(?:async\s+)?function\s+(?P<n>[a-zA-Z_$]\w*)\s*(?P<params>\([^)]{0,400}\))?",
    re.MULTILINE,
)
_JSDOC_PARAM_RE = re.compile(
    r"@param\s+(?:\{[^}]*\}\s+)?(?P<name>[a-zA-Z_$]\w*)",
)

# NumPy-style docstring sections
_NUMPY_SECTION_RE = re.compile(
    r"^(?P<section>Parameters|Returns|Raises|Yields|Attributes|Methods|Notes|Examples)\s*\n"
    r"-{3,}",
    re.MULTILINE,
)
_NUMPY_PARAM_LINE_RE = re.compile(
    r"^(?P<name>[a-zA-Z_]\w*)\s*:\s*(?P<type>.+)?$",
)

# Read the Docs: "class reference" or "API reference" heading patterns
_RTD_HEADING_RE = re.compile(
    r"^(?P<n>[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)\s*\((?P<params>[^)]*)\)\s*$",
    re.MULTILINE,
)

# Spaced-out param block: ( * , prefix = "" , tags = None , ... )
_SPACED_PARAMS_RE = re.compile(r"\(\s*[\*\w].*?\)", re.DOTALL)

# Parameter table: TYPE: lines
_PARAM_TABLE_RE = re.compile(
    r"^([a-zA-Z_]\w*)\n(?:(?!TYPE:|DEFAULT:|PARAMETER|DESCRIPTION).*\n)*?TYPE:\s*\S",
    re.MULTILINE,
)


def _extract_params_from_table(text_window: str) -> list[str]:
    """Extract parameter names from MkDocs PARAMETER/DESCRIPTION table."""
    params = []
    table_start = text_window.find("PARAMETER")
    if table_start == -1:
        return []

    table_text = text_window[table_start:]
    lines = table_text.splitlines()

    i = 1
    while i < len(lines):
        line = lines[i].strip()
        if (line
                and re.match(r"^[a-zA-Z_]\w*$", line)
                and line.lower() not in _STOPWORDS
                and line.lower() not in _JUNK_NAMES
                and line not in ("PARAMETER", "DESCRIPTION", "TYPE",
                                 "DEFAULT", "Note", "None", "True", "False")):
            params.append(line)
        if line in ("SOURCE", "RETURNS", "RAISES", "YIELDS",
                     "ATTRIBUTES", "METHODS"):
            break
        i += 1

    return params


def _extract_params_from_signature(sig_text: str) -> list[str]:
    """Extract params from spaced-out signature block."""
    inner = sig_text.strip().lstrip("(").rstrip(")")
    params = []
    for token in inner.split(","):
        token = token.strip().lstrip("*").strip()
        name = re.split(r"[\s=:\(]", token)[0].strip()
        if (name
                and re.match(r"^[a-zA-Z_]\w*$", name)
                and name not in ("self", "cls")
                and name.lower() not in _STOPWORDS
                and name.lower() not in _JUNK_NAMES):
            params.append(name)
    return params


def _extract_numpy_params(text_window: str) -> list[str]:
    """Extract parameter names from NumPy-style docstring sections."""
    params = []
    match = _NUMPY_SECTION_RE.search(text_window)
    if not match or match.group("section") != "Parameters":
        return []

    section_text = text_window[match.end():]
    for line in section_text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Stop at next section header
        if re.match(r"^[A-Z][a-z]+\s*$", line):
            break
        if re.match(r"^-{3,}$", line):
            break
        pm = _NUMPY_PARAM_LINE_RE.match(line)
        if pm:
            name = pm.group("name")
            if (name.lower() not in _STOPWORDS
                    and name.lower() not in _JUNK_NAMES
                    and name not in ("self", "cls")):
                params.append(name)
    return params


def _extract_jsdoc_params(text_window: str) -> list[str]:
    """Extract parameter names from JSDoc @param tags."""
    params = []
    for m in _JSDOC_PARAM_RE.finditer(text_window[:2000]):
        name = m.group("name")
        if name.lower() not in _STOPWORDS and name.lower() not in _JUNK_NAMES:
            params.append(name)
    return params


def _extract_description(text_window: str, max_chars: int = 800) -> Optional[str]:
    """Find the first real prose paragraph after a function heading."""
    skip_re = re.compile(
        r"^(¶|PARAMETER|DESCRIPTION|TYPE:|DEFAULT:|Example|SOURCE|"
        r"Bases:|Read more|Note:|Warning:|__CODE_BLOCK__|"
        r"from\s|import\s|async\s+def\s|def\s|class\s|return\s|"
        r"@\w|#|\`\`\`)",
        re.IGNORECASE,
    )
    punct_only = re.compile(r'^[\(\)\[\]{}\\.,=\*"\'\\s:¶|]{1,8}$')

    snippet = text_window[:max_chars]
    prose = []
    for line in snippet.splitlines():
        s = line.strip()
        if not s:
            if prose:
                break
            continue
        if skip_re.match(s):
            continue
        if punct_only.match(s):
            continue
        if len(s) < 20:
            continue
        prose.append(s)
        if len(prose) >= 3:
            break

    desc = " ".join(prose).strip()
    return desc if len(desc) >= 20 else None


def _nearest_code_block(pos: int, text: str, code_blocks: list[str]) -> Optional[str]:
    placeholder = "__CODE_BLOCK__"
    window = text[pos: pos + 4000]
    idx = window.find(placeholder)
    if idx == -1:
        return None
    preceding = text[:pos + idx].count(placeholder)
    if preceding < len(code_blocks):
        return code_blocks[preceding]
    return None


def extract_items(
    plain_text: str,
    code_blocks: list[str],
    library: str,
    source_url: str,
) -> list[dict]:
    seen: set[str] = set()
    items: list[dict] = []

    # --- Pattern A: dotted names (primary pattern for doc reference pages) ---
    for m in _DOTTED_NAME_RE.finditer(plain_text):
        raw_name = m.group("n")
        if not _is_valid_name(raw_name):
            continue
        short_name = raw_name.split(".")[-1]
        if not _is_valid_name(short_name):
            continue
        if raw_name in seen:
            continue
        seen.add(raw_name)

        parts = raw_name.split(".")
        if len(parts) == 1:
            etype = "function"
        elif parts[-1][0].isupper():
            etype = "class"
        else:
            etype = "method"

        window = plain_text[m.start(): m.start() + 2000]

        params = _extract_params_from_table(window)
        if not params:
            sig_m = _SPACED_PARAMS_RE.search(window)
            if sig_m:
                params = _extract_params_from_signature(sig_m.group(0))
        # Try NumPy-style params
        if not params:
            params = _extract_numpy_params(window)

        desc = _extract_description(plain_text[m.end():])
        example = _nearest_code_block(m.start(), plain_text, code_blocks)

        items.append({
            "type": etype,
            "name": raw_name,
            "library": library,
            "params": params,
            "description": desc,
            "example": example,
            "source_url": source_url,
        })

    # --- Pattern B: def/class (for tutorial/guide pages with code examples) ---
    for m in _DEF_CLASS_RE.finditer(plain_text):
        raw_name = m.group("n")
        if not _is_valid_name(raw_name):
            continue
        key = f"{library}.{raw_name}"
        if key in seen or raw_name in seen:
            continue
        seen.add(key)

        etype = "function" if "def" in m.group("type") else "class"
        raw_sig = m.group("params") or ""

        params = []
        for token in raw_sig.strip("()").split(","):
            token = token.strip().lstrip("*")
            name = re.split(r"[\s:=\(]", token)[0].strip()
            if (name
                    and re.match(r"^[a-zA-Z_]\w*$", name)
                    and name not in ("self", "cls")
                    and name.lower() not in _STOPWORDS
                    and name.lower() not in _JUNK_NAMES):
                params.append(name)

        desc = _extract_description(plain_text[m.end():])
        example = _nearest_code_block(m.start(), plain_text, code_blocks)

        items.append({
            "type": etype,
            "name": raw_name,
            "library": library,
            "params": params,
            "description": desc,
            "example": example,
            "source_url": source_url,
        })

    # --- Issue #5 — Sphinx directive pattern ---
    for m in _SPHINX_DIRECTIVE_RE.finditer(plain_text):
        raw_name = m.group("n")
        if not _is_valid_name(raw_name):
            continue
        if raw_name in seen:
            continue
        seen.add(raw_name)

        raw_sig = m.group("params") or ""
        params = _extract_params_from_signature(raw_sig) if raw_sig else []
        if not params:
            window = plain_text[m.start(): m.start() + 2000]
            params = _extract_numpy_params(window)

        parts = raw_name.split(".")
        if parts[-1][0:1].isupper():
            etype = "class"
        else:
            etype = "function"

        desc = _extract_description(plain_text[m.end():])
        example = _nearest_code_block(m.start(), plain_text, code_blocks)

        items.append({
            "type": etype,
            "name": raw_name,
            "library": library,
            "params": params,
            "description": desc,
            "example": example,
            "source_url": source_url,
        })

    # --- Issue #5 — JSDoc function pattern ---
    for m in _JSDOC_FUNC_RE.finditer(plain_text):
        raw_name = m.group("n")
        if not _is_valid_name(raw_name):
            continue
        key = f"{library}.{raw_name}"
        if key in seen or raw_name in seen:
            continue
        seen.add(key)

        raw_sig = m.group("params") or ""
        params = _extract_params_from_signature(raw_sig) if raw_sig else []
        if not params:
            window = plain_text[m.start(): m.start() + 2000]
            params = _extract_jsdoc_params(window)

        desc = _extract_description(plain_text[m.end():])
        example = _nearest_code_block(m.start(), plain_text, code_blocks)

        items.append({
            "type": "function",
            "name": raw_name,
            "library": library,
            "params": params,
            "description": desc,
            "example": example,
            "source_url": source_url,
        })

    # --- Issue #5 — RTD heading pattern: name(params) on its own line ---
    for m in _RTD_HEADING_RE.finditer(plain_text):
        raw_name = m.group("n")
        if not _is_valid_name(raw_name):
            continue
        if raw_name in seen:
            continue
        seen.add(raw_name)

        raw_params = m.group("params") or ""
        params = _extract_params_from_signature(f"({raw_params})") if raw_params else []

        parts = raw_name.split(".")
        if parts[-1][0:1].isupper():
            etype = "class"
        else:
            etype = "function"

        desc = _extract_description(plain_text[m.end():])
        example = _nearest_code_block(m.start(), plain_text, code_blocks)

        items.append({
            "type": etype,
            "name": raw_name,
            "library": library,
            "params": params,
            "description": desc,
            "example": example,
            "source_url": source_url,
        })

    return items


# ---------------------------------------------------------------------------
# Stage 3 — map to FunctionSchema
# ---------------------------------------------------------------------------

def map_to_schema(
    raw_items: list[dict], version: Optional[str] = None
) -> list[FunctionSchema]:
    results = []
    for item in raw_items:
        try:
            results.append(FunctionSchema(
                type=item.get("type", "function"),
                name=item["name"],
                library=item.get("library", "unknown"),
                version=version,
                params=item.get("params", []),
                description=item.get("description"),
                example=item.get("example"),
                source_url=item.get("source_url"),
                use_when=[],
                avoid_when=[],
                related=[],
                notes=None,
            ))
        except Exception as e:
            print(f"[parser] skipping '{item.get('name')}': {e}")
    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_pages(
    pages: list[dict],
    library: Optional[str] = None,
    version: Optional[str] = None,
) -> list[FunctionSchema]:
    """
    Main entry point. Accepts crawl_docs() output and returns structured
    FunctionSchema objects ready for chunking + embedding.
    """
    all_items: list[dict] = []
    global_seen: set[str] = set()

    for page in pages:
        url = page.get("url", "")
        content = page.get("markdown", "")
        lib_name = library or extract_library_name(url)

        plain_text, code_blocks = clean_page(content)
        raw_items = extract_items(plain_text, code_blocks, lib_name, url)

        for item in raw_items:
            key = f"{item['library']}::{item['name']}"
            if key not in global_seen:
                global_seen.add(key)
                all_items.append(item)

    return map_to_schema(all_items, version=version)