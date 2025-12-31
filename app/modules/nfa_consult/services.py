"""NFA Consult automation service."""

from typing import Any

from app.core.exceptions import JobNotFoundException
from app.core.execution_runtime import execution_runtime
from app.core.execution_state import ExecutionPhase, execution_state_store
from app.core.jobs import JobStatus, job_store
from app.core.logging_config import setup_logger
from app.modules.nfa_consult.tasks import run_nfa_consult_automation

logger = setup_logger(__name__)


async def create_nfa_consult_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a new NFA consultation job.

    Args:
        payload: NFA consultation payload with:
            - data_inicial: Initial date (DD/MM/YYYY)
            - data_final: Final date (DD/MM/YYYY)
            - matricula: Employee registration (optional, default: "1595504")
            - username: ATF username (optional, uses env var if not provided)
            - password: ATF password (optional, uses env var if not provided)

    Returns:
        Job creation response with job_id and status

    """
    # Validate required fields
    required_fields = ["data_inicial", "data_final"]
    missing = [f for f in required_fields if f not in payload]

    if missing:
        msg = f"Missing required fields: {missing}"
        raise ValueError(msg)

    # Validate date format (basic check)
    for date_field in ["data_inicial", "data_final"]:
        date_value = payload.get(date_field, "")
        if not date_value or len(date_value) != 10:
            msg = f"Invalid date format for {date_field}: expected DD/MM/YYYY"
            raise ValueError(msg)

    # Create job (metadata envelope)
    job = job_store.create_job(
        job_type="nfa_consult",
        payload=payload,
        timeout_seconds=600,  # 10 minutes for NFA consultation
    )

    # Create execution state (owns execution progress)
    execution_state = execution_state_store.create_execution(
        job_id=job.job_id, phase=ExecutionPhase.LOGIN
    )

    # Start execution in owned async context
    async def execute_fn(state: Any) -> None:
        await _execute_nfa_consult_execution(state, job.job_id)

    await execution_runtime.start_execution(execution_state, execute_fn)

    return {
        "job_id": job.job_id,
        "execution_id": execution_state.execution_id,
        "status": "queued",
    }


async def get_nfa_consult_job_status(job_id: str) -> dict[str, Any]:
    """Get NFA consultation job status.

    Args:
        job_id: Job identifier

    Returns:
        Job status and result (if completed)

    """
    job = job_store.get_job(job_id)

    if not job:
        raise JobNotFoundException(job_id)

    if job.job_type != "nfa_consult":
        msg = f"Job {job_id} is not an NFA consultation job"
        raise ValueError(msg)

    response = job.to_dict()

    # Extract specific fields from result if completed
    if job.status == JobStatus.COMPLETED and job.result:
        # Add NFA-specific fields to response
        response["nfa_numero"] = job.result.get("nfa_numero")
        response["danfe_path"] = job.result.get("danfe_path")
        response["dar_path"] = job.result.get("dar_path")
        response["result"] = job.result
    elif job.status == JobStatus.FAILED:
        response["error"] = job.error

    return response


async def _execute_nfa_consult_execution(execution_state: Any, job_id: str) -> None:
    """Execute NFA consultation execution.

    Args:
        execution_state: Execution state
        job_id: Job identifier

    """
    job = job_store.get_job(job_id)
    if not job:
        logger.error(f"Job {job_id} not found for execution")
        execution_state.fail(f"Job {job_id} not found")
        return

    try:
        # Update job status (metadata only)
        job.start()
        job_store.update_job(job)

        logger.info(
            f"Executing NFA consultation execution "
            f"{execution_state.execution_id} (job_id: {job_id})"
        )

        # Extract parameters from payload
        username = job.payload.get("username")
        password = job.payload.get("password")
        data_inicial = job.payload.get("data_inicial")
        data_final = job.payload.get("data_final")
        matricula = job.payload.get("matricula", "1595504")

        # Execute NFA consultation automation
        execution_state.transition_to_phase(ExecutionPhase.FORM_FILL)
        result = await run_nfa_consult_automation(
            username=username,
            password=password,
            data_inicial=data_inicial,
            data_final=data_final,
            matricula=matricula,
            headless=True,
        )

        # Check result status
        if result.get("status") == "ok":
            execution_state.transition_to_phase(ExecutionPhase.COMPLETED)
            execution_state.complete(result)
            job.complete(result)
            logger.info(
                f"NFA consultation execution {execution_state.execution_id} "
                f"completed successfully"
            )
        else:
            error_msg = result.get("error", "Unknown error during consultation")
            execution_state.fail(error_msg)
            job.fail(error_msg)
            logger.error(
                f"NFA consultation execution {execution_state.execution_id} "
                f"failed: {error_msg}"
            )

    except Exception as e:
        error_msg = str(e)
        logger.exception(
            f"NFA consultation execution {execution_state.execution_id} "
            f"failed: {error_msg}"
        )
        if not execution_state.is_terminal():
            execution_state.fail(error_msg)
        if job.status == JobStatus.RUNNING:
            job.fail(error_msg)

    finally:
        job_store.update_job(job)
        execution_state_store.update_execution(execution_state)
