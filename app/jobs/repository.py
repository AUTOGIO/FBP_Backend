from __future__ import annotations

import json
from pathlib import Path

from app.jobs.models import JobRecord


class JobRepository:
    def __init__(self, jobs_dir: Path) -> None:
        self._jobs_dir = jobs_dir

    def _job_file(self, job_id: str) -> Path:
        return self._jobs_dir / f"{job_id}.json"

    def save(self, job: JobRecord) -> None:
        path = self._job_file(job.job_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(job.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
        tmp.replace(path)

    def get(self, job_id: str) -> JobRecord | None:
        path = self._job_file(job_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return JobRecord.from_dict(payload)

    def list_all(self) -> list[JobRecord]:
        jobs: list[JobRecord] = []
        for path in sorted(self._jobs_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            jobs.append(JobRecord.from_dict(payload))
        return jobs
