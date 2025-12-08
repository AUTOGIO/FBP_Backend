"""Job tracking abstractions for background automation tasks."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from app.core.logging_config import setup_logger

logger = setup_logger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class Job:
    """Job representation."""

    def __init__(
        self,
        job_id: str,
        job_type: str,
        payload: dict[str, Any],
        timeout_seconds: int | None = None,
    ) -> None:
        self.job_id = job_id
        self.job_type = job_type
        self.payload = payload
        self.status = JobStatus.QUEUED
        self.created_at = datetime.utcnow()
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.result: dict[str, Any] | None = None
        self.error: str | None = None
        self.timeout_seconds = timeout_seconds or 3600  # Default 1 hour

    def start(self) -> None:
        """Mark job as started."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete(self, result: dict[str, Any]) -> None:
        """Mark job as completed with result."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.result = result

    def fail(self, error: str) -> None:
        """Mark job as failed with error message."""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error

    def timeout(self) -> None:
        """Mark job as timed out."""
        self.status = JobStatus.TIMEOUT
        self.completed_at = datetime.utcnow()
        self.error = "Job execution timeout"

    def is_expired(self) -> bool:
        """Check if job has exceeded timeout."""
        if self.status in [
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.TIMEOUT,
        ]:
            return False

        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return elapsed > self.timeout_seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary for API response."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat()
            if self.started_at
            else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "result": self.result,
            "error": self.error,
        }


class JobStore:
    """In-memory job store (can be extended to Redis/DB later)."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._cleanup_task: asyncio.Task | None = None

    def create_job(
        self,
        job_type: str,
        payload: dict[str, Any],
        timeout_seconds: int | None = None,
    ) -> Job:
        """Create a new job.

        Args:
            job_type: Type of job (e.g., "nfa_create", "redesim_extract")
            payload: Job payload
            timeout_seconds: Job timeout in seconds

        Returns:
            Created job

        """
        job_id = str(uuid.uuid4())
        job = Job(job_id, job_type, payload, timeout_seconds)
        self._jobs[job_id] = job
        logger.info(f"Created job {job_id} of type {job_type}")
        return job

    def get_job(self, job_id: str) -> Job | None:
        """Get job by ID."""
        return self._jobs.get(job_id)

    def update_job(self, job: Job) -> None:
        """Update job in store."""
        self._jobs[job.job_id] = job

    def list_jobs(
        self,
        job_type: str | None = None,
        status: JobStatus | None = None,
        limit: int = 100,
    ) -> list[Job]:
        """List jobs with optional filters.

        Args:
            job_type: Filter by job type
            status: Filter by status
            limit: Maximum number of jobs to return

        Returns:
            List of matching jobs

        """
        jobs = list(self._jobs.values())

        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]

        if status:
            jobs = [j for j in jobs if j.status == status]

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return jobs[:limit]

    async def cleanup_expired_jobs(self, interval_seconds: int = 300) -> None:
        """Background task to clean up expired jobs.

        Args:
            interval_seconds: Cleanup interval in seconds

        """
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                expired = [j for j in self._jobs.values() if j.is_expired()]
                for job in expired:
                    if job.status == JobStatus.RUNNING:
                        job.timeout()
                    logger.warning(f"Job {job.job_id} expired")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in cleanup task: {e}")


# Global job store instance
job_store = JobStore()
