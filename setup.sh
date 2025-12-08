#!/usr/bin/env bash
# Initial setup script for FBP Backend
# Creates venv, installs dependencies, sets up Playwright

set -euo pipefail

VENV_PATH="$HOME/Documents/.venvs/fbp"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Setting up FBP Backend..."

# Create venv if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
    echo "📦 Creating virtual environment at $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
else
    echo "✅ Virtual environment already exists"
fi

# Activate venv
echo "🔌 Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install project in editable mode with dev dependencies
echo "📥 Installing dependencies..."
cd "$PROJECT_ROOT"
pip install -e ".[dev]"

# Install Playwright browsers
echo "🎭 Installing Playwright browsers..."
python -m playwright install chromium || echo "⚠️  Playwright browser installation skipped (can be done later)"

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  ./scripts/start.sh"
echo ""
echo "To run tests:"
echo "  ./scripts/test.sh"
echo ""
echo "To setup Playwright browsers:"
echo "  ./scripts/setup_playwright.sh"

