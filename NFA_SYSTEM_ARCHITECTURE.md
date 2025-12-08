# 🏢 NFA System Architecture & Integration Guide

**Reference**: For NFA_AUTOMATION_SPECIALIST_AI  
**Status**: ✅ Production-Ready Architecture  
**Version**: 2.0  
**Location**: `/Users/dnigga/Documents/FBP_Backend`

---

## 📊 System Overview

```
┌──────────────────────────────────────────┐
│  NFA_AUTOMATION_SPECIALIST_AI (You)                    │
│  Responsibility: Stability, Reliability, Zero Regressions │
└──────────────────────────────────────────┘
                                ↑
                      Owns & Maintains
                                ↑
┌──────────────────────────────────────────┐
│           FBP BACKEND (FastAPI)                         │
│                                                           │
│  ┌──────────────────────────────────┐  │
│  │ app/modules/nfa/ (17 core modules)           │  │
│  │                                                │  │
│  │ 🔑 atf_login.py                               │  │
│  │    └─ LOGIN PIPELINE (MANDATORY sequence)   │  │
│  │    └─ edtNoLogin + edtDsSenha                │  │
│  │    └─ logarSistema() evaluation               │  │
│  │    └─ 4s wait + force NFA URL nav              │  │
│  │                                                │  │
│  │ 🗐 form_filler.py (ORCHESTRATOR)             │  │
│  │    └─ Calls all fillers sequentially            │  │
│  │    └─ Manages section state & delays            │  │
│  │    └─ Captures screenshots per step             │  │
│  │    └─ Coordinates PDF download                  │  │
│  │                                                │  │
│  │ 💪 Filler Modules (Parallel Authority)        │  │
│  │    └─ produto_filler.py                       │  │
│  │    └─ emitente_filler.py                      │  │
│  │    └─ destinatario_filler.py + CEP lookup      │  │
│  │    └─ endereco_filler.py (all address fields)  │  │
│  │    └─ campos_fixos_filler.py                  │  │
│  │    └─ informacoes_adicionais_filler.py         │  │
│  │                                                │  │
│  │ 🔍 atf_selectors.py (SINGLE SOURCE OF TRUTH) │  │
│  │    └─ Label-based CSS selectors                │  │
│  │    └─ Escape regex special chars               │  │
│  │    └─ Return exact selectors (no ambiguity)    │  │
│  │                                                │  │
│  │ ⏳ delays.py (CENTRALIZED WAITS)              │  │
│  │    └─ NO hardcoded wait_for_timeout()           │  │
│  │    └─ All constants centralized                │  │
│  │    └─ Exponential backoff retry                │  │
│  │                                                │  │
│  │ 💾 batch_processor.py                          │  │
│  │    └─ Process multiple CPFs                    │  │
│  │    └─ Retry failed CPFs (3x)                  │  │
│  │    └─ Error tracking per CPF                  │  │
│  │                                                │  │
│  │ 📸 screenshot_utils.py                        │  │
│  │    └─ Save on every step                       │  │
│  │    └─ Save on every error                      │  │
│  │    └─ Organize by CPF                          │  │
│  │                                                │  │
│  │ 📋 form_logging.py & form_logging.py          │  │
│  │    └─ Console + file logging                   │  │
│  │    └─ Browser console capture                  │  │
│  │                                                │  │
│  │ ✅ data_validator.py                           │  │
│  │    └─ CPF/CNPJ pre-flight validation            │  │
│  │    └─ Fail fast before form fill               │  │
│  │                                                │  │
│  │ 📋 pdf_downloader.py                         │  │
│  │    └─ DAR + NFA PDF extraction                 │  │
│  │    └─ Retry 3x on failure                     │  │
│  │    └─ Validate file size > 0                   │  │
│  │                                                │  │
│  │ 🛶 atf_frames.py (LOGGING ONLY)               │  │
│  │    └─ Log frame structure for debugging        │  │
│  │    └─ Form now on main page (NO navigation)   │  │
│  │                                                │  │
│  │ 🟕 nfa_context.py                              │  │
│  │    └─ Browser context lifecycle                │  │
│  │    └─ Cleanup between runs                    │  │
│  │                                                │  │
│  └──────────────────────────────────┘  │
│                                                           │
│  ┌──────────────────────────────────┐  │
│  │ routers/ (HTTP endpoints)                    │  │
│  │   └─ nfa_router.py                         │  │
│  │   └─ n8n_nfa_router.py (n8n-compatible)      │  │
│  │   └─ health_router.py                      │  │
│  └──────────────────────────────────┘  │
│                                                           │
└──────────────────────────────────────────┘
                    ↑                    ↑                    ↑
                                    Uses:
        [Playwright] [FastAPI] [Asyncio]
```

