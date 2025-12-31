# Troubleshooting: Terminal Exit Code 1

## Problema

O terminal termina com exit code 1 ao executar a automação REDESIM.

## Soluções

### 1. Usar o Script Wrapper (Recomendado)

O script wrapper garante que o ambiente está configurado corretamente:

```bash
cd /Users/dnigga/Documents/FBP_Backend
export ATF_USERNAME='eduardof'
export ATF_PASSWORD='atf101010'
./scripts/run_redesim_consulta_wrapper.sh
```

### 2. Executar Diretamente com PYTHONPATH

```bash
cd /Users/dnigga/Documents/FBP_Backend
export ATF_USERNAME='eduardof'
export ATF_PASSWORD='atf101010'
export PYTHONPATH=/Users/dnigga/Documents/FBP_Backend
python3 scripts/run_redesim_consulta.py
```

### 3. Verificar Dependências

```bash
# Verificar se httpx está instalado
python3 -c "import httpx; print('httpx OK')"

# Verificar se playwright está instalado
python3 -c "import playwright; print('playwright OK')"

# Instalar dependências se necessário
pip install httpx playwright
playwright install chromium
```

### 4. Verificar Imports

```bash
cd /Users/dnigga/Documents/FBP_Backend
export PYTHONPATH=/Users/dnigga/Documents/FBP_Backend
python3 -c "
from app.modules.cadastro.consultar_redesim import consultar_redesim
from app.modules.redesim.draft_creator import GmailService
import httpx
print('All imports OK')
"
```

### 5. Verificar Python Version

```bash
python3 --version
# Deve ser Python 3.9 ou superior
```

### 6. Problemas Comuns no macOS

#### Terminal não encontra python3

```bash
# Verificar localização
which python3

# Se não encontrar, instalar via Homebrew
brew install python3
```

#### Problemas com PATH

```bash
# Adicionar ao ~/.zshrc ou ~/.bash_profile
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
```

### 7. Executar com Logging Detalhado

```bash
cd /Users/dnigga/Documents/FBP_Backend
export ATF_USERNAME='eduardof'
export ATF_PASSWORD='atf101010'
export PYTHONPATH=/Users/dnigga/Documents/FBP_Backend
python3 -u scripts/run_redesim_consulta.py 2>&1 | tee run_log.txt
```

### 8. Verificar Permissões

```bash
# Tornar script executável
chmod +x scripts/run_redesim_consulta.py
chmod +x scripts/run_redesim_consulta_wrapper.sh
```

## Diagnóstico Rápido

Execute este comando para verificar tudo de uma vez:

```bash
cd /Users/dnigga/Documents/FBP_Backend && \
export PYTHONPATH=/Users/dnigga/Documents/FBP_Backend && \
python3 << 'EOF'
import sys
print("Python:", sys.version)
print("PYTHONPATH:", sys.path[0] if sys.path else "Not set")

try:
    from app.modules.cadastro.consultar_redesim import consultar_redesim
    print("✓ consultar_redesim import: OK")
except Exception as e:
    print(f"✗ consultar_redesim import: {e}")
    sys.exit(1)

try:
    from app.modules.redesim.draft_creator import GmailService
    print("✓ GmailService import: OK")
except Exception as e:
    print(f"✗ GmailService import: {e}")
    sys.exit(1)

try:
    import httpx
    print(f"✓ httpx import: OK (version {httpx.__version__})")
except Exception as e:
    print(f"✗ httpx import: {e}")
    sys.exit(1)

try:
    from playwright.async_api import Page
    print("✓ playwright import: OK")
except Exception as e:
    print(f"✗ playwright import: {e}")
    sys.exit(1)

print("\n✅ All checks passed!")
EOF
```

## Se Nada Funcionar

1. **Verificar logs detalhados:**

   ```bash
   python3 scripts/run_redesim_consulta.py 2>&1 | tee error_log.txt
   ```

2. **Verificar se o problema é específico do terminal:**

   - Tente executar em um terminal diferente (Terminal.app, iTerm2, etc.)
   - Verifique configurações do terminal (profiles, shell, etc.)

3. **Verificar se há processos bloqueando:**

   ```bash
   ps aux | grep python
   ps aux | grep playwright
   ```

4. **Reinstalar dependências:**
   ```bash
   pip install --upgrade httpx playwright
   playwright install chromium
   ```

## Referências

- [VS Code Terminal Troubleshooting](https://code.visualstudio.com/docs/supporting/troubleshoot-terminal-launch)
- [Playwright Installation](https://playwright.dev/python/docs/intro)

