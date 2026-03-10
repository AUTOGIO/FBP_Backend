#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${FBP_BASE_URL:-http://127.0.0.1:8000}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

require_cmd curl
require_cmd python3

echo "Using backend: ${BASE_URL}"

echo
printf '=== Health ===\n'
curl -s "${BASE_URL}/health" | python3 -m json.tool

create_job() {
  local endpoint="$1"
  local payload="$2"

  curl -s -X POST "${BASE_URL}${endpoint}" \
    -H "Content-Type: application/json" \
    -d "${payload}" | python3 -c 'import sys, json; print(json.load(sys.stdin)["job_id"])'
}

poll_job() {
  local job_id="$1"
  while true; do
    local status
    status="$(curl -s "${BASE_URL}/jobs/${job_id}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')"
    if [[ "$status" == "completed" || "$status" == "failed" ]]; then
      break
    fi
    sleep 1
  done
}

print_job() {
  local job_id="$1"
  echo
  printf 'Job %s\n' "$job_id"
  curl -s "${BASE_URL}/jobs/${job_id}" | python3 -m json.tool
  echo
  printf 'Artifacts for %s\n' "$job_id"
  curl -s "${BASE_URL}/jobs/${job_id}/artifacts" | python3 -m json.tool
}
echo
printf '=== daily-briefing ===\n'
DAILY_JOB="$(create_job "/workflows/daily-briefing" '{"priorities":["Review open PRs","Fix failing checks","Plan sprint tasks"]}')"
poll_job "$DAILY_JOB"
print_job "$DAILY_JOB"

echo
printf '=== doc-summarize (README.md) ===\n'
DOC_JOB="$(create_job "/workflows/doc-summarize" '{"file_path":"README.md"}')"
poll_job "$DOC_JOB"
print_job "$DOC_JOB"

echo
printf '=== risk-scan ===\n'
RISK_PAYLOAD='{"diff":"diff --git a/app/main.py b/app/main.py\n+new endpoint\n+queue processing\n-old handler"}'
RISK_JOB="$(create_job "/workflows/risk-scan" "$RISK_PAYLOAD")"
poll_job "$RISK_JOB"
print_job "$RISK_JOB"

echo
printf '=== Metrics ===\n'
curl -s "${BASE_URL}/metrics" | python3 -m json.tool

echo
echo "Demo complete."
echo "Tip: run with another URL via: FBP_BASE_URL=http://127.0.0.1:8000 bash demo.sh"
