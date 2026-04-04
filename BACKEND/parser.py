"""
parser.py — Phase 2 core pipeline (v4)

Root cause fix from v3: scrape_static() already converts HTML to plain text
before storing in page["markdown"]. The previous versions tried to parse HTML
tags that don't exist. This version works entirely on the plain text format
that scrape_static() actually produces.

Plain text format from scrape_static (confirmed via debug):
  - Function/class headings appear as:   fastapi.APIRouter\n¶
  - OR as a dotted name on its own line:  fastapi.APIRouter.websocket\n¶
  - Parameters appear as a table:
        prefix\nAn optional path prefix...\nTYPE: str\nDEFAULT: ''\n
  - Code examples appear inline as spaced-out Python:
        from\nfastapi\nimport\nAPIRouter\n...
  - No <pre>, no ##, no def/class keywords in doc pages (only inside source
    code toggle text which is also plain text by the time we see it)

Strategy:
  1. clean_page()    — strip nav/sponsor noise from the top of the plain text
  2. extract_items() — match dotted API names using plain-text patterns
  3. For each match, extract:
       - params: the (  *  , prefix = "" , ... ) block on the same/next line
       - description: first prose paragraph after the ¶ marker
       - example: first indented code block after the match
  4. map_to_schema() — validate into FunctionSchema
"""

import re
from typing import Optional
from urllib.parse import urlparse
from schemas.function import FunctionSchema


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
    # must start with a letter
    if not name[0].isalpha():
        return False
    # block known junk
    if name.lower() in _JUNK_NAMES:
        return False
    # single short lowercase words with no dots are likely prose, not API names
    if "." not in name and name.islower() and len(name) < 5:
        return False
    return True


def _extract_library_name(url: str) -> str:
    host = re.sub(r"^www\.", "", urlparse(url).netloc)
    parts = host.split(".")
    name = parts[0]
    if name in ("docs", "doc", "api"):
        name = parts[1] if len(parts) > 1 else name
    return name


# ---------------------------------------------------------------------------
# Stage 1 — clean plain text
# ---------------------------------------------------------------------------

# Lines that are pure nav/sponsor noise appearing before the real content
_NOISE_LINE_RE = re.compile(
    r"^(sponsor|skip to content|follow\s|join the|subscribe|"
    r"fastapi cloud|newsletter|@fastapi|linkedin|twitter|"
    r"initializing search|back to top|\s*$)",
    re.IGNORECASE,
)

# Lines that are pure punctuation / single symbols
_PUNCT_LINE_RE = re.compile(r"^[¶\-=~\.\,\:\;\|\s]{1,5}$")


def clean_page(plain_text: str) -> tuple[str, list[str]]:
    """
    Clean up plain text from scrape_static().

    Since scrape_static already strips HTML and returns plain text,
    this function:
      1. Removes nav/sponsor noise lines from the top
      2. Extracts indented/fenced code blocks as a separate list
      3. Returns (cleaned_text, code_blocks)

    The 'markdown' key from scrape_static is already plain text —
    no HTML parsing is done here.
    """
    lines = plain_text.splitlines()
    cleaned: list[str] = []
    code_blocks: list[str] = []
    current_code: list[str] = []
    in_code = False

    for line in lines:
        # Detect fenced code blocks (```...```)
        if line.strip().startswith("```"):
            if in_code:
                # end of code block
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

        # Skip pure noise lines
        if _NOISE_LINE_RE.match(line.strip()):
            continue
        if _PUNCT_LINE_RE.match(line):
            continue

        cleaned.append(line)

    # flush any unclosed code block
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
# Matches:  "fastapi.APIRouter"  /  "fastapi.APIRouter.websocket"
_DOTTED_NAME_RE = re.compile(
    r"^(?P<n>[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*){1,})\s*¶?\s*$",
    re.MULTILINE,
)

# Pattern B: Python def/class (appears in source-code sections of some pages)
_DEF_CLASS_RE = re.compile(
    r"^(?P<type>async def|def|class)\s+(?P<n>[a-zA-Z_]\w*)\s*(?P<params>\([^)]{0,400}\))?",
    re.MULTILINE,
)

# Matches the spaced-out param block:  ( * , prefix = "" , tags = None , ... )
# scrape_static separates tokens with spaces/newlines, so we look for a
# block starting with ( and ending with ) spanning up to 2000 chars
_SPACED_PARAMS_RE = re.compile(r"\(\s*[\*\w].*?\)", re.DOTALL)

# Matches a TYPE: line in the parameter table — used to extract param names
# Format:  "<param_name>\n<description prose>\nTYPE: <type>\nDEFAULT: <val>"
_PARAM_TABLE_RE = re.compile(
    r"^([a-zA-Z_]\w*)\n(?:(?!TYPE:|DEFAULT:|PARAMETER|DESCRIPTION).*\n)*?TYPE:\s*\S",
    re.MULTILINE,
)


