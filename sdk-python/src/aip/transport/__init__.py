"""AIP transport layer — pluggable transport abstractions.

The default transport is HTTP+JSON (via httpx). Additional transports
(WebSocket, gRPC, NATS, etc.) can be implemented by subclassing BaseTransport.
"""

from aip.transport.base import BaseTransport
from aip.transport.http import HTTPTransport

__all__ = ["BaseTransport", "HTTPTransport"]
