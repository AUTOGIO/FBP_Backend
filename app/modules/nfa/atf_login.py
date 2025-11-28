"""ATF Login Automation
Handles authentication with ATF system (manual and automated modes) while
supporting both root DOM and iframe-based layouts.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.logging_config import setup_logger
from app.modules.nfa.nfa_context import (
    NFAContext,
    resolve_nfa_context,
    wait_for_nfa_ready,
)

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page

logger = setup_logger(__name__)

# ATF Base URL - canonical URL for NFA automation
ATF_BASE_URL = "https://www4.sefaz.pb.gov.br/atf/"

# NFA Form URL - direct link to NFA emission form (post-login)
NFA_FORM_URL = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true"

LOGIN_PAGE_SRC = "SEGf_Login.jsp"
LOGIN_POLL_INTERVAL_MS = 4000
LOGIN_POLL_ATTEMPTS = 30

_LOGIN_READY_SCRIPT = """
() => {
    const marker = 'SEGf_Login.jsp';
    const html = document.documentElement ? document.documentElement.innerHTML : '';
    const stillOnLogin = html.includes(marker);
    if (stillOnLogin) {
        return false;
    }
    const body = document.body ? document.body.innerText.toLowerCase() : '';
    return body.includes('nota fiscal') || body.includes('repartição fiscal') || body.includes('menu principal');
}
"""


async def atf_manual_login(
    context: BrowserContext,
    page: Page,
) -> NFAContext:
    """Wait for user to manually login to ATF system.

    This function:
    1. Navigates to ATF login page
    2. Waits for manual credentials entry (no frame sniffing)
    3. Opens a dedicated tab with the NFA form
    4. Resolves the correct DOM context (root or iframe)
    5. Waits for NFA readiness and returns the NFAContext

    Args:
        context: Browser context hosting the login page
        page: Playwright Page instance

    Returns:
        NFAContext ready for form filling
    """
    logger.info("Manual ATF login flow is active.")
    logger.info("Navigating to ATF login page...")

    try:
        # Navigate to ATF login page
        await page.goto(
            ATF_BASE_URL,
            wait_until="domcontentloaded",
            timeout=60000,
        )
        logger.info(f"ATF login page loaded: {ATF_BASE_URL}")

        # Step 2: Wait for user to manually login
        logger.info("=" * 60)
        logger.info("🔐 WAITING FOR MANUAL LOGIN...")
        logger.info("➡️  Please log in manually using the opened browser window.")
        logger.info("➡️  Click 'Avançar' after entering your credentials.")
        logger.info("➡️  The bot will automatically continue after login.")
        logger.info("=" * 60)

        work_page = await context.new_page()

        for attempt in range(1, LOGIN_POLL_ATTEMPTS + 1):
            logger.info(
                "Checking manual login status (attempt %s/%s)...",
                attempt,
                LOGIN_POLL_ATTEMPTS,
            )
            await work_page.goto(
                NFA_FORM_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            if LOGIN_PAGE_SRC.lower() in work_page.url.lower():
                logger.info("Login not detected yet — waiting before retrying.")
                await page.wait_for_timeout(LOGIN_POLL_INTERVAL_MS)
                continue

            try:
                ctx = await resolve_nfa_context(work_page)
                await wait_for_nfa_ready(ctx)
                logger.info("✅ Manual login confirmed. NFA context ready.")
                return ctx
            except Exception as ctx_error:
                logger.debug("NFA context not ready yet: %s", ctx_error)
                await page.wait_for_timeout(LOGIN_POLL_INTERVAL_MS)

        msg = "Manual login not detected after waiting for NFA form."
        logger.error(msg)
        raise RuntimeError(msg)

    except Exception as e:
        logger.exception(f"Error in manual login flow: {e}", exc_info=True)
        raise


async def perform_login(
    page: Page,
    usuario: str | None = None,
    senha: str | None = None,
    timeout: int = 30000,
) -> bool:
    """Navigate to login page and perform automated authentication.

    Args:
        page: Playwright Page instance
        usuario: Username (if None, uses config)
        senha: Password (if None, uses config)
        timeout: Timeout in milliseconds

    Returns:
        True if login successful, False otherwise
    """
    try:
        # Get credentials from config or parameters
        if usuario is None:
            usuario = getattr(settings, "ATF_USERNAME", None)
        if senha is None:
            senha = getattr(settings, "ATF_PASSWORD", None)

        if not usuario or not senha:
            msg = "ATF credentials not configured"
            raise ValueError(msg)

        logger.info("Navigating to ATF login page...")
        await page.goto(
            ATF_BASE_URL,
            wait_until="domcontentloaded",
            timeout=timeout,
        )
        logger.info(f"Successfully navigated to {ATF_BASE_URL}")

        # Wait for login form
        await page.wait_for_selector("input[name='edtLogin']", timeout=timeout)

        # Fill credentials
        logger.debug("Filling login credentials")
        await page.locator("input[name='edtLogin']").fill(usuario)
        await page.locator("input[name='edtDsSenha']").fill(senha)

        # Click login button
        await page.locator("button[name='btnAvancar']").click()

        # Wait for login success without inspecting frames explicitly
        await page.wait_for_function(_LOGIN_READY_SCRIPT, timeout=timeout)

        logger.info("Login successful (login markers cleared)")
        return True

    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        return False


async def wait_for_post_login(page: Page, timeout: int = 30000) -> bool:
    """Wait for post-login page to load.

    Args:
        page: Playwright Page instance
        timeout: Timeout in milliseconds

    Returns:
        True if post-login page loaded, False otherwise
    """
    try:
        await page.wait_for_function(_LOGIN_READY_SCRIPT, timeout=timeout)
        logger.debug("Post-login page loaded (login markers gone)")
        return True
    except Exception as e:
        logger.exception(f"Error waiting for post-login: {e}")
        return False


async def select_function_fis_1698(page: Page, timeout: int = 30000) -> bool:
    """Select FIS_1698 function after login.

    Args:
        page: Playwright Page instance
        timeout: Timeout in milliseconds

    Returns:
        True if function selected successfully, False otherwise
    """
    try:
        # Look for FIS_1698 link or button
        fis_1698_selectors = [
            "a:has-text('FIS_1698')",
            "a:has-text('Nota Fiscal Avulsa')",
            "a[href*='fis_1698']",
            "a[href*='FIS_1698']",
        ]

        ctx = await resolve_nfa_context(page)
        for selector in fis_1698_selectors:
            try:
                locator = ctx.locator(selector)
                await locator.wait_for(timeout=timeout // len(fis_1698_selectors))
                await locator.click()
                logger.info(f"FIS_1698 function selected (selector: {selector})")
                return True
            except Exception:
                continue

        logger.warning("Could not find FIS_1698 selector")
        return False

    except Exception as e:
        logger.exception(f"Error selecting FIS_1698 function: {e}")
        return False
