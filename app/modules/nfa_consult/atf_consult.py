"""ATF Consult Automation - Playwright helper functions.

This module provides helper functions for automating NFA consultation
(FIS_308) on the ATF/SEFAZ-PB portal.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from app.core.config import settings
from app.modules.nfa.screenshot_utils import save_screenshot

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Frame, Page

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp"
OUTPUT_DIR = Path("/Users/dnigga/Downloads/NFA_Outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def _login_atf(
    page: Page,
    username: str,
    password: str,
    timeout: int = 60000,
) -> bool:
    """Login to ATF portal.

    Args:
        page: Playwright Page instance
        username: ATF username
        password: ATF password
        timeout: Timeout in milliseconds

    Returns:
        True if login successful, False otherwise

    """
    screenshots_dir = settings.paths.project_root / "output" / "nfa" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info("Navigating to ATF login page")
        await page.goto(LOGIN_URL, wait_until="load", timeout=timeout)
        await save_screenshot(page, screenshots_dir, filename="consult_login_start.png")

        # Wait for login form
        await page.wait_for_selector('input[name="edtNoLogin"]', timeout=10000)
        await page.fill('input[name="edtNoLogin"]', username)
        await page.fill('input[name="edtDsSenha"]', password)
        logger.info("Credentials filled")

        await save_screenshot(
            page, screenshots_dir, filename="consult_login_filled.png"
        )

        # Submit login
        try:
            await page.evaluate("logarSistema()")
        except Exception as eval_error:
            logger.warning(f"logarSistema() evaluation failed: {eval_error}")
            await page.click('button[name="btnAvancar"], input[name="btnAvancar"]')

        logger.info("Login submitted, waiting for session")
        await page.wait_for_timeout(4000)
        await save_screenshot(
            page, screenshots_dir, filename="consult_login_success.png"
        )

        # Debug: log current URL and available frames
        logger.info(f"Current URL after login: {page.url}")
        logger.info(f"Available frames: {len(page.frames)}")
        for i, frame in enumerate(page.frames):
            logger.info(
                f"Frame {i}: {frame.name or 'unnamed'} - {frame.url[:100] if frame.url else 'no URL'}"
            )

        return True

    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        await save_screenshot(page, screenshots_dir, filename="consult_login_error.png")
        return False


async def _navigate_to_fis308(page: Page, timeout: int = 30000) -> bool:
    """Navigate to FIS_308 function using the function search field.

    Args:
        page: Playwright Page instance
        timeout: Timeout in milliseconds

    Returns:
        True if navigation successful, False otherwise

    """
    try:
        logger.info("Navigating to FIS_308 function")

        # Wait a bit for page to stabilize after login
        await page.wait_for_timeout(3000)

        # Save screenshot for debugging
        screenshots_dir = settings.paths.project_root / "output" / "nfa" / "screenshots"
        await save_screenshot(
            page, screenshots_dir, filename="consult_before_fis308.png"
        )

        # Try multiple strategies to find the function search field
        target_frame = None
        field_found = False

        # Strategy 1: Try direct URL navigation (if available)
        try:
            fis308_url = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_ConsultarNotasFiscaisAvulsas.do"
            logger.info(f"Trying direct navigation to: {fis308_url}")
            await page.goto(fis308_url, wait_until="domcontentloaded", timeout=timeout)
            await page.wait_for_timeout(2000)
            # Check if we're on the right page
            try:
                await page.wait_for_selector(
                    'input[name="edtDtEmissaoNfaeInicial"]', timeout=5000
                )
                logger.info("Successfully navigated directly to FIS_308 form")
                return True
            except Exception:
                logger.info(
                    "Direct navigation didn't work, trying function search field"
                )
        except Exception as e:
            logger.warning(f"Direct navigation failed: {e}")

        # Strategy 2: Try main frame by name
        try:
            main_frame = page.frame(name="mainFrame")
            if main_frame:
                await main_frame.wait_for_selector(
                    'input[name="edtFuncao"]', timeout=5000
                )
                target_frame = main_frame
                field_found = True
                logger.info("Found function field in mainFrame")
        except Exception:
            pass

        # Strategy 3: Try all frames
        if not field_found:
            logger.info("Trying all available frames")
            for frame in page.frames:
                try:
                    await frame.wait_for_selector(
                        'input[name="edtFuncao"]', timeout=3000
                    )
                    target_frame = frame
                    field_found = True
                    logger.info(
                        f"Found function field in frame: {frame.url[:100] if frame.url else 'no URL'}"
                    )
                    break
                except Exception:
                    continue

        # Strategy 4: Try main page
        if not field_found:
            try:
                await page.wait_for_selector('input[name="edtFuncao"]', timeout=5000)
                target_frame = page
                field_found = True
                logger.info("Found function field in main page")
            except Exception:
                pass

        if not field_found:
            # Save debug screenshot
            await save_screenshot(
                page, screenshots_dir, filename="consult_fis308_field_not_found.png"
            )
            raise RuntimeError("Could not find function search field (edtFuncao)")

        # Fill and submit
        await target_frame.fill('input[name="edtFuncao"]', "fis_308")
        await target_frame.keyboard.press("Enter")
        await page.wait_for_timeout(3000)  # Wait for navigation

        logger.info("FIS_308 navigation completed")
        return True

    except Exception as e:
        logger.error(f"Failed to navigate to FIS_308: {e}", exc_info=True)
        return False


async def _get_main_frame(page: Page) -> Frame | Page:
    """Get the main content frame (handles iframe resolution).

    Args:
        page: Playwright Page instance

    Returns:
        Frame or Page object for main content

    """
    # Try to find frame with FIS_308 content
    for frame in page.frames:
        frame_url = frame.url or ""
        if "FIS_" in frame_url or "FISf_ConsultarNotasFiscaisAvulsas" in frame_url:
            logger.info(f"Found main frame: {frame_url}")
            return frame

    # Fallback: try IFramePrincipal
    try:
        main_frame = page.frame(name="IFramePrincipal")
        if main_frame:
            logger.info("Using IFramePrincipal as main frame")
            return main_frame
    except Exception:
        pass

    # Final fallback: use page itself
    logger.info("Using page as main frame (no iframe detected)")
    return page


async def _fill_consulta_form(
    frame: Frame | Page,
    data_inicial: str,
    data_final: str,
    matricula: str,
    timeout: int = 30000,
) -> bool:
    """Fill the NFA consultation form.

    Args:
        frame: Frame or Page object for main content
        data_inicial: Initial date in DD/MM/YYYY format
        data_final: Final date in DD/MM/YYYY format
        matricula: Employee registration number
        timeout: Timeout in milliseconds

    Returns:
        True if form filled successfully, False otherwise

    """
    try:
        logger.info("Filling consultation form")

        # Wait for form fields
        await frame.wait_for_selector(
            'input[name="edtDtEmissaoNfaeInicial"]',
            timeout=timeout,
        )

        # Fill dates
        await frame.fill('input[name="edtDtEmissaoNfaeInicial"]', data_inicial)
        await frame.fill('input[name="edtDtEmissaoNfaeFinal"]', data_final)
        logger.info(f"Dates filled: {data_inicial} to {data_final}")

        # Fill employee registration (matrícula)
        # Try direct hidden input first
        try:
            await frame.fill(
                'input[name="hidnrMatriculacmpFuncEmitente"]',
                matricula,
            )
            logger.info(f"Matrícula filled via hidden input: {matricula}")
        except Exception:
            # Fallback: try component iframe
            logger.info("Trying component iframe for matrícula")
            try:
                # Look for component frame
                if hasattr(frame, "child_frames"):
                    for child_frame in frame.child_frames:
                        if "cmpFuncEmitente" in (child_frame.url or ""):
                            await child_frame.fill("input[type='text']", matricula)
                            # Try to click search button in component
                            try:
                                await child_frame.click(
                                    "input[type='submit'][value='Pesquisar']",
                                )
                            except Exception:
                                pass
                            logger.info(
                                f"Matrícula filled via component iframe: {matricula}",
                            )
                            break
            except Exception as e:
                logger.warning(f"Could not fill matrícula: {e}")

        # Submit consultation
        logger.info("Submitting consultation form")
        try:
            # Try with navigation wait first
            async with frame.expect_navigation(wait_until="load", timeout=30000):
                await frame.click('input[name="btnConsultar"]')
            logger.info("Consultation form submitted (with navigation)")
        except Exception:
            # Fallback: click without navigation wait (page might just update content)
            logger.info("Clicking consult button without navigation wait")
            await frame.click('input[name="btnConsultar"]')
            await asyncio.sleep(3)  # Wait for results to load
            logger.info("Consultation form submitted (content update)")

        return True

    except Exception as e:
        logger.error(f"Failed to fill consultation form: {e}", exc_info=True)
        return False


async def _select_nfa_from_table(
    frame: Frame | Page,
    timeout: int = 30000,
) -> Optional[str]:
    """Select the first NFA from the results table.

    Args:
        frame: Frame or Page object for main content
        timeout: Timeout in milliseconds

    Returns:
        NFA number if found, None otherwise

    """
    try:
        logger.info("Waiting for results table")
        await frame.wait_for_selector("input[type='radio']", timeout=timeout)

        # Count available radio buttons
        radio_count = await frame.locator("input[type='radio']").count()
        if radio_count == 0:
            logger.warning("No NFA found in results table")
            return None

        logger.info(f"Found {radio_count} NFA(s) in table")

        # Select first radio button
        first_radio = frame.locator("input[type='radio']").first
        await first_radio.click()
        logger.info("First NFA selected")

        # Try to extract NFA number from the same row
        try:
            row = await first_radio.element_handle()
            if row:
                tr = await row.evaluate_handle("el => el.closest('tr')")
                if tr:
                    textos = await tr.evaluate(
                        "el => Array.from(el.querySelectorAll('td')).map(td => td.innerText.trim())",
                    )
                    # Heuristic: find something that looks like a long number
                    for texto in textos:
                        if texto.isdigit() and len(texto) >= 6:
                            logger.info(f"Extracted NFA number: {texto}")
                            return texto
        except Exception as e:
            logger.warning(f"Could not extract NFA number from row: {e}")

        # Fallback: return placeholder
        logger.info("Could not extract NFA number, using placeholder")
        return "UNKNOWN"

    except Exception as e:
        logger.error(f"Failed to select NFA from table: {e}", exc_info=True)
        return None


async def _download_danfe(
    context: BrowserContext,
    frame: Frame | Page,
    nfa_numero: str,
    timeout: int = 30000,
) -> Optional[Path]:
    """Download DANFE PDF.

    Args:
        context: BrowserContext instance (for download handling)
        frame: Frame or Page object for main content
        nfa_numero: NFA number for filename
        timeout: Timeout in milliseconds

    Returns:
        Path to downloaded PDF, or None if failed

    """
    try:
        logger.info(f"Downloading DANFE for NFA {nfa_numero}")

        # Try multiple button selectors
        button_selectors = [
            'input[type="button"][value="Imprimir"]',
            'input[type="button"][value*="Imprimir" i]',
            'button:has-text("Imprimir")',
            'input[name*="Imprimir" i]',
            'input[onclick*="imprimir" i]',
            'a:has-text("Imprimir")',
        ]

        button_found = False
        for selector in button_selectors:
            try:
                await frame.wait_for_selector(selector, timeout=5000)
                logger.info(f"Found DANFE button with selector: {selector}")

                # Wait for download event
                async with context.expect_event(
                    "download", timeout=timeout
                ) as download_info:
                    await frame.click(selector)

                download = await download_info.value
                filename = f"NFA_{nfa_numero}_DANFE.pdf"
                file_path = OUTPUT_DIR / filename

                await download.save_as(str(file_path))
                logger.info(f"DANFE saved to: {file_path}")

                button_found = True
                return file_path
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        if not button_found:
            logger.warning("Could not find DANFE download button")
            return None

    except Exception as e:
        logger.error(f"Failed to download DANFE: {e}", exc_info=True)
        return None


async def _download_dar(
    context: BrowserContext,
    frame: Frame | Page,
    nfa_numero: str,
    timeout: int = 30000,
) -> Optional[Path]:
    """Download DAR PDF.

    Args:
        context: BrowserContext instance (for download handling)
        frame: Frame or Page object for main content
        nfa_numero: NFA number for filename
        timeout: Timeout in milliseconds

    Returns:
        Path to downloaded PDF, or None if failed

    """
    try:
        logger.info(f"Downloading DAR for NFA {nfa_numero}")

        # Try multiple button selectors
        button_selectors = [
            'input[type="button"][value*="Taxa Serviço"]',
            'input[type="button"][value*="Emitir DAR"]',
            'button:has-text("Emitir DAR")',
            'button:has-text("Taxa Serviço")',
            'input[name*="DAR" i]',
            'input[onclick*="dar" i]',
            'a:has-text("DAR")',
            'a:has-text("Taxa")',
        ]

        button_found = False
        for selector in button_selectors:
            try:
                await frame.wait_for_selector(selector, timeout=5000)
                logger.info(f"Found DAR button with selector: {selector}")

                # Wait for download event
                async with context.expect_event(
                    "download", timeout=timeout
                ) as download_info:
                    await frame.click(selector)

                download = await download_info.value
                filename = f"NFA_{nfa_numero}_DAR.pdf"
                file_path = OUTPUT_DIR / filename

                await download.save_as(str(file_path))
                logger.info(f"DAR saved to: {file_path}")

                button_found = True
                return file_path
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        if not button_found:
            logger.warning("Could not find DAR download button")
            return None

    except Exception as e:
        logger.error(f"Failed to download DAR: {e}", exc_info=True)
        return None
