# FBP Backend - NFA Automation Engine ⚙️

**Global FastAPI Backend for SEFAZ-PB NFA automation and tax compliance workflows.**

**Status**: ✅ **PRODUCTION READY** | **Location**: `/Users/dnigga/Documents/FBP_Backend`  
**Powered by**: NFA_AUTOMATION_SPECIALIST_AI | **Mode**: Self-Healing & Self-Testing

---

## 🎯 Core Mission

This system is the **ONLY source of truth** for SEFAZ-PB NFA automation. It consolidates all NFA logic, provides self-healing capabilities, and maintains zero-regression discipline.

**Key Principle**: _Working code is sacred. Never break it._

---

## 🚀 Quick Start (5 minutes)

### 1. Environment Setup (One-time)

```bash
# Create venv (outside project)
python3 -m venv ~/Documents/.venvs/fbp
source ~/Documents/.venvs/fbp/bin/activate

# Install dependencies
cd /Users/dnigga/Documents/FBP_Backend
pip install -e ".[dev]"

# Setup Playwright browsers (Apple Silicon ready)
./scripts/setup_playwright.sh
```

### 2. Verify Installation

```bash
# Run diagnostics
./ops/nfa_self_test.sh

# Validate all systems
./ops/validate_nfa_system.sh
```

### 3. Start Server

**Option A: Manual Start (for development)**

```bash
# Production mode
./scripts/start.sh

# OR Development mode (hot reload)
./scripts/dev.sh
```

**Option B: Background Service (persistent, survives terminal closure)**

The server can run as a macOS LaunchAgent, ensuring it stays running even when iTerm2 or Cursor closes:

```bash
# 1. Copy LaunchAgent plist to user LaunchAgents directory
cp launch_agents/com.fbp.backend.plist ~/Library/LaunchAgents/

# 2. Load the service (starts immediately)
launchctl load ~/Library/LaunchAgents/com.fbp.backend.plist

# 3. Verify it's running
launchctl list | grep com.fbp.backend

# 4. View logs
tail -f logs/server.log
tail -f logs/server_error.log
```

**Managing the Background Service:**

```bash
# Restart the service
launchctl kickstart -k gui/$UID/com.fbp.backend

# Stop the service
launchctl unload ~/Library/LaunchAgents/com.fbp.backend.plist

# Check service status
launchctl list | grep com.fbp.backend
```

**Note:** The LaunchAgent will:

- Start automatically at login
- Restart automatically if the server crashes
- Keep running even when terminal windows close
- Log output to `logs/server.log` and `logs/server_error.log`

Server available at: `http://localhost:8000`  
API Docs: `http://localhost:8000/docs`

### 4. Run NFA Automation

```bash
# Single NFA (interactive)
./ops/run_nfa_now.sh single

# Batch NFA (from file: input/cpf_batch.json)
./ops/run_nfa_now.sh batch

# Health check
curl http://localhost:8000/health
```

---

## 📁 Project Structure

