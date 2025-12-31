from __future__ import annotations

import base64
import logging
from email.mime.text import MIMEText
from typing import Any

from googleapiclient.errors import HttpError

from app.integrations.gmail.gmail_auth import build_gmail_service

logger = logging.getLogger(__name__)


def _build_message(
    to: str, subject: str, body: str, from_email: str | None
) -> dict[str, Any]:
    """
    Build a raw RFC 2822 message payload encoded for Gmail API.
    """
    if not to:
        raise ValueError("Parameter 'to' is required for draft creation.")
    if not subject:
        raise ValueError("Parameter 'subject' is required for draft creation.")

    message = MIMEText(body or "")
    message["to"] = to
    message["subject"] = subject
    if from_email:
        message["from"] = from_email

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw_message}


def create_gmail_draft(
    to: str,
    subject: str,
    body: str,
    from_email: str | None = None,
) -> str:
    """
    Create a Gmail draft using compose scope only. Returns the draft ID.
    """
    service = build_gmail_service()
    payload = {"message": _build_message(to, subject, body, from_email)}

    try:
        draft = (
            service.users()
            .drafts()
            .create(userId="me", body=payload)
            .execute(num_retries=3)
        )
    except HttpError as exc:
        logger.exception("Gmail API error while creating draft: %s", exc)
        raise

    draft_id = draft.get("id")
    if not draft_id:
        raise RuntimeError("Draft creation succeeded but no draft ID was returned.")

    logger.info("Created Gmail draft with id: %s", draft_id)
    return draft_id
