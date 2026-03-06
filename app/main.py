from __future__ import annotations

import json
import logging
import re
import socket
import subprocess
from pathlib import Path
from typing import Any

from app.api.health import health_payload
from app.core.config import Settings, load_settings
from app.core.errors import ValidationError
from app.core.logging import configure_logging
from app.jobs.repository import JobRepository
from app.jobs.service import JobService
from app.jobs.worker import JobWorker, WorkflowHandler
from app.workflows import (
    daily_briefing,
    doc_summarize,
    fac_batch,
    nfa_consult,
    redesim_consulta,
    risk_scan,
)

configure_logging()
logger = logging.getLogger(__name__)


class AppState:
    def __init__(self) -> None:
        self.settings: Settings = load_settings()
        self.service = JobService(JobRepository(self.settings.jobs_dir))
        self.handlers: dict[str, WorkflowHandler] = self._build_handlers()
        self.worker = JobWorker(self.service, self.handlers)
        self._started = False

    def _build_handlers(self) -> dict[str, WorkflowHandler]:
        return {
            "daily-briefing": lambda payload: daily_briefing.run(
                payload,
                base_dir=self.settings.base_dir,
                artifacts_dir=self.settings.artifacts_dir,
            ),
            "doc-summarize": lambda payload: doc_summarize.run(
                payload,
                base_dir=self.settings.base_dir,
                artifacts_dir=self.settings.artifacts_dir,
            ),
            "risk-scan": lambda payload: risk_scan.run(
                payload,
                base_dir=self.settings.base_dir,
                artifacts_dir=self.settings.artifacts_dir,
            ),
            "nfa-consult": lambda payload: nfa_consult.run(
                payload,
                base_dir=self.settings.base_dir,
                artifacts_dir=self.settings.artifacts_dir,
            ),
            "redesim-consulta": lambda payload: redesim_consulta.run(
                payload,
                base_dir=self.settings.base_dir,
                artifacts_dir=self.settings.artifacts_dir,
            ),
            "fac-batch": lambda payload: fac_batch.run(
                payload,
                base_dir=self.settings.base_dir,
                artifacts_dir=self.settings.artifacts_dir,
            ),
        }

    def start(self) -> None:
        if not self._started:
            self.worker.start()
            self._started = True


state = AppState()


def _resolve_workflow_from_path(path: str) -> str:
    if path.startswith("/workflows/"):
        return path.removeprefix("/workflows/")
    return ""


def _safe_job_response(job_id: str) -> dict[str, Any]:
    job = state.service.get_job(job_id)
    if job is None:
        raise ValidationError(f"Unknown job_id: {job_id}")
    return job.to_dict()


def _normalize_cep(cep: str) -> str:
    return re.sub(r"\D", "", cep)


def _run_bash(script_content: str, timeout_seconds: int) -> dict[str, Any]:
    if not script_content.strip():
        raise ValidationError("'script_content' cannot be empty.")

    try:
        completed = subprocess.run(
            ["bash", "-lc", script_content],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "success": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "duration_ms": 0,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "") + "\nExecution timed out.",
            "duration_ms": 0,
        }


async def _read_body(receive: Any) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message.get("type") != "http.request":
            break
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


