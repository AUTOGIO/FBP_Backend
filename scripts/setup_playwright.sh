#!/bin/bash
# Setup Playwright browsers
# Installs all required browsers for Playwright

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$HOME/Documents/.venvs/fbp"

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

