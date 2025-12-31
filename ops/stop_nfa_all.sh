#!/usr/bin/env bash
#
# stop_nfa_all.sh - Safely stop all NFA-related processes
#
# This script:
#   1. Unloads relevant launchd agents (if present)
#   2. Stops FBP/NFA FastAPI servers on ports 9500 and 8000
#   3. Kills leftover Playwright/Chromium processes from NFA runs
#   4. Leaves unrelated processes alone
#
# Usage: ./ops/stop_nfa_all.sh
#
# Safe to run multiple times (idempotent).
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }

echo ""
echo "=============================================="
echo "  NFA Process Cleanup Script"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="
echo ""

# Track what we found/killed
KILLED_SERVERS=0
KILLED_BROWSERS=0
UNLOADED_AGENTS=0

# ============================================
# STEP 1: Unload launchd agents (if present)
# ============================================
log_info "Step 1: Checking launchd agents..."

LAUNCHD_AGENTS=(
    "com.fbp.backend"
    "com.fbp.bootstrap"
    "com.foks.bootstrap"
    "com.foks.backend"
)

LAUNCHAGENT_DIR="$HOME/Library/LaunchAgents"

for agent in "${LAUNCHD_AGENTS[@]}"; do
    # Check if agent is loaded
    if launchctl list 2>/dev/null | grep -q "$agent"; then
        log_info "  Found loaded agent: $agent"
        
        # Try to unload
        plist_path="$LAUNCHAGENT_DIR/${agent}.plist"
        if [[ -f "$plist_path" ]]; then
            if launchctl unload "$plist_path" 2>/dev/null; then
                log_success "  Unloaded: $agent"
                ((UNLOADED_AGENTS++)) || true
            else
                log_warn "  Could not unload: $agent (may already be stopped)"
            fi
        else
            # Try bootout (newer macOS)
            if launchctl bootout "gui/$(id -u)/$agent" 2>/dev/null; then
                log_success "  Booted out: $agent"
                ((UNLOADED_AGENTS++)) || true
            else
                log_warn "  Could not bootout: $agent"
            fi
        fi
    fi
done

if [[ $UNLOADED_AGENTS -eq 0 ]]; then
    log_info "  No launchd agents were loaded."
fi

# ============================================
# STEP 2: Stop servers on ports 9500 and 8000
# ============================================
log_info "Step 2: Stopping servers on ports 9500 and 8000..."

kill_port_gracefully() {
    local port="$1"
    local pids
    
    # Get PIDs listening on this port
    pids=$(lsof -ti "tcp:$port" 2>/dev/null || true)
    
    if [[ -z "$pids" ]]; then
        log_info "  Port $port: No process listening"
        return 0
    fi
    
    for pid in $pids; do
        local proc_name
        proc_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
        log_info "  Port $port: Found PID $pid ($proc_name)"
        
        # Send SIGTERM first (graceful)
        if kill -TERM "$pid" 2>/dev/null; then
            log_info "  Sent SIGTERM to PID $pid"
            
            # Wait up to 5 seconds for graceful shutdown
            for i in {1..10}; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    log_success "  PID $pid terminated gracefully"
                    ((KILLED_SERVERS++)) || true
                    break
                fi
                sleep 0.5
            done
            
            # Force kill if still alive
            if kill -0 "$pid" 2>/dev/null; then
                log_warn "  PID $pid still alive, sending SIGKILL"
                kill -KILL "$pid" 2>/dev/null || true
                sleep 0.5
                if ! kill -0 "$pid" 2>/dev/null; then
                    log_success "  PID $pid killed"
                    ((KILLED_SERVERS++)) || true
                else
                    log_error "  Could not kill PID $pid"
                fi
            fi
        else
            log_warn "  Could not send signal to PID $pid (may have already exited)"
        fi
    done
}

kill_port_gracefully 9500
kill_port_gracefully 8000

# ============================================
# STEP 3: Kill NFA-related Playwright/Chromium
# ============================================
log_info "Step 3: Cleaning up NFA-related browser processes..."

# Patterns that indicate NFA/Playwright browser processes
NFA_BROWSER_PATTERNS=(
    "foks_atf_profile"
    "ms-playwright"
    "playwright"
    "Playwright"
    "--disable-blink-features=AutomationControlled"
)

