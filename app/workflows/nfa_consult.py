from __future__ import annotations

from pathlib import Path

from app.adapters.files_adapter import write_artifact
from app.core.errors import ValidationError


async def run(payload: dict, *, base_dir: Path, artifacts_dir: Path) -> tuple[dict, list[str]]:
    data_inicial = str(payload.get("data_inicial", "")).strip()
    data_final = str(payload.get("data_final", "")).strip()
    matricula = str(payload.get("matricula", "")).strip() or "1595504"

    if not data_inicial or not data_final:
        raise ValidationError("'data_inicial' and 'data_final' are required.")

    nfa_numero = f"SIM-{data_inicial.replace('/', '')}-{data_final.replace('/', '')}"
    artifact_text = (
        f"NFA consultation simulated\n"
        f"period: {data_inicial} to {data_final}\n"
        f"matricula: {matricula}\n"
        f"nfa_numero: {nfa_numero}\n"
    )
    artifact_path = write_artifact(artifacts_dir, "nfa_consult", artifact_text)

    result = {
        "nfa_numero": nfa_numero,
        "danfe_path": artifact_path,
        "dar_path": artifact_path,
        "result": {
            "data_inicial": data_inicial,
            "data_final": data_final,
            "matricula": matricula,
        },
    }
    return result, [artifact_path]
