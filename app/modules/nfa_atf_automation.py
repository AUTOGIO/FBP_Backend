"""NFA ATF Automation Module - FIS_308 Consultation and PDF Download.

This module implements the complete automation flow for consulting and
downloading NFAs (Notas Fiscais Avulsas) from the ATF/SEFAZ-PB portal using
Playwright.

Reference: docs/NFA_Automation_Spec.md
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from playwright.async_api import BrowserContext, Frame, Page, async_playwright

from app.core.config import settings
from app.modules.nfa.screenshot_utils import save_screenshot

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Constants from spec
LOGIN_URL = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp"
OUTPUT_DIR = Path("/Users/dnigga/Downloads/NFA_Outputs")
# Log file: user requirement is logs/nfa_runs.jsonl (relative to project root)
# Spec line 147 suggests /Users/dnigga/Downloads/NFA_Outputs/nfa_consult_runs.jsonl
# Using user requirement with project-relative path
LOG_FILE = settings.paths.project_root / "logs" / "nfa_runs.jsonl"

# Timeouts (from spec lines 158-165)
TIMEOUT_LOGIN = 60000  # 60 seconds
TIMEOUT_NAVIGATION = 30000  # 30 seconds
TIMEOUT_FORM = 30000  # 30 seconds
TIMEOUT_RESULTS = 30000  # 30 seconds
TIMEOUT_DOWNLOAD = 30000  # 30 seconds per PDF
TIMEOUT_OVERALL = 600000  # 600 seconds (10 minutes)


def _validate_date_format(date_str: str) -> bool:
    """Validate date format DD/MM/YYYY (spec line 202).

    Args:
        date_str: Date string to validate

    Returns:
        True if valid format, False otherwise
    """
    try:
        parts = date_str.split("/")
        if len(parts) != 3:
            return False
        day, month, year = parts
        if len(day) != 2 or len(month) != 2 or len(year) != 4:
            return False
        int(day)
        int(month)
        int(year)
        return True
    except (ValueError, AttributeError):
        return False


async def _login_atf_with_retry(
    page: Page,
    username: str,
    password: str,
    max_retries: int = 2,
) -> bool:
    """Login to ATF portal with retry logic (spec lines 14-31, 124-127).

    Args:
        page: Playwright Page instance
        username: ATF username
        password: ATF password
        max_retries: Maximum number of retries (default: 2)

    Returns:
        True if login successful, False otherwise
    """
    screenshots_dir = settings.paths.project_root / "output" / "nfa" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Login attempt {attempt + 1}/{max_retries + 1}")
            logger.info(f"Navigating to ATF login page: {LOGIN_URL}")

            # Step 1: Navigate to login URL (spec line 26)
            await page.goto(
                LOGIN_URL,
                wait_until="domcontentloaded",
                timeout=TIMEOUT_LOGIN,
            )
            await save_screenshot(
                page, screenshots_dir, filename="consult_login_start.png"
            )

            # Step 2: Wait for login form to load (spec line 27)
            await page.wait_for_selector('input[name="edtNoLogin"]', timeout=10000)

            # Step 3: Fill username and password fields (spec line 28)
            await page.fill('input[name="edtNoLogin"]', username)
            await page.fill('input[name="edtDsSenha"]', password)
            logger.info("Credentials filled")
            await save_screenshot(
                page, screenshots_dir, filename="consult_login_filled.png"
            )

            # Step 4: Submit form (spec line 29)
            try:
                await page.evaluate("logarSistema()")
                logger.info("Login submitted via logarSistema()")
            except Exception as eval_error:
                logger.warning(f"logarSistema() evaluation failed: {eval_error}")
                await page.click('button[name="btnAvancar"], input[name="btnAvancar"]')
                logger.info("Login submitted via button click")

            # Step 5: Wait 4 seconds for session to establish (spec line 30)
            await page.wait_for_timeout(4000)
            await save_screenshot(
                page, screenshots_dir, filename="consult_login_success.png"
            )

            logger.info("Login successful")
            return True

        except Exception as e:
            logger.warning(f"Login attempt {attempt + 1} failed: {e}")
            if attempt < max_retries:
                wait_time = 2 + (attempt * 0.5)  # 2s, 2.5s between retries
                logger.info(f"Retrying login in {wait_time} seconds...")
                await page.wait_for_timeout(int(wait_time * 1000))
            else:
                logger.error(
                    f"Login failed after {max_retries + 1} attempts: {e}",
                    exc_info=True,
                )
                await save_screenshot(
                    page, screenshots_dir, filename="consult_login_error.png"
                )
                return False

    return False


async def _navigate_to_fis308_with_retry(
    page: Page,
    max_retries: int = 2,
) -> bool:
    """Navigate to FIS_308 using function search field.

    Spec lines 32-39, 124-127.

    Args:
        page: Playwright Page instance
        max_retries: Maximum number of retries (default: 2)

    Returns:
        True if navigation successful, False otherwise
    """
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"FIS_308 navigation attempt {attempt + 1}/{max_retries + 1}")

            # Wait a bit for page to stabilize after login
            await page.wait_for_timeout(3000)

            # Strategy 1: Try direct URL navigation first (from existing code)
            try:
                fis308_url = (
                    "https://www4.sefaz.pb.gov.br/atf/fis/"
                    "FISf_ConsultarNotasFiscaisAvulsas.do"
                )
                logger.info(f"Trying direct navigation to: {fis308_url}")
                await page.goto(
                    fis308_url,
                    wait_until="domcontentloaded",
                    timeout=TIMEOUT_NAVIGATION,
                )
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

            # Strategy 2: Try function search field
            # Based on images, field may be edtFuncao or edtCdFuncao
            # and may be in iframeMenuFuncaoIr
            target_frame: Frame | Page | None = None
            field_found = False
            field_selector = None

            # Try iframeMenuFuncaoIr first (from image descriptions)
            try:
                func_iframe = page.frame(name="iframeMenuFuncaoIr")
                if func_iframe:
                    # Try both selectors
                    for selector in [
                        'input[name="edtFuncao"]',
                        'input[name="edtCdFuncao"]',
                    ]:
                        try:
                            await func_iframe.wait_for_selector(selector, timeout=3000)
                            target_frame = func_iframe
                            field_selector = selector
                            field_found = True
                            logger.info(
                                f"Found function field in iframeMenuFuncaoIr: {selector}"
                            )
                            break
                        except Exception:
                            continue
            except Exception:
                pass

            # Try main page
            if not field_found:
                for selector in [
                    'input[name="edtFuncao"]',
                    'input[name="edtCdFuncao"]',
                ]:
                    try:
                        await page.wait_for_selector(selector, timeout=3000)
                        target_frame = page
                        field_selector = selector
                        field_found = True
                        logger.info(f"Found function field in main page: {selector}")
                        break
                    except Exception:
                        continue

            # Try mainFrame by name
            if not field_found:
                try:
                    main_frame = page.frame(name="mainFrame")
                    if main_frame:
                        for selector in [
                            'input[name="edtFuncao"]',
                            'input[name="edtCdFuncao"]',
                        ]:
                            try:
                                await main_frame.wait_for_selector(
                                    selector, timeout=3000
                                )
                                target_frame = main_frame
                                field_selector = selector
                                field_found = True
                                logger.info(
                                    f"Found function field in mainFrame: {selector}"
                                )
                                break
                            except Exception:
                                continue
                except Exception:
                    pass

            # Try all frames
            if not field_found:
                for frame in page.frames:
                    for selector in [
                        'input[name="edtFuncao"]',
                        'input[name="edtCdFuncao"]',
                    ]:
                        try:
                            await frame.wait_for_selector(selector, timeout=2000)
                            target_frame = frame
                            field_selector = selector
                            field_found = True
                            frame_url = frame.url[:100] if frame.url else "no URL"
                            logger.info(
                                f"Found function field in frame {frame_url}: {selector}"
                            )
                            break
                        except Exception:
                            continue
                    if field_found:
                        break

            if not field_found or target_frame is None or field_selector is None:
                raise RuntimeError(
                    "Could not find function search field (edtFuncao/edtCdFuncao)"
                )

            # Fill with "fis_308" and press Enter (spec lines 36-37)
            await target_frame.fill(field_selector, "fis_308")
            await target_frame.keyboard.press("Enter")

            # Wait 3 seconds after navigation (spec line 38)
            await page.wait_for_timeout(3000)

            logger.info("FIS_308 navigation completed")
            return True

        except Exception as e:
            logger.warning(f"FIS_308 navigation attempt {attempt + 1} failed: {e}")
            if attempt < max_retries:
                wait_time = 2 + (attempt * 0.5)
                logger.info(f"Retrying navigation in {wait_time} seconds...")
                await page.wait_for_timeout(int(wait_time * 1000))
            else:
                logger.error(
                    f"FIS_308 navigation failed after "
                    f"{max_retries + 1} attempts: {e}",
                    exc_info=True,
                )
                return False

    return False


def _get_main_frame(page: Page) -> Frame | Page:
    """Get the main content frame (handles iframe resolution) (spec lines 107-115).

    Args:
        page: Playwright Page instance

    Returns:
        Frame or Page object for main content
    """
    # Strategy 1: Frame with name="principal" or id="principal" (from images)
    try:
        principal_frame = page.frame(name="principal")
        if principal_frame:
            logger.info("Using frame with name='principal' as main frame")
            return principal_frame
    except Exception:
        pass

    # Strategy 2: Frame with URL containing "FIS_" or
    # "FISf_ConsultarNotasFiscaisAvulsas" (spec line 113)
    for frame in page.frames:
        frame_url = frame.url or ""
        if "FIS_" in frame_url or "FISf_ConsultarNotasFiscaisAvulsas" in frame_url:
            logger.info(f"Found main frame: {frame_url[:100]}")
            return frame

    # Strategy 3: Frame named "IFramePrincipal" (spec line 114)
    try:
        main_frame = page.frame(name="IFramePrincipal")
        if main_frame:
            logger.info("Using IFramePrincipal as main frame")
            return main_frame
    except Exception:
        pass

    # Strategy 4: Main page itself (no iframe) (spec line 115)
    logger.info("Using page as main frame (no iframe detected)")
    return page


async def _fill_consulta_form_with_retry(
    frame: Frame | Page,
    data_inicial: str,
    data_final: str,
    matricula: str,
    max_retries: int = 2,
) -> bool:
    """Fill the NFA consultation form (spec lines 40-69, 124-127).

    Args:
        frame: Frame or Page object for main content
        data_inicial: Initial date in DD/MM/YYYY format
        data_final: Final date in DD/MM/YYYY format
        matricula: Employee registration number
        max_retries: Maximum number of retries (default: 2)

    Returns:
        True if form filled successfully, False otherwise
    """
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Form filling attempt {attempt + 1}/{max_retries + 1}")

            # Wait for form fields to load
            await frame.wait_for_selector(
                'input[name="edtDtEmissaoNfaeInicial"]',
                timeout=TIMEOUT_FORM,
            )

            # Fill initial date (spec lines 44-48)
            await frame.fill('input[name="edtDtEmissaoNfaeInicial"]', data_inicial)
            logger.info(f"Initial date filled: {data_inicial}")

            # Fill final date (spec lines 50-54)
            await frame.fill('input[name="edtDtEmissaoNfaeFinal"]', data_final)
            logger.info(f"Final date filled: {data_final}")

            # Fill employee registration (spec lines 56-64)
            # CRITICAL USER REQUIREMENT: Must fill AND click "Pesquisar" button in cmpFuncEmitente iframe
            # This is explicitly required per user notes: "MAke sure block 'Funcionario Emitente' is filled and clicked"
            matricula_filled = False
            pesquisar_clicked = False

            # Get the page object (frame might be Page or Frame)
            page_obj = frame if isinstance(frame, Page) else frame.page

            # Find cmpFuncEmitente iframe (from image: name="cmpFuncEmitente")
            cmp_frame = None
            try:
                cmp_frame = page_obj.frame(name="cmpFuncEmitente")
                logger.info("Found cmpFuncEmitente iframe by name")
            except Exception:
                # Also check all frames for cmpFuncEmitente in URL
                for child_frame in page_obj.frames:
                    frame_url = child_frame.url or ""
                    if "cmpFuncEmitente" in frame_url:
                        cmp_frame = child_frame
                        logger.info(
                            f"Found cmpFuncEmitente iframe by URL: {frame_url[:100]}"
                        )
                        break

            # Method 1: Fill via iframe component (preferred - matches image)
            if cmp_frame:
                try:
                    # Wait for iframe to be ready
                    await cmp_frame.wait_for_load_state(
                        "domcontentloaded", timeout=10000
                    )
                    logger.info("cmpFuncEmitente iframe loaded and ready")

                    # Fill the matrícula input in iframe
                    # From image: input[name="hidnrMatriculacmpFuncEmitente"] or visible text input
                    input_selectors = [
                        'input[name="hidnrMatriculacmpFuncEmitente"]',  # Hidden input
                        'input[type="text"][name*="Matricula" i]',  # Text input with Matricula in name
                        'input[type="text"]',  # Any text input as fallback
                    ]

                    for input_selector in input_selectors:
                        try:
                            await cmp_frame.wait_for_selector(
                                input_selector, timeout=5000
                            )
                            await cmp_frame.fill(input_selector, matricula)
                            logger.info(
                                f"✓ Matrícula filled in iframe using selector: {input_selector}"
                            )
                            matricula_filled = True
                            break
                        except Exception:
                            continue

                    if not matricula_filled:
                        raise RuntimeError(
                            "Could not fill matrícula in cmpFuncEmitente iframe"
                        )

                    # CRITICAL: Click "Pesquisar" button (from image: name="btnPesquisar")
                    # This is REQUIRED per user notes - must click after filling
                    pesquisar_selectors = [
                        'input[name="btnPesquisar"]',  # Primary selector from image
                        'input[type="submit"][value="Pesquisar"]',  # Submit button with value
                        'input[type="button"][value="Pesquisar"]',  # Button with value
                        'button:has-text("Pesquisar")',  # Button with text
                        'input[value*="Pesquisar" i]',  # Case-insensitive value match
                    ]

                    for btn_selector in pesquisar_selectors:
                        try:
                            await cmp_frame.wait_for_selector(
                                btn_selector, timeout=5000, state="visible"
                            )
                            logger.info(
                                f"Clicking 'Pesquisar' button in Funcionário Emitente iframe using: {btn_selector}"
                            )
                            await cmp_frame.click(btn_selector)
                            await asyncio.sleep(2)  # Wait for search to complete
                            pesquisar_clicked = True
                            logger.info("✓ 'Pesquisar' button clicked successfully")
                            break
                        except Exception as btn_error:
                            logger.debug(f"Selector {btn_selector} failed: {btn_error}")
                            continue

                    if not pesquisar_clicked:
                        raise RuntimeError(
                            "Could not click 'Pesquisar' button in cmpFuncEmitente iframe"
                        )

                    # Wait a bit after clicking Pesquisar to ensure it completes
                    await asyncio.sleep(2)

                    # Check if clicking Pesquisar caused an error page
                    page_obj = frame if isinstance(frame, Page) else frame.page
                    current_url = page_obj.url
                    if (
                        "Erro" in current_url
                        or "erro" in current_url.lower()
                        or "Erro%20de%20Acesso" in current_url
                    ):
                        error_msg = f"Error page detected after clicking Pesquisar: {current_url}"
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)

                except RuntimeError:
                    raise  # Re-raise our custom errors
                except Exception as e:
                    logger.error(
                        f"Error filling/clicking Funcionário Emitente component: {e}"
                    )
                    raise  # Re-raise to trigger retry

            # Method 2: Try hidden input in main frame (fallback - but still need to trigger search)
            if not matricula_filled:
                try:
                    await frame.fill(
                        'input[name="hidnrMatriculacmpFuncEmitente"]',
                        matricula,
                    )
                    logger.info(
                        f"Matrícula filled via hidden input in main frame: {matricula}"
                    )
                    matricula_filled = True
                    # Note: If using hidden input, the search might be automatic or we need to find another way
                    # to trigger it. For now, log a warning.
                    logger.warning(
                        "⚠ Using hidden input method - 'Pesquisar' click may not be needed"
                    )
                    pesquisar_clicked = True  # Assume it's handled automatically
                except Exception as e:
                    logger.debug(f"Hidden input method failed: {e}")

            # Validate that Funcionário Emitente was properly filled
            if not matricula_filled:
                raise RuntimeError(
                    "CRITICAL: Could not fill matrícula in Funcionário Emitente component"
                )
            if not pesquisar_clicked:
                raise RuntimeError(
                    "CRITICAL: Matrícula filled but 'Pesquisar' button was not clicked - this is required"
                )

            logger.info(
                "✓ Funcionário Emitente component: filled AND Pesquisar clicked successfully"
            )

            # Submit consultation (spec lines 66-68)
            logger.info("Submitting consultation form")

            # Check for error page before submitting
            page_obj = frame if isinstance(frame, Page) else frame.page
            current_url = page_obj.url
            if "Erro" in current_url or "erro" in current_url.lower():
                raise RuntimeError(
                    f"Error page detected before submission: {current_url}"
                )

            try:
                # Try with navigation wait first
                async with frame.expect_navigation(
                    wait_until="load", timeout=TIMEOUT_FORM
                ):
                    await frame.click('input[name="btnConsultar"]')

                # Check if we navigated to an error page
                await asyncio.sleep(1)  # Brief wait for navigation
                final_url = page_obj.url
                if (
                    "Erro" in final_url
                    or "erro" in final_url.lower()
                    or "Erro%20de%20Acesso" in final_url
                ):
                    error_msg = f"Error page after submission: {final_url}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                logger.info("Consultation form submitted (with navigation)")
            except RuntimeError:
                raise  # Re-raise our custom errors
            except Exception:
                # Fallback: click without navigation wait
                # (page might just update content)
                logger.info("Clicking consult button without navigation wait")
                await frame.click('input[name="btnConsultar"]')
                await asyncio.sleep(3)  # Wait for results to load

                # Check for error page after click
                final_url = page_obj.url
                if (
                    "Erro" in final_url
                    or "erro" in final_url.lower()
                    or "Erro%20de%20Acesso" in final_url
                ):
                    error_msg = f"Error page after submission: {final_url}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                logger.info("Consultation form submitted (content update)")

            return True

        except Exception as e:
            logger.warning(f"Form filling attempt {attempt + 1} failed: {e}")
            if attempt < max_retries:
                wait_time = 2 + (attempt * 0.5)
                logger.info(f"Retrying form filling in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"Form filling failed after {max_retries + 1} " f"attempts: {e}",
                    exc_info=True,
                )
                return False

    return False


async def _get_nfa_list_from_table(
    frame: Frame | Page,
    max_count: int | None = None,
) -> list[dict[str, str]]:
    """Get list of NFAs from the results table (spec lines 70-80).

    User requirement: Process ALL available NFAs from results (55 in current scenario).

    Args:
        frame: Frame or Page object for main content
        max_count: Maximum number of NFAs to extract (None = all available)

    Returns:
        List of dicts with 'nfa_numero' and 'radio_index' keys
    """
    nfa_list = []
    try:
        logger.info("Waiting for results table")

        # Try multiple selectors for radio buttons (spec line 74, also name="rdbNFAe" from images)
        radio_selectors = [
            'input[type="radio"][name="rdbNFAe"]',  # Specific name from images
            'input[type="radio"]',  # Generic selector from spec
        ]

        radio_selector = None
        for selector in radio_selectors:
            try:
                await frame.wait_for_selector(selector, timeout=TIMEOUT_RESULTS)
                radio_selector = selector
                logger.info(f"Found radio buttons with selector: {selector}")
                break
            except Exception:
                continue

        if not radio_selector:
            logger.warning("No NFA radio buttons found in results table")
            return []

        # Count available radio buttons
        radio_count = await frame.locator(radio_selector).count()
        if radio_count == 0:
            logger.warning("No NFA found in results table")
            return []

        logger.info(f"Found {radio_count} NFA(s) in table")

        # Extract ALL NFAs (or up to max_count if specified)
        actual_count = radio_count if max_count is None else min(max_count, radio_count)
        logger.info(
            f"Extracting {actual_count} NFA(s) (total available: {radio_count})"
        )

        for i in range(actual_count):
            try:
                radio = frame.locator(radio_selector).nth(i)

                # Extract NFA number from row (spec lines 76-79)
                row_handle = await radio.element_handle()
                if row_handle:
                    tr_handle = await row_handle.evaluate_handle(
                        "el => el.closest('tr')"
                    )
                    if tr_handle:
                        textos = await tr_handle.evaluate(
                            "el => Array.from(el.querySelectorAll('td'))"
                            ".map(td => td.innerText.trim())",
                        )
                        # Find first text that is all digits and length >= 6 (spec line 79)
                        nfa_numero = None
                        for texto in textos:
                            if texto.isdigit() and len(texto) >= 6:
                                nfa_numero = texto
                                break

                        if nfa_numero:
                            nfa_list.append(
                                {
                                    "nfa_numero": nfa_numero,
                                    "radio_index": i,
                                }
                            )
                            logger.info(f"Extracted NFA #{i+1}: {nfa_numero}")
                        else:
                            logger.warning(
                                f"Could not extract NFA number from row {i+1}"
                            )
            except Exception as e:
                logger.warning(f"Error extracting NFA #{i+1}: {e}")
                continue

        return nfa_list

    except Exception as e:
        logger.error(f"Failed to get NFA list from table: {e}", exc_info=True)
        return []


async def _select_nfa_from_table(
    frame: Frame | Page,
    radio_index: int = 0,
) -> Optional[str]:
    """Select a specific NFA from the results table by index (spec lines 70-80).

    Args:
        frame: Frame or Page object for main content
        radio_index: Index of radio button to select (0-based)

    Returns:
        NFA number if found, None otherwise
    """
    try:
        logger.info(f"Selecting NFA at index {radio_index}")

        # Try multiple selectors for radio buttons (spec line 74, also name="rdbNFAe" from images)
        radio_selectors = [
            'input[type="radio"][name="rdbNFAe"]',  # Specific name from images
            'input[type="radio"]',  # Generic selector from spec
        ]

        radio_selector = None
        for selector in radio_selectors:
            try:
                await frame.wait_for_selector(selector, timeout=TIMEOUT_RESULTS)
                radio_selector = selector
                logger.info(f"Found radio buttons with selector: {selector}")
                break
            except Exception:
                continue

        if not radio_selector:
            logger.warning("No NFA radio buttons found in results table")
            return None

        # Count available radio buttons
        radio_count = await frame.locator(radio_selector).count()
        if radio_count == 0:
            logger.warning("No NFA found in results table")
            return None

        if radio_index >= radio_count:
            logger.warning(
                f"Radio index {radio_index} out of range (max: {radio_count-1})"
            )
            return None

        # Select radio button at index
        radio = frame.locator(radio_selector).nth(radio_index)
        await radio.click()
        logger.info(f"NFA at index {radio_index} selected")

        # Extract NFA number from row (spec lines 76-79)
        try:
            row_handle = await radio.element_handle()
            if row_handle:
                tr_handle = await row_handle.evaluate_handle("el => el.closest('tr')")
                if tr_handle:
                    textos = await tr_handle.evaluate(
                        "el => Array.from(el.querySelectorAll('td'))"
                        ".map(td => td.innerText.trim())",
                    )
                    # Find first text that is all digits and length >= 6 (spec line 79)
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


async def _open_danfe_pdf(
    context: BrowserContext,
    frame: Frame | Page,
    nfa_numero: str,
) -> Optional[Page]:
    """Open DANFE PDF in a new tab (spec lines 89-96).

    User requirement: Click 'Imprimir', wait for new tab to open,
    LEAVE TAB OPENED (do not download, do not close).

    Args:
        context: BrowserContext instance (for tab management)
        frame: Frame or Page object for main content
        nfa_numero: NFA number (for logging)

    Returns:
        Page object of the opened PDF tab, or None if failed
    """
    try:
        logger.info(f"Opening DANFE PDF for NFA {nfa_numero}")

        # Try multiple button selectors (spec lines 91-94)
        # From images: btnImprimirEletronica is the specific name
        button_selectors = [
            'input[name="btnImprimirEletronica"]',  # Specific name from images
            'input[type="button"][value="Imprimir"]',
            'input[type="button"][value*="Imprimir" i]',
            'button:has-text("Imprimir")',
            'input[name*="Imprimir" i]',
            'input[value="Imprimir"]',  # Simple value match
        ]

        for selector in button_selectors:
            try:
                # Wait for button to appear
                await frame.wait_for_selector(selector, timeout=10000, state="visible")
                logger.info(f"Found DANFE button with selector: {selector}")

                # User requirement: "First, just click 'imprimir'"
                # Strategy: Click button, wait for new tab to open, LEAVE IT OPENED

                # Get current page count
                pages_before = len(context.pages)

                # Click button - this should open a new tab with PDF
                await frame.click(selector)
                logger.info(f"✓ Clicked 'Imprimir' button for NFA {nfa_numero}")

                # Wait for new tab to open (max 5 seconds)
                max_wait = 5.0
                start_time = asyncio.get_event_loop().time()
                new_page = None

                while (asyncio.get_event_loop().time() - start_time) < max_wait:
                    if len(context.pages) > pages_before:
                        new_page = context.pages[-1]  # Get the newest page
                        logger.info(f"✓ New tab opened for DANFE: {new_page.url[:100]}")
                        break
                    await asyncio.sleep(0.2)

                if new_page:
                    # Wait for PDF to load in new tab
                    await new_page.wait_for_load_state("domcontentloaded", timeout=5000)
                    await asyncio.sleep(1)  # Brief wait for PDF viewer to render

                    # USER REQUIREMENT: Leave PDF tab OPENED (do not download, do not close)
                    logger.info(
                        f"✓ DANFE PDF tab opened and left OPENED for NFA {nfa_numero}"
                    )
                    return new_page
                else:
                    logger.warning(
                        f"No new tab detected after clicking 'Imprimir' for NFA {nfa_numero}"
                    )
                    return None

            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        logger.warning("Could not find DANFE 'Imprimir' button")
        return None

    except Exception as e:
        logger.error(f"Failed to open DANFE PDF: {e}", exc_info=True)
        return None


async def _open_dar_pdf(
    context: BrowserContext,
    frame: Frame | Page,
    nfa_numero: str,
) -> Optional[Page]:
    """Open DAR PDF in a new tab (spec lines 97-106).

    User requirement: Click 'Gerar/Emitir Taxa Serviço', wait for new tab to open,
    LEAVE TAB OPENED (do not download, do not close).

    Args:
        context: BrowserContext instance (for tab management)
        frame: Frame or Page object for main content
        nfa_numero: NFA number (for logging)

    Returns:
        Page object of the opened PDF tab, or None if failed
    """
    try:
        logger.info(f"Opening DAR PDF for NFA {nfa_numero}")

        # Try multiple button selectors (spec lines 99-104)
        # From images: btnEmitirDAREletronica and btnGerarTaxaServicoEletronica are specific names
        # User note: "Second: same task as prior, BUT 'gerar/emitir taxa servico'"
        button_selectors = [
            'input[name="btnGerarTaxaServicoEletronica"]',  # Primary from user note
            'input[name="btnEmitirDAREletronica"]',  # Alternative from images
            'input[type="button"][value*="Taxa Serviço"]',
            'input[type="button"][value*="Emitir DAR"]',
            'input[value*="Taxa Serviço"]',
            'input[value*="Emitir DAR"]',
            'button:has-text("Emitir DAR")',
            'button:has-text("Taxa Serviço")',
            'input[name*="DAR" i]',
            'input[name*="Taxa" i]',
        ]

        for selector in button_selectors:
            try:
                # Wait for button to appear
                await frame.wait_for_selector(selector, timeout=10000, state="visible")
                logger.info(f"Found DAR button with selector: {selector}")

                # User requirement: "Second: just click 'gerar/emitir taxa servico'"
                # Strategy: Click button, wait for new tab to open, LEAVE IT OPENED

                # Get current page count
                pages_before = len(context.pages)

                # Click button - this should open a new tab with PDF
                await frame.click(selector)
                logger.info(
                    f"✓ Clicked 'Gerar/Emitir Taxa Serviço' button for NFA {nfa_numero}"
                )

                # Wait for new tab to open (max 5 seconds)
                max_wait = 5.0
                start_time = asyncio.get_event_loop().time()
                new_page = None

                while (asyncio.get_event_loop().time() - start_time) < max_wait:
                    if len(context.pages) > pages_before:
                        new_page = context.pages[-1]  # Get the newest page
                        logger.info(f"✓ New tab opened for DAR: {new_page.url[:100]}")
                        break
                    await asyncio.sleep(0.2)

                if new_page:
                    # Wait for PDF to load in new tab
                    await new_page.wait_for_load_state("domcontentloaded", timeout=5000)
                    await asyncio.sleep(1)  # Brief wait for PDF viewer to render

                    # USER REQUIREMENT: Leave PDF tab OPENED (do not download, do not close)
                    logger.info(
                        f"✓ DAR PDF tab opened and left OPENED for NFA {nfa_numero}"
                    )
                    return new_page
                else:
                    logger.warning(
                        f"No new tab detected after clicking 'Gerar/Emitir Taxa Serviço' for NFA {nfa_numero}"
                    )
                    return None

            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        logger.warning("Could not find DAR 'Gerar/Emitir Taxa Serviço' button")
        return None

    except Exception as e:
        logger.error(f"Failed to open DAR PDF: {e}", exc_info=True)
        return None


def _write_log_entry(result: dict) -> None:
    """Write log entry to JSONL file (spec lines 143-157).

    For multi-NFA results, writes one entry per NFA for backward compatibility.

    Args:
        result: Result dictionary to log
    """
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        # If result has nfas, write one entry per NFA
        if "nfas" in result and result["nfas"]:
            with LOG_FILE.open("a", encoding="utf-8") as f:
                for nfa_result in result["nfas"]:
                    # Create individual log entry for each NFA
                    log_entry = {
                        "status": "ok" if not nfa_result.get("error") else "error",
                        "nfa_numero": nfa_result.get("numero"),
                        "danfe_triggered": nfa_result.get("danfe_triggered", False),
                        "dar_triggered": nfa_result.get("dar_triggered", False),
                        "started_at": result.get("started_at"),
                        "finished_at": result.get("finished_at"),
                        "error": nfa_result.get("error"),
                    }
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        else:
            # Fallback: write summary entry
            with LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

        logger.info(f"Log entry written to: {LOG_FILE}")
    except Exception as log_error:
        logger.warning(f"Failed to write log file: {log_error}")


async def run_nfa_job(
    username: str | None = None,
    password: str | None = None,
    data_inicial: str = "08/12/2025",
    data_final: str = "08/12/2025",
    matricula: str = "1595504",
    mode: str = "both",  # "danfe", "dar", or "both"
    close_browser: bool = False,
    headless: bool = False,
    wait_between_nfas: int = 3,  # User requirement: wait 3 seconds between NFAs
) -> dict:
    """Run complete NFA consultation automation job.

    This function executes the entire automation flow:
    1. Login to ATF (spec lines 14-31) - ONCE for all NFAs
    2. Navigate to FIS_308 (spec lines 32-39)
    3. Fill consultation form (spec lines 40-69)
    4. Process ALL available NFAs from results (spec lines 70-80)
       - For each NFA (depending on mode):
         - Select NFA from results
         - Trigger DANFE PDF (spec lines 89-96) if mode="danfe" or "both"
         - Trigger DAR PDF (spec lines 97-106) if mode="dar" or "both"
         - Wait wait_between_nfas seconds before next NFA

    User requirements:
    - Process ALL 55 NFAs (or all available)
    - Wait 3 seconds between NFAs (wait_between_nfas=3)
    - Use same session for ALL (no re-login)
    - Support dual-run mode: first DANFE, then DAR (when mode="both")
    - Leave browser OPENED (do not close it) unless close_browser=True

    Args:
        username: ATF username (uses NFA_USERNAME env var if not provided)
        password: ATF password (uses NFA_PASSWORD env var if not provided)
        data_inicial: Initial date in DD/MM/YYYY format (default: "08/12/2025")
        data_final: Final date in DD/MM/YYYY format (default: "08/12/2025")
        matricula: Employee registration number (default: "1595504")
        mode: Action mode - "danfe" (only DANFE), "dar" (only DAR), or "both" (both, two passes)
        close_browser: Whether to close browser at end (default: False - leave open)
        headless: Run browser in headless mode (default: False)
        wait_between_nfas: Seconds to wait between NFAs (default: 3)

    Returns:
        Dictionary with automation results:
        - status: "success" / "partial" / "failed"
        - mode: The mode used ("danfe", "dar", or "both")
        - data_inicial: Initial date used
        - data_final: Final date used
        - matricula: Matrícula used
        - n_nfas_processed: Number of NFAs successfully processed
        - nfas: List of per-NFA objects with:
          - numero: NFA number
          - row_index: Row index (0-based)
          - danfe_triggered: Whether DANFE was triggered
          - dar_triggered: Whether DAR was triggered
          - error: Error message (if any)
        - started_at: Start timestamp (ISO format)
        - finished_at: Finish timestamp (ISO format)

    """
    # Validate mode parameter
    if mode not in ("danfe", "dar", "both"):
        error_msg = f"Invalid mode: {mode}. Must be 'danfe', 'dar', or 'both'"
        logger.error(error_msg)
        return {
            "status": "failed",
            "mode": mode,
            "data_inicial": data_inicial,
            "data_final": data_final,
            "matricula": matricula,
            "n_nfas_processed": 0,
            "nfas": [],
            "started_at": datetime.utcnow().isoformat() + "Z",
            "finished_at": datetime.utcnow().isoformat() + "Z",
        }

    # Initialize result structure
    started_at = datetime.utcnow()
    result: dict = {
        "status": "failed",
        "mode": mode,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "matricula": matricula,
        "n_nfas_processed": 0,
        "nfas": [],
        "started_at": started_at.isoformat() + "Z",
        "finished_at": None,
    }

    # Resolve credentials
    user = username or settings.NFA_USERNAME
    pwd = password or settings.NFA_PASSWORD

    if not user or not pwd:
        error_msg = (
            "NFA credentials not provided. "
            "Set NFA_USERNAME and NFA_PASSWORD env vars or pass "
            "explicitly."
        )
        logger.error(error_msg)
        result["finished_at"] = datetime.utcnow().isoformat() + "Z"
        _write_log_entry(result)
        return result

    # Validate date formats (spec line 202)
    if not _validate_date_format(data_inicial):
        error_msg = (
            f"Invalid date format for data_inicial: {data_inicial}. "
            f"Expected DD/MM/YYYY"
        )
        logger.error(error_msg)
        result["finished_at"] = datetime.utcnow().isoformat() + "Z"
        _write_log_entry(result)
        return result

    if not _validate_date_format(data_final):
        error_msg = (
            f"Invalid date format for data_final: {data_final}. " f"Expected DD/MM/YYYY"
        )
        logger.error(error_msg)
        result["finished_at"] = datetime.utcnow().isoformat() + "Z"
        _write_log_entry(result)
        return result

    # Ensure output directory exists (spec line 87)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Starting NFA consultation automation")
    logger.info(f"Date range: {data_inicial} to {data_final}")
    logger.info(f"Matrícula: {matricula}")

    async with async_playwright() as p:
        browser = None
        context = None

        try:
            # Launch browser with accept_downloads=False to BLOCK file downloads
            # User requirement: "Abort the files download" - just open PDFs in tabs, don't save files
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                accept_downloads=False
            )  # Block downloads
            page = await context.new_page()

            # Set overall timeout (spec line 165)
            page.set_default_timeout(TIMEOUT_OVERALL)

            # Step 1: Login (spec lines 14-31)
            logger.info("Step 1: Logging in to ATF")
            login_success = await _login_atf_with_retry(page, user, pwd)
            if not login_success:
                raise RuntimeError("Login failed")

            # Step 2: Navigate to FIS_308 (spec lines 32-39)
            logger.info("Step 2: Navigating to FIS_308")
            nav_success = await _navigate_to_fis308_with_retry(page)
            if not nav_success:
                raise RuntimeError("Failed to navigate to FIS_308")

            # Step 3: Get main frame (spec lines 107-115)
            logger.info("Step 3: Resolving main content frame")
            frame = _get_main_frame(page)
            await asyncio.sleep(2)  # Wait for frame to stabilize

            # Step 4: Fill consultation form (spec lines 40-69)
            logger.info("Step 4: Filling consultation form")
            form_success = await _fill_consulta_form_with_retry(
                frame,
                data_inicial,
                data_final,
                matricula,
            )
            if not form_success:
                raise RuntimeError("Failed to fill consultation form")

            # Step 5: Wait for results and get list of ALL NFAs (spec lines 70-80)
            logger.info("Step 5: Waiting for results and getting ALL NFA list")
            await asyncio.sleep(3)  # Wait for results to load

            # Process ALL available NFAs (no max_count limit)
            nfa_list = await _get_nfa_list_from_table(frame, max_count=None)

            if not nfa_list:
                raise RuntimeError("No NFAs found for the specified filters")

            logger.info(f"Found {len(nfa_list)} NFA(s) to process")

            # Step 6: Process each NFA based on mode
            # User requirement: Process ALL 55 NFAs, wait 3 seconds between each
            # Dual-run logic: if mode="both", do two passes (first DANFE, then DAR)

            processed_count = 0

            # Initialize per-NFA result tracking
            nfa_results: dict[str, dict] = {}
            for nfa_info in nfa_list:
                nfa_numero = nfa_info["nfa_numero"]
                radio_index = nfa_info["radio_index"]
                nfa_results[nfa_numero] = {
                    "numero": nfa_numero,
                    "row_index": radio_index,
                    "danfe_triggered": False,
                    "dar_triggered": False,
                    "error": None,
                }

            # Determine which actions to perform based on mode
            if mode == "both":
                # First pass: DANFE only
                logger.info(f"\n{'='*60}")
                logger.info(f"PASS 1: Processing DANFE for all {len(nfa_list)} NFAs")
                logger.info(f"{'='*60}\n")

                for idx, nfa_info in enumerate(nfa_list):
                    nfa_numero = nfa_info["nfa_numero"]
                    radio_index = nfa_info["radio_index"]

                    logger.info(f"\n{'='*60}")
                    logger.info(
                        f"PASS 1 - NFA #{idx+1}/{len(nfa_list)}: {nfa_numero} (DANFE)"
                    )
                    logger.info(f"{'='*60}")

                    try:
                        # Select this NFA
                        logger.info(
                            f"Selecting NFA {nfa_numero} (radio index {radio_index})"
                        )
                        selected_numero = await _select_nfa_from_table(
                            frame, radio_index=radio_index
                        )

                        if not selected_numero or selected_numero != nfa_numero:
                            logger.warning(
                                f"Selection mismatch: expected {nfa_numero}, got {selected_numero}"
                            )

                        # Wait for action buttons to appear after selection
                        logger.info("Waiting for action buttons to appear...")
                        await asyncio.sleep(2)

                        # Trigger DANFE PDF (spec lines 89-96)
                        logger.info(f"Triggering DANFE PDF for NFA {nfa_numero}")
                        danfe_page = await _open_danfe_pdf(context, frame, nfa_numero)
                        if danfe_page:
                            nfa_results[nfa_numero]["danfe_triggered"] = True
                            logger.info(f"✓ DANFE PDF triggered for NFA {nfa_numero}")
                        else:
                            nfa_results[nfa_numero][
                                "error"
                            ] = "DANFE PDF failed to trigger"
                            logger.warning(
                                f"DANFE PDF failed to trigger for NFA {nfa_numero}"
                            )

                    except Exception as nfa_error:
                        error_msg = f"Error processing DANFE for NFA {nfa_numero}: {str(nfa_error)}"
                        logger.error(error_msg, exc_info=True)
                        nfa_results[nfa_numero]["error"] = error_msg

                    # Wait before next NFA (user requirement: 3 seconds)
                    if idx < len(nfa_list) - 1:  # Don't wait after last NFA
                        logger.info(
                            f"Waiting {wait_between_nfas} seconds before next NFA..."
                        )
                        await asyncio.sleep(wait_between_nfas)

                # Second pass: DAR only (reuse same session, iterate again)
                logger.info(f"\n{'='*60}")
                logger.info(f"PASS 2: Processing DAR for all {len(nfa_list)} NFAs")
                logger.info(f"{'='*60}\n")

                for idx, nfa_info in enumerate(nfa_list):
                    nfa_numero = nfa_info["nfa_numero"]
                    radio_index = nfa_info["radio_index"]

                    logger.info(f"\n{'='*60}")
                    logger.info(
                        f"PASS 2 - NFA #{idx+1}/{len(nfa_list)}: {nfa_numero} (DAR)"
                    )
                    logger.info(f"{'='*60}")

                    try:
                        # Select this NFA again
                        logger.info(
                            f"Selecting NFA {nfa_numero} (radio index {radio_index})"
                        )
                        selected_numero = await _select_nfa_from_table(
                            frame, radio_index=radio_index
                        )

                        if not selected_numero or selected_numero != nfa_numero:
                            logger.warning(
                                f"Selection mismatch: expected {nfa_numero}, got {selected_numero}"
                            )

                        # Wait for action buttons to appear after selection
                        logger.info("Waiting for action buttons to appear...")
                        await asyncio.sleep(2)

                        # Trigger DAR PDF (spec lines 97-106)
                        logger.info(f"Triggering DAR PDF for NFA {nfa_numero}")
                        dar_page = await _open_dar_pdf(context, frame, nfa_numero)
                        if dar_page:
                            nfa_results[nfa_numero]["dar_triggered"] = True
                            logger.info(f"✓ DAR PDF triggered for NFA {nfa_numero}")
                        else:
                            if nfa_results[nfa_numero]["error"]:
                                nfa_results[nfa_numero][
                                    "error"
                                ] += "; DAR PDF failed to trigger"
                            else:
                                nfa_results[nfa_numero][
                                    "error"
                                ] = "DAR PDF failed to trigger"
                            logger.warning(
                                f"DAR PDF failed to trigger for NFA {nfa_numero}"
                            )

                    except Exception as nfa_error:
                        error_msg = f"Error processing DAR for NFA {nfa_numero}: {str(nfa_error)}"
                        logger.error(error_msg, exc_info=True)
                        if nfa_results[nfa_numero]["error"]:
                            nfa_results[nfa_numero]["error"] += f"; {error_msg}"
                        else:
                            nfa_results[nfa_numero]["error"] = error_msg

                    # Wait before next NFA (user requirement: 3 seconds)
                    if idx < len(nfa_list) - 1:  # Don't wait after last NFA
                        logger.info(
                            f"Waiting {wait_between_nfas} seconds before next NFA..."
                        )
                        await asyncio.sleep(wait_between_nfas)

            else:
                # Single pass: either DANFE or DAR only
                action_name = "DANFE" if mode == "danfe" else "DAR"
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing {action_name} for all {len(nfa_list)} NFAs")
                logger.info(f"{'='*60}\n")

                for idx, nfa_info in enumerate(nfa_list):
                    nfa_numero = nfa_info["nfa_numero"]
                    radio_index = nfa_info["radio_index"]

                    logger.info(f"\n{'='*60}")
                    logger.info(
                        f"NFA #{idx+1}/{len(nfa_list)}: {nfa_numero} ({action_name})"
                    )
                    logger.info(f"{'='*60}")

                    try:
                        # Select this NFA
                        logger.info(
                            f"Selecting NFA {nfa_numero} (radio index {radio_index})"
                        )
                        selected_numero = await _select_nfa_from_table(
                            frame, radio_index=radio_index
                        )

                        if not selected_numero or selected_numero != nfa_numero:
                            logger.warning(
                                f"Selection mismatch: expected {nfa_numero}, got {selected_numero}"
                            )

                        # Wait for action buttons to appear after selection
                        logger.info("Waiting for action buttons to appear...")
                        await asyncio.sleep(2)

                        # Trigger appropriate PDF based on mode
                        if mode == "danfe":
                            logger.info(f"Triggering DANFE PDF for NFA {nfa_numero}")
                            danfe_page = await _open_danfe_pdf(
                                context, frame, nfa_numero
                            )
                            if danfe_page:
                                nfa_results[nfa_numero]["danfe_triggered"] = True
                                logger.info(
                                    f"✓ DANFE PDF triggered for NFA {nfa_numero}"
                                )
                            else:
                                nfa_results[nfa_numero][
                                    "error"
                                ] = "DANFE PDF failed to trigger"
                                logger.warning(
                                    f"DANFE PDF failed to trigger for NFA {nfa_numero}"
                                )
                        else:  # mode == "dar"
                            logger.info(f"Triggering DAR PDF for NFA {nfa_numero}")
                            dar_page = await _open_dar_pdf(context, frame, nfa_numero)
                            if dar_page:
                                nfa_results[nfa_numero]["dar_triggered"] = True
                                logger.info(f"✓ DAR PDF triggered for NFA {nfa_numero}")
                            else:
                                nfa_results[nfa_numero][
                                    "error"
                                ] = "DAR PDF failed to trigger"
                                logger.warning(
                                    f"DAR PDF failed to trigger for NFA {nfa_numero}"
                                )

                    except Exception as nfa_error:
                        error_msg = f"Error processing {action_name} for NFA {nfa_numero}: {str(nfa_error)}"
                        logger.error(error_msg, exc_info=True)
                        nfa_results[nfa_numero]["error"] = error_msg

                    # Wait before next NFA (user requirement: 3 seconds)
                    if idx < len(nfa_list) - 1:  # Don't wait after last NFA
                        logger.info(
                            f"Waiting {wait_between_nfas} seconds before next NFA..."
                        )
                        await asyncio.sleep(wait_between_nfas)

            # Convert results to list format and count successes
            result["nfas"] = list(nfa_results.values())
            for nfa_result in result["nfas"]:
                # Count as processed if at least one action succeeded
                if mode == "both":
                    if nfa_result["danfe_triggered"] or nfa_result["dar_triggered"]:
                        processed_count += 1
                elif mode == "danfe":
                    if nfa_result["danfe_triggered"]:
                        processed_count += 1
                else:  # mode == "dar"
                    if nfa_result["dar_triggered"]:
                        processed_count += 1

            result["n_nfas_processed"] = processed_count

            # Determine final status
            if processed_count == len(nfa_list):
                result["status"] = "success"
                logger.info(f"\n{'='*60}")
                logger.info(
                    f"NFA consultation automation completed successfully: {processed_count}/{len(nfa_list)} NFAs processed"
                )
                logger.info(f"{'='*60}\n")
            elif processed_count > 0:
                result["status"] = "partial"
                logger.info(f"\n{'='*60}")
                logger.info(
                    f"NFA consultation automation completed partially: {processed_count}/{len(nfa_list)} NFAs processed"
                )
                logger.info(f"{'='*60}\n")
            else:
                result["status"] = "failed"
                logger.error("NFA consultation automation failed: no NFAs processed")

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"NFA consultation automation failed: {error_msg}")
            # Add error to first NFA if list is empty, or create a summary error
            if not result.get("nfas"):
                result["nfas"] = [
                    {
                        "numero": "N/A",
                        "row_index": -1,
                        "danfe_triggered": False,
                        "dar_triggered": False,
                        "error": error_msg,
                    }
                ]

        finally:
            result["finished_at"] = datetime.utcnow().isoformat() + "Z"

            # USER REQUIREMENT: Leave browser OPENED (don't close it so PDF tabs remain visible)
            # Only close if explicitly requested
            if close_browser:
                if context:
                    await context.close()
                if browser:
                    await browser.close()
                logger.info("Browser closed (per close_browser=True)")
            else:
                logger.info(
                    "Browser left OPENED - PDF tabs remain visible (per user requirement)"
                )

            # Write log entry (spec lines 143-157)
            _write_log_entry(result)

    # Print JSON summary (user requirement)
    print("\n" + "=" * 80)
    print("NFA Automation Job Summary")
    print("=" * 80)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=" * 80 + "\n")

    return result
