# FBP Backend - Relatório Completo do Projeto

**Data de Geração:** 2025-01-XX
**Versão do Projeto:** 0.1.0
**Workspace:** `/Users/eduardofgiovannini/Documents/FBP_Backend`

---

## 📋 Sumário Executivo

O **FBP Backend** (FastAPI Backend) é um sistema centralizado de automação desenvolvido em Python/FastAPI que serve como hub de orquestração para múltiplos projetos de automação, incluindo:

- **NFA (Nota Fiscal Avulsa)**: Automação de criação de notas fiscais avulsas
- **REDESIM**: Extração e processamento de emails relacionados a processos de inscrição estadual
- **Utils**: Ferramentas utilitárias (validação de CEP, captura de HTML, etc.)
- **Browser**: Automação de navegador via Playwright

O sistema foi projetado para integração com ferramentas de workflow como **n8n**, **LM Studio agents**, e scripts customizados, seguindo uma arquitetura modular e extensível.

---

## 🏗️ Arquitetura do Sistema

### Visão Geral

O FBP segue uma arquitetura em camadas bem definida:

```
┌─────────────────────────────────────────┐
│     External Tools (n8n, LM Studio)     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Router Layer (FastAPI)           │
│  - health.py, echo.py, nfa.py, etc.     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│        Service Layer (Execution)         │
│  - nfa_service.py, redesim_service.py   │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Module Layer (Business Logic)       │
│  - modules/nfa/, modules/redesim/       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Core Layer (Infrastructure)      │
│  - jobs.py, clients.py, browser.py      │
└──────────────────────────────────────────┘
```

### Componentes Principais

#### 1. **Core Layer** (`app/core/`)

**config.py**

- Gerenciamento de configurações via Pydantic Settings
- Suporte a variáveis de ambiente (`.env`)
- Configurações para NFA, REDESIM, Gmail API, Job Backend

**jobs.py**

- Sistema de rastreamento de jobs assíncronos
- Estados: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `TIMEOUT`, `CANCELLED`
- Limpeza automática de jobs expirados
- Armazenamento em memória (extensível para Redis/DB)

**clients.py**

- Abstração para clientes de automação (HTTP/Local)
- Factory functions para NFA e REDESIM clients
- Suporte a modo HTTP (serviço externo) e Local (biblioteca)

**browser.py**

- Wrapper para Playwright
- Gerenciamento de instâncias de navegador
- Suporte a modo headless/visual

**exceptions.py**

- Hierarquia de exceções customizadas:
  - `FBPException` (base)
  - `ValidationException` (400)
  - `JobNotFoundException` (404)
  - `JobConflictException` (409)
  - `AutomationException` (500)

**logging_config.py**

- Logging estruturado
- Formatação JSON-compatível
- Níveis configuráveis via settings

#### 2. **Module Layer** (`app/modules/`)

**NFA Module** (`app/modules/nfa/`)

- `atf_login.py`: Autenticação no sistema ATF
- `atf_frames.py`: Navegação e gerenciamento de frames
- `atf_selectors.py`: Seletores CSS/XPath para elementos
- `form_filler.py`: Orquestrador de preenchimento de formulário
- `emitente_filler.py`: Preenchimento de dados do emitente
- `destinatario_filler.py`: Preenchimento de dados do destinatário
- `endereco_filler.py`: Preenchimento de endereço
- `produto_filler.py`: Adição de itens/produtos
- `batch_processor.py`: Processamento em lote com retry logic
- `data_validator.py`: Validação de dados de entrada

**REDESIM Module** (`app/modules/redesim/`)

- `extractor.py`: Orquestrador principal de extração
- `browser_extractor.py`: Extração via browser (Cursor/Playwright)
- `email_extractor.py`: Extração de emails de HTML/texto
- `email_collector.py`: Coleta e agregação de emails
- `data_extractor.py`: Extração e parsing de dados
- `draft_creator.py`: Criação de rascunhos Gmail
- `email_client.py`: Cliente Gmail API
- `playwright_extractor.py`: Extração via Playwright
- `auto_extractor.py`: Orquestração automatizada
- `devtools_extractor.py`: Extração via DevTools

**Utils Module** (`app/modules/utils/`)

- `cep_validator.py`: Validação e enriquecimento de CEP

**Organizer Module** (`app/modules/organizer/`)

