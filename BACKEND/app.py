from utils import process_input
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from model import UserInput, UserOutput, CrawlRequest, CrawlResponse
from utils import crawl_docs
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(
    title="Documentor API", 
    description="Provides backend logic for user input processing."
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Specify frontend url in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Documentor API!"}

@app.post("/api/process", response_model=UserOutput)
async def handle_user_input(user_input: UserInput):
    """
    Endpoint to receive and process user input.
    """
    try:
        # Pass logic to the utility function
        result = process_input(user_input.content)
        return UserOutput(processed_content=result, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

        
crawl_status = {}  # simple in-memory job tracker (use Redis in prod)

@app.post("/api/crawl", response_model=CrawlResponse)
async def start_crawl(req: CrawlRequest, background_tasks: BackgroundTasks):
    """Kick off a doc crawl job. Returns immediately, crawls in background."""
    job_id = req.url  # use URL as key for simplicity
    crawl_status[job_id] = {"status": "crawling", "pages": 0}

    async def do_crawl():
        try:
            pages = await crawl_docs(req.url)
            # TODO: chunk → embed → store in ChromaDB here (Week 2)
            crawl_status[job_id] = {"status": "done", "pages": len(pages)}
        except Exception as e:
            crawl_status[job_id] = {"status": "error", "error": str(e)}

    background_tasks.add_task(do_crawl)
    return CrawlResponse(status="started", pages_indexed=0,
                         library_name=req.url.split("//")[-1].split("/")[0],
                         message="Crawl started. Poll /api/crawl/status for progress.")

@app.get("/api/crawl/status")
def crawl_status_check(url: str):
    return crawl_status.get(url, {"status": "not_found"})