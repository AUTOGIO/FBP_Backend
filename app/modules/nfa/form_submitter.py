"""Form Submitter Module
Handles submitting the NFA form after all fields are filled.
"""

from __future__ import annotations

import logging
import random
import re
from urllib.parse import parse_qs, urlparse

from app.modules.nfa.delays import AFTER_SUBMIT_DELAY, BEFORE_SUBMIT_DELAY
from app.modules.nfa.nfa_context import NFAContext, get_page_from_context

logger = logging.getLogger(__name__)


def _extract_nfa_number_from_text(text: str) -> str | None:
    if not text:
        return None

    # Prefer matches explicitly anchored to NFA wording.
    patterns = [
        r"\bNFA\b\D{0,40}?(\d{4,})",
        r"\bNota\s+Fiscal\s+Avulsa\b\D{0,60}?(\d{4,})",
        r"\bNota\s+Fiscal\b\D{0,60}?(\d{4,})",
        r"\bN[úu]mero\b\D{0,20}?(\d{4,})",
    ]

    candidates: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            candidates.append(match.group(1))

    if not candidates:
        return None

    # Filter out obvious document numbers (CPF 11 digits / CNPJ 14 digits).
    filtered = [c for c in candidates if len(c) not in (11, 14)]
    if not filtered:
        filtered = candidates

    # Choose the most plausible: longest (often includes leading zeros), then last.
    filtered.sort(key=lambda v: (len(v), candidates.index(v)))
    return filtered[-1]


def _extract_nfa_number_from_url(url: str) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        for key in ("nfa", "nrNfa", "nr_nfa", "numeroNfa", "numero", "nr"):
            if key in qs and qs[key]:
                val = re.sub(r"\D+", "", qs[key][0])
                if len(val) >= 4:
                    return val
    except Exception:
        return None
    return None


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

        # Try to extract NFA number from URL first (sometimes present after submit)
        nfa_number = _extract_nfa_number_from_url(page.url)
        if nfa_number:
            logger.info(f"✓ Extracted NFA number from URL: {nfa_number}")

        # Then try targeted DOM locations
        if not nfa_number:
            nfa_extract_selectors = [
                "td:has-text('NFA') + td",
                "td:has-text('Nota Fiscal Avulsa') + td",
                "td:has-text('Nota Fiscal') + td",
                "text=/\\bNFA\\b/i",
                "text=/Nota\\s+Fiscal/i",
            ]

            for selector in nfa_extract_selectors:
                try:
                    element = ctx.locator(selector).first
                    if await element.is_visible(timeout=2500):
                        text = (await element.text_content()) or ""
                        candidate = _extract_nfa_number_from_text(text)
                        if candidate:
                            nfa_number = candidate
                            logger.info(
                                f"✓ Extracted NFA number via selector {selector}: {nfa_number}"
                            )
                            break
                except Exception:
                    continue

        # Finally, search the full page text anchored by NFA wording.
        if not nfa_number:
            try:
                body_text = await page.locator("body").inner_text()
                candidate = _extract_nfa_number_from_text(body_text)
                if candidate:
                    nfa_number = candidate
                    logger.info(f"✓ Extracted NFA number from page text: {nfa_number}")
            except Exception:
                pass

        if nfa_number:
            logger.info(f"NFA submitted successfully. NFA Number: {nfa_number}")
            return True, nfa_number
        else:
            logger.warning("NFA submitted but could not extract NFA number")
            return True, None

    except Exception as e:
        logger.error(f"Error submitting NFA form: {e}", exc_info=True)
        return False, None
