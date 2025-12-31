"""NFA Consult automation router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.exceptions import JobNotFoundException
from app.modules.nfa_consult import schemas
from app.modules.nfa_consult.services import (
    create_nfa_consult_job,
    get_nfa_consult_job_status,
)

router = APIRouter(prefix="/nfa/consult", tags=["nfa-consult"])


@router.post("", response_model=schemas.NFAConsultResponse)
async def create_nfa_consult(
    request: schemas.NFAConsultRequest,
) -> schemas.NFAConsultResponse:
    """Create NFA consultation job - dispatches job and returns job_id.

    Args:
        request: NFA consultation request

    Returns:
        Job creation response

    """
    try:
        payload = request.model_dump(exclude_none=True)
        result = await create_nfa_consult_job(payload)
        return schemas.NFAConsultResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create NFA consultation job: {e!s}",
        ) from e


@router.get("/status/{job_id}", response_model=schemas.NFAJobStatusResponse)
async def get_nfa_consult_status(job_id: str) -> schemas.NFAJobStatusResponse:
    """Get NFA consultation job status.

    Args:
        job_id: Job identifier

    Returns:
        Job status and result (if completed)

    """
    try:
        result = await get_nfa_consult_job_status(job_id)
        return schemas.NFAJobStatusResponse(**result)
    except JobNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {e!s}",
        ) from e
