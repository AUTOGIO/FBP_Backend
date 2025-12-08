#!/bin/bash
# Background server launcher for macOS LaunchAgent
# Ensures FastAPI server runs persistently even when terminal closes

set -euo pipefail

# Absolute paths (required for LaunchAgent)
ROOT="/Users/dnigga/Documents/FBP_Backend"
LOG_DIR="$ROOT/logs"
DEV_SCRIPT="$ROOT/scripts/dev.sh"

# Virtual environment paths (try primary first, then fallback)
PRIMARY_VENV="$ROOT/venv/bin/activate"
FALLBACK_VENV="$HOME/Documents/.venvs/fbp/bin/activate"

# Set PATH for non-interactive environments
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Determine which venv to use
if [ -f "$PRIMARY_VENV" ]; then
    VENV_ACTIVATE="$PRIMARY_VENV"
elif [ -f "$FALLBACK_VENV" ]; then
    VENV_ACTIVATE="$FALLBACK_VENV"
else
    printf "ERROR: Virtual environment not found at:\n  - %s\n  - %s\n" "$PRIMARY_VENV" "$FALLBACK_VENV" >> "$LOG_DIR/server_error.log" 2>&1
    exit 1
fi

# Verify dev.sh exists and is executable
if [ ! -f "$DEV_SCRIPT" ]; then
    printf "ERROR: dev.sh not found at: %s\n" "$DEV_SCRIPT" >> "$LOG_DIR/server_error.log" 2>&1
    exit 1
fi

if [ ! -x "$DEV_SCRIPT" ]; then
    printf "ERROR: dev.sh is not executable: %s\n" "$DEV_SCRIPT" >> "$LOG_DIR/server_error.log" 2>&1
    exit 1
fi

# Change to project root (required for relative paths in dev.sh)
cd "$ROOT" || {
    printf "ERROR: Cannot change to directory: %s\n" "$ROOT" >> "$LOG_DIR/server_error.log" 2>&1
    exit 1
}

# Activate virtual environment
# Note: LaunchAgent runs in non-interactive shell, so we need explicit source
source "$VENV_ACTIVATE" || {
    printf "ERROR: Failed to activate virtual environment: %s\n" "$VENV_ACTIVATE" >> "$LOG_DIR/server_error.log" 2>&1
    exit 1
}

# Set PYTHONPATH
export PYTHONPATH="$ROOT:$PYTHONPATH"

# Run dev.sh in background with nohup
# Redirect both stdout and stderr to log file
# LaunchAgent will also capture these, but this ensures we have logs even if LaunchAgent fails
# Note: We don't use 'exec' here because we want the script to continue running
# LaunchAgent's KeepAlive will restart this if it exits
nohup "$DEV_SCRIPT" >> "$LOG_DIR/server.log" 2>> "$LOG_DIR/server_error.log" &

# Store PID for reference (optional, LaunchAgent tracks it)
echo $! > "$LOG_DIR/server.pid"

# Wait a moment to ensure process started
sleep 2

# Verify process is still running
if ! kill -0 $! 2>/dev/null; then
    printf "ERROR: Process failed to start\n" >> "$LOG_DIR/server_error.log" 2>&1
    exit 1
fi

# Exit successfully - LaunchAgent will keep the nohup process alive
exit 0
