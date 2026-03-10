# fbp-cli Audit and Map

**Date:** 2026-03-09  
**Scope:** CLI commands, API client flow, config path — verified against repository code.

---

## 1. Repository layout (verified)

```
FBP_Backend/tools/fbp-cli/
├── Package.swift
├── Makefile
├── README.md
├── Sources/
│   ├── fbp-cli/           # executable target
│   │   ├── main.swift
│   │   ├── HealthCommand.swift
│   │   ├── NFACommand.swift      # + NFAConsultCommand, NFAStatusCommand
│   │   ├── RedesimCommand.swift  # + RedesimConsultaCommand, RedesimStatusCommand
│   │   ├── FACCommand.swift     # + FACBatchCommand, FACStatusCommand
│   │   ├── CEPCommand.swift      # + CEPValidateCommand
│   │   ├── RunBashCommand.swift
│   │   └── MetricsCommand.swift
│   └── FBPCLICore/         # library target
│       ├── FBPApiClient.swift
│       ├── Models.swift
│       └── CLIHelpers.swift
└── Tests/
    └── FBPCLITests/
        └── FBPApiClientTests.swift
```

- **No config file path** in repo: no `~/.fbp`, `~/.config/fbp`, or similar. Config is **env + per-command option only**.
- **Backend base URL resolution order** (same in client and every command): `--fbp-url` → `FBP_BASE_URL` env → `http://127.0.0.1:8000`.

---

## 2. CLI command tree (verified)

| Command | Subcommands | Backend path | Notes |
|---------|-------------|--------------|--------|
| `fbp` (default: health) | — | — | Version 0.2.0 |
| `fbp health` | — | GET `/health` | Optional `--json`, `--fbp-url` |
| `fbp nfa` | `consult`, `status` | POST `/nfa/consult`, GET `/nfa/consult/status/{id}` | consult: --from, --to, --matricula (default 1595504) |
| `fbp redesim` | `consulta`, `status` | POST `/cad/redesim/consulta`, GET `/cad/redesim/consulta/status/{id}` | Optional --from, --to |
| `fbp fac` | `batch`, `status` | POST `/fac/batch`, GET `/fac/status/{id}` | batch: --input path to JSON |
| `fbp cep` | `validate` | POST `/api/utils/cep` | CEP arg, --enrich |
| `fbp run-bash` | — | POST `/api/executor/run-bash` | --file or stdin, --timeout (default 60) |
| `fbp metrics` | — | GET `/metrics` | Optional `--json` |

- **Command registration:** All subcommands listed in `main.swift`; build and `fbp --help` confirm.
- **README drift:** README mentions `-u` for base URL; no command exposes short `-u`, only `--fbp-url`.

---

## 3. API client flow (verified)

1. **Config:** Each command builds `baseURL` locally: `fbpUrl ?? ProcessInfo.processInfo.environment["FBP_BASE_URL"] ?? "http://127.0.0.1:8000"`.
2. **Client:** `FBPApiClient(baseURL: baseURL)` — uses `URLSession.shared`, no custom timeout.
3. **Requests:**  
   - GET: `client.get(path:)` or `client.getData(path:)`.  
   - POST: `client.post(path:body:)` (Encodable) or `client.post(path:body:)` ([String: Any] for Metrics raw).
4. **Response:** Decode to typed model (from `Models.swift` or local struct) or raw `Data`/JSON.
5. **Output:** Human-readable lines or `--json` (pretty-printed).
6. **Errors:** Each command catches `ApiError.requestFailed`, `ApiError.networkError`, and generic; prints to stderr and `Darwin.exit(2)` (or RunBash uses script exit code when not `--json`).

**FBPApiClient** (FBPCLICore):

- `init(baseURL: String? = nil)` — env fallback above; strips trailing slash.
- `get<T>(path:)` → `getData` → decode to T.
- `getData(path:)` — no timeout; validates HTTP 2xx; throws `ApiError` (invalidURL, requestFailed, networkError, decodeError). `timeout` enum case exists but is never set by URLSession.
- `post<T,B>(path:body:)` — same; no timeout.
- `post(path:body:[String:Any])` — returns Data; same status handling.

---

## 4. Gap classification