async def _json_response(send: Any, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    headers = [(b"content-type", b"application/json")]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


async def _parse_json_body(receive: Any) -> dict[str, Any]:
    raw = await _read_body(receive)
    if not raw:
        return {}

    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON body: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ValidationError("JSON body must be an object.")
    return payload


def _build_health() -> dict[str, Any]:
    payload = health_payload()
    payload["machine"] = socket.gethostname()
    payload["project"] = "FBP_Backend"
    return payload


def _to_nfa_status(job_payload: dict[str, Any]) -> dict[str, Any]:
    result = job_payload.get("result") or {}
    return {
        "job_id": job_payload["job_id"],
        "job_type": "nfa_consult",
        "status": job_payload["status"],
        "created_at": job_payload["created_at"],
        "started_at": job_payload.get("started_at"),
        "completed_at": job_payload.get("completed_at"),
        "nfa_numero": result.get("nfa_numero"),
        "danfe_path": result.get("danfe_path"),
        "dar_path": result.get("dar_path"),
        "result": result.get("result"),
        "error": job_payload.get("error"),
    }


def _to_redesim_status(job_payload: dict[str, Any]) -> dict[str, Any]:
    result = job_payload.get("result") or {}
    return {
        "job_id": job_payload["job_id"],
        "status": job_payload["status"],
        "result": result.get("result"),
        "error": job_payload.get("error"),
    }


def _to_fac_status(job_payload: dict[str, Any]) -> dict[str, Any]:
    result = job_payload.get("result") or {}
    return {
        "success": job_payload["status"] != "failed",
        "job_id": job_payload["job_id"],
        "total": result.get("total", 0),
        "processed": result.get("processed", 0),
        "results": result.get("results", []),
        "errors": result.get("errors", []),
    }


async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    if scope.get("type") != "http":
        return

    state.start()

    method = scope.get("method", "GET").upper()
    path = str(scope.get("path", ""))

    try:
        if method == "GET" and path == "/health":
            await _json_response(send, 200, _build_health())
            return

        if method == "GET" and path == "/metrics":
            metrics = state.service.metrics()
            metrics["queue_size"] = state.service.queue.qsize()
            await _json_response(send, 200, metrics)
            return

        if method == "POST" and path == "/api/utils/cep":
            payload = await _parse_json_body(receive)
            cep = _normalize_cep(str(payload.get("cep", "")))
            enrich = bool(payload.get("enrich", False))

            if len(cep) != 8:
                await _json_response(
                    send,
                    200,
                    {"success": False, "data": None, "errors": ["CEP must have 8 digits."]},
                )
                return

            data = {
                "cep": cep,
                "valid": True,
                "logradouro": "Praca da Independencia" if cep.startswith("580") else None,
                "bairro": "Centro" if cep.startswith("580") else None,
                "cidade": "Joao Pessoa" if cep.startswith("580") else None,
                "uf": "PB" if cep.startswith("580") else None,
                "ibge": "2507507" if cep.startswith("580") else None,
                "source": "local-simulated",
            }
            if enrich:
                data["source"] = "local-simulated-enriched"

            await _json_response(send, 200, {"success": True, "data": data, "errors": []})
            return

        if method == "POST" and path == "/api/executor/run-bash":
            payload = await _parse_json_body(receive)
            script_content = str(payload.get("script_content", ""))
            timeout = int(payload.get("timeout", 60))
            timeout = min(max(timeout, 1), 300)
            execution = _run_bash(script_content, timeout)
            await _json_response(send, 200, execution)
            return

        if method == "POST" and path == "/nfa/consult":
            payload = await _parse_json_body(receive)
            job = state.service.create_job(workflow="nfa-consult", payload=payload)
            await _json_response(send, 200, {"job_id": job.job_id, "status": job.status})
            return

        if method == "GET" and path.startswith("/nfa/consult/status/"):
            job_id = path.removeprefix("/nfa/consult/status/")
            data = _safe_job_response(job_id)
            await _json_response(send, 200, _to_nfa_status(data))
            return

        if method == "POST" and path == "/cad/redesim/consulta":
            payload = await _parse_json_body(receive)
            job = state.service.create_job(workflow="redesim-consulta", payload=payload)
            await _json_response(
                send,
                200,
                {"job_id": job.job_id, "status": job.status, "execution_id": None},
            )
            return

        if method == "GET" and path.startswith("/cad/redesim/consulta/status/"):
            job_id = path.removeprefix("/cad/redesim/consulta/status/")
            data = _safe_job_response(job_id)
            await _json_response(send, 200, _to_redesim_status(data))
            return

        if method == "POST" and path == "/fac/batch":
            payload = await _parse_json_body(receive)
            facs = payload.get("facs")
            total = len(facs) if isinstance(facs, list) else 0
            job = state.service.create_job(workflow="fac-batch", payload=payload)
            await _json_response(
                send,
                200,
                {
                    "success": True,
                    "job_id": job.job_id,
                    "total": total,
                    "processed": 0,
                    "results": None,
                    "errors": None,
                },
            )
            return

        if method == "GET" and path.startswith("/fac/status/"):
            job_id = path.removeprefix("/fac/status/")
            data = _safe_job_response(job_id)
            await _json_response(send, 200, _to_fac_status(data))
            return

        if method == "POST" and path == "/jobs":
            payload = await _parse_json_body(receive)
            workflow = str(payload.get("workflow", "")).strip()
            job_input = payload.get("input", {})

            if workflow not in state.handlers:
                raise ValidationError(
                    "Unknown workflow. Supported: daily-briefing, doc-summarize, risk-scan, nfa-consult, redesim-consulta, fac-batch"
                )
            if not isinstance(job_input, dict):
                raise ValidationError("'input' must be an object.")

            job = state.service.create_job(workflow=workflow, payload=job_input)
            await _json_response(
                send,
                202,
                {"job_id": job.job_id, "status": job.status, "workflow": job.workflow},
            )
            return

        if method == "GET" and path.startswith("/jobs/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) >= 2 and parts[0] == "jobs":
                job_id = parts[1]
                job = state.service.get_job(job_id)
                if job is None:
                    await _json_response(send, 404, {"status": "not_found", "job_id": job_id})
                    return

                if len(parts) == 3 and parts[2] == "artifacts":
                    await _json_response(
                        send,
                        200,
                        {"job_id": job.job_id, "artifacts": job.artifacts},
                    )
                    return

                if len(parts) == 2:
                    await _json_response(send, 200, job.to_dict())
                    return

        workflow = _resolve_workflow_from_path(path)
        if method == "POST" and workflow:
            if workflow not in state.handlers:
                raise ValidationError(
                    "Unknown workflow. Supported: daily-briefing, doc-summarize, risk-scan, nfa-consult, redesim-consulta, fac-batch"
                )

            payload = await _parse_json_body(receive)
            job = state.service.create_job(workflow=workflow, payload=payload)
            await _json_response(
                send,
                202,
                {"job_id": job.job_id, "status": job.status, "workflow": job.workflow},
            )
            return

        await _json_response(send, 404, {"status": "not_found"})
    except ValidationError as exc:
        await _json_response(send, 400, {"status": "error", "message": str(exc)})
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Unexpected error processing request")
        await _json_response(send, 500, {"status": "error", "message": str(exc)})
