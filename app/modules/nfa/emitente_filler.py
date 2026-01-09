"""Emitente Form Filler
Handles filling emitente (issuer) fields in NFA form using direct main-page selectors.
"""

from __future__ import annotations

import logging

from app.modules.nfa.delays import FIELD_DELAY
from app.modules.nfa.nfa_context import NFAContext, get_page_from_context
from app.modules.nfa.screenshot_utils import (
    resolve_screenshots_dir,
    save_screenshot,
)

logger = logging.getLogger(__name__)


async def preencher_emitente(ctx: NFAContext, cnpj: str) -> NFAContext | None:
    """Fill emitente (issuer) fields in NFA form using direct main-page selectors.

    Args:
        ctx: Page context
        cnpj: CNPJ to search and fill (format: 28.842.017/0001-05)

    Returns:
        Updated NFAContext or None on error

    """
    try:
        page = get_page_from_context(ctx)
        screenshots_dir = resolve_screenshots_dir()

        logger.info(f"Filling Emitente CNPJ: {cnpj}")

        # Select CNPJ option (2 = CNPJ) in main form
        try:
            tipo_doc_select = page.locator("select[name='cmbTpDoccmpEmitente']").first
            if await tipo_doc_select.is_visible(timeout=5000):
                await tipo_doc_select.select_option("2")  # CNPJ
                logger.info("✓ Selected CNPJ as document type")
                await page.wait_for_timeout(FIELD_DELAY)
                await save_screenshot(
                    page, screenshots_dir, filename="emitente_tipo_doc.png"
                )
        except Exception as e:
            logger.warning(f"Could not select document type: {e}")

        # Fill CNPJ in main page (remove formatting for input)
        cnpj_clean = "".join(
            filter(str.isdigit, cnpj.replace("/", "").replace("-", ""))
        )

        try:
            cnpj_input = page.locator("input[name*='Emitente' i][type='text']").first
            if not await cnpj_input.is_visible(timeout=2000):
                cnpj_input = (
                    page.locator("input[type='text']").filter(has_text="").first
                )
            if await cnpj_input.is_visible(timeout=5000):
                await cnpj_input.clear()
                await cnpj_input.fill(cnpj_clean)
                logger.info(f"✓ CNPJ filled: {cnpj_clean}")
                await page.wait_for_timeout(FIELD_DELAY)
                await save_screenshot(
                    page, screenshots_dir, filename="emitente_cnpj_filled.png"
                )
            else:
                logger.error("CNPJ input not found")
                return None
        except Exception as e:
            logger.error(f"Error filling CNPJ: {e}")
            return None

        # Click Pesquisar button
        try:
            pesquisar_btn = page.get_by_role("button", name="Pesquisar").first
            if not await pesquisar_btn.is_visible(timeout=2000):
                pesquisar_btn = page.locator("input[value='Pesquisar']").first
            if await pesquisar_btn.is_visible(timeout=5000):
                await pesquisar_btn.click()
                logger.info("✓ Clicked Pesquisar for Emitente")
                await page.wait_for_timeout(2000)
                await save_screenshot(
                    page, screenshots_dir, filename="emitente_pesquisar_clicked.png"
                )
            else:
                logger.warning("Pesquisar button not found")
        except Exception as e:
            logger.warning(f"Could not click Pesquisar: {e}")

        logger.info(f"Emitente filled successfully: {cnpj}")
        return ctx

    except Exception as e:
        logger.error(f"Error filling emitente: {e}", exc_info=True)
        try:
            page = get_page_from_context(ctx)
            screenshots_dir = resolve_screenshots_dir()
            await save_screenshot(page, screenshots_dir, filename="emitente_error.png")
        except Exception:
            pass
        return None
