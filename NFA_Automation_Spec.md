# NFA Automation — Full Technical Specification
### SEFAZ-PB – ATF Portal (FIS_308)

This document defines, passo a passo, o fluxo completo para automatizar a consulta e a emissão de PDFs de **Notas Fiscais Avulsas (NFA)** no sistema **ATF / SEFAZ-PB**, usando Playwright e seguindo boas práticas.

Ele foi pensado para ser usado:

- Como documentação humana;
- Como contexto de referência para **Cursor_AI** (USER_RULES / PROJECT_RULES / docs);
- Como base para gerar/agregar código Playwright.

---

## 1. Escopo da Automação

Fluxo completo que o agente deve executar:

1. Abrir o portal ATF: `https://www4.sefaz.pb.gov.br/atf/`  
2. Fazer **login** com usuário/senha (formulário `FormLogin`).  
3. Usar o campo de função para navegar até **FIS_308 – Consultar Notas Fiscais Avulsas** (`edtFuncao = "fis_308"`).  
4. Na tela de consulta:
   - Informar **Data de Emissão Inicial** e **Final**;
   - Informar **Matrícula do Funcionário Emitente**;
   - Acionar **Consultar**.
5. Na lista de NFAs:
   - Selecionar uma linha (radio button);
   - Clicar em **Imprimir** → abre PDF da NFA (DANFE);
   - Clicar em **Emitir DAR** ou **Emitir Taxa Serviço** → abre PDF do DAR.
6. Fazer download dos dois PDFs e salvar em:

   ```text
   /Users/dnigga/Downloads/NFA_Outputs
   ```

   com nomes previsíveis, por exemplo:

   ```text
   NFA_900500381_DANFE.pdf
   NFA_900500381_DAR.pdf
   ```

---

## 2. Login – Página Inicial

### 2.1 URL

```text
https://www4.sefaz.pb.gov.br/atf/
```

### 2.2 Estrutura do formulário

Trechos relevantes do HTML da tela de login:

```html
<form id="loginForm" class="needs-validation" novalidate name="FormLogin" method="post" action="../seg/SEGf_Login.jsp">
  <input type="hidden" name="lembrarSenha">
  <input type="hidden" name="gerarSenha">
  <input type="hidden" name="pegarEmail">
  <input type="hidden" name="hidNoLogin" value="">
  <input type="hidden" name="hidDsSenha">
  <input type="hidden" name="hidLogin">
  <input type="hidden" name="hidAcao">
  ...
  <input type="text" name="edtNoLogin" id="login" placeholder="Usuário" ...>
  <input type="password" name="edtDsSenha" id="senha" placeholder="Senha" ...>
  <button type="submit" name="btnAvancar" class="btn btn-primary ...">Avançar</button>
</form>
```

### 2.3 Selectors importantes

- Usuário: `input[name="edtNoLogin"]` (também `#login`)
- Senha: `input[name="edtDsSenha"]` (também `#senha`)
- Botão: `button[name="btnAvancar"]`

A lógica de login chama a função JS `logarSistema()` e posta o formulário para `SEGf_Login.jsp`, definindo `hidLogin` / `hidAcao`. Para automação, basta submeter o form normalmente.

### 2.4 Passos para o agente

1. `page.goto("https://www4.sefaz.pb.gov.br/atf/")`
2. `await page.fill('input[name="edtNoLogin"]', USERNAME)`
3. `await page.fill('input[name="edtDsSenha"]', PASSWORD)`
4. `await Promise.all([page.waitForNavigation(), page.click('button[name="btnAvancar"]')])`

Após isso, o ATF carrega a página principal com:
- Menu lateral (à esquerda)
- Barra superior com campo de função
- Mensagem “Seja bem-vindo, EDUARDO FORSTER GIOVANNINI”

---

## 3. Navegar para a Função FIS_308

Na barra azul superior existe um campo de busca de função, onde você digita `fis_308`.

Trecho do HTML (simplificado) da barra de função:

```html
<input type="search" name="edtFuncao" ... />
```

