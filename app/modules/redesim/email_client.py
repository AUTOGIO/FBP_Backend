"""Gmail API Client for REDESIM Email Extractor
Handles Gmail OAuth and draft creation.
"""

from __future__ import annotations

import base64
import logging
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mimetypes import guess_type
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.modules.redesim.gmail_auth import (
    DEFAULT_CREDENTIALS_PATH,
    DEFAULT_TOKEN_PATH,
    SCOPES,
    get_gmail_credentials,
)

logger = logging.getLogger(__name__)


class GmailClient:
    """Gmail API client for creating drafts.

    Note: Credentials and token paths should be configured via environment
    variables or config files, not hard-coded.
    """

    def __init__(
        self,
        credentials_path: str | None = None,
        token_path: str | None = None,
    ) -> None:
        """Initialize Gmail client.

        Args:
            credentials_path: Path to credentials.json (defaults to credentials/gmail_credentials.json)
            token_path: Path to token.json (defaults to credentials/gmail_token.json)

        """
        resolved_credentials_path = Path(
            credentials_path or DEFAULT_CREDENTIALS_PATH,
        ).expanduser()
        resolved_token_path = Path(token_path or DEFAULT_TOKEN_PATH).expanduser()

        self.creds = None
        self.service = None

        try:
            self.creds = get_gmail_credentials(
                credentials_path=resolved_credentials_path,
                token_path=resolved_token_path,
                scopes=SCOPES,
            )
            self.service = build(
                "gmail",
                "v1",
                credentials=self.creds,
                cache_discovery=False,
            )
            logger.info("Gmail API service initialized successfully")

        except Exception as e:
            logger.error(
                f"Error initializing Gmail client: {e}",
                exc_info=True,
            )
            raise

    def create_draft(
        self,
        to: str,
        subject: str,
        message_text: str,
        attachments: list[str] | None = None,
    ) -> dict | None:
        """Create and insert a draft email.

        Args:
            to: Recipient email address
            subject: Email subject
            message_text: Email body text
            attachments: Optional list of file paths to attach

        Returns:
            Draft object, including draft id and message meta data, or None on error

        """
        try:
            mime_message = self._build_message(
                to,
                subject,
                message_text,
                attachments,
            )
            create_message = {
                "message": {
                    "raw": base64.urlsafe_b64encode(
                        mime_message.as_bytes(),
                    ).decode(),
                },
            }

            draft = (
                self.service.users()
                .drafts()
                .create(userId="me", body=create_message)
                .execute()
            )
            logger.info(f"Draft created: {draft.get('id', 'unknown')}")
            return draft
        except FileNotFoundError as error:
            logger.exception(f"Attachment not found: {error}")
            return None
        except HttpError as error:
            logger.exception(f"Gmail API error: {error}")
            return None
        except Exception as error:
            logger.error(
                f"Unexpected error creating draft: {error}",
                exc_info=True,
            )
            return None

    def _build_message(
        self,
        to: str,
        subject: str,
        message_text: str,
        attachments: list[str] | None = None,
    ):
        """Build MIME message with optional attachments."""
        attachments = attachments or []

        if attachments:
            message = MIMEMultipart()
            message.attach(MIMEText(message_text, "plain", "utf-8"))

            for attachment_path in attachments:
                path = Path(attachment_path)
                if not path.exists():
                    raise FileNotFoundError(path)

                content_type, encoding = guess_type(str(path))
                if content_type is None or encoding is not None:
                    content_type = "application/octet-stream"
                main_type, sub_type = content_type.split("/", 1)

                with open(path, "rb") as attachment_file:
                    mime_part = MIMEBase(main_type, sub_type)
                    mime_part.set_payload(attachment_file.read())

                encoders.encode_base64(mime_part)
                mime_part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{path.name}"',
                )
                message.attach(mime_part)
        else:
            message = MIMEText(message_text, "plain", "utf-8")

        message["To"] = to
        message["Subject"] = subject
        return message
