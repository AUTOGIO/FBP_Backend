# Legacy Iframe Form Automation - Bug Fixes Applied

## Overview

This document details all bug fixes applied to the REDESIM automation to handle legacy iframe-based, stateful web systems correctly.

## Critical Bugs Fixed

### 1. ✅ Reusing Stale DOM References After Iframe Reloads

**Problem:** Code was reusing frame and element references after iframe reloads, causing stale reference errors.

**Solution:**
- Always re-query iframe 'principal' after each navigation
- Always re-collect radio buttons after each iframe reload
- Never cache frame or element references across operations
- Added `_resolve_principal_iframe()` function that always queries fresh

**Code Location:**
- `app/modules/cadastro/consultar_redesim.py::_resolve_principal_iframe()`
- `app/modules/cadastro/consultar_redesim.py::_collect_radio_buttons_from_iframe()`
- `scripts/run_redesim_consulta.py::loop iteration` - always re-resolves iframe

---

### 2. ✅ Selecting Radios Via .checked = true Instead of Click Events

**Problem:** Code was setting `.checked = true` directly, which bypasses the `onClick` handler that updates hidden fields.

**Solution:**
- Always use `radio.click()` - never set `.checked` directly
- Added `scroll_into_view_if_needed()` before click for reliability
- Click triggers `defineCamposHid()` which updates hidden fields

**Code Location:**
- `app/modules/cadastro/consultar_redesim.py::process_redesim_stage2()` - line ~2136

---

### 3. ✅ Failing to Re-query Iframe After Navigation

**Problem:** After navigating back to results list, code wasn't re-querying the iframe.

**Solution:**
- Always call `_resolve_principal_iframe()` after navigation
- Always call `_collect_radio_buttons_from_iframe()` after iframe resolution
- Never reuse iframe references from previous iterations

**Code Location:**
- `scripts/run_redesim_consulta.py::loop iteration` - lines ~296-305

---

### 4. ✅ Submitting Form Before Hidden Fields Are Updated

**Problem:** Code was submitting forms immediately after click, before `defineCamposHid()` updated hidden fields.

**Solution:**
- Added `_wait_for_hidden_field_sync()` function that polls `hidNrProcesso` until it matches radio value
- Form submission only occurs AFTER hidden field synchronization is confirmed
- Validates `frmListagemPendeciaProc.hidNrProcesso.value === radio.value` before proceeding

**Code Location:**
- `app/modules/cadastro/consultar_redesim.py::_wait_for_hidden_field_sync()` - lines ~1240-1329
- `app/modules/cadastro/consultar_redesim.py::process_redesim_stage2()` - lines ~2148-2169

---

### 5. ✅ Assuming Visual Selection Equals Logical Selection

**Problem:** Code assumed that if a radio appeared checked, the hidden fields were updated.

**Solution:**
- Never rely on visual state (`.checked` property)
- Always validate hidden field state explicitly
- Use `_wait_for_hidden_field_sync()` to ensure logical state matches

**Code Location:**
- `app/modules/cadastro/consultar_redesim.py::_wait_for_hidden_field_sync()`

---

### 6. ✅ Always Submitting First Radio's Data Due to Stale Hidden Fields

**Problem:** Hidden fields weren't being updated, so form always submitted with first radio's value.

**Solution:**
- Wait for hidden field synchronization before submission
- Re-query form elements before submission (never reuse stale references)
- Validate hidden field value matches clicked radio value

**Code Location:**
- `app/modules/cadastro/consultar_redesim.py::_wait_for_hidden_field_sync()`
- `app/modules/cadastro/consultar_redesim.py::process_redesim_stage2()` - lines ~2177-2193

---

### 7. ✅ Missing Synchronization Between UI Interaction and Internal State

**Problem:** No validation that `defineCamposHid()` actually executed after click.

**Solution:**
- Added polling mechanism in `_wait_for_hidden_field_sync()`
- Checks every 100ms until hidden field matches expected value
- Times out after `ELEMENT_TIMEOUT * 2` with detailed error message

**Code Location:**
- `app/modules/cadastro/consultar_redesim.py::_wait_for_hidden_field_sync()` - lines ~1270-1309

---

### 8. ✅ Not Validating That defineCamposHid() Actually Executed

**Problem:** No way to know if the JavaScript function ran successfully.

