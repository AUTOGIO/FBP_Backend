# NFA Automation - Comprehensive Troubleshooting Guide

**Problem-solving reference for NFA_AUTOMATION_SPECIALIST_AI**

---

## 🗒️ Diagnostic Flowchart

```
Problem Detected
    |
    v
Check Latest Logs
    |
    +---> ERROR present? ----> Go to Issue Section
    |
    +---> No ERROR, behavior odd? ----> Check System Health
    |
    v
./ops/nfa_self_test.sh
    |
    +---> PASS ----> Problem is intermittent (see Intermittent Issues)
    |
    +---> FAIL ----> See component-specific section
    |
    v
Apply Fix from Section
    |
    v
Validate with Test Script
    |
    v
Run Self-Test Again
    |
    +---> PASS ----> ✅ ISSUE RESOLVED
    |
    +---> FAIL ----> Escalate (provide full logs)
```

---

## 🔌 Quick Diagnostic Commands

Always run these first:

```bash
# 1. Check system health (30 seconds)
./ops/nfa_self_test.sh

# 2. View latest errors
tail -50 logs/nfa/nfa_debug.log | grep -E "ERROR|FAILED|EXCEPTION"

# 3. Check SEFAZ connectivity
./ops/validate_sefaz_access.sh

# 4. Validate all modules
./ops/validate_nfa_system.sh

# 5. Check browser availability
python3 verify.py
```

If any of these fail, go to the specific issue section.

---

## 🔑 LOGIN ISSUES

### Problem: "Login failed - wrong credentials"

**Root Cause**: SEFAZ rejects credentials (password expired, locked account, etc.)

**Diagnosis**:
```bash
# Check login logs
grep -A10 "atf_login.py" logs/nfa/nfa_debug.log | head -20

# Test with manual login
curl -L https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp
```

**Solution**:
1. Verify SEFAZ login works manually in browser
2. Reset password if expired
3. Unlock account if locked (contact SEFAZ support)
4. Try again: `./ops/run_nfa_now.sh single`

---

### Problem: "Login timeout - waiting for form"

**Root Cause**: SEFAZ slow, network latency, or form selector changed

**Diagnosis**:
```bash
# Check network timing
grep "LOGIN_WAIT\|waiting for" logs/nfa/nfa_debug.log | tail -10

# Check if form loads
python3 -c "
import asyncio
from app.modules.nfa.atf_login import AutomatedLogin

async def test():
    login = AutomatedLogin('test@sefaz', 'pass')
    await login.test_login_form_loads()
    
asyncio.run(test())
"
```

**Solution**:
1. **If SEFAZ is slow**: Increase timeout in `delays.py`
   ```python
   # app/modules/nfa/delays.py
   LOGIN_WAIT = 8000  # was 5000
   ```
   Then test: `python3 app/modules/nfa/atf_login.py`

2. **If selector changed**: Update in `atf_selectors.py`
   ```bash
   # Take screenshot of current form
   python3 -c "from app.modules.nfa.screenshot_utils import *; take_screenshot('login_form')"
   # Inspect screenshot, update selector
   ```

3. **If network issue**: Check connectivity
   ```bash
   ping www4.sefaz.pb.gov.br
   curl -I https://www4.sefaz.pb.gov.br/atf/
   ```

---

### Problem: "Login succeeds but then redirects to menu"

**Root Cause**: Navigation rule changed, must force NFA URL

**Diagnosis**:
```bash
# Check if forced navigation happens
grep "FISf_EmitirNFAeReparticao" logs/nfa/nfa_debug.log
```

**Solution**:
Update `atf_login.py` - ensure forced navigation after login:
```python
# After successful login...
await page.goto(
    "https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true"
)
await page.wait_for_load_state("networkidle")
```

---

## 🗣️ FORM FILLING ISSUES

### Problem: "Field not found - selector invalid"

**Root Cause**: Field selector changed, iframe detection failed, or field moved

**Diagnosis**:
```bash
# Check selector errors
grep -i "selector.*not found\|element.*not found" logs/nfa/nfa_debug.log

# Check which field failed
grep -B5 "Field not found" logs/nfa/nfa_debug.log | head -20

# Check iframe detection
grep "iframe" logs/nfa/nfa_debug.log | grep -E "detected|found|error"
```

**Solution**:
1. **Take screenshot of form**:
   ```bash
   python3 -c "
   from app.modules.nfa.screenshot_utils import take_screenshot
   import asyncio
   asyncio.run(take_screenshot('form_current_state'))
   "
   ```

2. **Verify iframe detection**:
   ```bash
   python3 -c "
   from app.modules.nfa.atf_frames import FrameDetector
   detector = FrameDetector()
   print(detector.detect_all_iframes())
   "
   ```

3. **Update selector in `atf_selectors.py`**:
   ```python
   # Old selector that failed
   "nome_campo": "input[name='old_name']"
   
   # New selector (use label-based)
   "nome_campo": "label:has-text('Nome do Campo') ~ input"
   ```

4. **Test updated selector**:
   ```bash
   python3 tests/test_selectors.py -v
   ```

---

### Problem: "Form fills but one field stays empty"

**Root Cause**: Field requires special handling, search delay too short, or validation error

**Diagnosis**:
```bash
# Check which field
grep -i "filled" logs/nfa/nfa_debug.log | grep -i "false\|failed"

# Check delays
grep "FIELD_DELAY\|AFTER_SEARCH_DELAY" app/modules/nfa/delays.py
```

**Solution**:
1. **Check field type**:
   - Dropdown/select: Use `page.select()` not `page.fill()`
   - Searchable field: Add delay after search
   - Date field: Use proper format

2. **Increase delay** (if it's a timing issue):
   ```python
   # app/modules/nfa/delays.py
   AFTER_SEARCH_DELAY = 3000  # was 2000
   ```

3. **Add explicit wait** (if field updates dynamically):
   ```python
   await page.fill('input[name="field"]', value)
   await page.wait_for_selector('input[value="' + value + '"]', timeout=5000)
   ```

4. **Test specific filler**:
   ```bash
   python3 -c "
   from app.modules.nfa.<filler> import <Filler>
   filler = <Filler>()
   result = filler.fill({'field': 'value'})
   assert result.success, f'Failed: {result.error}'
   "
   ```

---

### Problem: "Form submission fails"

**Root Cause**: Validation error, required field empty, or form changed

**Diagnosis**:
```bash
# Check submission logs
grep -A5 "form_submitter\|submit" logs/nfa/nfa_debug.log | head -30

# Check validation errors from SEFAZ
grep -i "validation\|error\|invalid" logs/nfa/nfa_debug.log
```

**Solution**:
1. **Verify all required fields filled**:
   ```bash
   python3 -c "
   from app.modules.nfa.form_filler import FormFiller
   filler = FormFiller()
   result = filler.validate_all_fields()
   if not result.success:
       print(f'Missing fields: {result.errors}')
   "
   ```

2. **Check data validation**:
   ```bash
   python3 -c "
   from app.modules.nfa.data_validator import validate_cpf, validate_cnpj
   print(validate_cpf('12345678901'))  # Should be True or False
   "
   ```

3. **Take screenshot of form before submit**:
   ```bash
   # Edit form_submitter.py to capture state
   # Add before submit button click:
   screenshot_utils.take_screenshot('form_before_submit')
   ```

4. **Test submission with minimal data**:
   ```bash
   python3 tests/test_form_submission.py -v
   ```

---

## 📋 PDF DOWNLOAD ISSUES

### Problem: "PDF download timeout"

**Root Cause**: SEFAZ slow to generate PDFs, network latency, or timeout too short

**Diagnosis**:
```bash
# Check download attempt
grep -i "pdf\|dar\|download" logs/nfa/nfa_debug.log | tail -20

# Check current timeout
grep "PDF_WAIT" app/modules/nfa/delays.py
```

**Solution**:
1. **Increase PDF download timeout**:
   ```python
   # app/modules/nfa/delays.py
   PDF_WAIT = 8000  # was 5000
   ```

2. **Check retry logic**:
   ```bash
   grep -A10 "retry.*pdf\|pdf.*retry" app/modules/nfa/pdf_downloader.py
   # Should show 3 retry attempts
   ```

3. **If retries exhausted**, SEFAZ might be down:
   ```bash
   ./ops/validate_sefaz_access.sh
   ```

4. **Monitor SEFAZ status**:
   - Check SEFAZ maintenance schedule
   - Usually maintenance happens at night
   - Retry after maintenance window

---

### Problem: "PDF file empty or corrupted"

**Root Cause**: File download incomplete, SEFAZ sent error page, or file system issue

**Diagnosis**:
```bash
# Check file size
ls -lh output/nfa/pdf/*/

# Check file type
file output/nfa/pdf/*/*.pdf

# Check if file is valid PDF
python3 -c "
import PyPDF2
with open('output/nfa/pdf/CPF/DAR.pdf', 'rb') as f:
    try:
        PyPDF2.PdfReader(f)
        print('✅ PDF valid')
    except Exception as e:
        print(f'❌ PDF invalid: {e}')
"
```

**Solution**:
1. **Delete corrupted file and retry**:
   ```bash
   rm output/nfa/pdf/CPF/*.pdf
   ./ops/run_nfa_now.sh single
   ```

2. **Check if SEFAZ returned error**:
   ```bash
   # Examine PDF content
   pdftotext output/nfa/pdf/CPF/DAR.pdf - | head -20
   # If shows HTML or error message, SEFAZ failed
   ```

3. **If SEFAZ error, check form submission**:
   - Verify form filled correctly
   - Check screenshot of submitted form
   - Test with different CPF

---

### Problem: "PDF file not saved to expected location"

**Root Cause**: Output directory structure wrong, permissions issue, or download went to browser default

**Diagnosis**:
```bash
# Check if directories exist
ls -la output/nfa/pdf/
ls -la output/nfa/results/
ls -la output/nfa/screenshots/

# Check file permissions
ls -l output/nfa/pdf/*/

# Check if file elsewhere
find ~/Downloads -name "*.pdf" -mmin -5  # Modified in last 5 minutes
```

**Solution**:
1. **Create missing directories**:
   ```bash
   mkdir -p output/nfa/{pdf,results,screenshots}
   chmod 755 output/nfa/*
   ```

2. **Fix permissions**:
   ```bash
   chmod 755 output/nfa/pdf/*
   ```

3. **Check download path in code**:
   ```bash
   grep -n "output.*pdf\|pdf.*path" app/modules/nfa/pdf_downloader.py
   # Should point to output/nfa/pdf/
   ```

4. **Test PDF download**:
   ```bash
   python3 tests/test_pdf_download.py -v
   ```

---

## 🛠️ SYSTEM ISSUES

### Problem: "Playwright not installed or Chromium missing"

**Root Cause**: Installation incomplete, cache corrupted, or M3 incompatibility

**Diagnosis**:
```bash
# Check Playwright installation
python3 -m playwright --version

# Check Chromium availability
python3 -m playwright install chromium

# Check if Chromium runs
python3 verify.py
```

**Solution**:
1. **Reinstall Playwright**:
   ```bash
   pip install playwright --force-reinstall
   python3 -m playwright install
   ```

2. **For M3 Mac specifically**:
   ```bash
   # Run Apple Silicon install script
   ./scripts/setup_playwright.sh
   
   # Verify
   python3 verify.py
   ```

3. **Clear cache and retry**:
   ```bash
   rm -rf ~/Library/Caches/ms-playwright
   python3 -m playwright install
   ```

4. **Check gatekeeper (if Chromium won't run)**:
   ```bash
   xattr -dr com.apple.quarantine ~/Library/Caches/ms-playwright/chromium-*/
   ```

---

### Problem: "Port 8000 already in use"

**Root Cause**: Server already running, or port held by another process

**Diagnosis**:
```bash
# Check what's using port 8000
lsof -i :8000

# Get PID
PID=$(lsof -t -i :8000)
echo $PID
```

**Solution**:
1. **Kill existing process**:
   ```bash
   kill -9 $PID  # Replace $PID with actual PID
   ```

2. **Start server on different port**:
   ```bash
   # Edit scripts/start.sh
   # Change: uvicorn app.main:app --port 8000
   # To:     uvicorn app.main:app --port 8001
   
   ./scripts/start.sh
   ```

3. **Verify port free**:
   ```bash
   lsof -i :8000 | wc -l  # Should be 0 or 1
   ```

---

### Problem: "Memory usage too high"

**Root Cause**: Browser process not cleaned up, memory leak, or batch processing too many CPFs

**Diagnosis**:
```bash
# Check memory usage
ps aux | grep python3

# Monitor in real-time
watch -n 1 'ps aux | grep python3 | grep -v grep'

# Get memory by process
ps -A -o pid,%mem,cmd | grep -E "python|chromium" | sort -k2 -rn
```

**Solution**:
1. **Reduce batch size**:
   ```json
   {
     "destinatarios": [
       "CPF1",
       "CPF2",
       "CPF3"
     ]
   }
   // Process in smaller groups (3-5 CPFs at a time)
   ```

2. **Force cleanup**:
   ```bash
   # Restart server
   pkill -9 -f "python3.*uvicorn"
   ./scripts/start.sh
   ```

3. **Monitor for leaks**:
   ```bash
   # Run batch and monitor memory
   watch -n 2 'ps aux | grep python3 | grep uvicorn'
   ```

4. **If persists, debug browser cleanup**:
   ```bash
   # Check browser_launcher.py
   grep -n "close\|quit\|cleanup" app/modules/nfa/browser_launcher.py
   # Should properly close browser after each NFA
   ```

---

## 💁 INTERMITTENT ISSUES

### Problem: "Sometimes works, sometimes fails (random failures)"

**Root Cause**: Race condition, timing issue, or flaky selector

**Diagnosis**:
```bash
# Check failure pattern
grep "FAILED" logs/nfa/nfa_debug.log | wc -l
grep "SUCCESS" logs/nfa/nfa_debug.log | wc -l

# Calculate success rate
FAILED=$(grep "FAILED" logs/nfa/nfa_debug.log | wc -l)
SUCCESS=$(grep "SUCCESS" logs/nfa/nfa_debug.log | wc -l)
TOTAL=$((FAILED + SUCCESS))
echo "Success rate: $(( SUCCESS * 100 / TOTAL ))%"
```

**Solution**:
1. **Add longer waits** (if timing-related):
   ```python
   # app/modules/nfa/delays.py
   # Increase all delays by 20-30%
   DEFAULT_DELAY = 1800  # was 1500
   FIELD_DELAY = 1000    # was 800
   ```

2. **Add explicit waits** (if selector flaky):
   ```python
   # Instead of just:
   await page.fill('selector', value)
   
   # Use:
   await page.fill('selector', value)
   await page.wait_for_selector('selector[value="' + value + '"]', timeout=5000)
   ```

3. **Reduce batch size** (if overwhelmed):
   ```bash
   # Process 1-2 CPFs at a time instead of 10+
   ```

4. **Add retry logic** (if NFA sometimes succeeds):
   ```python
   # batch_processor.py should already have this
   for attempt in range(3):
       try:
           result = await create_nfa(...)
           if result.success:
               break
       except Exception as e:
           if attempt < 2:
               await asyncio.sleep(5000)  # Wait before retry
   ```

---

## 📈 PERFORMANCE ISSUES

### Problem: "NFA creation very slow"

**Root Cause**: SEFAZ slow, network latency, Playwright overhead, or system resource exhausted

**Diagnosis**:
```bash
# Measure execution time
grep "Execution time:" logs/nfa/nfa_debug.log | tail -5

# Check where time is spent
grep -E "login|filling|submit|pdf" logs/nfa/nfa_debug.log | grep "ms" | head -20

# Check system resources
top -n1 | head -20
```

**Solution**:
1. **Profile execution**:
   ```bash
   # Add timing to each major step
   import time
   
   start = time.time()
   await login_step()
   print(f"Login: {time.time() - start}ms")
   
   start = time.time()
   await form_filling_step()
   print(f"Form: {time.time() - start}ms")
   ```

2. **If SEFAZ slow**, nothing to optimize
3. **If network slow**, use faster connection
4. **If system resource constrained**:
   - Close other applications
   - Reduce browser window size
   - Process fewer CPFs in parallel

---

## 📒 LOG READING TIPS

### Find specific errors

```bash
# Login errors only
grep -i "login" logs/nfa/nfa_debug.log | grep -i "error\|failed"

# Form filling errors only
grep -i "field\|filler" logs/nfa/nfa_debug.log | grep -i "error\|failed"

# PDF errors only
grep -i "pdf\|dar\|download" logs/nfa/nfa_debug.log | grep -i "error\|failed"
```

### Timeline of events

```bash
# Show timestamps
grep -E "^\[.*\]" logs/nfa/nfa_debug.log | tail -50

# Extract timings
grep "took\|seconds\|ms" logs/nfa/nfa_debug.log | tail -20
```

### Follow specific CPF

```bash
# Extract all logs for specific CPF
CPF="12345678901"
grep "$CPF" logs/nfa/nfa_debug.log
```

---

## 📧 When to Escalate

If you've tried all solutions and issue persists:

1. **Gather complete context**:
   ```bash
   # Package debug info
   mkdir /tmp/debug_fbp
   cp logs/nfa/nfa_debug.log /tmp/debug_fbp/
   cp logs/nfa/browser_console.log /tmp/debug_fbp/
   cp output/nfa/screenshots/*/*.png /tmp/debug_fbp/
   tar -czf debug_fbp_$(date +%s).tar.gz /tmp/debug_fbp/
   ```

2. **Provide detailed report**:
   - What were you trying to do?
   - What happened instead?
   - What errors did you see?
   - What have you tried?
   - Attach debug archive

3. **Contact support**:
   - Email: [support email]
   - Slack: #fbp-support
   - Include debug archive

---

## 🌟 Helpful Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [SEFAZ-PB ATF Access](https://www4.sefaz.pb.gov.br/atf/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Python Asyncio Guide](https://docs.python.org/3/library/asyncio.html)

---

**Last Updated**: 2025-12-05  
**Maintained By**: NFA_AUTOMATION_SPECIALIST_AI
