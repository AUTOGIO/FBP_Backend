"""Produto Form Filler
Handles filling product/item fields in NFA form.
"""
from __future__ import annotations

import logging

from app.modules.nfa.atf_selectors import PRODUTO_TABLE
from app.modules.nfa.nfa_context import NFAContext, get_page_from_context

logger = logging.getLogger(__name__)


async def adicionar_item(
    ctx: NFAContext,
    item: dict[str, str],
) -> NFAContext | None:
    """Add product/item to NFA form.

    Args:
        ctx: Page or Frame context
        item: Dictionary with product fields:
            - descricao: Product description
            - unidade: Unit of measure
            - valor: Unit value
            - quantidade: Quantity
            - aliquota: Tax rate

    Returns:
        Updated NFAContext or None on error

    """
    try:
        # Fill product description
        await ctx.locator(f"{PRODUTO_TABLE} textarea").fill(
            item.get("descricao", ""),
        )

        # Select unit of measure
        await ctx.locator(f"{PRODUTO_TABLE} select").select_option(
            item.get("unidade", ""),
        )

        # Get all number inputs
        nums = ctx.locator("input[type='text']")

        # Fill values in order (adjust indices based on actual form structure)
        if await nums.count() > 0:
            await nums.nth(0).fill(item.get("valor", ""))
        if await nums.count() > 1:
            await nums.nth(1).fill(item.get("quantidade", ""))
        if await nums.count() > 2:
            await nums.nth(2).fill(item.get("aliquota", ""))

        # Click add/update button
        await ctx.locator(
            "input[type='submit'][value='Adicionar/Alterar Item']",
        ).click()

        # Wait for item to be added
        await get_page_from_context(ctx).wait_for_timeout(2000)

        logger.info(f"Item added: {item.get('descricao', '')[:50]}...")
        return ctx

    except Exception as e:
        logger.error(f"Error adding item: {e}", exc_info=True)
        return None
