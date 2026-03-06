from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from app.jobs.models import JobRecord, utc_now_iso
from app.jobs.repository import JobRepository


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository
        self.queue: asyncio.Queue[str] = asyncio.Queue()

    def create_job(self, workflow: str, payload: dict[str, Any]) -> JobRecord:
        job = JobRecord(workflow=workflow, input=payload)
        self.repository.save(job)
        self.queue.put_nowait(job.job_id)
        return job

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.repository.get(job_id)

    def mark_running(self, job: JobRecord) -> JobRecord:
        job.status = "running"
        job.started_at = utc_now_iso()
        self.repository.save(job)
        return job

    def mark_completed(self, job: JobRecord, result: dict[str, Any], artifacts: list[str]) -> JobRecord:
        job.status = "completed"
        job.result = result
        job.artifacts = artifacts
        job.completed_at = utc_now_iso()
        self.repository.save(job)
        return job

    def mark_failed(self, job: JobRecord, error: str) -> JobRecord:
        job.status = "failed"
        job.error = error
        job.completed_at = utc_now_iso()
        self.repository.save(job)
        return job

    def metrics(self) -> dict[str, Any]:
        jobs = self.repository.list_all()
        counts = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
        durations: list[float] = []

        for job in jobs:
            counts[job.status] = counts.get(job.status, 0) + 1
            if job.started_at and job.completed_at:
                started = datetime.fromisoformat(job.started_at)
                completed = datetime.fromisoformat(job.completed_at)
                durations.append((completed - started).total_seconds())

        avg_duration = sum(durations) / len(durations) if durations else 0.0
        return {
            "jobs_total": len(jobs),
            "jobs_queued": counts["queued"],
            "jobs_running": counts["running"],
            "jobs_completed": counts["completed"],
            "jobs_failed": counts["failed"],
            "avg_duration_seconds": round(avg_duration, 3),
        }
