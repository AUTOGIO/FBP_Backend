"""Destinatario Form Filler
Handles filling destinatario (recipient) fields in NFA form.
"""
from __future__ import annotations

import logging

from app.modules.nfa.atf_selectors import DEST_TABLE
from app.modules.nfa.nfa_context import NFAContext, get_page_from_context

logger = logging.getLogger(__name__)


async def preencher_destinatario(
    ctx: NFAContext,
    documento: str,
) -> NFAContext | None:
    """Fill destinatario (recipient) fields in NFA form.

    Args:
        ctx: Page or Frame context
        documento: CPF or CNPJ to search and fill

    Returns:
        Updated NFAContext or None on error

    """
    try:
        # Determine document type: CPF (11 digits) = 3, CNPJ (14 digits) = 2
        documento_clean = "".join(filter(str.isdigit, documento))
        tipo = "3" if len(documento_clean) == 11 else "2"

        # Select document type
        await ctx.locator(f"{DEST_TABLE} select").select_option(tipo)

        # Fill document
        await ctx.locator(f"{DEST_TABLE} input[type='text']").first.fill(
            documento,
        )

        # Click search button
        await ctx.locator(f"{DEST_TABLE} input[value='Pesquisar']").click()

        # Wait for search results
        await get_page_from_context(ctx).wait_for_timeout(2000)

        logger.info(f"Destinatario filled: {documento} (type: {tipo})")
        return ctx

    except Exception as e:
        logger.error(f"Error filling destinatario: {e}", exc_info=True)
        return None
