from __future__ import annotations

from pathlib import Path

from app.adapters.files_adapter import read_text_file, write_artifact
from app.adapters.llm_adapter import summarize_text
from app.core.errors import ValidationError


async def run(payload: dict, *, base_dir: Path, artifacts_dir: Path) -> tuple[dict, list[str]]:
    raw_text = str(payload.get("text", "")).strip()
    file_path = payload.get("file_path")

    if not raw_text and not file_path:
        raise ValidationError("Provide either 'text' or 'file_path'.")

    content = raw_text if raw_text else read_text_file(base_dir, str(file_path))
    bullets = summarize_text(content)

    artifact_text = "\n".join(f"- {item}" for item in bullets)
    artifact_path = write_artifact(artifacts_dir, "doc_summarize", artifact_text)

    result = {
        "summary_points": bullets,
        "source_length": len(content),
    }
    return result, [artifact_path]
