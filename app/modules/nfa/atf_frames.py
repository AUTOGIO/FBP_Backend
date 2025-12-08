"""ATF Frame Navigation and Management - Utility Logs Only
No frame logic - form is now directly on main page.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def log_page_frames(page: Page) -> None:
    """Log all frames for debugging purposes only.
    
    Args:
        page: Playwright Page instance
    """
    try:
        all_frames = page.frames
        logger.info(f"Total frames detected: {len(all_frames)}")
        
        frame_urls = []
        for idx, frame in enumerate(all_frames):
            frame_url = frame.url or "about:blank"
            frame_name = frame.name or "unnamed"
            frame_urls.append(f"Frame {idx}: name='{frame_name}', url='{frame_url}'")
            logger.debug(f"Frame {idx}: name='{frame_name}', url='{frame_url}'")
        
        from app.core.config import settings
        logs_dir = settings.paths.project_root / "logs" / "nfa"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        frame_log_file = logs_dir / "frame_detection.log"
        with open(frame_log_file, "w", encoding="utf-8") as f:
            f.write("Frame Detection Log (for debugging only)\n")
            f.write("=" * 50 + "\n")
            for url_info in frame_urls:
                f.write(url_info + "\n")
        logger.info(f"Frame URLs logged to: {frame_log_file}")
        
    except Exception as e:
        logger.exception(f"Error logging frames: {e}")
