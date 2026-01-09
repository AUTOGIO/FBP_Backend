"""Informações Adicionais Form Filler
Handles filling the "Informações Adicionais" (Additional Information) field in NFA form using direct main-page selectors.
"""

from __future__ import annotations

import logging
import random

from app.modules.nfa.delays import (
    AFTER_INFORMACOES_ADICIONAIS_DELAY,
    FIELD_DELAY,
)
from app.modules.nfa.nfa_context import NFAContext, get_page_from_context
from app.modules.nfa.screenshot_utils import (
    resolve_screenshots_dir,
    save_screenshot,
)

logger = logging.getLogger(__name__)


async def preencher_informacoes_adicionais(
    ctx: NFAContext,
    texto: str = "Remessa por conta de contrato de locacao",
) -> NFAContext | None:
    """Fill "Informações Adicionais" field in NFA form using direct main-page selectors.

    Args:
        ctx: Page context
        texto: Text to fill (default: "Remessa por conta de contrato de locacao")

    Returns:
        Updated NFAContext or None on error

    """
    try:
        page = get_page_from_context(ctx)
        screenshots_dir = resolve_screenshots_dir()

        logger.info(f"Filling Informações Adicionais: {texto}")

        # Try direct selector first
        selectors = [
            "textarea[name*='Informacoes' i]",
            "textarea[name*='Informações' i]",
            "textarea[name*='Adicionais' i]",
            "textarea[id*='Informacoes' i]",
            "textarea[id*='Informações' i]",
            "textarea[id*='Adicionais' i]",
            "table:has-text('Informações Adicionais') textarea",
            "table:has-text('Informacoes Adicionais') textarea",
            "td:has-text('Informações Adicionais') + td textarea",
            "td:has-text('Informacoes Adicionais') + td textarea",
        ]

        filled = False
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=3000):
                    await element.clear()
                    await page.wait_for_timeout(random.randint(100, 300))
                    await element.type(texto, delay=random.randint(50, 150))
                    logger.info(
                        f"✓ Informações Adicionais filled via selector: {selector}"
                    )
                    await page.wait_for_timeout(FIELD_DELAY)
                    await save_screenshot(
                        page,
                        screenshots_dir,
                        filename="informacoes_adicionais_filled.png",
                    )
                    filled = True
                    break
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        if not filled:
            logger.warning(
                "Could not find Informações Adicionais field with any selector"
            )
            # Try to expand section if collapsed
            try:
                expand_selectors = [
                    "text=Informações Adicionais",
                    "text=Informacoes Adicionais",
                    "a:has-text('Informações Adicionais')",
                    "a:has-text('Informacoes Adicionais')",
                    "[onclick*='Informacoes']",
                    "[onclick*='Informações']",
                ]
                for expand_selector in expand_selectors:
                    try:
                        expand_btn = page.locator(expand_selector).first
                        if await expand_btn.is_visible(timeout=2000):
                            await expand_btn.click()
                            logger.info("✓ Expanded Informações Adicionais section")
                            await page.wait_for_timeout(1000)
                            await save_screenshot(
                                page,
                                screenshots_dir,
                                filename="informacoes_adicionais_expanded.png",
                            )
                            # Retry filling after expansion
                            for selector in selectors[:5]:
                                try:
                                    element = page.locator(selector).first
                                    if await element.is_visible(timeout=2000):
                                        await element.clear()
                                        await element.type(
                                            texto, delay=random.randint(50, 150)
                                        )
                                        logger.info(
                                            "✓ Informações Adicionais filled after expansion"
                                        )
                                        filled = True
                                        break
                                except Exception:
                                    continue
                            if filled:
                                break
                    except Exception:
                        continue
            except Exception as expand_error:
                logger.debug(f"Failed to expand section: {expand_error}")

        if filled:
            await page.wait_for_timeout(AFTER_INFORMACOES_ADICIONAIS_DELAY)
            await save_screenshot(
                page, screenshots_dir, filename="informacoes_adicionais_complete.png"
            )
            logger.info("Informações Adicionais filled successfully")
            return ctx
        else:
            logger.error("Failed to fill Informações Adicionais field")
            await save_screenshot(
                page, screenshots_dir, filename="informacoes_adicionais_error.png"
            )
            return None

    except Exception as e:
        logger.error(f"Error filling Informações Adicionais: {e}", exc_info=True)
        try:
            page = get_page_from_context(ctx)
            screenshots_dir = resolve_screenshots_dir()
            await save_screenshot(
                page, screenshots_dir, filename="informacoes_adicionais_error.png"
            )
        except Exception:
            pass
        return None
