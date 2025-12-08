"""Custom exceptions for FBP."""

from __future__ import annotations

from typing import Any


class FBPException(Exception):
    """Base exception for FBP."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ServiceException(FBPException):
    """Exception raised by service layer."""


class ValidationException(FBPException):
    """Exception raised for validation errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, status_code=400, details=details)


class JobNotFoundException(FBPException):
    """Exception raised when job is not found."""

    def __init__(self, job_id: str) -> None:
        super().__init__(
            f"Job {job_id} not found",
            status_code=404,
            details={"job_id": job_id},
        )


class JobConflictException(FBPException):
    """Exception raised for conflicting job states."""

    def __init__(self, message: str, job_id: str, current_status: str) -> None:
        super().__init__(
            message,
            status_code=409,
            details={"job_id": job_id, "current_status": current_status},
        )


class AutomationException(FBPException):
    """Exception raised by automation services."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, status_code=500, details=details)


class AutomationFatalException(AutomationException):
    """Non-recoverable automation failure (even after fallbacks)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details=details)
