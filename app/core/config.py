"""Configuration management for FBP.

Optimized for: iMac M3 (Mac15,5) | 8 cores (4P+4E) | 16GB RAM | macOS 26.0 Tahoe
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


# ═══════════════════════════════════════════════════════════════════════════════
# HARDWARE PROFILE: iMac M3 (Mac15,5)
# ═══════════════════════════════════════════════════════════════════════════════
HARDWARE_PROFILE = {
    "model": "iMac (Mac15,5)",
    "chip": "Apple M3",
    "cpu_cores": 8,
    "performance_cores": 4,
    "efficiency_cores": 4,
    "gpu_cores": 10,
    "neural_engine_cores": 16,
    "neural_engine_tops": 18,  # 18 TOPS
    "memory_gb": 16,
    "os": "macOS 26.0 Tahoe (Beta)",
}

# M3-optimized concurrency limits (based on 16GB unified memory)
M3_LIMITS = {
    "max_concurrent_browsers": 3,  # ~1.5GB per Playwright instance
    "max_concurrent_jobs": 4,      # Leave headroom for system
    "browser_memory_mb": 1536,     # Expected memory per browser
    "safe_memory_threshold": 0.80, # Don't exceed 80% memory usage
    "batch_size_default": 10,      # Optimal batch size for M3
}


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
    """Application settings optimized for iMac M3."""

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

    # Machine info - iMac M3 (Mac15,5)
    MACHINE_INFO: str = "iMac M3 (Mac15,5) | 8 cores | 16GB | macOS 26.0"

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

    # Cloudflare Zero Trust tunnel settings
    EXTERNAL_URL: str = "https://fbp.giovannini.us"  # External access URL
    ALLOWED_ORIGINS: str = "http://localhost,http://127.0.0.1,https://foks.giovannini.us,https://fbp.giovannini.us,https://giovannini.us"

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
