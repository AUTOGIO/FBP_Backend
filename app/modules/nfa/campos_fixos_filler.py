"""Campos Fixos (Fixed Fields) Form Filler
Handles filling fixed/static fields in NFA form that don't change per request.
"""

from __future__ import annotations

import logging
import random

from app.modules.nfa.delays import AFTER_CAMPOS_FIXOS_DELAY, FIELD_DELAY
from app.modules.nfa.nfa_context import NFAContext, get_page_from_context
from app.modules.nfa.screenshot_utils import (
    resolve_screenshots_dir,
    save_screenshot,
)

logger = logging.getLogger(__name__)

# Fixed values that don't change per NFA
FIXED_VALUES = {
    "natureza_operacao": "REMESSA",
    "motivo": "DESPACHO",
    "reparticao_fiscal": "90102008",
    "codigo_municipio": "2051-6",
    "tipo_operacao": "SAIDA",
    "cfop": "6908",
}


async def preencher_campos_fixos(
    ctx: NFAContext,
    valores_fixos: dict[str, str] | None = None,
) -> NFAContext | None:
    """Fill fixed fields in NFA form using direct main-page selectors.

    Args:
        ctx: Page context
        valores_fixos: Optional dictionary to override fixed values

    Returns:
        Updated NFAContext or None on error

    """
    try:
        page = get_page_from_context(ctx)
        valores = valores_fixos or FIXED_VALUES
        screenshots_dir = resolve_screenshots_dir()

        logger.info("Filling fixed fields (Campos Fixos)")

        # Fill Natureza da Operação
        natureza = valores.get("natureza_operacao", "REMESSA")
        try:
            element = page.locator("select[name='cmbNaturezaOperacao']").first
            if await element.is_visible(timeout=5000):
                await element.select_option(natureza)
                logger.info(f"✓ Natureza da Operação: {natureza}")
                await page.wait_for_timeout(FIELD_DELAY)
                await save_screenshot(
                    page, screenshots_dir, filename="campos_fixos_natureza.png"
                )
        except Exception as e:
            logger.warning(f"Could not fill Natureza da Operação: {e}")

        # Fill Motivo
        motivo = valores.get("motivo", "DESPACHO")
        try:
            element = page.locator("select[name='cmbMotivo']").first
            if await element.is_visible(timeout=5000):
                await element.select_option(motivo)
                logger.info(f"✓ Motivo: {motivo}")
                await page.wait_for_timeout(FIELD_DELAY)
                await save_screenshot(
                    page, screenshots_dir, filename="campos_fixos_motivo.png"
                )
        except Exception as e:
            logger.warning(f"Could not fill Motivo: {e}")

        # Fill Repartição Fiscal
        reparticao = valores.get("reparticao_fiscal", "90102008")
        try:
            element = page.locator("input[name='txtCdReparticaoFiscal']").first
            if await element.is_visible(timeout=5000):
                await element.clear()
                await element.type(reparticao, delay=random.randint(50, 150))
                logger.info(f"✓ Repartição Fiscal: {reparticao}")
                await page.wait_for_timeout(FIELD_DELAY)
                await save_screenshot(
                    page, screenshots_dir, filename="campos_fixos_reparticao.png"
                )
        except Exception as e:
            logger.warning(f"Could not fill Repartição Fiscal: {e}")

        # Fill Código do Município
        codigo_municipio = valores.get("codigo_municipio", "2051-6")
        codigo_formats = [codigo_municipio, codigo_municipio.replace("-", "")]
        for codigo_format in codigo_formats:
            try:
                element = page.locator("input[name='txtCdMunicipio']").first
                if await element.is_visible(timeout=5000):
                    await element.clear()
                    await element.type(codigo_format, delay=random.randint(50, 150))
                    logger.info(f"✓ Código do Município: {codigo_format}")
                    await page.wait_for_timeout(FIELD_DELAY)
                    await save_screenshot(
                        page, screenshots_dir, filename="campos_fixos_municipio.png"
                    )
                    break
            except Exception:
                continue

        # Fill Tipo de Operação
        tipo_operacao = valores.get("tipo_operacao", "SAIDA")
        try:
            element = page.locator("select[name='cmbTipoOperacao']").first
            if await element.is_visible(timeout=5000):
                await element.select_option(tipo_operacao)
                logger.info(f"✓ Tipo de Operação: {tipo_operacao}")
                await page.wait_for_timeout(FIELD_DELAY)
                await save_screenshot(
                    page, screenshots_dir, filename="campos_fixos_tipo_operacao.png"
                )
        except Exception as e:
            logger.warning(f"Could not fill Tipo de Operação: {e}")

        # Fill CFOP
        cfop = valores.get("cfop", "6908")
        try:
            element = page.locator("select[name='cmbNrCfop']").first
            if await element.is_visible(timeout=5000):
                await element.select_option(cfop)
                logger.info(f"✓ CFOP: {cfop}")
                await page.wait_for_timeout(FIELD_DELAY)
                await save_screenshot(
                    page, screenshots_dir, filename="campos_fixos_cfop.png"
                )
        except Exception as e:
            logger.warning(f"Could not fill CFOP: {e}")

        await page.wait_for_timeout(AFTER_CAMPOS_FIXOS_DELAY)
        await save_screenshot(
            page, screenshots_dir, filename="campos_fixos_complete.png"
        )
        logger.info("Fixed fields filled successfully")
        return ctx

    except Exception as e:
        logger.error(f"Error filling fixed fields: {e}", exc_info=True)
        try:
            page = get_page_from_context(ctx)
            screenshots_dir = resolve_screenshots_dir()
            await save_screenshot(
                page, screenshots_dir, filename="campos_fixos_error.png"
            )
        except Exception:
            pass
        return None
