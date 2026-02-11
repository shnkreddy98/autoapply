import asyncio
import httpx
import logging
import random
import sys

from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright
from typing import Optional, Literal
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from autoapply.utils import read, write
from autoapply.logging import get_logger

get_logger()
logger = logging.getLogger(__name__)
DATA_DIR = "data/gsearch"


class GoogleSearchAutomation:
    def __init__(
        self,
        cache_file: str =f"{DATA_DIR}/cache/google_request_data.json",
        cache_duration_hours: int =24,
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
            try:
                accept_btn = page.locator('button:has-text("Accept all")')
                if await accept_btn.count() > 0:
                    await accept_btn.first.click()
                    await asyncio.sleep(1)
            except:
                pass

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

    async def search_with_httpx(self, search_query: str = None, retries: int = 3, time_filter: Literal["h", "d", "w", "m", "y"] = "d"):
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
            logger.info(f"Making request with httpx... (attempt {attempt + 1}/{retries})")

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
                response = await client.request(
                    method=data["method"],
                    url=url,
                    headers=data["headers"],
                    cookies=data["cookies"],
                )

                # Handle CAPTCHA (302 redirect)
                if response.status_code == 302:
                    logger.warning(f"CAPTCHA detected on attempt {attempt + 1}/{retries}")
                    
                    if attempt < retries - 1:
                        # Exponential backoff: 10s, 30s, 90s
                        wait_time = 10 * (3 ** attempt)
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
                            wait_time = 10 * (3 ** attempt)
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

    async def auto_search(
        self, search_query: str, force_recapture: bool = False, pages: int = 10
    ):
        """
        Automatically decides whether to use cache or recapture

        Args:
            search_query: The search query
            force_recapture: Force a fresh capture even if cache is valid
        """
        logger.debug("\n" + "=" * 60)
        logger.debug("Google Search Automation")
        logger.debug(f"Query: '{search_query}'")
        logger.debug("=" * 60)

        # Check if we need to capture
        needs_capture = force_recapture or not self.is_cache_valid()

        if needs_capture:
            success = await self.capture_fresh_data(search_query)
            if not success:
                return None

        # Make request with httpx
        logger.debug("\n" + "=" * 60)
        logger.debug("Using httpx (fast, no browser overhead)...")
        logger.debug("=" * 60)

        link = ""
        job_links = []
        for page_idx in range(1, pages + 1):
            q = search_query if len(link) == 0 else link
            html = await self.search_with_httpx(q)

            if html is None:
                # Try recapturing once
                logger.warning("CAPTCHA hit! Attempting to recapture headers...")
                success = await self.capture_fresh_data(search_query)
            
                if success:
                    # Retry this page with fresh headers
                    html = await self.search_with_httpx(q, retries=1)
                    
                if html is None:
                    logger.error(f"Failed even after recapture. Stopping at page {page_idx}")
                    break

            if html:
                res = await self.parse(html, search_query, page_idx)
                link = res.get("next_page", None)
                job_links.extend(res.get("job_links", []))
                if link is None:
                    logger.info(f"Pagination stopped at page {page_idx}")
                    break
            else:
                logger.error("Failed to get results. Try force_recapture=True")
                return None
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
        for link in data.find_all("a", href=True):
            h3 = link.find("h3")
            if h3 and link.get("href"):
                url = link.get("href")
                title = h3.get_text(strip=True)
                
                if url.startswith(("http://", "https://")):
                    if url not in company_dict:
                        company_dict[url] = title
                        job_links.append(url)
        
        logger.info(f"Found {len(company_dict)} unique job listings")
        
        if not company_dict:
            logger.error("No results extracted from page")
            return {}
        

        output_file = f"{DATA_DIR}/{date.today().strftime('%Y%m%d')}/jobs_page_{idx}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        logger.info(f"Writing jobs data to {output_file}")
        output_data = {
            "page_no": idx,
            "search_query": query,
            "results": company_dict
        }
        success = await write(output_file, output_data)

        if success:
            logger.info("Jobs written successfull")
            try:
                query = soup.find("a", attrs={"aria-label": f"Page {idx + 1}"}).get("href")
            except AttributeError:
                logger.info("You have reached end of search results")
                return {
                    "job_links": job_links
                }
            logger.debug(f"For Page {idx + 1}, Found query: {query}")
            return {
                "next_page": f"https://www.google.com{query}",
                "job_links": job_links
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
    links = asyncio.run(main(search=narrow_search, force_recapture=force, pages=int(pages)))
    logger.debug(f"Following links were scrapped: {links}")
