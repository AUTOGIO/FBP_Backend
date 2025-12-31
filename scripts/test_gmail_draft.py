"""Safe entrypoint to generate a Gmail draft (compose scope only)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# Ensure project root is on PYTHONPATH for absolute imports
ROOT_DIR = Path("/Users/dnigga/Documents/FBP_Backend")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.integrations.gmail.gmail_auth import (  # noqa: E402
    DEFAULT_CREDENTIALS_PATH,
    DEFAULT_TOKEN_PATH,
)
from app.integrations.gmail.gmail_draft import create_gmail_draft  # noqa: E402

LOG_FORMAT = "[%(levelname)s] %(message)s"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Gmail draft (never sends). Prompts if --to missing.",
    )
    parser.add_argument("--to", help="Recipient email address for the draft")
    parser.add_argument(
        "--subject",
        default="FBP Draft Validation",
        help="Draft subject (default: %(default)s)",
    )
    parser.add_argument(
        "--body",
        default="This is a validation draft created by scripts/test_gmail_draft.py.",
        help="Draft body (plain text)",
    )
    parser.add_argument(
        "--from-email",
        default=None,
        help="Optional From header (defaults to Gmail account owner)",
    )
    return parser.parse_args()


def resolve_recipient(to_arg: Optional[str]) -> str:
    """Ensure a recipient is provided without hardcoding emails."""
    if to_arg:
        return to_arg.strip()

    entered = input("Enter recipient email (draft only, will NOT send): ").strip()
    if not entered:
        raise ValueError("Recipient email is required to build the draft.")
    return entered


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    args = parse_args()

    logging.info("Using credentials: %s", DEFAULT_CREDENTIALS_PATH)
    logging.info("Token will be stored at: %s", DEFAULT_TOKEN_PATH)

    try:
        recipient = resolve_recipient(args.to)
        draft_id = create_gmail_draft(
            to=recipient,
            subject=args.subject,
            body=args.body,
            from_email=args.from_email,
        )
    except FileNotFoundError as exc:
        logging.error("Missing credentials file: %s", exc)
        sys.exit(2)
    except Exception as exc:  # noqa: BLE001
        logging.exception("Unexpected error creating draft: %s", exc)
        sys.exit(3)

    if draft_id:
        logging.info("Draft created successfully with id: %s", draft_id)
        sys.exit(0)

    logging.error("Failed to create Gmail draft (no draft_id returned)")
    sys.exit(1)


if __name__ == "__main__":
    main()
