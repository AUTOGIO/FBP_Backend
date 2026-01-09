#!/usr/bin/env bash
# NFA Automation Runner - Fixed for socket mode
# Runs NFA batch processing with correct paths and health checks

set -euo pipefail

echo "=== FBP NFA AUTOMATION RUN START ==="

cd /Users/dnigga/Documents/FBP_Backend

# Activate venv (corrected path)
source ~/.venvs/fbp/bin/activate

# Set PYTHONPATH
export PYTHONPATH="/Users/dnigga/Documents/FBP_Backend:${PYTHONPATH:-}"

# Fix for macOS fork safety (deadlock avoidance)
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Load .env if it exists (using python-dotenv or manual parsing)
if [ -f .env ]; then
    # Export variables from .env, handling quoted values
    export $(grep -v '^#' .env | grep -v '^$' | xargs | sed 's/"//g')
fi

echo "Checking API health via UNIX socket..."
HEALTH_RESPONSE=$(curl -s --unix-socket /tmp/fbp.sock http://localhost/health 2>&1)
if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
    echo "✓ Backend is healthy"
    echo "Response: $HEALTH_RESPONSE"
else
    echo "⚠️  Backend health check failed or backend not running on socket"
    echo "Response: $HEALTH_RESPONSE"
    echo "💡 Make sure backend is running: ./scripts/start.sh"
    exit 1
fi

echo ""
echo "Preparing batch input file..."
if [ -f data_input_final ]; then
    cp data_input_final input/cpf_batch.json
    echo "✓ Copied data_input_final to input/cpf_batch.json"
else
    echo "⚠️  data_input_final not found, using existing input/cpf_batch.json"
fi

echo ""
echo "Running NFA automation batch..."
python nfa_batch_processor.py input/cpf_batch.json --max-forms 20

echo ""
echo "=== AUTOMATION COMPLETE ==="



