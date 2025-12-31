# NFA Automation Performance Optimization

## Quick wins (no code changes)

- Use the existing `--speed` flag (scales all sleeps):
  - `--speed 1.5` (estável, ~33% mais rápido)
  - `--speed 2.0` (rápido, ~50% mais rápido)
  - `--speed 3.0` (agressivo, monitorar erros)
- Comando recomendado (balanceado):
  ```bash
  cd /Users/dnigga/Documents/FBP_Backend
  source ~/.venvs/fbp/bin/activate
  export PYTHONPATH="/Users/dnigga/Documents/FBP_Backend:${PYTHONPATH:-}"
  export $(grep -v '^#' .env | grep -v '^$' | xargs | sed 's/"//g')
  python nfa_batch_processor.py input/cpf_batch.json --max-forms 20 --speed 2.0
  ```

## Code tweaks already applied

- Login waits trocados de sleeps longos para `wait_for_selector` + `networkidle` com fallback rápido.
- Pausa entre CPFs reduzida de 3s para 1.5s (ainda escalonada por `--speed`).

## Next easy tweaks (if needed)

- Reduzir timeouts suaves: `wait_for_page_load_soft` de 8000ms para 5000ms.
- Diminuir tentativas/retries para 3 (hoje 5) onde houver `attempt` loops.
- Usar waits condicionais em vez de `sleep(0.5)` em pontos críticos (preenchimento de CFOP, repartição, município).

## Estimativa de ganho

| Speed      | Tempo por NFA (estim.) | 20 NFAs    |
| ---------- | ---------------------- | ---------- |
| 1.0 (base) | ~80–120s               | ~27–40 min |
| 1.5        | ~60–80s                | ~20–27 min |
| 2.0        | ~40–60s                | ~13–20 min |
| 3.0        | ~25–40s                | ~8–13 min  |

## Cuidados

- `--speed` alto aumenta risco de timing issues; monitore logs.
- Se o site estiver lento, reduza para 1.5 ou 1.0.
- Mantenha o headless desativado (anti-bot).