### 3.1 Selector do campo da função

- `input[name="edtFuncao"]`

### 3.2 Passos

1. Esperar o campo aparecer:
   ```ts
   await page.waitForSelector('input[name="edtFuncao"]');
   ```
2. Preencher e pressionar Enter:
   ```ts
   await page.fill('input[name="edtFuncao"]', 'fis_308');
   await page.keyboard.press('Enter');
   ```
3. Aguardar o carregamento da tela “Consultar Notas Fiscais Avulsas” dentro do conteúdo principal.

> Observação: em algumas instalações o conteúdo é carregado em um iframe (por exemplo `name="IFramePrincipal"`). O agente deve detectar se a tela de consulta está em um frame e, se sim, operar através dele.

---

## 4. Tela “Consultar Notas Fiscais Avulsas” (FIS_308)

O formulário principal dessa tela se chama:

```html
<form name="frmConsultar" action="../fis/FISf_ConsultarNotasFiscaisAvulsas.do" method="post" onSubmit="return validaFormConsultar();">
```

### 4.1 Campos de Data de Emissão

```html
<input type="text" name="edtDtEmissaoNfaeInicial" class="caixas" size="12" value="" maxlength="10" title="Data de Emissão Inicial" alt="VALIDA_DATA">
<input type="text" name="edtDtEmissaoNfaeFinal"   class="caixas" size="12" value="" maxlength="10" title="Data de Emissão Final"   alt="VALIDA_DATA">
```

Selectors:

- Data inicial: `input[name="edtDtEmissaoNfaeInicial"]`
- Data final: `input[name="edtDtEmissaoNfaeFinal"]`

Formato: `dd/mm/aaaa`.

### 4.2 Funcionário Emitente – Matrícula

O bloco “Funcionário Emitente” é montado via iframe:

```html
<iframe class="cmpWrapper" frameborder="0" name="cmpFuncEmitente" scrolling="no" width="600" height="100" src="../componentes/CodDescLst.jsp?id=FISf_ConsultarNotasFiscaisAvulsas_cmpFuncEmitente"></iframe>

<input type="hidden" name="hidnrMatriculacmpFuncEmitente" value="">
<input type="hidden" name="hidnoHumanocmpFuncEmitente" value="">
<input type="hidden" name="hidsqFuncionariocmpFuncEmitente">
```

Na prática, ao interagir com o componente, o sistema preenche o hidden `hidnrMatriculacmpFuncEmitente` com a matrícula (`1595504` no exemplo).

Existem duas abordagens:

1. **Abordagem “componente”** (mais próxima do usuário):  
   - Entrar no iframe `cmpFuncEmitente`  
   - Preencher o campo de matrícula visível  
   - Acionar o botão “Pesquisar” interno  
   - O JS do componente atualiza os hiddens no `frmConsultar` do frame pai.

2. **Abordagem direta** (mais simples, mas menos “humana”):  
   - Setar diretamente o hidden no formulário principal:
     ```js
     document.frmConsultar.hidnrMatriculacmpFuncEmitente.value = "1595504";
     ```

Para robustez, recomenda-se a abordagem **(1)**.

### 4.3 Botão “Consultar”

Trecho:

```html
<input  type="hidden" name="hidHistorico" value="">
<input  type="hidden" name="hidAcao" value="">
...
<input name="btnConsultar" type="submit" class="botoes" value="Consultar" onClick="frmConsultar.hidAcao.value = 'consultar';">
<input name="btnLimpar"    type="submit" class="botoes" value="Limpar"     onClick="frmConsultar.hidAcao.value = 'limpar';">
```

Selector:

- `input[name="btnConsultar"][type="submit"]`

### 4.4 Fluxo completo da tela de consulta

Ordem recomendada:

1. (Se a tela estiver em iframe) obter `frame = page.frame({ name: "IFramePrincipal" })` ou outro nome equivalente.  
2. Dentro do frame, preencher datas:
   - `edtDtEmissaoNfaeInicial = "08/12/2025"`
   - `edtDtEmissaoNfaeFinal   = "10/12/2025"`
