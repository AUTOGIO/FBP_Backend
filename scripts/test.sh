#!/bin/bash
# Run all tests: pytest + ruff + mypy
# Comprehensive test suite for FBP Backend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$HOME/Documents/.venvs/fbp"

# Activate venv
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH"
    echo "💡 Run: python3 -m venv $VENV_PATH"
    exit 1
fi

source "$VENV_PATH/bin/activate"

cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 Running test suite..."

# 1. Ruff linting
echo -e "\n${YELLOW}1. Running Ruff linting...${NC}"
if ruff check app tests; then
    echo -e "${GREEN}✅ Ruff linting passed${NC}"
else
    echo -e "${RED}❌ Ruff linting failed${NC}"
    exit 1
fi

# 2. Ruff formatting check
echo -e "\n${YELLOW}2. Checking code formatting...${NC}"
if ruff format --check app tests; then
    echo -e "${GREEN}✅ Code formatting OK${NC}"
else
    echo -e "${RED}❌ Code formatting issues found${NC}"
    echo "💡 Run: ruff format app tests"
    exit 1
fi

# 3. MyPy type checking
echo -e "\n${YELLOW}3. Running MyPy type checking...${NC}"
if mypy app --ignore-missing-imports; then
    echo -e "${GREEN}✅ MyPy type checking passed${NC}"
else
    echo -e "${YELLOW}⚠️  MyPy found some issues (non-blocking)${NC}"
fi

# 4. Pytest
echo -e "\n${YELLOW}4. Running pytest...${NC}"
if pytest tests -v --tb=short; then
    echo -e "${GREEN}✅ All tests passed${NC}"
else
    echo -e "${RED}❌ Tests failed${NC}"
    exit 1
fi

echo -e "\n${GREEN}🎉 All checks passed!${NC}"

