"""Configuration management for FBP."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class PathsConfig:
    """Path configuration helper."""

    def __init__(self, project_root: Optional[str | Path] = None) -> None:
        """Initialize paths configuration.

        Args:
            project_root: Optional project root path. If None, derived from config file location.
        """
        if project_root is None:
            # Derive project_root from this file's location
            # config.py is in app/core/, so go up 2 levels to get project root
            config_file = Path(__file__).resolve()
            self._project_root = config_file.parent.parent.parent
        else:
            self._project_root = Path(project_root).resolve()

    @property
    def project_root(self) -> Path:
        """Get project root directory."""
        return self._project_root

    @property
    def screenshots_dir(self) -> Path:
        """Get screenshots directory (relative to project_root)."""
        return self.project_root / "output" / "nfa" / "screenshots"


class Settings(BaseSettings):
    """Application settings."""

    # Project metadata
    PROJECT_NAME: str = "FBP"
    PROJECT_VERSION: str = "0.1.0"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # UNIX Socket settings (2025 Apple Silicon best practices)
    SOCKET_PATH: str = "/tmp/fbp.sock"
    USE_SOCKET: bool = True  # Use UNIX socket by default, fallback to PORT if False

    # Logging
    LOG_LEVEL: str = "INFO"

    # Machine info (can be overridden via env)
    MACHINE_INFO: str = "iMac M3 / MacBook Air M4"

    # Paths configuration
    PROJECT_ROOT: Optional[str] = None  # Optional override for project root
    SCREENSHOTS_DIR: Optional[str] = None  # Optional override for screenshots directory

    # NFA Automation settings
    NFA_AUTOMATION_MODE: str = "http"  # "http" or "local"
    NFA_AUTOMATION_URL: Optional[str] = None  # Required if mode is "http"

    # NFA Login Credentials (loaded from .env)
    NFA_USERNAME: str = ""  # SEFAZ PB username
    NFA_PASSWORD: str = ""  # SEFAZ PB password

    # REDESIM Automation settings
    REDESIM_AUTOMATION_MODE: str = "http"  # "http" or "local"
    REDESIM_AUTOMATION_URL: Optional[str] = None  # Required if mode is "http"

    # Gmail API settings
    GMAIL_CREDENTIALS_FILE: Optional[str] = None  # Path to credentials.json
    GMAIL_TOKEN_FILE: Optional[str] = None  # Path to token.json

    # Job backend settings
    JOB_BACKEND: str = "in_memory"  # "in_memory", "redis", "db"
    JOB_TIMEOUT_SECONDS: int = 3600  # Default job timeout (1 hour)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def log_level_int(self) -> int:
        """Convert log level string to logging constant."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        return level_map.get(self.LOG_LEVEL.upper(), logging.INFO)

    @property
    def paths(self) -> PathsConfig:
        """Get paths configuration."""
        return PathsConfig(project_root=self.PROJECT_ROOT)

    @property
    def socket_path(self) -> Path:
        """Get UNIX socket path as Path object."""
        return Path(self.SOCKET_PATH)


# Global settings instance
settings = Settings()
