"""Logging configuration for FBP."""
from __future__ import annotations

import logging
import sys

from app.core.config import settings


def setup_logger(name: str | None = None) -> logging.Logger:
    """Configure and return a logger instance.

    Args:
        name: Logger name (defaults to 'fbp')

    Returns:
        Configured logger instance

    """
    logger = logging.getLogger(name or "fbp")

    if logger.handlers:
        return logger

    logger.setLevel(settings.LOG_LEVEL)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(settings.LOG_LEVEL)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger
