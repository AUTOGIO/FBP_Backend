# HOW TO USE FOKS SYSTEM

## Document Purpose
This document is the full operating manual for the FoKS ecosystem as currently documented across your project READMEs and governance files.

It is written as a practical runbook for daily use on your local Apple Silicon macOS setup, with clear boundaries between projects:
- PromptForge Personal (orchestration layer)
- FBP Backend + `fbp` CLI (backend execution layer)
- Nexus Workspace (workspace intelligence layer)
- FoKS + CORTEX Mission Control + native macOS apps (control/visualization layer)

---

## Scope and Assumptions
- Machine profile: Apple Silicon Mac (M3-class), macOS 13+ (some modules require macOS 15+).
- Workspace root pattern: `/Users/dnigga/Documents/Active_Projects/`
- You operate locally-first with privacy-first automation.
- You use Swift-native tooling plus Python FastAPI where required (FBP backend).

---

## System Architecture Overview

### Layer 1: Orchestration (PromptForge Personal)
Primary command center for daily automation, diagnostics, and workflow execution.

Key capabilities:
- Config generation/validation
- Workflow execution (DayStart, health checks, AI routines)
- Integration status/audit for FoKS and FBP
- Doctor diagnostics
- launchd automation generation
- Keychain-backed API key handling

### Layer 2: Execution Backend (FBP Backend + fbp CLI)
Backend job processing and API operations.

Key capabilities:
- FastAPI backend endpoints (`/health`, jobs, workflows)
- Swift CLI (`fbp`) to submit/query jobs
- Domain workflows such as NFA consultation, REDESIM, FAC batch, CEP validation

### Layer 3: Workspace Intelligence (Nexus)
Workspace orchestration and AI-assisted profile/layout operations.

Key capabilities:
- Profile suggestion/application
- Display reconciliation and layout guidance
- Auto-tiling integration with YABAI
- Analytics and monitor status
- Optional MCP server bridge

### Layer 4: Native UI + Monitoring (FoKS / CORTEX Mission Control)
Native Swift/SwiftUI interfaces for real-time visibility and operational control.

Key capabilities:
- Live system stats and project status visualization
- AI suggestions and natural language interaction surfaces
- Operational dashboard for workspace and health signals

---

## Repositories and Their Roles

### 1) PromptForge Personal
Purpose: local workflow orchestrator and integration backbone.

Core commands:
- `swift run promptforge-personal config validate`
- `swift run promptforge-personal doctor`
- `swift run promptforge-personal workflow --name <workflow>`
- `swift run promptforge-personal integration audit`
- `./scripts/verify.sh`
- `./scripts/deep_check.sh`

### 2) FBP_Backend
Purpose: backend runtime and Swift CLI surface.

Core paths:
- Backend app: `app/`
- API routes: `app/api/`
- Jobs engine: `app/jobs/`
- Workflow modules: `app/workflows/`
- Startup script: `scripts/start.sh`
- Swift CLI: `tools/fbp-cli/`

### 3) Nexus Workspace
Purpose: workspace profile intelligence and reconciliation.

Core commands:
- `swift run nexus doctor`
- `swift run nexus status`
- `swift run nexus reconcile`
- `swift run nexus suggest profile`
- `swift run nexus analytics`
- `swift run nexus ai stats`

### 4) FoKS Intelligence
Purpose: Swift-native local automation brain and app-level capabilities.

Current status from docs:
- Swift app exists and is active.
- `foks` CLI is planned (not fully productionized in cited docs).
- OpenAI key required for OpenAI-based app features.

### 5) CORTEX Mission Control / MenuBar Apps
Purpose: operational visibility and control UI.

Notes:
- Native SwiftUI app architecture documented.
- Production-oriented constraints defined (polling limits, concurrency patterns, dependency policy).

---

## Installation and Prerequisites

## macOS and Toolchain
- macOS 13+ minimum for major Swift apps.
- macOS 15+ required for some CORTEX components.
- Swift 6 toolchain (recommended for strict concurrency targets).
- Xcode 15+ or newer toolchain where needed.

## Runtime dependencies
- Python 3 (for FBP backend and scripts that require Python execution).
- Uvicorn available for FastAPI preferred startup path.
- YABAI optional for tiling-aware workflows.

## Permissions
For native monitoring apps, verify:
- Full Disk Access
- Accessibility permissions

---

## Configuration Standards

