"""Playwright CDP Extractor for REDESIM
Fallback extractor using Playwright for standalone execution outside Cursor.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Playwright imports
try:
    from playwright.async_api import Browser, async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning(
        "Playwright not available. Install with: pip install playwright",
    )

# Email regex pattern
EMAIL_RE = re.compile(
    r"([a-z0-9_.+-]+@[a-z0-9-]+\.[a-z0-9-.]+)", re.IGNORECASE,
)

# Process number pattern (Brazilian format)
PROCESSO_RE = re.compile(r"\b2\d{8,}-\d\b")

# CNPJ pattern (Brazilian format)
CNPJ_RE = re.compile(r"\d{2,3}\.\d{3}\.\d{3}/\d{4}-\d{2}")


class PlaywrightExtractor:
    """Extract REDESIM data using Playwright CDP."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize Playwright extractor.

        Args:
            config: Optional configuration dictionary

        """
        self.config = config or {}
        if not PLAYWRIGHT_AVAILABLE:
            msg = "Playwright not available. Install with: pip install playwright && playwright install chromium"
            raise RuntimeError(
                msg,
            )

    @staticmethod
    def normalize_text(text: str | None) -> str:
        """Normalize text by removing extra whitespace."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def deduplicate_emails(emails: list[str]) -> list[str]:
        """Remove duplicate emails while preserving order."""
        seen = set()
        result = []
        for email in emails:
            key = email.lower()
            if key not in seen:
                seen.add(key)
                result.append(email)
        return result

    async def get_browser(self, headless: bool = True) -> Browser:
        """Get Playwright browser instance.

        Args:
            headless: Whether to run browser in headless mode

        Returns:
            Playwright Browser instance

        """
        playwright = await async_playwright().__aenter__()
        return await playwright.chromium.launch(headless=headless)

    async def extract_all(self) -> list[dict[str, Any]]:
        """Extract process data using Playwright CDP.

        Returns:
            List of dictionaries containing process metadata

        """
        logger.info("Extracting data using Playwright CDP...")

        try:
            # Get browser configuration
            browser_config = self.config.get("browser", {})
            headless = browser_config.get("headless", True)
            url = browser_config.get("url", "")

            if not url:
                # Try to get from settings
                url = (
                    getattr(settings, "REDESIM_BASE_URL", None)
                    or "https://atf.sefaz.pb.gov.br/"
                )
                logger.info(f"Using default URL: {url}")

            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(headless=headless)
                page = await browser.new_page()

                logger.info(f"Navigating to: {url}")
                await page.goto(url)

                # Wait for page to load
                await page.wait_for_load_state("networkidle")

                # Get page content
                html = await page.content()
                logger.info(f"Retrieved HTML content ({len(html)} characters)")

                # Extract results
                results = await self._extract_processes_from_html(html)

                await browser.close()

                logger.info(f"Extracted {len(results)} processes")
                return results

        except Exception as e:
            logger.exception(f"Error during extraction: {e}")
            raise

    async def extract_from_url(
        self,
        url: str,
        headless: bool = True,
    ) -> list[dict[str, Any]]:
        """Extract process data from a specific URL.

        Args:
            url: Target URL to extract from
            headless: Whether to run browser in headless mode

        Returns:
            List of dictionaries containing process metadata

        """
        logger.info(f"Extracting data from URL: {url}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless)
                page = await browser.new_page()

                await page.goto(url)
                await page.wait_for_load_state("networkidle")

                html = await page.content()
                results = await self._extract_processes_from_html(html)

                await browser.close()
                return results

        except Exception as e:
            logger.exception(f"Error extracting from URL: {e}")
            raise

    async def _extract_processes_from_html(
        self,
        html: str,
    ) -> list[dict[str, Any]]:
        """Extract process data from HTML content using configured patterns."""
        # Get row pattern from config
        row_pattern = self.config.get("browser", {}).get(
            "results_row_pattern",
            r"<tr[^>]*>.*?</tr>",
        )

        # Find all table rows
        rows = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)
        logger.info(f"Found {len(rows)} table rows")

        results = []
        extraction_config = self.config.get("extraction", {})

        for i, row in enumerate(rows, 1):
            try:
                # Extract process number
                processo_match = re.search(
                    extraction_config.get(
                        "campo_processo", PROCESSO_RE.pattern,
                    ),
                    row,
                    re.IGNORECASE,
                )

                # Extract company name
                razao_match = re.search(
                    extraction_config.get(
                        "campo_razao", r"(?i)raz[aã]o\s*social",
                    ),
                    row,
                    re.IGNORECASE,
                )

                # Extract CNPJ
                cnpj_match = re.search(
                    extraction_config.get("campo_cnpj", CNPJ_RE.pattern),
                    row,
                    re.IGNORECASE,
                )

                # Extract emails
                emails = EMAIL_RE.findall(row)
                emails = self.deduplicate_emails(emails)

                # Only add if we have at least process number and company name
                if processo_match and razao_match:
                    process_data = {
                        "processo": self.normalize_text(
                            processo_match.group(0),
                        ),
                        "razao_social": self.normalize_text(
                            razao_match.group(0),
                        ),
                        "cnpj": (
                            self.normalize_text(cnpj_match.group(0))
                            if cnpj_match
                            else ""
                        ),
                        "emails": emails,
                        "row_index": i,
                    }
                    results.append(process_data)

                    logger.debug(
                        f"{i} {process_data['processo']} "
                        f"({len(emails)} emails) - {process_data['razao_social'][:50]}...",
                    )

            except Exception as e:
                logger.warning(f"Error processing row {i}: {e}")
                continue

        return results

    def save_results(
        self,
        results: list[dict[str, Any]],
        output_path: Path | None = None,
    ) -> Path:
        """Save extraction results to JSON file.

        Args:
            results: List of extracted process data
            output_path: Optional output file path

        Returns:
            Path to saved JSON file

        """
        if output_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            output_path = (
                project_root / "traces" / "playwright_extraction_results.json"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"Results saved to: {output_path}")
        return output_path
