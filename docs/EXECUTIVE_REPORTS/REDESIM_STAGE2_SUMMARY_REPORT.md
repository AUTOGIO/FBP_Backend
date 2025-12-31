# REDESIM Stage 2 Automation - Summary Report

**Data:** Janeiro 2025  
**Projeto:** FBP Backend - REDESIM Automation  
**Status:** ✅ Implementado e Funcional

---

## 📋 Visão Geral

Implementação completa da automação **Stage 2** do sistema REDESIM, que processa resultados de consultas, extrai dados de processos, valida informações e cria rascunhos de e-mail no Gmail automaticamente.

### Objetivo Principal
Automatizar o processamento em lote de processos REDESIM encontrados em consultas, extraindo informações relevantes e criando rascunhos de e-mail padronizados para comunicação com contribuintes.

---

## 🎯 Funcionalidades Implementadas

### 1. **Processamento em Lote de Resultados**
- ✅ Processa **todos os processos** encontrados em uma consulta REDESIM
- ✅ Navegação automática entre processos (volta para lista após cada processamento)
- ✅ Controle de estado persistente para retomada após interrupções
- ✅ Validação de duplicatas (evita reprocessar o mesmo processo)

### 2. **Extração de Dados**
- ✅ Extração de e-mails dos processos (frame FC)
- ✅ Extração de dados do processo (número, razão social, etc.)
- ✅ Validação de CEP via API ViaCEP
- ✅ Verificação de CPF do contabilista via site CFC

### 3. **Integração com Gmail**
- ✅ Criação automática de rascunhos no Gmail
- ✅ OAuth 2.0 com escopo mínimo (`gmail.compose`)
- ✅ Assunto formatado: "Número do processo: {num} - Razão Social: {name}"
- ✅ Corpo do e-mail padronizado com solicitação de documentos
- ✅ Suporte a múltiplos destinatários

### 4. **Persistência e Logging**
- ✅ Salva resultados em JSON (`output/redesim_stage2_results_{timestamp}.json`)
- ✅ Logging estruturado com níveis apropriados
- ✅ Estado de iteração persistido para retomada
- ✅ Relatórios de sucesso/falha por processo

---

## 📁 Arquivos Criados/Modificados

### Scripts de Execução

#### 1. `scripts/run_redesim_stage2_only.py` ⭐ **NOVO**
**Propósito:** Processa apenas Stage 2, conectando-se a uma sessão de browser já aberta.

**Características:**
- Não requer login (assume que usuário já está logado)
- Não requer submissão de formulário (assume que resultados já estão visíveis)
- Conecta-se ao browser persistente existente
- Processa **todos os resultados** encontrados na página
- Ideal para uso após consulta manual

**Uso:**
```bash
cd /Users/dnigga/Documents/FBP_Backend
.venv/bin/python scripts/run_redesim_stage2_only.py
```

#### 2. `scripts/run_redesim_stage2.py`
**Propósito:** Execução completa incluindo login e consulta.

**Características:**
- Requer variáveis de ambiente `ATF_USERNAME` e `ATF_PASSWORD`
- Faz login automático
- Executa consulta REDESIM
- Processa Stage 2 para o primeiro resultado

#### 3. `scripts/run_redesim_consulta.py`
**Propósito:** Script principal que executa consulta completa + Stage 2 em lote.

**Características:**
- Login automático
- Consulta REDESIM com parâmetros configuráveis
- Processa **todos os resultados** em sequência
- Cria rascunhos Gmail para cada processo
- Relatório final com estatísticas

#### 4. `scripts/run_redesim_stage2_visual.sh`
**Propósito:** Launcher visual com prompts interativos.

**Características:**
- Solicita credenciais se não estiverem em variáveis de ambiente
- Abre browser em modo visível
- Execução completa com feedback visual

### Módulos Principais

#### `app/modules/cadastro/consultar_redesim.py`
**Função Principal:** `process_redesim_stage2()`

**Fluxo de Execução:**

1. **Carregamento de Estado**
   - Carrega estado persistente da iteração
   - Valida índice atual vs. total de processos

2. **Resolução de Iframe**
   - Resolve iframe `principal` explicitamente (crítico)
   - Aguarda carregamento completo da página

3. **Coleta de Radio Buttons**
   - Coleta todos os radio buttons do iframe
   - Usa índice determinístico (não depende de valores)

4. **Seleção de Processo**
   - Seleciona radio button por índice
   - Valida sincronização de campos hidden
   - Evita duplicatas (verifica último processado)

5. **Submissão de Formulário**
   - Clica no botão "Detalhar" ou pressiona Enter
   - Aguarda navegação para página de detalhes

6. **Extração de Dados**
   - Extrai e-mails da página de detalhes
   - Extrai dados do processo (número, razão social, etc.)

7. **Criação de Rascunho Gmail**
   - Inicializa GmailService com credenciais
   - Cria rascunho com assunto e corpo formatados
   - Retorna ID do rascunho criado

8. **Persistência de Resultados**
   - Salva resultados em JSON
   - Atualiza estado de iteração

---

## 🔧 Melhorias Técnicas Implementadas

### 1. **Gerenciamento de Estado Robusto**
```python
# Estado persistido em arquivo JSON
state = {
    "current_index": 0,
    "total": None,
    "last_processed_value": None,
    "timestamp": "2025-01-XX..."
}
```

**Benefícios:**
- Retomada após crash/interrupção
- Prevenção de duplicatas
- Rastreamento de progresso

### 2. **Resolução Explícita de Iframe**
```python
principal_frame = await _resolve_principal_iframe(page, timeout=FAST_TIMEOUT)
```

**Problema Resolvido:**
- Radio buttons estão dentro de iframe `principal`
- Resolução explícita garante acesso correto aos elementos
- Timeouts configuráveis para diferentes operações

### 3. **Sincronização de Campos Hidden**
```python
hidden_field_updated = await _wait_for_hidden_field_sync(
    principal_frame, radio_value, timeout=ELEMENT_TIMEOUT * 2
)
```

**Problema Resolvido:**
- Sistema REDESIM usa campos hidden atualizados por JavaScript
- Aguarda sincronização antes de submeter formulário
- Valida que campo `hidNrProcesso` foi atualizado corretamente

### 4. **Navegação Robusta Entre Processos**
```python
# Tenta go_back() primeiro (mais rápido)
try:
    await page.go_back(wait_until="domcontentloaded", timeout=FAST_TIMEOUT)
except Exception:
    # Fallback: navegação direta para URL de resultados
    results_url = "https://www4.sefaz.pb.gov.br/atf/cad/CADf_ConsultarProcessosREDESIM2.do"
    await page.goto(results_url, wait_until="domcontentloaded", timeout=FAST_TIMEOUT)
```

**Benefícios:**
- Fallback automático se `go_back()` falhar
- Validação de retorno à lista de resultados
- Aguarda carregamento completo antes de próxima iteração

### 5. **Integração Gmail com Escopo Mínimo**
```python
# Escopo mínimo: apenas compose (criar rascunhos)
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
```

**Segurança:**
- Não requer acesso a leitura de e-mails
- Não pode enviar e-mails automaticamente
- Apenas criação de rascunhos (requer aprovação manual)

---

## 📊 Estrutura de Resultados

### JSON de Saída
```json
{
  "timestamp": "2025-01-XXT...",
  "success": true,
  "steps": {
    "process_selection": {
      "success": true,
      "row_index": 0,
      "radio_value": "123456"
    },
    "email_extraction": {
      "emails": ["email1@example.com", "email2@example.com"],
      "count": 2
    },
    "process_data": {
      "processo_numero": "123456",
      "razao_social": "Empresa Exemplo LTDA",
      ...
    },
    "gmail_draft": {
      "success": true,
      "draft_id": "r1234567890",
      "message_id": "msg1234567890"
    }
  },
  "errors": [],
  "output_file": "/path/to/output/redesim_stage2_results_20250101_120000.json"
}
```

---

## 🚀 Como Usar

### Modo 1: Processamento Completo (Login + Consulta + Stage 2)
```bash
export ATF_USERNAME="seu_usuario"
export ATF_PASSWORD="sua_senha"

cd /Users/dnigga/Documents/FBP_Backend
PYTHONPATH=/Users/dnigga/Documents/FBP_Backend python3 scripts/run_redesim_consulta.py
```

### Modo 2: Stage 2 Apenas (Browser Já Aberto)
```bash
# 1. Abra browser manualmente e faça login no ATF
# 2. Execute consulta REDESIM e veja resultados
# 3. Execute Stage 2:

cd /Users/dnigga/Documents/FBP_Backend
.venv/bin/python scripts/run_redesim_stage2_only.py
```

### Modo 3: Launcher Visual Interativo
```bash
cd /Users/dnigga/Documents/FBP_Backend
./scripts/run_redesim_stage2_visual.sh
```

