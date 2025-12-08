"""Utilities Module.

Shared utilities: CEP validation, browser management, AI integration, etc.
"""

from app.modules.utils.cep_validator import CEPData, CEPValidator, validate_cep

__all__ = ["CEPData", "CEPValidator", "validate_cep"]
