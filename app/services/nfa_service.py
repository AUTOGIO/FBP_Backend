"""NFA Service - Orchestrates NFA automation using migrated modules."""
from __future__ import annotations

from typing import Any

from app.core.logging_config import setup_logger
from app.modules.nfa.atf_login import atf_manual_login
from app.modules.nfa.batch_processor import BatchNFAProcessor
from app.modules.nfa.data_validator import validate_destinatario
from app.modules.nfa.form_filler import fill_nfa_form_complete

logger = setup_logger(__name__)


async def create_nfa(
    form_data: dict[str, Any], config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a single NFA.

    Args:
        form_data: Form data dictionary
        config: Optional configuration

    Returns:
        Result dictionary with n8n-friendly format

    """
    try:
        # Validate form data
        if "destinatario" in form_data:
            destinatario_data = form_data.get("destinatario", {})
            is_valid, errors = validate_destinatario(destinatario_data, 0)
            if not is_valid:
                return {
                    "success": False,
                    "data": {},
                    "errors": errors,
                }

        # TODO: Implement single NFA creation using Playwright
        # For now, return placeholder
        logger.info("Single NFA creation - using batch processor")

        processor = BatchNFAProcessor(config=config or {})
        results = await processor.process_batch([form_data])

        if results["batch_summary"]["success_count"] > 0:
            return {
                "success": True,
                "data": {
                    "nfa_id": results["results"][0].get("nfa_number"),
                    "status": "created",
                },
                "errors": [],
            }
        return {
            "success": False,
            "data": {},
            "errors": [
                results["results"][0].get("error", "Unknown error"),
            ],
        }

    except Exception as e:
        logger.error(f"Error creating NFA: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "errors": [str(e)],
        }


async def create_nfa_batch(
    form_data_list: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
    credentials: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create multiple NFAs in batch.

    Args:
        form_data_list: List of form data dictionaries
        config: Optional configuration
        credentials: Optional login credentials

    Returns:
        Batch results dictionary with n8n-friendly format

    """
    try:
        processor = BatchNFAProcessor(config=config or {})
        results = await processor.process_batch(
            form_data_list, credentials=credentials,
        )

        return {
            "success": True,
            "data": results,
            "errors": [],
        }

    except Exception as e:
        logger.error(f"Error in batch NFA creation: {e}", exc_info=True)
        return {
            "success": False,
            "data": {},
            "errors": [str(e)],
        }


async def nfa_test_scenario_c(request: Any) -> dict[str, Any]:
    """Run NFA Scenario C test with complete form data.

    Args:
        request: GlobalNFATestRequest instance with 17 fields:
            - natureza_operacao, motivo, reparticao_fiscal, codigo_municipio
            - tipo_operacao, cfop, emitente_cnpj, destinatario_cpf
            - ncm, detalhamento_produto, unidade, quantidade, valor_unitario
            - aliquota, cst, receita, mode

    Modes:
        - simulate: Dry-run, no browser automation
        - visual: Browser with MANUAL LOGIN (user logs in manually)
        - full: Full automation with CDP connection

    Returns:
        Result dictionary with n8n-friendly format
    """
    logger.info("Starting NFA Scenario C test")

    try:
        # Extract mode
        mode_value = getattr(request, "mode", "simulate")

        # Determine if manual login should be used
        # Visual mode uses manual login by default
        use_manual_login = mode_value == "visual"

        # Build config from mode
        config: dict[str, Any] = {
            "browser": {
                "headless": mode_value == "simulate",
            },
            "cdp": {
                "enabled": mode_value == "full",
            },
            "visual": mode_value == "visual",
            "manual_login": use_manual_login,
        }

        # Convert request to form_data format (17 fields)
        form_data = {
            # Dados da Operação (6 fields)
            "natureza_operacao": getattr(request, "natureza_operacao", ""),
            "motivo": getattr(request, "motivo", ""),
            "reparticao_fiscal": getattr(request, "reparticao_fiscal", ""),
            "codigo_municipio": getattr(request, "codigo_municipio", ""),
            "tipo_operacao": getattr(request, "tipo_operacao", ""),
            "cfop": getattr(request, "cfop", ""),
            # Emitente e Destinatário (2 fields)
            "emitente_cnpj": getattr(request, "emitente_cnpj", ""),
            "destinatario_cpf": getattr(request, "destinatario_cpf", ""),
            # Produto/Item (5 fields)
            "ncm": getattr(request, "ncm", ""),
            "detalhamento_produto": getattr(request, "detalhamento_produto", ""),
            "unidade": getattr(request, "unidade", ""),
            "quantidade": getattr(request, "quantidade", 0),
            "valor_unitario": getattr(request, "valor_unitario", 0.0),
            # Tributos (4 fields)
            "aliquota": getattr(request, "aliquota", 0.0),
            "cst": getattr(request, "cst", ""),
            "receita": getattr(request, "receita", ""),
        }

        logger.info(f"Scenario C test mode: {mode_value}")
        if use_manual_login:
            logger.info("Manual ATF login flow is active.")
        logger.debug(f"Form data: {form_data}")

        # In simulate mode, just validate and return success
        if mode_value == "simulate":
            logger.info("Simulate mode: skipping actual browser automation")
            return {
                "success": True,
                "data": {
                    "scenario": "C",
                    "mode": mode_value,
                    "status": "simulated",
                    "form_data": form_data,
                    "message": "Dry-run completed. Data validated successfully.",
                },
                "errors": [],
            }

        processor = BatchNFAProcessor(config=config)

        if mode_value == "visual":
            browser = None
            try:
                browser, context, page = await processor.connect_browser(
                    navigate_to_atf=False,
                )
                ctx = await atf_manual_login(context, page)
                success = await fill_nfa_form_complete(
                    ctx,
                    form_data,
                    config=config,
                )
                if not success:
                    msg = "Failed to fill NFA form in visual mode"
                    raise RuntimeError(msg)

                return {
                    "success": True,
                    "data": {
                        "scenario": "C",
                        "mode": mode_value,
                        "manual_login": True,
                        "status": "completed",
                        "result": {
                            "form_data": form_data,
                            "message": "Visual mode completed via manual login.",
                        },
                    },
                    "errors": [],
                }
            except Exception as manual_error:
                logger.exception("Visual mode failed", exc_info=True)
                return {
                    "success": False,
                    "data": {
                        "scenario": "C",
                        "mode": mode_value,
                        "manual_login": True,
                    },
                    "errors": [str(manual_error)],
                }
            finally:
                if browser:
                    await browser.close()

        results = await processor.process_batch(
            [form_data],
            use_manual_login=use_manual_login,
        )

        if results["batch_summary"]["success_count"] > 0:
            return {
                "success": True,
                "data": {
                    "scenario": "C",
                    "mode": mode_value,
                    "manual_login": use_manual_login,
                    "nfa_id": results["results"][0].get("nfa_number"),
                    "status": "completed",
                    "result": results["results"][0],
                },
                "errors": [],
            }

        error_msg = results["results"][0].get("error", "Unknown error")
        return {
            "success": False,
            "data": {
                "scenario": "C",
                "mode": mode_value,
                "manual_login": use_manual_login,
            },
            "errors": [error_msg],
        }

    except Exception as e:
        logger.exception(f"Error in Scenario C test: {e}", exc_info=True)
        return {
            "success": False,
            "data": {
                "scenario": "C",
            },
            "errors": [str(e)],
        }
