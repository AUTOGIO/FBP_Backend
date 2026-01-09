#!/usr/bin/env bash
# Run script for FBP (Global FastAPI Backend)
# Uses absolute paths for Apple Silicon macOS

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Venv resolution: project-local first, then centralized fallback
PRIMARY_VENV="$SCRIPT_DIR/venv"
FALLBACK_VENV="$HOME/Documents/.venvs/fbp"
if [ -d "$PRIMARY_VENV" ]; then
    source "$PRIMARY_VENV/bin/activate"
elif [ -d "$FALLBACK_VENV" ]; then
    source "$FALLBACK_VENV/bin/activate"
else
    echo "❌ Virtual environment not found at $PRIMARY_VENV or $FALLBACK_VENV"
    exit 1
fi

# Set Python path
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# Fix for macOS fork safety (deadlock avoidance)
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Run uvicorn
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info


