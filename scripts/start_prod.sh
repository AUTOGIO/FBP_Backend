#!/usr/bin/env bash
# Production mode: run backend without hot reload (for LaunchAgent)
# Similar to start.sh but without --reload flag

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PRIMARY_VENV="/Users/dnigga/Documents/FBP_Backend/venv"
FALLBACK_VENV="$HOME/Documents/.venvs/fbp"
if [ -d "$PRIMARY_VENV" ]; then
    VENV_PATH="$PRIMARY_VENV"
else
    VENV_PATH="$FALLBACK_VENV"
fi

# Activate venv
if [ ! -d "$VENV_PATH" ]; then
    echo "Virtual environment not found at $VENV_PATH"
    echo "Run: python3 -m venv $VENV_PATH"
    exit 1
fi

source "$VENV_PATH/bin/activate"

# Set environment variables
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export DEBUG=false
export LOG_LEVEL=INFO

# UNIX Socket configuration (2025 Apple Silicon best practices)
SOCKET_PATH="${FBP_SOCKET_PATH:-/tmp/fbp.sock}"

# Fallback to PORT mode if FBP_PORT is explicitly set (debug only)
if [[ -n "${FBP_PORT:-}" ]]; then
    echo "⚠️  PORT mode enabled (debug): Using TCP port $FBP_PORT"
    cd "$PROJECT_ROOT"
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port "$FBP_PORT" \
        --log-level info
fi

# UNIX Socket mode (default production)
echo "🚀 Starting FBP on UNIX socket: $SOCKET_PATH (production mode)"
rm -f "$SOCKET_PATH"

cd "$PROJECT_ROOT"
# Production: 4 workers, uvloop, httptools for optimal Apple Silicon performance
exec uvicorn app.main:app \
    --uds "$SOCKET_PATH" \
    --workers 4 \
    --loop uvloop \
    --http httptools \
    --log-level info

