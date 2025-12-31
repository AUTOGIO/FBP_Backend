"""Global FastAPI router - Unified endpoints for FBP backend execution."""

from __future__ import annotations

import platform
import re
import sys
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.browser import PLAYWRIGHT_AVAILABLE
from app.core.config import settings
from app.core.jobs import JobStatus, job_store
from app.core.logging_config import setup_logger
from app.modules.redesim.extractor import REDESIMExtractor
from app.modules.utils.cep_validator import validate_cep
from app.services.nfa_service import create_nfa

logger = setup_logger(__name__)

router = APIRouter(prefix="/global", tags=["global"])

# Track application startup time for uptime calculation
_app_start_time = time.time()


def _validate_cnpj(cnpj: str) -> bool:
    """Basic CNPJ validation (format check only).

    Args:
        cnpj: CNPJ string

    Returns:
        True if format is valid

    """
    # Remove non-numeric characters
    cnpj_clean = re.sub(r"[^\d]", "", cnpj)
    # CNPJ must have 14 digits
    return len(cnpj_clean) == 14 and cnpj_clean.isdigit()


def _validate_cpf(cpf: str) -> bool:
    """Basic CPF validation (format check only).

    Args:
        cpf: CPF string

    Returns:
        True if format is valid

    """
    # Remove non-numeric characters
    cpf_clean = re.sub(r"[^\d]", "", cpf)
    # CPF must have 11 digits
    return len(cpf_clean) == 11 and cpf_clean.isdigit()


def _get_machine_id() -> str:
    """Get machine identifier - returns exact hardware profile.

    Returns:
        Machine identifier string for iMac M3 (Mac15,5)

    """
    from app.core.config import HARDWARE_PROFILE

    try:
        # Return exact hardware profile
        return f"{HARDWARE_PROFILE['chip']} ({HARDWARE_PROFILE['model']})"
    except Exception:
        # Fallback to platform detection
        try:
            machine = platform.machine()
            processor = platform.processor()

            if "arm64" in machine.lower() or "arm" in processor.lower():
                if "M3" in processor or "M3" in platform.platform():
                    return "Apple M3"
                if "M4" in processor or "M4" in platform.platform():
                    return "Apple M4"
                return "Apple Silicon (ARM)"
            return f"{machine} ({processor})"
        except Exception:
            return "Unknown"


def _check_gmail_credentials() -> dict[str, Any]:
    """Check Gmail credentials status.

    Returns:
        Dictionary with credentials status

    """
    credentials_file = settings.GMAIL_CREDENTIALS_FILE
    token_file = settings.GMAIL_TOKEN_FILE

    credentials_exists = Path(credentials_file).exists() if credentials_file else False
    token_exists = Path(token_file).exists() if token_file else False

    return {
        "credentials_file_exists": credentials_exists,
        "token_file_exists": token_exists,
        "credentials_path": credentials_file,
        "token_path": token_file,
        "ready": credentials_exists and token_exists,
    }


class N8NResponse(BaseModel):
    """Standard n8n response format."""

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class NFATestRequest(BaseModel):
    """Minimal NFA test request."""

    emitente_cnpj: str = Field(..., description="Emitente CNPJ")
    destinatario_cpf: str = Field(..., description="Destinatario CPF")
    descricao: str = Field(..., description="Product description")
    quantidade: int = Field(..., description="Quantity", gt=0)
    preco: float = Field(..., description="Price", gt=0)


class CEPValidateRequest(BaseModel):
    """CEP validation request."""

    cep: str = Field(..., description="CEP to validate")


