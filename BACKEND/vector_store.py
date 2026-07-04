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

from functools import lru_cache


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer("all-MiniLM-L6-v2")  


# write lock to prevent race conditions on delete+recreate
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
    embeddings = get_embedding_model().encode(chunks, show_progress_bar=True).tolist()

    # 3. Build the BM25 index and pickle it to a TEMP file first (Issue #10 —
    #    Chroma/BM25 drift). This is the cheap, easily-retryable work, so we
    #    do it before touching Chroma. If it fails, nothing live has been
    #    touched yet.
    tokenized_chunks = [chunk.lower().split() for chunk in chunks]
    bm25 = BM25Okapi(tokenized_chunks)

    bm25_path = os.path.join(col_dir, "bm25_index.pkl")
    bm25_tmp_path = bm25_path + ".tmp"
    with open(bm25_tmp_path, "wb") as f:
        pickle.dump(
            {
                "bm25": bm25,
                "ids": ids,
                "chunks": chunks,
                "metadatas": metadatas,
            },
            f
        )

    # 4. Store in ChromaDB under a staging collection name first, so the OLD
    #    (still-live) collection stays fully intact and queryable while the
    #    new one is being written. Only after every batch succeeds do we
    #    promote staging -> live and atomically swap in the BM25 file. This
    #    is the fix for Issue #10: the two stores can never be observed in a
    #    half-updated state relative to each other, and a crash mid-write
    #    just leaves the old data as the live data (safe), never a mix.
    staging_col_name = f"{col_name}__staging"

    with _chroma_write_lock:
        try:
            chroma_client.delete_collection(name=staging_col_name)
        except Exception:
            pass  # no leftover staging collection from a previous failed run

        collection = chroma_client.get_or_create_collection(name=staging_col_name)

        try:
            for i in range(0, len(ids), 5000):
                collection.add(
                    ids=ids[i:i + 5000],
                    embeddings=embeddings[i:i + 5000],
                    metadatas=metadatas[i:i + 5000],
                    documents=chunks[i:i + 5000]
                )
        except Exception:
            # Staging write failed partway through. Clean up the partial
            # staging collection and the BM25 temp file; leave the OLD
            # (still-live) collection and BM25 index completely untouched,
            # then re-raise so the caller knows the crawl/index failed.
            try:
                chroma_client.delete_collection(name=staging_col_name)
            except Exception:
                pass
            if os.path.exists(bm25_tmp_path):
                os.remove(bm25_tmp_path)
            raise

        # Staging is fully populated. Promote it to the live name. Newer
        # chromadb versions support renaming in place via modify(); older
        # ones don't, so fall back to copying staging's contents into a
        # freshly (re)created live collection.
        try:
            collection.modify(name=col_name)
        except Exception:
            try:
                chroma_client.delete_collection(name=col_name)
            except Exception:
                pass
            final_collection = chroma_client.get_or_create_collection(name=col_name)
            all_data = collection.get(include=["embeddings", "metadatas", "documents"])
            if all_data.get("ids"):
                final_collection.add(
                    ids=all_data["ids"],
                    embeddings=all_data["embeddings"],
                    metadatas=all_data["metadatas"],
                    documents=all_data["documents"],
                )
            try:
                chroma_client.delete_collection(name=staging_col_name)
            except Exception:
                pass

        # Chroma is now live under col_name. Atomically swap the BM25 file
        # in as the very last step — os.replace is atomic on POSIX and
        # Windows, so bm25_path is never observably half-written.
        os.replace(bm25_tmp_path, bm25_path)

        # Drop any process-level BM25 cache entry so the next query reloads
        # the freshly-swapped file instead of serving a stale in-memory copy
        # (see retriever.py's python_bm25_cache).
        try:
            from retriever import python_bm25_cache
            python_bm25_cache.pop(col_name, None)
        except Exception:
            pass

    # 5. Version caching — written last, acts as the "commit succeeded"
    #    signal for check_cache(). If anything above raised, execution never
    #    reaches here, so a stale manifest can never point at a broken or
    #    partially-written index.
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