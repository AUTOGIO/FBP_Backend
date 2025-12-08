"""Generic utility functions."""

from typing import Any


def sanitize_response(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize response data (remove None values, etc.).

    Args:
        data: Raw response data

    Returns:
        Sanitized dictionary

    """
    return {k: v for k, v in data.items() if v is not None}


def get_machine_info() -> str:
    """Get machine information.

    Returns:
        Machine identifier string

    """
    import platform

    machine = platform.machine()
    system = platform.system()

    if "arm" in machine.lower() or "aarch64" in machine.lower():
        if system == "Darwin":
            return "Apple Silicon (M3/M4)"

    return f"{system} {machine}"
