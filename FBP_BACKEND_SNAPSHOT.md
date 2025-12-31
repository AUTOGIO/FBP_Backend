# FBP_Backend - Snapshot Completo do Projeto

**Data/Hora:** 2025-12-10 00:48:00  
**Localização:** `/Users/dnigga/Documents/FBP_Backend`

---

## 📊 Visão Geral

**FBP_Backend** é um backend FastAPI para automação de processos (REDESIM, NFA, Utils, Browser).

### Estatísticas do Projeto

- **Arquivo Principal NFA:** `nfa_batch_processor.py` (1,520 linhas, 61KB)
- **Total de Módulos Python:** 63 arquivos em `app/` (1.5MB)
- **Scripts de Automação:** 13 arquivos em `ops/` (84KB)
- **Scripts de Setup:** 11 arquivos em `scripts/` (48KB)
- **Documentação:** 16 arquivos Markdown em `docs/` (120KB)
- **Testes:** 16 arquivos em `tests/` (316KB)
- **Git Status:** Repositório ativo (último commit: `b541da4`)

---

## 📁 Estrutura de Diretórios

```
FBP_Backend/
├── .cursor/                    # Configurações do Cursor IDE
│   ├── rules/                 # 8 arquivos .mdc de regras
│   └── *.md                   # Documentação adicional
│
├── app/                       # Aplicação principal (63 arquivos Python)
│   ├── core/                  # Utilitários centrais
│   │   ├── browser.py
│   │   ├── clients.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── jobs.py
│   │   ├── logger.py
│   │   └── logging_config.py
│   │
│   ├── modules/               # Módulos de negócio
│   │   ├── nfa/               # Automação NFA (20+ arquivos)
│   │   │   ├── batch_processor.py
│   │   │   ├── form_filler.py
│   │   │   ├── form_submitter.py
│   │   │   ├── atf_login.py
│   │   │   └── ... (outros módulos NFA)
│   │   │
│   │   ├── redesim/           # Automação REDESIM (10+ arquivos)
│   │   │   ├── email_extractor.py
│   │   │   ├── draft_creator.py
│   │   │   └── ... (outros módulos REDESIM)
│   │   │
│   │   ├── organizer/         # Gerenciamento de janelas
│   │   └── utils/             # Funções utilitárias
│   │
│   ├── routers/               # Rotas FastAPI
│   │   ├── global_router.py
│   │   ├── health.py
│   │   ├── nfa.py
│   │   ├── nfa_real.py
│   │   ├── redesim.py
│   │   └── n8n_*.py           # Integrações n8n
│   │
│   ├── services/              # Serviços de negócio
│   │   ├── nfa_service.py
│   │   ├── nfa_real_service.py
│   │   ├── redesim_service.py
│   │   └── echo_service.py
│   │
│   └── main.py                # Entry point FastAPI
│
├── ops/                       # Scripts operacionais (13 arquivos)
│   ├── run_nfa_fast.sh        # ⭐ Runner principal otimizado
│   ├── run_nfa_now.sh         # Runner alternativo
│   ├── apply_iterm2_profile.sh
│   ├── fbp_nfa_iterm2_profile.json
│   ├── ITerm2_RUN_INSTRUCTIONS.md
│   ├── validate_nfa_system.sh
│   ├── validate_sefaz_access.sh
│   ├── nfa_form_diagnostic.py
│   ├── nfa_live_fill_demo.py
│   └── scripts/               # Scripts auxiliares
│       ├── foks_boot.sh
│       └── foks_env_autofix.sh
│
├── scripts/                   # Scripts de setup/manutenção (11 arquivos)
│   ├── start.sh               # Inicia servidor FastAPI
│   ├── setup_playwright.sh
│   └── ... (outros scripts)
│
├── docs/                      # Documentação (16 arquivos)
│   ├── NFA/
│   │   ├── PERFORMANCE_OPTIMIZATION.md
│   │   └── ... (outros docs NFA)
│   └── ... (outros documentos)
│
├── tests/                     # Testes (16 arquivos)
│   └── test_*.py
│
├── input/                     # Arquivos de entrada
│   ├── cpf_batch.json        # 1.0KB (copiado de data_input_final)
│   ├── cpf_batch_from_mg23.json  # 811B (batch específico MG23)
│   └── batch_example.json    # 303B (exemplo)
│
├── nfa_batch_processor.py    # ⭐ Processador principal NFA (1,520 linhas)
├── data_input_final           # ⭐ Arquivo de dados atual (10 itens)
├── run_nfa_automation.sh     # Runner legacy
├── iterm2_automation.sh      # Runner iTerm2
│
├── README.md                  # Documentação principal
├── README_ENHANCED.md         # Documentação expandida (755 linhas)
├── pyproject.toml             # Configuração do projeto
└── requirements.txt           # Dependências Python
```

