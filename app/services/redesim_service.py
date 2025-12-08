"""REDESIM automation service."""

import asyncio
from typing import Any

from app.core.clients import get_redesim_client
from app.core.exceptions import AutomationException, JobNotFoundException
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
        msg = "Missing required fields: at least 'cnpj' or 'filters' must be provided"
        raise ValueError(
            msg,
        )

    # Create job
    job = job_store.create_job(
        job_type="redesim_extract",
        payload=payload,
        timeout_seconds=300,  # 5 minutes for email extraction
    )

    # Dispatch job to background task
    asyncio.create_task(_execute_redesim_job(job.job_id))

    return {"job_id": job.job_id, "status": "queued"}


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


async def _execute_redesim_job(job_id: str) -> None:
    """Execute REDESIM email extraction job in background.

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

        logger.info(f"Executing REDESIM job {job_id}")

        # Get automation client
        client = get_redesim_client()

        try:
            # Execute email extraction
            if hasattr(client, "extract_emails"):
                result = await client.extract_emails(job.payload)
            else:
                # Fallback to generic execute
                result = await client.execute(job.payload)

            job.complete(result)
            logger.info(f"REDESIM job {job_id} completed successfully")

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"REDESIM job {job_id} failed: {error_msg}")
            job.fail(error_msg)
            msg = f"REDESIM extraction failed: {error_msg}"
            raise AutomationException(
                msg,
            ) from e

        finally:
            # Close HTTP client if applicable
            if hasattr(client, "close"):
                await client.close()

    except Exception as e:
        if job.status == JobStatus.RUNNING:
            job.fail(str(e))
        logger.exception(f"Unexpected error in REDESIM job {job_id}: {e}")

    finally:
        job_store.update_job(job)
