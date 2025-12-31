#!/bin/bash
# Wrapper script for REDESIM consulta automation
# Fixes terminal exit code 1 issues by ensuring proper environment setup

set -e  # Exit on error

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT"

# Check if credentials are set
if [ -z "$ATF_USERNAME" ] || [ -z "$ATF_PASSWORD" ]; then
    echo "❌ ERROR: ATF_USERNAME and ATF_PASSWORD must be set"
    echo ""
    echo "Set them with:"
    echo "  export ATF_USERNAME='eduardof'"
    echo "  export ATF_PASSWORD='atf101010'"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: python3 not found"
    exit 1
fi

# Run the script
echo "🚀 Starting REDESIM consulta automation..."
echo "📁 Project root: $PROJECT_ROOT"
echo "🐍 Python: $(python3 --version)"
echo ""

python3 "$SCRIPT_DIR/run_redesim_consulta.py"

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Script completed successfully"
else
    echo ""
    echo "❌ Script exited with code: $EXIT_CODE"
fi

exit $EXIT_CODE

