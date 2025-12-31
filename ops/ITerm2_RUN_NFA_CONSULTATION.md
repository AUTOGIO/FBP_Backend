# Step-by-Step Guide: Running NFA Consultation Automation in iTerm2

## Overview
This guide walks you through running the NFA consultation automation that opens PDFs (DANFE + DAR) for the first 15 NFAs without downloading them to disk.

## Prerequisites
1. Environment variables set:
   ```bash
   export NFA_USERNAME='eduardof'
   export NFA_PASSWORD='atf101010'
   ```
2. Python environment with dependencies installed
3. Playwright browsers installed (`playwright install chromium`)

## Step-by-Step Instructions

### Step 1: Open iTerm2 Terminal
- Press `Cmd + Space` to open Spotlight
- Type `iTerm2` and press Enter
- Or click the iTerm2 icon in your Dock/Applications

### Step 2: Navigate to Project Directory
```bash
cd ~/.cursor/worktrees/FBP_Backend__Workspace_/wxh
```

**OR** if using absolute path:
```bash
cd /Users/dnigga/.cursor/worktrees/FBP_Backend__Workspace_/wxh
```

### Step 3: Verify Environment Variables
```bash
echo $NFA_USERNAME
echo $NFA_PASSWORD
```

**Expected output:**
```
eduardof
atf101010
```

**If not set**, export them:
```bash
export NFA_USERNAME='eduardof'
export NFA_PASSWORD='atf101010'
```

### Step 4: Activate Python Virtual Environment (if using one)
```bash
# Option A: If using venv
source venv/bin/activate

# Option B: If using conda
conda activate fbp

# Option C: If using uv
source .venv/bin/activate
```

**Skip this step if running Python directly without a virtual environment.**

### Step 5: Verify Playwright is Installed
```bash
python -c "import playwright; print('Playwright installed')"
```

**If not installed:**
```bash
pip install playwright
playwright install chromium
```

### Step 6: Run the Automation Script
```bash
python -c "
import asyncio
from app.modules.nfa_atf_automation import run_nfa_job

result = asyncio.run(run_nfa_job(
    data_inicial='08/12/2025',
    data_final='08/12/2025',
    matricula='1595504',
    headless=False,
    max_nfas=15,
    wait_between_nfas=3
))
"
```

### Step 7: Watch the Automation Execute
- Browser window will open automatically (headless=False)
- You'll see:
  1. Login to ATF portal
  2. Navigation to FIS_308
  3. Form filling with dates and matrícula
  4. Consultation submission
  5. For each of the first 15 NFAs:
     - Selection of NFA row
     - Click "Imprimir" → DANFE PDF opens in new tab (left open)
     - Click "Gerar/Emitir Taxa Serviço" → DAR PDF opens in new tab (left open)
     - Wait 3 seconds before next NFA

### Step 8: Review Results
After completion, you'll see:
- JSON summary printed to terminal
- Browser remains open with all PDF tabs visible (30 tabs total: 15 DANFE + 15 DAR)
- Log entry written to: `logs/nfa_runs.jsonl`

### Step 9: Manual Cleanup (Optional)
When done reviewing PDFs, manually close the browser window or press `Ctrl+C` in iTerm2 to stop the script.

## Troubleshooting

### Issue: "NFA credentials not provided"
**Solution:** Export environment variables (see Step 3)

### Issue: "Playwright not installed"
**Solution:** Install Playwright (see Step 5)

### Issue: "ModuleNotFoundError: No module named 'app'"
**Solution:** Make sure you're in the project root directory (see Step 2)

### Issue: Browser doesn't open
**Solution:** Check that `headless=False` in the script call

### Issue: PDFs don't open in new tabs
**Solution:** 
- Check network connectivity
- Verify ATF portal is accessible
- Check browser console for JavaScript errors (F12)

## Quick One-Liner (All Steps Combined)
```bash
cd ~/.cursor/worktrees/FBP_Backend__Workspace_/wxh && \
export NFA_USERNAME='eduardof' && \
export NFA_PASSWORD='atf101010' && \
python -c "
import asyncio
from app.modules.nfa_atf_automation import run_nfa_job
result = asyncio.run(run_nfa_job(
    data_inicial='08/12/2025',
    data_final='08/12/2025',
    matricula='1595504',
    headless=False,
    max_nfas=15,
    wait_between_nfas=3
))
"
```

## Alternative: Create a Shell Script
Create file `run_nfa_consultation.sh`:
```bash
#!/bin/bash
cd ~/.cursor/worktrees/FBP_Backend__Workspace_/wxh
export NFA_USERNAME='eduardof'
export NFA_PASSWORD='atf101010'
python -c "
import asyncio
from app.modules.nfa_atf_automation import run_nfa_job
result = asyncio.run(run_nfa_job(
    data_inicial='08/12/2025',
    data_final='08/12/2025',
    matricula='1595504',
    headless=False,
    max_nfas=15,
    wait_between_nfas=3
))
"
```

Make it executable:
```bash
chmod +x run_nfa_consultation.sh
```

Run it:
```bash
./run_nfa_consultation.sh
```

## Notes
- **No files are downloaded** - PDFs open in browser tabs only
- **Browser stays open** - All PDF tabs remain visible after automation completes
- **30 tabs total** - 15 DANFE PDFs + 15 DAR PDFs
- **Same session** - Login happens once, all NFAs processed in same session
- **3 second delay** - Between each NFA to allow time for PDFs to load
