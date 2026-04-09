"""
utils.py — Crawler utilities.

Issue #19 additions:
  - robots.txt checking via urllib.robotparser
  - Per-domain crawl delay (0.5s between requests)
  - Timeout per domain (default 60s total)
"""

import asyncio
import logging
import os
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("documentor.crawler")

CLOUDFLARE_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CF_API_TOKEN")

# Per-domain crawl delay in seconds (Issue #19)
CRAWL_DELAY = float(os.getenv("DOCUMENTOR_CRAWL_DELAY", "0.5"))
# Max time in seconds to spend crawling a single domain
DOMAIN_TIMEOUT = float(os.getenv("DOCUMENTOR_DOMAIN_TIMEOUT", "120"))


def is_js_rendered(url: str) -> bool:
    """Heuristic: known JS-heavy doc hosts."""
    js_hosts = ["reactjs.org", "vuejs.org", "nextjs.org", "vitejs.dev", "jestjs.io"]
    return any(host in url for host in js_hosts)


# -- Issue #19 — robots.txt compliance ----------------------------------------

def _check_robots(base_url: str, user_agent: str = "*") -> RobotFileParser:
    """Fetch and parse robots.txt for the given base URL."""
    rp = RobotFileParser()
    robots_url = f"{base_url}/robots.txt"
    try:
        rp.set_url(robots_url)
        rp.read()
    except Exception:
        # If robots.txt is unreachable, allow everything
        rp.allow_all = True
    return rp


def _is_allowed(rp: RobotFileParser, url: str, user_agent: str = "*") -> bool:
    """Check if URL is allowed by robots.txt."""
    try:
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True  # Permissive on error


async def scrape_static(url: str, max_pages: int = 80) -> list[dict]:
    visited, results = set(), []
    parsed_url = urlparse(url)
    base = f"{parsed_url.scheme}://{parsed_url.netloc}"
    queue = [url]

    # Issue #19 — Check robots.txt
    rp = _check_robots(base)
    crawl_delay = rp.crawl_delay("*") or CRAWL_DELAY

    start_time = time.monotonic()

    async with httpx.AsyncClient(timeout=15) as client:
        while queue and len(visited) < max_pages:
            # Issue #19 — domain timeout
            elapsed = time.monotonic() - start_time
            if elapsed > DOMAIN_TIMEOUT:
                logger.warning(
                    "Domain timeout reached (%.1fs) for %s after %d pages",
                    elapsed, base, len(visited),
                )
                break

            page_url = queue.pop(0)
            if page_url in visited:
                continue

            # Issue #19 — robots.txt check
            if not _is_allowed(rp, page_url):
                logger.debug("Blocked by robots.txt: %s", page_url)
                continue

            visited.add(page_url)
            try:
                r = await client.get(page_url, follow_redirects=True)
                soup = BeautifulSoup(r.text, "html.parser")
                for tag in soup(["nav", "footer", "script", "style", "header"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)
                results.append({"url": page_url, "markdown": text})
                for a in soup.find_all("a", href=True):
                    href = urljoin(page_url, a["href"]).split("#")[0]
                    if href.startswith(base) and href not in visited:
                        queue.append(href)
            except Exception:
                logger.debug("Failed to fetch %s", page_url, exc_info=True)

            # Issue #19 — per-domain crawl delay
            if queue and len(visited) < max_pages:
                await asyncio.sleep(crawl_delay)

    return results


async def scrape_cloudflare(url: str) -> list[dict]:
    cf_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/browser-rendering/crawl"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "url": url,
        "depth": 3,
        "limit": 80,
        "allowedDomains": [urlparse(url).netloc],
    }

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(cf_url, json=payload, headers=headers)
        r.raise_for_status()
        job_id = r.json().get("result")

        for _ in range(30):
            await asyncio.sleep(4)
            status_r = await client.get(f"{cf_url}/{job_id}", headers=headers)
            data = status_r.json()
            result = data.get("result", {})
            if result.get("status") == "completed":
                return [
                    {"url": p["url"], "markdown": p.get("content", "")}
                    for p in result.get("pages", [])
                    if p.get("status") != "skipped"
                ]
            if result.get("status") in ("errored", "cancelled_due_to_timeout"):
                raise RuntimeError(f"Cloudflare crawl failed: {result.get('status')}")

    raise TimeoutError("Cloudflare crawl timed out")


async def crawl_docs(url: str) -> list[dict]:
    """Entry point — picks the right scraper automatically."""
    if is_js_rendered(url) and CLOUDFLARE_ACCOUNT_ID:
        return await scrape_cloudflare(url)
    return await scrape_static(url)