---

## 🎯 Arquivos Principais

### 1. `nfa_batch_processor.py` (⭐ Core)

- **Tamanho:** 61KB, 1,520 linhas
- **Função:** Processador principal de lote NFA
- **Recursos:**
  - Proteção de campo DATE (`edtDtEmissao`)
  - Múltiplas estratégias de preenchimento (frame-based, direct page)
  - Retry logic (3 tentativas por operação)
  - Timeouts otimizados (5000ms default)
  - Speed multiplier (`--speed` parameter)
  - Logging contextualizado

### 2. `data_input_final` (⭐ Dados Atuais)

- **Formato:** JSON array
- **Total de Itens:** 10
- **Tamanho:** 44 linhas
- **Estrutura:** `[{"loja": "...", "cpf": "..."}, ...]`
- **Itens Atuais:**
  1. SP19 - 073.899.878-80
  2. SP32 - 286.773.348-07
  3. AM13 - 844.652.042-72 (duplicado 3x - itens 3, 4, 5)
  4. SP236 - 299.715.388-30
  5. SP43 - 345.336.128-81
  6. SP44 - 894.392.794-00
  7. SP47 - 090.192.538-16
  8. SP49 - 190.709.658-28
- **Nota:** Arquivo válido, pronto para processamento

### 3. `ops/run_nfa_fast.sh` (⭐ Runner Otimizado)

- **Função:** Executa automação NFA com controle de velocidade
- **Parâmetros:**
  - `SPEED_MULTIPLIER` (default: 2.0)
  - `MAX_FORMS` (default: 20)
- **Features:**
  - Ativa venv automaticamente
  - Carrega variáveis `.env`
  - Copia `data_input_final` para `input/cpf_batch.json`
  - Calcula tempo total e média por NFA

### 4. `ops/ITerm2_RUN_INSTRUCTIONS.md`

- **Função:** Guia completo de comandos para iTerm2
- **Conteúdo:** Sequência passo-a-passo e comandos únicos

---

## ⚙️ Configurações Atuais

### Performance Otimizations (Aplicadas)

1. **Timeouts Reduzidos:**

   - `wait_for_page_load_soft`: 8000ms → 5000ms
   - Element waits: 10000ms → 5000ms (botões críticos)
   - Safe clicks: 6000ms → 4000ms

2. **Retry Attempts Reduzidos:**

   - De 5 tentativas → 3 tentativas (todos os loops)

3. **Login Otimizado:**

   - Substituído `sleep(2)` + `sleep(4)` por `wait_for_selector` + `networkidle`
   - Timeout reduzido: 8000ms → 5000ms

4. **Pausa Entre CPFs:**
   - Reduzida de 3s → 1.5s (ainda escalonada por `--speed`)

### Speed Multiplier

- **Default:** 2.0x (50% mais rápido)
- **Range:** 1.0 (normal) a 3.0 (agressivo)
- **Uso:** `--speed 2.0` no `nfa_batch_processor.py`

### Max Forms

- **Default:** 20 itens
- **Configurado em:** Todos os scripts principais

---

## 🔧 Scripts Disponíveis

### Runners Principais

1. **`ops/run_nfa_fast.sh`** ⭐ (Recomendado)

   ```bash
   bash ops/run_nfa_fast.sh [SPEED] [MAX_FORMS]
   # Exemplo: bash ops/run_nfa_fast.sh 2.0 20
   ```

2. **`ops/run_nfa_now.sh`**

   - Usa backend na porta 8000 (LaunchAgent)
   - Requer backend rodando

3. **`run_nfa_automation.sh`**

   - Runner legacy
   - Usa socket mode (`/tmp/fbp.sock`)

4. **`iterm2_automation.sh`**
   - Runner para iTerm2
   - Versão simplificada

### Scripts de Setup

- `scripts/start.sh` - Inicia servidor FastAPI
- `scripts/setup_playwright.sh` - Configura Playwright

### Scripts de Validação

- `ops/validate_nfa_system.sh` - Valida sistema NFA
- `ops/validate_sefaz_access.sh` - Testa acesso SEFAZ

---

## 📝 Documentação

### Arquivos Principais

1. **`README.md`** (243 linhas)

   - Quick start
   - Estrutura do projeto
   - Setup básico

2. **`README_ENHANCED.md`** (755 linhas)

   - Documentação expandida
   - Detalhes técnicos