- Módulo para gerenciamento de janelas (em desenvolvimento)

#### 3. **Service Layer** (`app/services/`)

**nfa_service.py**

- `create_nfa()`: Criação de NFA única
- `create_nfa_batch()`: Criação em lote
- Integração com `BatchNFAProcessor`
- Validação de dados via `data_validator`

**redesim_service.py**

- `create_redesim_job()`: Criação de job de extração
- `get_redesim_job_status()`: Consulta de status
- Execução assíncrona em background
- Integração com clientes HTTP/Local

**echo_service.py**

- Serviço de teste/echo para validação de conectividade

#### 4. **Router Layer** (`app/routers/`)

**Endpoints Principais:**

**health.py**

- `GET /health`: Health check básico

**echo.py**

- `POST /echo`: Endpoint de teste/echo

**global_router.py**

- `POST /global/nfa/test`: Teste de NFA com dados mínimos
- `POST /global/nfa/test/scenario-c`: Teste completo Scenario C
- `POST /global/nfa/visual`: Lançamento de teste visual
- `POST /global/redesim/test`: Teste de extração REDESIM
- `POST /global/cep/validate`: Validação de CEP
- `GET /global/health`: Health check completo com status de sistema

**nfa.py** (Phase 1 - Mock)

- Endpoints mock para desenvolvimento/teste

**nfa_real.py** (Phase 2 - Real)

- `POST /nfa/create`: Criação de NFA (job-based)
- `GET /nfa/status/{job_id}`: Status do job

**redesim.py** (Phase 2)

- `POST /redesim/email-extract`: Extração de emails (job-based)
- `GET /redesim/status/{job_id}`: Status do job

**n8n\_\*.py** (Endpoints n8n-compatíveis)

- `n8n_redesim.py`: `/api/redesim/*`
- `n8n_nfa.py`: `/api/nfa/*`
- `n8n_utils.py`: `/api/utils/*`
- `n8n_browser.py`: `/api/browser/*`

Todos os endpoints n8n retornam formato padronizado:

```json
{
  "success": true|false,
  "data": {},
  "errors": []
}
```

---

## 🔄 Fluxo de Requisições

### Fluxo Simples (Phase 1)

```
Client → Router → Service → Response
```

Exemplo: `POST /echo`

### Fluxo com Jobs (Phase 2)

```
1. Client → Router → Service → Job Store → {job_id, status: "queued"}
2. Background Task → Automation Client → External Service
3. Client → Router → Service → Job Store → {status, result}
```

Exemplo: `POST /nfa/create`

**Estados do Job:**

- `QUEUED`: Job criado, aguardando execução
- `RUNNING`: Em execução
- `COMPLETED`: Concluído com sucesso
- `FAILED`: Falhou com erro
- `TIMEOUT`: Excedeu tempo limite
- `CANCELLED`: Cancelado

---

## 📦 Dependências e Tecnologias

### Core Dependencies

```toml
fastapi>=0.104.0          # Framework web assíncrono
uvicorn[standard]>=0.24.0  # ASGI server
pydantic>=2.5.0           # Validação de dados
pydantic-settings>=2.1.0   # Configurações
httpx>=0.25.0             # Cliente HTTP assíncrono
playwright>=1.40.0        # Automação de browser
google-auth>=2.23.0       # Autenticação Google
google-api-python-client>=2.100.0  # Gmail API
requests>=2.31.0          # Cliente HTTP síncrono
pyyaml>=6.0.0             # Parsing YAML
```

### Dev Dependencies

```toml
pytest>=7.4.0             # Framework de testes
pytest-asyncio>=0.21.0    # Suporte assíncrono
pytest-cov>=4.1.0         # Coverage
ruff>=0.1.0               # Linter/formatter
mypy>=1.7.0               # Type checking
black>=23.11.0            # Code formatter
```

---

## 🔐 Segurança e Configuração

### Gerenciamento de Credenciais

- Credenciais armazenadas em `config/auth/` (gitignored)
- Gmail OAuth: `credentials.json` e `token.json`
- Variáveis de ambiente via `.env`
- Nenhum secret hardcoded no código
- Logging estruturado (sem vazamento de credenciais)

### Configurações Principais

**Settings (app/core/config.py):**

