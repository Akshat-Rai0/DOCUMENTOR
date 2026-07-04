import json
import pickle
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Optional
from urllib.parse import urlparse

from url_utils import extract_library_name
from vector_store import DATA_DIR, build_collection_name, chroma_client, model as embedding_model


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _infer_library_from_source_url(source_url: Optional[str]) -> Optional[str]:
    """Use the shared extract_library_name utility (Issue #3)."""
    if source_url:
        return extract_library_name(source_url)

    # fallback — find most recently indexed library from manifests
    data_root = Path(DATA_DIR)
    newest_library: Optional[str] = None
    newest_date: Optional[datetime] = None

    for child in data_root.iterdir():
        if not child.is_dir() or child.name == "chroma":
            continue
        manifest_path = child / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text())
            crawl_date = manifest.get("crawl_date")
            parsed_date = datetime.fromisoformat(crawl_date) if crawl_date else datetime.min
            if newest_date is None or parsed_date > newest_date:
                newest_date = parsed_date
                newest_library = manifest.get("library") or child.name
        except Exception:
            continue

    return newest_library


def _bm25_index_path(collection_name: str) -> Path:
    return Path(DATA_DIR) / collection_name / "bm25_index.pkl"


def _semantic_search(query: str, collection_name: str, top_k: int) -> list[dict[str, Any]]:
    try:
        collection = chroma_client.get_collection(name=collection_name)
    except Exception:
        return []

    query_embedding = embedding_model.encode([query])[0].tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = (results.get("ids") or [[]])[0]
    docs = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    ranked: list[dict[str, Any]] = []
    for idx, doc in enumerate(docs):
        metadata = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}
        chunk_id = ids[idx] if idx < len(ids) else f"semantic_{idx}"
        distance = distances[idx] if idx < len(distances) else 1.0
        similarity = 1.0 / (1.0 + _safe_float(distance, 1.0))
        ranked.append(
            {
                "chunk_id": str(chunk_id),
                "text": doc,
                "metadata": metadata,
                "source_url": metadata.get("source_url"),
                "function_name": metadata.get("name"),
                "semantic_score": similarity,
            }
        )

    return ranked


python_bm25_cache: dict[str, dict] = {}


def _bm25_search(query: str, collection_name: str, top_k: int) -> list[dict[str, Any]]:
    if collection_name not in python_bm25_cache:
        bm25_path = _bm25_index_path(collection_name)
        if not bm25_path.exists():
            return []
        try:
            with bm25_path.open("rb") as f:
                payload = pickle.load(f)
        except Exception:
            return []
        python_bm25_cache[collection_name] = payload

    payload = python_bm25_cache[collection_name]
    bm25 = payload.get("bm25")
    ids = payload.get("ids", [])
    chunks = payload.get("chunks", [])
    metadatas = payload.get("metadatas", [])

    if bm25 is None or not chunks:
        return []

    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    ranked: list[dict[str, Any]] = []
    for idx in ranked_indices:
        metadata = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}
        ranked.append(
            {
                "chunk_id": str(ids[idx]) if idx < len(ids) else f"bm25_{idx}",
                "text": chunks[idx],
                "metadata": metadata,
                "source_url": metadata.get("source_url"),
                "function_name": metadata.get("name"),
                "bm25_score": _safe_float(scores[idx]),
            }
        )

    return ranked


