"""NFA Form Filler - Main Orchestrator
Coordinates filling all sections of the NFA form.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from app.modules.nfa.campos_fixos_filler import preencher_campos_fixos
from app.modules.nfa.destinatario_filler import preencher_destinatario
from app.modules.nfa.emitente_filler import preencher_emitente
from app.modules.nfa.endereco_filler import preencher_endereco
from app.modules.nfa.informacoes_adicionais_filler import (
    preencher_informacoes_adicionais,
)
from app.modules.nfa.nfa_context import (
    NFAContext,
    get_page_from_context,
    resolve_nfa_context,
    wait_for_nfa_ready,
)
from app.modules.nfa.produto_filler import adicionar_item
from app.modules.nfa.screenshot_utils import resolve_screenshots_dir, save_screenshot

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def preencher_nfa(page: Page, dados: dict) -> bool:
    """Fill complete NFA form with all sections.

    Args:
        page: Playwright Page instance
        dados: Dictionary with form data:
            - emitente: {cnpj: str}
            - destinatario: {documento: str}
            - endereco: {cep, logradouro, numero, complemento, bairro, uf}
            - item: {descricao, unidade, valor, quantidade, aliquota}

    Returns:
        True if form filled successfully, False otherwise

    """
    ctx: NFAContext | None = None
    try:
        logger.info("Starting NFA form filling")

        # Resolve NFA context (handles both Page and Frame)
        ctx = await resolve_nfa_context(page)
        await wait_for_nfa_ready(ctx, timeout=45000)
        logger.info("NFA context resolved and ready")

        # Fill fixed fields first (natureza, motivo, repartição, etc.)
        valores_fixos = dados.get("valores_fixos", {})
        ctx_result = await preencher_campos_fixos(ctx, valores_fixos)
        if ctx_result:
            ctx = ctx_result
        else:
            logger.warning("Failed to fill fixed fields, continuing anyway...")
        await get_page_from_context(ctx).wait_for_timeout(1000)

        # Fill emitente
        emitente_cnpj = dados.get("emitente", {}).get("cnpj", "")
        if emitente_cnpj:
            ctx = await preencher_emitente(ctx, emitente_cnpj)
            if not ctx:
                logger.error("Failed to fill emitente")
                return False
            await get_page_from_context(ctx).wait_for_timeout(1000)

        # Fill destinatario
        destinatario_doc = dados.get("destinatario", {}).get("documento", "")
        if destinatario_doc:
            ctx = await preencher_destinatario(ctx, destinatario_doc)
            if not ctx:
                logger.error("Failed to fill destinatario")
                return False
            await get_page_from_context(ctx).wait_for_timeout(1000)

        # Fill endereco
        endereco_data = dados.get("endereco", {})
        if endereco_data:
            ctx = await preencher_endereco(ctx, endereco_data)
            if not ctx:
                logger.error("Failed to fill endereco")
                return False
            await get_page_from_context(ctx).wait_for_timeout(1000)

        # Add item
        item_data = dados.get("item", {})
        if item_data:
            ctx = await adicionar_item(ctx, item_data)
            if not ctx:
                logger.error("Failed to add item")
                return False
            await get_page_from_context(ctx).wait_for_timeout(1000)

        # Fill Informações Adicionais
        informacoes_texto = dados.get(
            "informacoes_adicionais", "Remessa por conta de contrato de locacao"
        )
        ctx_result = await preencher_informacoes_adicionais(ctx, informacoes_texto)
        if ctx_result:
            ctx = ctx_result
        else:
            logger.warning(
                "Failed to fill Informações Adicionais, continuing anyway..."
            )
        await get_page_from_context(ctx).wait_for_timeout(1000)

        logger.info("NFA form filled successfully")
        return True

    except Exception as e:
        logger.error(f"Error filling NFA form: {e}", exc_info=True)
        # Save screenshot on error
        try:
            screenshots_dir = resolve_screenshots_dir()
            page_for_screenshot = page if ctx is None else get_page_from_context(ctx)
            await save_screenshot(
                page_for_screenshot,
                screenshots_dir,
                filename="nfa_form_error.png",
            )
        except Exception as screenshot_error:
            logger.warning(f"Failed to save error screenshot: {screenshot_error}")
        return False


async def fill_nfa_form_complete(
    page: Page,
    form_data: dict,
    screenshots_dir: Optional[str] = None,
    config: Optional[dict] = None,
) -> bool:
    """Fill complete NFA form with extended data.

    Args:
        page: Playwright Page instance
        form_data: Complete form data dictionary
        screenshots_dir: Optional directory for screenshots (from config if None)
        config: Optional configuration dictionary (may contain paths.screenshots_dir)

    Returns:
        True if form filled successfully, False otherwise

    """
    ctx: NFAContext | None = None
    try:
        # Resolve screenshots_dir from config if provided
        if screenshots_dir is None and config:
            screenshots_dir = config.get("paths", {}).get("screenshots_dir")

        # Map form_data to expected format
        # Handle both old format (emitente_cnpj) and new format (emitente.cnpj)
        emitente_data = form_data.get("emitente", {})
        if isinstance(emitente_data, dict):
            emitente_cnpj = emitente_data.get("cnpj", "") or form_data.get(
                "emitente_cnpj", ""
            )
        else:
            emitente_cnpj = form_data.get("emitente_cnpj", "")

        destinatario_data = form_data.get("destinatario", {})
        if isinstance(destinatario_data, dict):
            destinatario_doc = destinatario_data.get("documento", "") or form_data.get(
                "destinatario_doc", ""
            )
            endereco_data = destinatario_data.get("endereco", {}) or form_data.get(
                "endereco", {}
            )
        else:
            destinatario_doc = form_data.get("destinatario_doc", "")
            endereco_data = form_data.get("endereco", {})

        # Handle produtos array
        produtos = form_data.get("produtos", [])
        item_data = produtos[0] if produtos else form_data.get("item", {})

        # Use fixed values for fields that don't change
        fixed_values = {
            "natureza_operacao": form_data.get("natureza_operacao", "REMESSA"),
            "motivo": form_data.get("motivo", "DESPACHO"),
            "reparticao_fiscal": form_data.get("reparticao_fiscal", "90102008"),
            "codigo_municipio": form_data.get("codigo_municipio", "2051-6"),
            "tipo_operacao": form_data.get("tipo_operacao", "SAIDA"),
            "cfop": form_data.get("cfop", "6908"),
        }

        # Map to internal format with fixed product values
        item_defaults = {
            "descricao": form_data.get("detalhamento_produto", "1 - SID241"),
            "ncm": form_data.get("ncm", "0000.00.00"),
            "unidade": form_data.get("unidade", "UN"),
            "valor_unitario": form_data.get("valor_unitario", 1100),
            "quantidade": form_data.get("quantidade", 1),
            "aliquota": form_data.get("aliquota", 0),
            "cst": form_data.get("cst", "41"),
            "receita": form_data.get(
                "receita", "1199 - ICMS - OUTROS (COMERCIO E INDUSTRIA)"
            ),
        }

        # Merge with provided item_data
        if item_data:
            item_defaults.update(item_data)

        dados = {
            "valores_fixos": fixed_values,
            "emitente": {
                "cnpj": emitente_cnpj,
            },
            "destinatario": {
                "documento": destinatario_doc,
            },
            "endereco": (
                endereco_data
                if endereco_data
                else {
                    "cep": form_data.get("cep", ""),
                    "logradouro": form_data.get("logradouro", ""),
                    "numero": form_data.get("numero", ""),
                    "complemento": form_data.get("complemento", ""),
                    "bairro": form_data.get("bairro", ""),
                    "uf": form_data.get("uf", ""),
                }
            ),
            "item": item_defaults,
            "informacoes_adicionais": form_data.get(
                "informacoes_adicionais", "Remessa por conta de contrato de locacao"
            ),
        }

        return await preencher_nfa(page, dados)

    except Exception as e:
        logger.error(f"Error in fill_nfa_form_complete: {e}", exc_info=True)
        # Save screenshot on error
        try:
            page_for_screenshot = page if ctx is None else get_page_from_context(ctx)
            await save_screenshot(
                page_for_screenshot,
                screenshots_dir,
                filename="nfa_form_complete_error.png",
            )
        except Exception as screenshot_error:
            logger.warning(f"Failed to save error screenshot: {screenshot_error}")
        return False
