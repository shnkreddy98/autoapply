import logging
import os

from datetime import datetime
from playwright.async_api import async_playwright

from autoapply.logging import get_logger

get_logger()
logger = logging.getLogger(__name__)
applications_dir = "data/applications"

async def handle_cookie_popup(page):
    """
    Try to accept cookie consent popups using common patterns.
    Returns True if a popup was found and clicked, False otherwise.
    """
    # Common selectors and text patterns for cookie consent buttons
    selectors_to_try = [
        # By button text (most common)
        "button:has-text('Accept')",
        "button:has-text('Accept all')",
        "button:has-text('Accept All')",
        "button:has-text('Accept all and continue')",
        "button:has-text('I agree')",
        "button:has-text('I Agree')",
        "button:has-text('Agree')",
        "button:has-text('OK')",
        "button:has-text('Got it')",
        "button:has-text('Allow all')",
        "button:has-text('Consent')",

        # By common IDs and classes
        "#onetrust-accept-btn-handler",  # OneTrust
        "#accept-cookies",
        ".accept-cookies",
        "[data-testid='cookie-accept']",
        "[data-testid='accept-all-cookies']",
        ".cookie-consent-accept",
        ".cookies-accept-all",

        # By aria-label
        "[aria-label*='Accept']",
        "[aria-label*='Agree']",
    ]

    for selector in selectors_to_try:
        try:
            # Wait up to 2 seconds for this selector
            button = await page.wait_for_selector(selector, timeout=2000, state="visible")
            if button:
                await button.click()
                logger.info(f"Clicked cookie consent button: {selector}")
                await page.wait_for_timeout(500)  # Wait for popup to close
                return True
        except Exception:
            continue  # Try next selector

    logger.debug("No cookie popup found or already accepted")
    return False

async def save_page_as_markdown(url: str, company_name: str) -> bool:
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            # Set default timeout for all operations on this page
            page.set_default_timeout(timeout=60000)

            # Navigate to URL
            await page.goto(url)
            # handle cookies if any
            await handle_cookie_popup(page)

            # Wait for page to load
            await page.wait_for_timeout(10000)

            # Get the page content
            content = await page.inner_text('body')

            todays_date = datetime.now()
            output_dir = os.path.join(applications_dir, todays_date.strftime("%Y-%m-%d"), company_name)
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, "job_description.md")
            # Save to markdown file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {await page.title()}\n\n")
                f.write(f"Source: {url}\n\n")
                f.write("---\n\n")
                f.write(content)

            await browser.close()
            logger.info(f"Content saved to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error occured for {url}: {e}")
        return False