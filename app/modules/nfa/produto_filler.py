"""Produto Form Filler
Handles filling product/item fields in NFA form using direct main-page selectors.
"""

from __future__ import annotations

import logging
import random

from app.modules.nfa.nfa_context import NFAContext, get_page_from_context
from app.modules.nfa.screenshot_utils import resolve_screenshots_dir, save_screenshot

logger = logging.getLogger(__name__)


async def adicionar_item(
    ctx: NFAContext,
    item: dict[str, str],
) -> NFAContext | None:
    """Add product/item to NFA form using direct main-page selectors.

    Args:
        ctx: Page context
        item: Dictionary with product fields:
            - descricao: Product description
            - ncm: NCM code
            - unidade: Unit of measure
            - valor_unitario: Unit value
            - quantidade: Quantity
            - aliquota: Tax rate
            - cst: CST code
            - receita: Revenue code

    Returns:
        Updated NFAContext or None on error

    """
    try:
        page = get_page_from_context(ctx)
        screenshots_dir = resolve_screenshots_dir()

        # Fill NCM (Código NCM)
        ncm = item.get("ncm", "")
        if ncm:
            try:
                element = page.locator("input[name='txtNrNcm']").first
                if await element.is_visible(timeout=5000):
                    await element.clear()
                    await element.type(ncm, delay=random.randint(50, 150))
                    logger.info(f"✓ NCM filled: {ncm}")
                    await page.wait_for_timeout(300)
                    await save_screenshot(
                        page, screenshots_dir, filename="produto_ncm.png"
                    )
            except Exception as e:
                logger.warning(f"Could not fill NCM: {e}")

        # Fill product description (Detalhamento)
        descricao = item.get("descricao", "") or item.get("detalhamento", "")
        if descricao:
            try:
                element = page.locator("textarea[name='txaDsDetalheProduto']").first
                if await element.is_visible(timeout=5000):
                    await element.clear()
                    await element.type(descricao, delay=random.randint(50, 150))
                    logger.info(f"✓ Descrição filled: {descricao[:50]}...")
                    await page.wait_for_timeout(300)
                    await save_screenshot(
                        page, screenshots_dir, filename="produto_descricao.png"
                    )
            except Exception as e:
                logger.warning(f"Could not fill Descrição: {e}")

        # Select unit of measure
        unidade = item.get("unidade", "")
        if unidade:
            try:
                element = page.locator("select[name='cmbUnidadeMedidaItem']").first
                if await element.is_visible(timeout=5000):
                    await element.select_option(unidade)
                    logger.info(f"✓ Unidade selected: {unidade}")
                    await page.wait_for_timeout(300)
                    await save_screenshot(
                        page, screenshots_dir, filename="produto_unidade.png"
                    )
            except Exception as e:
                logger.warning(f"Could not select Unidade: {e}")

        # Fill Quantidade
        quantidade = str(item.get("quantidade", ""))
        if quantidade:
            try:
                element = page.locator("input[name='txtQuantidadeItem']").first
                if await element.is_visible(timeout=5000):
                    await element.clear()
                    await element.type(quantidade, delay=random.randint(50, 150))
                    logger.info(f"✓ Quantidade filled: {quantidade}")
                    await page.wait_for_timeout(300)
                    await save_screenshot(
                        page, screenshots_dir, filename="produto_quantidade.png"
                    )
            except Exception as e:
                logger.warning(f"Could not fill Quantidade: {e}")

        # Fill Valor Unitário
        valor_unitario = str(item.get("valor_unitario", "") or item.get("valor", ""))
        if valor_unitario:
            try:
                element = page.locator("input[name='txtVlrtUnitarioItem']").first
                if await element.is_visible(timeout=5000):
                    await element.clear()
                    await element.type(valor_unitario, delay=random.randint(50, 150))
                    logger.info(f"✓ Valor Unitário filled: {valor_unitario}")
                    await page.wait_for_timeout(300)
                    await save_screenshot(
                        page, screenshots_dir, filename="produto_valor_unitario.png"
                    )
            except Exception as e:
                logger.warning(f"Could not fill Valor Unitário: {e}")

        # Fill CST
        cst = str(item.get("cst", ""))
        if cst:
            try:
                element = page.locator("select[name='cmbCst']").first
                if await element.is_visible(timeout=5000):
                    await element.select_option(cst)
                    logger.info(f"✓ CST selected: {cst}")
                    await page.wait_for_timeout(300)
                    await save_screenshot(
                        page, screenshots_dir, filename="produto_cst.png"
                    )
            except Exception as e:
                logger.warning(f"Could not select CST: {e}")

        # Fill Receita
        receita = str(item.get("receita", ""))
        if receita and receita != "None":
            try:
                element = page.locator("select[name='cmbSqReceitaSefin']").first
                if await element.is_visible(timeout=5000):
                    await element.select_option(receita)
                    logger.info(f"✓ Receita selected: {receita}")
                    await page.wait_for_timeout(300)
                    await save_screenshot(
                        page, screenshots_dir, filename="produto_receita.png"
                    )
            except Exception as e:
                logger.warning(f"Could not select Receita: {e}")

        # Click add/update button
        try:
            submit_selectors = [
                "input[type='submit'][value='Adicionar/Alterar Item']",
                "input[value*='Adicionar' i]",
                "input[value*='Alterar' i]",
                "button:has-text('Adicionar')",
                "button:has-text('Alterar')",
            ]
            for selector in submit_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        await element.click()
                        logger.info("✓ Clicked Adicionar/Alterar Item button")
                        await page.wait_for_timeout(2000)
                        await save_screenshot(
                            page, screenshots_dir, filename="produto_item_added.png"
                        )
                        break
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Could not click add/update button: {e}")

        logger.info(
            f"Item added successfully: {descricao[:50] if descricao else 'N/A'}..."
        )
        return ctx

    except Exception as e:
        logger.error(f"Error adding item: {e}", exc_info=True)
        try:
            page = get_page_from_context(ctx)
            screenshots_dir = resolve_screenshots_dir()
            await save_screenshot(page, screenshots_dir, filename="produto_error.png")
        except Exception:
            pass
        return None
