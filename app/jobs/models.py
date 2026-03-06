from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

JobStatus = Literal["queued", "running", "completed", "failed"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobRecord:
    workflow: str
    input: dict[str, Any]
    status: JobStatus = "queued"
    result: dict[str, Any] | None = None
    error: str | None = None
    artifacts: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    started_at: str | None = None
    completed_at: str | None = None
    job_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobRecord":
        return cls(
            job_id=str(payload.get("job_id", str(uuid4()))),
            workflow=str(payload.get("workflow", "")),
            input=dict(payload.get("input", {})),
            status=payload.get("status", "queued"),
            result=payload.get("result"),
            error=payload.get("error"),
            artifacts=list(payload.get("artifacts", [])),
            created_at=str(payload.get("created_at", utc_now_iso())),
            started_at=payload.get("started_at"),
            completed_at=payload.get("completed_at"),
        )