## PromptForge config
- Keep committed sample config only (`promptforge_personal.sample.yml`).
- Keep local machine config uncommitted (`promptforge_personal.yml`).
- Validate after any config edit:
  - `swift run promptforge-personal config validate`

## Secrets and API keys
- Do not store secrets in repo files.
- Use environment variables or Keychain.
- PromptForge keychain service policy: Keychain-backed provider keys.

Examples:
- `swift run promptforge-personal key set openai "sk-..."`
- `swift run promptforge-personal key set anthropic "sk-ant-..."`
- `swift run promptforge-personal key set grok "xai-..."`

## Environment variables in use across system
Common examples from docs:
- `FBP_BASE_URL`
- `OPENAI_API_KEY`
- `CORTEX_AI_PROVIDER`
- `CORTEX_AI_KEY`
- `CORTEX_YABAI_ENABLED`
- `NEXUS_SYNC_ENABLED`

---

## Daily Operating Runbook (Recommended)

## Step 1: Morning preflight (PromptForge first)
Run from PromptForge repo:
```bash
swift run promptforge-personal config validate
swift run promptforge-personal doctor
./scripts/verify.sh
```

If performing deeper confidence checks:
```bash
./scripts/deep_check.sh
```

## Step 2: Start FBP backend
Run from FBP backend repo:
```bash
/Users/dnigga/Documents/Active_Projects/FBP_Backend/scripts/start.sh
```

What start script does:
- If `uvicorn` is available: starts `app.main:app` on `FBP_HOST`/`FBP_PORT` (defaults `127.0.0.1:8000`).
- If `uvicorn` is unavailable: falls back to a standard-library HTTP server exposing at least `/health`.

## Step 3: Verify FBP API health
```bash
fbp health
```
Expected result: backend health returns successfully.

## Step 4: Execute daily backend tasks
Examples:
```bash
fbp nfa consult --from DD/MM/YYYY --to DD/MM/YYYY --matricula 1595504
fbp nfa status <job_id> --wait

fbp redesim consulta
fbp redesim status <job_id> --wait

fbp fac batch --input facs.json
fbp fac status <job_id>

fbp cep validate 58010120 --enrich --json
fbp metrics
```

## Step 5: Use Nexus for workspace intelligence
```bash
swift run nexus status
swift run nexus reconcile
swift run nexus suggest profile
swift run nexus analytics
```

## Step 6: End-of-day checks
- Run integration/audit checks in PromptForge.
- Capture logs/artifacts.
- Review failures and queue remediation.

---

## Command Reference (High-Value)

## FBP CLI (tools/fbp-cli)
Core commands:
- `fbp health`
- `fbp nfa consult --from --to [--matricula]`
- `fbp nfa status <job_id> [--wait]`
- `fbp redesim consulta`
- `fbp redesim status <job_id> [--wait]`
- `fbp fac batch --input <file.json>`
- `fbp fac status <job_id>`
- `fbp cep validate <cep> [--enrich] [--json]`
- `fbp run-bash --file <script.sh> [--timeout <sec>]`
- `fbp metrics`

Global base URL control:
- Env: `FBP_BASE_URL`
- Per command override: `--fbp-url` / `-u`

## PromptForge (selected)
- `config validate`
- `doctor`
- `workflow --name morningDesk`
- `workflow --name foksAndFbpHealth`
- `workflow --name aiSummary`
- `integration audit`
- `launchd ...`

## Nexus (selected)
- `doctor`
- `start`
- `status`
- `autotile status`
- `reconcile`
- `suggest profile`
- `analytics`
- `ai stats`
- `sync status`
- `space optimize`
- `db doctor`

---

## Troubleshooting Runbook

## PromptForge issues

### Config validation fails
Actions:
1. Recheck all configured paths in YAML.
2. Ensure `machineProfile` matches expected profile.
3. Re-run `config validate`.

### Missing API key during AI commands
Actions:
1. Set key in Keychain with `key set` command.
2. Or export provider env var temporarily.

### launchd job not running
Actions:
1. Validate plist: `plutil -lint <plist>`
2. Inspect launchctl status: `launchctl print gui/$(id -u)/<label>`
3. Check output logs directory.

## FBP backend issues

### Backend not starting
Actions:
1. Verify Python 3 present.
2. Verify `uvicorn` availability (or allow fallback server).
3. Check `FBP_HOST` and `FBP_PORT` collision.

