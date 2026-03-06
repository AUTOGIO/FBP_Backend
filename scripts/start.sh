#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${FBP_HOST:-127.0.0.1}"
PORT="${FBP_PORT:-8000}"

# Prefer uvicorn + ASGI app when available.
if python3 -c "import uvicorn" >/dev/null 2>&1; then
  exec python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT"
fi

# Fallback to standard-library HTTP server for /health.
exec python3 - <<'PY'
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

HOST = os.environ.get("FBP_HOST", "127.0.0.1")
PORT = int(os.environ.get("FBP_PORT", "8000"))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            payload = {
                "status": "ok",
                "service": "fbp-backend",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            data = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        data = b'{"status":"not_found"}'
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        return

HTTPServer((HOST, PORT), Handler).serve_forever()
PY