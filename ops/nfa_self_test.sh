#!/usr/bin/env bash

# NFA Self-Test Script
# Runs diagnostic test for NFA automation system

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Unified backend URL - always use LaunchAgent-managed server (port 8000)
API_URL="http://localhost:8000"
BASE_URL="$API_URL"
HEALTH_URL="${BASE_URL}/health"
CREATE_URL="${BASE_URL}/api/nfa/create"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_CPF="73825506215"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== NFA Self-Test Diagnostic Script ===${NC}"
echo "Project Root: $PROJECT_ROOT"
echo "Test CPF: $TEST_CPF"
echo ""

# Function to check if server is running
check_server() {
    curl -s -f "$HEALTH_URL" > /dev/null 2>&1
}

# Check if server is running
if ! check_server; then
    echo -e "${RED}✗ Backend is not running at ${API_URL}${NC}"
    echo -e "${YELLOW}Please ensure LaunchAgent is running:${NC}"
    echo "  launchctl list | grep com.fbp.backend"
    echo "  launchctl load ~/Library/LaunchAgents/com.fbp.backend.plist"
    exit 1
fi

echo -e "${GREEN}✓ Server is running${NC}"
echo ""

# Test 1: Health check
echo -e "${YELLOW}Test 1: Health Check${NC}"
HEALTH_RESPONSE=$(curl -s "$HEALTH_URL")
if echo "$HEALTH_RESPONSE" | grep -q "ok\|healthy\|status"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    echo "Response: $HEALTH_RESPONSE"
fi
echo ""

# Test 2: NFA Creation (single)
echo -e "${YELLOW}Test 2: Single NFA Creation${NC}"
PAYLOAD=$(cat <<EOF
{
  "natureza_operacao": "REMESSA",
  "motivo": "DESPACHO",
  "reparticao_fiscal": "90102008",
  "codigo_municipio": "2051-6",
  "tipo_operacao": "SAIDA",
  "cfop": "6908",
  "emitente": {
    "cnpj": "28842017000105"
  },
  "destinatario": {
    "documento": "$TEST_CPF"
  },
  "produtos": [
    {
      "ncm": "0000.00.00",
      "descricao": "1 - SID241",
      "unidade": "UN",
      "quantidade": 1,
      "valor_unitario": 1100,
      "aliquota": 0,
      "cst": "41",
      "receita": "1199 - ICMS - OUTROS (COMERCIO E INDUSTRIA)"
    }
  ],
  "config": {
    "browser": {
      "headless": false,
      "viewport": {
        "width": 1920,
        "height": 1080
      }
    },
    "timeouts": {
      "navigation": 30000,
      "element_wait": 20000
    },
    "paths": {
      "screenshots_dir": "${PROJECT_ROOT}/output/nfa/screenshots"
    }
  }
}
EOF
)

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$CREATE_URL" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" || echo -e "\n000")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "HTTP Status Code: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(echo "$BODY" | jq -r '.success // false' 2>/dev/null || echo "false")
    if [ "$SUCCESS" = "true" ]; then
        echo -e "${GREEN}✓ NFA creation test passed${NC}"
        NFA_ID=$(echo "$BODY" | jq -r '.data.nfa_id // .data.nfa_number // "N/A"' 2>/dev/null || echo "N/A")
        echo "NFA ID: $NFA_ID"
    else
        echo -e "${RED}✗ NFA creation failed (success=false)${NC}"
        ERRORS=$(echo "$BODY" | jq -r '.errors[]?' 2>/dev/null || echo "Unknown error")
        echo "Errors:"
        echo "$ERRORS"
    fi
else
    echo -e "${RED}✗ Request failed with HTTP $HTTP_CODE${NC}"
    echo "Response: $BODY"
fi
echo ""

# Test 3: Check output directories
echo -e "${YELLOW}Test 3: Output Directories${NC}"
DIRS=(
    "output/nfa/pdf"
    "output/nfa/results"
    "output/nfa/screenshots"
    "logs/nfa"
    "input"
)

for dir in "${DIRS[@]}"; do
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        echo -e "${GREEN}✓ Directory exists: $dir${NC}"
    else
        echo -e "${YELLOW}⚠ Directory missing: $dir (will be created on first run)${NC}"
    fi
done
echo ""

# Test 4: Check CPF batch file
echo -e "${YELLOW}Test 4: CPF Batch File${NC}"
CPF_BATCH_FILE="$PROJECT_ROOT/input/cpf_batch.json"
if [ -f "$CPF_BATCH_FILE" ]; then
    echo -e "${GREEN}✓ CPF batch file exists${NC}"
    CPF_COUNT=$(jq '.destinatarios | length' "$CPF_BATCH_FILE" 2>/dev/null || echo "0")
    echo "CPFs in batch file: $CPF_COUNT"
    if [ "$CPF_COUNT" -gt 0 ]; then
        echo "Sample CPFs:"
        jq -r '.destinatarios[:3][]' "$CPF_BATCH_FILE" 2>/dev/null | head -3 | while read cpf; do
            echo "  - $cpf"
        done
    fi
else
    echo -e "${YELLOW}⚠ CPF batch file not found: $CPF_BATCH_FILE${NC}"
fi
echo ""

# Test 5: Check Python modules
echo -e "${YELLOW}Test 5: Python Module Imports${NC}"
PYTHON_MODULES=(
    "app.modules.nfa.delays"
    "app.modules.nfa.form_filler"
    "app.modules.nfa.batch_processor"
    "app.modules.nfa.pdf_downloader"
    "app.modules.nfa.data_validator"
)

for module in "${PYTHON_MODULES[@]}"; do
    if python3 -c "import $module" 2>/dev/null; then
        echo -e "${GREEN}✓ Module importable: $module${NC}"
    else
        echo -e "${RED}✗ Module import failed: $module${NC}"
    fi
done
echo ""

# Test 6: Check Playwright
echo -e "${YELLOW}Test 6: Playwright Installation${NC}"
if python3 -c "import playwright" 2>/dev/null; then
    echo -e "${GREEN}✓ Playwright installed${NC}"
    if python3 -m playwright install chromium --dry-run 2>/dev/null; then
        echo -e "${GREEN}✓ Chromium browser available${NC}"
    else
        echo -e "${YELLOW}⚠ Chromium browser not installed${NC}"
        echo "  Run: python3 -m playwright install chromium"
    fi
else
    echo -e "${RED}✗ Playwright not installed${NC}"
    echo "  Run: pip install playwright"
fi
echo ""

# Summary
echo -e "${BLUE}=== Test Summary ===${NC}"
echo "Test completed at: $(date)"
echo "Check logs at: $PROJECT_ROOT/logs/nfa/"
echo "Check screenshots at: $PROJECT_ROOT/output/nfa/screenshots/"
echo "Check PDFs at: $PROJECT_ROOT/output/nfa/pdf/"
echo ""
