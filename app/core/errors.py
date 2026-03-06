from __future__ import annotations


class AppError(Exception):
    """Base application error."""


class ValidationError(AppError):
    """Invalid user-provided request payload."""


class NotFoundError(AppError):
    """Requested resource was not found."""
