"""Service layer for CAD REDESIM consulta jobs."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import JobNotFoundException
from app.core.execution_runtime import execution_runtime
from app.core.execution_state import ExecutionPhase, execution_state_store
from app.core.jobs import JobStatus, job_store
from app.core.logging_config import setup_logger
from app.modules.cad_redesim_consulta.schemas import (
    DEFAULT_FIM,
    DEFAULT_INICIO,
    CadRedesimConsultaRequest,
    CadRedesimConsultaResponse,
    CadRedesimJobStatusResponse,
)
from app.modules.cad_redesim_consulta.tasks import run_cad_redesim_consulta

logger = setup_logger(__name__)


async def create_cad_redesim_job(payload: dict[str, Any]) -> CadRedesimConsultaResponse:
    """Create a new REDESIM consulta job."""
    req = CadRedesimConsultaRequest.model_validate(payload)

    data_inicio = req.data_criacao_inicio or DEFAULT_INICIO
    data_fim = req.data_criacao_fim or DEFAULT_FIM

    # Basic date sanity (length only, validation full is handled in automation)
    for value, name in (
        (data_inicio, "data_criacao_inicio"),
        (data_fim, "data_criacao_fim"),
    ):
        if value and len(value) != 10:
            raise ValueError(f"Invalid date format for {name}: expected DD/MM/AAAA")

    # Create job (metadata envelope)
    job = job_store.create_job(
        job_type="cad_redesim_consulta",
        payload={
            "data_criacao_inicio": data_inicio,
            "data_criacao_fim": data_fim,
            "wait_user_dates": req.wait_user_dates,
            "username": req.username,
            "password": req.password,
        },
        timeout_seconds=900,
    )

    # Create execution state (owns execution progress)
    execution_state = execution_state_store.create_execution(
        job_id=job.job_id, phase=ExecutionPhase.LOGIN
    )

    # Start execution in owned async context
    async def execute_fn(state: Any) -> None:
        await _execute_cad_redesim_execution(state, job.job_id)

    await execution_runtime.start_execution(execution_state, execute_fn)

    return CadRedesimConsultaResponse(
        job_id=job.job_id,
        status="queued",
        execution_id=execution_state.execution_id,
    )


async def get_cad_redesim_job_status(job_id: str) -> CadRedesimJobStatusResponse:
    """Return job status and result."""
    job = job_store.get_job(job_id)
    if not job:
        raise JobNotFoundException(job_id)
    if job.job_type != "cad_redesim_consulta":
        raise ValueError(f"Job {job_id} is not cad_redesim_consulta")

    response: dict[str, Any] = job.to_dict()
    if job.status == JobStatus.FAILED:
        response["error"] = job.error
    if job.result:
        response["result"] = job.result
    return CadRedesimJobStatusResponse.model_validate(response)


async def _execute_cad_redesim_execution(execution_state: Any, job_id: str) -> None:
    """Execute CAD REDESIM consulta execution.

    Args:
        execution_state: Execution state
        job_id: Job identifier

    """
    job = job_store.get_job(job_id)
    if not job:
        logger.error("cad_redesim_consulta: job %s not found", job_id)
        execution_state.fail(f"Job {job_id} not found")
        return

    try:
        # Update job status (metadata only)
        job.start()
        job_store.update_job(job)

        logger.info(
            f"Executing CAD REDESIM consulta execution "
            f"{execution_state.execution_id} (job_id: {job_id})"
        )

        execution_state.transition_to_phase(ExecutionPhase.FORM_FILL)
        result = await run_cad_redesim_consulta(job.payload)

        if result.get("status") == "ok":
            execution_state.transition_to_phase(ExecutionPhase.COMPLETED)
            execution_state.complete(result)
            job.complete(result)
            logger.info(
                f"CAD REDESIM consulta execution "
                f"{execution_state.execution_id} completed"
            )
        else:
            error_msg = result.get("error", "Unknown error")
            execution_state.fail(error_msg)
            job.fail(error_msg)
    except Exception as e:
        error_msg = str(e)
        logger.exception(
            f"CAD REDESIM consulta execution {execution_state.execution_id} "
            f"failed: {error_msg}"
        )
        if not execution_state.is_terminal():
            execution_state.fail(error_msg)
        if job.status == JobStatus.RUNNING:
            job.fail(error_msg)
    finally:
        job_store.update_job(job)
        execution_state_store.update_execution(execution_state)
