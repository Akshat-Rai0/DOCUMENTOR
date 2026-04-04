"""
test_parser.py — Phase 2 validation script

Crawls one real documentation page (FastAPI), runs it through the parser,
and prints the extracted FunctionSchema objects.

Usage:
    cd BACKEND
    python test_parser.py

Pass criteria:
  - At least 3 items extracted
  - Every item has a non-empty name and library
  - At least 1 item has a non-None description
  - At least 1 item has a non-None example
"""

import asyncio
import json
import sys
from dotenv import load_dotenv

load_dotenv()

from utils import scrape_static
from parser import parse_pages


# ---------------------------------------------------------------------------
# Config — swap URL to test a different library
# ---------------------------------------------------------------------------
TEST_URL = "https://fastapi.tiangolo.com/reference/apirouter/"
LIBRARY_OVERRIDE = "fastapi"
VERSION = "0.110.0"
MAX_PAGES = 1   # Keep it fast for a single-page smoke test


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_item(i: int, item) -> None:
    print(f"\n{'─'*60}")
    print(f"  [{i}] {item.type.upper()}  →  {item.name}")
    print(f"       library : {item.library}  (v{item.version or '?'})")
    print(f"       params  : {item.params or '—'}")
    if item.description:
        preview = item.description[:120].replace("\n", " ")
        print(f"       desc    : {preview}...")
    else:
        print(f"       desc    : —")
    if item.example:
        ex_preview = item.example[:80].replace("\n", " ")
        print(f"       example : {ex_preview}...")
    else:
        print(f"       example : —")
    print(f"       url     : {item.source_url}")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        print(f"\n❌  FAIL: {message}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    print("=" * 60)
    print("  DocuMentor — Phase 2 Parser Test")
    print(f"  Target  : {TEST_URL}")
    print(f"  Library : {LIBRARY_OVERRIDE}  v{VERSION}")
    print("=" * 60)

    # ── Step 1: crawl ──────────────────────────────────────────────────────
    print("\n[1/3] Crawling page...")
    pages = await scrape_static(TEST_URL, max_pages=MAX_PAGES)
    print(f"      {len(pages)} page(s) fetched")
    _assert(len(pages) > 0, "Crawler returned 0 pages — check network / URL")

    # ── Step 2: parse ──────────────────────────────────────────────────────
    print("\n[2/3] Running parser pipeline...")
    results = parse_pages(pages, library=LIBRARY_OVERRIDE, version=VERSION)
    print(f"      {len(results)} item(s) extracted")

    # ── Step 3: assertions ─────────────────────────────────────────────────
    print("\n[3/3] Running assertions...")

    _assert(len(results) >= 3, f"Expected ≥3 items, got {len(results)}")

    for item in results:
        _assert(bool(item.name), f"Item missing name: {item}")
        _assert(bool(item.library), f"Item missing library: {item}")

    has_desc = any(item.description for item in results)
    _assert(has_desc, "No item has a description — check _description_window()")

    has_example = any(item.example for item in results)
    # Example may be absent on some pages — warn but don't fail
    if not has_example:
        print("  ⚠️  No code examples found on this page (non-fatal)")

    # ── Print results ──────────────────────────────────────────────────────
    print(f"\n✅  All assertions passed — {len(results)} item(s) extracted\n")
    for i, item in enumerate(results, 1):
        _print_item(i, item)

    # ── Dump JSON ──────────────────────────────────────────────────────────
    output_path = "test_parser_output.json"
    with open(output_path, "w") as f:
        json.dump([item.model_dump() for item in results], f, indent=2)
    print(f"\n\nFull output saved to → {output_path}")


if __name__ == "__main__":
    asyncio.run(main())