---

## ⚙️ Configuração

### Credenciais Gmail
**Localização Padrão:**
- Credenciais: `credentials/gmail_credentials.json`
- Token: `credentials/gmail_token.json`

**Primeira Execução:**
- Token será criado automaticamente via OAuth flow
- Browser será aberto para autorização
- Token será salvo para reutilização

### Variáveis de Ambiente
```bash
# ATF (obrigatório para modo completo)
export ATF_USERNAME="seu_usuario"
export ATF_PASSWORD="sua_senha"

# Gmail (opcional - usa caminhos padrão se não definido)
export GMAIL_CREDENTIALS_PATH="/path/to/credentials.json"
export GMAIL_TOKEN_PATH="/path/to/token.json"
```

---

## 📈 Estatísticas e Relatórios

### Relatório Final (Console)
```
======================================================================
📊 Stage 2 Summary:
   Total processes: 15
   Successful drafts: 14
   Failed drafts: 1
   Success rate: 93.3%
======================================================================
```

### Arquivos de Saída
- **JSON Results:** `output/redesim_stage2_results_{timestamp}.json`
- **Logs:** `logs/server.log` (com logging estruturado)

---

## 🔍 Troubleshooting

### Problema: Radio buttons não encontrados
**Solução:**
- Verifique se está na página de resultados correta
- Aguarde carregamento completo da página
- Verifique se iframe `principal` está carregado

### Problema: Navegação falha entre processos
**Solução:**
- Script tem fallback automático (navegação direta)
- Verifique conectividade com site ATF
- Aumente timeouts se necessário

### Problema: Gmail draft não criado
**Solução:**
- Verifique se credenciais Gmail estão corretas
- Verifique se token OAuth é válido
- Verifique se e-mails foram extraídos (pode não haver e-mails no processo)

### Problema: Processo duplicado processado
**Solução:**
- Sistema detecta duplicatas automaticamente
- Verifique estado persistente em `output/iteration_state.json`
- Limpe estado se necessário para reprocessar

---

## ✅ Validações e Testes

### Testes Implementados
- ✅ `tests/test_redesim_stage2.py` - Testes unitários
- ✅ `scripts/test_stage2_automation.py` - Testes de componentes
- ✅ `scripts/test_redesim_gmail_draft.py` - Teste de criação de rascunho

### Validações em Produção
- ✅ Processamento em lote de 15+ processos
- ✅ Criação de rascunhos Gmail funcionando
- ✅ Navegação entre processos estável
- ✅ Prevenção de duplicatas funcionando

---

## 🎯 Próximos Passos Sugeridos

1. **Melhorias de Performance**
   - Paralelização de processamento (com cuidado para não sobrecarregar servidor)
   - Cache de validações (CEP, CPF)

2. **Melhorias de UX**
   - Dashboard web para acompanhamento de processamento
   - Notificações quando processamento completo

3. **Integração n8n/Node-RED**
   - Endpoints REST para trigger externo
   - Webhooks para notificações

4. **Monitoramento**
   - Métricas de sucesso/falha
   - Alertas para erros críticos

---

## 📝 Notas Técnicas

### Timeouts Configurados
```python
FAST_TIMEOUT = 10000  # 10s para operações rápidas
ELEMENT_TIMEOUT = 30000  # 30s para elementos críticos
FAST_DEFAULT_DELAY = 300  # 300ms delay padrão
FAST_SEARCH_DELAY = 500  # 500ms para operações de busca
```

### Browser Persistente
- Usa `launch_persistent_browser()` para manter sessão
- Browser permanece aberto por 1 hora após processamento
- Permite inspeção manual dos resultados

### Logging Estruturado
- Logs com prefixo `cadastro_redesim: Stage 2`
- Níveis: INFO, WARNING, ERROR
- Inclui contexto detalhado para debugging

---

## 🏆 Conclusão

A implementação do **REDESIM Stage 2** está completa e funcional, permitindo:

✅ Processamento automatizado em lote de processos REDESIM  
✅ Extração automática de dados e e-mails  
✅ Criação automática de rascunhos Gmail padronizados  
✅ Navegação robusta entre processos  
✅ Prevenção de duplicatas e retomada após interrupções  
✅ Logging e persistência completos  

O sistema está pronto para uso em produção e pode ser facilmente integrado com workflows n8n/Node-RED conforme necessário.

---

**Documentado por:** K.K.  
**Data:** Janeiro 2025  
**Versão:** 1.0

