"""NFA Form Utilities
Helper functions for setting form fields in frmIncluiNotaAvulsa using JavaScript.
"""
from __future__ import annotations

from typing import Any

from app.core.logging_config import setup_logger
from app.modules.nfa.nfa_context import NFAContext

logger = setup_logger(__name__)

# Form name in ATF system
NFA_FORM_NAME = "frmIncluiNotaAvulsa"


async def set_form_value(ctx: NFAContext, field: str, value: str) -> None:
    """Set a field value inside frmIncluiNotaAvulsa directly using JavaScript.

    Args:
        ctx: Page or Frame instance able to evaluate JavaScript
        field: Field name in the form
        value: Value to set
    """
    # Escape quotes in value
    safe_value = str(value).replace('"', '\\"').replace("'", "\\'")

    js = f"""
        const form = document.{NFA_FORM_NAME};
        if (form && form['{field}']) {{
            form['{field}'].value = "{safe_value}";
        }} else {{
            console.warn('Field not found: {field}');
        }}
    """
    await ctx.evaluate(js)
    logger.debug(f"Set form field '{field}' = '{value}'")


async def get_form_value(ctx: NFAContext, field: str) -> str | None:
    """Get a field value from frmIncluiNotaAvulsa.

    Args:
        ctx: Page or Frame instance
        field: Field name in the form

    Returns:
        Field value or None if not found
    """
    js = f"""
        const form = document.{NFA_FORM_NAME};
        if (form && form['{field}']) {{
            return form['{field}'].value;
        }}
        return null;
    """
    result = await ctx.evaluate(js)
    return result


async def click_form_button(ctx: NFAContext, button_name: str) -> None:
    """Click a button inside frmIncluiNotaAvulsa.

    Args:
        ctx: Page or Frame instance
        button_name: Button name in the form
    """
    js = f"""
        const form = document.{NFA_FORM_NAME};
        if (form && form['{button_name}']) {{
            form['{button_name}'].click();
        }} else {{
            console.warn('Button not found: {button_name}');
        }}
    """
    await ctx.evaluate(js)
    logger.debug(f"Clicked form button '{button_name}'")


async def select_form_option(
    ctx: NFAContext,
    field: str,
    value: str,
) -> None:
    """Select an option in a dropdown field.

    Args:
        ctx: Page or Frame instance
        field: Field name in the form
        value: Option value to select
    """
    safe_value = str(value).replace('"', '\\"').replace("'", "\\'")

    js = f"""
        const form = document.{NFA_FORM_NAME};
        if (form && form['{field}']) {{
            form['{field}'].value = "{safe_value}";
            // Trigger change event
            const event = new Event('change', {{ bubbles: true }});
            form['{field}'].dispatchEvent(event);
        }} else {{
            console.warn('Select field not found: {field}');
        }}
    """
    await ctx.evaluate(js)
    logger.debug(f"Selected option '{value}' in field '{field}'")


async def fill_form_fields(ctx: NFAContext, fields: dict[str, Any]) -> None:
    """Fill multiple form fields at once.

    Args:
        ctx: Page or Frame instance
        fields: Dictionary of field_name: value pairs
    """
    for field, value in fields.items():
        if value is not None and value != "":
            await set_form_value(ctx, field, str(value))


async def submit_form(ctx: NFAContext) -> None:
    """Submit the NFA form.

    Args:
        ctx: Page or Frame instance
    """
    js = f"""
        const form = document.{NFA_FORM_NAME};
        if (form) {{
            form.submit();
        }} else {{
            console.warn('Form not found: {NFA_FORM_NAME}');
        }}
    """
    await ctx.evaluate(js)
    logger.info("Form submitted")


async def click_calcular(ctx: NFAContext) -> None:
    """Click the CALCULAR button to calculate NFA values.

    Args:
        ctx: Page or Frame instance
    """
    # Try multiple button names/IDs
    button_selectors = [
        "btnCalcular",
        "btCalcular",
        "btnCalc",
    ]

    for button in button_selectors:
        try:
            await click_form_button(ctx, button)
            logger.info("CALCULAR button clicked")
            return
        except Exception:
            continue

    # Fallback: try locator click
    try:
        await ctx.locator("button:has-text('Calcular')").click()
        logger.info("CALCULAR button clicked (via locator)")
    except Exception as e:
        logger.warning(f"Could not click CALCULAR button: {e}")

