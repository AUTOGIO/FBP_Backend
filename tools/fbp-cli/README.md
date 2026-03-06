# fbp – Swift Native FBP CLI

Native macOS command-line client for FBP Backend. Built with Swift Package Manager and ArgumentParser.

## Requirements

- macOS 13+
- Swift 5.9+
- FBP Backend running (default: http://127.0.0.1:8000)

## Build

```bash
swift build
swift run fbp --help
```

## Install

```bash
make install
# or:
swift build -c release
cp .build/release/fbp /usr/local/bin/fbp
```

## Usage

| Command | Description |
|---------|-------------|
| `fbp health` | Check FBP backend health |
| `fbp nfa consult --from DD/MM/YYYY --to DD/MM/YYYY` | Create NFA consultation job |
| `fbp nfa status <job_id> [--wait]` | Get NFA job status (--wait polls until done) |
| `fbp redesim consulta` | Create REDESIM consulta job |
| `fbp redesim status <job_id> [--wait]` | Get REDESIM job status (--wait polls) |
| `fbp fac batch --input facs.json` | Process FAC batch |
| `fbp fac status <job_id>` | Get FAC batch status |
| `fbp cep validate <cep>` | Validate Brazilian postal code |
| `fbp run-bash --file script.sh` | Run bash script via FBP executor |
| `fbp metrics` | Get system metrics |

## Environment

- `FBP_BASE_URL` – FBP base URL (default: http://127.0.0.1:8000)
- `--fbp-url` / `-u` – Override per command

## Examples

```bash
# Health check
fbp health
fbp health --json

# NFA consultation (create job, then poll until done)
fbp nfa consult --from 08/12/2025 --to 10/12/2025 --matricula 1595504
fbp nfa status <job_id>
fbp nfa status <job_id> --wait   # poll every 3s until completed/failed

# Run a script
echo 'echo "Hello from FBP"' | fbp run-bash
fbp run-bash --file /path/to/script.sh --timeout 30

# CEP validation
fbp cep validate 58010120
fbp cep validate 58010120 --enrich --json
```
