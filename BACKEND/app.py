import logging
import traceback

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from model import UserInput, UserOutput, CrawlRequest, CrawlResponse
from url_utils import extract_library_name
from utils import crawl_docs
from parser import parse_pages
from pipeline import run_rag_pipeline
from job_store import create_job, update_job, get_job
from dotenv import load_dotenv
from fastapi.concurrency import run_in_threadpool

# -- Rate limiting (Issue #18) ------------------------------------------------
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

logger = logging.getLogger("documentor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Documentor API",
    description="Provides backend logic for user input processing."
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Specify frontend url in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to Documentor API!"}


@app.post("/api/process", response_model=UserOutput)
@limiter.limit("10/minute")
async def handle_user_input(request: Request, user_input: UserInput):
    try:
        result = await run_in_threadpool(
            run_rag_pipeline,
            query=user_input.content,
            source_url=user_input.source_url or user_input.context,
            use_reranker=user_input.use_reranker,
        )
        return UserOutput(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error in /api/process")
        raise HTTPException(status_code=500, detail=str(e))


# -- Streaming endpoint (Issue #2) --------------------------------------------
@app.post("/api/process/stream")
@limiter.limit("10/minute")
async def handle_user_input_stream(request: Request, user_input: UserInput):
    """SSE streaming endpoint. Sends intermediate chunks then a final JSON payload."""
    from llm import generate_grounded_answer_stream
    from intent_classifier import classify_intent
    from llm import disambiguate_intent_with_local_llm
    from reranker import rerank_candidates
    from retriever import hybrid_retrieve
    from pipeline import _serialize_chunks

    async def event_stream():
        try:
            # 1. Classify intent
            intent_result = await run_in_threadpool(
                classify_intent,
                user_input.content.strip(),
                llm_disambiguator=disambiguate_intent_with_local_llm,
            )

            # 2. Retrieve
            retrieval_payload = await run_in_threadpool(
                hybrid_retrieve,
                query=user_input.content.strip(),
                source_url=user_input.source_url or user_input.context,
            )
            fused_chunks = retrieval_payload.get("fused_results", [])

            # 3. Rerank
            final_chunks = await run_in_threadpool(
                rerank_candidates,
                query=user_input.content.strip(),
                candidates=fused_chunks,
                top_k=3,
                enabled=user_input.use_reranker,
            )

            # 4. Stream LLM answer
            accumulated = ""
            for token in generate_grounded_answer_stream(
                query=user_input.content.strip(),
                intent=intent_result.intent,
                chunks=final_chunks,
            ):
                accumulated += token
                yield f"data: {token}\n\n"

            # 5. Send final structured payload
            import json as _json
            from llm import _extract_json_object, _normalize_answer
            try:
                parsed = _extract_json_object(accumulated)
                answer = _normalize_answer(parsed, chunks=final_chunks)
            except Exception:
                from llm import _fallback_answer
                answer = _fallback_answer(intent=intent_result.intent, chunks=final_chunks)

            # Override confidence with reranker score (Issue #9)
            if final_chunks and final_chunks[0].get("reranker_score") is not None:
                import math
                raw = float(final_chunks[0]["reranker_score"])
                answer["confidence"] = 1.0 / (1.0 + math.exp(-raw))

            explanation = answer.get("explanation") or "The answer is not in the retrieved documentation chunks."
            final_payload = {
                "status": "success",
                "intent": intent_result.intent,
                "processed_content": explanation,
                **answer,
                "retrieved_chunks": _serialize_chunks(final_chunks),
            }
            yield f"event: done\ndata: {_json.dumps(final_payload)}\n\n"

        except Exception as e:
            logger.exception("Error in streaming endpoint")
            import json as _json
            yield f"event: error\ndata: {_json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


from vector_store import check_cache, process_and_store

@app.post("/api/crawl", response_model=CrawlResponse)
@limiter.limit("5/minute")
async def start_crawl(request: Request, req: CrawlRequest, background_tasks: BackgroundTasks):
    """Kick off a doc crawl + parse job. Returns immediately, runs in background."""
    job_id = req.url
    library_name = extract_library_name(req.url)
    create_job(job_id)

    async def do_crawl():
        try:
            # Check cache before re-crawling
            if check_cache(req.url, library_name):
                update_job(
                    job_id,
                    status="done",
                    pages=0,
                    functions=0,
                    message="Used cached version (less than 7 days old)",
                )
                return

            # Phase 1 — crawl
            pages = await crawl_docs(req.url)
            update_job(job_id, pages=len(pages))

            # Phase 2 — parse
            update_job(job_id, status="parsing")
            functions = parse_pages(pages, library=library_name)

            # Phase 3 — process and store (chunk, embed, chroma, bm25)
            update_job(job_id, status="indexing")
            process_and_store(functions, library=library_name, url=req.url, pages_count=len(pages))

            update_job(job_id, status="done", pages=len(pages), functions=len(functions))
        except Exception as e:
            # Issue #17 — log the full traceback, store sanitised message
            logger.exception("Crawl job failed for %s", req.url)
            update_job(
                job_id,
                status="error",
                error=str(e),
                message=traceback.format_exc()[-500:],
            )

    background_tasks.add_task(do_crawl)
    return CrawlResponse(
        status="started",
        pages_indexed=0,
        library_name=library_name,
        message="Crawl started. Poll /api/crawl/status for progress.",
    )


@app.get("/api/crawl/status")
def crawl_status_check(url: str):
    return get_job(url)


@app.get("/api/functions")
def get_functions(url: str):
    """Return parsed functions for a completed crawl job."""
    # parsed_store was in-memory — now we just report that
    # functions are available via the vector store / ChromaDB
    from vector_store import build_collection_name, chroma_client
    lib = extract_library_name(url)
    col_name = build_collection_name(lib)
    try:
        collection = chroma_client.get_collection(name=col_name)
        count = collection.count()
        return {"library": lib, "collection": col_name, "function_count": count}
    except Exception:
        raise HTTPException(status_code=404, detail="No parsed data for this URL. Run /api/crawl first.")