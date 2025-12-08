"""NFA real automation router."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.exceptions import JobNotFoundException
from app.services import nfa_real_service

router = APIRouter(prefix="/nfa", tags=["nfa-real"])


class NFACreateRequest(BaseModel):
    """NFA creation request model."""

    emitente: dict = Field(..., description="Emitente information")
    destinatario: dict = Field(..., description="Destinatário information")
    # Add other NFA fields as needed
    # items: Optional[list] = None
    # observacoes: Optional[str] = None


class NFACreateResponse(BaseModel):
    """NFA creation response model."""

    job_id: str
    status: str


class NFAJobStatusResponse(BaseModel):
    """NFA job status response model."""

    job_id: str
    job_type: str
    status: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result: dict | None = None
    error: str | None = None


@router.post("/create")
async def create_nfa(request: NFACreateRequest) -> NFACreateResponse:
    """Create NFA - dispatches job and returns job_id.

    Args:
        request: NFA creation request

    Returns:
        Job creation response

    """
    try:
        payload = request.model_dump()
        result = await nfa_real_service.create_nfa_job(payload)
        return NFACreateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create NFA job: {e!s}",
        ) from e


@router.get("/status/{job_id}")
async def get_nfa_status(job_id: str) -> NFAJobStatusResponse:
    """Get NFA job status.

    Args:
        job_id: Job identifier

    Returns:
        Job status and result (if completed)

    """
    try:
        result = await nfa_real_service.get_nfa_job_status(job_id)
        return NFAJobStatusResponse(**result)
    except JobNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get job status: {e!s}",
        ) from e
