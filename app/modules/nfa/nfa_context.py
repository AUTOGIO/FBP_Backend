"""NFA Context Resolution Helpers.

Provides unified handling for ATF's NFA form whether it renders in the root DOM
or inside legacy frames.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union, cast

from app.core.logging_config import setup_logger

if TYPE_CHECKING:  # pragma: no cover
    from playwright.async_api import Frame, Page
else:  # pragma: no cover
    Frame = Any  # type: ignore[assignment]
    Page = Any  # type: ignore[assignment]

logger = setup_logger(__name__)

NFAContext = Union["Page", "Frame"]

_FRAME_NAME = "contents"
_FRAME_URL_KEYWORDS = ("nota", "nfa", "fis")
_READY_SELECTORS = [
    "text=Nota Fiscal",
    "text=Repartição Fiscal",
    "input[name*='CodigoNCM' i]",
    "input",
]


async def resolve_nfa_context(page: Page) -> NFAContext:
    """Return the proper context (Page or Frame) for interacting with the NFA form."""
    logger.debug("Resolving NFA context (root DOM vs iframe).")

    try:
        await page.wait_for_load_state("domcontentloaded")
    except Exception:
        logger.debug("DOM content load state wait skipped due to navigation timing.")

    frame = page.frame(name=_FRAME_NAME)
    if frame:
        logger.info("NFA context resolved via frame[name='contents'].")
        return frame

    for candidate in page.frames:
        candidate_url = (candidate.url or "").lower()
        if any(keyword in candidate_url for keyword in _FRAME_URL_KEYWORDS):
            logger.info("NFA context resolved via frame URL: %s", candidate.url)
            return candidate

    logger.info("Using root page as NFA context.")
    return page


async def wait_for_nfa_ready(ctx: NFAContext, timeout: int = 45000) -> None:
    """Wait until the NFA UI exposes key selectors, regardless of DOM context."""
    timeout = max(timeout, 1000)
    per_selector_timeout = max(timeout // len(_READY_SELECTORS), 3000)

    for selector in _READY_SELECTORS:
        try:
            await ctx.wait_for_selector(selector, timeout=per_selector_timeout)
            logger.debug("NFA context ready via selector %s", selector)
            return
        except Exception as exc:
            logger.debug("Selector %s not ready yet: %s", selector, exc)

    msg = "NFA context not ready: no known selectors found."
    logger.error(msg)
    raise RuntimeError(msg)


def get_page_from_context(ctx: NFAContext) -> Page:
    """Return the owning Page for the given context."""
    if hasattr(ctx, "page"):
        return cast("Frame", ctx).page
    return cast("Page", ctx)


__all__ = [
    "NFAContext",
    "get_page_from_context",
    "resolve_nfa_context",
    "wait_for_nfa_ready",
]