3. Preencher componente de Funcionário Emitente:
   - Entrar no iframe `cmpFuncEmitente`;
   - Preencher matrícula (`1595504`) no campo de matrícula interno;
   - Clicar em `Pesquisar`;
   - Voltar ao frame principal da consulta.
4. Clicar em **Consultar**.
5. Aguardar carregamento da tabela de resultados.

---

## 5. Tabela de Resultados – Seleção da NFA

Após o submit, a mesma tela passa a exibir uma tabela com as NFAs encontradas.  
Cada linha geralmente contém, entre outras colunas:

- Radio button para seleção
- Número da NFA
- Série
- Data de Emissão
- Emitente
- Situação
- Valor

No HTML, os radios são algo como:

```html
<input type="radio" name="rdbNFAe" value="...">
```

ou, em alguns casos, outro `name` (como `rdbNotaFiscal`). A lógica JS define arrays como `arrayNFe` para mapear radio → chave de acesso.

### 5.1 Estratégias de seleção

1. **Primeira NFA da lista**  
   - Simples: selecionar `page.locator('input[type="radio"][name="rdbNFAe"]').first()`.

2. **NFA por número específico**  
   - Ler todas as linhas (`<tr>`) do corpo da tabela;  
   - Encontrar a coluna onde o texto é o número desejado (ex.: `900500381`);  
   - Dentro da mesma linha, localizar e clicar o radio.

### 5.2 Regras

- Sempre garantir que **apenas uma NFA** está selecionada.  
- Se nenhuma NFA for encontrada, o agente deve logar erro e encerrar com mensagem clara.

---

## 6. Botões de Ação: Imprimir & Emitir DAR / Taxa de Serviço

Na parte inferior da tabela há uma barra de botões, incluindo:

```html
<input name="btnImprimir"       type="button" class="botoes" value="Imprimir"         onClick="tratarAcao('imprimir');">
<input name="btnEmitirDar"      type="button" class="botoes" value="Emitir DAR"      onClick="tratarAcao('emitirDar');">
<input name="btnEmitirTaxaServ" type="button" class="botoes" value="Emitir Taxa Serviço" onClick="tratarAcao('emitirTaxaServico');">
```

> Os nomes exatos (`name` / `value`) podem variar um pouco por versão, mas os valores (`value`) são estáveis: **"Imprimir"**, **"Emitir DAR"**, **"Emitir Taxa Serviço"**, etc.

### 6.1 Ação “Imprimir” – DANFE

`tratarAcao('imprimir')` ajusta o formulário `frmDetalhar` e abre:

```html
document.frmDetalhar.target = 'ImprimirNotaFiscalAvulsa';
document.frmDetalhar.action = '../fis/FISf_ImprimirNotasFiscaisAvulsas.do';
```

Na prática: um **novo tab/janela** é aberto com o PDF da NFA (DANFE).

### 6.2 Ação “Emitir DAR” / “Emitir Taxa Serviço”

Quando a NFA é do tipo correto, a ação:

```js
tratarAcao('emitirDar')  // ou 'emitirTaxaServico'
```

ajusta o `frmDetalhar` e abre outro alvo:

```html
document.frmDetalhar.target = 'emissaoDARImpostoNFA';
```

ALVO: PDF do DAR (boleto/taxa).

### 6.3 Passos para o agente Playwright

1. Garantir que uma NFA está selecionada.  
2. Preparar `waitForEvent("page")` ou `waitForEvent("download")` ANTES de clicar.  
3. Clicar no botão **Imprimir**; capturar o PDF.  
4. Voltar à aba principal (se necessário).  
5. Repetir o processo para **Emitir DAR / Emitir Taxa Serviço**.

---

## 7. Tratando os PDFs e Salvando Arquivos

### 7.1 Diretório de saída

O diretório **deve existir**:

```bash
mkdir -p /Users/dnigga/Downloads/NFA_Outputs
```

### 7.2 Convenção de nomes

Recomendação:
- DANFE:

  ```text
  NFA_{NUMERO}_DANFE.pdf
  ```

