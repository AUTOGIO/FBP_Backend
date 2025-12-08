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
            - logradouro: Street name (ENDEREÇO)
            - numero: Street number (NÚMERO)
            - complemento: Optional complement
            - bairro: Neighborhood (BAIRRO)
            - municipio: City (MUNICÍPIO)
            - uf: State code (UF)
            - telefone: Phone number (TELEFONE)

    Returns:
        Updated NFAContext or None on error

    """
    try:
        # Try to find fields by label/name first (more reliable)
        # CEP field
        cep = data.get("cep", "")
        if cep:
            cep_selectors = [
                f"{ENDERECO_TABLE} input[name*='CEP' i]",
                f"{ENDERECO_TABLE} input[id*='CEP' i]",
                f"{ENDERECO_TABLE} td:has-text('CEP') + td input",
            ]
            for selector in cep_selectors:
                try:
                    element = ctx.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        await element.fill(cep)
                        logger.info(f"CEP filled: {cep}")
                        break
                except Exception:
                    continue

        # ENDEREÇO (logradouro) field
        logradouro = data.get("logradouro", "") or data.get("endereco", "")
        if logradouro:
            endereco_selectors = [
                f"{ENDERECO_TABLE} input[name*='Endereco' i]",
                f"{ENDERECO_TABLE} input[name*='Logradouro' i]",
                f"{ENDERECO_TABLE} input[id*='Endereco' i]",
                f"{ENDERECO_TABLE} td:has-text('Endereço') + td input",
                f"{ENDERECO_TABLE} td:has-text('Logradouro') + td input",
            ]
            for selector in endereco_selectors:
                try:
                    element = ctx.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        await element.fill(logradouro)
                        logger.info(f"ENDEREÇO filled: {logradouro}")
                        break
                except Exception:
                    continue

        # NÚMERO field
        numero = data.get("numero", "")
        if numero:
            numero_selectors = [
                f"{ENDERECO_TABLE} input[name*='Numero' i]",
                f"{ENDERECO_TABLE} input[name*='Número' i]",
                f"{ENDERECO_TABLE} input[id*='Numero' i]",
                f"{ENDERECO_TABLE} td:has-text('Número') + td input",
            ]
            for selector in numero_selectors:
                try:
                    element = ctx.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        await element.fill(numero)
                        logger.info(f"NÚMERO filled: {numero}")
                        break
                except Exception:
                    continue

        # BAIRRO field
        bairro = data.get("bairro", "")
        if bairro:
            bairro_selectors = [
                f"{ENDERECO_TABLE} input[name*='Bairro' i]",
                f"{ENDERECO_TABLE} input[id*='Bairro' i]",
                f"{ENDERECO_TABLE} td:has-text('Bairro') + td input",
            ]
            for selector in bairro_selectors:
                try:
                    element = ctx.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        await element.fill(bairro)
                        logger.info(f"BAIRRO filled: {bairro}")
                        break
                except Exception:
                    continue

        # MUNICÍPIO field
        municipio = data.get("municipio", "") or data.get("município", "")
        if municipio:
            municipio_selectors = [
                f"{ENDERECO_TABLE} input[name*='Municipio' i]",
                f"{ENDERECO_TABLE} input[name*='Município' i]",
                f"{ENDERECO_TABLE} input[id*='Municipio' i]",
                f"{ENDERECO_TABLE} td:has-text('Município') + td input",
            ]
            for selector in municipio_selectors:
                try:
                    element = ctx.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        await element.fill(municipio)
                        logger.info(f"MUNICÍPIO filled: {municipio}")
                        break
                except Exception:
                    continue

        # UF (state) field - use select
        uf = data.get("uf", "").upper()
        if uf:
            uf_selectors = [
                f"{ENDERECO_TABLE} select[name*='UF' i]",
                f"{ENDERECO_TABLE} select[name*='Estado' i]",
                f"{ENDERECO_TABLE} select[id*='UF' i]",
                f"{ENDERECO_TABLE} td:has-text('UF') + td select",
            ]
            for selector in uf_selectors:
                try:
                    element = ctx.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        await element.select_option(uf)
                        logger.info(f"UF filled: {uf}")
                        break
                except Exception:
                    continue

        # TELEFONE field (if present)
        telefone = data.get("telefone", "")
        if telefone:
            telefone_selectors = [
                f"{ENDERECO_TABLE} input[name*='Telefone' i]",
                f"{ENDERECO_TABLE} input[id*='Telefone' i]",
                f"{ENDERECO_TABLE} td:has-text('Telefone') + td input",
            ]
            for selector in telefone_selectors:
                try:
                    element = ctx.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        await element.fill(telefone)
                        logger.info(f"TELEFONE filled: {telefone}")
                        break
                except Exception:
                    continue

        # Fallback: use nth() approach if label-based selectors fail
        try:
            inputs = ctx.locator(f"{ENDERECO_TABLE} input[type='text']")
            input_count = await inputs.count()

            if input_count > 0 and not cep:
                await inputs.nth(0).fill(data.get("cep", ""))
            if input_count > 1 and not logradouro:
                await inputs.nth(1).fill(data.get("logradouro", ""))
            if input_count > 2 and not numero:
                await inputs.nth(2).fill(data.get("numero", ""))
            if input_count > 3:
                await inputs.nth(3).fill(data.get("complemento", ""))
            if input_count > 4 and not bairro:
                await inputs.nth(4).fill(data.get("bairro", ""))
        except Exception as e:
            logger.debug(f"Fallback nth() approach failed: {e}")

        # Fallback for UF select
        if not uf:
            try:
                await ctx.locator(f"{ENDERECO_TABLE} select").select_option(uf)
            except Exception:
                pass

        logger.info(
            f"Endereco filled: {logradouro}, {numero}",
        )
        return ctx

    except Exception as e:
        logger.error(f"Error filling endereco: {e}", exc_info=True)
        return None
