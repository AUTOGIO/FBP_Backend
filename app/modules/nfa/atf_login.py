"""ATF Login Automation
Handles authentication with ATF system.
"""

from __future__ import annotations

import logging
import time

try:
    from playwright.async_api import Page
except ImportError:
    Page = None  # type: ignore

from app.core.config import settings
from app.modules.nfa.screenshot_utils import save_screenshot

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp"
NFA_FORM_URL = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true"


async def perform_login(
    page: Page,
    username: str | None = None,
    password: str | None = None,
    timeout: int = 60000,
) -> bool:
    """Execute the minimal working login flow without legacy redirects."""
    screenshots_dir = settings.paths.project_root / "output" / "nfa" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    try:
        user = username or settings.NFA_USERNAME
        pwd = password or settings.NFA_PASSWORD
        if not user or not pwd:
            msg = "NFA credentials not configured in .env (NFA_USERNAME, NFA_PASSWORD)"
            raise ValueError(msg)

        logger.info("login_start: navigating to ATF login page")
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=timeout)
        await save_screenshot(page, screenshots_dir, filename="login_start.png")

        await page.fill("input[name='edtNoLogin']", user)
        await page.fill("input[name='edtDsSenha']", pwd)
        logger.info("login_filled: credentials populated with validated selectors")
        await save_screenshot(page, screenshots_dir, filename="login_filled.png")

        logger.info("login_trigger: executing logarSistema() with click fallback")
        try:
            await page.evaluate("logarSistema()")
        except Exception as eval_error:
            logger.warning(f"logarSistema() evaluation failed: {eval_error}")
            await page.click("button[name='btnAvancar'], input[name='btnAvancar']")

        logger.info("login_success: login JS triggered, waiting 4s for session")
        await save_screenshot(page, screenshots_dir, filename="login_success.png")
        await page.wait_for_timeout(4000)

        return True

    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        await save_screenshot(page, screenshots_dir, filename="login_error.png")
        return False


async def wait_for_post_login(page: Page, timeout: int = 30000) -> bool:
    """Wait for post-login page to load.

    Args:
        page: Playwright Page instance
        timeout: Timeout in milliseconds

    Returns:
        True if post-login page loaded, False otherwise

    """
    screenshots_dir = settings.paths.project_root / "output" / "nfa" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    def _looks_logged_in(url: str) -> bool:
        # Login page is /atf/seg/SEGf_Login.jsp.
        # ATF may keep /atf/ but should not keep this path.
        return "SEGf_Login.jsp" not in (url or "")

    # Best-effort authenticated endpoint probe (shares cookies with page/context)
    menu_url = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_MontarMenu.jsp"

    deadline = time.monotonic() + (timeout / 1000.0)
    last_error: str | None = None

    while time.monotonic() < deadline:
        remaining_ms = max(250, int((deadline - time.monotonic()) * 1000))
        try:
            # 1) Let network settle (SEFAZ does async redirects / session setup)
            try:
                await page.wait_for_load_state(
                    "networkidle",
                    timeout=min(remaining_ms, 5000),
                )
            except Exception:
                # networkidle isn't guaranteed; keep going with other signals
                pass

            current_url = page.url

            # 2) Session-based URL validation: not stuck on the login JSP anymore
            if _looks_logged_in(current_url):
                logger.info("Login validated (session-based): URL left login page")
                return True

            # 3) Probe a known authenticated endpoint.
            # If we bounce back to login, keep waiting.
            try:
                resp = await page.request.get(
                    menu_url,
                    timeout=min(remaining_ms, 8000),
                )
                final_url = getattr(resp, "url", "") or ""
                if resp.ok and _looks_logged_in(final_url):
                    logger.info(
                        "Login validated (session-based): authenticated endpoint reachable"
                    )
                    return True
            except Exception as probe_error:
                last_error = f"probe_error: {probe_error}"

            await page.wait_for_timeout(300)

        except Exception as e:
            last_error = str(e)
            await page.wait_for_timeout(300)

    # Failure: capture diagnostics without requiring any specific iframe name
    try:
        current_url = page.url
        title = await page.title()
    except Exception:
        current_url = "<unavailable>"
        title = "<unavailable>"

    logger.error(
        "Login validation failed (session-based). url=%s title=%s last_error=%s",
        current_url,
        title,
        last_error,
    )
    await save_screenshot(
        page,
        screenshots_dir,
        filename="login_validation_failed.png",
    )
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
        await page.wait_for_selector(
            "frame[name='mainFrame']",
            timeout=timeout,
        )

        frame = page.frame_locator("frame").first

        fis_1698_selector = "a:has-text('FIS_1698')"

        try:
            await frame.locator(fis_1698_selector).wait_for(timeout=timeout)
            await frame.locator(fis_1698_selector).click()
            logger.info("FIS_1698 function selected")
            return True
        except Exception:
            alt_selector = "a[href*='fis_1698']"
            try:
                await frame.locator(alt_selector).wait_for(timeout=timeout)
                await frame.locator(alt_selector).click()
                logger.info(
                    "FIS_1698 function selected (alternative selector)",
                )
                return True
            except Exception as e:
                logger.warning(f"Could not find FIS_1698 selector: {e}")
                return False

    except Exception as e:
        logger.exception(f"Error selecting FIS_1698 function: {e}")
        return False


