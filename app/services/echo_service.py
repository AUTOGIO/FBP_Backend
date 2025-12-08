"""Echo service - simple echo functionality."""

from typing import Any


async def echo_message(message: str) -> dict[str, Any]:
    """Echo a message back.

    Args:
        message: Message to echo

    Returns:
        Dictionary with echoed message

    """
    return {"echo": message}
