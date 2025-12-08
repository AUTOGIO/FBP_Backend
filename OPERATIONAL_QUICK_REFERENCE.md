# 📊 NFA System - Operational Quick Reference

**For**: NFA_AUTOMATION_SPECIALIST_AI  
**Updated**: 2025-12-05  
**Status**: Production Ready

---

## 🚀 INSTANT COMMANDS

### Health & Diagnostics
```bash
# Full diagnostics
./ops/nfa_self_test.sh

# System validation
./ops/validate_nfa_system.sh

# SEFAZ connectivity
./ops/validate_sefaz_access.sh
```

### Runtime
```bash
# Single NFA
./ops/run_nfa_now.sh single

# Batch NFA
./ops/run_nfa_now.sh batch

# API health
curl http://localhost:9500/health
```

### Debugging
```bash
# Follow logs
tail -f logs/nfa/nfa_debug.log

# View latest screenshots
open output/nfa/screenshots/

# Extract errors
grep -i "error\|failed\|exception" logs/nfa/nfa_debug.log
```

---

## 🔧 MANDATORY LOGIN PIPELINE

ALL login flows MUST follow this sequence:

```
1. Navigate to: https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp
2. Fill:
   - input[name='edtNoLogin'] = username
   - input[name='edtDsSenha'] = password
3. Trigger: page.evaluate("logarSistema()")
4. Wait: 4 seconds
5. Navigate to: https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true
```

File: `app/modules/nfa/atf_login.py`

---

## 🔍 CRITICAL FILES (Never remove)

```
app/modules/nfa/
 ├── delays.py              <- ALL waits centralized here
 ├── atf_selectors.py       <- ALL selectors defined here
 ├── atf_login.py           <- Login MUST follow pipeline
 ├── form_filler.py         <- Main orchestrator
 └── [13 other modules]    <- Filler + utils
```

---

## 💾 RULES (Non-negotiable)

✅ **ALWAYS**:
- Use `delays.py` for ALL waits (zero hardcoded timeouts)
- Log errors with screenshots
- Retry failed steps (3x max)
- Validate CPF/CNPJ before form fill

❌ **NEVER**:
- Reference NOTAS_AVULSAS (folder deleted)
- Hardcode selectors (use `atf_selectors.py`)
- Break existing working logic
- Ask user to perform automation-able steps

---

## 📺 OUTPUT STRUCTURE

```
output/nfa/
 ├── pdf/<cpf>/
 ├── results/<cpf>.json
 ├── screenshots/<cpf>/

logs/nfa/
 ├── nfa_debug.log
 ├── browser_console.log
 ├── frame_detection.log
```

---

## 💋 FIX WORKFLOW

1. **Diagnose**: Extract context (logs + screenshots)
2. **Isolate**: Create minimal test case
3. **Patch**: Modify only the failing module
4. **Validate**: Run test case + full system
5. **Deploy**: Commit + document

---

## 🚨 ESCALATION CHECKLIST

If ANY of these occur, STOP:
- [ ] SEFAZ returns 403/401
- [ ] Form HTML fundamentally changed
- [ ] Playwright crashes > 2x per batch
- [ ] Network timeouts > 50% of runs
- [ ] Selector failures > 5% of form fills

Action: Collect diagnostics + alert user

---

**Working code is sacred. Stability is everything.**
