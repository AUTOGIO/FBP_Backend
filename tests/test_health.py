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


class HealthAPITest(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        async def receive() -> dict:
            return {"type": "http.request", "body": b"", "more_body": False}

        messages: list[dict] = []

        async def send(message: dict) -> None:
            messages.append(message)

        scope = {"type": "http", "method": "GET", "path": "/health"}
        asyncio.run(app(scope, receive, send))

        start = messages[0]
        body = messages[1]
        payload = json.loads(body["body"].decode("utf-8"))

        self.assertEqual(start["status"], 200)
        self.assertEqual(payload["status"], "ok")


if __name__ == "__main__":
    unittest.main()