```
FBP_Backend/
├── app/                           # FastAPI application core
│   ├── core/                      # Core utilities
│   │   ├── config.py             # Pydantic configuration
│   │   ├── logging_setup.py       # Structured logging
│   │   ├── browser.py            # Playwright launcher
│   │   └── constants.py           # Global constants
│   │
│   ├── modules/                   # Business logic (reusable, no HTTP)
│   │   ├── nfa/                  # ✅ NFA AUTOMATION (17 modules)
│   │   │   ├── atf_login.py              # Login + forced navigation
│   │   │   ├── atf_frames.py             # Dynamic iframe detection
│   │   │   ├── atf_selectors.py          # CSS selectors (label-based)
│   │   │   ├── form_filler.py            # Main orchestrator
│   │   │   ├── produto_filler.py         # Product/item filling
│   │   │   ├── emitente_filler.py        # Emitente section
│   │   │   ├── destinatario_filler.py    # Destinatario section
│   │   │   ├── endereco_filler.py        # Address filling (all fields)
│   │   │   ├── batch_processor.py        # Batch processing with retry
│   │   │   ├── data_validator.py         # CPF/CNPJ validation
│   │   │   ├── delays.py                 # 🔑 UNIVERSAL DELAY SYSTEM
│   │   │   ├── campos_fixos_filler.py    # Fixed fields
│   │   │   ├── informacoes_adicionais_filler.py  # Additional info
│   │   │   ├── form_submitter.py         # Form submission
│   │   │   ├── pdf_downloader.py         # PDF extraction (retry logic)
│   │   │   ├── screenshot_utils.py       # Screenshot pipeline
│   │   │   ├── nfa_context.py            # Context management
│   │   │   ├── form_logging.py           # Detailed logging
│   │   │   └── browser_launcher.py       # Browser lifecycle
│   │   │
│   │   ├── redesim/               # REDESIM automation
│   │   ├── utils/                 # Utility functions
│   │   └── organizer/             # Window management
│   │
│   ├── routers/                   # FastAPI endpoints (HTTP layer)
│   │   ├── nfa_router.py         # NFA endpoints
│   │   ├── n8n_nfa_router.py      # n8n-compatible NFA endpoints
│   │   ├── health_router.py       # Health check endpoints
│   │   └── *.py                   # Other routers
│   │
│   ├── services/                  # Orchestration layer
│   │   └── nfa_service.py        # NFA orchestrator
│   │
│   └── main.py                    # FastAPI app entry point
│
├── ops/                           # 🔧 OPERATIONS & SCRIPTS
│   ├── run_nfa_now.sh            # End-to-end NFA runner
│   ├── nfa_self_test.sh           # Self-test diagnostics
│   ├── validate_nfa_system.sh     # System validation
│   ├── validate_sefaz_access.sh   # SEFAZ connectivity test
│   └── scripts/
│       ├── foks_env_autofix.sh    # Environment auto-fix
│       ├── foks_boot.sh           # Server boot script
│       └── install-and-activate.sh # Safari extension installer
│
├── scripts/                       # Development scripts
│   ├── start.sh                  # Start server (port 8000)
│   ├── dev.sh                    # Development mode
│   ├── test.sh                   # Run test suite
│   ├── setup_playwright.sh        # Install browsers
│   └── reinst-chrome.sh           # Chromium reinstall
│
├── fallback_extension/            # Safari extension (auto-inject)
│   ├── NFA*.xcodeproj/
│   ├── shared/                   # Shared scripts
│   └── README.md                 # Extension docs
│
├── input/                         # Input data
│   └── cpf_batch.json            # Batch CPF list
│
├── output/                        # Generated outputs
│   ├── nfa/
│   │   ├── pdf/                  # DAR + NFA PDFs (by CPF)
│   │   ├── results/              # JSON results
│   │   └── screenshots/          # Debug screenshots (by CPF)
│   └── redesim/                  # REDESIM outputs
│
├── logs/                          # Application logs
│   └── nfa/
│       ├── nfa_debug.log         # Main debug log
│       └── browser_console.log   # Browser console output
│
├── config/                        # Configuration files
│   ├── auth/                     # Credentials (gitignored)
│   └── nfa.yaml                  # NFA config
│
├── docs/                          # Documentation
│   ├── NFA/                       # NFA documentation
│   │   ├── OVERVIEW.md           # System overview
│   │   ├── MODULES.md            # Module documentation
│   │   └── API.md                # API endpoints
│   ├── n8n/                       # n8n integration
│   ├── ARCHITECTURE_DIAGRAM.md   # System architecture
│   └── TROUBLESHOOTING.md        # Debug procedures
│
├── tests/                         # Test suite
├── .env                          # Environment variables (local)
├── .env.example                  # Example env
├── pyproject.toml                # Project metadata (PEP 621)
└── README.md                     # Original README
```

---

## ⚙️ Configuration

### Universal Delay System

**File**: `app/modules/nfa/delays.py`

All delays centralized—**NO hardcoded waits**:

```python
DEFAULT_DELAY = 1500          # ms - General operations
FIELD_DELAY = 800             # ms - Field interactions
NETWORK_IDLE_TIMEOUT = 30000  # ms - Network waits
CLICK_DELAY = 600             # ms - Click actions
AFTER_SEARCH_DELAY = 2000     # ms - CEP/search results
SUBMIT_WAIT = 3000            # ms - Form submission
PDF_WAIT = 5000               # ms - PDF download
```

