"""Emitente Form Filler
Handles filling emitente (issuer) fields in NFA form.
"""
from __future__ import annotations

import logging

from app.modules.nfa.atf_selectors import EMITENTE_TABLE
from app.modules.nfa.nfa_context import NFAContext, get_page_from_context

logger = logging.getLogger(__name__)


async def preencher_emitente(ctx: NFAContext, cnpj: str) -> NFAContext | None:
    """Fill emitente (issuer) fields in NFA form.

    Args:
        ctx: Page or Frame context resolved by resolve_nfa_context
        cnpj: CNPJ to search and fill

    Returns:
        Updated NFAContext or None on error

    """
    try:
        # Select CNPJ option (2 = CNPJ)
        await ctx.locator(f"{EMITENTE_TABLE} select").select_option("2")

        # Fill CNPJ
        await ctx.locator(f"{EMITENTE_TABLE} input[type='text']").first.fill(
            cnpj,
        )

        # Click search button
        await ctx.locator(
            f"{EMITENTE_TABLE} input[value='Pesquisar']",
        ).click()

        # Wait for search results
        await get_page_from_context(ctx).wait_for_timeout(2000)

        logger.info(f"Emitente filled: {cnpj}")
        return ctx

    except Exception as e:
        logger.error(f"Error filling emitente: {e}", exc_info=True)
        return None
