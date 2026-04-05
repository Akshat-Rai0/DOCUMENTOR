import os
import json
import pickle
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

import chromadb
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from schemas.function import FunctionSchema

# Setup base directory for data storage
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Chroma setup
CHROMA_DIR = os.path.join(DATA_DIR, "chroma")
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

model = SentenceTransformer('all-MiniLM-L6-v2')

def build_collection_name(library: str, version: Optional[str] = None) -> str:
    lib_clean = library.replace("-", "_").lower()
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
        
    # 1. Chunk by function boundary
    chunks = [format_chunk(f) for f in functions]
    metadatas = []
    
    for f in functions:
        md = f.model_dump(exclude_none=True)
        # ChromaDB requires all metadata values to be str, int, float, or bool
        for k, v in md.items():
            if isinstance(v, list) or isinstance(v, dict):
                md[k] = json.dumps(v)
        metadatas.append(md)
    
    ids = [f"{col_name}_{i}" for i in range(len(functions))]
    
    # 2. Generate embeddings
    embeddings = model.encode(chunks, show_progress_bar=True).tolist()
    
    # 3. Store in ChromaDB
    try:
        chroma_client.delete_collection(name=col_name) # Fresh start if recrawling
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
        "function_count": len(functions)
    }
    manifest_path = os.path.join(col_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest
