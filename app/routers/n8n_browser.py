"""n8n-compatible browser endpoints.
All responses follow n8n-friendly format: {success, data, errors}.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.modules.redesim.browser_extractor import BrowserExtractor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/browser", tags=["n8n", "browser"])


class N8NResponse(BaseModel):
    """Standard n8n response format."""

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class HTMLCaptureRequest(BaseModel):
    """HTML capture request."""

    url: str = Field(..., description="URL to capture")
    use_cursor: bool = Field(
        True, description="Try Cursor browser first, fallback to Playwright",
    )
    config: dict[str, Any] | None = Field(
        None, description="Optional browser configuration",
    )


@router.post("/html")
async def capture_html(request: HTMLCaptureRequest) -> N8NResponse:
    """Capture HTML content from a URL.

    n8n-compatible endpoint for browser HTML capture.
    """
    errors: list[str] = []
    data: dict[str, Any] = {}

    try:
        browser_extractor = BrowserExtractor(config=request.config or {})

        if request.use_cursor:
            html = await browser_extractor.cursor_fallback_capture(request.url)
        else:
            html = await browser_extractor.capture_page(request.url)

        data = {
            "url": request.url,
            "html_length": len(html),
            "html": html[:10000],  # Limit HTML in response (first 10KB)
            "truncated": len(html) > 10000,
        }

        return N8NResponse(success=True, data=data, errors=errors)

    except Exception as e:
        logger.error(f"Error capturing HTML: {e}", exc_info=True)
        errors.append(str(e))
        return N8NResponse(success=False, data=data, errors=errors)
