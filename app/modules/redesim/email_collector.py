#!/usr/bin/env python3
"""Email Collector Module for REDESIM
Collects and aggregates emails from REDESIM process details.

Note: This module contains core email collection logic.
For Outlook integration (CLASS B), see the original script.
"""

import re

# Email regex pattern
EMAIL_PATTERN = re.compile(
    r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b",
    re.IGNORECASE,
)


def extract_emails_from_html(html: str) -> list[str]:
    """Extract all unique emails from HTML content.
    Removes duplicates (case-insensitive).
    """
    emails = EMAIL_PATTERN.findall(html)

    # Remove duplicates (case-insensitive)
    unique_emails = []
    seen = set()

    for email in emails:
        email_lower = email.lower()
        if email_lower not in seen:
            seen.add(email_lower)
            unique_emails.append(email)

    return unique_emails


def extract_specific_emails(html: str) -> dict[str, list[str]]:
    """Extract emails from specific sections of the processo page.
    Returns a dict with categorized emails.
    """
    result: dict[str, list[str]] = {
        "interessado": [],
        "domicilio": [],
        "socios": [],
        "contabilista": [],
        "todos": [],
    }

    # Split HTML into sections
    sections = {
        "interessado": re.search(
            r"Interessado:.*?(?=Elem\.|$)",
            html,
            re.DOTALL | re.IGNORECASE,
        ),
        "domicilio": re.search(
            r"Domicílio tributário.*?(?=Identificação de sócio|$)",
            html,
            re.DOTALL | re.IGNORECASE,
        ),
        "socios": re.search(
            r"Identificação de sócio.*?(?=Identificação do contabilista|$)",
            html,
            re.DOTALL | re.IGNORECASE,
        ),
        "contabilista": re.search(
            r"Identificação do contabilista.*?$",
            html,
            re.DOTALL | re.IGNORECASE,
        ),
    }

    # Extract emails from each section
    for section_name, section_match in sections.items():
        if section_match:
            section_text = section_match.group(0)
            emails = EMAIL_PATTERN.findall(section_text)

            # Remove duplicates
            unique_emails = []
            seen = set()
            for email in emails:
                email_lower = email.lower()
                if email_lower not in seen:
                    seen.add(email_lower)
                    unique_emails.append(email)

            result[section_name] = unique_emails

    # Get all unique emails
    all_emails = []
    seen_all = set()
    for section_emails in result.values():
        if isinstance(section_emails, list):
            for email in section_emails:
                email_lower = email.lower()
                if email_lower not in seen_all:
                    seen_all.add(email_lower)
                    all_emails.append(email)

    result["todos"] = all_emails

    return result
