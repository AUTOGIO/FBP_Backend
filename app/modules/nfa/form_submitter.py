"""Form Submitter Module
Handles submitting the NFA form after all fields are filled.
"""

from __future__ import annotations

import logging
import random

from app.modules.nfa.delays import AFTER_SUBMIT_DELAY, BEFORE_SUBMIT_DELAY
from app.modules.nfa.nfa_context import NFAContext, get_page_from_context

logger = logging.getLogger(__name__)


async def submeter_nfa(ctx: NFAContext) -> tuple[bool, str | None]:
    """Submit NFA form and extract NFA number.

    Args:
        ctx: Page or Frame context

    Returns:
        Tuple of (success: bool, nfa_number: str | None)

    """
    try:
        page = get_page_from_context(ctx)

        logger.info("Submitting NFA form...")

        # Wait before submit
        await page.wait_for_timeout(BEFORE_SUBMIT_DELAY)

        # Multiple selector strategies for submit button
        submit_selectors = [
            "input[type='submit'][value*='Submeter' i]",
            "input[type='submit'][value*='Enviar' i]",
            "input[type='submit'][value*='Confirmar' i]",
            "input[type='submit'][value*='Salvar' i]",
            "button:has-text('Submeter')",
            "button:has-text('Enviar')",
            "button:has-text('Confirmar')",
            "button:has-text('Salvar')",
            "a:has-text('Submeter')",
            "a:has-text('Enviar')",
            # Table-based selectors
            "table:has-text('Submeter') input[type='submit']",
            "td:has-text('Submeter') + td input",
        ]

        submitted = False
        for selector in submit_selectors:
            try:
                element = ctx.locator(selector).first
                if await element.is_visible(timeout=3000):
                    await element.click()
                    logger.info(f"✓ Clicked submit button via selector: {selector}")
                    submitted = True
                    await page.wait_for_timeout(AFTER_SUBMIT_DELAY)
                    break
            except Exception as e:
                logger.debug(f"Submit selector {selector} failed: {e}")
                continue

        if not submitted:
            logger.error("Could not find submit button with any selector")
            return False, None

        # Wait for form submission to complete
        await page.wait_for_timeout(3000)

        # Try to wait for success message or NFA number
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        # Try to extract NFA number from page
        nfa_number = None
        nfa_extract_selectors = [
            "text=/NFA[\\s\\-]?[0-9]+/i",
            "text=/Nota[\\s]+Fiscal[\\s]+[0-9]+/i",
            "td:has-text('NFA') + td",
            "td:has-text('Nota Fiscal') + td",
        ]

        for selector in nfa_extract_selectors:
            try:
                element = ctx.locator(selector).first
                if await element.is_visible(timeout=3000):
                    text = await element.text_content()
                    # Extract numbers from text
                    import re

                    numbers = re.findall(r"\d+", text or "")
                    if numbers:
                        nfa_number = numbers[0]
                        logger.info(f"✓ Extracted NFA number: {nfa_number}")
                        break
            except Exception:
                continue

        if nfa_number:
            logger.info(f"NFA submitted successfully. NFA Number: {nfa_number}")
            return True, nfa_number
        else:
            logger.warning("NFA submitted but could not extract NFA number")
            return True, None

    except Exception as e:
        logger.error(f"Error submitting NFA form: {e}", exc_info=True)
        return False, None
