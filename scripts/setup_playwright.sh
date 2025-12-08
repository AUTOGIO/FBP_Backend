#!/usr/bin/env bash
# Setup Playwright browsers
# Installs all required browsers for Playwright

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Venv resolution: project-local first, then centralized fallback
PRIMARY_VENV="$PROJECT_ROOT/venv"
FALLBACK_VENV="$HOME/Documents/.venvs/fbp"
if [ -d "$PRIMARY_VENV" ]; then
    VENV_PATH="$PRIMARY_VENV"
else
    VENV_PATH="$FALLBACK_VENV"
fi

# Activate venv
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH"
    echo "💡 Run: python3 -m venv $VENV_PATH"
    exit 1
fi

source "$VENV_PATH/bin/activate"

# Install Playwright browsers
echo "🎭 Installing Playwright browsers..."
python -m playwright install chromium
python -m playwright install-deps chromium

echo "✅ Playwright browsers installed successfully"