- DAR:

  ```text
  NFA_{NUMERO}_DAR.pdf
  ```

Exemplo:

```text
/Users/dnigga/Downloads/NFA_Outputs/NFA_900500381_DANFE.pdf
/Users/dnigga/Downloads/NFA_Outputs/NFA_900500381_DAR.pdf
```

Se não for possível extrair o número diretamente do DOM, usar fallback:

```text
NFA_DANFE_{timestamp}.pdf
NFA_DAR_{timestamp}.pdf
```

### 7.3 Boas práticas com Playwright (downloads)

- Criar o browser/contexto com `acceptDownloads: true`.  
- Para cada ação que gera PDF:

  ```ts
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    botao.click(),
  ]);

  const suggested = download.suggestedFilename();
  await download.saveAs(`/Users/dnigga/Downloads/NFA_Outputs/${nomeFinal}`);
  ```

- Se, em vez de download direto, abrir uma aba com viewer de PDF:  
  - Usar `context.waitForEvent('page')`,  
  - Buscar a response `application/pdf`,  
  - Fazer `response.body()` e gravar em arquivo manualmente.

---

## 8. Tratamento de Erros e Robustez

### 8.1 Situações previstas

- Falha no login (credenciais inválidas);
- Timeout no carregamento da tela FIS_308;
- Nenhuma NFA retornada na consulta;
- Botões de ação desabilitados (NFA em status que não permite emissão);
- Download não iniciado dentro do timeout.

### 8.2 Comportamento desejado do agente

- Nunca entrar em loop infinito.  
- Sempre logar:
  - Hora,
  - URL atual,
  - Passo onde falhou,
  - Mensagem de erro.

- Tentar no máximo **N** retentativas configuráveis (ex.: 2) para:
  - clique em botões,
  - espera de carregamento de tabela.

- Em caso de erro crítico, retornar um relatório JSON, por exemplo:

```json
{
  "status": "error",
  "step": "emitir_dar",
  "message": "Timeout waiting for download",
  "nfa_numero": "900500381"
}
```

---

## 9. Resumo do Fluxo Operacional

1. `goto` → página de login ATF.  
2. Preencher `edtNoLogin`, `edtDsSenha`; clicar **Avançar**; aguardar home.  
3. Preencher campo `edtFuncao` com `fis_308`; pressionar Enter; aguardar tela de consulta.  
4. Na tela de consulta:
   - Preencher `edtDtEmissaoNfaeInicial` e `edtDtEmissaoNfaeFinal`;
   - Preencher/marcar matrícula do Funcionário Emitente (`1595504`);
   - Clicar **Consultar**.
5. Na lista de NFAs:
   - Selecionar linha desejada (radio);
6. Clicar **Imprimir** → capturar download PDF DANFE → salvar como `NFA_{numero}_DANFE.pdf`.  
7. Clicar **Emitir DAR** / **Emitir Taxa Serviço** → capturar download DAR → salvar como `NFA_{numero}_DAR.pdf`.  
8. Garantir que ambos arquivos existem em `/Users/dnigga/Downloads/NFA_Outputs`.  
9. Retornar log/JSON de sucesso com:
   - número da NFA,
   - caminhos dos PDFs,
   - hora de execução.

---

## 10. Uso com Cursor_AI

Quando esta especificação for usada como contexto em Cursor:

- O agente deve:
  - Respeitar rigorosamente os selectors e o caminho de saída;
  - Implementar automação usando **Playwright**;
  - Usar **código idempotente**: várias execuções não devem corromper o sistema;
  - Nunca alterar configurações globais do macOS do usuário;
  - Produzir logs claros quando ajustar seletores ou tratamento de iframes.

- Recomenda-se colocar este arquivo em:
  - `/docs/NFA_Automation_Spec.md` ou
  - `/.cursor/rules/NFA_ATF_RULES.md`

e referenciá-lo nos USER_RULES / PROJECT_RULES.

---

_Fim do documento – NFA_Automation_Spec.md_
