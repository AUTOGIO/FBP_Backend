#!/usr/bin/env python3
"""Safe test entrypoint for creating a Gmail draft (compose scope only)."""

from __future__ import annotations

import argparse
import logging
from typing import Sequence

from app.modules.redesim.gmail_draft_creator import create_gmail_draft


def _parse_recipients(raw: str) -> list[str]:
    """Split comma-separated recipients into a clean list."""
    return [recipient.strip() for recipient in raw.split(",") if recipient.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a single Gmail draft using the compose-only scope. "
            "This script never sends email."
        ),
    )
    parser.add_argument(
        "--to",
        required=True,
        help="Comma-separated recipient list (required).",
    )
    parser.add_argument(
        "--subject",
        default="REDESIM Gmail draft test",
        help="Draft subject (default: 'REDESIM Gmail draft test').",
    )
    parser.add_argument(
        "--body",
        default="Safe test draft created by REDESIM pipeline.",
        help="Draft body text.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    recipients: Sequence[str] = _parse_recipients(args.to)
    draft_id = create_gmail_draft(
        to=recipients,
        subject=args.subject,
        body=args.body,
    )

    if draft_id:
        print(f"Draft created successfully. ID: {draft_id}")
    else:
        print("Failed to create Gmail draft.")


if __name__ == "__main__":
    main()
