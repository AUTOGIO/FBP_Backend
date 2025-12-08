"""ATF REDESIM Auto-Extractor
Extracts data automatically using multiple strategies from HTML content.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ATFAutoExtractor:
    """Automatic extractor for ATF REDESIM data."""

    def __init__(
        self,
        output_dir: str | None = None,
    ) -> None:
        """Initialize auto extractor.

        Args:
            output_dir: Optional output directory path

        """
        if output_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            output_dir = str(project_root / "traces" / "extension_files")

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Optimized regex patterns for real ATF HTML
        self.patterns = {
            "processo": re.compile(
                r"&nbsp;- Número do processo:.*?<b>(\d{10}-\d)</b>",
                re.IGNORECASE | re.DOTALL,
            ),
            "razao_social": re.compile(
                r"&nbsp;- Razão Social:.*?<td[^>]*>([^<]+)</td>",
                re.IGNORECASE | re.DOTALL,
            ),
            "email": re.compile(
                r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b",
                re.IGNORECASE,
            ),
        }

        # Contexts for categorization
        self.contexts = {
            "interessado": ["interessado", "jose eduardo", "contato"],
            "domicilio": ["domicílio", "tributário", "contribuinte"],
            "socios": ["sócio", "administrador", "maiza", "amadeu"],
            "contabilista": ["contabilista", "crc", "escritório"],
        }

    def extract_from_html(self, html_content: str) -> dict:
        """Extract data from HTML using multiple strategies.

        Args:
            html_content: HTML content string

        Returns:
            Dictionary with extracted data

        """
        logger.info("Starting automatic HTML extraction...")

        data = {
            "timestamp": datetime.now().isoformat(),
            "processo": None,
            "razao_social": None,
            "emails": {
                "interessado": [],
                "domicilio": [],
                "socios": [],
                "contabilista": [],
                "todos": [],
            },
            "url": "manual_html_extraction",
            "pageType": "processo_detail",
            "extracted_by": "python_auto_extractor",
        }

        # STRATEGY 1: Extraction via optimized regex
        processo_match = self.patterns["processo"].search(html_content)
        if processo_match:
            data["processo"] = processo_match.group(1)
            logger.info(f"Processo found: {data['processo']}")

        razao_match = self.patterns["razao_social"].search(html_content)
        if razao_match:
            data["razao_social"] = razao_match.group(1).strip()
            logger.info(f"Razão Social found: {data['razao_social']}")

        # STRATEGY 2: Contextual email extraction
        self._extract_emails_contextual(html_content, data)

        logger.info(
            f"Extraction completed: {len(data['emails']['todos'])} emails found",
        )
        return data

    def _extract_emails_contextual(
        self, html_content: str, data: dict,
    ) -> None:
        """Extract emails with contextual categorization."""
        html_lower = html_content.lower()
        all_emails = self.patterns["email"].findall(html_content)

        logger.debug(f"{len(all_emails)} emails found in HTML")

        for email in all_emails:
            email_lower = email.lower()

            # Find email context
            email_index = html_lower.find(email_lower)
            if email_index == -1:
                continue

            context_before = html_content[
                max(0, email_index - 300) : email_index
            ]
            context_after = html_content[
                email_index : min(len(html_content), email_index + 300)
            ]
            full_context = (context_before + context_after).lower()

            # Automatic categorization
            categorized = False

            for section, keywords in self.contexts.items():
                if not categorized and any(
                    keyword in full_context for keyword in keywords
                ):
                    data["emails"][section].append(email)
                    categorized = True
                    logger.debug(f"{email} → {section}")
                    break

            # If not categorized, put in interessado
            if not categorized:
                data["emails"]["interessado"].append(email)
                logger.debug(f"{email} → interessado (default)")

        # Remove duplicates
        for section in data["emails"]:
            if section != "todos":
                data["emails"][section] = list(set(data["emails"][section]))

        # Compile unique list
        all_unique = set()
        for section in ["interessado", "domicilio", "socios", "contabilista"]:
            all_unique.update(data["emails"][section])

        data["emails"]["todos"] = list(all_unique)

    def save_to_file(self, data: dict) -> str:
        """Save data to JSON file.

        Args:
            data: Extracted data dictionary

        Returns:
            Path to saved file

        """
        if not data["razao_social"]:
            filename = f"atf_extraction_{data['processo'] or 'unknown'}_{int(time.time())}.json"
        else:
            filename = f"{data['razao_social'].replace(' ', '_').replace('/', '_').upper()}.json"

        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"File saved: {filepath}")
        return str(filepath)

    def process_html_file(self, html_file: str) -> str:
        """Process HTML file and save result.

        Args:
            html_file: Path to HTML file

        Returns:
            Path to saved JSON file

        """
        with open(html_file, encoding="utf-8") as f:
            html_content = f.read()

        data = self.extract_from_html(html_content)
        return self.save_to_file(data)

    def process_html_string(self, html_content: str) -> str:
        """Process HTML string and save result.

        Args:
            html_content: HTML content string

        Returns:
            Path to saved JSON file

        """
        data = self.extract_from_html(html_content)
        return self.save_to_file(data)
