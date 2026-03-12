"""Abstract base transport for AIP message delivery."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTransport(ABC):
    """Base class for AIP transports.

    Implement this to add support for WebSocket, gRPC, NATS, Kafka, or any
    other transport. The contract is simple: deliver a JSON-serializable dict
    and return the parsed response.
    """

    @abstractmethod
    def send(self, url: str, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Send a message synchronously and return the response."""
        ...

    @abstractmethod
    async def async_send(self, url: str, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Send a message asynchronously and return the response."""
        ...

    def close(self) -> None:
        """Clean up resources. Override if the transport holds connections."""

    async def async_close(self) -> None:
        """Async cleanup. Override if the transport holds async connections."""
