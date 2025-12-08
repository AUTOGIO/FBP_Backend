"""Modern structured logging configuration for FBP.
Replaces app/core/logger.py with structured logging support.
"""
from __future__ import annotations

import logging
import sys

from app.core.config import settings


class StructuredFormatter(logging.Formatter):
    """Structured formatter for JSON-compatible logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Format as JSON-like string (can be changed to actual JSON)
        return (
            f"{log_data['timestamp']} | {log_data['level']:8s} | "
            f"{log_data['logger']:30s} | {log_data['message']}"
        )


def setup_logger(name: str | None = None) -> logging.Logger:
    """Configure and return a logger instance with structured logging.

    Args:
        name: Logger name (defaults to 'fbp')

    Returns:
        Configured logger instance

    """
    logger = logging.getLogger(name or "fbp")

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(settings.log_level_int)

    # Console handler with structured formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(settings.log_level_int)

    # Use structured formatter in DEBUG mode, simple formatter otherwise
    if settings.DEBUG:
        formatter = StructuredFormatter(
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Get or create a logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance

    """
    return setup_logger(name)
