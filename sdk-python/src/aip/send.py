"""AIP send layer — reliable message delivery with retry, backoff, and timeouts.

Public API:
    send, async_send          — single message (JSON response)
    send_batch, async_send_batch  — parallel delivery
    send_stream, async_send_stream — SSE streaming response

Logging:
    Set AIP_LOG=1 for INFO-level protocol logs.
    Pass logger= to fuse with your application logger.
    Pass log_extra= to add trace_id, agent_id, etc. to every log record.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from collections.abc import AsyncGenerator, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aip.message import AIPMessage

_default_logger = logging.getLogger("aip.send")

if os.getenv("AIP_LOG", "").strip().lower() in ("1", "true", "yes"):
    _default_logger.setLevel(logging.INFO)

DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 4
DEFAULT_BACKOFF_BASE = 1.0
DEFAULT_BACKOFF_MAX = 60.0
DEFAULT_BACKOFF_JITTER = 0.2
DEFAULT_API_VERSION = "v1"


def _log_suffix(extra: dict[str, Any]) -> str:
    parts = [f"{k}={v}" for k, v in extra.items() if v not in (None, "", {}, [])]
    return (" " + " ".join(parts)) if parts else ""


@dataclass
class SendParams:
    """Delivery parameters — override for your deployment."""

    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_base: float = DEFAULT_BACKOFF_BASE
    backoff_max: float = DEFAULT_BACKOFF_MAX
    backoff_jitter: float = DEFAULT_BACKOFF_JITTER
    idempotency_key: str | None = None
    api_version: str = DEFAULT_API_VERSION

    def backoff_delay(self, attempt: int) -> float:
        """Exponential backoff with cap and jitter."""
        delay = min(self.backoff_max, self.backoff_base * (2**attempt))
        jitter = delay * self.backoff_jitter * (2 * random.random() - 1)
        return max(0.0, delay + jitter)


@dataclass
class SSEEvent:
    """A single Server-Sent Event from an AIP streaming response."""

    event: str
    data: dict[str, Any]


# ── SSE parsing ──────────────────────────────────────────────────────


def _parse_sse_lines(lines) -> Generator[SSEEvent, None, None]:
    """Parse an iterable of SSE text lines into SSEEvent objects."""
    event_type = "message"
    data_parts: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip("\r\n") if isinstance(raw_line, str) else raw_line
        if not line:
            if data_parts:
                yield _build_sse_event(event_type, "\n".join(data_parts))
            event_type = "message"
            data_parts = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_parts.append(line[5:].strip())
    if data_parts:
        yield _build_sse_event(event_type, "\n".join(data_parts))


async def _parse_sse_lines_async(lines) -> AsyncGenerator[SSEEvent, None]:
    """Async version of SSE line parser."""
    event_type = "message"
    data_parts: list[str] = []
    async for raw_line in lines:
        line = raw_line.rstrip("\r\n") if isinstance(raw_line, str) else raw_line
        if not line:
            if data_parts:
                yield _build_sse_event(event_type, "\n".join(data_parts))
            event_type = "message"
            data_parts = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data_parts.append(line[5:].strip())
    if data_parts:
        yield _build_sse_event(event_type, "\n".join(data_parts))


def _build_sse_event(event_type: str, data_str: str) -> SSEEvent:
    try:
        data = json.loads(data_str)
    except (json.JSONDecodeError, ValueError):
        data = {"raw": data_str}
    return SSEEvent(event=event_type, data=data)


# ── Send (JSON) ──────────────────────────────────────────────────────


def send(
    base_url: str,
    message: AIPMessage | dict[str, Any],
    params: SendParams | None = None,
    *,
    log_extra: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Send an AIP message (sync). Retries on 5xx, timeout, and connection errors.

    Returns the parsed JSON ack; raises on final failure.
    """
    import httpx

    body = message.to_wire() if hasattr(message, "to_wire") else message
    p = params or SendParams()
    log = logger or _default_logger
    url = f"{base_url.rstrip('/')}/{p.api_version}/aip"
    extra = {"message_id": body.get("message_id", ""), **(log_extra or {})}

    sfx = _log_suffix(extra)
    if log.isEnabledFor(logging.INFO):
        log.info("aip.send start url=%s action=%s%s", url, body.get("action", ""), sfx)

    t0 = time.perf_counter()
    last_exc: Exception | None = None
    last_status: int | None = None

    headers: dict[str, str] = {"Accept": "application/json"}
    if p.idempotency_key:
        headers["Idempotency-Key"] = p.idempotency_key

    _retryable = (
        httpx.ConnectError, httpx.TimeoutException,
        httpx.RemoteProtocolError, OSError,
    )
    with httpx.Client(timeout=p.timeout) as client:
        for attempt in range(p.max_retries):
            try:
                r = client.post(url, json=body, headers=headers)
                last_status = r.status_code
                if r.is_success:
                    ms = round((time.perf_counter() - t0) * 1000)
                    if log.isEnabledFor(logging.INFO):
                        log.info("aip.send ok url=%s %dms%s", url, ms, sfx)
                    return r.json()
                if 400 <= r.status_code < 500:
                    r.raise_for_status()
                last_exc = RuntimeError(
                    f"HTTP {r.status_code}: {(r.text or '')[:200]}"
                )
            except httpx.HTTPStatusError as e:
                last_status = (
                    e.response.status_code if e.response is not None else None
                )
                last_exc = e
                if last_status is not None and 400 <= last_status < 500:
                    raise
            except _retryable as e:
                last_exc = e
                last_status = None

            if attempt < p.max_retries - 1:
                delay = p.backoff_delay(attempt)
                if log.isEnabledFor(logging.INFO):
                    log.info(
                        "aip.send retry url=%s attempt=%d delay=%.2fs%s",
                        url, attempt + 1, delay, sfx,
                    )
                time.sleep(delay)

    if log.isEnabledFor(logging.INFO):
        log.info(
            "aip.send failed url=%s attempts=%d status=%s%s",
            url, p.max_retries, last_status, sfx,
        )
    raise last_exc or RuntimeError("aip.send failed after retries")


