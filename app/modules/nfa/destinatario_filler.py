"""Destinatario Form Filler
Handles filling destinatario (recipient) fields in NFA form using direct main-page selectors.
"""

from __future__ import annotations

import logging

from app.modules.nfa.delays import FIELD_DELAY
from app.modules.nfa.nfa_context import NFAContext, get_page_from_context
from app.modules.nfa.screenshot_utils import resolve_screenshots_dir, save_screenshot

logger = logging.getLogger(__name__)


async def preencher_destinatario(
    ctx: NFAContext,
    documento: str,
) -> NFAContext | None:
    """Fill destinatario (recipient) fields in NFA form using direct main-page selectors.

    Args:
        ctx: Page context
        documento: CPF or CNPJ to search and fill (format: 738.255.062-15 for CPF)

    Returns:
        Updated NFAContext or None on error

    """
    try:
        page = get_page_from_context(ctx)
        screenshots_dir = resolve_screenshots_dir()

        # Determine document type: CPF (11 digits) = 3, CNPJ (14 digits) = 2
        documento_clean = "".join(
            filter(str.isdigit, documento.replace("/", "").replace("-", ""))
        )
        tipo = "3" if len(documento_clean) == 11 else "2"

        logger.info(f"Filling Destinatario {documento_clean} (type: {tipo})")

        # Select document type in main form (3 = CPF, 2 = CNPJ)
        try:
            tipo_doc_select = page.locator(
                "select[name='cmbTpDoccmpDestinatario']"
            ).first
            if await tipo_doc_select.is_visible(timeout=5000):
                await tipo_doc_select.select_option(tipo)
                logger.info(f"✓ Selected document type: {tipo}")
                await page.wait_for_timeout(FIELD_DELAY)
                await save_screenshot(
                    page, screenshots_dir, filename="destinatario_tipo_doc.png"
                )
        except Exception as e:
            logger.warning(f"Could not select document type: {e}")

        # Fill document in main page
        try:
            doc_input = page.locator("input[name*='Destinatario' i][type='text']").first
            if not await doc_input.is_visible(timeout=2000):
                doc_input = (
                    page.locator("input[type='text']").filter(has_text="").nth(1)
                )
            if await doc_input.is_visible(timeout=5000):
                await doc_input.clear()
                await doc_input.fill(documento_clean)
                logger.info(f"✓ Document filled: {documento_clean}")
                await page.wait_for_timeout(FIELD_DELAY)
                await save_screenshot(
                    page, screenshots_dir, filename="destinatario_doc_filled.png"
                )
            else:
                logger.error("Document input not found")
                return None
        except Exception as e:
            logger.error(f"Error filling document: {e}")
            return None

        # Click Pesquisar button
        try:
            pesquisar_btn = page.get_by_role("button", name="Pesquisar").first
            if not await pesquisar_btn.is_visible(timeout=2000):
                pesquisar_btn = page.locator("input[value='Pesquisar']").first
            if await pesquisar_btn.is_visible(timeout=5000):
                await pesquisar_btn.click()
                logger.info("✓ Clicked Pesquisar for Destinatario")
                await page.wait_for_timeout(2000)
                await save_screenshot(
                    page, screenshots_dir, filename="destinatario_pesquisar_clicked.png"
                )
            else:
                logger.warning("Pesquisar button not found")
        except Exception as e:
            logger.warning(f"Could not click Pesquisar: {e}")

        logger.info(
            f"Destinatario filled successfully: {documento_clean} (type: {tipo})"
        )
        return ctx

    except Exception as e:
        logger.error(f"Error filling destinatario: {e}", exc_info=True)
        try:
            page = get_page_from_context(ctx)
            screenshots_dir = resolve_screenshots_dir()
            await save_screenshot(
                page, screenshots_dir, filename="destinatario_error.png"
            )
        except Exception:
            pass
        return None
