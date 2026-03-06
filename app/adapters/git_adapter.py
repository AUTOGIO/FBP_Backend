from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(base_dir: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(base_dir),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def collect_recent_activity(base_dir: Path) -> dict[str, str | int]:
    branch = _run_git(base_dir, ["rev-parse", "--abbrev-ref", "HEAD"])
    short_status = _run_git(base_dir, ["status", "--short"])
    recent_commits = _run_git(base_dir, ["log", "-5", "--pretty=format:%h %s"])

    changed_lines = [line for line in short_status.splitlines() if line.strip()]
    return {
        "branch": branch or "unknown",
        "changed_files_count": len(changed_lines),
        "recent_commits": recent_commits or "No recent commits found.",
        "status": short_status or "Clean working tree or git unavailable.",
    }


def get_diff(base_dir: Path, git_range: str | None = None) -> str:
    if git_range:
        return _run_git(base_dir, ["diff", git_range])
    return _run_git(base_dir, ["diff"])
