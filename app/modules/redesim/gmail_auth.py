"""Gmail OAuth helper for creating drafts only (compose scope)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Sequence

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from app.core.config import settings

logger = logging.getLogger(__name__)

# Exclusive compose scope as requested (no broader permissions)
SCOPES: list[str] = ["https://www.googleapis.com/auth/gmail.compose"]

# Default credential locations (project-scoped)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CREDENTIALS_PATH = PROJECT_ROOT / "credentials" / "gmail_credentials.json"
DEFAULT_TOKEN_PATH = PROJECT_ROOT / "credentials" / "gmail_token.json"


def _ensure_parent_dir(path: Path) -> None:
    """Create parent directory if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)


def _resolve_paths(
    credentials_path: Optional[str | Path],
    token_path: Optional[str | Path],
) -> tuple[Path, Path]:
    """Resolve credentials and token paths using settings/env defaults."""
    resolved_credentials = Path(
        credentials_path or settings.GMAIL_CREDENTIALS_FILE or DEFAULT_CREDENTIALS_PATH,
    ).expanduser()
    resolved_token = Path(
        token_path or settings.GMAIL_TOKEN_FILE or DEFAULT_TOKEN_PATH,
    ).expanduser()
    return resolved_credentials, resolved_token


def _validated_scopes(scopes: Sequence[str] | None) -> list[str]:
    """Validate that only the compose scope is requested."""
    effective_scopes = list(scopes or SCOPES)
    if set(effective_scopes) != set(SCOPES):
        raise ValueError(
            "Only the gmail.compose scope is allowed for REDESIM Gmail usage.",
        )
    return effective_scopes


def get_gmail_credentials(
    credentials_path: Optional[str | Path] = None,
    token_path: Optional[str | Path] = None,
    scopes: Optional[Sequence[str]] = None,
) -> Credentials:
    """Return valid Gmail credentials, refreshing or running OAuth as needed.

    Args:
        credentials_path: Optional path to the Google OAuth client JSON.
        token_path: Optional path to persist the OAuth token.
        scopes: Optional scopes override (defaults to compose-only scope).

    Returns:
        google.oauth2.credentials.Credentials

    Raises:
        FileNotFoundError: If the credentials file does not exist.
        Exception: Any OAuth or refresh-related error is raised after logging.
    """
    scopes = _validated_scopes(scopes)
    creds: Credentials | None = None

    resolved_credentials, resolved_token = _resolve_paths(
        credentials_path=credentials_path,
        token_path=token_path,
    )

    if not resolved_credentials.exists():
        message = (
            "Gmail credentials file not found. " f"Expected at: {resolved_credentials}"
        )
        logger.error(message)
        raise FileNotFoundError(message)

    try:
        if resolved_token.exists():
            creds = Credentials.from_authorized_user_file(
                str(resolved_token),
                scopes,
            )
            logger.debug("Loaded Gmail token from %s", resolved_token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing Gmail OAuth token...")
                    creds.refresh(Request())
                    logger.info("Gmail OAuth token refreshed successfully")
                except RefreshError as exc:
                    logger.error(
                        "Failed to refresh Gmail OAuth token: %s",
                        exc,
                        exc_info=True,
                    )
                    creds = None
            if not creds or not creds.valid:
                logger.info(
                    "Starting Gmail OAuth flow (InstalledAppFlow desktop)...",
                )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(resolved_credentials),
                    scopes,
                )
                creds = flow.run_local_server(port=0)
                logger.info("Gmail OAuth flow completed")

            _ensure_parent_dir(resolved_token)
            assert creds is not None
            resolved_token.write_text(creds.to_json(), encoding="utf-8")
            logger.info("Saved Gmail token to %s", resolved_token)

        assert creds is not None
        return creds

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "OAuth error while obtaining Gmail credentials: %s",
            exc,
            exc_info=True,
        )
        raise