- `NFA_AUTOMATION_MODE`: "http" | "local"
- `NFA_AUTOMATION_URL`: URL do serviço externo (se HTTP)
- `REDESIM_AUTOMATION_MODE`: "http" | "local"
- `REDESIM_AUTOMATION_URL`: URL do serviço externo (se HTTP)
- `GMAIL_CREDENTIALS_FILE`: Caminho para credentials.json
- `GMAIL_TOKEN_FILE`: Caminho para token.json
- `JOB_BACKEND`: "in_memory" | "redis" | "db"
- `JOB_TIMEOUT_SECONDS`: Timeout padrão (3600s)

---

## 🧪 Testes

### Estrutura de Testes

```
tests/
├── __init__.py
├── test_health.py          # Testes de health check
├── test_echo.py            # Testes de echo
├── test_nfa.py             # Testes NFA (mock)
├── test_nfa_real.py        # Testes NFA (real)
├── test_redesim.py         # Testes REDESIM
├── n8n/                    # Testes de integração n8n
│   ├── test_browser_endpoints.py
│   ├── test_redesim_endpoints.py
│   └── test_utils_endpoints.py
├── nfa/                    # Testes específicos NFA
│   ├── test_data_validator.py
│   └── test_endpoints.py
└── manual/                # Testes manuais/visuais
    ├── nfa_visual_test.py
    └── RELATORIO_TESTE_VISUAL.md
```

### Executar Testes

```bash
# Todos os testes
./scripts/test.sh

# Testes específicos
pytest tests/n8n/
pytest tests/nfa/
```

---

## 📚 Documentação

### Documentos Disponíveis

- `README.md`: Guia rápido de setup e uso
- `docs/ARCHITECTURE_DIAGRAM.md`: Diagramas Mermaid da arquitetura
- `docs/EXPLAINER_FOR_HUMANS.md`: Explicação não-técnica do sistema
- `docs/n8n/README.md`: Guia de integração n8n
- `docs/n8n/REDESIM.md`: Documentação específica REDESIM
- `docs/n8n/NFA.md`: Documentação específica NFA
- `docs/n8n/UTILS.md`: Documentação de utilitários
- `docs/n8n/BROWSER.md`: Documentação de browser automation
- `docs/NFA/OVERVIEW.md`: Visão geral do módulo NFA
- `docs/NFA/API.md`: Documentação da API NFA
- `docs/NFA/FLOWS.md`: Fluxos de trabalho NFA
- `docs/NFA/PLAYWRIGHT.md`: Detalhes de automação Playwright

---

## 🚀 Setup e Execução

### Pré-requisitos

- Python 3.9+
- Virtual environment manager (venv)
- Playwright browsers (instalados via script)

### Instalação

```bash
# 1. Criar venv (fora do projeto)
python3 -m venv ~/Documents/.venvs/fbp
source ~/Documents/.venvs/fbp/bin/activate

# 2. Instalar dependências
pip install -e ".[dev]"

# 3. Setup Playwright
./scripts/setup_playwright.sh

# 4. Iniciar servidor
./scripts/start.sh
```

### Scripts Disponíveis

- `scripts/start.sh`: Inicia servidor em produção
- `scripts/dev.sh`: Modo desenvolvimento (hot reload, DEBUG)
- `scripts/test.sh`: Executa testes (ruff, mypy, pytest)
- `scripts/setup_playwright.sh`: Instala browsers Playwright

---

## 🔌 Integrações

### n8n

Todos os endpoints n8n-compatíveis seguem formato padronizado:

- Prefixo `/api/{module}/`
- Resposta: `{success, data, errors}`
- Documentação em `docs/n8n/`

### LM Studio / AI Agents

- Endpoints REST padrão
- Suporte a job-based async operations
- Health checks para monitoramento

### External Automation Services

- Modo HTTP: Conecta a serviços externos via HTTP
- Modo Local: Executa bibliotecas Python diretamente (futuro)

---

## 📊 Estatísticas do Projeto

### Estrutura de Arquivos

- **Total de módulos Python:** ~50+
- **Routers:** 12
- **Services:** 4
- **Core utilities:** 6
- **Modules:** 3 principais (NFA, REDESIM, Utils)
- **Testes:** 15+ arquivos de teste

### Linhas de Código (Estimativa)