@router.post("/nfa/test")
async def nfa_test_endpoint(request: NFATestRequest) -> N8NResponse:
    """Test NFA creation with minimal data.

    Args:
        request: NFA test request

    Returns:
        n8n-formatted response

    """
    errors: list[str] = []
    data: dict[str, Any] = {}

    try:
        # Validate CNPJ format
        if not _validate_cnpj(request.emitente_cnpj):
            errors.append(f"Invalid CNPJ format: {request.emitente_cnpj}")
            return N8NResponse(success=False, data=data, errors=errors)

        # Validate CPF format
        if not _validate_cpf(request.destinatario_cpf):
            errors.append(f"Invalid CPF format: {request.destinatario_cpf}")
            return N8NResponse(success=False, data=data, errors=errors)

        # Prepare form data for service
        form_data = {
            "emitente": {
                "cnpj": request.emitente_cnpj,
            },
            "destinatario": {
                "documento": request.destinatario_cpf,
            },
            "produtos": [
                {
                    "descricao": request.descricao,
                    "quantidade": request.quantidade,
                    "preco": request.preco,
                },
            ],
        }

        # Call service
        result = await create_nfa(form_data)

        if result["success"]:
            data = result["data"]
            return N8NResponse(success=True, data=data, errors=[])
        errors = result.get("errors", ["Unknown error"])
        return N8NResponse(success=False, data=data, errors=errors)

    except Exception as e:
        logger.error(f"Error in NFA test: {e}", exc_info=True)
        errors.append(str(e))
        raise HTTPException(
            status_code=500,
            detail=f"NFA test failed: {e}",
        ) from e


@router.post("/redesim/test")
async def redesim_test_endpoint() -> N8NResponse:
    """Test REDESIM extraction (dummy extractor test).

    Returns:
        n8n-formatted response

    """
    errors: list[str] = []
    data: dict[str, Any] = {}

    try:
        extractor = REDESIMExtractor()
        results = await extractor.extract_data()

        data = {
            "extracted_count": len(results),
            "results": results[:5],  # Limit to first 5 for response
        }

        return N8NResponse(success=True, data=data, errors=[])

    except Exception as e:
        logger.error(f"Error in REDESIM test: {e}", exc_info=True)
        errors.append(str(e))
        raise HTTPException(
            status_code=500,
            detail=f"REDESIM test failed: {e}",
        ) from e


@router.post("/cep/validate")
async def cep_validate_endpoint(request: CEPValidateRequest) -> N8NResponse:
    """Validate CEP using utils validator.

    Args:
        request: CEP validation request

    Returns:
        n8n-formatted response

    """
    errors: list[str] = []
    data: dict[str, Any] = {}

    try:
        cep_data = validate_cep(request.cep)

        if cep_data.valid:
            data = {
                "cep": cep_data.cep,
                "logradouro": cep_data.logradouro,
                "bairro": cep_data.bairro,
                "cidade": cep_data.cidade,
                "uf": cep_data.uf,
                "ibge": cep_data.ibge,
                "source": cep_data.source,
            }
            return N8NResponse(success=True, data=data, errors=[])
        errors.append(cep_data.error or "Invalid CEP")
        return N8NResponse(success=False, data=data, errors=errors)

    except Exception as e:
        logger.error(f"Error in CEP validation: {e}", exc_info=True)
        errors.append(str(e))
        raise HTTPException(
            status_code=500,
            detail=f"CEP validation failed: {e}",
        ) from e


@router.get("/health")
async def global_health_endpoint() -> dict[str, Any]:
    """Full backend health status.

    Returns:
        Complete health status with uptime, jobs, Playwright, Gmail, etc.

    """
    try:
        # Calculate uptime
        uptime_seconds = int(time.time() - _app_start_time)
        uptime_hours = uptime_seconds // 3600
        uptime_minutes = (uptime_seconds % 3600) // 60
        uptime_str = f"{uptime_hours}h {uptime_minutes}m"

        # Count NFA jobs running
        nfa_jobs = job_store.list_jobs(job_type="nfa_create", status=JobStatus.RUNNING)
        nfa_jobs_count = len(nfa_jobs)

        # Check Playwright status
        playwright_status = {
            "available": PLAYWRIGHT_AVAILABLE,
            "status": "ready" if PLAYWRIGHT_AVAILABLE else "not_installed",
        }

        # Check Gmail credentials
        gmail_status = _check_gmail_credentials()

        # Get Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # Get machine ID
        machine_id = _get_machine_id()

        return {
            "status": "ok",
            "uptime_seconds": uptime_seconds,
            "uptime": uptime_str,
            "nfa_jobs_running": nfa_jobs_count,
            "playwright": playwright_status,
            "gmail": gmail_status,
            "python_version": python_version,
            "machine_id": machine_id,
            "project": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION,
        }

    except Exception as e:
        logger.error(f"Error in global health check: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {e}",
        ) from e
