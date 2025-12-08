#!/bin/bash

# NFA System Validation Script
# Validates the entire NFA automation system end-to-end

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Unified backend URL - always use LaunchAgent-managed server (port 8000)
API_URL="http://localhost:8000"
BASE_URL="$API_URL"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== NFA System Validation ===${NC}"
echo "Project Root: $PROJECT_ROOT"
echo ""

ERRORS=0
WARNINGS=0

# Test 1: Validate Python imports
echo -e "${YELLOW}Test 1: Python Module Imports${NC}"
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/Users/dnigga/Documents/FBP_Backend')

try:
    from app.modules.nfa.form_filler import fill_nfa_form_complete, preencher_nfa
    print("✓ form_filler")
except Exception as e:
    print(f"✗ form_filler: {e}")
    sys.exit(1)

try:
    from app.modules.nfa.pdf_downloader import download_nfa_pdfs, download_dar_pdf, download_nota_fiscal_pdf
    print("✓ pdf_downloader")
except Exception as e:
    print(f"✗ pdf_downloader: {e}")
    sys.exit(1)

try:
    from app.modules.nfa.batch_processor import BatchNFAProcessor
    print("✓ batch_processor")
except Exception as e:
    print(f"✗ batch_processor: {e}")
    sys.exit(1)

try:
    from app.modules.nfa.delays import DEFAULT_DELAY, FIELD_DELAY, NETWORK_IDLE_TIMEOUT
    print("✓ delays")
except Exception as e:
    print(f"✗ delays: {e}")
    sys.exit(1)

print("✅ All imports OK")
PYEOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All Python imports successful${NC}"
else
    echo -e "${RED}✗ Python imports failed${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Test 2: Validate all NFA components exist
echo -e "${YELLOW}Test 2: Component Files${NC}"
COMPONENTS=(
    "app/modules/nfa/atf_login.py"
    "app/modules/nfa/atf_frames.py"
    "app/modules/nfa/atf_selectors.py"
    "app/modules/nfa/form_filler.py"
    "app/modules/nfa/produto_filler.py"
    "app/modules/nfa/emitente_filler.py"
    "app/modules/nfa/destinatario_filler.py"
    "app/modules/nfa/endereco_filler.py"
    "app/modules/nfa/batch_processor.py"
    "app/modules/nfa/data_validator.py"
    "app/modules/nfa/delays.py"
    "app/modules/nfa/campos_fixos_filler.py"
    "app/modules/nfa/informacoes_adicionais_filler.py"
    "app/modules/nfa/form_submitter.py"
    "app/modules/nfa/pdf_downloader.py"
    "app/modules/nfa/screenshot_utils.py"
    "app/modules/nfa/nfa_context.py"
)

for component in "${COMPONENTS[@]}"; do
    if [ -f "$PROJECT_ROOT/$component" ]; then
        echo -e "${GREEN}✓${NC} $component"
    else
        echo -e "${RED}✗${NC} $component (MISSING)"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# Test 3: Validate scripts
echo -e "${YELLOW}Test 3: Scripts${NC}"
SCRIPTS=(
    "ops/run_nfa_now.sh"
    "ops/nfa_self_test.sh"
    "ops/scripts/foks_env_autofix.sh"
    "ops/scripts/foks_boot.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$PROJECT_ROOT/$script" ]; then
        if [ -x "$PROJECT_ROOT/$script" ]; then
            echo -e "${GREEN}✓${NC} $script (executable)"
        else
            echo -e "${YELLOW}⚠${NC} $script (not executable)"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo -e "${RED}✗${NC} $script (MISSING)"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# Test 4: Validate directories
echo -e "${YELLOW}Test 4: Output Directories${NC}"
DIRS=(
    "output/nfa/pdf"
    "output/nfa/results"
    "output/nfa/screenshots"
    "logs/nfa"
    "input"
)

for dir in "${DIRS[@]}"; do
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        echo -e "${GREEN}✓${NC} $dir"
    else
        echo -e "${YELLOW}⚠${NC} $dir (will be created on first run)"
        WARNINGS=$((WARNINGS + 1))
    fi
done
echo ""

# Test 5: Validate CPF batch file
echo -e "${YELLOW}Test 5: CPF Batch File${NC}"
CPF_BATCH="$PROJECT_ROOT/input/cpf_batch.json"
if [ -f "$CPF_BATCH" ]; then
    if command -v jq &> /dev/null; then
        if jq empty "$CPF_BATCH" 2>/dev/null; then
            CPF_COUNT=$(jq '.destinatarios | length' "$CPF_BATCH" 2>/dev/null || echo "0")
            echo -e "${GREEN}✓${NC} CPF batch file (valid JSON, $CPF_COUNT CPFs)"
        else
            echo -e "${RED}✗${NC} CPF batch file (invalid JSON)"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo -e "${YELLOW}⚠${NC} CPF batch file exists (jq not installed for validation)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${YELLOW}⚠${NC} CPF batch file not found (will be created on first run)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Test 6: Validate no hardcoded delays
echo -e "${YELLOW}Test 6: Delay System${NC}"
HARDCODED_DELAYS=$(grep -r "wait_for_timeout([0-9]" "$PROJECT_ROOT/app/modules/nfa" 2>/dev/null | grep -v "delays.py" | wc -l | tr -d ' ')
if [ "$HARDCODED_DELAYS" -eq 0 ]; then
    echo -e "${GREEN}✓${NC} No hardcoded delays found (using delays.py)"
else
    echo -e "${RED}✗${NC} Found $HARDCODED_DELAYS hardcoded delays"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Test 7: Validate no NOTAS_AVULSAS references in code
echo -e "${YELLOW}Test 7: NOTAS_AVULSAS References${NC}"
NOTAS_REFS=$(grep -r "NOTAS_AVULSAS\|/Projects/NOTAS" "$PROJECT_ROOT/app" 2>/dev/null | grep -v ".pyc" | wc -l | tr -d ' ')
if [ "$NOTAS_REFS" -eq 0 ]; then
    echo -e "${GREEN}✓${NC} No NOTAS_AVULSAS references in code"
else
    echo -e "${RED}✗${NC} Found $NOTAS_REFS NOTAS_AVULSAS references"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Summary
echo -e "${BLUE}=== Validation Summary ===${NC}"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All critical tests passed${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠ $WARNINGS warnings (non-critical)${NC}"
    fi
    exit 0
else
    echo -e "${RED}✗ $ERRORS errors found${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠ $WARNINGS warnings${NC}"
    fi
    exit 1
fi