---

## 🔁 EXECUTION FLOW: Single NFA Creation

```
1. USER INITIATES
   curl -X POST http://localhost:9500/api/nfa/create \
     -H "Content-Type: application/json" \
     -d '{"cpf": "12345678900", "data": {...}}'

        ↓

2. ROUTER DISPATCHES (nfa_router.py)
   - Validate input schema
   - Call nfa_service.create_nfa()

        ↓

3. SERVICE ORCHESTRATES (nfa_service.py)
   - Initialize context (nfa_context.py)
   - Launch browser (anti-bot config)
   - Return page object to form_filler.py

        ↓

4. LOGIN PHASE (atf_login.py)
   Step 1: Navigate to https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp
   Step 2: Fill input[name='edtNoLogin'] + input[name='edtDsSenha']
   Step 3: Evaluate page.evaluate("logarSistema()")
   Step 4: Wait 4 seconds (session init)
   Step 5: Navigate to NFA form URL
           https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true
           ✅ Form ready on main page

        ↓

5. FORM ORCHESTRATION BEGINS (form_filler.py)
   - Log page frames (atf_frames.py) — for debugging only
   - Call each filler sequentially with delays.py constants

        ↓

6. FILLER SEQUENCE
   A. campos_fixos_filler.py
      └─ Fill: tax regime, ICMS rate, nature of operation
      └─ Wait: AFTER_CAMPOS_FIXOS_DELAY (1000ms)
      └─ Screenshot: step1_fields_*.png

   B. emitente_filler.py
      └─ Extract: name, CNPJ from data
      └─ Fill selectors from atf_selectors.py
      └─ Wait: AFTER_EMITENTE_DELAY (1000ms)
      └─ Screenshot: step2_emitente_*.png

   C. destinatario_filler.py
      └─ Extract: CPF/CNPJ from data
      └─ Search CNPJ (if destinatario type = empresa)
      └─ Fill: name, address, contact
      └─ Wait: AFTER_DESTINATARIO_DELAY (1000ms)
      └─ Screenshot: step3_destinatario_*.png

   D. endereco_filler.py
      └─ CEP lookup (external API or form search)
      └─ Fill: cep, endereco, numero, complemento, bairro, cidade, uf
      └─ Wait: AFTER_ENDERECO_DELAY (1000ms)
      └─ Screenshot: step4_endereco_*.png

   E. produto_filler.py
      └─ Extract: product data (description, quantity, price)
      └─ Fill: product section
      └─ Wait: AFTER_PRODUTO_DELAY (1000ms)
      └─ Screenshot: step5_produto_*.png

   F. informacoes_adicionais_filler.py
      └─ Fill: additional information field (if present)
      └─ Wait: AFTER_INFORMACOES_ADICIONAIS_DELAY (500ms)
      └─ Screenshot: step6_info_adicionais_*.png

        ↓

7. FORM SUBMISSION (form_submitter.py)
   - Validate all fields pre-submission
   - Execute form submit
   - Wait for response (NETWORK_IDLE_TIMEOUT = 30000ms)
   - Capture success indicator

        ↓

8. PDF EXTRACTION (pdf_downloader.py)
   A. Download DAR PDF
      └─ Retry: 3 attempts
      └─ Validate: file size > 10KB
      └─ Save: output/nfa/pdf/<cpf>/DAR.pdf

   B. Download NFA PDF
      └─ Retry: 3 attempts
      └─ Validate: file size > 50KB
      └─ Save: output/nfa/pdf/<cpf>/NFA.pdf

        ↓

9. CLEANUP & RESULT (nfa_context.py + form_filler.py)
   - Close browser context
   - Compile results to JSON
   - Save: output/nfa/results/<cpf>.json
   - Return success response

        ↓

10. RESPONSE TO USER
    {
      "success": true,
      "cpf": "12345678900",
      "dar_path": "output/nfa/pdf/<cpf>/DAR.pdf",
      "nfa_path": "output/nfa/pdf/<cpf>/NFA.pdf",
      "screenshots_dir": "output/nfa/screenshots/<cpf>/",
      "processing_time_ms": 78234
    }
```

