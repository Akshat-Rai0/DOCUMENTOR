from utils import process_input
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from model import UserInput, UserOutput, CrawlRequest, CrawlResponse
from utils import crawl_docs
from parser import parse_pages
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(
    title="Documentor API",
    description="Provides backend logic for user input processing."
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Specify frontend url in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores (replace with Redis + ChromaDB in Phase 3)
crawl_status_dict: dict = {}
parsed_store: dict = {}  # job_id → List[FunctionSchema]


@app.get("/")
def read_root():
    return {"message": "Welcome to Documentor API!"}


@app.post("/api/process", response_model=UserOutput)
async def handle_user_input(user_input: UserInput):
    """Endpoint to receive and process user input."""
    try:
        result = process_input(user_input.content)
        return UserOutput(processed_content=result, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from vector_store import check_cache, process_and_store

@app.post("/api/crawl", response_model=CrawlResponse)
async def start_crawl(req: CrawlRequest, background_tasks: BackgroundTasks):
    """Kick off a doc crawl + parse job. Returns immediately, runs in background."""
    job_id = req.url
    library_name = req.url.split("//")[-1].split("/")[0]
    crawl_status_dict[job_id] = {"status": "crawling", "pages": 0, "functions": 0}

    async def do_crawl():
        try:
            # Check cache before re-crawling
            if check_cache(req.url, library_name):
                crawl_status_dict[job_id] = {
                    "status": "done",
                    "pages": 0,
                    "functions": 0,
                    "message": "Used cached version (less than 7 days old)"
                }
                return

            # Phase 1 — crawl
            pages = await crawl_docs(req.url)
            crawl_status_dict[job_id]["pages"] = len(pages)

            # Phase 2 — parse
            crawl_status_dict[job_id]["status"] = "parsing"
            functions = parse_pages(pages, library=library_name)
            parsed_store[job_id] = functions

            # Phase 3 — process and store (chunk, embed, chroma, bm25)
            crawl_status_dict[job_id]["status"] = "indexing"
            process_and_store(functions, library=library_name, url=req.url, pages_count=len(pages))

            crawl_status_dict[job_id] = {
                "status": "done",
                "pages": len(pages),
                "functions": len(functions),
            }
        except Exception as e:
            crawl_status_dict[job_id] = {"status": "error", "error": str(e)}

    background_tasks.add_task(do_crawl)
    return CrawlResponse(
        status="started",
        pages_indexed=0,
        library_name=req.url.split("//")[-1].split("/")[0],
        message="Crawl started. Poll /api/crawl/status for progress.",
    )


@app.get("/api/crawl/status")
def crawl_status_check(url: str):
    return crawl_status_dict.get(url, {"status": "not_found"})


@app.get("/api/functions")
def get_functions(url: str):
    """Return parsed functions for a completed crawl job."""
    functions = parsed_store.get(url)
    if functions is None:
        raise HTTPException(status_code=404, detail="No parsed data for this URL. Run /api/crawl first.")
    return [f.model_dump() for f in functions]