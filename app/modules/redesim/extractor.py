"""REDESIM Email Extractor - Main Execution Engine
Dual-mode execution engine supporting Cursor Browser Agent and Playwright CDP fallback.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from app.modules.redesim.browser_extractor import BrowserExtractor
from app.modules.utils.cep_validator import CEPValidator

logger = logging.getLogger(__name__)


class REDESIMExtractor:
    """Main execution engine for REDESIM email extraction.
    Supports dual-mode extraction: Cursor Browser Agent + Playwright CDP fallback.
    """

    def __init__(self, config_path: str | None = None) -> None:
        """Initialize REDESIM extractor.

        Args:
            config_path: Optional path to config YAML file

        """
        self.config = self._load_config(config_path)
        self.browser_extractor = BrowserExtractor()
        self.cep_validator = (
            CEPValidator()
            if self.config.get("cep_validation", {}).get("enabled", True)
            else None
        )

        # Setup paths from config
        project_root = Path(__file__).parent.parent.parent.parent
        self.traces_dir = Path(
            self.config.get("paths", {}).get(
                "traces",
                str(project_root / "traces"),
            ),
        )
        self.reports_dir = Path(
            self.config.get("paths", {}).get(
                "reports",
                str(project_root / "reports"),
            ),
        )

        # Ensure directories exist
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(
        self,
        config_path: str | None = None,
    ) -> dict[str, Any]:
        """Load configuration from YAML file."""
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "redesim.yaml"

        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, encoding="utf-8") as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(
                    f"Config file not found: {config_path}. Using defaults.",
                )
                return self._get_default_config()
        except Exception as e:
            logger.warning(f"Error loading config: {e}. Using defaults.")
            return self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Default configuration."""
        return {
            "runtime": {
                "use_cursor_browser": True,
            },
            "cep_validation": {
                "enabled": True,
            },
            "paths": {
                "traces": "traces",
                "reports": "reports",
            },
            "output": {
                "timestamp_format": "%Y%m%d_%H%M%S",
            },
        }

    async def extract_data(self) -> list[dict[str, Any]]:
        """Extract data using the selected extractor."""
        logger.info("Starting REDESIM data extraction...")

        try:
            # Use browser extractor (handles Cursor/Playwright fallback internally)
            results = await self.browser_extractor.extract_from_cursor()

            logger.info(
                f"Extraction completed: {len(results)} processes found",
            )
            return results

        except Exception as e:
            logger.exception(f"Error during extraction: {e}")
            raise

    def create_email_payload(
        self,
        process_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create email payload with subject and body.

        Args:
            process_data: Process data dictionary

        Returns:
            Email payload dictionary

        """
        processo = process_data.get("processo", "")
        razao_social = process_data.get("razao_social", "")

        # Subject contains ONLY Processo and Razão Social
        subject = f"Processo: {processo} - Razão Social: {razao_social}"

        # Body contains the official message from RECEITA ESTADUAL
        body = """Foi protocolado o processo supracitado de requerimento de inscrição estadual. Solicitamos que seja enviada a seguinte documentação:

ANEXOS (sem compactação):

FOTOS INTERNAS E EXTERNAS tiradas na DATA do ENVIO (em JPG, deve constar a numeração na fachada)
CONTRATO DE LOCAÇÃO com assinaturas reconhecidas (em PDF)
LISTA DO ATIVO IMOBILIZADO e ESTOQUE
Favor NÃO modificar o assunto do email para fácil identificação do processo e arquivo das informações.

Prazo de 3 dias corridos.



Atenciosamente,

RECEITA ESTADUAL."""

        return {
            "subject": subject,
            "body": body,
            "processo": processo,
            "razao_social": razao_social,
        }

    def save_draft_payload(self, payload: dict[str, Any], index: int) -> Path:
        """Save draft payload to JSON file named with Razão Social.

        Args:
            payload: Email payload dictionary
            index: Process index for deduplication

        Returns:
            Path to saved JSON file

        """
        razao_social = payload.get("razao_social", f"processo_{index}")

        # Create safe filename from razao_social
        safe_filename = re.sub(r"[^\w\s-]", "", razao_social)
        safe_filename = re.sub(r"[-\s]+", "_", safe_filename)
        safe_filename = safe_filename.strip("_")[:100]  # Limit length

        json_path = self.traces_dir / f"{safe_filename}.json"

        # If file exists, add index
        if json_path.exists():
            json_path = self.traces_dir / f"{safe_filename}_{index:03d}.json"

        # Save subject and body
        output = {"subject": payload["subject"], "body": payload["body"]}

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        return json_path

    def enrich_with_cep_data(
        self,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Enrich extracted data with CEP validation.

        Args:
            results: List of process data dictionaries

        Returns:
            Enriched results list

        """
        if not self.cep_validator:
            return results

        logger.info("Enriching data with CEP validation...")

        try:
            enriched_results = []

            for result in results:
                # Extract CEP from company data if available
                cep = result.get("cep") or result.get("endereco_cep")

                if cep:
                    # Validate and enrich CEP data
                    enriched_result = self.cep_validator.enrich_company_data(
                        result.copy(),
                    )
                    enriched_results.append(enriched_result)

                    # Log validation result
                    if enriched_result.get("cep_valid"):
                        logger.debug(f"CEP {cep} validated")
                    else:
                        logger.warning(
                            f"CEP {cep} invalid: {enriched_result.get('cep_error', 'Unknown error')}",
                        )
                else:
                    enriched_results.append(result)

            logger.info(
                f"Data enriched: {len(enriched_results)} records processed",
            )
            return enriched_results

        except Exception as e:
            logger.warning(f"Error in CEP validation: {e}")
            return results

    def enrich_with_ai(
        self,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Enrich data using n8n AI workflow for difficult cases.

        Args:
            results: List of process data dictionaries

        Returns:
            Enriched results list

        """
        n8n_cfg = self.config.get("n8n_integration", {})
        if not n8n_cfg.get("enabled", False):
            return results

        logger.info("Analyzing complex cases with AI (n8n)...")

        try:
            from app.modules.utils.n8n_integration import N8NIntegration

            n8n = N8NIntegration()

            enriched_results = []
            for result in results:
                # Check if we need AI help (e.g. no emails found but we have raw text)
                emails = result.get("emails", [])
                raw_text = result.get("raw_text", "")

                if not emails and raw_text:
                    logger.info(
                        f"Process {result.get('processo')} without emails. Consulting AI...",
                    )
                    ai_data = n8n.process_text_with_ai(raw_text)

                    if ai_data and "emails" in ai_data:
                        found_emails = ai_data["emails"]
                        if isinstance(found_emails, list):
                            result["emails"] = found_emails
                            logger.info(f"AI found {len(found_emails)} emails")
                            # Add AI metadata
                            result["ai_enriched"] = True
                            result["ai_data"] = ai_data

                enriched_results.append(result)

            return enriched_results

        except ImportError:
            logger.warning(
                "n8n_integration module not found. Skipping AI enrichment.",
            )
            return results
        except Exception as e:
            logger.exception(f"Error in AI enrichment: {e}")
            return results

    def save_report(
        self,
        report_rows: list[dict[str, Any]],
    ) -> Path:
        """Save extraction report to CSV file with CEP enrichment.

        Args:
            report_rows: List of report row dictionaries

        Returns:
            Path to saved CSV file

        """
        timestamp = datetime.now().strftime(
            self.config.get("output", {}).get(
                "timestamp_format",
                "%Y%m%d_%H%M%S",
            ),
        )
        csv_path = self.reports_dir / f"atf_redesim_{timestamp}.csv"

        if not report_rows:
            logger.warning("No data for report")
            return csv_path

        # Enhanced fieldnames with CEP data
        fieldnames = [
            "processo",
            "razao_social",
            "cep",
            "cep_valid",
            "endereco_completo",
            "codigo_ibge",
            "coordenadas",
            "timestamp",
        ]

        # Filter fieldnames to only include those present in data
        available_fields = set()
        for row in report_rows:
            available_fields.update(row.keys())

        final_fieldnames = [f for f in fieldnames if f in available_fields]

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=final_fieldnames)
            writer.writeheader()
            writer.writerows(report_rows)

        logger.info(f"Report saved: {csv_path}")
        return csv_path

    async def process_all(self) -> dict[str, Any]:
        """Main processing function: extract, enrich, and save results.

        Returns:
            Dictionary with processing results and statistics

        """
        logger.info("Starting REDESIM extraction process...")

        try:
            # Extract data
            results = await self.extract_data()

            if not results:
                logger.warning("No processes found.")
                return {
                    "success": False,
                    "message": "No processes found",
                    "results": [],
                    "report_path": None,
                }

            # Enrich data with CEP validation
            results = self.enrich_with_cep_data(results)

            # Enrich data with AI-based analysis for complex cases
            results = self.enrich_with_ai(results)

            # Process results and create payloads
            logger.info(f"Creating payloads for {len(results)} processes...")

            report_rows = []

            for i, process_data in enumerate(results):
                try:
                    # Create email payload
                    payload = self.create_email_payload(process_data)

                    # Save draft payload
                    self.save_draft_payload(payload, i)

                    # Add to report with CEP enrichment
                    report_row = {
                        "processo": process_data.get("processo", ""),
                        "razao_social": process_data.get("razao_social", ""),
                        "cep": process_data.get("cep", ""),
                        "cep_valid": process_data.get("cep_valid", False),
                        "endereco_completo": process_data.get(
                            "endereco_completo",
                            "",
                        ),
                        "codigo_ibge": process_data.get("codigo_ibge", ""),
                        "coordenadas": str(
                            process_data.get("coordenadas", ""),
                        ),
                        "timestamp": datetime.now().isoformat(),
                    }
                    report_rows.append(report_row)

                    logger.debug(
                        f"Processed {i + 1}/{len(results)}: {payload['processo']}",
                    )

                except Exception as e:
                    logger.exception(f"Error processing process {i + 1}: {e}")
                    report_rows.append(
                        {
                            "processo": process_data.get("processo", ""),
                            "razao_social": process_data.get(
                                "razao_social",
                                "",
                            ),
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

            # Save report
            report_path = self.save_report(report_rows)

            return {
                "success": True,
                "message": f"Processed {len(results)} processes",
                "results": results,
                "report_path": str(report_path),
                "report_rows": report_rows,
            }

        except Exception as e:
            logger.exception(f"Error during execution: {e}")
            raise
