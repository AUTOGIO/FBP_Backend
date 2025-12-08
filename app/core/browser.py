"""Browser automation scaffolding for Playwright/browser integration."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Playwright imports
try:
    from playwright.async_api import Browser, async_playwright  # type: ignore

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None  # type: ignore
    logger.warning(
        "Playwright not available. Install with: pip install playwright",
    )


def _resolve_extension_args() -> tuple[list[str], bool]:
    """Resolve extension launch args when fallback is enabled."""
    use_extension = os.getenv("USE_EXTENSION_FALLBACK", "false").lower() == "true"
    if not use_extension:
        return [], False

    project_root = Path(__file__).resolve().parents[2]
    extension_path = project_root / "fallback_extension"
    if not extension_path.exists():
        logger.warning(
            "USE_EXTENSION_FALLBACK set but fallback_extension not found at %s",
            extension_path,
        )
        return [], False

    args = [
        f"--disable-extensions-except={extension_path}",
        f"--load-extension={extension_path}",
    ]
    return args, True


async def get_browser(headless: bool = True) -> Browser:
    """Get Playwright browser instance.

    Args:
        headless: Whether to run browser in headless mode

    Returns:
        Playwright Browser instance

    Raises:
        RuntimeError: If Playwright is not available

    """
    if not PLAYWRIGHT_AVAILABLE:
        msg = (
            "Playwright not available. "
            "Install with: pip install playwright && playwright install chromium"
        )
        raise RuntimeError(msg)

    try:
        extension_args, force_headful = _resolve_extension_args()
        if force_headful and headless:
            logger.info(
                "USE_EXTENSION_FALLBACK enabled; forcing headful Chromium "
                "to load extension"
            )
            headless = False

        playwright = await async_playwright().__aenter__()
        return await playwright.chromium.launch(
            headless=headless,
            args=extension_args if extension_args else None,
        )
    except Exception as e:
        logger.exception(f"Error creating browser instance: {e}")
        msg = f"Failed to create browser instance: {e}"
        raise RuntimeError(msg) from e


class BrowserClient:
    """Browser automation client using Playwright."""

    def __init__(self, headless: bool = True) -> None:
        """Initialize browser client.

        Args:
            headless: Whether to run browser in headless mode

        """
        self.headless = headless
        self.browser: Browser | None = None
        self.initialized = False

    async def initialize(self) -> None:
        """Initialize browser session."""
        if not self.initialized:
            self.browser = await get_browser(headless=self.headless)
            self.initialized = True

    async def close(self) -> None:
        """Close browser session."""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.initialized = False

    async def navigate(self, url: str) -> str | None:
        """Navigate to URL and return page content.

        Args:
            url: URL to navigate to

        Returns:
            Page HTML content or None on error

        """
        if not self.initialized:
            await self.initialize()

        if not self.browser:
            logger.error("Browser not initialized")
            return None

        try:
            page = await self.browser.new_page()
            await page.goto(url, wait_until="networkidle")
            content: str = await page.content()
            await page.close()
            return content
        except Exception as e:
            logger.exception(f"Error navigating to {url}: {e}")
            return None
