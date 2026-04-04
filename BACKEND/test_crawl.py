import asyncio
import httpx
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()



CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
CF_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/browser-rendering/crawl"


def strip_html(raw: str) -> str:
    from html.parser import HTMLParser
    class Stripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text = []
        def handle_data(self, data):
            self.text.append(data)
    s = Stripper()
    s.feed(raw)
    return " ".join(s.text).strip()

# updated payload
target_url = "https://fastapi.tiangolo.com"
payload = {
    "url": target_url,
    "depth": 1,
    "limit": 3,
    "allowedDomains": [urlparse(target_url).netloc],  # stay on fastapi.tiangolo.com only
}

async def test_crawl():
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "url": "https://fastapi.tiangolo.com",
        "depth": 1,
        "limit": 3,
    }

    print("=== DocuMentor Cloudflare Crawl Test ===\n")
    print(f"Account ID loaded : {'YES' if CF_ACCOUNT_ID else 'NO — check .env'}")
    print(f"API Token loaded  : {'YES' if CF_API_TOKEN else 'NO — check .env'}")
    print(f"Target URL        : {payload['url']}")
    print(f"Max pages         : {payload['limit']}\n")

    async with httpx.AsyncClient(timeout=30) as client:

        # Step 1 — start the job
        print("Step 1: Starting crawl job...")
        r = await client.post(CF_URL, json=payload, headers=headers)

        if r.status_code == 403:
            print("FAILED — 403 Forbidden")
            print("  Check: Does your token have Browser Rendering:Edit permission?")
            return
        if r.status_code == 401:
            print("FAILED — 401 Unauthorized")
            print("  Check: Is your CF_API_TOKEN correct in .env?")
            return
        if not r.is_success:
            print(f"FAILED — HTTP {r.status_code}")
            print(f"  Response: {r.text}")
            return

        job = r.json()
        job_id = job.get("result")
        print(f"Job started — ID: {job_id}\n")

        if not job_id:
            print("FAILED — No job ID returned")
            print(f"  Full response: {job}")
            return

        # Step 2 — poll for result
        print("Step 2: Polling for result (this may take 20-60s)...")
        async with httpx.AsyncClient(timeout=30) as poll_client:
            for attempt in range(30):
                await asyncio.sleep(5)
                status_r = await poll_client.get(
                    f"{CF_URL}/{job_id}?limit=1",
                    headers=headers
                )
                data = status_r.json()
                status = data.get("result", {}).get("status", "unknown")
                print(f"  [{attempt + 1}] status: {status}")

                # if status == "completed":
                #     # fetch full results without ?limit=1
                #     full_r = await poll_client.get(
                #         f"{CF_URL}/{job_id}",
                #         headers=headers
                #     )
                #     full_data = full_r.json()
                #     pages = full_data.get("result", {}).get("pages", [])
                #     print(f"\nSUCCESS — {len(pages)} pages crawled\n")
                #     for i, page in enumerate(pages):
                #         print(f"  Page {i + 1}: {page.get('url')}")
                #         preview = page.get("content", "")[:200].replace("\n", " ")
                #         print(f"  Preview: {preview}...\n")
                #     return
                if status == "completed":
                    full_r = await poll_client.get(f"{CF_URL}/{job_id}", headers=headers)
                    full_data = full_r.json()
                    pages = full_data.get("result", {}).get("pages", [])
                    crawled = [p for p in pages if p.get("status") != "skipped"]
                    print(f"\nSUCCESS — {len(crawled)} pages crawled ({len(pages) - len(crawled)} skipped)\n")
                    for i, page in enumerate(crawled):
                        clean = strip_html(page.get("content", ""))[:300].replace("\n", " ")
                        print(f"  Page {i+1}: {page.get('url')}")
                        print(f"  Preview: {clean}...\n")
                    return

                if status in ("errored", "cancelled_due_to_timeout",
                              "cancelled_due_to_limits", "cancelled_by_user"):
                    print(f"\nFAILED — crawl job status: {status}")
                    print(f"  Details: {data}")
                    return

        print("\nTIMEOUT — job did not complete in 150 seconds")
        print(f"  Last known job ID: {job_id}")
        print("  You can manually check:")
        print(f"  curl -X GET '{CF_URL}/{job_id}' -H 'Authorization: Bearer $CF_API_TOKEN'")

asyncio.run(test_crawl())