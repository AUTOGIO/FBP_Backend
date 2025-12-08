#!/usr/bin/env bash
# Development mode: run backend with hot reload
# Same as start.sh but with DEBUG mode enabled

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
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run uvicorn in dev mode
cd "$PROJECT_ROOT"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-exclude ".venvs/*" \
    --reload-exclude "**/__pycache__/*" \
    --reload-exclude "tests/*" \
    --log-level debug

