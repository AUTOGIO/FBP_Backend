"""NFA real automation service."""

from typing import Any

from app.core.clients import get_nfa_client
from app.core.exceptions import AutomationException, JobNotFoundException
from app.core.execution_runtime import execution_runtime
from app.core.execution_state import ExecutionPhase, execution_state_store
from app.core.jobs import JobStatus, job_store
from app.core.logging_config import setup_logger

logger = setup_logger(__name__)


async def create_nfa_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a new NFA creation job.

    Args:
        payload: NFA creation payload with emitente, destinatario, etc.

    Returns:
        Job creation response with job_id and status

    """
    # Validate required fields (basic validation - extend as needed)
    required_fields = ["emitente", "destinatario"]
    missing = [f for f in required_fields if f not in payload]

    if missing:
        msg = f"Missing required fields: {missing}"
        raise ValueError(msg)

    # Create job (metadata envelope)
    job = job_store.create_job(
        job_type="nfa_create",
        payload=payload,
        timeout_seconds=600,  # 10 minutes for NFA creation
    )

    # Create execution state (owns execution progress)
    execution_state = execution_state_store.create_execution(
        job_id=job.job_id, phase=ExecutionPhase.LOGIN
    )

    # Start execution in owned async context
    async def execute_fn(state: Any) -> None:
        await _execute_nfa_execution(state, job.job_id)

    await execution_runtime.start_execution(execution_state, execute_fn)

    return {
        "job_id": job.job_id,
        "execution_id": execution_state.execution_id,
        "status": "queued",
    }


async def get_nfa_job_status(job_id: str) -> dict[str, Any]:
    """Get NFA job status.

    Args:
        job_id: Job identifier

    Returns:
        Job status and result (if completed)

    """
    job = job_store.get_job(job_id)

    if not job:
        raise JobNotFoundException(job_id)

    if job.job_type != "nfa_create":
        msg = f"Job {job_id} is not an NFA job"
        raise ValueError(msg)

    response = job.to_dict()

    # Only include result if completed
    if job.status == JobStatus.COMPLETED:
        response["result"] = job.result
    elif job.status == JobStatus.FAILED:
        response["error"] = job.error

    return response


async def _execute_nfa_execution(execution_state: Any, job_id: str) -> None:
    """Execute NFA creation execution.

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
            f"Executing NFA execution {execution_state.execution_id} "
            f"(job_id: {job_id})"
        )

        # Get automation client
        client = get_nfa_client()

        try:
            # Execute NFA creation
            execution_state.transition_to_phase(ExecutionPhase.FORM_FILL)

            if hasattr(client, "create_nfa"):
                result = await client.create_nfa(job.payload)
            else:
                # Fallback to generic execute
                result = await client.execute(job.payload)

            execution_state.transition_to_phase(ExecutionPhase.COMPLETED)
            execution_state.complete(result)

            # Update job (metadata only)
            job.complete(result)
            logger.info(
                f"NFA execution {execution_state.execution_id} "
                f"completed successfully"
            )

        except Exception as e:
            error_msg = str(e)
            logger.exception(
                f"NFA execution {execution_state.execution_id} " f"failed: {error_msg}"
            )
            execution_state.fail(error_msg)
            job.fail(error_msg)
            msg = f"NFA creation failed: {error_msg}"
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
            f"Unexpected error in NFA execution " f"{execution_state.execution_id}: {e}"
        )

    finally:
        job_store.update_job(job)
        execution_state_store.update_execution(execution_state)