3. **`docs/NFA/PERFORMANCE_OPTIMIZATION.md`**

   - Guia de otimização
   - Tabelas de performance
   - Recomendações de speed

4. **`ops/ITerm2_RUN_INSTRUCTIONS.md`**
   - Comandos para iTerm2
   - Exemplos de uso

---

## 🔐 Configuração de Ambiente

### Variáveis de Ambiente (`.env`)

- `NFA_USERNAME` - Usuário SEFAZ (carregado de `.env`)
- `NFA_PASSWORD` - Senha SEFAZ (carregado de `.env`)
- `NFA_EMITENTE_CNPJ` - CNPJ do emitente (atual: `28.842.017/0001-05`)
- **Arquivo:** `.env` (87 bytes, criado em Dec 9)
- **Template:** `.env.example` (145 bytes)

### Virtual Environment

- **Localização:** `~/.venvs/fbp`
- **Python:** 3.11+
- **Ativação:** `source ~/.venvs/fbp/bin/activate`

### PYTHONPATH

- **Configurado:** `/Users/dnigga/Documents/FBP_Backend`
- **Exportado automaticamente** pelos scripts

---

## 🚀 Fluxo de Execução Atual

### Processo Completo

1. **Preparação:**

   - Copia `data_input_final` → `input/cpf_batch.json`
   - Valida JSON
   - Carrega variáveis `.env`

2. **Login:**

   - Navega para `LOGIN_URL`
   - Preenche credenciais
   - Aguarda navegação (timeout: 5000ms)

3. **Para Cada Item:**

   - Navega para formulário
   - **Protege campo DATE** (JavaScript injection)
   - Preenche Informações Adicionais
   - Preenche Emitente CNPJ (múltiplas estratégias)
   - Preenche Destinatário CPF
   - Seleciona checkbox Produto
   - Preenche campos do produto (5 campos)
   - Clica ADICIONAR/ALTERAR ITEM
   - Seleciona CST
   - Seleciona checkbox do item na tabela
   - Clica CALCULAR
   - **Re-verifica campo DATE** antes de submeter
   - Clica SUBMETER NOTA
   - Aguarda confirmação (múltiplos métodos)
   - Prossegue para próximo CPF

4. **Proteção de DATE:**
   - Captura valor original no carregamento
   - Injeta JavaScript para tornar `readonly`
   - Adiciona event listeners para restaurar valor
   - Verifica e restaura antes de SUBMETER NOTA
   - Loga qualquer alteração como erro crítico

---

## 📊 Métricas de Performance

### Tempos Estimados (por NFA)

| Speed           | Tempo/NFA | 20 NFAs    | Melhoria        |
| --------------- | --------- | ---------- | --------------- |
| 1.0 (normal)    | ~80-120s  | ~27-40 min | Baseline        |
| 1.5             | ~60-80s   | ~20-27 min | 33% mais rápido |
| 2.0 (default)   | ~40-60s   | ~13-20 min | 50% mais rápido |
| 3.0 (agressivo) | ~25-40s   | ~8-13 min  | 66% mais rápido |

### Otimizações Aplicadas

- ✅ Timeouts reduzidos (50-60% redução)
- ✅ Retry attempts reduzidos (5→3)
- ✅ Login otimizado (6s→1s)
- ✅ Pausa entre CPFs reduzida (3s→1.5s)

---

## 🛠️ Tecnologias e Dependências

### Stack Principal

- **Python:** 3.11+
- **FastAPI:** Backend framework
- **Playwright:** Automação de browser
- **Pydantic:** Validação de dados

### Dependências Principais

- `playwright` - Automação browser
- `fastapi` - Framework web
- `uvicorn` - ASGI server
- `pydantic` - Validação
- `python-dotenv` - Gerenciamento de .env

---

## 📍 Estado Atual do Sistema

### Processos em Execução

**Backend FastAPI (Ativo):**

- PID: 4677
- Comando: `uvicorn app.main:app --uds /tmp/fbp.sock`
- Status: Rodando em socket mode (`/tmp/fbp.sock`)
- Workers: 1
- Loop: uvloop

**NFA Batch Processor:**

- Verificar com: `ps aux | grep nfa_batch_processor`
- Status: Executa sob demanda via scripts

### Logs Recentes

- **Localização:** `/tmp/nfa_run_*.log`
- **Monitoramento:** `tail -f /tmp/nfa_run_*.log`
- **Formato:** Timestamp | Level | Context | Message

### Backend Status

