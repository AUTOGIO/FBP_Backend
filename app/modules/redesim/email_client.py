"""Gmail API Client for REDESIM Email Extractor
Handles Gmail OAuth and draft creation.
"""
from __future__ import annotations

import base64
import logging
import os.path
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mimetypes import guess_type
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


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
            credentials_path: Path to credentials.json (defaults to config/auth/credentials.json)
            token_path: Path to token.json (defaults to config/auth/token.json)

        """
        # Use FBP project root for default paths (consolidated in config/auth/)
        if credentials_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            auth_dir = project_root / "config" / "auth"
            auth_dir.mkdir(parents=True, exist_ok=True)
            credentials_path = str(auth_dir / "credentials.json")

        if token_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            auth_dir = project_root / "config" / "auth"
            auth_dir.mkdir(parents=True, exist_ok=True)
            token_path = str(auth_dir / "token.json")

        self.creds = None
        self.service = None

        try:
            # The file token.json stores the user's access and refresh tokens, and is
            # created automatically when the authorization flow completes for the first
            # time.
            if os.path.exists(token_path):
                self.creds = Credentials.from_authorized_user_file(
                    token_path, SCOPES,
                )
                logger.debug(f"Loaded credentials from {token_path}")

            # If there are no (valid) credentials available, let the user log in.
            if not self.creds or not self.creds.valid:
                if (
                    self.creds
                    and self.creds.expired
                    and self.creds.refresh_token
                ):
                    logger.info("Refreshing expired credentials...")
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(credentials_path):
                        msg = (
                            f"Credentials file not found: {credentials_path}. "
                            "Please download credentials.json from Google Cloud Console."
                        )
                        raise FileNotFoundError(
                            msg,
                        )
                    logger.info("Starting OAuth flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, SCOPES,
                    )
                    self.creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open(token_path, "w") as token:
                    token.write(self.creds.to_json())
                logger.info(f"Credentials saved to {token_path}")

            self.service = build("gmail", "v1", credentials=self.creds)
            logger.info("Gmail API service initialized successfully")

        except Exception as e:
            logger.error(
                f"Error initializing Gmail client: {e}", exc_info=True,
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
                to, subject, message_text, attachments,
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
                f"Unexpected error creating draft: {error}", exc_info=True,
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
