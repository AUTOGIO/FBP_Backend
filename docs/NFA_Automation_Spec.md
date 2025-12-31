# NFA Automation Specification - FIS_308 Consultation

## Overview

This document specifies the automation flow for consulting and downloading NFAs (Notas Fiscais Avulsas) from the ATF/SEFAZ-PB portal using the FIS_308 function.

## Target System

- **Portal**: ATF (Ambiente de Testes Fiscais) / SEFAZ-PB
- **Base URL**: `https://www4.sefaz.pb.gov.br/atf/`
- **Function**: FIS_308 - Consultar Notas Fiscais Avulsas

## Authentication

### Login Form

- **URL**: `https://www4.sefaz.pb.gov.br/atf/`
- **Form Name**: `FormLogin`
- **Fields**:
  - Username: `input[name="edtNoLogin"]`
  - Password: `input[name="edtDsSenha"]`
  - Submit: `button[name="btnAvancar"]` or `input[name="btnAvancar"]`

### Login Flow

1. Navigate to login URL
2. Wait for login form to load
3. Fill username and password fields
4. Submit form (try `logarSistema()` JavaScript function first, fallback to button click)
5. Wait 4 seconds for session to establish

## Navigation to FIS_308

### Function Search Field

- **Selector**: `input[name="edtFuncao"]`
- **Action**: Fill with `"fis_308"` and press Enter
- **Wait**: 3 seconds after navigation

## Consultation Form

### Form Fields

1. **Initial Date** (`edtDtEmissaoNfaeInicial`)

   - Selector: `input[name="edtDtEmissaoNfaeInicial"]`
   - Format: DD/MM/YYYY
   - Example: "08/12/2025"

2. **Final Date** (`edtDtEmissaoNfaeFinal`)

   - Selector: `input[name="edtDtEmissaoNfaeFinal"]`
   - Format: DD/MM/YYYY
   - Example: "10/12/2025"

3. **Employee Registration** (`cmpFuncEmitente`)

   - Default: "1595504"
   - **Primary Method**: Hidden input
     - Selector: `input[name="hidnrMatriculacmpFuncEmitente"]`
   - **Fallback Method**: Component iframe
     - Look for iframe containing "cmpFuncEmitente" in URL
     - Fill text input: `input[type='text']`
     - Optionally click search: `input[type='submit'][value='Pesquisar']`

4. **Submit Button** (`btnConsultar`)
   - Selector: `input[name="btnConsultar"]`
   - Action: Click and wait for navigation

## Results Table

### NFA Selection

- **Radio Buttons**: `input[type='radio']`
- **Selection**: Click first radio button
- **NFA Number Extraction**:
  - Find closest `<tr>` element
  - Extract text from all `<td>` elements
  - Find first text that is all digits and length >= 6

## PDF Downloads

### Download Configuration

- Browser context must have `accept_downloads=True`
- Use `context.expect_event("download")` before clicking download buttons
- Save files to: `/Users/dnigga/Downloads/NFA_Outputs/`

### DANFE Download

- **Button Selectors**:
  - `input[type="button"][value="Imprimir"]`
  - `button:has-text("Imprimir")`
  - `input[name*="Imprimir" i]`
- **Filename**: `NFA_{NUMERO}_DANFE.pdf`

### DAR Download

- **Button Selectors**:
  - `input[type="button"][value*="Taxa Serviço"]`
  - `input[type="button"][value*="Emitir DAR"]`
  - `button:has-text("Emitir DAR")`
  - `button:has-text("Taxa Serviço")`
  - `input[name*="DAR" i]`
- **Filename**: `NFA_{NUMERO}_DAR.pdf`

## Iframe Handling

### Main Content Frame

The main content may be in:

1. Frame with URL containing "FIS\_" or "FISf_ConsultarNotasFiscaisAvulsas"
2. Frame named "IFramePrincipal"
3. Main page itself (no iframe)

### Component Frames

- `cmpFuncEmitente` component may be in a separate iframe
- Check `frame.child_frames` for frames with "cmpFuncEmitente" in URL

## Error Handling

### Retry Logic

- Maximum 2 retries for transient failures (timeouts, delayed rendering)
- Wait 2-3 seconds between retries

### Screenshots

- Save screenshots on errors to: `output/nfa/screenshots/`
- Filenames:
  - `consult_login_start.png`
  - `consult_login_filled.png`
  - `consult_login_success.png`
  - `consult_login_error.png`

### Error Messages

- Clear error messages in job results
- Include context (step, selector, timeout) in error messages

## Logging

### Log File

- Location: `/Users/dnigga/Downloads/NFA_Outputs/nfa_consult_runs.jsonl`
- Format: JSON Lines (one JSON object per line)
- Fields:
  - `status`: "ok" or "error"
  - `nfa_numero`: NFA number found
  - `danfe_path`: Path to DANFE PDF
  - `dar_path`: Path to DAR PDF
  - `started_at`: ISO timestamp
  - `finished_at`: ISO timestamp
  - `error`: Error message (if failed)

## Timeouts

- Login: 60 seconds
- Navigation: 30 seconds
- Form filling: 30 seconds
- Results table: 30 seconds
- Download: 30 seconds per PDF
- Overall job: 600 seconds (10 minutes)

## Response Structure

### Success Response

```json
{
  "status": "ok",
  "nfa_numero": "12345678",
  "danfe_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_12345678_DANFE.pdf",
  "dar_path": "/Users/dnigga/Downloads/NFA_Outputs/NFA_12345678_DAR.pdf",
  "started_at": "2025-12-10T10:00:00.000Z",
  "finished_at": "2025-12-10T10:02:30.000Z",
  "error": null
}
```

### Error Response

```json
{
  "status": "error",
  "nfa_numero": null,
  "danfe_path": null,
  "dar_path": null,
  "started_at": "2025-12-10T10:00:00.000Z",
  "finished_at": "2025-12-10T10:01:00.000Z",
  "error": "Login failed"
}
```

## Implementation Notes

1. **Browser Context**: Always use `accept_downloads=True` when creating browser context
2. **Frame Resolution**: Always resolve main frame before interacting with form elements
3. **Wait Strategies**: Use explicit waits for elements, not fixed timeouts when possible
4. **Date Format**: Always validate date format (DD/MM/YYYY) before submission
5. **Component Handling**: Employee registration component may require iframe navigation
6. **Download Handling**: Always use `expect_event("download")` before clicking download buttons

## Testing Checklist

- [ ] Login with valid credentials
- [ ] Navigate to FIS_308 function
- [ ] Fill consultation form with valid dates
- [ ] Submit form and wait for results
- [ ] Select first NFA from table
- [ ] Download DANFE PDF
- [ ] Download DAR PDF
- [ ] Verify files saved with correct names
- [ ] Handle case with no results
- [ ] Handle login failures
- [ ] Handle timeout scenarios
- [ ] Verify iframe resolution works
- [ ] Test component iframe fallback