**When adding new delays**: Edit `delays.py` ONLY. Never hardcode waits.

### Batch Input Format

**File**: `input/cpf_batch.json`

```json
{
  "destinatarios": ["73825506215", "12345678901"]
}
```

---

## 🔧 API Endpoints

### Health & Status

```bash
GET /health
→ {"status": "healthy", "components": {...}}

GET /api/nfa/health
→ {"status": "ready", "playwright": "ok", "chromium": "ok"}
```

### NFA Operations

```bash
# Create single NFA
POST /api/nfa/create
Content-Type: application/json

{
  "cpf_emitter": "12345678901",
  "login": "user@sefaz.pb",
  "password": "****",
  "data": {...}
}

Response: {
  "success": true,
  "nfa_key": "35250112345678901650650000000123456789012345",
  "pdf_dar": "/path/to/DAR.pdf",
  "pdf_nfa": "/path/to/NFA.pdf",
  "screenshots": [...]
}

# Process batch
POST /api/nfa/batch
Content-Type: application/json

{
  "file": "input/cpf_batch.json"
}

Response: {
  "success": true,
  "processed": 2,
  "failed": 0,
  "results": [...]
}
```

### n8n-Compatible Endpoints

```bash
# n8n: Create NFA
POST /api/n8n/nfa/create
→ Returns n8n-friendly format

# n8n: Extract SEFAZ data
POST /api/n8n/redesim/extract
→ Returns structured JSON
```

---

## 🚀 Production Usage

### Scenario 1: Single NFA (Manual)

```bash
./ops/run_nfa_now.sh single
# Prompts for CPF, login, password
# Creates NFA, downloads PDFs, saves screenshots
```

### Scenario 2: Batch Processing

```bash
# Edit input/cpf_batch.json with CPF list
./ops/run_nfa_now.sh batch
# Processes all CPFs, logs results, organizes by CPF
```

### Scenario 3: n8n Integration

In n8n workflow:

1. **HTTP Request** node posts to `/api/n8n/nfa/create`
2. **Workflow** waits for response
3. **Logging** node captures JSON result
4. **File** node saves PDFs from response

### Scenario 4: Continuous Monitoring

```bash
# Run nightly batch processing
0 2 * * * cd /Users/dnigga/Documents/FBP_Backend && ./ops/run_nfa_now.sh batch >> logs/nfa/batch_$(date +%Y%m%d).log 2>&1
```

---

## 🔍 Validation & Diagnostics

### Quick Validation

```bash
# Check all systems
./ops/validate_nfa_system.sh

# Output shows:
# ✅ NFA modules exist
# ✅ Delays centralized
# ✅ Selectors valid
# ✅ Scripts executable
# ✅ Playwright ready
```

### Component Testing

```bash
# Test login module only
python3 -c "from app.modules.nfa.atf_login import AutomatedLogin; print('✅ Login module OK')"

# Test selector extraction
python3 -c "from app.modules.nfa.atf_selectors import get_emitente_selectors; print(get_emitente_selectors())"

# Test delay system
python3 -c "from app.modules.nfa.delays import DEFAULT_DELAY; print(f'DEFAULT_DELAY = {DEFAULT_DELAY}ms')"
```

### Browser Diagnostics

```bash
# Verify Chromium installation
python3 -m playwright install
python3 -m playwright install-deps

# Test browser launch
python3 verify.py
# Shows: Chromium version, path, M3 compatibility
```

---

## 🛠️ NFA_AUTOMATION_SPECIALIST_AI Mode

This system operates as **NFA_AUTOMATION_SPECIALIST_AI**—a self-healing automation engineer that:

1. **Detects regressions** automatically
2. **Repairs broken logic** without user intervention
3. **Maintains zero-regression discipline**
4. **Captures error context** (screenshots + logs)
5. **Diagnoses root causes** systematically

### Triggering Self-Healing

**Automatic** (runs every test cycle):

```bash
./ops/nfa_self_test.sh
# If any component fails → automatically patches
```

**Manual** (when you suspect issues):