---

## 🔧 CRITICAL DEPENDENCY TREE

### form_filler.py (ORCHESTRATOR) depends on:
```
form_filler.py
 ├── atf_login.py (login MUST succeed first)
 ├── atf_frames.py (logging only, no blocking)
 ├── delays.py (timing constants)
 ├── atf_selectors.py (selector definitions)
 ├── screenshot_utils.py (capture on each step)
 ├── form_logging.py (logging)
 ├──
 ├── campos_fixos_filler.py
 ├── emitente_filler.py
 ├── destinatario_filler.py
 └── endereco_filler.py
 └── produto_filler.py
 └── informacoes_adicionais_filler.py
 └── form_submitter.py
 └── pdf_downloader.py
```

### BREAK IN ANY OF THESE = FORM FILL FAILS

---

## 🔍 SELECTOR RELIABILITY MATRIX

### Label-Based Approach (Current)
```python
def get_selector(field_name: str) -> str:
    """Get CSS selector using label-based strategy."""
    selectors = {
        "emitente_input": "input[placeholder*='Raz\\xe3o Social']",
        "destinatario_input": "input[placeholder*='CPF/CNPJ']",
        "cep_input": "input[placeholder*='CEP']",
        # ... more
    }
    return selectors.get(field_name, None)
```

**Advantages**:
- ✅ Resistant to HTML restructuring
- ✅ Matches semantic meaning
- ✅ Easy to verify in Chrome DevTools

**Risks**:
- ❌ Label text changes → selector fails
- ❌ Multiple inputs with same placeholder → ambiguity

**Mitigation**:
- Always add context (parent container + sibling elements)
- Use `nth-child()` as fallback ONLY if label-based fails
- Test against live SEFAZ before deploying

---

## 💾 BATCH PROCESSING FLOW

```
1. Load CPF batch from input/cpf_batch.json
   {
     "destinatarios": ["11111111111", "22222222222", ...]
   }

2. For each CPF:
   a. Validate CPF (data_validator.py)
   b. Run single NFA flow (form_filler.py)
   c. Save results per CPF
   d. On error: log + retry (max 3x) + mark as failed

3. Compile batch results:
   {
     "total": 10,
     "succeeded": 8,
     "failed": 2,
     "results": [
       {"cpf": "11111111111", "status": "success", "nfa_path": "...pdf"},
       {"cpf": "22222222222", "status": "failed", "error": "selector_not_found"}
     ]
   }

4. Return summary to user
```

---

## ⏳ DELAY STRATEGY & TUNING

### Current Delays (in milliseconds)
```python
DEFAULT_DELAY = 1500              # Default wait
FIELD_DELAY = 800                 # Field-level interactions
NETWORK_IDLE_TIMEOUT = 30000      # Max network wait
CLICK_DELAY = 600                 # Post-click pause
AFTER_SEARCH_DELAY = 2000         # After CEP/CNPJ lookup

# Section-specific
AFTER_EMITENTE_DELAY = 1000
AFTER_DESTINATARIO_DELAY = 1000
AFTER_ENDERECO_DELAY = 1000
AFTER_PRODUTO_DELAY = 1000
```

### When to Increase Delays
- ⚠️ Timeout errors on slow networks
- ⚠️ SEFAZ returns 504/502 responses
- ⚠️ JavaScript rendering incomplete

### When to Decrease Delays
- 🚀 Fast network connection (< 50ms latency)
- 🚀 Local testing / staging environments
- 🚀 Performance benchmarking

**Rule**: Never hardcode delays in module code. Always use `delays.py`.

---

## 📺 SCREENSHOT STRATEGY

### Automatic Capture Points
```
✅ After login success
✅ Before form fill starts
✅ After each section complete
✅ On any error (selector, timeout, validation)
✅ After form submission
✅ After PDF download
```

### Organization
```
output/nfa/screenshots/<cpf>/
 ├── login_success.png              # Login phase
 ├── form_ready.png                 # Form loaded
 ├── campos_fixos_filled.png        # Section 1
 ├── emitente_filled.png            # Section 2
 ├── destinatario_filled.png        # Section 3
 ├── endereco_filled.png            # Section 4
 ├── produto_filled.png             # Section 5
 ├── form_submitted.png             # After submit
 └── error_selector_*.png           # Error context
```