# Find and kill matching Chromium/Chrome processes
kill_nfa_browsers() {
    local pattern="$1"
    local pids
    
    # Find Chromium/Chrome processes with this pattern in command line
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    
    for pid in $pids; do
        local cmdline
        cmdline=$(ps -p "$pid" -o command= 2>/dev/null || echo "")
        
        # Only kill if it looks like a browser (Chromium, Chrome, chrome_crashpad_handler)
        if echo "$cmdline" | grep -qiE "(chromium|chrome|Google Chrome|Chrome Helper)" 2>/dev/null; then
            local proc_name
            proc_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
            log_info "  Found NFA browser: PID $pid ($proc_name)"
            
            # Send SIGTERM
            if kill -TERM "$pid" 2>/dev/null; then
                sleep 0.5
                if ! kill -0 "$pid" 2>/dev/null; then
                    log_success "  Terminated PID $pid"
                    ((KILLED_BROWSERS++)) || true
                else
                    # Force kill
                    kill -KILL "$pid" 2>/dev/null || true
                    sleep 0.3
                    if ! kill -0 "$pid" 2>/dev/null; then
                        log_success "  Killed PID $pid"
                        ((KILLED_BROWSERS++)) || true
                    fi
                fi
            fi
        fi
    done
}

for pattern in "${NFA_BROWSER_PATTERNS[@]}"; do
    kill_nfa_browsers "$pattern"
done

# Also check for orphaned Chromium processes from temp profiles
# These have --user-data-dir=/tmp/foks_atf_profile_*
orphan_pids=$(pgrep -f "user-data-dir=/tmp/foks_atf" 2>/dev/null || true)
for pid in $orphan_pids; do
    if kill -0 "$pid" 2>/dev/null; then
        log_info "  Found orphaned browser: PID $pid"
        kill -TERM "$pid" 2>/dev/null || true
        sleep 0.3
        kill -KILL "$pid" 2>/dev/null || true
        ((KILLED_BROWSERS++)) || true
    fi
done

if [[ $KILLED_BROWSERS -eq 0 ]]; then
    log_info "  No NFA browser processes found."
fi

# ============================================
# STEP 4: Clean up temp profiles
# ============================================
log_info "Step 4: Cleaning up temporary browser profiles..."

TEMP_PROFILES=$(ls -d /tmp/foks_atf_profile_* 2>/dev/null || true)
if [[ -n "$TEMP_PROFILES" ]]; then
    for profile in $TEMP_PROFILES; do
        if rm -rf "$profile" 2>/dev/null; then
            log_success "  Removed: $profile"
        fi
    done
else
    log_info "  No temporary profiles found."
fi

# ============================================
# STEP 5: Final status report
# ============================================
echo ""
echo "=============================================="
echo "  CLEANUP SUMMARY"
echo "=============================================="
echo ""

log_info "Launchd agents unloaded: $UNLOADED_AGENTS"
log_info "Server processes killed: $KILLED_SERVERS"
log_info "Browser processes killed: $KILLED_BROWSERS"

echo ""
log_info "Port status check:"
echo ""

# Check port 9500
port_9500_status=$(lsof -nP -iTCP:9500 -sTCP:LISTEN 2>/dev/null || true)
if [[ -z "$port_9500_status" ]]; then
    log_success "  Port 9500: FREE"
else
    log_warn "  Port 9500: STILL IN USE"
    echo "$port_9500_status" | head -5
fi

# Check port 8000
port_8000_status=$(lsof -nP -iTCP:8000 -sTCP:LISTEN 2>/dev/null || true)
if [[ -z "$port_8000_status" ]]; then
    log_success "  Port 8000: FREE"
else
    log_warn "  Port 8000: STILL IN USE"
    echo "$port_8000_status" | head -5
fi

echo ""
log_info "Remaining Playwright/Chromium processes:"
remaining=$(pgrep -fl "playwright|chromium|Chrome Helper" 2>/dev/null | grep -v "grep" || true)
if [[ -z "$remaining" ]]; then
    log_success "  None found (clean)"
else
    echo "$remaining" | head -10
fi

echo ""
echo "=============================================="
log_success "NFA cleanup complete!"
echo "=============================================="
echo ""

exit 0
