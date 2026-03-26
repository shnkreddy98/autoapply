import asyncio
import httpx
import logging
import random
import sys

from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright
from typing import Literal
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from autoapply.utils import read, write
from autoapply.logging import get_logger

get_logger()
logger = logging.getLogger(__name__)
DATA_DIR = "data/gsearch"


class GoogleSearchAutomation:
    def __init__(
        self,
        cache_file: str = f"{DATA_DIR}/cache/google_request_data.json",
        cache_duration_hours: int = 24,
    ):
        self.cache_file = cache_file
        self.cache_duration = timedelta(hours=cache_duration_hours)

    def is_cache_valid(self):
        """Check if cached request data is still valid"""
        if not Path(self.cache_file).exists():
            return False

        # Check file age
        file_time = datetime.fromtimestamp(Path(self.cache_file).stat().st_mtime)
        age = datetime.now() - file_time

        if age > self.cache_duration:
            logger.warning(
                f"Cache is {age.total_seconds() / 3600:.1f} hours old (max: {self.cache_duration.total_seconds() / 3600:.1f}h)"
            )
            return False

        logger.info(
            f"Cache is {age.total_seconds() / 3600:.1f} hours old (still valid)"
        )
        return True

    async def capture_fresh_data(self, search_query: str):
        """Capture fresh request data using Playwright"""
        logger.debug("\n" + "=" * 60)
        logger.debug("Capturing fresh request data with Playwright...")
        logger.debug("=" * 60)

        captured_request = None
        user_data_dir = Path.home() / ".playwright_google_profile"

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            )

            page = context.pages[0] if context.pages else await context.new_page()

            # Stealth injection
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            # Request interception
            async def capture_handler(route, request):
                nonlocal captured_request
                if "google.com/search" in request.url and "q=" in request.url:
                    captured_request = {
                        "url": request.url,
                        "method": request.method,
                        "headers": request.headers,
                    }
                await route.continue_()

            await page.route("**/*", capture_handler)

            # Navigate and search
            await page.goto("https://www.google.com", wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Handle cookie consent
            accept_btn = page.locator('button:has-text("Accept all")')
            if await accept_btn.count() > 0:
                await accept_btn.first.click()
                await asyncio.sleep(1)

            # Search
            search_box = await page.wait_for_selector(
                'textarea[name="q"], input[name="q"]'
            )
            await search_box.click()
            for char in search_query:
                await search_box.type(char, delay=50)
            await asyncio.sleep(0.3)
            await search_box.press("Enter")

            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            await asyncio.sleep(3)

            # Get cookies
            cookies = await context.cookies()
            await context.close()

            if not captured_request:
                logger.error("Failed to capture request")
                return False

            # Save data
            cookies_dict = {c["name"]: c["value"] for c in cookies}
            data = {
                "url": captured_request["url"],
                "method": captured_request["method"],
                "headers": dict(captured_request["headers"]),
                "cookies": cookies_dict,
                "captured_at": datetime.now().isoformat(),
            }

            await write(self.cache_file, data)

            logger.info(f"Captured and saved to {self.cache_file}")
            return True

    async def search_with_httpx(
        self,
        search_query: str = None,
        retries: int = 3,
        time_filter: Literal["h", "d", "w", "m", "y"] = "d",
    ):
        """
        Perform search using cached request data.
        If search_query is provided, modifies the URL; otherwise uses cached URL.
        time_filter: 'h' (hour), 'd' (day), 'w' (week), 'm' (month), 'y' (year)
        """
        if not Path(self.cache_file).exists():
            logger.error("No cached data found. Run capture first.")
            return None

        data = await read(self.cache_file)

        url = data["url"]

        # Optionally modify search query
        if search_query and search_query.startswith("http"):
            url = search_query
        elif search_query:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            params["q"] = [search_query]
            params["tbs"] = [f"qdr:{time_filter}"]
            if "oq" in params:
                params["oq"] = [search_query]

            url = urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    urlencode(params, doseq=True),
                    parsed.fragment,
                )
            )
            logger.info(f"Modified search query to: '{search_query}'")
        else:
            url = data["url"]

        logger.info("Making request with httpx...")

        # Retry loop with exponential backoff
        for attempt in range(retries):
            logger.info(
                f"Making request with httpx... (attempt {attempt + 1}/{retries})"
            )

            async with httpx.AsyncClient(
                timeout=30.0, follow_redirects=False
            ) as client:
                response = await client.request(
                    method=data["method"],
                    url=url,
                    headers=data["headers"],
                    cookies=data["cookies"],
                )

                # Handle CAPTCHA (302 redirect)
                if response.status_code == 302:
                    logger.warning(
                        f"CAPTCHA detected on attempt {attempt + 1}/{retries}"
                    )

                    if attempt < retries - 1:
                        # Exponential backoff: 10s, 30s, 90s
                        wait_time = 10 * (3**attempt)
                        logger.info(f"Waiting {wait_time} seconds before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error("Max retries reached. Google has blocked us.")
                        return None

                # Success
                if 200 <= response.status_code <= 299:
                    logger.info(f"Success! Got {len(response.text)} bytes")

                    # Check for CAPTCHA in HTML
                    if "unusual traffic" in response.text.lower():
                        logger.warning("Got CAPTCHA in response body!")
                        if attempt < retries - 1:
                            wait_time = 10 * (3**attempt)
                            logger.info(f"Waiting {wait_time} seconds before retry...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            return None

                    return response.text
                else:
                    logger.error(f"Request failed: {response.status_code}")
                    return None

        return None

    async def search_with_google_cse(
        self, search_query: str, pages: int = 5, api_key: str = "", cx: str = ""
    ) -> list[str]:
        """
        Search using Google Custom Search JSON API.
        Requires GOOGLE_API_KEY and GOOGLE_CSE_ID.
        Each page = 10 results; free tier = 100 queries/day.
        """
        job_links = []
        query_words = set(search_query.lower().split())
        for page_idx in range(pages):
            start = page_idx * 10 + 1  # 1, 11, 21, ...
            params = {
                "key": api_key,
                "cx": cx,
                "q": search_query,
                "num": 10,
                "start": start,
                "dateRestrict": "d1",  # last 24 hours
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params=params,
                )
            if response.status_code != 200:
                logger.error(f"Google CSE error {response.status_code}: {response.text[:200]}")
                break
            data = response.json()
            items = data.get("items", [])
            if not items:
                logger.info(f"Google CSE: no more results at page {page_idx + 1}")
                break
            for item in items:
                url = item.get("link", "")
                title = item.get("title", "")
                if not url.startswith("http"):
                    continue
                if not any(w in title.lower() for w in query_words):
                    logger.debug(f"CSE skipping '{title}' — no title overlap")
                    continue
                job_links.append(url)
            logger.info(f"Google CSE page {page_idx + 1}: {len(items)} results, {len(job_links)} total so far")
            await asyncio.sleep(0.5)
        return job_links

    async def search_with_duckduckgo(
        self, search_query: str, pages: int = 5
    ) -> list[str]:
        """
        Search using DuckDuckGo HTML endpoint (no API key required).
        DDG returns ~15 results/page. Uses POST for first page, offset for subsequent.
        """
        from urllib.parse import urlparse, parse_qs, unquote

        job_links = []
        query_words = set(search_query.lower().split())
        seen = set()

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        for page_idx in range(pages):
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    if page_idx == 0:
                        response = await client.post(
                            "https://html.duckduckgo.com/html/",
                            data={"q": search_query, "kl": "us-en"},
                            headers=headers,
                        )
                    else:
                        response = await client.post(
                            "https://html.duckduckgo.com/html/",
                            data={"q": search_query, "kl": "us-en", "s": str(page_idx * 30), "dc": str(page_idx * 30 + 1)},
                            headers=headers,
                        )

                if response.status_code != 200:
                    logger.warning(f"DDG returned {response.status_code} on page {page_idx + 1}")
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                results = soup.find_all("a", class_="result__a")
                if not results:
                    logger.info(f"DDG: no more results at page {page_idx + 1}")
                    break

                page_links = 0
                for a_tag in results:
                    href = a_tag.get("href", "")
                    title = a_tag.get_text(strip=True)

                    # DDG wraps URLs in redirect: //duckduckgo.com/l/?uddg=ENCODED
                    if "duckduckgo.com/l/" in href:
                        parsed = urlparse("https:" + href if href.startswith("//") else href)
                        uddg = parse_qs(parsed.query).get("uddg", [None])[0]
                        url = unquote(uddg) if uddg else ""
                    elif href.startswith("http"):
                        url = href
                    else:
                        continue

                    if not url or url in seen:
                        continue
                    if not any(w in title.lower() for w in query_words):
                        logger.debug(f"DDG skipping '{title}' — no title overlap")
                        continue
                    seen.add(url)
                    job_links.append(url)
                    page_links += 1

                logger.info(f"DDG page {page_idx + 1}: {page_links} new links, {len(job_links)} total")
                if page_links == 0:
                    break
                delay = random.uniform(2, 5)
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"DDG search error on page {page_idx + 1}: {e}")
                break

        return job_links

    async def auto_search(
        self, search_query: str, force_recapture: bool = False, pages: int = 10
    ) -> list[str]:
        """
        Search with automatic backend selection:
        1. Google Custom Search API (if GOOGLE_API_KEY + GOOGLE_CSE_ID are set)
        2. DuckDuckGo HTML (no credentials needed, automatic fallback)
        3. httpx with cached Google session (legacy, often blocked)
        """
        from autoapply.env import GOOGLE_API_KEY, GOOGLE_CSE_ID

        logger.info(f"Job search query: '{search_query}'")

        # 1. Google Custom Search API
        if GOOGLE_API_KEY and GOOGLE_CSE_ID:
            logger.info("Using Google Custom Search API")
            try:
                results = await self.search_with_google_cse(
                    search_query, pages=pages, api_key=GOOGLE_API_KEY, cx=GOOGLE_CSE_ID
                )
                if results:
                    return results
                logger.warning("Google CSE returned no results, falling back to DDG")
            except Exception as e:
                logger.error(f"Google CSE failed: {e}, falling back to DDG")

        # 2. DuckDuckGo (zero-config fallback)
        logger.info("Using DuckDuckGo search (no API key required)")
        try:
            results = await self.search_with_duckduckgo(search_query, pages=pages)
            if results:
                return results
            logger.warning("DuckDuckGo returned no results")
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")

        # 3. Legacy httpx with cached Google session
        logger.info("Falling back to cached Google session (may be blocked)")
        needs_capture = force_recapture or not self.is_cache_valid()
        if needs_capture:
            success = await self.capture_fresh_data(search_query)
            if not success:
                logger.error("All search backends failed")
                return []

        link = ""
        job_links = []
        for page_idx in range(1, pages + 1):
            q = search_query if len(link) == 0 else link
            html = await self.search_with_httpx(q)

            if html is None:
                logger.warning("CAPTCHA hit on legacy backend, attempting recapture...")
                success = await self.capture_fresh_data(search_query)
                if success:
                    html = await self.search_with_httpx(q, retries=1)
                if html is None:
                    logger.error(f"Legacy backend blocked. Stopping at page {page_idx}")
                    break

            if html:
                res = await self.parse(html, search_query, page_idx)
                link = res.get("next_page", None)
                job_links.extend(res.get("job_links", []))
                if link is None:
                    break
            else:
                break
            delay = random.uniform(3, 8)
            await asyncio.sleep(delay)

        return job_links

    async def parse(self, html_doc: str, query: str, idx: int) -> dict:
        """
        Parse HTML to get Title and URL links

        Args:
            html_doc: The HTML tag to parse
        Returns:
            The google search link
        """
        soup = BeautifulSoup(html_doc, "html.parser")
        data = soup.find(id="search")

        if not data:
            logger.error("Could not find search results container")

        company_dict: dict = {}
        job_links: list[str] = []
        # Find all <a> tags that contain an <h3> (most reliable structure)
        query_words = set(query.lower().split())
        for link in data.find_all("a", href=True):
            h3 = link.find("h3")
            if h3 and link.get("href"):
                url = link.get("href")
                title = h3.get_text(strip=True)

                if url.startswith(("http://", "https://")):
                    if url not in company_dict:
                        if not any(w in title.lower() for w in query_words):
                            logger.debug(f"Skipping '{title}' — no overlap with query '{query}'")
                            continue
                        company_dict[url] = title
                        job_links.append(url)

        logger.info(f"Found {len(company_dict)} unique job listings")

        if not company_dict:
            logger.error("No results extracted from page")
            return {}

        output_file = f"{DATA_DIR}/{date.today().strftime('%Y%m%d')}/jobs_page_{idx}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        logger.info(f"Writing jobs data to {output_file}")
        output_data = {"page_no": idx, "search_query": query, "results": company_dict}
        success = await write(output_file, output_data)

        if success:
            logger.info("Jobs written successfull")
            try:
                query = soup.find("a", attrs={"aria-label": f"Page {idx + 1}"}).get(
                    "href"
                )
            except AttributeError:
                logger.info("You have reached end of search results")
                return {"job_links": job_links}
            logger.debug(f"For Page {idx + 1}, Found query: {query}")
            return {
                "next_page": f"https://www.google.com{query}",
                "job_links": job_links,
            }

        else:
            logger.error("Writing companies failed")
            return {}


async def main(
    search: str,
    pages: int = 10,
    force_recapture: bool = False,
) -> list[str]:
    """main function"""
    automation = GoogleSearchAutomation(cache_duration_hours=24)
    return await automation.auto_search(search, force_recapture, pages)


if __name__ == "__main__":
    if len(sys.argv) % 2 == 1:
        logger.error("Pass proper parameters")
        logger.error("pass --search or -s with search query")
        logger.error("pass --force or -f to force recapture google search signature")
        logger.error("pass --pages or -p to scrape no. of pages, default=10")

    force = False

    args = {}
    for idx in range(1, len(sys.argv), 2):
        try:
            val = sys.argv[idx + 1]
        except IndexError:
            val = None
        args[sys.argv[idx].replace("--", "").replace("-", "")] = val

    force = args.get("force", False)
    search = args.get("search", "")
    pages = args.get("pages", 0)
    narrow_search = f"{search} +site:greenhouse.io"
    logger.info(
        f"Calling main with --search {narrow_search} and --force {force} and --pages {pages}"
    )
    links = asyncio.run(
        main(search=narrow_search, force_recapture=force, pages=int(pages))
    )
    logger.debug(f"Following links were scrapped: {links}")