### Debug Usage
```bash
# View all screenshots for a CPF
open output/nfa/screenshots/12345678900/

# Find error screenshots
find output/nfa/screenshots -name "*error*"

# Extract HTML on selector failure
# (Implemented in screenshot_utils.py on critical errors)
```

---

## 📳 ERROR HANDLING & RECOVERY

### Retry Strategy (Exponential Backoff)
```python
BASE_DELAY = 2000  # milliseconds

# Retry pattern:
# Attempt 1: immediate
# Attempt 2: wait 2s, retry
# Attempt 3: wait 4s, retry
# Fail after 3 attempts

delay_ms = BASE_DELAY * (2 ** (attempt - 1))
await page.wait_for_timeout(delay_ms)
```

### Error Capture (Every Failure)
```python
try:
    await page.fill(selector, value)
except Exception as e:
    # Capture error context
    logger.error(f"Fill failed for {selector}: {e}")
    await save_screenshot(page, dir, "error_fill.png")
    
    # Extract HTML for inspection
    html_dump = await page.content()
    with open(f"logs/nfa/html_dump_{timestamp}.html", "w") as f:
        f.write(html_dump)
    
    # Retry OR escalate
    if attempt < 3:
        await page.wait_for_timeout(BASE_DELAY * (2 ** attempt))
        return await retry_fill(...)  # Recursive
    else:
        raise  # Escalate
```

---

## 🚨 FAILURE MODES & RECOVERY

| Failure | Symptom | Root Cause | Recovery |
|---------|---------|-----------|----------|
| **Login Timeout** | `wait_for_selector(mainFrame)` fails | SEFAZ down / network issue | Retry login 3x + alert |
| **Selector Not Found** | `Error: failed to find element matching selector" | HTML changed on SEFAZ | Extract HTML + update `atf_selectors.py` |
| **CEP Lookup Fails** | Endereço fields remain empty | Invalid ZIP / API error | Log warning + skip auto-fill |
| **PDF Download Fails** | File size 0 bytes | Browser context lost | Close + reopen context + retry 3x |
| **Form Submit Fails** | Validation error on form | Missing required field | Screenshot + extract error message |
| **Browser Crash** | Process exits | OOM / Playwright issue | Rebuild context + retry CPF |

---

## 🔐 SECURITY CONSIDERATIONS

### Credential Handling
- ✅ NFA_USERNAME in `.env` (never in code)
- ✅ NFA_PASSWORD in `.env` (never in code)
- ✅ No credential logging (sanitize logs)

### Form Data
- ✅ Data isolation per CPF
- ✅ Screenshots saved locally only
- ✅ PDFs encrypted at rest (optional)
- ✅ No data sent to external services (except CEP lookup)

### Anti-Bot
- ✅ Realistic user-agent (handled by Playwright)
- ✅ Proper delays between actions (delays.py)
- ✅ No rapid form resubmission
- ✅ Chromium stealth mode enabled

---

## 📊 TESTING STRATEGY

### Pre-Deployment Checklist
```bash
# 1. Syntax check
python -m py_compile app/modules/nfa/*.py

# 2. Module imports
python -c "from app.modules.nfa import *; print('OK')"

# 3. Self-test
./ops/nfa_self_test.sh

# 4. System validation
./ops/validate_nfa_system.sh

# 5. Single CPF test
./ops/run_nfa_now.sh single

# 6. Batch test (5 CPFs)
./ops/run_nfa_now.sh batch
```

### Validation Criteria
- ✅ Exit code 0 (success)
- ✅ Logs contain "Form submitted successfully"
- ✅ PDFs exist and > 0 bytes
- ✅ No error screenshots in output/
- ✅ JSON results valid JSON

---

## 🚀 DEPLOYMENT & SCALING

### Single Instance (Current)
- Port: 9500
- venv: `~/Documents/.venvs/fbp`
- Processes: 1 (sequential CPF processing)
- Time per NFA: 45-60 seconds

### Parallel Scaling (Future)
- Use `asyncio.gather()` for 3-5 concurrent contexts
- Isolate state per context (browser session unique)
- Aggregate results after all complete
- Expected: 60% faster batch processing

---

**Last Updated**: 2025-12-05  
**Architecture Status**: ✅ Production-Ready  
**Maintenance**: NFA_AUTOMATION_SPECIALIST_AI
