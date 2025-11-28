# Playwright Integration for NFA

## Overview

The NFA module uses Playwright for browser automation with ATF system.

## Context Resolution (Root DOM or iframe)

ATF may render the NFA form in the root DOM or inside `frame[name='contents']`.  
Use the unified helpers from `nfa_context.py`:

```python
from app.modules.nfa import resolve_nfa_context, wait_for_nfa_ready

ctx = await resolve_nfa_context(page)
await wait_for_nfa_ready(ctx, timeout=45000)
```

## Selectors

CSS selectors are centralized in `atf_selectors.py`:

```python
from app.modules.nfa import EMITENTE_TABLE, DEST_TABLE, ENDERECO_TABLE

# Use selectors
frame.locator(f"{EMITENTE_TABLE} select").select_option("2")
```

## Browser Connection

### CDP Connection (Preferred)

Connect to existing browser via Chrome DevTools Protocol:

```python
browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
```

### New Browser Instance

Launch new browser if CDP unavailable:

```python
browser = await playwright.chromium.launch(headless=False)
```

## Form Filling Pattern

Standard context-agnostic flow:

1. Resolve `ctx = await resolve_nfa_context(page)`
2. `await wait_for_nfa_ready(ctx)`
3. Interact using `ctx.locator(...)`
4. Reuse the same context (it works for both Page and Frame)

Example:

```python
ctx = await resolve_nfa_context(page)
await ctx.locator(f"{SELECTOR} input").fill(value)
await ctx.locator(f"{SELECTOR} button").click()
await ctx.wait_for_timeout(2000)
```

## Error Handling

Always wrap operations in try/except:

```python
try:
    ctx = await resolve_nfa_context(page)
    # ... operations
except Exception as e:
    logger.error(f"Error: {e}")
    return None
```

## Timeouts

Configure timeouts appropriately:

- Navigation: 30000ms (30s)
- Element wait: 10000ms (10s)
- Form ready: 30000ms (30s)

## Best Practices

1. **Wait for elements**: Always wait for elements before interaction
2. **Use context locators**: Always interact through the `ctx.locator(...)` API
3. **Handle timeouts**: Set appropriate timeouts for slow operations
4. **Log operations**: Log all major operations for debugging
5. **Retry on failure**: Implement retry logic for transient errors

