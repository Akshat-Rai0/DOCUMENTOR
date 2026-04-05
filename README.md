# DocuMentor — AI-Powered Documentation Assistant

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange)](https://www.trychroma.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black)](https://ollama.ai/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

> Ask anything about any library — in plain English. DocuMentor crawls documentation from any URL, indexes it using a hybrid RAG pipeline, and answers developer questions with the right function, when to use it, when to avoid it, and working code.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [How It Works](#how-it-works)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

DocuMentor solves a real problem for developers learning new libraries: official documentation is written for experienced users, organized by API reference rather than use case, and requires you to already know what you're looking for.

Paste any documentation URL. DocuMentor crawls the entire site, parses and indexes every function into a structured knowledge base, and lets you ask questions in plain English. The system classifies your intent (function search, error fix, or concept explanation), retrieves the most relevant documentation chunks using hybrid BM25 + semantic search, reranks them with a cross-encoder, and generates a grounded answer using a local LLM — with source citations and zero hallucination of function names.

**Target users:** Computer science students, bootcamp learners, self-taught developers, and anyone onboarding to an unfamiliar library.

---

## Key Features

- **Bring-your-own documentation** — works with any library that has a public documentation URL, not just popular ones baked into training data
- **Three intelligent response modes:**
  - **Function recommendation** — describes a goal, gets ranked function candidates with trade-offs and code snippets
  - **Anti-pattern detection** — every answer includes a structured "avoid when" section
  - **Error fix mode** — paste a traceback, get root cause + fix + working code
- **Hybrid retrieval pipeline** — BM25 keyword search + dense embeddings merged via Reciprocal Rank Fusion (RRF), followed by a cross-encoder reranker
- **Hallucination-proof by design** — the LLM is strictly grounded to retrieved documentation chunks only
- **Version caching** — already-indexed libraries are served from cache for 7 days; no redundant re-crawling
- **Fully local LLM** — runs on your machine via Ollama with no API costs
- **Real-time indexing progress** — frontend polls and displays crawl → parse → index stages with a progress bar

---

## Architecture

The system follows a 7-stage pipeline from URL to answer:
URL Input
→ Scrape (httpx + BeautifulSoup / Cloudflare Browser Rendering)
→ Clean + Structure (strip noise, extract function boundaries)
→ Chunk (by function boundary, not token count)
→ Embed (sentence-transformers all-MiniLM-L6-v2 → ChromaDB)
→ Hybrid Retrieval (BM25 + semantic search → RRF merge)
→ Rerank (cross-encoder/ms-marco-MiniLM-L-6-v2)
→ LLM Answer (Ollama qwen2.5-coder:7b, strict JSON output)

Each scraped function is stored as a typed JSON object:
```json
{
  "type": "function",
  "name": "pandas.read_csv",
  "library": "pandas",
  "version": "2.1.0",
  "params": ["filepath_or_buffer", "sep", "dtype"],
  "use_when": ["loading tabular data from disk"],
  "avoid_when": ["file > available RAM — use chunksize or Dask"],
  "example": "df = pd.read_csv('data.csv', dtype={'id': str})",
  "related": ["pandas.read_parquet", "pandas.read_json"],
  "notes": "Use engine='pyarrow' for 3–5× faster parse",
  "source_url": "https://pandas.pydata.org/docs/..."
}
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI + Uvicorn |
| Scraping (static) | httpx + BeautifulSoup4 |
| Scraping (JS-heavy) | Cloudflare Browser Rendering REST API |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` |
| Vector store | ChromaDB (persistent, local) |
| Keyword search | rank-bm25 |
| Reranker | sentence-transformers `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Local LLM | Ollama (`qwen2.5-coder:7b`) |
| Frontend | React 18 + TypeScript + Vite |
| Styling | Tailwind CSS + shadcn/ui |
| Data validation | Pydantic v2 |

---

## Project Structure

```
DOCUMENTOR/
├── BACKEND/
│   ├── app.py                  # FastAPI application, route definitions
│   ├── pipeline.py             # RAG orchestration (intent → retrieve → rerank → LLM)
│   ├── retriever.py            # Hybrid BM25 + semantic search with RRF fusion
│   ├── reranker.py             # Cross-encoder reranking
│   ├── llm.py                  # Ollama integration and JSON answer generation
│   ├── intent_classifier.py    # Rule-based + LLM intent classification
│   ├── prompts.py              # Prompt templates per intent type
│   ├── parser.py               # HTML → plain text → structured function extraction
│   ├── vector_store.py         # ChromaDB + BM25 storage, caching, embeddings
│   ├── utils.py                # Crawlers (static + Cloudflare)
│   ├── model.py                # Pydantic request/response models
│   ├── schemas/
│   │   └── function.py         # FunctionSchema definition
│   ├── data/                   # Persisted ChromaDB + per-library manifests (gitignored locally)
│   ├── requirements.txt
│   ├── .env                    # Environment variables (not committed)
│   ├── test_crawl.py           # Cloudflare crawl integration test
│   └── test_parser.py          # Parser validation script
│
└── FRONTEND/
    ├── src/
    │   ├── pages/
    │   │   ├── Index.tsx       # Home: doc URL input, quick-start pills, feature previews
    │   │   ├── ChatPage.tsx    # Chat UI after indexing
    │   │   ├── QueryPage.tsx   # Explore / demo route
    │   │   └── NotFound.tsx
    │   ├── components/         # Shared UI (shadcn/ui)
    │   ├── hooks/
    │   └── lib/
    ├── .env                    # VITE_API_BASE_URL
    ├── package.json
    ├── tailwind.config.ts
    └── vite.config.ts
```

---

## Prerequisites

Ensure the following are installed before proceeding:

- **Python 3.11+**
- **Node.js 18+**
- **Ollama** — [install from ollama.ai](https://ollama.ai)

Pull the LLM model before starting:
```bash
ollama pull qwen2.5-coder:7b
```

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/documentor.git
cd documentor
```

### 2. Backend setup
```bash
cd BACKEND

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend setup
```bash
cd FRONTEND
npm install
```

---

## Environment Variables

### Backend — `BACKEND/.env`
```env
# Ollama (local LLM)
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_URL=http://localhost:11434/api/generate

# Cloudflare Browser Rendering (optional — only needed for JS-heavy doc sites)
CF_ACCOUNT_ID=your_cloudflare_account_id
CF_API_TOKEN=your_cloudflare_api_token
```

Optional — **data directory override** (set in the shell or add to `.env` if your tooling loads it into the environment):

| Variable | Purpose |
|----------|---------|
| `DOCUMENTOR_DATA_DIR` | Absolute path to a **writable** folder for `data/` contents. Default: `BACKEND/data`. Use this in Docker, read-only installs, or when the default path is not writable. ChromaDB stores SQLite under `<DOCUMENTOR_DATA_DIR>/chroma`. |

> The Cloudflare credentials are **optional**. The system automatically falls back to the static scraper (`httpx` + `BeautifulSoup`) for most documentation sites. Cloudflare is only used for JS-rendered sites like React, Vue, or Next.js docs.

### Frontend — `FRONTEND/.env`
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## Running the Application

### 1. Start Ollama
```bash
ollama serve
```

### 2. Start the backend
```bash
cd BACKEND
source .venv/bin/activate
uvicorn app:app --reload --port 8000
```

### 3. Start the frontend
```bash
cd FRONTEND
npm run dev
```

The application will be available at **`http://localhost:8080`** (see `FRONTEND/vite.config.ts`).

### Routes (frontend)

| Path | Description |
|------|-------------|
| `/` | **Home** — paste a documentation URL or pick a quick-start library (Pandas, FastAPI, Three.js, Scikit-learn, SQLAlchemy). Indexing runs from the URL bar or a pill; progress is shown inline. **What you can ask** cards open a modal with more detail; click outside or press Escape to close. |
| `/chat?url=...` | **Chat** — opens after a successful index (or when linked with a `url` query). Ask questions against the indexed docs. |
| `/explore` | **Explore** — additional demo / query page in the app shell. |

---

## API Reference

### `POST /api/crawl`

Initiates a crawl, parse, and index job for a documentation URL. Returns immediately; runs in the background.

**Request body:**
```json
{ "url": "https://fastapi.tiangolo.com/reference/apirouter/" }
```

**Response:**
```json
{
  "status": "started",
  "pages_indexed": 0,
  "library_name": "fastapi.tiangolo.com",
  "message": "Crawl started. Poll /api/crawl/status for progress."
}
```

---

### `GET /api/crawl/status?url=<url>`

Polls the current indexing status for a given URL.

**Response states:** `crawling` → `parsing` → `indexing` → `done` | `error`
```json
{
  "status": "done",
  "pages": 42,
  "functions": 187
}
```

---

### `POST /api/process`

Runs the full RAG pipeline against the indexed documentation.

**Request body:**
```json
{
  "content": "How do I add a route to a router?",
  "source_url": "https://fastapi.tiangolo.com/reference/apirouter/",
  "use_reranker": true
}
```

**Response:**
```json
{
  "status": "success",
  "intent": "concept_explain",
  "processed_content": "To add a route to a router in FastAPI...",
  "recommended_functions": ["include_router"],
  "use_when": ["When you want to add a route to a router in FastAPI"],
  "avoid_when": ["When you have a simple API with few routes"],
  "code_snippet": "from fastapi import APIRouter...",
  "source_url": "https://fastapi.tiangolo.com/reference/apirouter/",
  "confidence": 1.0,
  "fixes": [],
  "retrieved_chunks": [...]
}
```

---

### `GET /api/functions?url=<url>`

Returns all parsed function objects for a completed crawl job.

---

## How It Works

### Intent Classification

Before retrieval, every query is classified into one of three intents:

| Intent | Trigger | Output format |
|---|---|---|
| `function_search` | Default — action-oriented queries | Ranked functions + use/avoid when + code |
| `error_fix` | Traceback detected or capitalized ErrorName | Root cause + numbered fixes + working code |
| `concept_explain` | "how", "why", "what", "difference", etc. | Plain explanation + example |

Ambiguous queries are resolved by the local LLM before retrieval.

### Retrieval

Both BM25 (keyword) and dense embedding (semantic) searches run in parallel. Results are merged using **Reciprocal Rank Fusion**:
score = Σ 1 / (k + rank_i)   where k = 60

The top-5 fused results are then re-scored by the cross-encoder reranker, and the top-3 are passed to the LLM.

### Grounded Generation

The LLM receives only the retrieved documentation chunks — no general knowledge is used. The system prompt enforces strict grounding:

> *"Answer ONLY using the provided documentation chunks. If the answer is not in the chunks, say so. Do not use general knowledge."*

The model is instructed to return a fixed JSON schema, ensuring the frontend always receives structured, renderable output.

---

## Troubleshooting

### `Database error: ... unable to open database file` (SQLite code 14)

ChromaDB persists metadata in SQLite under `BACKEND/data/chroma` (or under `DOCUMENTOR_DATA_DIR/chroma` if set). Try:

1. Ensure the backend process can **create and write** to that directory (not a read-only mount).
2. Set **`DOCUMENTOR_DATA_DIR`** to a folder you own, then restart the API.
3. Stop the server, delete the **`chroma`** folder inside your data directory (not the whole repo), and re-run indexing so Chroma can recreate a clean database.
4. Avoid running **multiple API workers** against the same Chroma path; use a single Uvicorn worker for local dev, or give each worker its own data directory.

### Ollama connection errors

Confirm `ollama serve` is running and that `OLLAMA_URL` / `OLLAMA_MODEL` in `BACKEND/.env` match your setup (`ollama list`).

### CORS / API unreachable from the browser

Set `VITE_API_BASE_URL` in `FRONTEND/.env` to the full origin of the FastAPI server (for example `http://localhost:8000`).

---

## Validation Scripts

Run these scripts to verify individual pipeline stages:
```bash
# Test the Cloudflare crawl connection
cd BACKEND
python test_crawl.py

# Test the parser against a live documentation page
python test_parser.py
# Output saved to: test_parser_output.json
```

---

## Contributing

Contributions are welcome. To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a pull request

Please ensure your changes do not break the existing parser or retrieval pipeline before submitting.

---

## Roadmap

- [ ] Sandboxed Python snippet executor (verify code runs before showing)
- [ ] VS Code extension
- [ ] Multi-library comparison mode
- [ ] Auto re-index on new library version detection
- [ ] Conversation history persistence
- [ ] GitHub Issues + Stack Overflow ingestion as additional context

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## Author

Built by **AKSHAT RAI** as part of an intermediate-level RAG systems project.

> *"Students waste hours scanning documentation for a function they can't name, to solve a problem they can only describe in plain English."* — This project exists to fix that.
