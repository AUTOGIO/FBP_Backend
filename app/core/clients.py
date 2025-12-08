"""HTTP clients and internal library abstractions for automation services."""

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging_config import setup_logger

logger = setup_logger(__name__)


class AutomationClient(ABC):
    """Abstract base class for automation clients."""

    @abstractmethod
    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute automation task.

        Args:
            payload: Task payload

        Returns:
            Task result

        """


class HTTPAutomationClient(AutomationClient):
    """HTTP client for external automation services."""

    def __init__(self, base_url: str, timeout: int = 300) -> None:
        """Initialize HTTP client.

        Args:
            base_url: Base URL of automation service
            timeout: Request timeout in seconds

        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout,
        )

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute automation via HTTP POST.

        Args:
            payload: Task payload

        Returns:
            Task result from service

        """
        try:
            response = await self.client.post("/execute", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error calling automation service: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in HTTP client: {e}")
            raise

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


class NFAHTTPClient(HTTPAutomationClient):
    """HTTP client specifically for NFA automation."""

    def __init__(self) -> None:
        base_url = settings.NFA_AUTOMATION_URL or "http://localhost:8001"
        super().__init__(base_url, timeout=600)  # 10 min timeout for NFA

    async def create_nfa(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create NFA via HTTP.

        Args:
            payload: NFA creation payload

        Returns:
            NFA creation result

        """
        try:
            response = await self.client.post("/nfa/create", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error creating NFA via HTTP: {e}")
            raise


class REDESIMHTTPClient(HTTPAutomationClient):
    """HTTP client specifically for REDESIM automation."""

    def __init__(self) -> None:
        base_url = settings.REDESIM_AUTOMATION_URL or "http://localhost:8002"
        super().__init__(base_url, timeout=300)  # 5 min timeout for REDESIM

    async def extract_emails(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract emails via HTTP.

        Args:
            payload: Email extraction payload

        Returns:
            Extraction result

        """
        try:
            response = await self.client.post("/redesim/extract", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error extracting emails via HTTP: {e}")
            raise


# Factory functions for getting clients
def get_nfa_client() -> AutomationClient:
    """Get NFA automation client based on configuration.

    Returns:
        Automation client instance

    """
    mode = settings.NFA_AUTOMATION_MODE or "http"

    if mode == "http":
        return NFAHTTPClient()
    if mode == "local":
        # TODO: Import and return local library client when available
        # from app.integrations.nfa_local import NFALocalClient
        # return NFALocalClient()
        msg = "Local NFA client not yet implemented"
        raise NotImplementedError(msg)
    msg = f"Unknown NFA automation mode: {mode}"
    raise ValueError(msg)


def get_redesim_client() -> AutomationClient:
    """Get REDESIM automation client based on configuration.

    Returns:
        Automation client instance

    """
    mode = settings.REDESIM_AUTOMATION_MODE or "http"

    if mode == "http":
        return REDESIMHTTPClient()
    if mode == "local":
        # TODO: Import and return local library client when available
        # from app.integrations.redesim_local import REDESIMLocalClient
        # return REDESIMLocalClient()
        msg = "Local REDESIM client not yet implemented"
        raise NotImplementedError(msg)
    msg = f"Unknown REDESIM automation mode: {mode}"
    raise ValueError(msg)
