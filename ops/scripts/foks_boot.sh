#!/bin/bash

# FBP Boot Script
# Starts FBP server with proper environment setup for macOS M3/M4

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# NOTE: This script starts a temporary server for manual testing
# For production, use the LaunchAgent-managed backend on port 8000
PORT="${PORT:-9500}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== FBP Boot Script ===${NC}"
echo "Project Root: $PROJECT_ROOT"
echo "Port: $PORT"
echo ""

# Find virtual environment
VENV_DIR=""
if [ -d "$PROJECT_ROOT/venv" ]; then
    VENV_DIR="$PROJECT_ROOT/venv"
elif [ -d "$PROJECT_ROOT/.venv" ]; then
    VENV_DIR="$PROJECT_ROOT/.venv"
else
    echo -e "${RED}✗ Virtual environment not found${NC}"
    echo -e "${YELLOW}Run: ./ops/scripts/foks_env_autofix.sh${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Verify dependencies
echo -e "${YELLOW}Verifying dependencies...${NC}"
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo -e "${RED}✗ uvicorn not found${NC}"
    echo -e "${YELLOW}Run: ./ops/scripts/foks_env_autofix.sh${NC}"
    exit 1
fi

if ! python3 -c "import playwright" 2>/dev/null; then
    echo -e "${RED}✗ playwright not found${NC}"
    echo -e "${YELLOW}Run: ./ops/scripts/foks_env_autofix.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Dependencies verified${NC}"

# Check if server is already running
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}Port $PORT is already in use${NC}"
    read -p "Kill existing process? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "uvicorn.*main:app.*port.*${PORT}" || pkill -f "python.*main.py.*port.*${PORT}" || true
        sleep 2
        echo -e "${GREEN}✓ Existing process killed${NC}"
    else
        echo -e "${RED}Exiting...${NC}"
        exit 1
    fi
fi

# Start server
echo -e "${YELLOW}Starting FBP server on port $PORT...${NC}"
echo "Logs: $PROJECT_ROOT/logs/server.log"
echo ""

python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" \
    > "$PROJECT_ROOT/logs/server.log" 2>&1 &

SERVER_PID=$!
echo -e "${GREEN}✓ Server started with PID: $SERVER_PID${NC}"
echo ""
echo -e "${BLUE}Server running at: http://localhost:$PORT${NC}"
echo -e "${BLUE}Health check: http://localhost:$PORT/health${NC}"
echo -e "${BLUE}API docs: http://localhost:$PORT/docs${NC}"
echo ""
echo "To stop: kill $SERVER_PID"
echo "To view logs: tail -f $PROJECT_ROOT/logs/server.log"
