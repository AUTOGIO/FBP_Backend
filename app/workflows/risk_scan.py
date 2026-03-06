from __future__ import annotations

from pathlib import Path

from app.adapters.files_adapter import write_artifact
from app.adapters.git_adapter import get_diff


async def run(payload: dict, *, base_dir: Path, artifacts_dir: Path) -> tuple[dict, list[str]]:
    diff_text = str(payload.get("diff", "")).strip()
    git_range = payload.get("git_range")

    if not diff_text:
        diff_text = get_diff(base_dir, str(git_range) if git_range else None)

    added = sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---"))
    touched = added + removed

    if touched >= 600:
        level = "high"
    elif touched >= 200:
        level = "medium"
    else:
        level = "low"

    notes = [
        f"Risk level: {level}",
        f"Lines added: {added}",
        f"Lines removed: {removed}",
        "Review integration paths and regression tests for high-volume changes.",
    ]
    artifact_path = write_artifact(artifacts_dir, "risk_scan", "\n".join(notes))

    result = {
        "risk_level": level,
        "lines_added": added,
        "lines_removed": removed,
        "lines_touched": touched,
    }
    return result, [artifact_path]
