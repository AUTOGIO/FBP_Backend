#!/usr/bin/env bash
# Start FBP Backend Server
# Activates venv and runs uvicorn with auto settings

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Venv resolution: project-local first, then centralized fallback
PRIMARY_VENV="$PROJECT_ROOT/venv"
FALLBACK_VENV="$HOME/.venvs/fbp"
if [ -d "$PRIMARY_VENV" ]; then
    VENV_PATH="$PRIMARY_VENV"
else
    VENV_PATH="$FALLBACK_VENV"
fi

# Activate venv
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH"
    echo "💡 Run: python3 -m venv $VENV_PATH"
    echo "💡 Then: $VENV_PATH/bin/pip install -e '.[dev]'"
    exit 1
fi

source "$VENV_PATH/bin/activate"

# Set environment variables
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# UNIX Socket configuration (2025 Apple Silicon best practices)
SOCKET_PATH="${FBP_SOCKET_PATH:-/tmp/fbp.sock}"

# Fallback to PORT mode if FBP_PORT is explicitly set (debug only)
if [[ -n "${FBP_PORT:-}" ]]; then
    echo "⚠️  PORT mode enabled (debug): Using TCP port $FBP_PORT"
    cd "$PROJECT_ROOT"
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port "$FBP_PORT" \
        --reload \
        --reload-exclude ".venvs/*" \
        --reload-exclude "**/__pycache__/*" \
        --reload-exclude "tests/*" \
        --log-level info
fi

# UNIX Socket mode (default)
echo "🚀 Starting FBP on UNIX socket: $SOCKET_PATH"
rm -f "$SOCKET_PATH"

cd "$PROJECT_ROOT"
exec uvicorn app.main:app \
    --uds "$SOCKET_PATH" \
    --workers 1 \
    --loop uvloop \
    --http httptools \
    --reload \
    --reload-exclude ".venvs/*" \
    --reload-exclude "**/__pycache__/*" \
    --reload-exclude "tests/*" \
    --log-level info

