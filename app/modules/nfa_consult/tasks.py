"""NFA Consult Automation Tasks.

Main automation execution for NFA consultation and PDF download.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import BrowserContext, async_playwright

from app.core.config import settings
from app.core.logging_config import setup_logger
from app.modules.nfa_consult.atf_consult import (
    _download_danfe,
    _download_dar,
    _fill_consulta_form,
    _get_main_frame,
    _login_atf,
    _navigate_to_fis308,
    _select_nfa_from_table,
)

logger = setup_logger(__name__)

LOG_FILE = Path("/Users/dnigga/Downloads/NFA_Outputs/nfa_consult_runs.jsonl")


async def run_nfa_consult_automation(
    username: Optional[str] = None,
    password: Optional[str] = None,
    data_inicial: str = "08/12/2025",
    data_final: str = "10/12/2025",
    matricula: str = "1595504",
    headless: bool = True,
) -> dict[str, Any]:
    """Run complete NFA consultation automation.

    This function executes the entire automation flow:
    1. Login to ATF
    2. Navigate to FIS_308
    3. Fill consultation form
    4. Select NFA from results
    5. Download DANFE and DAR PDFs

    Args:
        username: ATF username (uses NFA_USERNAME env var if not provided)
        password: ATF password (uses NFA_PASSWORD env var if not provided)
        data_inicial: Initial date in DD/MM/YYYY format
        data_final: Final date in DD/MM/YYYY format
        matricula: Employee registration number
        headless: Whether to run browser in headless mode

    Returns:
        Dictionary with automation results:
        - status: "ok" or "error"
        - nfa_numero: NFA number found
        - danfe_path: Path to DANFE PDF
        - dar_path: Path to DAR PDF
        - started_at: Start timestamp
        - finished_at: Finish timestamp
        - error: Error message (if failed)

    """
    # Resolve credentials
    user = username or settings.NFA_USERNAME
    pwd = password or settings.NFA_PASSWORD

    if not user or not pwd:
        error_msg = (
            "NFA credentials not provided. "
            "Set NFA_USERNAME and NFA_PASSWORD env vars or pass explicitly."
        )
        logger.error(error_msg)
        return {
            "status": "error",
            "nfa_numero": None,
            "danfe_path": None,
            "dar_path": None,
            "started_at": datetime.utcnow().isoformat(),
            "finished_at": datetime.utcnow().isoformat(),
            "error": error_msg,
        }

    result: dict[str, Any] = {
        "status": "error",
        "nfa_numero": None,
        "danfe_path": None,
        "dar_path": None,
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": None,
        "error": None,
    }

    async with async_playwright() as p:
        browser = None
        context = None

        try:
            logger.info("Starting NFA consultation automation")
            logger.info(f"Date range: {data_inicial} to {data_final}")
            logger.info(f"Matrícula: {matricula}")

            # Launch browser
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()

            # Step 1: Login
            logger.info("Step 1: Logging in to ATF")
            login_success = await _login_atf(page, user, pwd)
            if not login_success:
                raise RuntimeError("Login failed")

            # Step 2: Navigate to FIS_308
            logger.info("Step 2: Navigating to FIS_308")
            nav_success = await _navigate_to_fis308(page)
            if not nav_success:
                raise RuntimeError("Failed to navigate to FIS_308")

            # Step 3: Get main frame
            logger.info("Step 3: Resolving main content frame")
            frame = await _get_main_frame(page)
            await asyncio.sleep(2)  # Wait for frame to stabilize

            # Step 4: Fill consultation form
            logger.info("Step 4: Filling consultation form")
            form_success = await _fill_consulta_form(
                frame,
                data_inicial,
                data_final,
                matricula,
            )
            if not form_success:
                raise RuntimeError("Failed to fill consultation form")

            # Step 5: Wait for results and select NFA
            logger.info("Step 5: Waiting for results and selecting NFA")
            await asyncio.sleep(3)  # Wait for results to load
            nfa_numero = await _select_nfa_from_table(frame)

            if not nfa_numero:
                raise RuntimeError("No NFA found for the specified filters")

            result["nfa_numero"] = nfa_numero
            logger.info(f"Selected NFA: {nfa_numero}")

            # Step 6: Download DANFE
            logger.info("Step 6: Downloading DANFE")
            danfe_path = await _download_danfe(context, frame, nfa_numero)
            if danfe_path:
                result["danfe_path"] = str(danfe_path)
            else:
                logger.warning("DANFE download failed")

            # Step 7: Download DAR
            logger.info("Step 7: Downloading DAR")
            await asyncio.sleep(2)  # Wait between downloads
            dar_path = await _download_dar(context, frame, nfa_numero)
            if dar_path:
                result["dar_path"] = str(dar_path)
            else:
                logger.warning("DAR download failed")

            # Success
            result["status"] = "ok"
            logger.info("NFA consultation automation completed successfully")

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"NFA consultation automation failed: {error_msg}")
            result["error"] = error_msg

        finally:
            result["finished_at"] = datetime.utcnow().isoformat()

            # Close browser
            if context:
                await context.close()
            if browser:
                await browser.close()

            # Log to JSONL file
            try:
                LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
                with LOG_FILE.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
            except Exception as log_error:
                logger.warning(f"Failed to write log file: {log_error}")

    return result
