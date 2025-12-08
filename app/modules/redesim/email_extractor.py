#!/usr/bin/env python3
"""Email Extractor for REDESIM Processes
Extracts email addresses from the ATF process detail pages.
"""

import re
from typing import Any


class EmailExtractor:
    """Extract email addresses from REDESIM process details."""

    # Regex pattern to match email addresses
    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", re.IGNORECASE,
    )

    def extract_emails_from_text(self, text: str) -> list[str]:
        """Extract all email addresses from a text string.

        Args:
            text: Text content to search for emails

        Returns:
            List of unique email addresses found

        """
        emails = self.EMAIL_PATTERN.findall(text)
        # Remove duplicates while preserving order
        return list(dict.fromkeys(emails))

    def extract_emails_from_process_details(
        self, process_details: str,
    ) -> dict[str, Any]:
        """Extract emails from a complete process details text.

        Expected sections:
        - Interessado (interested party)
        - Domicílio tributário (tax address)
        - Sócios/Administradores (partners/administrators)
        - Contabilista (accountant)

        Args:
            process_details: Complete text content of the process detail page

        Returns:
            Dictionary with extracted emails organized by category

        """
        all_emails = self.extract_emails_from_text(process_details)

        # Extract specific emails by section
        emails_data = {
            "all_emails": all_emails,
            "interessado_emails": [],
            "domicilio_emails": [],
            "socios_emails": [],
            "contabilista_emails": [],
        }

        # Find Interessado section
        interessado_match = re.search(
            r"Interessado:(.*?)(?=(?:Elem\.|Protocolo|$))",
            process_details,
            re.DOTALL | re.IGNORECASE,
        )
        if interessado_match:
            emails_data["interessado_emails"] = self.extract_emails_from_text(
                interessado_match.group(1),
            )

        # Find Domicílio section
        domicilio_match = re.search(
            r"Domicílio tributário.*?MAIL:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})",
            process_details,
            re.IGNORECASE,
        )
        if domicilio_match:
            emails_data["domicilio_emails"] = [domicilio_match.group(1)]

        # Find Sócios section
        socios_match = re.search(
            r"Identificação de sócio.*?(?=Identificação do contabilista|$)",
            process_details,
            re.DOTALL | re.IGNORECASE,
        )
        if socios_match:
            emails_data["socios_emails"] = self.extract_emails_from_text(
                socios_match.group(0),
            )

        # Find Contabilista section
        contabilista_match = re.search(
            r"Identificação do contabilista.*?(?=Mensagens|$)",
            process_details,
            re.DOTALL | re.IGNORECASE,
        )
        if contabilista_match:
            emails_data["contabilista_emails"] = self.extract_emails_from_text(
                contabilista_match.group(0),
            )

        return emails_data

    def clean_emails(self, emails: list[str]) -> list[str]:
        """Clean email addresses by removing duplicates and sorting.

        Args:
            emails: List of email addresses

        Returns:
            Cleaned and sorted list of unique emails

        """
        # Convert to lowercase first to ensure proper deduplication
        lowercase_emails = [email.lower() for email in emails]
        # Remove duplicates while preserving order
        unique_emails = list(dict.fromkeys(lowercase_emails))

        # Filter out system emails from SEFAZ
        system_patterns = ["sefaz.pb.gov.br", "cacgr1@sefaz.pb.gov.br"]

        unique_emails = [
            email
            for email in unique_emails
            if not any(pattern in email for pattern in system_patterns)
        ]

        # Sort alphabetically
        unique_emails.sort()
        return unique_emails