| # | Finding | Category |
|---|--------|----------|
| 1 | Base URL resolution duplicated in 8 places (every command + client). | D – architecture debt |
| 2 | No URLSession timeout; long-running backend can hang CLI. | B – runtime risk |
| 3 | `ApiError.timeout` never thrown (URLSession not configured). | B – runtime risk |
| 4 | RunBash with `--json`: always exits 0; script exit_code not propagated. | B – runtime risk |
| 5 | No explicit “backend unreachable” message (only generic networkError). | C – API-integration / UX |
| 6 | README claims `-u` for base URL; not implemented. | F – docs drift |
| 7 | No verbose/debug mode for diagnosing connectivity. | E – production hardening |
| 8 | FAC status uses local `FACStatusResponse`; could live in Models for consistency. | D – minor debt |
| 9 | Tests only cover client init and invalid URL; no request-building or decode tests. | E – test coverage |
| 10 | Make install path `/usr/local/bin` may need sudo; not documented. | F – docs |

---

## 5. Backend contract (verified against app/main.py)

- `/health` GET → 200, JSON `{ status, machine?, project? }`
- `/metrics` GET → 200, JSON object
- `/nfa/consult` POST → 200, `{ job_id, status }`
- `/nfa/consult/status/{id}` GET → 200, NFA job status
- `/cad/redesim/consulta` POST → 200, `{ job_id, status, execution_id? }`
- `/cad/redesim/consulta/status/{id}` GET → 200
- `/fac/batch` POST → 200, `{ success, job_id, total, processed, ... }`
- `/fac/status/{id}` GET → 200
- `/api/utils/cep` POST → 200, `{ success, data?, errors }`
- `/api/executor/run-bash` POST → 200, `{ success, exit_code, stdout, stderr, duration_ms }`

All paths used by the CLI exist in backend.

---

## 6. Build and test (verified)

- `swift build` — success.
- `swift test` — 4 tests pass (FBPApiClient init and invalid-URL behavior).
- `swift run fbp --help` — lists all subcommands; default subcommand `health`.

---

## 7. Prioritized change plan

1. **Centralize config:** Introduce `FBPConfig` (or single function) in FBPCLICore for base URL resolution; commands and client use it. Reduces duplication and keeps one place for future env (e.g. timeout).
2. **Harden FBPApiClient:** Set `URLSessionConfiguration.timeoutIntervalForRequest` (e.g. 30s); map `URLError.timedOut` to `ApiError.timeout`; optional user-facing “backend unreachable” when appropriate.
3. **Fix RunBash --json:** When `--json`, exit with `response.exit_code` (or 1 on failure) so scripts and automation get correct exit code.
4. **Consistent error handling:** Optional shared helper to print ApiError to stderr and exit(2); ensure timeout and invalidURL get clear messages.
5. **Tests:** Add tests for base URL resolution, request path construction, and (with mock or fixture) decode/error handling where possible without live backend.
6. **Docs:** Update README: remove `-u`, document `FBP_BASE_URL` and `--fbp-url`, install path/sudo, and that backend must be running; add timeout/limitations if we add it.

---

## 8. Changes applied (post-audit)

| Item | Change |
|------|--------|
| Config | Added `FBPConfig` in FBPCLICore: `baseURL(explicit:)` and `defaultBaseURL`. Single place for URL resolution. |
| Client | `FBPApiClient(baseURL: String, timeout: TimeInterval = 30)`. Custom URLSession with timeout. Map `URLError.timedOut` → `ApiError.timeout`. |
| Commands | All 7 command files use `FBPConfig.baseURL(explicit: fbpUrl)` and `exitWithApiError(e)` for `ApiError`. |
| RunBash | With `--json`, exit code now propagates script `exit_code` (was always 0). |
| CLIHelpers | Added `exitWithApiError(_:)` with backend-unreachable message for `URLError.cannotConnectToHost`. |
| Tests | Updated for non-optional client baseURL; added `testConfigBaseURLExplicitOverridesEnv`, `testConfigBaseURLStripsTrailingSlash`, renamed env test to `testConfigBaseURLUsesEnvironmentWhenExplicitNil`. |
| README | Removed `-u`; documented config order, install/sudo, limitations, timeout. |

**Build:** `swift build`  
**Test:** `swift test`  
**Install:** `make install` (or `swift build -c release && cp .build/release/fbp /usr/local/bin/fbp`)
