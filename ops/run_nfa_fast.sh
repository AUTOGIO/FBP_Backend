#!/usr/bin/env bash
# Fast NFA Automation Runner - tuned for speed via --speed
# Usage:
#   ./ops/run_nfa_fast.sh [SPEED_MULTIPLIER] [MAX_FORMS]
# Examples:
#   ./ops/run_nfa_fast.sh              # default speed=2.0, max_forms=20
#   ./ops/run_nfa_fast.sh 1.5 8        # safer speed, first 8 forms
#   ./ops/run_nfa_fast.sh 3.0 5        # aggressive speed, 5 forms

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

SPEED_MULTIPLIER="${1:-2.0}"
MAX_FORMS="${2:-20}"

echo "=== FBP NFA FAST AUTOMATION RUN ==="
echo "Speed Multiplier: ${SPEED_MULTIPLIER}x"
echo "Max Forms: ${MAX_FORMS}"
echo ""

# Activate venv
if [ -d "$HOME/.venvs/fbp" ]; then
    source "$HOME/.venvs/fbp/bin/activate"
else
    echo "❌ venv not found at $HOME/.venvs/fbp"
    exit 1
fi

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# Load .env variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs | sed 's/"//g')
fi

# Prepare batch input
echo "Preparing batch input file..."
if [ -f data_input_final ]; then
    cp data_input_final input/cpf_batch.json
    echo "✓ Copied data_input_final to input/cpf_batch.json"
else
    echo "⚠️  data_input_final not found, using existing input/cpf_batch.json"
fi
echo ""

# Run with speed multiplier
echo "🚀 Running NFA automation with ${SPEED_MULTIPLIER}x speed..."
START_TIME=$(date +%s)
python nfa_batch_processor.py input/cpf_batch.json --max-forms "$MAX_FORMS" --speed "$SPEED_MULTIPLIER"
END_TIME=$(date +%s)

ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo ""
echo "=== AUTOMATION COMPLETE ==="
echo "⏱️  Total time: ${MINUTES}m ${SECONDS}s"
if [ "$MAX_FORMS" -gt 0 ]; then
    echo "📊 Avg per NFA: ~$((ELAPSED / MAX_FORMS))s"
fi
