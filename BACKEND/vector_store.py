import os
import json
import pickle
import threading
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

import chromadb
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from schemas.function import FunctionSchema

# Setup base directory for data storage
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_default_data = os.path.join(BASE_DIR, "data")
DATA_DIR = os.path.abspath(os.environ.get("DOCUMENTOR_DATA_DIR", _default_data))
os.makedirs(DATA_DIR, mode=0o755, exist_ok=True)

# Chroma persists SQLite under this path
CHROMA_DIR = os.path.join(DATA_DIR, "chroma")
if os.path.isfile(CHROMA_DIR):
    raise RuntimeError(
        f"Chroma path {CHROMA_DIR!r} is a file. Remove it or set DOCUMENTOR_DATA_DIR to a writable folder."
    )
os.makedirs(CHROMA_DIR, mode=0o755, exist_ok=True)

try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
except Exception as e:
    hint = (
        " If the database looks corrupted, stop the server, delete the 'chroma' folder under your data directory, and retry."
    )
    raise RuntimeError(
        f"Could not open ChromaDB at {CHROMA_DIR!r}. "
        "Ensure the path exists, is a directory, and is writable (or set DOCUMENTOR_DATA_DIR). "
        f"Original error: {e!s}.{hint}"
    ) from e

model = SentenceTransformer('all-MiniLM-L6-v2')

# Issue #8 — write lock to prevent race conditions on delete+recreate
_chroma_write_lock = threading.Lock()


def build_collection_name(library: str, version: Optional[str] = None) -> str:
    lib_clean = library.replace("-", "_").replace(".", "_").lower()
    if version:
        ver_clean = version.replace(".", "_")
        return f"{lib_clean}_{ver_clean}"
    return lib_clean


def check_cache(url: str, library: str, version: Optional[str] = None) -> bool:
    """Check if we have a fresh manifest.json for this library/url."""
    col_name = build_collection_name(library, version)
    manifest_path = os.path.join(DATA_DIR, col_name, "manifest.json")
    if not os.path.exists(manifest_path):
        return False

    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        if manifest.get("url") != url:
            return False

        crawl_date = datetime.fromisoformat(manifest.get("crawl_date", ""))
        if datetime.now() - crawl_date < timedelta(days=7):
            return True
    except Exception as e:
        print(f"Cache check failed: {e}")

    return False


# -- Issue #6 — Sliding-window sub-chunking -----------------------------------

def _sliding_window_chunks(
    text: str,
    window_size: int = 512,
    overlap: int = 128,
) -> list[str]:
    """
    Split a long text into overlapping windows.
    Returns at least one chunk (the original text if short enough).
    """
    words = text.split()
    if len(words) <= window_size:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + window_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start += window_size - overlap

    return chunks


def format_chunk(func: FunctionSchema) -> str:
    """Concatenate into a single string chunk text."""
    parts = []
    parts.append(f"Name: {func.name}")
    if func.description:
        parts.append(f"Description: {func.description}")
    if func.params:
        parts.append(f"Params: {', '.join(func.params)}")
    if func.example:
        parts.append(f"Example:\n{func.example}")

    return "\n".join(parts)


def _build_sub_chunks(
    functions: List[FunctionSchema],
    col_name: str,
) -> tuple[list[str], list[dict], list[str]]:
    """
    Build sub-chunks with sliding window for long functions.
    Returns (chunks, metadatas, ids).
    """
    chunks: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    for func_idx, f in enumerate(functions):
        full_text = format_chunk(f)
        sub_chunks = _sliding_window_chunks(full_text)

        md_base = f.model_dump(exclude_none=True)
        for k, v in md_base.items():
            if isinstance(v, (list, dict)):
                md_base[k] = json.dumps(v)

        for sub_idx, sub_text in enumerate(sub_chunks):
            chunk_id = f"{col_name}_{func_idx}_{sub_idx}"
            md = dict(md_base)
            md["sub_chunk_index"] = sub_idx
            md["total_sub_chunks"] = len(sub_chunks)

            chunks.append(sub_text)
            metadatas.append(md)
            ids.append(chunk_id)

    return chunks, metadatas, ids


def process_and_store(
    functions: List[FunctionSchema],
    library: str,
    url: str,
    pages_count: int,
    version: Optional[str] = None
):
    col_name = build_collection_name(library, version)
    col_dir = os.path.join(DATA_DIR, col_name)
    os.makedirs(col_dir, exist_ok=True)

    if not functions:
        print(f"No functions to process for {col_name}")
        return

    # 1. Build sub-chunks with sliding window (Issue #6)
    chunks, metadatas, ids = _build_sub_chunks(functions, col_name)

    # 2. Generate embeddings
    embeddings = model.encode(chunks, show_progress_bar=True).tolist()

    # 3. Store in ChromaDB (Issue #8 — use write lock)
    with _chroma_write_lock:
        try:
            chroma_client.delete_collection(name=col_name)
        except (ValueError, Exception):
            pass

        collection = chroma_client.get_or_create_collection(name=col_name)

    for i in range(0, len(ids), 5000):
        collection.add(
            ids=ids[i:i+5000],
            embeddings=embeddings[i:i+5000],
            metadatas=metadatas[i:i+5000],
            documents=chunks[i:i+5000]
        )

    # 4. Build BM25 index alongside
    tokenized_chunks = [chunk.lower().split() for chunk in chunks]
    bm25 = BM25Okapi(tokenized_chunks)

    bm25_path = os.path.join(col_dir, "bm25_index.pkl")
    with open(bm25_path, "wb") as f:
        pickle.dump(
            {
                "bm25": bm25,
                "ids": ids,
                "chunks": chunks,
                "metadatas": metadatas,
            },
            f
        )

    # 5. Version caching
    manifest = {
        "url": url,
        "crawl_date": datetime.now().isoformat(),
        "page_count": pages_count,
        "library_version": version,
        "library": library,
        "function_count": len(functions),
        "chunk_count": len(chunks),
    }
    manifest_path = os.path.join(col_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest
