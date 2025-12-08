"""Universal Delay System for NFA Automation
Centralized delay constants to avoid hardcoded waits throughout the codebase.
"""

from __future__ import annotations

# Default delays (in milliseconds)
DEFAULT_DELAY = 1500  # 1.5 seconds
FIELD_DELAY = 800  # 0.8 seconds
NETWORK_IDLE_TIMEOUT = 30000  # 30 seconds
CLICK_DELAY = 600  # 0.6 seconds
AFTER_SEARCH_DELAY = 2000  # 2.0 seconds

# Section delays
AFTER_CAMPOS_FIXOS_DELAY = 1000
AFTER_EMITENTE_DELAY = 1000
AFTER_DESTINATARIO_DELAY = 1000
AFTER_ENDERECO_DELAY = 1000
AFTER_PRODUTO_DELAY = 1000
AFTER_INFORMACOES_ADICIONAIS_DELAY = 500

# Form submission delays
AFTER_SUBMIT_DELAY = 1000
BEFORE_SUBMIT_DELAY = 500

# PDF download delays
BETWEEN_PDF_DELAYS = 1000
AFTER_PDF_CLICK_DELAY_MIN = 500
AFTER_PDF_CLICK_DELAY_MAX = 1000

# Page load delays
PAGE_LOAD_DELAY = 2000
COOKIE_BANNER_DELAY = 1000
LOADING_SCREEN_DELAY = 2000

# Retry delays
RETRY_BASE_DELAY = 2000  # Base delay in milliseconds (will be converted to seconds)

# Browser console logging
CONSOLE_LOG_ENABLED = True
