"""n8n-compatible utility endpoints.
All responses follow n8n-friendly format: {success, data, errors}.
"""

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.modules.utils.cep_validator import CEPValidator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/utils", tags=["n8n", "utils"])


class N8NResponse(BaseModel):
    """Standard n8n response format."""

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class CEPValidationRequest(BaseModel):
    """CEP validation request."""

    cep: str = Field(..., description="CEP to validate")
    enrich: bool = Field(
        False, description="Whether to enrich with additional data",
    )


class CEPBatchValidationRequest(BaseModel):
    """Batch CEP validation request."""

    ceps: list[str] = Field(..., description="List of CEPs to validate")


@router.post("/cep")
async def validate_cep(request: CEPValidationRequest) -> N8NResponse:
    """Validate CEP (Brazilian postal code).

    n8n-compatible endpoint for CEP validation.
    """
    errors: list[str] = []
    data: dict[str, Any] = {}

    try:
        validator = CEPValidator()
        cep_data = validator.validate_cep(request.cep)

        if cep_data.valid:
            data = {
                "cep": cep_data.cep,
                "valid": True,
                "logradouro": cep_data.logradouro,
                "bairro": cep_data.bairro,
                "cidade": cep_data.cidade,
                "uf": cep_data.uf,
                "ibge": cep_data.ibge,
                "source": cep_data.source,
            }

            if request.enrich and cep_data.lat and cep_data.lng:
                data["coordinates"] = {
                    "latitude": cep_data.lat,
                    "longitude": cep_data.lng,
                }

            return N8NResponse(success=True, data=data, errors=errors)
        errors.append(cep_data.error or "Invalid CEP")
        data = {
            "cep": cep_data.cep,
            "valid": False,
        }
        return N8NResponse(success=False, data=data, errors=errors)

    except Exception as e:
        logger.error(f"Error validating CEP: {e}", exc_info=True)
        errors.append(str(e))
        return N8NResponse(success=False, data=data, errors=errors)


@router.post("/cep/batch")
async def validate_cep_batch(
    request: CEPBatchValidationRequest,
) -> N8NResponse:
    """Validate multiple CEPs in batch.

    n8n-compatible endpoint for batch CEP validation.
    """
    errors: list[str] = []
    data: dict[str, Any] = {}

    try:
        validator = CEPValidator()
        results = validator.batch_validate(request.ceps)

        validated = {}
        for cep, cep_data in results.items():
            validated[cep] = {
                "valid": cep_data.valid,
                "logradouro": cep_data.logradouro,
                "cidade": cep_data.cidade,
                "uf": cep_data.uf,
                "error": cep_data.error,
            }

        data = {
            "total": len(request.ceps),
            "validated": validated,
            "valid_count": sum(1 for r in results.values() if r.valid),
            "invalid_count": sum(1 for r in results.values() if not r.valid),
        }

        return N8NResponse(success=True, data=data, errors=errors)

    except Exception as e:
        logger.error(f"Error in batch CEP validation: {e}", exc_info=True)
        errors.append(str(e))
        return N8NResponse(success=False, data=data, errors=errors)
