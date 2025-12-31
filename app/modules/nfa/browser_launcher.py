"""Browser Launcher with Persistent Context and Anti-Bot Bypass

Hardened browser launch for SEFAZ PB ATF automation.
Optimized for: iMac M3 (Mac15,5) | 8 cores | 16GB | macOS 26.0 Tahoe
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import settings

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


async def launch_persistent_browser(
    headless: bool = False,
    slow_mo: int = 100,
    user_data_dir: str | None = None,
) -> tuple[Browser, BrowserContext, Page]:
    """Launch Chromium with persistent context and anti-bot bypass.

    Uses launch_persistent_context for better SEFAZ PB compatibility.

    Args:
        headless: Whether to run in headless mode
        slow_mo: Slow motion delay in milliseconds
        user_data_dir: Custom user data directory (creates temp if None)

    Returns:
        Tuple of (Browser, BrowserContext, Page)

    """
    playwright = await async_playwright().start()

    # Create user data directory if not provided
    if user_data_dir is None:
        # Use unique directory per execution to avoid conflicts
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        user_data_dir = str(Path(tempfile.gettempdir()) / f"fbp_playwright_user_data_{unique_id}")
        os.makedirs(user_data_dir, exist_ok=True)
        logger.info(f"Using temporary user data dir: {user_data_dir}")

    # Clean up SingletonLock if it exists (prevents "profile already in use" error)
    singleton_lock = Path(user_data_dir) / "SingletonLock"
    if singleton_lock.exists():
        try:
            singleton_lock.unlink()
            logger.info("Removed existing SingletonLock file")
        except Exception as e:
            logger.warning(f"Could not remove SingletonLock: {e}")

    # Browser launch args for anti-bot evasion
    # Add crash prevention flags
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-crash-reporter",
        "--disable-background-networking",
        "--disable-breakpad",
        "--disable-background-networking",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-breakpad",
        "--disable-client-side-phishing-detection",
        "--disable-component-extensions-with-background-pages",
        "--disable-default-apps",
        "--disable-domain-reliability",
        "--disable-extensions",
        "--disable-features=TranslateUI",
        "--disable-hang-monitor",
        "--disable-ipc-flooding-protection",
        "--disable-notifications",
        "--disable-offer-store-unmasked-wallet-cards",
        "--disable-popup-blocking",
        "--disable-print-preview",
        "--disable-prompt-on-repost",
        "--disable-renderer-backgrounding",
        "--disable-speech-api",
        "--disable-sync",
        "--disable-translate",
        "--hide-scrollbars",
        "--ignore-gpu-blacklist",
        "--metrics-recording-only",
        "--mute-audio",
        "--no-first-run",
        "--no-pings",
        "--password-store=basic",
        "--use-mock-keychain",
    ]

    # Launch persistent context (better for SEFAZ PB)
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=headless,
        slow_mo=slow_mo,
        args=launch_args,
        viewport={
            "width": 1920,
            "height": 1080,
        },
        user_agent=(
            "Mozilla/5.0 (Macintosh; Apple M3 Mac OS X 26_0) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/18.0 Safari/605.1.15"
        ),
        locale="pt-BR",
        timezone_id="America/Recife",
        geolocation={"latitude": -8.0476, "longitude": -34.8770},  # Recife, Brazil
        permissions=["geolocation"],
        extra_http_headers={
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
        ignore_https_errors=True,
    )

    # Add anti-bot init script
    await context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Override plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Override languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['pt-BR', 'pt', 'en-US', 'en']
        });
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Chrome runtime
        window.chrome = {
            runtime: {}
        };
        
        // Override webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
        """
    )

    # Get or create page
    pages = context.pages
    if pages:
        page = pages[0]
        logger.info("Using existing page from persistent context")
    else:
        page = await context.new_page()
        logger.info("Created new page in persistent context")

    # Add route handler to continue all requests
    async def route_handler(route):
        await route.continue_()

    await context.route("**/*", route_handler)

    logger.info(
        f"Launched persistent browser context (headless={headless}, "
        f"user_data_dir={user_data_dir})"
    )

    # Return browser-like object (persistent context acts as browser)
    browser = context.browser if hasattr(context, "browser") else None

    return browser, context, page


async def navigate_to_sefaz_with_fallback(
    page: Page,
    url: str = "https://www4.sefaz.pb.gov.br/atf/",
    timeout: int = 120000,
) -> bool:
    """Navigate to SEFAZ PB ATF with fallback strategies.

    Args:
        page: Playwright Page instance
        url: URL to navigate to
        timeout: Timeout in milliseconds

    Returns:
        True if navigation successful, False otherwise

    """
    logger.info(f"Navigating to SEFAZ PB ATF: {url}")

    # Strategy 1: Try HTTPS with domcontentloaded
    try:
        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=timeout,
        )
        current_url = page.url
        logger.info(f"Navigation successful (Strategy 1): {current_url}")

        # Check if we got blank page
        if current_url == "about:blank":
            logger.warning("Got about:blank, trying reload...")
            await page.reload(wait_until="domcontentloaded", timeout=timeout)
            current_url = page.url
            logger.info(f"After reload: {current_url}")

        # If still blank, try Strategy 2
        if current_url == "about:blank":
            logger.warning("Still blank after reload, trying HTTP fallback...")
            http_url = url.replace("https://", "http://")
            await page.goto(
                http_url,
                wait_until="domcontentloaded",
                timeout=timeout,
            )
            current_url = page.url
            logger.info(f"HTTP fallback result: {current_url}")

        # Final check
        if current_url == "about:blank":
            logger.error("All navigation strategies failed - still on about:blank")
            # Save screenshot for debugging
            screenshot_path = (
                settings.paths.project_root / "logs" / "nfa" / "blank_page_debug.png"
            )
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Saved blank page screenshot: {screenshot_path}")
            return False

        # Wait for network idle
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception as e:
            logger.warning(f"Network idle wait failed: {e}")

        logger.info(f"Final URL: {page.url}")
        return True

    except Exception as e:
        logger.error(f"Navigation failed: {e}", exc_info=True)
        # Save screenshot
        screenshot_path = (
            settings.paths.project_root / "logs" / "nfa" / "navigation_error.png"
        )
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"Saved error screenshot: {screenshot_path}")
        return False
