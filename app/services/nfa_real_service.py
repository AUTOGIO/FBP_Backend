"""NFA real automation service."""

import asyncio
from typing import Any

from app.core.clients import get_nfa_client
from app.core.exceptions import AutomationException, JobNotFoundException
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

    # Create job
    job = job_store.create_job(
        job_type="nfa_create",
        payload=payload,
        timeout_seconds=600,  # 10 minutes for NFA creation
    )

    # Dispatch job to background task
    asyncio.create_task(_execute_nfa_job(job.job_id))

    return {"job_id": job.job_id, "status": "queued"}


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


async def _execute_nfa_job(job_id: str) -> None:
    """Execute NFA creation job in background.

    Args:
        job_id: Job identifier

    """
    job = job_store.get_job(job_id)
    if not job:
        logger.error(f"Job {job_id} not found for execution")
        return

    try:
        job.start()
        job_store.update_job(job)

        logger.info(f"Executing NFA job {job_id}")

        # Get automation client
        client = get_nfa_client()

        try:
            # Execute NFA creation
            if hasattr(client, "create_nfa"):
                result = await client.create_nfa(job.payload)
            else:
                # Fallback to generic execute
                result = await client.execute(job.payload)

            job.complete(result)
            logger.info(f"NFA job {job_id} completed successfully")

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"NFA job {job_id} failed: {error_msg}")
            job.fail(error_msg)
            msg = f"NFA creation failed: {error_msg}"
            raise AutomationException(msg) from e

        finally:
            # Close HTTP client if applicable
            if hasattr(client, "close"):
                await client.close()

    except Exception as e:
        if job.status == JobStatus.RUNNING:
            job.fail(str(e))
        logger.exception(f"Unexpected error in NFA job {job_id}: {e}")

    finally:
        job_store.update_job(job)
