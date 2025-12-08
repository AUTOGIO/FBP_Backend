#!/usr/bin/env bash
# iTerm2 NFA automation runner
set -euo pipefail

echo "=== FBP NFA AUTOMATION RUN START ==="
cd ~/Documents/FBP_Backend

# Venv resolution: project-local first, then centralized fallback
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "$HOME/Documents/.venvs/fbp" ]; then
    source "$HOME/Documents/.venvs/fbp/bin/activate"
else
    echo "❌ Virtual environment not found"
    exit 1
fi
curl -s http://localhost:8000/health
cp data_input_final input/cpf_batch.json
python nfa_batch_processor.py input/cpf_batch.json --max-forms 10
echo "=== AUTOMATION COMPLETE ==="
