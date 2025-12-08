from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

FORM_FILL_LOG = settings.paths.project_root / "logs" / "nfa" / "form_fill.log"


def log_form_fill(message: str) -> None:
    """Write form-fill events to dedicated log file and logger."""
    FORM_FILL_LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().isoformat()
    entry = f"{timestamp} {message}"
    try:
        with FORM_FILL_LOG.open("a", encoding="utf-8") as fp:
            fp.write(entry + "\n")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to write form_fill log: %s", exc)
    logger.info(message)
