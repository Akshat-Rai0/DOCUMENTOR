import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os

CLOUDFLARE_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CF_API_TOKEN")

def is_js_rendered(url: str) -> bool:
    """Heuristic: known JS-heavy doc hosts."""
    js_hosts = ["reactjs.org", "vuejs.org", "nextjs.org", "vitejs.dev", "jestjs.io"]
    return any(host in url for host in js_hosts)

def process_input(content: str) -> str:
    """Process user input."""
    # Placeholder for actual processing logic
    return f"Processed: {content}"

async def scrape_static(url: str, max_pages: int = 80) -> list[dict]:
    """Fast scraper for static HTML doc sites (Pandas, FastAPI, SQLAlchemy etc.)"""
    visited, results = set(), []
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    async def crawl(page_url: str):
        if page_url in visited or len(visited) >= max_pages:
            return
        visited.add(page_url)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(page_url, follow_redirects=True)
            soup = BeautifulSoup(r.text, "html.parser")
            # Remove nav/footer noise
            for tag in soup(["nav", "footer", "script", "style", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            results.append({"url": page_url, "markdown": text})
            # Follow internal links only
            for a in soup.find_all("a", href=True):
                href = urljoin(page_url, a["href"]).split("#")[0]
                if href.startswith(base) and href not in visited:
                    await crawl(href)
        except Exception:
            pass

    await crawl(url)
    return results

async def scrape_cloudflare(url: str) -> list[dict]:
    """Async crawl via Cloudflare Browser Rendering /crawl endpoint."""
    cf_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/browser-rendering/crawl"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "url": url,
        "responseFormat": "markdown",
        "maxDepth": 3,
        "maxPages": 80,
        "allowedDomains": [urlparse(url).netloc],
    }

    async with httpx.AsyncClient(timeout=120) as client:
        # Step 1: start the job
        r = await client.post(cf_url, json=payload, headers=headers)
        r.raise_for_status()
        job_id = r.json()["id"]

        # Step 2: poll until done
        import asyncio
        for _ in range(30):
            await asyncio.sleep(4)
            status_r = await client.get(f"{cf_url}/{job_id}", headers=headers)
            data = status_r.json()
            result = data.get("result", {})
            if result.get("status") == "done":
                return [{"url": p["url"], "markdown": p["content"]} for p in result.get("pages", [])]
            if result.get("status") == "failed":
                raise RuntimeError("Cloudflare crawl job failed")

    raise TimeoutError("Cloudflare crawl timed out")

async def crawl_docs(url: str) -> list[dict]:
    """Entry point — picks the right scraper automatically."""
    if is_js_rendered(url) and CLOUDFLARE_ACCOUNT_ID:
        return await scrape_cloudflare(url)
    return await scrape_static(url)