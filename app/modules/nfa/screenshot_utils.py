"""Screenshot utilities for NFA automation."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from app.core.config import settings

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


def resolve_screenshots_dir(
    screenshots_dir: Optional[str | Path] = None,
) -> Path:
    """Resolve screenshots directory path.

    Args:
        screenshots_dir: Optional explicit screenshots directory path.
            If None, uses config.paths.screenshots_dir.
            If relative, joins with project_root.

    Returns:
        Resolved absolute Path to screenshots directory.

    """
    if screenshots_dir is None:
        # Use config default
        resolved = settings.paths.screenshots_dir
    else:
        screenshots_path = Path(screenshots_dir)
        if screenshots_path.is_absolute():
            resolved = screenshots_path
        else:
            # Relative path: join with project_root
            resolved = settings.paths.project_root / screenshots_path

    return resolved.resolve()


async def save_screenshot(
    page: Page,
    screenshots_dir: Optional[str | Path] = None,
    filename: Optional[str] = None,
) -> Optional[Path]:
    """Save screenshot from Playwright page.

    Args:
        page: Playwright Page instance.
        screenshots_dir: Directory to save screenshot (will be created if needed).
        filename: Optional filename. If None, generates timestamp-based name.

    Returns:
        Path to saved screenshot file, or None if save failed.

    """
    try:
        # Resolve screenshots directory
        screenshots_path = resolve_screenshots_dir(screenshots_dir)

        # Create directory if it doesn't exist
        screenshots_path.mkdir(parents=True, exist_ok=True)

        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"nfa_screenshot_{timestamp}.png"
        elif not filename.endswith((".png", ".jpg", ".jpeg")):
            filename = f"{filename}.png"

        # Full path to screenshot file
        screenshot_file = screenshots_path / filename

        # Save screenshot
        await page.screenshot(path=str(screenshot_file), full_page=True)

        logger.info(
            f"Screenshot saved: {screenshot_file}",
            extra={"screenshot_path": str(screenshot_file)},
        )

        return screenshot_file

    except Exception as e:
        logger.error(
            f"Failed to save screenshot: {e}",
            exc_info=True,
            extra={"screenshots_dir": str(screenshots_dir), "screenshot_filename": filename},
        )
        return None

