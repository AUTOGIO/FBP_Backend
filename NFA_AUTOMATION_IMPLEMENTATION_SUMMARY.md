# NFA Automation Implementation Summary

## Overview

This document summarizes the implementation of the NFA consultation automation for the SEFAZ-PB ATF portal. The automation processes NFAs (Notas Fiscais Avulsas) by consulting the portal, selecting NFAs from results, and downloading both DANFE and DAR PDFs.

## Files Created/Modified

### 1. `app/modules/nfa_atf_automation.py` (Updated)

**Key Changes:**
- ✅ Updated `max_nfas` default from 3 to **15** (process first 15 NFAs)
- ✅ Updated `wait_between_nfas` default from 4 to **3 seconds**
- ✅ Changed `headless` default to `False` (show browser for debugging)
- ✅ Modified PDF download functions to **leave PDF tabs OPENED** (not close them)
- ✅ Updated docstrings to reflect correct wait time (3 seconds)
- ✅ Both dates default to `"08/12/2025"` as required

**Main Function Signature:**

```python
async def run_nfa_job(
    username: str | None = None,
    password: str | None = None,
    data_inicial: str = "08/12/2025",
    data_final: str = "08/12/2025",
    matricula: str = "1595504",
    headless: bool = False,  # Changed to False to see browser for debugging
    max_nfas: int = 15,  # Process first 15 NFAs
    wait_between_nfas: int = 3,  # Wait 3 seconds between NFAs
) -> dict:
```

**Returns:**
```python
{
    "status": "ok" | "error",
    "nfas_processed": [
        {
            "nfa_numero": str,
            "danfe_path": str | None,
            "dar_path": str | None,
            "status": "ok" | "error",
            "error": str | None
        },
        ...
    ],
    "total_processed": int,
    "started_at": str,  # ISO timestamp
    "finished_at": str,  # ISO timestamp
    "error": str | None
}
```

### 2. `run_nfa_consultation.py` (Created)

Simple runner script that:
- Reads credentials from environment variables (`NFA_USERNAME`, `NFA_PASSWORD`)
- Calls `run_nfa_job()` with default parameters
- Provides clear error messages if credentials are missing
- Exits with appropriate status codes

**Usage:**
```bash
export NFA_USERNAME='eduardof'
export NFA_PASSWORD='atf101010'
python run_nfa_consultation.py
```

### 3. `ops/ITerm2_RUN_INSTRUCTIONS.md` (Created)

Comprehensive step-by-step guide for running the automation in iTerm2, including:
- Prerequisites
- Environment setup
- Execution steps
- Monitoring and troubleshooting
- Quick reference commands

## Implementation Details

### Automation Flow

1. **Login** (once for all NFAs)
   - Navigate to ATF login page
   - Fill credentials
   - Submit and wait for session

2. **Navigate to FIS_308**
   - Use function search field or direct URL
   - Wait for form to load

3. **Fill Consultation Form**
   - Initial date: `08/12/2025`
   - Final date: `08/12/2025`
   - Matrícula: `1595504` (in `cmpFuncEmitente` iframe)
   - **CRITICAL**: Fill matrícula AND click "Pesquisar" button
   - Submit form

4. **Process NFAs** (first 15)
   - For each NFA:
     - Select NFA row (radio button)
     - Click "Imprimir" → opens DANFE PDF in new tab (**left OPENED**)
     - Click "Gerar/Emitir Taxa Serviço" → opens DAR PDF in new tab (**left OPENED**)
     - Wait **3 seconds** before next NFA

### Key Features

- ✅ **Session Reuse**: Login once, process all NFAs in same session
- ✅ **Iframe Handling**: Properly handles `cmpFuncEmitente` iframe for matrícula input
- ✅ **PDF Management**: Opens PDFs in new tabs and leaves them OPENED
- ✅ **Error Handling**: Retry logic (max 2 retries) for transient failures
- ✅ **Logging**: JSONL log file at `logs/nfa_runs.jsonl`
- ✅ **Output**: PDFs saved to `/Users/dnigga/Downloads/NFA_Outputs/`

### File Naming

PDFs are saved with names:
- `NFA_{NUMERO}_DANFE.pdf`
- `NFA_{NUMERO}_DAR.pdf`

Where `{NUMERO}` is the NFA number extracted from the results table.

## TODOs / Future Improvements

### Current Implementation Status: ✅ COMPLETE

All user requirements have been implemented:
- ✅ Process first 15 NFAs
- ✅ Wait 3 seconds between NFAs
- ✅ Leave PDF tabs OPENED
- ✅ Use same session (no re-login)
- ✅ Fill and click "Funcionário Emitente" component
- ✅ Both dates set to 08/12/2025

### Potential Future Enhancements

1. **Error Recovery**: 
   - If a specific NFA fails, continue with next NFA instead of stopping
   - Currently: continues but logs error

2. **Batch Processing**:
   - Support for processing multiple date ranges in one run
   - Currently: single date range per run

3. **PDF Validation**:
   - Verify downloaded PDFs are valid before marking as successful
   - Currently: assumes download success if file path is returned

4. **Progress Reporting**:
   - Real-time progress updates (e.g., "Processing 5/15")
   - Currently: logged but not displayed prominently

5. **Configuration File**:
   - Support for configuration file instead of hardcoded defaults
   - Currently: defaults are in function signature

## Testing Checklist

- [x] Login with valid credentials
- [x] Navigate to FIS_308 function
- [x] Fill consultation form with dates and matrícula
- [x] Submit form and wait for results
- [x] Select first NFA from table
- [x] Download DANFE PDF (tab left opened)
- [x] Download DAR PDF (tab left opened)
- [x] Process multiple NFAs (15 total)
- [x] Wait 3 seconds between NFAs
- [x] Verify files saved with correct names
- [x] Verify log file created
- [x] Handle case with no results
- [x] Handle login failures
- [x] Handle timeout scenarios
- [x] Verify iframe resolution works
- [x] Test component iframe fallback

## Dependencies

- Python 3.9+
- Playwright (`playwright` package)
- Chromium browser (installed via `playwright install chromium`)

## Environment Variables

Required:
- `NFA_USERNAME`: ATF portal username
- `NFA_PASSWORD`: ATF portal password

Optional (can be passed as function parameters):
- All other parameters have sensible defaults

## Output Locations

- **PDFs**: `/Users/dnigga/Downloads/NFA_Outputs/`
- **Logs**: `logs/nfa_runs.jsonl` (relative to project root)
- **Screenshots**: `output/nfa/screenshots/` (relative to project root)

## Notes

- The browser runs in **headed mode** (`headless=False`) by default for easier debugging
- PDF tabs are intentionally **not closed** to allow manual review
- The automation uses **retry logic** (max 2 retries) for transient failures
- All operations are **logged** to both console and JSONL file
- The script **validates date formats** before submission
