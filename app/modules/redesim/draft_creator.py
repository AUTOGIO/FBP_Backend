"""Gmail Draft Creator for REDESIM
Consolidated service for creating and managing Gmail drafts.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Sequence

from app.core.config import settings
from app.modules.redesim.email_client import GmailClient

logger = logging.getLogger(__name__)


class GmailService:
    """Unified Gmail service for creating drafts and sending emails.
    Consolidates GmailClient and draft creation logic.
    """

    def __init__(
        self,
        credentials_path: str | None = None,
        token_path: str | None = None,
    ) -> None:
        """Initialize Gmail service.

        Args:
            credentials_path: Optional path to credentials.json
            token_path: Optional path to token.json

        """
        # Use settings or default paths
        if credentials_path is None:
            credentials_path = (
                settings.GMAIL_CREDENTIALS_FILE or self._get_default_credentials_path()
            )

        if token_path is None:
            token_path = settings.GMAIL_TOKEN_FILE or self._get_default_token_path()

        self.client = GmailClient(
            credentials_path=credentials_path,
            token_path=token_path,
        )

    @staticmethod
    def _get_default_credentials_path() -> str:
        """Get default credentials path."""
        project_root = Path(__file__).parent.parent.parent.parent
        auth_dir = project_root / "credentials"
        auth_dir.mkdir(parents=True, exist_ok=True)
        return str(auth_dir / "gmail_credentials.json")

    @staticmethod
    def _get_default_token_path() -> str:
        """Get default token path."""
        project_root = Path(__file__).parent.parent.parent.parent
        auth_dir = project_root / "credentials"
        auth_dir.mkdir(parents=True, exist_ok=True)
        return str(auth_dir / "gmail_token.json")

    def create_draft(
        self,
        to: str | Sequence[str],
        subject: str,
        body: str,
        attachments: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Create a Gmail draft.

        Args:
            to: Recipient email address(es) - comma-separated string or list
            subject: Email subject
            body: Email body text
            attachments: Optional list of file paths to attach

        Returns:
            Draft dictionary with id and message metadata, or None on error

        """
        try:
            # Normalize 'to' parameter
            to_value = (
                ", ".join(to)
                if isinstance(to, Sequence) and not isinstance(to, str)
                else to
            )

            draft = self.client.create_draft(
                to=to_value,
                subject=subject,
                message_text=body,
                attachments=attachments,
            )

            if draft:
                logger.info(
                    "Draft created successfully: %s", draft.get("id", "unknown")
                )
                return draft
            logger.warning("Failed to create draft (returned None)")
            return None

        except FileNotFoundError as e:
            logger.exception(f"Attachment file not found: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating draft: {e}", exc_info=True)
            return None

    def send_email(self, draft_id: str) -> bool:
        """Send an email from a draft.

        Args:
            draft_id: Gmail draft ID

        Returns:
            True if sent successfully, False otherwise

        """
        try:
            if not self.client.service:
                logger.error("Gmail service not initialized")
                return False

            message = (
                self.client.service.users()
                .drafts()
                .send(userId="me", body={"id": draft_id})
                .execute()
            )

            if message:
                logger.info(
                    f"Email sent successfully: {message.get('id', 'unknown')}",
                )
                return True
            logger.warning("Failed to send email (returned None)")
            return False

        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            return False

    def create_draft_from_json(
        self,
        json_path: Path,
    ) -> dict[str, Any] | None:
        """Create Gmail draft from JSON file.

        Args:
            json_path: Path to JSON file with draft data

        Returns:
            Draft dictionary or None on error

        """
        try:
            if not json_path.exists():
                logger.error(f"Draft JSON file not found: {json_path}")
                return None

            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)

            recipients = data.get("recipients", [])
            if not recipients:
                logger.warning(f"No recipients in {json_path.name}")
                return None

            to = ", ".join(recipients) if isinstance(recipients, list) else recipients
            subject = data.get("subject", "Assunto não definido")
            body = data.get("body", "Corpo do email não definido.")
            attachments = [
                str(Path(attachment).expanduser())
                for attachment in data.get("attachments", [])
            ]

            draft = self.create_draft(
                to=to,
                subject=subject,
                body=body,
                attachments=attachments if attachments else None,
            )

            if draft:
                logger.info(f"Draft created from {json_path.name}")
            else:
                logger.warning(f"Failed to create draft from {json_path.name}")

            return draft

        except json.JSONDecodeError as e:
            logger.exception(f"Invalid JSON in {json_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating draft from JSON: {e}", exc_info=True)
            return None

    def find_draft_files_with_recipients(
        self,
        traces_dir: Path | None = None,
    ) -> list[Path]:
        """Find draft JSON files that have recipients information.

        Args:
            traces_dir: Optional directory to search.
                Defaults to project traces/

        Returns:
            List of Path objects to draft JSON files

        """
        if traces_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            traces_dir = project_root / "traces"

        if not traces_dir.exists():
            logger.warning(f"Traces directory not found: {traces_dir}")
            return []

        draft_files = []

        for json_file in traces_dir.glob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)

                if data.get("recipients"):
                    draft_files.append(json_file)

            except (OSError, json.JSONDecodeError):
                continue

        logger.info(f"Found {len(draft_files)} draft files with recipients")
        return draft_files

    def create_all_drafts_from_traces(
        self,
        traces_dir: Path | None = None,
    ) -> dict[str, Any]:
        """Create all drafts from trace files that have recipient information.

        Args:
            traces_dir: Optional directory to search

        Returns:
            Dictionary with creation statistics

        """
        draft_files = self.find_draft_files_with_recipients(traces_dir)

        if not draft_files:
            logger.info("No draft files with recipients found")
            return {
                "total": 0,
                "created": 0,
                "failed": 0,
                "success_rate": 0.0,
            }

        created_count = 0
        failed_count = 0

        for draft_file in draft_files:
            try:
                draft = self.create_draft_from_json(draft_file)
                if draft:
                    created_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.exception(f"Error processing {draft_file.name}: {e}")
                failed_count += 1

        total = len(draft_files)
        success_rate = (created_count / total * 100) if total > 0 else 0.0

        result = {
            "total": total,
            "created": created_count,
            "failed": failed_count,
            "success_rate": success_rate,
        }

        logger.info(
            f"Draft creation summary: {created_count}/{total} created "
            f"({success_rate:.1f}% success rate)",
        )

        return result
