"""HTTP+JSON transport — the default AIP transport."""

from __future__ import annotations

from typing import Any

import httpx


class HTTPTransport:
    """Default AIP transport using HTTP POST with JSON bodies.

    Thin wrapper around httpx; for production use with retries,
    use the higher-level aip.send / aip.async_send functions.
    """

    def __init__(self, timeout: float = 30.0, headers: dict[str, str] | None = None):
        self._timeout = timeout
        self._headers = headers or {}

    def send(self, url: str, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        headers = {**self._headers, **kwargs.get("headers", {})}
        with httpx.Client(timeout=self._timeout) as client:
            r = client.post(url, json=body, headers=headers or None)
            r.raise_for_status()
            return r.json()

    async def async_send(self, url: str, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        headers = {**self._headers, **kwargs.get("headers", {})}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(url, json=body, headers=headers or None)
            r.raise_for_status()
            return r.json()
