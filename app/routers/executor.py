from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/executor", tags=["bailiff", "execution"])

class ScriptExecutionRequest(BaseModel):
    """Request to execute a deterministic script."""
    script_content: str = Field(..., description="The full bash script to execute.")
    timeout: int = Field(60, description="Execution timeout in seconds.")

class ScriptExecutionResponse(BaseModel):
    """Response from script execution with evidence."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int

@router.post("/run-bash", response_model=ScriptExecutionResponse)
async def run_bash(request: ScriptExecutionRequest) -> ScriptExecutionResponse:
    """
    Executes a bash script received from the Control Plane.
    This fulfills the 'Bailiff' role of executing deterministic instructions.
    """
    import time
    start = time.perf_counter()

    # We use a temporary file to run the script or pass it directly to bash -s
    process = await asyncio.create_subprocess_exec(
        "/bin/bash", "-s",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=request.script_content.encode()),
            timeout=request.timeout
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        duration = int((time.perf_counter() - start) * 1000)
        return ScriptExecutionResponse(
            success=False,
            exit_code=-1,
            stdout="",
            stderr=f"Execution timed out after {request.timeout}s",
            duration_ms=duration
        )

    duration = int((time.perf_counter() - start) * 1000)

    return ScriptExecutionResponse(
        success=(process.returncode == 0),
        exit_code=process.returncode or 0,
        stdout=stdout.decode().strip(),
        stderr=stderr.decode().strip(),
        duration_ms=duration
    )
