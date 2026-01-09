from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Absolute paths per workspace rules
BASE_DIR = Path("/Users/dnigga/Documents/FBP_Backend")
DEFAULT_CREDENTIALS_PATH = BASE_DIR / "credentials" / "gmail_credentials.json"
DEFAULT_TOKEN_PATH = BASE_DIR / "credentials" / "gmail_token.json"
GMAIL_COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose"
SCOPES: list[str] = [GMAIL_COMPOSE_SCOPE]


def load_credentials(
    credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_TOKEN_PATH,
    scopes: Iterable[str] = SCOPES,
) -> Credentials:
    """
    Load user credentials, performing OAuth flow if needed.

    - Reuses cached token when valid
    - Refreshes expired tokens automatically
    - Runs local server OAuth for first-time login
    """
    if not credentials_path.is_file():
        raise FileNotFoundError(f"Credentials file not found at {credentials_path}")

    creds: Credentials | None = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Gmail token...")
            creds.refresh(Request())
        else:
            logger.info("Starting Gmail OAuth flow (compose scope only)...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path),
                scopes,
            )
            creds = flow.run_local_server(port=0, prompt="consent")

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())
        logger.info("Saved Gmail token to %s", token_path)

    return creds


def build_gmail_service(
    credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> object:
    """
    Construct an authenticated Gmail API client using compose scope only.
    """
    creds = load_credentials(credentials_path=credentials_path, token_path=token_path)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)