```bash
# Read detailed debug output
tail -200 logs/nfa/nfa_debug.log

# Take screenshot of current SEFAZ state
python3 app/modules/nfa/screenshot_utils.py

# Re-run the last failed operation
./ops/run_nfa_now.sh --debug
```

---

## 🧰 Troubleshooting

### Issue: Login fails repeatedly

**Root cause**: SEFAZ password changed or form selector changed.

**Fix**:

```bash
# 1. Check current login flow
tail -100 logs/nfa/nfa_debug.log | grep -i "login"

# 2. Capture current SEFAZ form
python3 -c "from app.modules.nfa.atf_login import AutomatedLogin; \
AutomatedLogin('user', 'pass').take_login_screenshot()"

# 3. Update selectors in atf_selectors.py if needed

# 4. Validate with test script
python3 tests/test_login.py
```

### Issue: Form fields not filling

**Root cause**: Iframe selector changed or field structure updated.

**Fix**:

```bash
# 1. Inspect current iframes
tail -100 logs/nfa/nfa_debug.log | grep -i "iframe"

# 2. Run iframe detection test
python3 -c "from app.modules.nfa.atf_frames import FrameDetector; \
FrameDetector().detect_all_iframes()"

# 3. Update atf_frames.py if needed

# 4. Re-run field test
python3 tests/test_form_filling.py
```

### Issue: PDF download fails

**Root cause**: Download timeout or file path issue.

**Fix**:

```bash
# 1. Check PDF wait times
grep -n "PDF_WAIT\|pdf_wait" app/modules/nfa/delays.py

# 2. Increase timeout (if SEFAZ is slow):
# Edit delays.py: PDF_WAIT = 8000  # was 5000

# 3. Verify output directory
ls -la output/nfa/pdf/

# 4. Re-run download test
python3 tests/test_pdf_download.py
```

---

## 📊 Monitoring & Logging

### Log Locations

```
logs/nfa/
├── nfa_debug.log              # Main debug log (all operations)
├── browser_console.log         # Browser console errors
├── batch_2024-12-05.log       # Batch processing log (by date)
└── login_failures.log         # Login-specific failures
```

### Log Levels

```
DEBUG   → Detailed state, selector matching, iframe detection
INFO    → Operation milestones, form filling progress
WARNING → Timeout warnings, selector not found (retrying)
ERROR   → Failures, login denied, form submission failed
```

### Monitoring Dashboard

```bash
# Real-time log tail (all NFA operations)
tail -f logs/nfa/nfa_debug.log

# Watch for errors
grep ERROR logs/nfa/nfa_debug.log | tail -20

# Count successful vs failed
grep "✅ NFA Created" logs/nfa/nfa_debug.log | wc -l
grep "❌ NFA Failed" logs/nfa/nfa_debug.log | wc -l
```

---

## 🔐 Security & Credentials

### Credential Management

```
config/auth/               # Gitignored directory
├── sefaz_credentials.yaml # SEFAZ login (not in git)
├── gmail_token.json       # OAuth token (not in git)
└── .gitignore            # Ensures never committed
```

### Safe Usage

```python
# ✅ CORRECT: Use environment variables
login = os.getenv("SEFAZ_LOGIN")
password = os.getenv("SEFAZ_PASSWORD")

# ❌ WRONG: Hardcode credentials
login = "user@sefaz.pb"  # NEVER do this
```

### CI/CD Integration

In GitHub Actions / n8n:

```bash
# Set secrets in CI environment
export SEFAZ_LOGIN=...
export SEFAZ_PASSWORD=...

# Scripts auto-read from env
./ops/run_nfa_now.sh batch
```

---

## 🧪 Testing

### Run Full Test Suite

```bash
./scripts/test.sh
# Runs:
# - Ruff linting
# - MyPy type checking
# - Pytest unit tests
# - Coverage report
```

### Run Specific Tests

```bash
# Test login only
pytest tests/test_login.py -v

# Test form filling
pytest tests/test_form_filling.py -v

# Test with coverage
pytest tests/ --cov=app --cov-report=html
```

### Write New Tests

