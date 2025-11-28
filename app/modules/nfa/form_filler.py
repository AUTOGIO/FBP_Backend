"""NFA Form Filler - Main Orchestrator
Coordinates filling all sections of the NFA form regardless of DOM context.
"""
from __future__ import annotations

from typing import Any

from app.core.logging_config import setup_logger
from app.modules.nfa.form_utils import (
    click_calcular,
    fill_form_fields,
    set_form_value,
)
from app.modules.nfa.nfa_context import NFAContext

logger = setup_logger(__name__)


async def preencher_nfa(
    ctx: NFAContext,
    dados: dict[str, Any],
) -> bool:
    """Fill complete NFA form with all sections.

    Args:
        ctx: Playwright Page or Frame instance
        dados: Dictionary with form data:
            - emitente: {cnpj: str}
            - destinatario: {documento: str}
            - endereco: {cep, logradouro, numero, complemento, bairro, uf}
            - item: {descricao, unidade, valor, quantidade, aliquota}
    Returns:
        True if form filled successfully, False otherwise
    """
    try:
        logger.info("Starting NFA form filling")

        # Fill emitente
        emitente_cnpj = dados.get("emitente", {}).get("cnpj", "")
        if emitente_cnpj:
            logger.debug(f"Filling emitente CNPJ: {emitente_cnpj}")
            await set_form_value(ctx, "cnpjEmitente", emitente_cnpj)

        # Fill destinatario
        destinatario_doc = dados.get("destinatario", {}).get("documento", "")
        if destinatario_doc:
            logger.debug(f"Filling destinatario: {destinatario_doc}")
            # Determine field based on document length (CPF=11, CNPJ=14)
            clean_doc = "".join(filter(str.isdigit, destinatario_doc))
            if len(clean_doc) == 11:
                await set_form_value(ctx, "cpfDestinatario", destinatario_doc)
            else:
                await set_form_value(ctx, "cnpjDestinatario", destinatario_doc)

        # Fill endereco
        endereco_data = dados.get("endereco", {})
        if endereco_data:
            logger.debug("Filling endereco...")
            endereco_fields = {
                "cep": endereco_data.get("cep", ""),
                "logradouro": endereco_data.get("logradouro", ""),
                "numero": endereco_data.get("numero", ""),
                "complemento": endereco_data.get("complemento", ""),
                "bairro": endereco_data.get("bairro", ""),
                "uf": endereco_data.get("uf", ""),
            }
            await fill_form_fields(ctx, endereco_fields)

        # Fill item/product
        item_data = dados.get("item", {})
        if item_data:
            logger.debug("Filling item...")
            item_fields = {
                "descProduto": item_data.get("descricao", ""),
                "unidade": item_data.get("unidade", ""),
                "valorUnitario": item_data.get("valor", ""),
                "quantidade": item_data.get("quantidade", ""),
                "aliquota": item_data.get("aliquota", ""),
            }
            await fill_form_fields(ctx, item_fields)

        logger.info("NFA form filled successfully")
        return True

    except Exception as e:
        logger.error(f"Error filling NFA form: {e}", exc_info=True)
        return False


async def fill_nfa_form_complete(
    ctx: NFAContext,
    form_data: dict[str, Any],
    screenshots_dir: str | None = None,
    config: dict[str, Any] | None = None,
) -> bool:
    """Fill complete NFA form with extended data (Scenario C format).

    Args:
        ctx: Page or Frame instance resolved via NFAContext
        form_data: Complete form data dictionary (17 fields)
        screenshots_dir: Optional directory for screenshots
        config: Optional configuration dictionary
    Returns:
        True if form filled successfully, False otherwise
    """
    try:
        logger.info("Filling NFA form (Scenario C format)...")

        # Map Scenario C fields to ATF form fields
        # Dados da Operação
        operacao_fields = {
            "naturezaOperacao": form_data.get("natureza_operacao", ""),
            "motivo": form_data.get("motivo", ""),
            "reparticaoFiscal": form_data.get("reparticao_fiscal", ""),
            "codMunicipio": form_data.get("codigo_municipio", ""),
            "tipoOperacao": form_data.get("tipo_operacao", ""),
            "cfop": form_data.get("cfop", ""),
        }
        logger.debug("Filling operacao fields...")
        await fill_form_fields(ctx, operacao_fields)

        # Emitente
        emitente_cnpj = form_data.get("emitente_cnpj", "")
        if emitente_cnpj:
            logger.debug(f"Filling emitente CNPJ: {emitente_cnpj}")
            await set_form_value(ctx, "cnpjEmitente", emitente_cnpj)

        # Destinatário
        destinatario_cpf = form_data.get("destinatario_cpf", "")
        if destinatario_cpf:
            logger.debug(f"Filling destinatario CPF: {destinatario_cpf}")
            await set_form_value(ctx, "cpfDestinatario", destinatario_cpf)

        # Produto
        produto_fields = {
            "ncm": form_data.get("ncm", ""),
            "descProduto": form_data.get("detalhamento_produto", ""),
            "unidade": form_data.get("unidade", ""),
            "quantidade": str(form_data.get("quantidade", "")),
            "valorUnitario": str(form_data.get("valor_unitario", "")),
        }
        logger.debug("Filling produto fields...")
        await fill_form_fields(ctx, produto_fields)

        # Tributos
        tributos_fields = {
            "aliquota": str(form_data.get("aliquota", "")),
            "cst": form_data.get("cst", ""),
            "receita": form_data.get("receita", ""),
        }
        logger.debug("Filling tributos fields...")
        await fill_form_fields(ctx, tributos_fields)

        # Click CALCULAR if configured
        if config and config.get("auto_calculate", True):
            logger.info("Clicking CALCULAR button...")
            await click_calcular(ctx)

        logger.info("NFA form (Scenario C) filled successfully")
        return True

    except Exception as e:
        logger.error(f"Error in fill_nfa_form_complete: {e}", exc_info=True)
        return False