- **Core:** ~500 linhas
- **Modules:** ~3000+ linhas
- **Routers:** ~1000 linhas
- **Services:** ~500 linhas
- **Tests:** ~1000+ linhas
- **Total:** ~6000+ linhas

---

## 🎯 Funcionalidades Principais

### 1. NFA (Nota Fiscal Avulsa)

**Capacidades:**

- Criação de NFA única ou em lote
- Preenchimento automático de formulários ATF
- Validação de dados de entrada
- Retry logic para operações falhas
- Modo visual para inspeção manual
- Suporte a Scenario C completo

**Endpoints:**

- `POST /api/nfa/create`: Criar NFA
- `POST /global/nfa/test`: Teste com dados mínimos
- `POST /global/nfa/test/scenario-c`: Teste completo
- `POST /global/nfa/visual`: Modo visual

### 2. REDESIM

**Capacidades:**

- Extração de emails de processos REDESIM
- Enriquecimento com validação de CEP
- Criação automática de rascunhos Gmail
- Processamento em lote
- Relatórios CSV com timestamps
- Integração com Gmail API

**Endpoints:**

- `POST /api/redesim/extract`: Extrair dados
- `POST /api/redesim/email/create-draft`: Criar rascunho
- `POST /api/redesim/email/send`: Enviar email

### 3. Utils

**Capacidades:**

- Validação de CEP com múltiplas fontes
- Enriquecimento de dados com informações de endereço
- Validação em lote

**Endpoints:**

- `POST /api/utils/cep`: Validar CEP
- `POST /api/utils/cep/batch`: Validação em lote

### 4. Browser

**Capacidades:**

- Captura de HTML de URLs
- Automação via Playwright
- Suporte a CDP (Chrome DevTools Protocol)

**Endpoints:**

- `POST /api/browser/html`: Capturar HTML

---

## 🔄 Job System

### Características

- **Assíncrono:** Jobs executam em background
- **Rastreável:** Cada job tem ID único
- **Timeout:** Limpeza automática de jobs expirados
- **Extensível:** Suporte a Redis/DB no futuro

### API de Jobs

```python
# Criar job
job = job_store.create_job(
    job_type="nfa_create",
    payload={...},
    timeout_seconds=3600
)

# Consultar job
job = job_store.get_job(job_id)

# Listar jobs
jobs = job_store.list_jobs(
    job_type="nfa_create",
    status=JobStatus.RUNNING,
    limit=100
)
```

---

## 🐛 Tratamento de Erros

### Hierarquia de Exceções

```
FBPException (base)
├── ValidationException (400)
├── JobNotFoundException (404)
├── JobConflictException (409)
├── AutomationException (500)
└── ServiceException (500)
```

### Estratégias

- **Validação:** Validação de entrada via Pydantic
- **Retry:** Lógica de retry em operações críticas
- **Logging:** Logging estruturado de todos os erros
- **Graceful Degradation:** Fallbacks quando possível

---

## 📈 Melhorias Futuras

### Planejadas

1. **Job Backend:**

   - Suporte a Redis para jobs distribuídos
   - Persistência em banco de dados

2. **Local Mode:**

   - Implementação de clientes locais (sem HTTP)
   - Integração direta com bibliotecas Python

3. **Monitoramento:**

   - Métricas de performance
   - Dashboard de jobs
   - Alertas de falhas

4. **Testes:**

   - Aumentar cobertura de testes
   - Testes de integração end-to-end
   - Testes de carga

5. **Documentação:**
   - OpenAPI/Swagger completo
   - Exemplos de uso
   - Guias de troubleshooting

---

## 🏁 Conclusão

O **FBP Backend** é um sistema robusto e bem estruturado que serve como hub centralizado para automações. Com arquitetura modular, sistema de jobs assíncrono, e integração n8n, o projeto está preparado para escalar e adicionar novas funcionalidades.

**Pontos Fortes:**

- ✅ Arquitetura limpa e modular
- ✅ Sistema de jobs assíncrono
- ✅ Integração n8n completa
- ✅ Logging estruturado
- ✅ Tratamento de erros robusto
- ✅ Documentação abrangente

**Áreas de Melhoria:**

- 🔄 Job backend distribuído (Redis/DB)
- 🔄 Modo local para automações
- 🔄 Monitoramento e métricas
- 🔄 Cobertura de testes

---

**Relatório gerado automaticamente**
**Última atualização:** 2025-01-XX