**Solution:**
- Poll hidden field value until it matches expected radio value
- If timeout occurs, raise explicit error with current vs expected values
- Log detailed debugging information on timeout

**Code Location:**
- `app/modules/cadastro/consultar_redesim.py::_wait_for_hidden_field_sync()` - lines ~1311-1329

---

### 9. ✅ Not Accounting for Iframe-Scoped DOM Access

**Problem:** Code was querying elements from main page instead of iframe.

**Solution:**
- All DOM queries are scoped to `principal_frame` (the iframe)
- Never use `page.locator()` for elements inside iframe
- Always use `frame.locator()` for iframe-scoped queries

**Code Location:**
- `app/modules/cadastro/consultar_redesim.py::_resolve_principal_iframe()` - ensures iframe is resolved
- All radio/form queries use `principal_frame.locator()` not `page.locator()`

---

### 10. ✅ No Protection Against Session Timeout or Partial Reloads

**Problem:** Code didn't handle session expiration or partial page reloads.

**Solution:**
- Added timeout detection in `_wait_for_hidden_field_sync()`
- Added error handling with detailed messages
- State persistence allows resuming from last successful index
- Loop continues even if one process fails

**Code Location:**
- `app/modules/cadastro/consultar_redesim.py::_load_iteration_state()` / `_save_iteration_state()`
- `scripts/run_redesim_consulta.py::loop iteration` - error handling and state updates

---

## Implementation Details

### State Persistence

- State file: `/Volumes/MICRO/ATF/REDESIM/state.json`
- Tracks: `current_index`, `total`, `last_processed_value`
- Allows resuming from last successful position
- Prevents reprocessing same items

### Iframe Resolution Strategy

1. Wait for iframe element in DOM (`iframe[name="principal"]`)
2. Try direct frame lookup by name
3. Iterate through all frames checking name/URL
4. Fallback: Find any iframe with radio buttons
5. JavaScript-based detection as last resort

### Hidden Field Synchronization

1. Click radio button (triggers `defineCamposHid()`)
2. Poll `frmListagemPendeciaProc.hidNrProcesso.value` every 100ms
3. Compare with expected radio value
4. Timeout after `ELEMENT_TIMEOUT * 2` (10 seconds)
5. Only proceed to form submission after sync confirmed

### Form Submission Discipline

1. Radio click completed
2. Hidden fields updated (validated)
3. Re-query form elements (fresh references)
4. Submit via "Detalhar" button or Enter key
5. Wait for detail page to load

---

## Testing Checklist

- [x] Each row is processed once (no duplicates)
- [x] No duplicate submissions occur
- [x] Hidden fields always match clicked radio
- [x] First row is NOT repeatedly processed
- [x] Solution is deterministic and stable
- [x] Iframe is always re-queried after navigation
- [x] Radio buttons are always re-collected after reload
- [x] Hidden field synchronization is validated before submission
- [x] State persistence allows resuming from failures
- [x] Error handling prevents infinite retry loops

---

## Key Functions

### `_resolve_principal_iframe(page, timeout)`
- Resolves iframe 'principal' explicitly
- Multiple fallback strategies
- Always returns fresh frame reference

### `_collect_radio_buttons_from_iframe(frame)`
- Collects ALL radio buttons from iframe
- Index-based, deterministic
- Must be called after every iframe reload

### `_wait_for_hidden_field_sync(frame, expected_value, timeout)`
- Polls hidden field until it matches expected value
- Validates `defineCamposHid()` executed
- Returns True if synchronized, False on timeout

### `_load_iteration_state()` / `_save_iteration_state(state)`
- Persists iteration state to disk
- Allows resuming from last successful index
- Prevents reprocessing same items

---

## Best Practices Enforced

1. **Always re-query after navigation** - Never reuse stale references
2. **Always use real clicks** - Never set `.checked` directly
3. **Always validate hidden fields** - Wait for synchronization
4. **Always scope to iframe** - Never use page.locator() for iframe elements
5. **Always handle timeouts** - Graceful error handling with state updates
6. **Always persist state** - Allow resuming from failures

---

## Notes

- The system uses legacy JavaScript (`defineCamposHid()`) that only runs on real click events
- Hidden fields (`hidNrProcesso`, `hidStFac`, etc.) control form submission, not `.checked` state
- Iframe fully reloads after each operation, invalidating all DOM references
- State persistence is critical for handling failures and long-running batches
