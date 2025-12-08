#!/bin/bash
# Start FBP Backend Server
# Activates venv and runs uvicorn with auto settings

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$HOME/Documents/.venvs/fbp"

# Activate venv
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH"
    echo "💡 Run: python3 -m venv $VENV_PATH"
    echo "💡 Then: $VENV_PATH/bin/pip install -e '.[dev]'"
    exit 1
fi

source "$VENV_PATH/bin/activate"

# Set environment variables
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Run uvicorn
cd "$PROJECT_ROOT"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-exclude ".venvs/*" \
    --reload-exclude "**/__pycache__/*" \
    --reload-exclude "tests/*" \
    --log-level info

