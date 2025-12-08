echo "=== FBP NFA AUTOMATION RUN START ==="
cd ~/Documents/FBP_Backend
source ~/Documents/.venvs/fbp/bin/activate
curl -s http://localhost:8000/health
cp data_input_final input/cpf_batch.json
python nfa_batch_processor.py input/cpf_batch.json --max-forms 10
echo "=== AUTOMATION COMPLETE ==="