def send_batch(
    requests: list[tuple[str, AIPMessage | dict[str, Any]]],
    params: SendParams | None = None,
    *,
    max_workers: int | None = None,
    log_extra: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> list[dict[str, Any] | BaseException]:
    """Send multiple AIP messages in parallel (sync, thread pool)."""
    p = params or SendParams()
    n = len(requests)
    if n == 0:
        return []
    workers = min(max_workers or n, n)
    out: dict[int, dict[str, Any] | BaseException] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_idx = {
            pool.submit(send, base_url, msg, p, log_extra=log_extra, logger=logger): i
            for i, (base_url, msg) in enumerate(requests)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                out[idx] = future.result()
            except BaseException as e:
                out[idx] = e
    return [out[i] for i in range(n)]


# ── Send stream (SSE) ────────────────────────────────────────────────


def send_stream(
    base_url: str,
    message: AIPMessage | dict[str, Any],
    params: SendParams | None = None,
    *,
    log_extra: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> Generator[SSEEvent, None, None]:
    """Send an AIP message and consume the SSE streaming response.

    Yields SSEEvent objects. The final event has ``event="done"``
    and its ``data`` contains the AIPAck.
    """
    import httpx

    body = message.to_wire() if hasattr(message, "to_wire") else message
    p = params or SendParams()
    log = logger or _default_logger
    url = f"{base_url.rstrip('/')}/{p.api_version}/aip"
    extra = {"message_id": body.get("message_id", ""), **(log_extra or {})}

    sfx = _log_suffix(extra)
    if log.isEnabledFor(logging.INFO):
        log.info(
            "aip.send_stream start url=%s action=%s%s",
            url, body.get("action", ""), sfx,
        )

    headers: dict[str, str] = {"Accept": "text/event-stream"}
    if p.idempotency_key:
        headers["Idempotency-Key"] = p.idempotency_key

    with httpx.Client(timeout=p.timeout) as client:
        with client.stream("POST", url, json=body, headers=headers) as resp:
            resp.raise_for_status()
            yield from _parse_sse_lines(resp.iter_lines())

    if log.isEnabledFor(logging.INFO):
        log.info("aip.send_stream done url=%s%s", url, sfx)


# ── Async send (JSON) ────────────────────────────────────────────────


async def async_send(
    base_url: str,
    message: AIPMessage | dict[str, Any],
    params: SendParams | None = None,
    *,
    log_extra: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Send an AIP message (async). Same retry semantics as send()."""
    import httpx

    body = message.to_wire() if hasattr(message, "to_wire") else message
    p = params or SendParams()
    log = logger or _default_logger
    url = f"{base_url.rstrip('/')}/{p.api_version}/aip"
    extra = {"message_id": body.get("message_id", ""), **(log_extra or {})}

    sfx = _log_suffix(extra)
    if log.isEnabledFor(logging.INFO):
        log.info(
            "aip.async_send start url=%s action=%s%s",
            url, body.get("action", ""), sfx,
        )

    t0 = time.perf_counter()
    last_exc: Exception | None = None
    last_status: int | None = None

    headers: dict[str, str] = {"Accept": "application/json"}
    if p.idempotency_key:
        headers["Idempotency-Key"] = p.idempotency_key

    _retryable = (
        httpx.ConnectError, httpx.TimeoutException,
        httpx.RemoteProtocolError, OSError,
    )
    async with httpx.AsyncClient(timeout=p.timeout) as client:
        for attempt in range(p.max_retries):
            try:
                r = await client.post(url, json=body, headers=headers)
                last_status = r.status_code
                if r.is_success:
                    ms = round((time.perf_counter() - t0) * 1000)
                    if log.isEnabledFor(logging.INFO):
                        log.info("aip.async_send ok url=%s %dms%s", url, ms, sfx)
                    return r.json()
                if 400 <= r.status_code < 500:
                    r.raise_for_status()
                last_exc = RuntimeError(
                    f"HTTP {r.status_code}: {(r.text or '')[:200]}"
                )
            except httpx.HTTPStatusError as e:
                last_status = (
                    e.response.status_code if e.response is not None else None
                )
                last_exc = e
                if last_status is not None and 400 <= last_status < 500:
                    raise
            except _retryable as e:
                last_exc = e
                last_status = None

            if attempt < p.max_retries - 1:
                delay = p.backoff_delay(attempt)
                if log.isEnabledFor(logging.INFO):
                    log.info(
                        "aip.async_send retry url=%s attempt=%d delay=%.2fs%s",
                        url, attempt + 1, delay, sfx,
                    )
                await asyncio.sleep(delay)

    if log.isEnabledFor(logging.INFO):
        log.info(
            "aip.async_send failed url=%s attempts=%d status=%s%s",
            url, p.max_retries, last_status, sfx,
        )
    raise last_exc or RuntimeError("aip.async_send failed after retries")


async def async_send_batch(
    requests: list[tuple[str, AIPMessage | dict[str, Any]]],
    params: SendParams | None = None,
    *,
    log_extra: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> list[dict[str, Any] | BaseException]:
    """Send multiple AIP messages in parallel (async)."""
    p = params or SendParams()
    tasks = [
        async_send(base_url, msg, p, log_extra=log_extra, logger=logger)
        for base_url, msg in requests
    ]
    return list(await asyncio.gather(*tasks, return_exceptions=True))


# ── Async send stream (SSE) ──────────────────────────────────────────


async def async_send_stream(
    base_url: str,
    message: AIPMessage | dict[str, Any],
    params: SendParams | None = None,
    *,
    log_extra: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> AsyncGenerator[SSEEvent, None]:
    """Send an AIP message and consume the SSE streaming response (async).

    Yields SSEEvent objects. The final event has ``event="done"``
    and its ``data`` contains the AIPAck.
    """
    import httpx

    body = message.to_wire() if hasattr(message, "to_wire") else message
    p = params or SendParams()
    log = logger or _default_logger
    url = f"{base_url.rstrip('/')}/{p.api_version}/aip"
    extra = {"message_id": body.get("message_id", ""), **(log_extra or {})}

    sfx = _log_suffix(extra)
    if log.isEnabledFor(logging.INFO):
        log.info(
            "aip.async_send_stream start url=%s action=%s%s",
            url, body.get("action", ""), sfx,
        )

    headers: dict[str, str] = {"Accept": "text/event-stream"}
    if p.idempotency_key:
        headers["Idempotency-Key"] = p.idempotency_key

    async with httpx.AsyncClient(timeout=p.timeout) as client:
        async with client.stream("POST", url, json=body, headers=headers) as resp:
            resp.raise_for_status()
            async for event in _parse_sse_lines_async(resp.aiter_lines()):
                yield event

    if log.isEnabledFor(logging.INFO):
        log.info("aip.async_send_stream done url=%s%s", url, sfx)
