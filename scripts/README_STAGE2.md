# REDESIM Stage 2 Automation - Visual Execution

## Quick Start

### Option 1: Interactive Launcher (Recommended)

```bash
cd /Users/dnigga/Documents/FBP_Backend
./scripts/run_redesim_stage2_visual.sh
```

This will:

- Prompt for ATF credentials if not set
- Open browser in visible mode (headless=False)
- Run the complete Stage 2 automation
- Keep browser open for 1 hour for inspection

### Option 2: Direct Execution with Environment Variables

```bash
export ATF_USERNAME="your_username"
export ATF_PASSWORD="your_password"

# Optional: Gmail credentials for draft creation
export GMAIL_CREDENTIALS_PATH="/path/to/credentials.json"
export GMAIL_TOKEN_PATH="/path/to/token.json"

cd /Users/dnigga/Documents/FBP_Backend
PYTHONPATH=/Users/dnigga/Documents/FBP_Backend python3 scripts/run_redesim_stage2.py
```

## What It Does

1. **Opens visible browser** - You can watch the automation in real-time
2. **Logs into ATF** - Uses your credentials
3. **Runs REDESIM consultation** - Searches for processes
4. **Stage 2 Automation**:
   - Selects checkbox in LISTA frame
   - Validates CEP via ViaCEP API
   - Checks contabilista CPF via CFC site
   - Extracts all emails from FC frame
   - Creates Gmail draft with proper subject/body
   - Saves results to JSON file

## Output

- **Console logs**: Real-time progress updates
- **JSON results**: `output/redesim_stage2_results_{timestamp}.json`
- **Gmail draft**: Created if emails found and credentials provided
- **Browser**: Stays open for manual inspection

## Troubleshooting

If browser doesn't open:

- Check Playwright installation: `playwright install chromium`
- Verify credentials are correct
- Check network connectivity to ATF site

If Gmail draft fails:

- Verify Gmail credentials path
- Check OAuth token is valid
- Ensure Gmail API is enabled in Google Cloud Console
