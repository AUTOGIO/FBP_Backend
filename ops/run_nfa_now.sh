#!/usr/bin/env bash

# FBP NFA End-to-End Runner Script
# Uses the unified backend from LaunchAgent (port 8000)
# Does NOT start a server - relies on LaunchAgent-managed backend

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Unified backend URL - always use LaunchAgent-managed server
API_URL="http://localhost:8000"
HEALTH_URL="${API_URL}/health"
CREATE_URL="${API_URL}/api/nfa/create"
BATCH_URL="${API_URL}/api/nfa/batch"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_DIR="${PROJECT_ROOT}/output/nfa/results"
RESULTS_FILE="${RESULTS_DIR}/run_${TIMESTAMP}.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== FBP NFA Auto-Run Script ===${NC}"
echo "Project Root: $PROJECT_ROOT"
echo "Backend URL: $API_URL (LaunchAgent-managed)"
echo ""

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"

# Pre-flight health check - fail fast if backend is unavailable
echo -e "${YELLOW}Step 1: Checking backend availability...${NC}"
if ! curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
    echo -e "${RED}✗ Backend unavailable at $API_URL${NC}"
    echo -e "${YELLOW}Please ensure LaunchAgent is running:${NC}"
    echo "  launchctl list | grep com.fbp.backend"
    echo "  launchctl load ~/Library/LaunchAgents/com.fbp.backend.plist"
    exit 1
fi
echo -e "${GREEN}✓ Backend is available${NC}"
echo ""

# Check if batch mode is requested
BATCH_MODE=false
if [ "$1" = "--batch" ] || [ "$1" = "-b" ] || [ "$1" = "batch" ]; then
    BATCH_MODE=true
    echo -e "${GREEN}Batch mode enabled${NC}"
fi

# Load credentials from .env if available
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -E '^NFA_USERNAME=|^NFA_PASSWORD=' "$PROJECT_ROOT/.env" | xargs)
fi

# Allow credentials to be passed as environment variables or use defaults
NFA_USERNAME="${NFA_USERNAME:-}"
NFA_PASSWORD="${NFA_PASSWORD:-}"

if [ -z "$NFA_USERNAME" ] || [ -z "$NFA_PASSWORD" ]; then
    echo -e "${YELLOW}Warning: NFA credentials not found.${NC}"
    echo "Please set NFA_USERNAME and NFA_PASSWORD in .env file or as environment variables"
    echo "Continuing anyway (will fail if credentials are required)..."
fi

# Prepare NFA payload
if [ "$BATCH_MODE" = true ]; then
    echo -e "${YELLOW}Step 2: Preparing batch NFA payload...${NC}"
    PAYLOAD=$(cat <<EOF
{
  "emitente_cnpj": "28842017000105",
  "destinatarios": [
    "73825506215",
    "11122233344",
    "55566677788"
  ],
  "credentials": {
    "usuario": "${NFA_USERNAME}",
    "senha": "${NFA_PASSWORD}"
  },
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
    CREATE_URL="$BATCH_URL"
else
    echo -e "${YELLOW}Step 2: Preparing single NFA payload...${NC}"
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
    "cpf": "73825506215",
    "documento": "73825506215"
  },
  "produtos": [
    {
      "ncm": "0000.00.00",
      "descricao": "1 - SID241",
      "detalhamento_produto": "1 - SID241",
      "unidade": "UN",
      "quantidade": 1,
      "valor_unitario": 1100,
      "aliquota": 0,
      "cst": "41",
      "receita": "1199 - ICMS - OUTROS (COMERCIO E INDUSTRIA)"
    }
  ],
  "informacoes_adicionais": "Remessa por conta de contrato de locacao",
  "credentials": {
    "usuario": "${NFA_USERNAME}",
    "senha": "${NFA_PASSWORD}"
  },
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
fi

# Send NFA creation request
if [ "$BATCH_MODE" = true ]; then
    echo -e "${YELLOW}Step 3: Sending batch NFA creation request...${NC}"
else
    echo -e "${YELLOW}Step 3: Sending single NFA creation request...${NC}"
fi
echo "URL: $CREATE_URL"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$CREATE_URL" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" || echo -e "\n000")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

# Save response to file
echo "$BODY" | jq . > "$RESULTS_FILE" 2>/dev/null || echo "$BODY" > "$RESULTS_FILE"

# Display results
echo -e "${YELLOW}Step 4: Results${NC}"
echo "HTTP Status Code: $HTTP_CODE"
echo "Results saved to: $RESULTS_FILE"
echo ""
echo -e "${GREEN}=== Response Body ===${NC}"
echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
echo ""

# Check if successful
if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(echo "$BODY" | jq -r '.success // false' 2>/dev/null || echo "false")
    if [ "$SUCCESS" = "true" ]; then
        if [ "$BATCH_MODE" = true ]; then
            echo -e "${GREEN}✓ Batch NFA creation completed successfully!${NC}"
            GENERATED=$(echo "$BODY" | jq -r '.data.generated // 0' 2>/dev/null || echo "0")
            TOTAL=$(echo "$BODY" | jq -r '.data.total // 0' 2>/dev/null || echo "0")
            echo -e "${GREEN}Generated: ${GENERATED}/${TOTAL} NFAs${NC}"
            
            # Show PDF paths
            echo -e "${YELLOW}PDFs saved to:${NC}"
            echo "$BODY" | jq -r '.data.results[]? | "  CPF \(.cpf): DAR=\(.dar_pdf // "N/A"), NFA=\(.nota_pdf // "N/A")"' 2>/dev/null || echo "  (Unable to parse results)"
        else
            echo -e "${GREEN}✓ NFA creation completed successfully!${NC}"
            
            # Extract NFA ID if available
            NFA_ID=$(echo "$BODY" | jq -r '.data.nfa_id // .data.nfa_number // "N/A"' 2>/dev/null || echo "N/A")
            echo -e "${GREEN}NFA ID: ${NFA_ID}${NC}"
            
            # Show PDF paths
            DAR_PDF=$(echo "$BODY" | jq -r '.data.dar_pdf // "N/A"' 2>/dev/null || echo "N/A")
            NOTA_PDF=$(echo "$BODY" | jq -r '.data.nota_pdf // "N/A"' 2>/dev/null || echo "N/A")
            echo -e "${GREEN}DAR PDF: ${DAR_PDF}${NC}"
            echo -e "${GREEN}Nota PDF: ${NOTA_PDF}${NC}"
        fi
        
        EXIT_CODE=0
    else
        echo -e "${RED}✗ NFA creation failed (success=false)${NC}"
        ERRORS=$(echo "$BODY" | jq -r '.errors[]?' 2>/dev/null || echo "Unknown error")
        echo -e "${RED}Errors:${NC}"
        echo "$ERRORS"
        EXIT_CODE=1
    fi
else
    echo -e "${RED}✗ Request failed with HTTP $HTTP_CODE${NC}"
    EXIT_CODE=1
fi

# Summary
echo ""
echo -e "${YELLOW}=== Summary ===${NC}"
echo "Backend URL: $API_URL"
echo "Results file: $RESULTS_FILE"
echo "PDFs: ${PROJECT_ROOT}/output/nfa/pdf/"
echo "Screenshots: ${PROJECT_ROOT}/output/nfa/screenshots/"
echo "Logs: ${PROJECT_ROOT}/logs/nfa/"
echo ""
echo "Usage:"
echo "  Single NFA:  $0 [single]"
echo "  Batch NFAs:  $0 --batch"

exit $EXIT_CODE
