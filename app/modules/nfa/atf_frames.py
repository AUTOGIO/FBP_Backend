"""Deprecated ATF frame helpers.

All legacy frame logic moved to app.modules.nfa.nfa_context.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.nfa.nfa_context import NFAContext, wait_for_nfa_ready

if TYPE_CHECKING:  # pragma: no cover
    from playwright.async_api import Page


async def get_main_frame(page: Page) -> None:
    """Raise to force callers to migrate to resolve_nfa_context."""
    raise RuntimeError("Deprecated: replace usages with resolve_nfa_context")


async def wait_for_nfa_fields(ctx: NFAContext) -> None:
    """Compatibility wrapper for wait_for_nfa_ready."""
    await wait_for_nfa_ready(ctx)
