# FBP Backend

Global FastAPI Backend for automation projects (REDESIM, NFA, Utils, Browser).

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Virtual environment manager (venv)

### Setup

1. **Create virtual environment** (outside project):

   ```bash
   python3 -m venv ~/Documents/.venvs/fbp
   source ~/Documents/.venvs/fbp/bin/activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -e ".[dev]"
   ```

3. **Setup Playwright browsers**:

   ```bash
   ./scripts/setup_playwright.sh
   ```

4. **Start server**:
   ```bash
   ./scripts/start.sh
   ```

Server will be available at `http://localhost:8000`

## 📁 Project Structure

```
FBP_Backend/
├── app/                    # Main application
│   ├── core/              # Core utilities (config, logging, browser)
│   ├── modules/           # Business logic modules
│   │   ├── redesim/      # REDESIM automation
│   │   ├── nfa/          # NFA automation
│   │   ├── utils/        # Utility functions
│   │   └── organizer/    # Window management
│   ├── routers/           # FastAPI routers
│   │   ├── n8n_*.py     # n8n-compatible endpoints
│   │   └── *.py         # Other endpoints
│   └── services/          # Service layer (execution)
├── docs/                  # Documentation
├── tests/                 # Test suite
├── scripts/               # Utility scripts
│   ├── start.sh          # Start server
│   ├── dev.sh            # Development mode
│   ├── test.sh           # Run tests
│   └── setup_playwright.sh  # Install browsers
├── config/                # Configuration files
└── pyproject.toml         # Project configuration (PEP 621)
```

## 🛠️ Development

### Running Tests

```bash
./scripts/test.sh
```

This runs:

- Ruff linting
- Code formatting check
- MyPy type checking
- Pytest

### Development Mode

```bash
./scripts/dev.sh
```

Runs server with:

- Hot reload enabled
- DEBUG mode
- Detailed logging

### Unified Backend Architecture

The FastAPI backend is **ALWAYS** started by the LaunchAgent (port 8000).

**Key Principles:**

- Automation scripts do **NOT** start backend servers
- All scripts always call `API_URL=http://localhost:8000`
- Playwright flows use the same backend → ensures consistency, correct inputs, no mismatched payloads
- Single source of truth: LaunchAgent is the sole owner of the backend process

**Benefits:**

- Deterministic behavior: same backend instance for all operations
- No port conflicts: single port (8000) for all services
- Consistent state: all automations share the same backend state
- Simplified debugging: single log file, single process to monitor

### Running FastAPI as a Background macOS Service

1. Copy plist:
   ```bash
   cp launch_agents/com.fbp.backend.plist ~/Library/LaunchAgents/
   ```
2. Load service:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.fbp.backend.plist
   ```
3. Check backend status:
   ```bash
   curl http://localhost:8000/health
   ```
4. Restart service:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.fbp.backend.plist
   launchctl load ~/Library/LaunchAgents/com.fbp.backend.plist
   ```
5. Check LaunchAgent status:
   ```bash
   launchctl list | grep com.fbp.backend
   ```
6. Verify server running after closing terminal:
   ```bash
   ps aux | grep uvicorn
   curl http://localhost:8000/health
   ```
7. View logs:
   ```bash
   tail -f logs/server.log
   ```

## Fallback Extension Mode

- Chrome extension at `fallback_extension/` auto-loads when `USE_EXTENSION_FALLBACK=true`.
- Python automation runs first; if a field fails, it triggers `window.nfaFallback.tryFillAll(...)`.
- Provides deep iframe DOM helpers and visual overlays for debugging.
- Sandboxed: only matches `https://www4.sefaz.pb.gov.br/*` and runs inside Playwright Chromium.

## 📚 Documentation

- [n8n Integration](./docs/n8n/README.md)
- [NFA Module](./docs/NFA/OVERVIEW.md)
- [Architecture](./docs/ARCHITECTURE_DIAGRAM.md)

## 🔧 Configuration

Configuration is managed via:

- `app/core/config.py` - Pydantic settings
- `.env` file - Environment variables
- `config/*.yaml` - Module-specific configs

## 🧰 Chromium Playwright Reinstall (Apple Silicon)

- Reinstall and relink Playwright Chromium (removes Brew/manual installs):
  ```bash
  /Users/dnigga/Documents/FBP_Backend/run_reinstall.sh
  ```
- Validate browser launch:
  ```bash
  python3 /Users/dnigga/Documents/FBP_Backend/verify.py
  ```
- Version checks:
  ```bash
  /Applications/Chromium.app/Contents/MacOS/Chromium --version
  python3 -m playwright --version
  ```
- Troubleshooting:
  - Clear cache manually if needed: `rm -rf ~/Library/Caches/ms-playwright`
  - Remove old profiles: `rm -rf ~/Library/Application\ Support/Chromium`
  - Gatekeeper: `xattr -dr com.apple.quarantine /Applications/Chromium.app`
  - Ensure Homebrew is on PATH: `/opt/homebrew/bin` or `/usr/local/bin`

## 🌐 API Endpoints

### n8n-Compatible Endpoints

All endpoints return n8n-friendly format:

```json
{
  "success": true|false,
  "data": {},
  "errors": []
}
```

- `POST /api/redesim/extract` - Extract REDESIM data
- `POST /api/redesim/email/create-draft` - Create Gmail draft
- `POST /api/redesim/email/send` - Send email
- `POST /api/nfa/create` - Create NFA
- `POST /api/utils/cep` - Validate CEP
- `POST /api/browser/html` - Capture HTML

See [n8n docs](./docs/n8n/) for details.

## 🔐 Security

- Credentials stored in `config/auth/` (gitignored)
- No hard-coded secrets
- Structured logging (no credential leaks)
- Environment variables for sensitive data

## 📦 Dependencies

See `pyproject.toml` for full dependency list.

Core:

- FastAPI
- Uvicorn
- Pydantic
- Playwright
- Google API Client

Dev:

- Pytest
- Ruff
- MyPy
- Black

## 🏗️ Architecture

- **Routers**: HTTP endpoints (no business logic)
- **Services**: Execution layer
- **Modules**: Business logic (reusable)
- **Core**: Shared utilities

## 📝 License

MIT