- **Socket Mode:** ✅ ATIVO em `/tmp/fbp.sock`
- **HTTP Mode:** Não configurado (usando socket)
- **Health Check:** `curl --unix-socket /tmp/fbp.sock http://localhost/health`

---

## 🔄 Comandos Rápidos de Referência

### Executar Automação

```bash
# Modo rápido (recomendado)
cd /Users/dnigga/Documents/FBP_Backend
source ~/.venvs/fbp/bin/activate
export PYTHONPATH="/Users/dnigga/Documents/FBP_Backend:${PYTHONPATH:-}"
export $(grep -v '^#' .env | grep -v '^$' | xargs | sed 's/"//g')
bash ops/run_nfa_fast.sh 2.0 20
```

### Comando Único

```bash
cd /Users/dnigga/Documents/FBP_Backend && source ~/.venvs/fbp/bin/activate && export PYTHONPATH="/Users/dnigga/Documents/FBP_Backend:${PYTHONPATH:-}" && export $(grep -v '^#' .env | grep -v '^$' | xargs | sed 's/"//g') && bash ops/run_nfa_fast.sh 2.0 20
```

### Monitorar Progresso

```bash
tail -f /tmp/nfa_run_*.log | grep -E "(completed|SUBMETER|ERROR|Processing NFA)"
```

---

## 📌 Notas Importantes

1. **Campo DATE:** Sempre protegido via JavaScript injection
2. **Speed Multiplier:** Afeta todos os `sleep()` calls
3. **Retry Logic:** 3 tentativas por operação crítica
4. **Timeouts:** Otimizados para balancear velocidade e estabilidade
5. **JSON Input:** Sempre validar antes de executar (mesclar arrays se necessário)

---

## 🔍 Arquivos de Referência

- **Configuração iTerm2:** `ops/fbp_nfa_iterm2_profile.json`
- **Instruções iTerm2:** `ops/ITerm2_RUN_INSTRUCTIONS.md`
- **Otimização:** `docs/NFA/PERFORMANCE_OPTIMIZATION.md`
- **Dados Atuais:** `data_input_final` (10 itens)

---

## 📚 Arquivos de Documentação Adicional

### Relatórios e Análises

- `ENHANCEMENTS_SUMMARY.md` - Resumo de melhorias
- `EXECUTIVE_ANALYSIS_REPORT.md` - Análise executiva
- `FBP_PRODUCTION_READY_SUMMARY.md` - Status de produção
- `NFA_AUTOMATION_SPECIALIST_ENHANCED.md` - Especialista NFA
- `NFA_CLEANUP_SUMMARY.md` - Limpeza NFA
- `NFA_FORM_FILLING_FIXES.md` - Correções de preenchimento
- `NFA_SYSTEM_ARCHITECTURE.md` - Arquitetura do sistema
- `OPERATIONAL_QUICK_REFERENCE.md` - Referência rápida
- `PLAYWRIGHT_FIXES_SUMMARY.md` - Correções Playwright
- `PROJECT_FULL_REPORT.md` - Relatório completo
- `SUMMARY_FEYNMAN.md` - Resumo Feynman

### Documentação Principal

- `README.md` (243 linhas) - Documentação básica
- `README_ENHANCED.md` (755 linhas) - Documentação expandida

---

## 🔄 Histórico Git Recente

```
b541da4 - fix(nfa): update form filling logic to use direct selectors
212a006 - fix(nfa): modernize form filling logic - remove frame dependencies
7b61eed - chore(deps): add Google API dependencies for REDESIM Gmail integration
3d0a8dc - chore(env): heal FBP venv and socket readiness
fbd69a1 - CHECKPOINT: before FBP env healing
```

---

## ⚠️ Problemas Conhecidos e Soluções

### 1. JSON com Arrays Separados

**Problema:** `data_input_final` frequentemente tem dois arrays JSON separados  
**Solução:** Mesclar manualmente ou usar script de validação  
**Status:** Corrigido no snapshot atual (10 itens válidos)

### 2. Campo DATE sendo Alterado

**Problema:** Campo `edtDtEmissao` pode ser modificado durante SUBMETER NOTA  
**Solução:** JavaScript injection para proteção + verificação antes de submeter  
**Status:** ✅ Implementado e funcionando

### 3. Terminal Exit Code 1

**Problema:** `.zshrc` referenciava `PYTHONPATH_CLEAN` não definido  
**Solução:** Alterado para `export PYTHONPATH="${PYTHONPATH_CLEAN:-}"`  
**Status:** ✅ Corrigido

---

**Última Atualização:** 2025-12-10 00:48:00  
**Versão do Snapshot:** 1.0  
**Backend Status:** ✅ Ativo (Socket mode)
