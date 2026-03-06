from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from app.jobs.service import JobService

WorkflowHandler = Callable[[dict], Awaitable[tuple[dict, list[str]]]]
logger = logging.getLogger(__name__)


class JobWorker:
    def __init__(self, service: JobService, handlers: dict[str, WorkflowHandler]) -> None:
        self._service = service
        self._handlers = handlers
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())

    async def _run_loop(self) -> None:
        while True:
            job_id = await self._service.queue.get()
            job = self._service.get_job(job_id)
            if job is None:
                self._service.queue.task_done()
                continue

            handler = self._handlers.get(job.workflow)
            if handler is None:
                self._service.mark_failed(job, f"Unknown workflow: {job.workflow}")
                self._service.queue.task_done()
                continue

            self._service.mark_running(job)
            try:
                result, artifacts = await handler(job.input)
                self._service.mark_completed(job, result=result, artifacts=artifacts)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.exception("Job %s failed", job_id)
                self._service.mark_failed(job, str(exc))
            finally:
                self._service.queue.task_done()
