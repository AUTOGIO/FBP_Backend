"""REDESIM automation service."""

from typing import Any

from app.core.clients import get_redesim_client
from app.core.exceptions import AutomationException, JobNotFoundException
from app.core.execution_runtime import execution_runtime
from app.core.execution_state import ExecutionPhase, execution_state_store
from app.core.jobs import JobStatus, job_store
from app.core.logging_config import setup_logger

logger = setup_logger(__name__)


async def create_redesim_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a new REDESIM email extraction job.

    Args:
        payload: Email extraction payload (CNPJ, filters, mailbox spec, etc.)

    Returns:
        Job creation response with job_id and status

    """
    # Validate required fields (basic validation - extend as needed)
    # Adjust based on actual REDESIM requirements
    if "cnpj" not in payload and "filters" not in payload:
        msg = (
            "Missing required fields: at least 'cnpj' or 'filters' " "must be provided"
        )
        raise ValueError(msg)

    # Create job (metadata envelope)
    job = job_store.create_job(
        job_type="redesim_extract",
        payload=payload,
        timeout_seconds=300,  # 5 minutes for email extraction
    )

    # Create execution state (owns execution progress)
    execution_state = execution_state_store.create_execution(
        job_id=job.job_id, phase=ExecutionPhase.LOGIN
    )

    # Start execution in owned async context
    async def execute_fn(state: Any) -> None:
        await _execute_redesim_execution(state, job.job_id)

    await execution_runtime.start_execution(execution_state, execute_fn)

    return {
        "job_id": job.job_id,
        "execution_id": execution_state.execution_id,
        "status": "queued",
    }


async def get_redesim_job_status(job_id: str) -> dict[str, Any]:
    """Get REDESIM job status.

    Args:
        job_id: Job identifier

    Returns:
        Job status and result (if completed)

    """
    job = job_store.get_job(job_id)

    if not job:
        raise JobNotFoundException(job_id)

    if job.job_type != "redesim_extract":
        msg = f"Job {job_id} is not a REDESIM job"
        raise ValueError(msg)

    response = job.to_dict()

    # Only include result if completed
    if job.status == JobStatus.COMPLETED:
        response["result"] = job.result
    elif job.status == JobStatus.FAILED:
        response["error"] = job.error

    return response


async def _execute_redesim_execution(execution_state: Any, job_id: str) -> None:
    """Execute REDESIM email extraction execution.

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
            f"Executing REDESIM execution {execution_state.execution_id} "
            f"(job_id: {job_id})"
        )

        # Get automation client
        client = get_redesim_client()

        try:
            # Execute email extraction
            execution_state.transition_to_phase(ExecutionPhase.FORM_FILL)

            if hasattr(client, "extract_emails"):
                result = await client.extract_emails(job.payload)
            else:
                # Fallback to generic execute
                result = await client.execute(job.payload)

            execution_state.transition_to_phase(ExecutionPhase.COMPLETED)
            execution_state.complete(result)

            # Update job (metadata only)
            job.complete(result)
            logger.info(
                f"REDESIM execution {execution_state.execution_id} "
                f"completed successfully"
            )

        except Exception as e:
            error_msg = str(e)
            logger.exception(
                f"REDESIM execution {execution_state.execution_id} "
                f"failed: {error_msg}"
            )
            execution_state.fail(error_msg)
            job.fail(error_msg)
            msg = f"REDESIM extraction failed: {error_msg}"
            raise AutomationException(msg) from e

        finally:
            # Close HTTP client if applicable
            if hasattr(client, "close"):
                await client.close()

    except Exception as e:
        error_msg = str(e)
        if not execution_state.is_terminal():
            execution_state.fail(error_msg)
        if job.status == JobStatus.RUNNING:
            job.fail(error_msg)
        logger.exception(
            f"Unexpected error in REDESIM execution "
            f"{execution_state.execution_id}: {e}"
        )

    finally:
        job_store.update_job(job)
        execution_state_store.update_execution(execution_state)
