"""API Router for CAD REDESIM consulta."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.exceptions import JobNotFoundException
from app.modules.cad_redesim_consulta import schemas
from app.modules.cad_redesim_consulta.services import (
    create_cad_redesim_job,
    get_cad_redesim_job_status,
)

router = APIRouter(prefix="/cad/redesim/consulta", tags=["cad-redesim-consulta"])


@router.post("", response_model=schemas.CadRedesimConsultaResponse)
async def create_cad_redesim_consulta(
    request: schemas.CadRedesimConsultaRequest,
) -> schemas.CadRedesimConsultaResponse:
    try:
        payload = request.model_dump(exclude_none=True)
        return await create_cad_redesim_job(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create cad_redesim_consulta job: {e!s}"
        ) from e


@router.get("/status/{job_id}", response_model=schemas.CadRedesimJobStatusResponse)
async def get_cad_redesim_consulta_status(
    job_id: str,
) -> schemas.CadRedesimJobStatusResponse:
    try:
        return await get_cad_redesim_job_status(job_id)
    except JobNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch cad_redesim_consulta job: {e!s}",
        ) from e

