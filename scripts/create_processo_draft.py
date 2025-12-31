#!/usr/bin/env python3
"""Create Gmail draft from REDESIM processo data."""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

# Ensure project root is on sys.path for direct execution
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.modules.redesim.email_extractor import EmailExtractor  # noqa: E402
from app.modules.redesim.gmail_draft_creator import create_gmail_draft  # noqa: E402

logger = logging.getLogger(__name__)


def extract_processo_number(processo_text: str) -> str | None:
    """Extract processo number from text."""
    match = re.search(r" - Número do processo:\s+(\d+-\d+)", processo_text)
    return match.group(1) if match else None


def extract_razao_social(processo_text: str) -> str | None:
    """Extract Razão Social from text."""
    match = re.search(r" - Razão Social:\s+(.+?)(?:\n|$)", processo_text)
    return match.group(1).strip() if match else None


def generate_subject(processo_text: str) -> str:
    """Auto-generate subject line from processo data."""
    numero = extract_processo_number(processo_text)
    razao = extract_razao_social(processo_text)
    if numero and razao:
        return f"Número do processo: {numero} - Razão Social: {razao}"
    return "Processo REDESIM - Documentação Pendente"  # fallback


def extract_emails_from_processo(processo_text: str) -> list[str]:
    """Extract and clean emails from processo data."""
    extractor = EmailExtractor()
    emails_data = extractor.extract_emails_from_process_details(processo_text)
    all_emails = emails_data["all_emails"]
    cleaned = extractor.clean_emails(all_emails)
    return cleaned


def create_processo_draft(
    processo_text: str,
    body: str,
    subject: str | None = None,  # Auto-generate if None
) -> str | None:
    """Create Gmail draft from processo data.

    Args:
        processo_text: Full processo data text
        body: Draft body text
        subject: Draft subject line (auto-generated if None)

    Returns:
        Draft ID if successful, None otherwise
    """
    # Auto-generate subject if not provided
    if subject is None:
        subject = generate_subject(processo_text)
        logger.info(f"Auto-generated subject: {subject}")

    emails = extract_emails_from_processo(processo_text)

    if not emails:
        logger.warning("No emails found in processo data")
        return None

    logger.info(f"Found {len(emails)} recipient(s): {', '.join(emails)}")

    draft_id = create_gmail_draft(
        to=emails,
        subject=subject,
        body=body,
    )

    return draft_id


def main() -> None:
    """Main entry point.

    Supports multiple input methods:
    - Command-line argument: python create_processo_draft.py "processo text"
    - File path: python create_processo_draft.py /path/to/file.txt
    - stdin: echo "processo text" | python create_processo_draft.py
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    # Read processo text from stdin, command-line argument, or file
    processo_text: str | None = None

    if len(sys.argv) > 1:
        # Command-line argument provided
        arg = sys.argv[1]

        # Check if it's likely text (contains newlines) or a reasonable file path
        is_likely_text = "\n" in arg or len(arg) > 255

        if not is_likely_text:
            # Try to check if it's a file path
            try:
                path = Path(arg)
                if path.exists() and path.is_file():
                    # It's a file path
                    processo_text = path.read_text(encoding="utf-8")
                    logger.info(f"Reading processo data from file: {arg}")
                else:
                    # Not a file, treat as text
                    processo_text = arg
                    logger.info("Reading processo data from command-line argument")
            except (OSError, ValueError):
                # Path too long or invalid, treat as text
                processo_text = arg
                logger.info("Reading processo data from command-line argument")
        else:
            # Contains newlines or too long, definitely text
            processo_text = arg
            logger.info("Reading processo data from command-line argument")
    else:
        # Read from stdin
        logger.info("Reading processo data from stdin (press Ctrl+D when done)")
        processo_text = sys.stdin.read()

    if not processo_text or not processo_text.strip():
        logger.error("No processo data provided")
        print("Usage:")
        print("  python create_processo_draft.py 'processo text'")
        print("  python create_processo_draft.py /path/to/file.txt")
        print("  echo 'processo text' | python create_processo_draft.py")
        sys.exit(1)

    # Auto-generate subject from processo data
    subject = generate_subject(processo_text)
    logger.info(f"Auto-generated subject: {subject}")

    # Extract emails for display
    emails = extract_emails_from_processo(processo_text)

    body = """O processo de cadastramento estadual encontra-se em fase de análise final. Para conclusão do parecer fiscal, solicitamos o envio digital (sem compactação) dos documentos abaixo em até 3 (três) dias corridos:

• Fotos internas e externas atualizadas do estabelecimento (fachada com numeração visível)

• Contrato de locação ou documento de posse do imóvel

• Relação do ativo imobilizado (veículos, máquinas e equipamentos) vinculados à unidade da Paraíba

• Comprovante de endereço atualizado e registro/contrato empresarial completo

Solicitamos que o retorno seja feito respondendo a este e-mail, mantendo o assunto original, com os documentos anexados e, se possível, esclarecimentos adicionais sobre a operação (estrutura local, principais atividades exercidas nesta unidade e fluxo de mercadorias).

Atenciosamente,"""

    draft_id = create_processo_draft(
        processo_text=processo_text,
        body=body,
        # subject=None will trigger auto-generation
    )

    if draft_id:
        print(f"\n✓ Draft created successfully!")
        print(f"  Draft ID: {draft_id}")
        print(f"  Subject: {subject}")
        print(f"  Recipients ({len(emails)}): {', '.join(emails)}")
    else:
        print("✗ Failed to create Gmail draft.")
        sys.exit(1)


if __name__ == "__main__":
    main()
