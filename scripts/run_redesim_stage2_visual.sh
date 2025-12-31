#!/bin/bash
# Visual launcher for REDESIM Stage 2 automation
# Opens browser in visible mode for interactive inspection

set -e

cd "$(dirname "$0")/.."

echo "=========================================="
echo "REDESIM Stage 2 Automation - Visual Mode"
echo "=========================================="
echo ""

# Check for credentials
if [ -z "$ATF_USERNAME" ] || [ -z "$ATF_PASSWORD" ]; then
    echo "⚠️  ATF credentials not found in environment"
    echo ""
    read -p "Enter ATF Username: " ATF_USERNAME
    read -s -p "Enter ATF Password: " ATF_PASSWORD
    echo ""
    echo ""
    export ATF_USERNAME
    export ATF_PASSWORD
fi

# Optional Gmail credentials
if [ -z "$GMAIL_CREDENTIALS_PATH" ]; then
    echo "ℹ️  Gmail credentials not set (draft creation will be skipped)"
    echo "   Set GMAIL_CREDENTIALS_PATH and GMAIL_TOKEN_PATH to enable Gmail drafts"
    echo ""
fi

echo "🚀 Starting browser automation..."
echo "   Browser will open in visible mode"
echo "   Keep browser open to inspect results"
echo ""

# Run the Python script
PYTHONPATH=/Users/dnigga/Documents/FBP_Backend python3 scripts/run_redesim_stage2.py
