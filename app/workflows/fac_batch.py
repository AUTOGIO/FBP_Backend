from __future__ import annotations

from pathlib import Path

from app.adapters.files_adapter import write_artifact
from app.core.errors import ValidationError


async def run(payload: dict, *, base_dir: Path, artifacts_dir: Path) -> tuple[dict, list[str]]:
    facs = payload.get("facs")
    if not isinstance(facs, list):
        raise ValidationError("'facs' must be a list.")

    processed_results: list[dict[str, str]] = []
    for item in facs:
        if not isinstance(item, dict):
            continue
        processo = str(item.get("processo", "")).strip()
        fac = str(item.get("fac", "")).strip()
        if not processo:
            continue
        processed_results.append(
            {
                "processo": processo,
                "fac": fac or "N/A",
                "status": "processed",
            }
        )

    lines = [f"{entry['processo']} | {entry['fac']} | {entry['status']}" for entry in processed_results]
    artifact_path = write_artifact(artifacts_dir, "fac_batch", "\n".join(lines) or "No valid FAC records.")

    result = {
        "success": True,
        "total": len(facs),
        "processed": len(processed_results),
        "results": processed_results,
        "errors": [],
    }
    return result, [artifact_path]
