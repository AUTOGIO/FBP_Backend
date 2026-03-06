from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def resolve_path(base_dir: Path, maybe_path: str) -> Path:
    candidate = Path(maybe_path)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def read_text_file(base_dir: Path, file_path: str) -> str:
    resolved = resolve_path(base_dir, file_path)
    return resolved.read_text(encoding="utf-8")


def write_artifact(artifacts_dir: Path, prefix: str, content: str, suffix: str = "txt") -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{prefix}_{timestamp}.{suffix}"
    target = artifacts_dir / filename
    target.write_text(content, encoding="utf-8")
    return str(target)
