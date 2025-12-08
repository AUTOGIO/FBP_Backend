"""Batch NFA Processor
Handles batch processing of multiple NFAs with error handling and retry logic.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import settings
from app.modules.nfa.atf_login import navigate_to_nfa_form, perform_login
from app.modules.nfa.form_filler import fill_nfa_form_complete
from app.modules.nfa.form_submitter import submeter_nfa
from app.modules.nfa.nfa_context import resolve_nfa_context
from app.modules.nfa.pdf_downloader import download_all_pdfs
from app.modules.nfa.screenshot_utils import save_screenshot

logger = logging.getLogger(__name__)


def setup_nfa_logging() -> None:
    """Setup verbose logging for NFA automation."""
    # Create logs directory
    logs_dir = settings.paths.project_root / "logs" / "nfa"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Create file handler for debug log
    debug_log_file = logs_dir / "nfa_debug.log"
    file_handler = logging.FileHandler(debug_log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # Add handler to NFA loggers
    nfa_logger = logging.getLogger("app.modules.nfa")
    nfa_logger.addHandler(file_handler)
    nfa_logger.setLevel(logging.DEBUG)

    logger.info(f"NFA debug logging enabled: {debug_log_file}")


async def handle_cookie_banners_and_loading(page: Page) -> None:
    """Handle cookie banners, loading screens, and anti-bot splash pages.

    Args:
        page: Playwright Page instance

    """
    try:
        # Wait for page to stabilize
        await page.wait_for_load_state("domcontentloaded", timeout=10000)
        await page.wait_for_timeout(2000)

        # Try to dismiss cookie banners
        cookie_selectors = [
            "button:has-text('Aceitar')",
            "button:has-text('Accept')",
            "button:has-text('Aceito')",
            "button:has-text('OK')",
            "#cookie-accept",
            ".cookie-accept",
            "[id*='cookie']",
            "[class*='cookie']",
        ]

        for selector in cookie_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=2000):
                    await element.click()
                    logger.info(f"Dismissed cookie banner with selector: {selector}")
                    await page.wait_for_timeout(1000)
                    break
            except Exception:
                continue

        # Wait for any loading screens to disappear
        loading_selectors = [
            ".loading",
            "[class*='loading']",
            "[id*='loading']",
            ".spinner",
            "[class*='spinner']",
        ]

        for selector in loading_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=2000):
                    logger.info(f"Waiting for loading screen to disappear: {selector}")
                    await element.wait_for(state="hidden", timeout=10000)
            except Exception:
                continue

        # Check for captcha (log only, don't try to solve)
        captcha_selectors = [
            "[class*='captcha']",
            "[id*='captcha']",
            "iframe[src*='recaptcha']",
            "iframe[src*='captcha']",
        ]

        for selector in captcha_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=2000):
                    logger.warning(f"CAPTCHA detected: {selector}")
                    await save_screenshot(
                        page,
                        None,
                        filename="captcha_detected.png",
                    )
            except Exception:
                continue

    except Exception as e:
        logger.warning(f"Error handling cookie banners/loading: {e}")


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

        # Setup verbose logging
        setup_nfa_logging()

        # Ensure screenshot directory exists
        screenshots_dir = self.config.get("paths", {}).get("screenshots_dir")
        if screenshots_dir:
            Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
        else:
            settings.paths.screenshots_dir.mkdir(parents=True, exist_ok=True)

    async def connect_browser(self) -> tuple[Browser, BrowserContext, Page]:
        """Connect to browser (CDP or launch new) with anti-bot evasion.

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
                    return browser, context, page
            except Exception as e:
                logger.warning(
                    f"CDP connection failed: {e}, falling back to new browser",
                )

        # Launch new browser with anti-bot evasion
        browser_config = self.config.get("browser", {})
        # Force non-headless for anti-bot evasion
        headless = browser_config.get("headless", False)

        browser = await playwright.chromium.launch(
            headless=headless,
            slow_mo=browser_config.get("slow_mo", 100),
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )

        # Create context with anti-bot evasion settings
        viewport_config = browser_config.get("viewport", {})
        context = await browser.new_context(
            viewport={
                "width": viewport_config.get("width", 1920),
                "height": viewport_config.get("height", 1080),
            },
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            extra_http_headers={
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            },
        )

        # Add stealth script to remove webdriver property
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        )

        page = await context.new_page()
        logger.info("Launched new browser instance with anti-bot evasion")
        return browser, context, page

    async def process_single_nfa(
        self,
        page: Page,
        form_data: dict[str, Any],
        index: int,
        total: int,
    ) -> dict[str, Any]:
        """Process a single NFA with retry logic, PDF download, and per-CPF logging.

        Args:
            page: Playwright Page instance
            form_data: Form data dictionary
            index: Current index
            total: Total count

        Returns:
            Result dictionary with PDF paths and logs

        """
        # Extract CPF for directory structure
        destinatario_data = form_data.get("destinatario", {})
        cpf_raw = (
            destinatario_data.get("cpf", "")
            or destinatario_data.get("CPF", "")
            or destinatario_data.get("documento", "")
            or form_data.get("destinatario_doc", "")
        )
        cpf_clean = "".join(
            filter(
                str.isdigit, cpf_raw.replace("/", "").replace("-", "").replace(".", "")
            )
        )

        # Create per-CPF directories
        project_root = settings.paths.project_root
        cpf_output_dir = project_root / "output" / "nfa" / "pdf" / cpf_clean
        cpf_screenshots_dir = (
            project_root / "output" / "nfa" / "screenshots" / cpf_clean
        )
        cpf_results_dir = project_root / "output" / "nfa" / "results"
        cpf_results_dir.mkdir(parents=True, exist_ok=True)
        cpf_screenshots_dir.mkdir(parents=True, exist_ok=True)

        result: dict[str, Any] = {
            "index": index,
            "cpf": cpf_clean,
            "status": "pending",
            "nfa_number": None,
            "dar_pdf": None,
            "nota_pdf": None,
            "error": None,
            "timestamp": datetime.now().isoformat(),
            "retry_count": 0,
            "screenshots": [],
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

                # Use per-CPF screenshots directory
                steps_dir = cpf_screenshots_dir

                # Step 1: Wait for form to be ready
                logger.info(f"Step 1: Waiting for NFA form to be ready...")
                # Ensure page is still alive
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception:
                    logger.warning("Page load state check failed, continuing...")

                from app.modules.nfa.nfa_context import (
                    resolve_nfa_context,
                    wait_for_nfa_ready,
                )

                try:
                    ctx = await resolve_nfa_context(page)
                    await wait_for_nfa_ready(
                        ctx,
                        timeout=self.config.get("timeouts", {}).get(
                            "element_wait",
                            10000,
                        )
                        * 3,
                    )
                    form_ready = True
                except Exception as ready_error:
                    logger.warning(
                        f"Form ready check failed: {ready_error}, continuing anyway..."
                    )
                    form_ready = False

                if not form_ready:
                    logger.warning(
                        "Form ready check returned False, continuing anyway..."
                    )

                try:
                    screenshot_path = await save_screenshot(
                        page,
                        steps_dir,
                        filename=f"step1_form_ready_{cpf_clean}_attempt_{attempt + 1}.png",
                    )
                    if screenshot_path:
                        result["screenshots"].append(str(screenshot_path))
                except Exception as screenshot_error:
                    logger.warning(
                        f"Failed to save step 1 screenshot: {screenshot_error}"
                    )

                # Step 2: Wait for NFA form to be ready (form is on main page)
                logger.info(f"Step 2: Waiting for NFA form to be ready on main page...")
                from app.modules.nfa.nfa_context import (
                    resolve_nfa_context,
                    wait_for_nfa_ready,
                )

                # Ensure page is still alive before trying to resolve context
                try:
                    # Check if page is still valid
                    _ = page.url
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    await page.wait_for_timeout(3000)  # Extra wait for form to render
                except Exception as page_check_error:
                    logger.error(f"Page is no longer valid: {page_check_error}")
                    msg = "Browser page was closed or invalid"
                    raise RuntimeError(msg) from page_check_error

                try:
                    logger.info("Resolving NFA context (main page - no frames)...")
                    ctx = await resolve_nfa_context(page)
                    await wait_for_nfa_ready(ctx, timeout=60000)  # Longer timeout
                    logger.info("Successfully resolved NFA context on main page")
                except Exception as ctx_error:
                    logger.error(f"Context resolution failed: {ctx_error}")
                    # Try alternative detection - check if form fields exist
                    try:
                        await page.wait_for_selector("select[name='cmbNaturezaOperacao']", timeout=10000)
                        logger.info("Form found via alternative selector")
                    except Exception:
                        msg = "NFA form not found on main page"
                        raise RuntimeError(msg) from ctx_error

                try:
                    screenshot_path = await save_screenshot(
                        page,
                        steps_dir,
                        filename=f"step2_form_ready_{cpf_clean}_attempt_{attempt + 1}.png",
                    )
                    if screenshot_path:
                        result["screenshots"].append(str(screenshot_path))
                except Exception as screenshot_error:
                    logger.warning(
                        f"Failed to save step 2 screenshot: {screenshot_error}"
                    )

                # Step 3: Fill form
                logger.info(f"Step 3: Filling NFA form for CPF {cpf_clean}...")
                success = await fill_nfa_form_complete(
                    page,
                    form_data,
                    None,
                    self.config,
                )

                try:
                    screenshot_path = await save_screenshot(
                        page,
                        steps_dir,
                        filename=f"step3_form_filled_{cpf_clean}_attempt_{attempt + 1}.png",
                    )
                    if screenshot_path:
                        result["screenshots"].append(str(screenshot_path))
                except Exception as screenshot_error:
                    logger.warning(
                        f"Failed to save step 3 screenshot: {screenshot_error}"
                    )

                if not success:
                    msg = "Form filling failed"
                    raise RuntimeError(msg)

                # Step 4: Submit form
                logger.info(f"Step 4: Submitting NFA form for CPF {cpf_clean}...")
                ctx = await resolve_nfa_context(page)
                submit_success, nfa_number = await submeter_nfa(ctx)

                if not submit_success:
                    msg = "Form submission failed"
                    raise RuntimeError(msg)

                result["nfa_number"] = nfa_number

                try:
                    screenshot_path = await save_screenshot(
                        page,
                        steps_dir,
                        filename=f"step4_submitted_{cpf_clean}_attempt_{attempt + 1}.png",
                    )
                    if screenshot_path:
                        result["screenshots"].append(str(screenshot_path))
                except Exception as screenshot_error:
                    logger.warning(
                        f"Failed to save step 4 screenshot: {screenshot_error}"
                    )

                # Step 5: Download PDFs
                logger.info(f"Step 5: Downloading PDFs for CPF {cpf_clean}...")
                try:
                    pdf_results = await download_all_pdfs(ctx, cpf_output_dir, cpf_raw)
                    result["dar_pdf"] = (
                        str(pdf_results["dar_pdf"]) if pdf_results["dar_pdf"] else None
                    )
                    result["nota_pdf"] = (
                        str(pdf_results["nota_pdf"])
                        if pdf_results["nota_pdf"]
                        else None
                    )

                    if pdf_results["dar_pdf"]:
                        logger.info(f"✓ DAR PDF saved: {pdf_results['dar_pdf']}")
                    if pdf_results["nota_pdf"]:
                        logger.info(
                            f"✓ Nota Fiscal PDF saved: {pdf_results['nota_pdf']}"
                        )
                except Exception as pdf_error:
                    logger.warning(f"PDF download failed: {pdf_error}")
                    result["error"] = f"PDF download failed: {pdf_error}"

                # Step 6: Save JSON log per CPF
                log_file = cpf_results_dir / f"{cpf_clean}.json"
                try:
                    with open(log_file, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    logger.info(f"✓ JSON log saved: {log_file}")
                except Exception as log_error:
                    logger.warning(f"Failed to save JSON log: {log_error}")

                result["status"] = "completed"
                self.success_count += 1
                logger.info(
                    f"NFA {index + 1}/{total} (CPF: {cpf_clean}) completed successfully",
                )
                break

            except Exception as e:
                result["error"] = str(e)
                logger.exception(f"Attempt {attempt + 1} failed: {e}")

                # Save screenshot on error
                try:
                    screenshot_path = await save_screenshot(
                        page,
                        cpf_screenshots_dir,
                        filename=f"error_{cpf_clean}_attempt_{attempt + 1}.png",
                    )
                    if screenshot_path:
                        result["screenshots"].append(str(screenshot_path))
                        logger.info(f"Error screenshot saved: {screenshot_path}")
                except Exception as screenshot_error:
                    logger.warning(
                        f"Failed to save error screenshot: {screenshot_error}",
                    )

                # Save error log per CPF
                if attempt == max_retries - 1:
                    log_file = cpf_results_dir / f"{cpf_clean}.json"
                    try:
                        with open(log_file, "w", encoding="utf-8") as f:
                            json.dump(result, f, indent=2, ensure_ascii=False)
                        logger.info(f"✓ Error log saved: {log_file}")
                    except Exception as log_error:
                        logger.warning(f"Failed to save error log: {log_error}")

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
    ) -> dict[str, Any]:
        """Process batch of NFAs.

        Args:
            form_data_list: List of form data dictionaries
            credentials: Optional login credentials {usuario, senha}

        Returns:
            Batch processing results

        """
        logger.info(f"Starting batch processing: {len(form_data_list)} NFAs")

        browser, _context, page = await self.connect_browser()

        try:
            # Setup console message logging
            console_messages = []

            def handle_console(msg):
                console_messages.append(
                    {
                        "type": msg.type,
                        "text": msg.text,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                logger.debug(f"Console {msg.type}: {msg.text}")

            page.on("console", handle_console)

            # Perform login if credentials provided
            if credentials:
                auth_config = self.config.get("authentication", {})
                if auth_config.get("enabled", True):
                    logger.info("Performing login...")

                    # Handle cookie banners and loading screens before login
                    await handle_cookie_banners_and_loading(page)

                    await perform_login(
                        page,
                        credentials.get("usuario"),
                        credentials.get("senha"),
                        timeout=self.config.get("timeouts", {}).get(
                            "navigation",
                            30000,
                        ),
                    )

                    # Wait for post-login page to stabilize
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    await page.wait_for_timeout(3000)

                    await navigate_to_nfa_form(
                        page,
                        timeout=self.config.get("timeouts", {}).get(
                            "navigation",
                            60000,  # Longer timeout for form navigation
                        ),
                    )

                    # Wait for form to be fully loaded
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    await page.wait_for_timeout(
                        5000
                    )  # Extra wait for page to stabilize

                    await handle_cookie_banners_and_loading(page)

            # Save console messages to file
            try:
                logs_dir = settings.paths.project_root / "logs" / "nfa"
                logs_dir.mkdir(parents=True, exist_ok=True)
                console_log_file = logs_dir / "browser_console.log"
                import json

                with open(console_log_file, "w", encoding="utf-8") as f:
                    json.dump(console_messages, f, indent=2, ensure_ascii=False)
                logger.info(f"Browser console messages saved: {console_log_file}")
            except Exception as e:
                logger.warning(f"Failed to save console messages: {e}")

            # Process each NFA
            for index, form_data in enumerate(form_data_list):
                await self.process_single_nfa(
                    page,
                    form_data,
                    index,
                    len(form_data_list),
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