### `fbp health` fails
Actions:
1. Confirm backend process is running.
2. Confirm base URL: `FBP_BASE_URL` or command override.
3. Retry with direct curl to `/health`.

### Jobs stuck in pending/running
Actions:
1. Poll with `--wait` for known intervals.
2. Check backend logs and storage job records.
3. Validate input payload format (JSON for FAC batch, date formats for NFA).

## Nexus issues

### `swift test` signal issue after passing tests
Known condition in status report: tests may pass yet process exits with signal 5.
Action:
1. Treat as tooling/test-runner defect until fixed.
2. Validate individual suites if needed.
3. Track as priority remediation item.

### Reconcile/apply not affecting layout
Actions:
1. Confirm YABAI installed and active.
2. Confirm relevant feature flags enabled.
3. Re-run status and reconcile with actionable suggestions present.

---

## Data, Output, and Governance Contract

From Active Projects contract:

## Documentation placement
- Auto-generated docs: `<project_root>/docs/auto/`
- Manual docs: `<project_root>/docs/manual/`
- Never overwrite manual documentation with generated outputs.

## Runtime outputs (never commit)
Do not commit:
- Build artifacts (`dist/`, `build/`, `out/`)
- Caches (`node_modules/`, `__pycache__/`, `.cache/`)
- Secret-bearing env files
- Runtime logs and temp files

## Centralized Ops output routing
Route operational outputs to:
- `/Users/dnigga/Documents/Ops/Run_Logs/`
- `/Users/dnigga/Documents/Ops/Artifacts/`
- `/Users/dnigga/Documents/Ops/Automation_Reports/`
- `/Users/dnigga/Documents/Ops/System_Snapshots/`
- `/Users/dnigga/Documents/Ops/Quarantine/`

## Project entry points preferred by automation
1. `docker-compose.yml`
2. `scripts/start.sh`
3. `Makefile`
4. `package.json`
5. `pyproject.toml`

---

## Security and Compliance Guidelines
- Keep credentials in Keychain or env vars only.
- Never commit machine-specific secret config.
- Keep path usage consistent with Active_Projects roots.
- Run integration audits regularly to detect legacy paths/drift.
- Use minimal privileges for automation routines.

---

## Suggested Weekly Operational Cadence

### Daily
- PromptForge preflight + doctor
- FBP health check
- Nexus status/reconcile as needed
- Capture run outputs and failures

### Weekly
- Full deep check (`deep_check.sh`)
- Integration audit
- Review drift/legacy path hits
- Review workflow reliability metrics and unresolved incidents

### Monthly
- Retrospective on automation wins/failures
- Remove stale scripts and dead config
- Revalidate launchd agents and environment variable inventory

---

## Known Gaps / Reality Check
- Some ecosystem components are fully operational, others are partially implemented by design.
- Nexus report explicitly flags certain features as partially verified or unverified in production contexts (GUI, iCloud sync, MCP client invocation).
- FoKS CLI is described as planned in provided docs; do not assume parity with PromptForge/FBP CLI capabilities unless explicitly implemented in code.

---

## Practical Golden Path (Minimal Reliable Flow)
1. Validate PromptForge config and run doctor.
2. Start FBP backend (`scripts/start.sh`).
3. Verify `fbp health`.
4. Run one real workflow/job end-to-end and confirm completion.
5. Use Nexus suggestion/reconcile only after base services are healthy.
6. Store logs/artifacts under governed output paths.
7. Commit only source/config templates/docs that are safe and intended.

---

## Quick Recovery Checklist
If system behavior is unclear, run in this exact order:
1. PromptForge: `config validate`
2. PromptForge: `doctor`
3. FBP: start backend script
4. FBP: `fbp health`
5. Nexus: `doctor`
6. Nexus: `status`
7. Review logs and recent artifacts
8. Re-run only the failing command with verbose output

---

## Source References Used for This Manual
- PromptForge Personal README and User Guide
- FBP backend README + fbp-cli README + startup script
- FoKS Intelligence README
- Nexus project status report
- CORTEX native macOS docs and mission control prompt docs
- Active Projects governance contract
- Contributing and code of conduct documents where relevant to process discipline

---

## Final Notes
This manual is intentionally operational-first: use it as your day-to-day command center.
When new workflows or services are added, update this document in `docs/manual/` and keep generated technical references in `docs/auto/`.
