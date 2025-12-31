"""NFA Service - Executes NFA automation using migrated modules.

⚠️ ARCHITECTURAL GUARDRAIL:
This service OWNS execution. Do NOT add orchestration logic here.
Do NOT delegate execution to external systems. Do NOT add workflow engines,
background job frameworks, or schedulers. Keep execution deterministic and resumable.
"""

from __future__ import annotations

import logging
from typing import Any

from app.modules.nfa.batch_processor import BatchNFAProcessor
from app.modules.nfa.data_validator import validate_destinatario, validate_emitente

logger = logging.getLogger(__name__)


async def test_nfa(payload: dict[str, Any]) -> dict[str, Any]:
    """Test NFA service (mock stub).

    Args:
        payload: Test payload (currently unused)

    Returns:
        Test result with success status and message

    """
    logger.info("NFA test stub executed")
    return {
        "success": True,
        "message": "NFA test stub executed successfully",
    }


async def create_nfa(
    form_data: dict[str, Any],
    config: dict[str, Any] | None = None,
    credentials: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a single NFA.

    Args:
        form_data: Form data dictionary
        config: Optional configuration

    Returns:
        Result dictionary with n8n-friendly format

    """
    try:
        # Validate emitente CNPJ
        if "emitente" in form_data:
            emitente_data = form_data.get("emitente", {})
            is_valid, errors = validate_emitente(emitente_data, 0)
            if not is_valid:
                return {
                    "success": False,
                    "data": {},
                    "errors": errors,
                }

        # Validate destinatario CPF
        if "destinatario" in form_data:
            destinatario_data = form_data.get("destinatario", {})
            is_valid, errors = validate_destinatario(destinatario_data, 0)
            if not is_valid:
                return {
                    "success": False,
                    "data": {},
                    "errors": errors,
                }

        # Use batch processor for single NFA (reuses same logic)
        logger.info("Single NFA creation - using batch processor")

        # Use credentials from request or fallback to settings
        if not credentials:
            from app.core.config import settings

            if settings.NFA_USERNAME and settings.NFA_PASSWORD:
                credentials = {
                    "usuario": settings.NFA_USERNAME,
                    "senha": settings.NFA_PASSWORD,
                }

        processor = BatchNFAProcessor(config=config or {})
        results = await processor.process_batch([form_data], credentials=credentials)

        if results["batch_summary"]["success_count"] > 0:
            first_result = results["results"][0]
            return {
                "success": True,
                "data": {
                    "nfa_id": first_result.get("nfa_number"),
                    "cpf": first_result.get("cpf"),
                    "dar_pdf": first_result.get("dar_pdf"),
                    "nota_pdf": first_result.get("nota_pdf"),
                    "status": first_result.get("status", "completed"),
                },
                "errors": [],
            }
        return {
            "success": False,
            "data": {},
            "errors": [
                (
                    results["results"][0].get("error", "Unknown error")
                    if results["results"]
                    else "No results"
                ),
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
        # If credentials not provided, fall back to backend settings/env.
        # This matches create_nfa() behavior and avoids requiring clients to send secrets.
        if not credentials:
            from app.core.config import settings

            if settings.NFA_USERNAME and settings.NFA_PASSWORD:
                credentials = {
                    "usuario": settings.NFA_USERNAME,
                    "senha": settings.NFA_PASSWORD,
                }

        processor = BatchNFAProcessor(config=config or {})
        results = await processor.process_batch(
            form_data_list,
            credentials=credentials,
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
