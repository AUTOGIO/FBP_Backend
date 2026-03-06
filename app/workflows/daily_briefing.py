from __future__ import annotations

from pathlib import Path

from app.adapters.files_adapter import write_artifact
from app.adapters.git_adapter import collect_recent_activity


async def run(payload: dict, *, base_dir: Path, artifacts_dir: Path) -> tuple[dict, list[str]]:
    activity = collect_recent_activity(base_dir)
    priorities = payload.get("priorities") or [
        "Review open pull requests with highest regression risk.",
        "Resolve failing checks and flaky tests.",
        "Confirm service health and deployment blockers.",
        "Prepare next feature slice and estimated effort.",
        "Document key decisions and pending dependencies.",
    ]

    report_lines = [
        "FBP Daily Briefing",
        f"Branch: {activity['branch']}",
        f"Changed files: {activity['changed_files_count']}",
        "",
        "Recent commits:",
        str(activity["recent_commits"]),
        "",
        "Status snapshot:",
        str(activity["status"]),
        "",
        "Top priorities:",
        *[f"- {item}" for item in priorities[:5]],
    ]

    artifact_path = write_artifact(artifacts_dir, "daily_briefing", "\n".join(report_lines))
    result = {
        "branch": activity["branch"],
        "changed_files_count": activity["changed_files_count"],
        "priorities": priorities[:5],
    }
    return result, [artifact_path]
