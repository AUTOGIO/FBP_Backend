from __future__ import annotations

from pathlib import Path

from app.adapters.files_adapter import write_artifact


async def run(payload: dict, *, base_dir: Path, artifacts_dir: Path) -> tuple[dict, list[str]]:
    data_inicio = str(payload.get("data_criacao_inicio", "")).strip()
    data_fim = str(payload.get("data_criacao_fim", "")).strip()

    summary = {
        "data_criacao_inicio": data_inicio or "not provided",
        "data_criacao_fim": data_fim or "not provided",
        "status": "simulated_completed",
    }
    artifact_text = "\n".join(f"{k}: {v}" for k, v in summary.items())
    artifact_path = write_artifact(artifacts_dir, "redesim_consulta", artifact_text)

    result = {
        "execution_id": artifact_path.split("/")[-1].replace(".txt", ""),
        "result": {"summary": artifact_path},
    }
    return result, [artifact_path]
