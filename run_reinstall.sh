#!/usr/bin/env bash

set -euo pipefail

PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

CHROMIUM_APP="/Applications/Chromium.app"
PLAYWRIGHT_CACHE="$HOME/Library/Caches/ms-playwright"
USER_CHROMIUM_SUPPORT="$HOME/Library/Application Support/Chromium"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3.11 || true)}"
if [ -z "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi

timestamp() { date +"%Y-%m-%d %H:%M:%S"; }
log() { echo "[$(timestamp)] $*"; }
fail() { echo "[$(timestamp)] ERROR: $*" >&2; exit 1; }

spinner() {
  local pid=$1
  local marks='|/-\\'
  local i=0
  while kill -0 "$pid" 2>/dev/null; do
    printf "\r[%s] %s" "$(timestamp)" "${marks:i++%${#marks}:1}"
    sleep 0.1
  done
  printf "\r"
}

run_step() {
  local title="$1"; shift
  log "$title"
  (
    set -euo pipefail
    "$@"
  ) &
  local pid=$!
  spinner "$pid"
  if wait "$pid"; then
    log "$title ✓"
  else
    fail "$title failed"
  fi
}

command_exists() { command -v "$1" >/dev/null 2>&1; }

assert_python() {
  [ -n "$PYTHON_BIN" ] || fail "No Python found; install Python 3.11+"
  command_exists "$PYTHON_BIN" || fail "python3.11 not found; install Python 3.11+"
  local version
  version=$("$PYTHON_BIN" -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
  "$PYTHON_BIN" - <<'PY' || fail "Python 3.11+ required (found '"$version"')"
import sys
major, minor = sys.version_info[:2]
sys.exit(0 if (major, minor) >= (3, 11) else 1)
PY
  log "Python version OK: $version"
}

assert_homebrew() {
  if command_exists brew; then
    log "Homebrew detected at $(command -v brew)"
    return
  fi
  if [ -x "/opt/homebrew/bin/brew" ]; then
    log "Homebrew available at /opt/homebrew/bin/brew"
    return
  fi
  if [ -x "/usr/local/bin/brew" ]; then
    log "Homebrew available at /usr/local/bin/brew"
    return
  fi
  log "Homebrew not found; skipping brew uninstall step"
}

assert_playwright_cli() {
  if "$PYTHON_BIN" - <<'PY'
try:
    import playwright  # noqa: F401
    import playwright.__main__  # noqa: F401
except Exception:
    raise SystemExit(1)
PY
  then
    log "Playwright Python package detected"
    return
  fi
  log "Playwright Python package missing; installing via pip"
  "$PYTHON_BIN" -m pip install --upgrade playwright >/dev/null
  log "Playwright Python package installed"
}

brew_uninstall_chromium() {
  if command_exists brew; then
    if brew list --cask chromium >/dev/null 2>&1; then
      brew uninstall --cask --force chromium >/dev/null
      log "Removed Homebrew Chromium cask"
    else
      log "Homebrew Chromium cask not installed"
    fi
  else
    log "brew not available; skipping brew uninstall"
  fi
}

remove_manual_chromium() {
  if [ -d "$CHROMIUM_APP" ] || [ -L "$CHROMIUM_APP" ]; then
    rm -rf "$CHROMIUM_APP"
    log "Removed $CHROMIUM_APP"
  else
    log "No existing /Applications/Chromium.app found"
  fi
  if [ -d "$USER_CHROMIUM_SUPPORT" ]; then
    rm -rf "$USER_CHROMIUM_SUPPORT"
    log "Cleared user Chromium profile data at $USER_CHROMIUM_SUPPORT"
  else
    log "No Chromium user data at $USER_CHROMIUM_SUPPORT"
  fi
}

clear_playwright_cache() {
  if [ -d "$PLAYWRIGHT_CACHE" ]; then
    rm -rf "$PLAYWRIGHT_CACHE"
    log "Cleared Playwright cache at $PLAYWRIGHT_CACHE"
  else
    log "No Playwright cache found at $PLAYWRIGHT_CACHE"
  fi
}

install_playwright_chromium() {
  "$PYTHON_BIN" -m playwright install chromium --with-deps >/dev/null
  log "Playwright chromium installed"
}

resolve_playwright_chromium_app() {
  "$PYTHON_BIN" - <<'PY'
import glob
import os
import pathlib

base = os.path.expanduser("~/Library/Caches/ms-playwright")
candidates = sorted(glob.glob(os.path.join(base, "chromium-*")), key=os.path.getmtime, reverse=True)
for cand in candidates:
    app = pathlib.Path(cand) / "chrome-mac" / "Chromium.app"
    if app.exists():
        print(app)
        raise SystemExit(0)
raise SystemExit("Chromium.app not found in Playwright cache")
PY
}

apply_gatekeeper_exemption() {
  local app_path="$1"
  if [ -d "$app_path" ]; then
    xattr -dr com.apple.quarantine "$app_path" || true
    log "Removed Gatekeeper quarantine attributes"
  fi
}

link_to_applications() {
  local app_path="$1"
  ln -sfn "$app_path" "$CHROMIUM_APP"
  log "Linked $app_path -> $CHROMIUM_APP"
}

verify_chromium_version() {
  if [ -x "$CHROMIUM_APP/Contents/MacOS/Chromium" ]; then
    "$CHROMIUM_APP/Contents/MacOS/Chromium" --version
  else
    fail "Chromium binary not found at $CHROMIUM_APP"
  fi
}

log "=== Chromium Playwright Reinstaller (Apple Silicon) ==="
assert_python
assert_homebrew
assert_playwright_cli

log "--- Removing existing Chromium installations ---"
run_step "Uninstall Homebrew Chromium (if present)" brew_uninstall_chromium
run_step "Remove manual Chromium installs" remove_manual_chromium
run_step "Clear Playwright Chromium cache" clear_playwright_cache

log "--- Installing Playwright Chromium ---"
run_step "Install Playwright Chromium" install_playwright_chromium

log "--- Linking Playwright Chromium to /Applications ---"
PLAYWRIGHT_APP_PATH=$(resolve_playwright_chromium_app)
log "Playwright Chromium located at $PLAYWRIGHT_APP_PATH"
run_step "Remove Gatekeeper quarantine" apply_gatekeeper_exemption "$PLAYWRIGHT_APP_PATH"
run_step "Symlink Chromium into /Applications" link_to_applications "$PLAYWRIGHT_APP_PATH"

log "--- Verifying installation ---"
run_step "Chromium version check" verify_chromium_version

log "Chromium reinstall and linking complete."

