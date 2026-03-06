from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    jobs_dir: Path
    artifacts_dir: Path


def load_settings() -> Settings:
    base_dir = Path(__file__).resolve().parents[2]
    jobs_dir = base_dir / "storage" / "jobs"
    artifacts_dir = base_dir / "storage" / "artifacts"

    jobs_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        base_dir=base_dir,
        jobs_dir=jobs_dir,
        artifacts_dir=artifacts_dir,
    )
