"""Developer Tools Extractor for REDESIM
Provides JavaScript console scripts for manual browser extraction.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DeveloperToolsExtractor:
    """Extractor using browser Developer Tools console scripts."""

    def __init__(
        self,
        output_dir: str | None = None,
    ) -> None:
        """Initialize Developer Tools extractor.

        Args:
            output_dir: Optional output directory path

        """
        if output_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            output_dir = str(project_root / "traces" / "extension_files")

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_console_script(self) -> str:
        """Get JavaScript script to execute in browser console.

        Returns:
            JavaScript code as string

        """
        return """
        // Script para extrair dados ATF via console
        (function() {
            console.log('🔍 ATF REDESIM: Iniciando extração via console...');

            const data = {
                timestamp: new Date().toISOString(),
                processo: null,
                razaoSocial: null,
                emails: {
                    interessado: [],
                    domicilio: [],
                    socios: [],
                    contabilista: [],
                    todos: []
                },
                url: window.location.href,
                pageType: 'processo_detail',
                extracted_by: 'developer_tools_console'
            };

            // Extrair processo e razão social
            const allTds = document.querySelectorAll('td');
            allTds.forEach(td => {
                const text = td.textContent || '';
                const nextTd = td.nextElementSibling;

                if (text.includes('Número do processo:')) {
                    data.processo = nextTd ? nextTd.textContent.trim() : null;
                }

                if (text.includes('Razão Social:')) {
                    data.razaoSocial = nextTd ? nextTd.textContent.trim() : null;
                }
            });

            // Extrair emails contextual
            const htmlContent = document.documentElement.outerHTML;
            const emailRegex = /\\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})\\b/gi;
            const allEmails = [...htmlContent.matchAll(emailRegex)].map(match => match[1]);

            allEmails.forEach(email => {
                const emailIndex = htmlContent.toLowerCase().indexOf(email.toLowerCase());
                const context = htmlContent.substring(
                    Math.max(0, emailIndex - 300),
                    Math.min(htmlContent.length, emailIndex + 300)
                ).toLowerCase();

                if (context.includes('interessado') || context.includes('jose eduardo')) {
                    data.emails.interessado.push(email);
                } else if (context.includes('domicílio') || context.includes('tributário')) {
                    data.emails.domicilio.push(email);
                } else if (context.includes('sócio') || context.includes('administrador')) {
                    data.emails.socios.push(email);
                } else if (context.includes('contabilista') || context.includes('crc')) {
                    data.emails.contabilista.push(email);
                } else {
                    data.emails.interessado.push(email);
                }
            });

            // Remover duplicatas
            Object.keys(data.emails).forEach(section => {
                if (section !== 'todos') {
                    data.emails[section] = [...new Set(data.emails[section])];
                }
            });

            // Compilar todos os emails
            data.emails.todos = [...new Set([
                ...data.emails.interessado,
                ...data.emails.domicilio,
                ...data.emails.socios,
                ...data.emails.contabilista
            ])];

            console.log('📊 Dados extraídos:', data);

            // Copiar para clipboard
            navigator.clipboard.writeText(JSON.stringify(data, null, 2)).then(() => {
                console.log('✅ Dados copiados para clipboard!');
                console.log('📋 Cole os dados em um arquivo JSON');
            });

            return data;
        })();
        """

    def process_json_data(self, json_data: str) -> dict:
        """Process JSON data extracted from browser console.

        Args:
            json_data: JSON string from browser console

        Returns:
            Parsed data dictionary

        """
        try:
            return json.loads(json_data)
        except json.JSONDecodeError as e:
            logger.exception(f"Error parsing JSON data: {e}")
            raise

    def save_extracted_data(self, data: dict) -> Path:
        """Save extracted data to JSON file.

        Args:
            data: Extracted data dictionary

        Returns:
            Path to saved file

        """
        try:
            razao_social = data.get(
                "razaoSocial", data.get("razao_social", "unknown"),
            )
            processo = data.get("processo", "unknown")

            # Create safe filename
            safe_name = (
                razao_social.replace(" ", "_").replace("/", "_").upper()[:100]
            )
            filename = f"{safe_name}_{processo}.json"
            filepath = self.output_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Extracted data saved to: {filepath}")
            return filepath

        except Exception as e:
            logger.exception(f"Error saving extracted data: {e}")
            raise
