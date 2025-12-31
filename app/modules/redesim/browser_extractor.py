"""Browser Extractor for REDESIM
Handles HTML extraction with Cursor Browser Agent and Playwright CDP fallback.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from cursor import browser

    CURSOR_AVAILABLE = True
except ImportError:
    CURSOR_AVAILABLE = False
    # Silent: Cursor browser is only available inside Cursor IDE, not in terminal.
    # Playwright is the primary automation method for terminal execution.


class BrowserExtractor:
    """Extract data from browser using Cursor Browser Agent or Playwright fallback."""

    EMAIL_RE = re.compile(
        r"([a-z0-9_.+-]+@[a-z0-9-]+\.[a-z0-9-.]+)",
        re.IGNORECASE,
    )
    PROCESSO_RE = re.compile(r"\b2\d{8,}-\d\b")
    CNPJ_RE = re.compile(r"\d{2,3}\.\d{3}\.\d{3}/\d{4}-\d{2}")

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize browser extractor.

        Args:
            config: Optional configuration dictionary

        """
        self.config = config or {}

    def normalize_text(self, text: str | None) -> str:
        """Normalize text by removing extra whitespace."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def deduplicate_emails(self, emails: list[str]) -> list[str]:
        """Remove duplicate emails while preserving order."""
        seen = set()
        result = []
        for email in emails:
            key = email.lower()
            if key not in seen:
                seen.add(key)
                result.append(email)
        return result

    async def extract_from_cursor(self) -> list[dict[str, Any]]:
        """Extract data from active Cursor browser tab.

        Returns:
            List of process data dictionaries

        """
        if not CURSOR_AVAILABLE:
            msg = "Cursor Browser API not available"
            raise RuntimeError(msg)

        logger.info("Extracting data from Cursor browser tab...")

        try:
            page = await browser.page()
            html = await page.content()
            logger.info(f"Retrieved HTML content ({len(html)} characters)")
            return await self._extract_processes_from_html(html)
        except Exception as e:
            logger.exception(f"Error during extraction: {e}")
            raise

    async def _extract_processes_from_html(
        self,
        html: str,
    ) -> list[dict[str, Any]]:
        """Extract process data from HTML content."""
        row_pattern = self.config.get("browser", {}).get(
            "results_row_pattern",
            r"<tr[^>]*>.*?</tr>",
        )
        rows = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)
        logger.info(f"Found {len(rows)} table rows")

        results = []
        extraction_config = self.config.get("extraction", {})

        for i, row in enumerate(rows, 1):
            processo_match = re.search(
                extraction_config.get(
                    "campo_processo",
                    self.PROCESSO_RE.pattern,
                ),
                row,
                re.IGNORECASE,
            )
            razao_match = re.search(
                extraction_config.get("campo_razao", r"(?i)raz[aã]o\s*social"),
                row,
                re.IGNORECASE,
            )
            cnpj_match = re.search(
                extraction_config.get("campo_cnpj", self.CNPJ_RE.pattern),
                row,
                re.IGNORECASE,
            )
            emails = self.EMAIL_RE.findall(row)
            emails = self.deduplicate_emails(emails)

            if processo_match and razao_match:
                process_data = {
                    "processo": self.normalize_text(processo_match.group(0)),
                    "razao_social": self.normalize_text(razao_match.group(0)),
                    "cnpj": (
                        self.normalize_text(cnpj_match.group(0)) if cnpj_match else ""
                    ),
                    "emails": emails,
                    "row_index": i,
                    "raw_text": self.normalize_text(row),
                }
                results.append(process_data)
                logger.info(
                    f"Extracted {process_data['processo']} ({len(emails)} emails)",
                )

        return results

    async def get_raw_html(self) -> str:
        """Get raw HTML content with cursor/playwright fallback.

        Returns:
            HTML content as string

        """
        # Try cursor first if available
        if CURSOR_AVAILABLE:
            logger.info("Attempting to get HTML from Cursor browser tab...")
            try:
                page = await browser.page()
                html = await page.content()
                logger.info(
                    f"Retrieved HTML from Cursor ({len(html)} characters)",
                )
                return html
            except Exception as e:
                logger.warning(
                    f"Cursor failed: {e}, falling back to Playwright",
                )

        # Fallback to playwright
        logger.info(
            "Using Playwright fallback to navigate and extract HTML...",
        )
        return await self._get_html_with_playwright()

    async def capture_page(self, url: str | None = None) -> str:
        """Capture page content using Playwright.

        Args:
            url: Optional URL to navigate to. If None, uses config or settings.

        Returns:
            HTML content as string

        """
        try:
            from app.core.browser import get_browser

            browser_instance = await get_browser()
            page = await browser_instance.new_page()

            if url is None:
                url = (
                    self.config.get("runtime", {}).get("base_url")
                    or getattr(settings, "REDESIM_BASE_URL", None)
                    or "https://atf.sefaz.pb.gov.br/"
                )

            logger.info(f"Navigating to: {url}")
            await page.goto(url, wait_until="networkidle")

            # Wait a bit more for dynamic content
            await page.wait_for_timeout(2000)

            html = await page.content()
            logger.info(
                f"Retrieved HTML via Playwright ({len(html)} characters)",
            )

            await page.close()
            return html

        except ImportError:
            logger.exception(
                "Playwright not installed. Run: pip install playwright && playwright install chromium",
            )
            msg = "Playwright not available for HTML extraction"
            raise RuntimeError(msg) from None
        except Exception as e:
            logger.exception(f"Playwright extraction failed: {e}")
            msg = f"Failed to extract HTML with Playwright: {e}"
            raise RuntimeError(msg) from e

    async def cursor_fallback_capture(self, url: str | None = None) -> str:
        """Capture page content using Cursor Browser Agent with Playwright fallback.

        Args:
            url: Optional URL to navigate to. If None, uses config or settings.

        Returns:
            HTML content as string

        """
        # Try cursor first if available
        if CURSOR_AVAILABLE:
            logger.info("Attempting to get HTML from Cursor browser tab...")
            try:
                page = await browser.page()
                html = await page.content()
                logger.info(
                    f"Retrieved HTML from Cursor ({len(html)} characters)",
                )
                return html
            except Exception as e:
                logger.warning(
                    f"Cursor failed: {e}, falling back to Playwright",
                )

        # Fallback to playwright
        logger.info(
            "Using Playwright fallback to navigate and extract HTML...",
        )
        return await self.capture_page(url)

    async def _get_html_with_playwright(self) -> str:
        """Playwright fallback implementation with proper error handling."""
        return await self.cursor_fallback_capture()
