# ATF System Explorer - Advanced Version

Sistema avançado de exploração do ATF (Ambiente de Testes Fiscais) da SEFAZ-PB, implementando as melhores práticas de web crawling e análise de sistemas.

## 🎯 Características Principais

### ✅ Melhores Práticas Implementadas

1. **Exploração Recursiva Profunda**

   - Navegação automática por múltiplos níveis de profundidade
   - Controle de profundidade máxima configurável
   - Limite de páginas por nível para evitar sobrecarga

2. **Rate Limiting e Crawling Respeitoso**

   - Delays configuráveis entre requisições
   - Respeito aos limites do servidor
   - Prevenção de sobrecarga do sistema ATF

3. **Tratamento Robusto de Erros**

   - Retry logic com múltiplas tentativas
   - Tratamento específico de timeouts
   - Logging detalhado de erros
   - Continuidade mesmo com falhas pontuais

4. **Extração Estruturada de Dados**

   - Type hints completos (Python 3.11+)
   - Dataclasses para estruturas de dados
   - Classificação automática de tipos de página
   - Extração detalhada de formulários, campos, tabelas

5. **Rastreamento de Progresso**

   - Estatísticas em tempo real
   - Contadores por tipo de página
   - Contadores por profundidade
   - Tempo de carregamento por página

6. **Gerenciamento de Configuração**

   - Arquivo YAML de configuração
   - Valores padrão sensatos
   - Override via parâmetros

7. **Detecção de Padrões**

   - Identificação de padrões de URL
   - Análise de padrões de formulários
   - Priorização inteligente de URLs

8. **Filtros e Priorização**

   - URLs a serem ignoradas (skip patterns)
   - URLs prioritárias (priority patterns)
   - Classificação automática de links

9. **Geração de Relatórios**

   - JSON estruturado completo
   - Relatório Markdown legível
   - Estatísticas consolidadas
   - Análise de padrões descobertos

10. **Screenshots Automáticos**
    - Captura em pontos críticos
    - Organização por timestamp
    - Debug visual facilitado

## 📋 Requisitos

```bash
pip install playwright pyyaml
playwright install chromium
```

## 🚀 Uso Básico

```bash
# Execução simples
python3 ops/atf_system_explorer_advanced.py

# Com configuração customizada
# Edite ops/atf_explorer_config.yaml primeiro
python3 ops/atf_system_explorer_advanced.py
```

## ⚙️ Configuração

Edite `ops/atf_explorer_config.yaml` para personalizar:

```yaml
exploration:
  max_depth: 5 # Profundidade máxima
  max_pages_per_depth: 50 # Limite por nível
  rate_limit_delay: 1.0 # Delay entre requisições
  request_timeout: 30000 # Timeout em ms
  max_retries: 3 # Tentativas de retry
  retry_delay: 2.0 # Delay entre retries

filters:
  skip_patterns: # URLs a ignorar
    - "logout"
    - "timeout"
    - ".pdf"

  priority_patterns: # URLs prioritárias
    - "nfa"
    - "nota"
    - "fiscal"
```

## 📊 Estrutura de Dados

### PageInfo

Informações completas sobre cada página explorada:

- URL, título, timestamp
- Tipo de página (LOGIN, MENU, FORM, LIST, etc.)
- Status de exploração
- Formulários e campos
- Tabelas e botões
- Links descobertos
- Iframes detectados
- Tempo de carregamento
- Screenshot path

### LinkInfo

Informações estruturadas sobre links:

- Texto, URL, título
- Tipo (internal, external, javascript, anchor)
- Contexto de descoberta
- Profundidade e URL pai

### FormField

Informações detalhadas sobre campos de formulário:

- Tipo, nome, ID
- Label, placeholder
- Required, value
- Opções (para selects)

## 📈 Estatísticas Geradas

O script gera estatísticas completas:

- Total de páginas descobertas/exploradas
- Total de links descobertos
- Total de formulários encontrados
- Total de erros
- Duração total
- Distribuição por tipo de página
- Distribuição por profundidade
- Padrões de URL detectados
- Padrões de formulários detectados

## 📁 Output

### Arquivos Gerados

1. **JSON Completo**: `atf_exploration_advanced_TIMESTAMP.json`

   - Todos os dados estruturados
   - Informações completas de cada página
   - Links e padrões descobertos

2. **Relatório Markdown**: `atf_exploration_advanced_TIMESTAMP.md`

   - Resumo legível
   - Estatísticas consolidadas
   - Análise de padrões

3. **Screenshots**: `output/atf_exploration/*.png`
   - Screenshots de cada página explorada
   - Screenshots de login
   - Screenshots de erros

## 🔍 Funcionalidades Avançadas

### Classificação Automática de Páginas

O sistema classifica automaticamente páginas em:

- **LOGIN**: Páginas de autenticação
- **MENU**: Menus de navegação
- **FORM**: Formulários de entrada
- **LIST**: Listagens/consultas
- **DETAIL**: Detalhes de registros
- **DOCUMENT**: Documentos/PDFs
- **UNKNOWN**: Não classificado

### Detecção de Padrões

- **Padrões de URL**: Identifica padrões comuns (ex: `/atf/fis/FISf_*.do`)
- **Padrões de Formulário**: Agrupa formulários por action
- **Análise de Links**: Classifica links por tipo

### Priorização Inteligente

URLs são priorizadas baseado em:

- Padrões de prioridade configurados
- Tipo de página
- Profundidade
- Número de links descobertos

## 🛡️ Segurança e Boas Práticas

1. **Rate Limiting**: Respeita o servidor com delays configuráveis
2. **Timeout Handling**: Tratamento adequado de timeouts
3. **Error Recovery**: Continua exploração mesmo com erros pontuais
4. **Resource Management**: Fechamento adequado de recursos
5. **Logging Estruturado**: Logs detalhados para debugging
6. **Type Safety**: Type hints completos para manutenibilidade

## 📝 Exemplo de Uso Programático

```python
from ops.atf_system_explorer_advanced import ATFSystemExplorerAdvanced

explorer = ATFSystemExplorerAdvanced(
    max_depth=3,
    rate_limit=2.0,
    max_pages_per_depth=20,
)

results = await explorer.run_exploration()
explorer.save_results(results)
```

## 🔧 Troubleshooting

### Login Falha

- Verifique credenciais em `atf_explorer_config.yaml`
- Verifique screenshots de login para debug
- Aumente `retry_delay` se necessário

### Timeouts Frequentes

- Aumente `request_timeout` no config
- Reduza `rate_limit_delay` (com cuidado)
- Verifique conectividade

### Muitas Páginas

- Reduza `max_depth`
- Reduza `max_pages_per_depth`
- Adicione mais `skip_patterns`

## 📚 Arquitetura

```
ATFSystemExplorerAdvanced
├── Configuration Management
├── Rate Limiting
├── Login Handler (with retry)
├── Page Explorer (recursive)
│   ├── Link Extractor
│   ├── Form Extractor
│   ├── Pattern Detector
│   └── Screenshot Manager
├── Statistics Tracker
└── Report Generator
```

## 🎯 Casos de Uso

1. **Mapeamento Completo do Sistema**: Descobrir todas as funcionalidades
2. **Análise de Formulários**: Extrair estrutura de formulários
3. **Detecção de Padrões**: Identificar padrões de URL e navegação
4. **Documentação Automática**: Gerar documentação do sistema
5. **Testes de Integração**: Base para testes automatizados

## 📄 Licença

MIT

## 🤝 Contribuições

Melhorias são bem-vindas! Foque em:

- Performance
- Robustez
- Documentação
- Type safety
