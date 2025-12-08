#!/bin/bash

# FBP Environment Auto-Fix Script
# Automatically fixes common environment issues for macOS M3/M4

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== FBP Environment Auto-Fix ===${NC}"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Detect Python version
PYTHON_CMD="python3"
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo -e "${RED}✗ Python3 not found${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"

# Find or create virtual environment
VENV_DIR=""
if [ -d "$PROJECT_ROOT/venv" ]; then
    VENV_DIR="$PROJECT_ROOT/venv"
elif [ -d "$PROJECT_ROOT/.venv" ]; then
    VENV_DIR="$PROJECT_ROOT/.venv"
else
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    "$PYTHON_CMD" -m venv "$PROJECT_ROOT/venv"
    VENV_DIR="$PROJECT_ROOT/venv"
fi

echo -e "${GREEN}✓ Virtual environment: $VENV_DIR${NC}"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install/upgrade dependencies
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
    pip install -r "$PROJECT_ROOT/requirements.txt" --quiet
    echo -e "${GREEN}✓ Dependencies installed${NC}"
fi

# Verify Playwright
echo -e "${YELLOW}Verifying Playwright...${NC}"
if ! python3 -c "import playwright" 2>/dev/null; then
    echo -e "${YELLOW}Installing Playwright...${NC}"
    pip install playwright>=1.40.0 --quiet
fi

# Install Chromium browser
echo -e "${YELLOW}Verifying Chromium browser...${NC}"
if ! python3 -m playwright install chromium --dry-run 2>/dev/null; then
    echo -e "${YELLOW}Installing Chromium browser...${NC}"
    python3 -m playwright install chromium
fi
echo -e "${GREEN}✓ Playwright and Chromium ready${NC}"

# Create necessary directories
echo -e "${YELLOW}Creating output directories...${NC}"
mkdir -p "$PROJECT_ROOT/output/nfa/pdf"
mkdir -p "$PROJECT_ROOT/output/nfa/results"
mkdir -p "$PROJECT_ROOT/output/nfa/screenshots"
mkdir -p "$PROJECT_ROOT/logs/nfa"
mkdir -p "$PROJECT_ROOT/input"
echo -e "${GREEN}✓ Directories created${NC}"

# Create CPF batch file if missing
if [ ! -f "$PROJECT_ROOT/input/cpf_batch.json" ]; then
    echo -e "${YELLOW}Creating CPF batch file...${NC}"
    cat > "$PROJECT_ROOT/input/cpf_batch.json" << 'EOF'
{
  "destinatarios": [
    "73825506215"
  ]
}
EOF
    echo -e "${GREEN}✓ CPF batch file created${NC}"
fi

echo ""
echo -e "${GREEN}=== Environment Auto-Fix Complete ===${NC}"
echo "Virtual environment: $VENV_DIR"
echo "To activate: source $VENV_DIR/bin/activate"
