"""PDF Download Module for NFA Automation
Handles downloading DAR and Nota Fiscal PDFs from SEFAZ PB system.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Optional

from app.modules.nfa.delays import (
    AFTER_PDF_CLICK_DELAY_MAX,
    AFTER_PDF_CLICK_DELAY_MIN,
    BETWEEN_PDF_DELAYS,
)
from app.modules.nfa.nfa_context import NFAContext, get_page_from_context

logger = logging.getLogger(__name__)


async def wait_for_download(
    page,
    download_path: Path,
    timeout: int = 30000,
) -> Optional[Path]:
    """Wait for a file download to complete.

    Args:
        page: Playwright Page instance
        download_path: Expected download path
        timeout: Timeout in milliseconds

    Returns:
        Path to downloaded file if successful, None otherwise

    """
    import asyncio

    start_time = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start_time) * 1000 < timeout:
        if download_path.exists() and download_path.stat().st_size > 0:
            logger.info(f"Download completed: {download_path}")
            return download_path
        await asyncio.sleep(0.5)

    logger.warning(f"Download timeout: {download_path}")
    return None


async def download_dar_pdf(
    ctx: NFAContext,
    output_dir: Path,
    cpf: str,
) -> Optional[Path]:
    """Download DAR (Documento de Arrecadação de Receitas) PDF.

    Args:
        ctx: Page or Frame context
        output_dir: Directory to save PDF
        cpf: CPF for file naming (cleaned, no formatting)

    Returns:
        Path to downloaded DAR PDF if successful, None otherwise

    """
    logger.info("Skipping DAR PDF download (disabled as per request)")
    return None


async def download_nota_fiscal_pdf(
    ctx: NFAContext,
    output_dir: Path,
    cpf: str,
) -> Optional[Path]:
    """Download Nota Fiscal PDF.

    Args:
        ctx: Page or Frame context
        output_dir: Directory to save PDF
        cpf: CPF for file naming (cleaned, no formatting)

    Returns:
        Path to downloaded Nota Fiscal PDF if successful, None otherwise

    """
    logger.info("Skipping Nota Fiscal PDF download (disabled as per request)")
    return None


async def download_all_pdfs(
    ctx: NFAContext,
    output_dir: Path,
    cpf: str,
) -> dict[str, Optional[Path]]:
    """Download both DAR and Nota Fiscal PDFs.

    Args:
        ctx: Page or Frame context
        output_dir: Directory to save PDFs
        cpf: CPF for file naming

    Returns:
        Dictionary with 'dar_pdf' and 'nota_pdf' keys containing file paths

    """
    page = get_page_from_context(ctx)
    results = {
        "dar_pdf": None,
        "nota_pdf": None,
    }

    # Download DAR first
    logger.info("Starting DAR PDF download...")
    dar_path = await download_dar_pdf(ctx, output_dir, cpf)
    results["dar_pdf"] = dar_path

    # Wait between downloads
    await page.wait_for_timeout(BETWEEN_PDF_DELAYS)

    # Download Nota Fiscal
    logger.info("Starting Nota Fiscal PDF download...")
    nota_path = await download_nota_fiscal_pdf(ctx, output_dir, cpf)
    results["nota_pdf"] = nota_path

    return results
