from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app


def run_request(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    body_bytes = b"" if payload is None else json.dumps(payload).encode("utf-8")
    delivered = False

    async def receive() -> dict:
        nonlocal delivered
        if delivered:
            return {"type": "http.request", "body": b"", "more_body": False}
        delivered = True
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    messages: list[dict] = []

    async def send(message: dict) -> None:
        messages.append(message)

    scope = {"type": "http", "method": method, "path": path}
    asyncio.run(app(scope, receive, send))

    status = messages[0]["status"]
    data = json.loads(messages[1]["body"].decode("utf-8"))
    return status, data


class JobsAPITest(unittest.TestCase):
    def test_create_and_read_job(self) -> None:
        status, created = run_request(
            "POST",
            "/jobs",
            {"workflow": "doc-summarize", "input": {"text": "Hello\nWorld"}},
        )
        self.assertEqual(status, 202)

        job_id = created["job_id"]
        status, current = run_request("GET", f"/jobs/{job_id}")
        self.assertEqual(status, 200)
        self.assertEqual(current["workflow"], "doc-summarize")


if __name__ == "__main__":
    unittest.main()
