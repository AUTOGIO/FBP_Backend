"""Create Gmail drafts using compose-only scope."""

from __future__ import annotations

import base64
import logging
from collections.abc import Sequence
from email.message import EmailMessage
from typing import Optional, cast

from googleapiclient.discovery import build  # type: ignore[import]
from googleapiclient.errors import HttpError  # type: ignore[import]

from app.modules.redesim.gmail_auth import get_gmail_credentials

logger = logging.getLogger(__name__)


def _build_message(
    to: str | Sequence[str],
    subject: str,
    body: str,
    from_email: Optional[str] = None,
) -> EmailMessage:
    """Build a simple MIME message (text/plain)."""
    msg = EmailMessage()
    if isinstance(to, (list, tuple, set)):
        msg["To"] = ", ".join(to)
    else:
        msg["To"] = to
    if from_email:
        msg["From"] = from_email
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def create_gmail_draft(
    to: str | Sequence[str],
    subject: str,
    body: str,
    from_email: Optional[str] = None,
) -> Optional[str]:
    """Create a Gmail draft and return its draft_id.

    Note: This function is synchronous but safe to call from async contexts
    via run_in_executor if needed.
    """
    try:
        credentials = get_gmail_credentials()
        service = build(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

        message = _build_message(
            to=to,
            subject=subject,
            body=body,
            from_email=from_email,
        )
        encoded_message = base64.urlsafe_b64encode(
            message.as_bytes(),
        ).decode()
        create_body = {"message": {"raw": encoded_message}}

        draft = service.users().drafts().create(userId="me", body=create_body).execute()

        draft_id = cast(Optional[str], draft.get("id"))
        if draft_id:
            logger.info("Created Gmail draft with id %s", draft_id)
        else:
            logger.warning("Draft created but id missing in response")
        return draft_id

    except HttpError as exc:
        logger.error(
            "Gmail API error while creating draft: %s",
            exc,
            exc_info=True,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Unexpected error while creating draft: %s",
            exc,
            exc_info=True,
        )
        return None