def reciprocal_rank_fusion(
    semantic_results: list[dict[str, Any]],
    bm25_results: list[dict[str, Any]],
    k: int = 60,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for source_name, results in (
        ("semantic", semantic_results),
        ("bm25", bm25_results),
    ):
        for rank, item in enumerate(results, start=1):
            chunk_id = item.get("chunk_id") or f"hash_{hash(item.get('text', ''))}"
            if chunk_id not in merged:
                merged[chunk_id] = {
                    **item,
                    "rrf_score": 0.0,
                    "matched_by": [],
                }
            merged[chunk_id]["rrf_score"] += 1.0 / (k + rank)
            merged[chunk_id][f"{source_name}_rank"] = rank
            if source_name not in merged[chunk_id]["matched_by"]:
                merged[chunk_id]["matched_by"].append(source_name)

    fused = sorted(merged.values(), key=lambda x: x["rrf_score"], reverse=True)
    return fused[:top_k]


# ---------------------------------------------------------------------------
# Issue #14 — LRU cache on (query, library) retrieval results
# ---------------------------------------------------------------------------
#
# Keyed on the *resolved* library (post _infer_library_from_source_url), not
# on the raw source_url param, since source_url=None resolves differently
# depending on what's most recently indexed. Also keyed on the retrieval
# knobs (top_k / rrf_k) so a call with different params never returns a
# cached result meant for different params.
#
# A manual OrderedDict is used instead of functools.lru_cache because we
# need to selectively invalidate all entries for a single library when it
# gets re-indexed (see invalidate_retrieval_cache below) — lru_cache only
# supports clearing everything at once.

_RETRIEVAL_CACHE_MAXSIZE = 256
_retrieval_cache: "OrderedDict[tuple, dict[str, Any]]" = OrderedDict()
_retrieval_cache_lock = Lock()


def _retrieval_cache_key(
    query: str,
    library: str,
    semantic_top_k: int,
    bm25_top_k: int,
    fused_top_k: int,
    rrf_k: int,
) -> tuple:
    return (query, library, semantic_top_k, bm25_top_k, fused_top_k, rrf_k)


def invalidate_retrieval_cache(library: Optional[str] = None) -> None:
    """
    Drop cached retrieval results. Call this whenever a library is
    re-indexed (vector_store.process_and_store) so stale results for that
    library can't be served after fresh data is written.

    If library is None, clears the entire cache.
    """
    with _retrieval_cache_lock:
        if library is None:
            _retrieval_cache.clear()
            return
        stale_keys = [k for k in _retrieval_cache if k[1] == library]
        for k in stale_keys:
            del _retrieval_cache[k]


def hybrid_retrieve(
    query: str,
    source_url: Optional[str] = None,
    semantic_top_k: int = 10,
    bm25_top_k: int = 10,
    fused_top_k: int = 5,
    rrf_k: int = 60,
) -> dict[str, Any]:
    library = _infer_library_from_source_url(source_url)
    if not library:
        raise ValueError("No indexed library found. Crawl documentation first or pass source_url.")

    cache_key = _retrieval_cache_key(
        query, library, semantic_top_k, bm25_top_k, fused_top_k, rrf_k
    )
    with _retrieval_cache_lock:
        cached = _retrieval_cache.get(cache_key)
        if cached is not None:
            _retrieval_cache.move_to_end(cache_key)  # mark as recently used
            return cached

    collection_name = build_collection_name(library)

    # -- Issue #7 — query expansion --------------------------------------------
    try:
        from query_rewriter import expand_query
        query_variants = expand_query(query)
    except Exception:
        query_variants = [query]

    all_semantic: list[dict[str, Any]] = []
    all_bm25: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()

    for variant in query_variants:
        with ThreadPoolExecutor(max_workers=2) as executor:
            semantic_future = executor.submit(_semantic_search, variant, collection_name, semantic_top_k)
            bm25_future = executor.submit(_bm25_search, variant, collection_name, bm25_top_k)
            sem_results = semantic_future.result()
            bm_results = bm25_future.result()

        # Deduplicate across variants
        for r in sem_results:
            cid = r.get("chunk_id", "")
            if cid not in seen_chunk_ids:
                seen_chunk_ids.add(cid)
                all_semantic.append(r)
        for r in bm_results:
            cid = r.get("chunk_id", "")
            if cid not in seen_chunk_ids:
                seen_chunk_ids.add(cid)
                all_bm25.append(r)

    fused_results = reciprocal_rank_fusion(
        semantic_results=all_semantic,
        bm25_results=all_bm25,
        k=rrf_k,
        top_k=fused_top_k,
    )

    result = {
        "library": library,
        "collection_name": collection_name,
        "semantic_results": all_semantic[:semantic_top_k],
        "bm25_results": all_bm25[:bm25_top_k],
        "fused_results": fused_results,
        "query_variants": query_variants,
    }

    with _retrieval_cache_lock:
        _retrieval_cache[cache_key] = result
        _retrieval_cache.move_to_end(cache_key)
        while len(_retrieval_cache) > _RETRIEVAL_CACHE_MAXSIZE:
            _retrieval_cache.popitem(last=False)  # evict least-recently-used

    return result