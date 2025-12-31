# iTerm2 Run Instructions - NFA Consultation Automation

## Prerequisites

1. **Python Environment**: Ensure Python 3.9+ is installed and accessible
2. **Dependencies**: Install required packages (Playwright, etc.)
3. **Environment Variables**: Set NFA credentials

## Step-by-Step Instructions

### Step 1: Open iTerm2

Open iTerm2 terminal application on your Mac.

### Step 2: Navigate to Project Directory

```bash
cd /Users/dnigga/.cursor/worktrees/FBP_Backend__Workspace_/mxs
```

### Step 3: Activate Virtual Environment (if using one)

If you're using a virtual environment, activate it:

```bash
# Example for venv
source venv/bin/activate

# OR for conda
conda activate fbp_env

# OR for uv
source .venv/bin/activate
```

### Step 4: Set Environment Variables

Set the NFA credentials as environment variables:

```bash
export NFA_USERNAME='eduardof'
export NFA_PASSWORD='atf101010'
```

**Note**: These credentials will be available only in this terminal session. If you close iTerm2, you'll need to set them again.

### Step 5: Verify Environment Variables

Verify that the environment variables are set correctly:

```bash
echo "Username: $NFA_USERNAME"
echo "Password: [check if set]"
```

### Step 6: Install Dependencies (if needed)

If you haven't installed Playwright browsers yet:

```bash
playwright install chromium
```

Or if using uv:

```bash
uv sync
```

### Step 7: Run the Automation

Execute the automation script:

```bash
python run_nfa_consultation.py
```

**Alternative**: If you prefer to use the module directly:

```bash
python -m app.modules.nfa_atf_automation
```

Or using Python's async runner:

```python
python -c "
import asyncio
from app.modules.nfa_atf_automation import run_nfa_job
import os

async def main():
    result = await run_nfa_job(
        username=os.getenv('NFA_USERNAME'),
        password=os.getenv('NFA_PASSWORD'),
        data_inicial='08/12/2025',
        data_final='08/12/2025',
        matricula='1595504',
        headless=False,
        max_nfas=15,
        wait_between_nfas=3
    )
    print(result)

asyncio.run(main())
"
```

### Step 8: Monitor the Execution

The script will:

1. **Login** to ATF portal (once for all NFAs)
2. **Navigate** to FIS_308 function
3. **Fill** consultation form with:
   - Initial date: 08/12/2025
   - Final date: 08/12/2025
   - Matrícula: 1595504
4. **Process** first 15 NFAs from results:
   - For each NFA:
     - Select the NFA row
     - Click "Imprimir" → opens DANFE PDF in new tab (left OPENED)
     - Click "Gerar/Emitir Taxa Serviço" → opens DAR PDF in new tab (left OPENED)
     - Wait 3 seconds before next NFA

### Step 9: Check Results

After execution completes:

1. **Check Console Output**: The script will print a JSON summary with:
   - Status (ok/error)
   - Number of NFAs processed
   - File paths for downloaded PDFs
   - Any errors encountered

2. **Check Output Directory**: PDFs are saved to:
   ```
   /Users/dnigga/Downloads/NFA_Outputs/
   ```
   Files are named:
   - `NFA_{NUMERO}_DANFE.pdf`
   - `NFA_{NUMERO}_DAR.pdf`

3. **Check Log File**: Detailed logs are written to:
   ```
   logs/nfa_runs.jsonl
   ```

4. **Check Browser Tabs**: PDF tabs will remain OPENED in the browser (per requirement)

### Step 10: Troubleshooting

If you encounter issues:

1. **Login Failed**:
   - Verify credentials are correct
   - Check if ATF portal is accessible
   - Check network connection

2. **No NFAs Found**:
   - Verify date range is correct
   - Check if matrícula is correct
   - Verify there are NFAs in the system for the specified date range

3. **Download Failed**:
   - Check if output directory exists and is writable
   - Verify browser has permission to download files
   - Check if PDF tabs are being blocked by popup blocker

4. **Timeout Errors**:
   - Increase timeout values in the code if needed
   - Check network speed
   - Verify ATF portal is responding normally

## Quick Reference Commands

```bash
# One-liner to set env vars and run
export NFA_USERNAME='eduardof' && export NFA_PASSWORD='atf101010' && python run_nfa_consultation.py

# Check if script is executable
chmod +x run_nfa_consultation.py

# Run with verbose logging
PYTHONPATH=. python -u run_nfa_consultation.py 2>&1 | tee nfa_run.log

# Check output directory
ls -lh /Users/dnigga/Downloads/NFA_Outputs/

# View log file
tail -f logs/nfa_runs.jsonl
```

## Expected Output

```
================================================================================
NFA Consultation Automation - Starting
================================================================================
Username: eduardof
Password: [REDACTED]
Date range: 08/12/2025 to 08/12/2025
Matrícula: 1595504
Max NFAs: 15
Wait between NFAs: 3 seconds
================================================================================
Starting NFA consultation automation
...
Processing NFA #1/15: 900500381
...
✓ DANFE triggered for NFA 900500381
✓ DAR triggered for NFA 900500381
Waiting 3 seconds before next NFA...
...
================================================================================
NFA Automation Job Summary
================================================================================
{
  "status": "ok",
  "nfas_processed": [...],
  "total_processed": 15,
  "started_at": "2025-12-10T10:00:00.000Z",
  "finished_at": "2025-12-10T10:15:00.000Z",
  "error": null
}
================================================================================
```

## Notes

- **Browser Visibility**: The script runs with `headless=False` by default, so you'll see the browser window
- **PDF Tabs**: PDF tabs are intentionally left OPENED (not closed) per requirement
- **Session Reuse**: Login happens once, then all NFAs are processed in the same session
- **Wait Time**: 3 seconds between each NFA processing
- **Max NFAs**: Processes first 15 NFAs from results table