async def navigate_to_nfa_form(
    page: Page,
    timeout: int = 60000,
) -> bool:
    """Navigate directly to the NFA form immediately after login."""
    screenshots_dir = settings.paths.project_root / "output" / "nfa" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info("nfa_navigation_start: forcing navigation to NFA form")
        await save_screenshot(
            page, screenshots_dir, filename="nfa_navigation_start.png"
        )

        await page.goto(NFA_FORM_URL, wait_until="domcontentloaded", timeout=timeout)
        await page.wait_for_timeout(3000)  # Wait longer for page to load

        # Try multiple strategies to detect form
        form_detected = False

        # Strategy 1: Try text selector
        try:
            await page.wait_for_selector("text=Emitir NFA-e Repartição", timeout=10000)
            form_detected = True
            logger.info("nfa_navigation_success: Form detected via text selector")
        except Exception:
            logger.debug(
                "Text selector 'Emitir NFA-e Repartição' not found, trying alternatives..."
            )

        # Strategy 2: Try context resolution (form is on main page)
        if not form_detected:
            try:
                from app.modules.nfa.nfa_context import (
                    resolve_nfa_context,
                    wait_for_nfa_ready,
                )

                ctx = await resolve_nfa_context(page)
                await wait_for_nfa_ready(ctx, timeout=30000)
                form_detected = True
                logger.info(
                    "nfa_navigation_success: Form detected via context resolution"
                )
            except Exception as ctx_error:
                logger.debug(f"Context resolution failed: {ctx_error}")

        # Strategy 3: Try alternative text selectors
        if not form_detected:
            alternative_selectors = [
                "text=Nota Fiscal",
                "text=Repartição Fiscal",
                "input[name*='CodigoNCM' i]",
                "table:has-text('Emitente')",
                "table:has-text('Destinatário')",
            ]
            for selector in alternative_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    form_detected = True
                    logger.info(
                        f"nfa_navigation_success: Form detected via selector: {selector}"
                    )
                    break
                except Exception:
                    continue

        if not form_detected:
            await save_screenshot(page, screenshots_dir, filename="nfa_form_fail.png")
            # Log current URL and page content for debugging
            current_url = page.url
            logger.error(f"NFA form not detected. Current URL: {current_url}")
            raise Exception(f"NFA form DID NOT LOAD. URL: {current_url}")

        await save_screenshot(
            page, screenshots_dir, filename="nfa_navigation_success.png"
        )

        return True

    except Exception as e:
        logger.error(f"Error navigating to NFA form: {e}", exc_info=True)
        await save_screenshot(page, screenshots_dir, filename="nfa_form_error.png")
        return False
