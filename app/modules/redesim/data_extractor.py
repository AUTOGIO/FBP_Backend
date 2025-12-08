"""ATF REDESIM Data Extractor
Specialized extractor for "Processos REDESIM Encontrados" table structure.

Extracts ONLY:
- Processo (e.g., 2344402025-2)
- Razão Social (e.g., REINO DO SORVETE COMERCIO DE ALIMENTOS LTDA)
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.modules.redesim.browser_extractor import BrowserExtractor

logger = logging.getLogger(__name__)

# REDESIM-specific patterns
PROCESSO_PATTERN = re.compile(r"\b(2\d{9}-\d)\b")
CNPJ_PATTERN = re.compile(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b")


class REDESIMDataExtractor:
    """Extract processo and razão social from REDESIM table."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize REDESIM data extractor.

        Args:
            config: Optional configuration dictionary

        """
        self.config = config or {}
        self.browser_extractor = BrowserExtractor(config)

    @staticmethod
    def normalize_text(text: str | None) -> str:
        """Normalize text by removing extra whitespace."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def extract_processo_razao_from_row(
        row_text: str,
    ) -> dict[str, str] | None:
        """Extract Processo and Razão Social from a table row.

        Table structure:
        Processo | Protocolo | Insc. Est. | Sit. Cadastral | CPF/CNPJ | Razão Social | ...
        """
        # Find processo number
        processo_match = PROCESSO_PATTERN.search(row_text)
        if not processo_match:
            return None

        processo = processo_match.group(1)

        # Find CNPJ
        cnpj_match = CNPJ_PATTERN.search(row_text)
        if not cnpj_match:
            return None

        # Extract text after CNPJ to find Razão Social
        cnpj_pos = cnpj_match.end()
        remaining_text = row_text[cnpj_pos:]

        # Split by tab or multiple spaces (table cell separators)
        cells = re.split(r"\t+|\s{2,}", remaining_text.strip())

        # The first non-empty cell after CNPJ should be Razão Social
        razao_social = ""
        for cell in cells:
            cell = REDESIMDataExtractor.normalize_text(cell)
            # Check if this looks like a company name
            if cell and len(cell) > 3 and any(c.isalpha() for c in cell):
                # Stop at common field names that come after Razão Social
                if not re.match(
                    r"^(CADASTRAMENTO|ALTERAÇÃO|BAIXA|EVENTO|\d+)",
                    cell,
                    re.IGNORECASE,
                ):
                    razao_social = cell
                    break

        if not razao_social:
            return None

        return {
            "processo": processo,
            "razao_social": razao_social,
        }

    async def extract_from_cursor(self) -> list[dict[str, Any]]:
        """Extract process data from active Cursor browser tab.

        Returns:
            List of dictionaries containing processo and razao_social

        """
        logger.info("Extracting REDESIM data from Cursor browser tab...")

        try:
            # Get page content from Cursor browser
            html = await self.browser_extractor.get_raw_html()

            logger.info(f"Retrieved HTML content ({len(html)} characters)")

            # Extract results using REDESIM-specific logic
            results = await self._extract_redesim_table(html)

            logger.info(f"Extracted {len(results)} processes")
            return results

        except Exception as e:
            logger.exception(f"Error during extraction: {e}")
            raise

    async def _extract_redesim_table(
        self,
        html: str,
    ) -> list[dict[str, Any]]:
        """Extract processo and razão social from REDESIM table."""
        # Get row pattern from config
        row_pattern = self.config.get("browser", {}).get(
            "results_row_pattern",
            r"<tr[^>]*>.*?</tr>",
        )

        # Find all table rows
        rows = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)
        logger.info(f"Found {len(rows)} table rows")

        results = []

        for i, row in enumerate(rows, 1):
            # Remove HTML tags to get plain text
            row_text = re.sub(r"<[^>]+>", " ", row)

            # Extract processo and razão social
            data = self.extract_processo_razao_from_row(row_text)

            if data:
                results.append(
                    {
                        "processo": data["processo"],
                        "razao_social": data["razao_social"],
                        "row_index": i,
                    },
                )

                logger.debug(
                    f"{i} {data['processo']} - {data['razao_social'][:60]}...",
                )

        return results

    def save_results(
        self,
        results: list[dict[str, Any]],
        output_path: Path | None = None,
    ) -> Path:
        """Save extraction results to JSON file.

        Args:
            results: List of extracted process data
            output_path: Optional output file path

        Returns:
            Path to saved JSON file

        """
        if output_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            output_path = (
                project_root / "traces" / "redesim_extraction_results.json"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"Results saved to: {output_path}")
        return output_path
