"""
Browser Manager for handling shared browser with multiple tabs.
Each job application runs in its own tab for concurrent processing and VNC viewing.
"""

import asyncio
import logging
from typing import Dict, Tuple, Optional

from playwright.async_api import async_playwright, Browser, Page, Playwright

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages a shared browser instance with multiple tabs for concurrent job applications."""

    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.tabs: Dict[str, Tuple[Page, int]] = {}  # session_id -> (Page, tab_index)
        self.lock = asyncio.Lock()

    async def initialize(self):
        """
        Start browser once at application startup.
        Browser runs in non-headless mode for VNC viewing.
        """
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            logger.info("Browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def create_tab_for_session(self, session_id: str) -> Tuple[Page, int]:
        """
        Create new browser tab for a job application session.

        Args:
            session_id: Unique session identifier

        Returns:
            Tuple of (Page object, tab index)
        """
        async with self.lock:
            if not self.browser:
                raise RuntimeError("Browser not initialized. Call initialize() first.")

            # Create new page/tab
            page = await self.browser.new_page()

            # Get tab index (position in browser's page list)
            all_pages = self.browser.contexts[0].pages
            tab_index = all_pages.index(page)

            # Store mapping
            self.tabs[session_id] = (page, tab_index)

            logger.info(f"Created tab {tab_index} for session {session_id}")
            return page, tab_index

    async def get_tab(self, session_id: str) -> Optional[Tuple[Page, int]]:
        """
        Get existing tab for a session.

        Args:
            session_id: Session identifier

        Returns:
            Tuple of (Page, tab_index) or None if not found
        """
        return self.tabs.get(session_id)

    async def focus_tab(self, tab_index: int):
        """
        Bring specific tab to front (visible in VNC).

        Args:
            tab_index: Index of tab to focus
        """
        async with self.lock:
            if not self.browser:
                raise RuntimeError("Browser not initialized")

            all_pages = self.browser.contexts[0].pages
            if 0 <= tab_index < len(all_pages):
                await all_pages[tab_index].bring_to_front()
                logger.info(f"Focused tab {tab_index}")
            else:
                logger.warning(
                    f"Tab index {tab_index} out of range (total tabs: {len(all_pages)})"
                )

    async def close_tab(self, session_id: str):
        """
        Close tab after application completes.

        Args:
            session_id: Session identifier whose tab to close
        """
        async with self.lock:
            if session_id in self.tabs:
                page, tab_index = self.tabs[session_id]
                try:
                    await page.close()
                    logger.info(f"Closed tab {tab_index} for session {session_id}")
                except Exception as e:
                    logger.warning(f"Error closing tab for session {session_id}: {e}")
                finally:
                    del self.tabs[session_id]

    async def shutdown(self):
        """
        Shutdown browser and cleanup resources.
        Called during application shutdown.
        """
        async with self.lock:
            # Close all tabs
            for session_id in list(self.tabs.keys()):
                await self.close_tab(session_id)

            # Close browser
            if self.browser:
                await self.browser.close()
                logger.info("Browser closed")

            # Stop playwright
            if self.playwright:
                await self.playwright.stop()
                logger.info("Playwright stopped")

    def get_active_sessions(self) -> list[str]:
        """
        Get list of active session IDs with open tabs.

        Returns:
            List of session IDs
        """
        return list(self.tabs.keys())
