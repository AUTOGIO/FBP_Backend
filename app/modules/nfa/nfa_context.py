"""NFA Context Resolution Helpers.

Provides unified handling for ATF's NFA form - now always uses main page (no frames).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging_config import setup_logger

if TYPE_CHECKING:  # pragma: no cover
    from playwright.async_api import Page
else:  # pragma: no cover
    Page = None  # type: ignore[assignment]

logger = setup_logger(__name__)

NFAContext = "Page"

_READY_SELECTORS = [
    "select[name='cmbNaturezaOperacao']",  # Most reliable - main form field
    "select[name='cmbTpOperacao']",  # Tipo de Operação
    "table:has-text('Emitente')",  # Emitente table
    "table:has-text('Destinatário')",  # Destinatário table
    "textarea[name='txaDsDetalheProduto']",  # Product description
    "input[name='edtVlProduto']",  # Product value
    "select[name='cmbUnidMedida']",  # Unit of measure
    "text=Nota Fiscal",
    "text=Repartição Fiscal",
    "input",
]


async def resolve_nfa_context(page: Page) -> Page:
    """Return the page context (no frames - form is directly on main page).

    Args:
        page: Playwright Page instance

    Returns:
        Page instance (always main page, no frames)
    """
    logger.info("Resolving NFA context (using main page - no frames)")

    try:
        await page.wait_for_load_state("domcontentloaded", timeout=10000)
    except Exception:
        logger.debug("DOM content load state wait skipped due to navigation timing.")

    logger.info("NFA context resolved: using main page")
    return page


async def wait_for_nfa_ready(ctx: Page, timeout: int = 45000) -> None:
    """Wait until the NFA UI exposes key selectors on main page.

    Args:
        ctx: Page context
        timeout: Timeout in milliseconds
    """
    timeout = max(timeout, 1000)
    per_selector_timeout = max(timeout // len(_READY_SELECTORS), 3000)

    logger.info(f"Waiting for NFA form to be ready (timeout: {timeout}ms)...")

    found_selector = None
    for selector in _READY_SELECTORS:
        try:
            logger.debug(f"Trying selector: {selector}")
            await ctx.wait_for_selector(selector, timeout=per_selector_timeout)
            logger.info(f"NFA context ready via selector: {selector}")
            found_selector = selector
            break
        except Exception as exc:
            logger.debug(f"Selector {selector} not ready yet: {exc}")
            continue

    if not found_selector:
        # Try to get page content for debugging
        try:
            content_preview = await ctx.content()
            # Log first 500 chars of HTML for debugging
            logger.warning(f"Page content preview: {content_preview[:500]}...")
        except Exception:
            pass

        msg = f"NFA context not ready: no known selectors found. Tried: {_READY_SELECTORS}"
        logger.error(msg)
        raise RuntimeError(msg)

    logger.info("NFA form is ready and fields are available")


def get_page_from_context(ctx: Page) -> Page:
    """Return the page (always the same since no frames).

    Args:
        ctx: Page context

    Returns:
        Page instance
    """
    return ctx


__all__ = [
    "NFAContext",
    "get_page_from_context",
    "resolve_nfa_context",
    "wait_for_nfa_ready",
]
