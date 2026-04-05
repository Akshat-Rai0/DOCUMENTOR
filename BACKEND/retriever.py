import json
import pickle
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from vector_store import DATA_DIR, build_collection_name, chroma_client, model as embedding_model


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _infer_library_from_source_url(source_url: Optional[str]) -> Optional[str]:
    if source_url:
        raw = source_url.strip()
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        if parsed.netloc:
            return parsed.netloc
        return raw.split("/")[0]

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


def _bm25_search(query: str, collection_name: str, top_k: int) -> list[dict[str, Any]]:
    bm25_path = _bm25_index_path(collection_name)
    if not bm25_path.exists():
        return []

    try:
        with bm25_path.open("rb") as f:
            payload = pickle.load(f)
    except Exception:
        return []

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

    collection_name = build_collection_name(library)

    with ThreadPoolExecutor(max_workers=2) as executor:
        semantic_future = executor.submit(_semantic_search, query, collection_name, semantic_top_k)
        bm25_future = executor.submit(_bm25_search, query, collection_name, bm25_top_k)
        semantic_results = semantic_future.result()
        bm25_results = bm25_future.result()

    fused_results = reciprocal_rank_fusion(
        semantic_results=semantic_results,
        bm25_results=bm25_results,
        k=rrf_k,
        top_k=fused_top_k,
    )

    return {
        "library": library,
        "collection_name": collection_name,
        "semantic_results": semantic_results,
        "bm25_results": bm25_results,
        "fused_results": fused_results,
    }
