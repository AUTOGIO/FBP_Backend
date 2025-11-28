"""Endereco Form Filler
Handles filling address fields in NFA form.
"""
from __future__ import annotations

import logging

from app.modules.nfa.atf_selectors import ENDERECO_TABLE
from app.modules.nfa.nfa_context import NFAContext

logger = logging.getLogger(__name__)


async def preencher_endereco(
    ctx: NFAContext,
    data: dict[str, str],
) -> NFAContext | None:
    """Fill address fields in NFA form.

    Args:
        ctx: Page or Frame context
        data: Dictionary with address fields:
            - cep: CEP (postal code)
            - logradouro: Street name
            - numero: Street number
            - complemento: Optional complement
            - bairro: Neighborhood
            - uf: State code

    Returns:
        Updated NFAContext or None on error

    """
    try:
        # Get all text inputs in address table
        inputs = ctx.locator(f"{ENDERECO_TABLE} input[type='text']")

        # Fill fields in order
        await inputs.nth(0).fill(data.get("cep", ""))
        await inputs.nth(1).fill(data.get("logradouro", ""))
        await inputs.nth(2).fill(data.get("numero", ""))
        await inputs.nth(3).fill(data.get("complemento", ""))

        # Bairro might be in a different position, try nth(4)
        if await inputs.count() > 4:
            await inputs.nth(4).fill(data.get("bairro", ""))

        # Select UF (state)
        uf = data.get("uf", "").upper()
        if uf:
            await ctx.locator(f"{ENDERECO_TABLE} select").select_option(uf)

        logger.info(
            f"Endereco filled: {data.get('logradouro', '')}, {data.get('numero', '')}",
        )
        return ctx

    except Exception as e:
        logger.error(f"Error filling endereco: {e}", exc_info=True)
        return None
