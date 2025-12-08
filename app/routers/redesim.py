"""REDESIM automation router."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.exceptions import JobNotFoundException
from app.services import redesim_service

router = APIRouter(prefix="/redesim", tags=["redesim"])


class REDESIMExtractRequest(BaseModel):
    """REDESIM email extraction request model."""

    cnpj: str | None = Field(None, description="CNPJ to filter emails")
    filters: dict | None = Field(None, description="Email filters")
    mailbox: str | None = Field(None, description="Mailbox specification")
    # Add other REDESIM fields as needed


class REDESIMExtractResponse(BaseModel):
    """REDESIM extraction response model."""

    job_id: str
    status: str


class REDESIMJobStatusResponse(BaseModel):
    """REDESIM job status response model."""

    job_id: str
    job_type: str
    status: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result: dict | None = None
    error: str | None = None


@router.post("/email-extract")
async def extract_emails(
    request: REDESIMExtractRequest,
) -> REDESIMExtractResponse:
    """Extract REDESIM emails - dispatches job and returns job_id.

    Args:
        request: Email extraction request

    Returns:
        Job creation response

    """
    try:
        payload = request.model_dump(exclude_none=True)
        result = await redesim_service.create_redesim_job(payload)
        return REDESIMExtractResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create REDESIM job: {e!s}",
        ) from e


@router.get("/status/{job_id}")
async def get_redesim_status(job_id: str) -> REDESIMJobStatusResponse:
    """Get REDESIM job status.

    Args:
        job_id: Job identifier

    Returns:
        Job status and result (if completed)

    """
    try:
        result = await redesim_service.get_redesim_job_status(job_id)
        return REDESIMJobStatusResponse(**result)
    except JobNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get job status: {e!s}",
        ) from e
