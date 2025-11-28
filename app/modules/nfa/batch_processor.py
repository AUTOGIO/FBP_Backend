"""Batch NFA Processor
Handles batch processing of multiple NFAs with error handling and retry logic.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    async_playwright,
)

from app.core.logging_config import setup_logger
from app.modules.nfa.atf_login import (
    ATF_BASE_URL,
    atf_manual_login,
    perform_login,
    select_function_fis_1698,
    wait_for_post_login,
)
from app.modules.nfa.form_filler import fill_nfa_form_complete
from app.modules.nfa.nfa_context import (
    NFAContext,
    get_page_from_context,
    resolve_nfa_context,
    wait_for_nfa_ready,
)

logger = setup_logger(__name__)


class BatchNFAProcessor:
    """Batch NFA processing handler with retry logic and error recovery."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize batch processor.

        Args:
            config: Optional configuration dictionary

        """
        self.config = config or {}
        self.results: list[dict[str, Any]] = []
        self.success_count = 0
        self.failure_count = 0
        self.start_time = datetime.now()

    async def connect_browser(
        self,
        navigate_to_atf: bool = True,
    ) -> tuple[Browser, BrowserContext, Page]:
        """Connect to browser (CDP or launch new).

        Args:
            navigate_to_atf: Whether to navigate to ATF page after connecting

        Returns:
            Tuple of (Browser, BrowserContext, Page)
        """
        playwright = await async_playwright().start()

        # Try CDP connection first
        cdp_config = self.config.get("cdp", {})
        if cdp_config.get("enabled", True):
            try:
                cdp_url = cdp_config.get("url", "http://localhost:9222")
                logger.info(f"Attempting CDP connection to {cdp_url}")
                browser = await playwright.chromium.connect_over_cdp(cdp_url)
                contexts = browser.contexts
                if contexts:
                    context = contexts[0]
                    pages = context.pages
                    page = pages[0] if pages else await context.new_page()
                    logger.info("Connected to existing browser via CDP")

                    # Navigate to ATF if requested and page is blank
                    if navigate_to_atf:
                        current_url = page.url
                        if current_url in ("about:blank", "", "chrome://newtab/"):
                            await self._navigate_to_atf(page)

                    return browser, context, page
            except Exception as e:
                logger.warning(
                    f"CDP connection failed: {e}, falling back to new browser",
                )

        # Launch new browser
        browser_config = self.config.get("browser", {})
        browser = await playwright.chromium.launch(
            headless=browser_config.get("headless", False),
            slow_mo=browser_config.get("slow_mo", 100),
        )
        context = await browser.new_context(
            viewport={
                "width": browser_config.get("viewport", {}).get("width", 1920),
                "height": browser_config.get("viewport", {}).get(
                    "height", 1080,
                ),
            },
        )
        page = await context.new_page()
        logger.info("Launched new browser instance")

        # Navigate to ATF page immediately after creating page
        if navigate_to_atf:
            await self._navigate_to_atf(page)

        return browser, context, page

    async def _navigate_to_atf(self, page: Page) -> None:
        """Navigate to ATF login page.

        Args:
            page: Playwright Page instance
        """
        logger.info("Navigating to ATF login page...")
        try:
            await page.goto(
                ATF_BASE_URL,
                wait_until="domcontentloaded",
                timeout=60000,  # 60 seconds timeout
            )
            logger.info(f"Successfully navigated to {ATF_BASE_URL}")
        except Exception as e:
            logger.exception(f"Failed to navigate to ATF: {e}", exc_info=True)
            raise

    async def process_single_nfa(
        self,
        page: Page,
        form_data: dict[str, Any],
        index: int,
        total: int,
        ctx: NFAContext | None = None,
    ) -> dict[str, Any]:
        """Process a single NFA with retry logic.

        Args:
            page: Playwright Page instance
            form_data: Form data dictionary
            index: Current index
            total: Total count
            ctx: Optional pre-resolved NFAContext (manual login re-use)

        Returns:
            Result dictionary
        """
        result: dict[str, Any] = {
            "index": index,
            "status": "pending",
            "nfa_number": None,
            "error": None,
            "timestamp": datetime.now().isoformat(),
            "retry_count": 0,
        }

        max_retries = self.config.get("retry", {}).get("max_attempts", 3)
        retry_delay = self.config.get("retry", {}).get("delay", 2000) / 1000

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    result["retry_count"] = attempt
                    logger.warning(
                        f"Retry {attempt}/{max_retries - 1} for NFA {index + 1}",
                    )
                    await asyncio.sleep(retry_delay * attempt)

                logger.info(
                    f"Processing NFA {index + 1}/{total} (attempt {attempt + 1})",
                )

                # Resolve DOM context if not provided
                active_ctx = ctx
                if active_ctx is None:
                    logger.info("Resolving NFA context for current page...")
                    active_ctx = await resolve_nfa_context(page)

                await wait_for_nfa_ready(
                    active_ctx,
                    timeout=self.config.get("timeouts", {}).get(
                        "form_ready",
                        45000,
                    ),
                )

                logger.info("NFA form detected — filling fields...")

                # Fill form
                success = await fill_nfa_form_complete(
                    active_ctx,
                    form_data,
                    None,
                    self.config,
                )

                if success:
                    result["status"] = "success"
                    self.success_count += 1
                    logger.info(
                        f"NFA {index + 1}/{total} completed successfully",
                    )
                    break
                msg = "Form filling failed"
                raise RuntimeError(msg)

            except Exception as e:
                result["error"] = str(e)
                logger.exception(f"Attempt {attempt + 1} failed: {e}")

                if attempt == max_retries - 1:
                    result["status"] = "error"
                    self.failure_count += 1
                    logger.exception(
                        f"Final failure for NFA {index + 1}/{total} after {max_retries} attempts",
                    )

        self.results.append(result)
        return result

    async def process_batch(
        self,
        form_data_list: list[dict[str, Any]],
        credentials: dict[str, str] | None = None,
        use_manual_login: bool = False,
    ) -> dict[str, Any]:
        """Process batch of NFAs.

        Args:
            form_data_list: List of form data dictionaries
            credentials: Optional login credentials {usuario, senha}
            use_manual_login: If True, wait for manual login instead of automated

        Returns:
            Batch processing results
        """
        logger.info(f"Starting batch processing: {len(form_data_list)} NFAs")

        # Check if manual login mode is enabled
        manual_login = use_manual_login or self.config.get("manual_login", False)

        # For manual login, we don't navigate on connect (we do it in atf_manual_login)
        # For automated login with credentials, perform_login will navigate
        # Otherwise, connect_browser should navigate
        navigate_on_connect = not manual_login and credentials is None

        browser, context, page = await self.connect_browser(
            navigate_to_atf=navigate_on_connect,
        )

        ctx: NFAContext | None = None
        nfa_page = page

        try:
            if manual_login:
                # Use manual login flow - returns NFAContext directly
                logger.info("Manual ATF login flow is active.")
                ctx = await atf_manual_login(context, page)
                nfa_page = get_page_from_context(ctx)
                logger.info("Manual login completed. NFA form ready.")

            elif credentials:
                # Perform automated login if credentials provided
                auth_config = self.config.get("authentication", {})
                if auth_config.get("enabled", True):
                    logger.info("Performing automated login...")
                    await perform_login(
                        page,
                        credentials.get("usuario"),
                        credentials.get("senha"),
                        timeout=self.config.get("timeouts", {}).get(
                            "navigation", 30000,
                        ),
                    )
                    await wait_for_post_login(
                        page,
                        timeout=self.config.get("timeouts", {}).get(
                            "navigation", 30000,
                        ),
                    )

                    if not self.config.get("mode", {}).get(
                        "manual_function_selection", False,
                    ):
                        await select_function_fis_1698(
                            page,
                            timeout=self.config.get("timeouts", {}).get(
                                "navigation", 30000,
                            ),
                        )
                        await asyncio.sleep(3)

            # Process each NFA
            for index, form_data in enumerate(form_data_list):
                await self.process_single_nfa(
                    nfa_page,
                    form_data,
                    index,
                    len(form_data_list),
                    ctx,
                )

                # Small delay between NFAs
                if index < len(form_data_list) - 1:
                    await asyncio.sleep(2)

        finally:
            await browser.close()

        end_time = datetime.now()
        duration = end_time - self.start_time

        return {
            "batch_summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration.total_seconds(),
                "total_processed": len(self.results),
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "success_rate": (
                    (self.success_count / len(self.results) * 100)
                    if self.results
                    else 0
                ),
            },
            "results": self.results,
        }