```python
# tests/test_nfa_module.py
import pytest
from app.modules.nfa.form_filler import FormFiller

@pytest.mark.asyncio
async def test_form_filler_emitente():
    filler = FormFiller()
    result = await filler.fill_emitente({"nome": "Test Company"})
    assert result.success is True
    assert result.filled_fields > 0
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions (Recommended)

```yaml
# .github/workflows/nfa-test.yaml
name: NFA Automation Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: macos-latest-xlarge # Apple Silicon
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: ./scripts/test.sh
      - run: ./ops/validate_nfa_system.sh
```

### Docker Build (Optional)

```bash
# Build Docker image
docker build -t fbp-nfa:latest .

# Run NFA in container
docker run -e SEFAZ_LOGIN=... -e SEFAZ_PASSWORD=... \
  -v $(pwd)/output:/app/output \
  fbp-nfa:latest ./ops/run_nfa_now.sh batch
```

---

## 📚 Documentation

| Document                                                | Purpose                 |
| ------------------------------------------------------- | ----------------------- |
| [OVERVIEW.md](docs/NFA/OVERVIEW.md)                     | NFA system architecture |
| [MODULES.md](docs/NFA/MODULES.md)                       | Module-by-module guide  |
| [API.md](docs/NFA/API.md)                               | API endpoint reference  |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)           | Debug procedures        |
| [n8n Integration](docs/n8n/README.md)                   | n8n workflow setup      |
| [ARCHITECTURE_DIAGRAM.md](docs/ARCHITECTURE_DIAGRAM.md) | System design           |

---

## 🚀 Production Deployment

### Pre-Deployment Checklist

```bash
# 1. Validate system
./ops/validate_nfa_system.sh

# 2. Run full test suite
./scripts/test.sh

# 3. Check logs for errors
grep ERROR logs/nfa/*.log

# 4. Verify SEFAZ connectivity
./ops/validate_sefaz_access.sh

# 5. Test batch processing
./ops/run_nfa_now.sh batch

# 6. Confirm PDFs generated
ls -la output/nfa/pdf/*/
```

### Deployment Steps

```bash
# 1. SSH to production server
ssh user@prod-server

# 2. Pull latest code
cd /Users/dnigga/Documents/FBP_Backend
git pull origin main

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Start server
./scripts/start.sh

# 5. Monitor logs
tail -f logs/nfa/nfa_debug.log
```

---

## 🔑 Key Features

✅ **Self-Healing Automation** - Detects & repairs regressions  
✅ **Zero Hardcoded Waits** - All delays in `delays.py`  
✅ **Universal Delay System** - Centralized timing  
✅ **Label-Based Selectors** - More stable than nth() selectors  
✅ **Dynamic Iframe Detection** - Scans all iframes automatically  
✅ **Robust Error Handling** - Try/catch around all Playwright actions  
✅ **Screenshot Pipeline** - Captures state on every failure  
✅ **PDF Retry Logic** - 3 attempts for DAR + NFA downloads  
✅ **Batch Processing** - Multiple CPFs from JSON file  
✅ **Per-CPF Organization** - PDFs and screenshots organized by CPF  
✅ **Comprehensive Logging** - Console + file logging for all modules  
✅ **n8n Integration** - Ready for automation workflows  
✅ **Apple Silicon Ready** - Tested on M3/M4 Macs

---

## 🎯 Core Beliefs (NFA_AUTOMATION_SPECIALIST_AI)

1. **Working code is sacred** — Never break it.
2. **If a regression is detected, repair it automatically.**
3. **Stability > Complexity** — Prefer small, reliable, battle-tested functions.
4. **Never assume SEFAZ will behave normally** — Always implement failover strategies.
5. **You own the integration** — The user should not have to debug.

---

## 📞 Support

For issues or questions:

1. Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
2. Review logs: `tail -200 logs/nfa/nfa_debug.log`
3. Run diagnostics: `./ops/nfa_self_test.sh`
4. Validate system: `./ops/validate_nfa_system.sh`

---

## 📝 License

MIT

---

**System Status**: ✅ **PRODUCTION READY**  
**Last Updated**: 2025-12-05  
**Maintained By**: NFA_AUTOMATION_SPECIALIST_AI