def _extract_params_from_table(text_window: str) -> list[str]:
    """
    Extract parameter names from the PARAMETER/DESCRIPTION table that
    MkDocs griddoc renders after each function signature.

    Table format in plain text:
        PARAMETER   DESCRIPTION
        prefix
        An optional path prefix for the router.
        TYPE: str
        DEFAULT: ''
        tags
        A list of tags...
        TYPE: list[str | Enum] | None
        ...
    """
    params = []
    # Find the PARAMETER DESCRIPTION header
    table_start = text_window.find("PARAMETER")
    if table_start == -1:
        return []

    table_text = text_window[table_start:]
    lines = table_text.splitlines()

    # Skip the header line "PARAMETER   DESCRIPTION"
    i = 1
    while i < len(lines):
        line = lines[i].strip()
        # A param name line: non-empty, a single valid identifier, not a keyword
        if (line
                and re.match(r"^[a-zA-Z_]\w*$", line)
                and line.lower() not in _STOPWORDS
                and line.lower() not in _JUNK_NAMES
                and line not in ("PARAMETER", "DESCRIPTION", "TYPE",
                                 "DEFAULT", "Note", "None", "True", "False")):
            params.append(line)
        # Stop at the next section heading (all-caps word alone on a line
        # that isn't a known param section marker)
        if line in ("SOURCE", "RETURNS", "RAISES", "YIELDS",
                    "ATTRIBUTES", "METHODS"):
            break
        i += 1

    return params


def _extract_params_from_signature(sig_text: str) -> list[str]:
    """
    Extract params from the spaced-out signature block.
    e.g. '( * , prefix = "" , tags = None , ... )'
    Keeps only bare identifier tokens that appear before '='.
    """
    # Remove the outer parens
    inner = sig_text.strip().lstrip("(").rstrip(")")
    params = []
    for token in inner.split(","):
        token = token.strip().lstrip("*").strip()
        # Take only the part before = or space
        name = re.split(r"[\s=:\(]", token)[0].strip()
        if (name
                and re.match(r"^[a-zA-Z_]\w*$", name)
                and name not in ("self", "cls")
                and name.lower() not in _STOPWORDS
                and name.lower() not in _JUNK_NAMES):
            params.append(name)
    return params


def _extract_description(text_window: str, max_chars: int = 800) -> Optional[str]:
    """
    Find the first real prose paragraph after a function heading.

    Skips:
      - The ¶ symbol
      - Lines that are just type names / punctuation
      - Lines starting with code keywords
      - PARAMETER / TYPE / DEFAULT table lines
      - Lines shorter than 20 chars (likely fragment noise)

    Returns the first 1-3 prose lines joined into a string, or None.
    """
    skip_re = re.compile(
        r"^(¶|PARAMETER|DESCRIPTION|TYPE:|DEFAULT:|Example|SOURCE|"
        r"Bases:|Read more|Note:|Warning:|__CODE_BLOCK__|"
        r"from\s|import\s|async\s+def\s|def\s|class\s|return\s|"
        r"@\w|#|\`\`\`)",
        re.IGNORECASE,
    )
    # Also skip lines that are spaced-out identifiers/tokens from the signature
    # (they look like:  "prefix\n=\n\"\"\n,\ntags\n=")
    punct_only = re.compile(r'^[\(\)\[\]{}\.,=\*"\'\s:¶|]{1,8}$')

    snippet = text_window[:max_chars]
    prose = []
    for line in snippet.splitlines():
        s = line.strip()
        if not s:
            if prose:
                break   # blank line after content = end of paragraph
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
        # Use just the last component as the display name, keep full for dedup
        short_name = raw_name.split(".")[-1]
        if not _is_valid_name(short_name):
            continue
        if raw_name in seen:
            continue
        seen.add(raw_name)

        # Determine type from name structure
        parts = raw_name.split(".")
        if len(parts) == 1:
            etype = "function"
        elif parts[-1][0].isupper():
            etype = "class"
        else:
            etype = "method"

        # Look for params in the next 2000 chars
        window = plain_text[m.start(): m.start() + 2000]

        # Try table first (most reliable for doc reference pages)
        params = _extract_params_from_table(window)

        # Fall back to spaced signature block
        if not params:
            sig_m = _SPACED_PARAMS_RE.search(window)
            if sig_m:
                params = _extract_params_from_signature(sig_m.group(0))

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
        # Build a qualified name for dedup
        key = f"{library}.{raw_name}"
        if key in seen or raw_name in seen:
            continue
        seen.add(key)

        etype = "function" if "def" in m.group("type") else "class"
        raw_sig = m.group("params") or ""

        # Clean params from the signature
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

    Args:
        pages:   List of {"url": str, "markdown": str} from the crawler.
                 The "markdown" value is plain text (scrape_static already
                 converts HTML to text before storing it here).
        library: Override library name (auto-detected from URL if None).
        version: Optional version string e.g. "2.1.0".

    Returns:
        Deduplicated list of FunctionSchema objects.
    """
    all_items: list[dict] = []
    global_seen: set[str] = set()

    for page in pages:
        url = page.get("url", "")
        content = page.get("markdown", "")
        lib_name = library or _extract_library_name(url)

        plain_text, code_blocks = clean_page(content)
        raw_items = extract_items(plain_text, code_blocks, lib_name, url)

        for item in raw_items:
            key = f"{item['library']}::{item['name']}"
            if key not in global_seen:
                global_seen.add(key)
                all_items.append(item)

    return map_to_schema(all_items, version=version)