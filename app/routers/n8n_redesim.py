"""n8n-compatible REDESIM endpoints.
All responses follow n8n-friendly format: {success, data, errors}.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.modules.redesim import GmailService, REDESIMExtractor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/redesim", tags=["n8n", "redesim"])


class N8NResponse(BaseModel):
    """Standard n8n response format."""

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class ExtractRequest(BaseModel):
    """REDESIM extraction request."""

    url: str | None = Field(
        None, description="Optional URL to extract from",
    )
    config: dict[str, Any] | None = Field(
        None, description="Optional extraction configuration",
    )


class CreateDraftRequest(BaseModel):
    """Gmail draft creation request."""

    to: str = Field(..., description="Recipient email address(es)")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")
    attachments: list[str] | None = Field(
        None, description="Optional list of attachment file paths",
    )


class SendEmailRequest(BaseModel):
    """Send email from draft request."""

    draft_id: str = Field(..., description="Gmail draft ID to send")


@router.post("/extract")
async def extract_redesim(request: ExtractRequest) -> N8NResponse:
    """Extract REDESIM data using browser automation.

    n8n-compatible endpoint for REDESIM extraction.
    """
    errors: list[str] = []
    data: dict[str, Any] = {}

    try:
        extractor = REDESIMExtractor(config=request.config or {})
        result = await extractor.process_all()

        if result.get("success"):
            data = {
                "job_id": result.get("report_path", ""),
                "processes_found": len(result.get("results", [])),
                "report_path": result.get("report_path"),
                "results": result.get("results", [])[:10],  # Limit to first 10
            }
            return N8NResponse(success=True, data=data, errors=errors)
        errors.append(result.get("message", "Extraction failed"))
        return N8NResponse(success=False, data=data, errors=errors)

    except Exception as e:
        logger.error(f"Error in REDESIM extraction: {e}", exc_info=True)
        errors.append(str(e))
        return N8NResponse(success=False, data=data, errors=errors)


@router.post("/email/create-draft")
async def create_draft(request: CreateDraftRequest) -> N8NResponse:
    """Create Gmail draft.

    n8n-compatible endpoint for Gmail draft creation.
    """
    errors: list[str] = []
    data: dict[str, Any] = {}

    try:
        gmail_service = GmailService()
        draft = gmail_service.create_draft(
            to=request.to,
            subject=request.subject,
            body=request.body,
            attachments=request.attachments,
        )

        if draft:
            data = {
                "draft_id": draft.get("id", ""),
                "message_id": draft.get("message", {}).get("id", ""),
                "thread_id": draft.get("message", {}).get("threadId", ""),
            }
            return N8NResponse(success=True, data=data, errors=errors)
        errors.append("Failed to create draft")
        return N8NResponse(success=False, data=data, errors=errors)

    except FileNotFoundError as e:
        error_msg = f"Attachment file not found: {e}"
        logger.exception(error_msg)
        errors.append(error_msg)
        return N8NResponse(success=False, data=data, errors=errors)
    except Exception as e:
        logger.error(f"Error creating draft: {e}", exc_info=True)
        errors.append(str(e))
        return N8NResponse(success=False, data=data, errors=errors)


@router.post("/email/send")
async def send_email(request: SendEmailRequest) -> N8NResponse:
    """Send email from draft.

    n8n-compatible endpoint for sending emails from drafts.
    """
    errors: list[str] = []
    data: dict[str, Any] = {}

    try:
        gmail_service = GmailService()
        success = gmail_service.send_email(request.draft_id)

        if success:
            data = {
                "draft_id": request.draft_id,
                "sent": True,
            }
            return N8NResponse(success=True, data=data, errors=errors)
        errors.append("Failed to send email")
        return N8NResponse(success=False, data=data, errors=errors)

    except Exception as e:
        logger.error(f"Error sending email: {e}", exc_info=True)
        errors.append(str(e))
        return N8NResponse(success=False, data=data, errors=errors)
