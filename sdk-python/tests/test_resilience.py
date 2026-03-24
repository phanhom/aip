"""Tests for bridge resilience: retry, reconnect, circuit breaker."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from aip.bridge import (
    HTTPTransport,
    StdioTransport,
    WebSocketTransport,
    _retry,
)
from aip.gateway import (
    CIRCUIT_COOLDOWN_SECS,
    CIRCUIT_FAILURE_THRESHOLD,
    AgentEntry,
    _AgentBackend,
)

# ── _retry helper ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retry_succeeds_first_try():
    factory = AsyncMock(return_value="ok")
    result = await _retry(factory, max_retries=3, backoff_base=0.001)
    assert result == "ok"
    assert factory.call_count == 1


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("transient")
        return "recovered"

    result = await _retry(flaky, max_retries=3, backoff_base=0.001)
    assert result == "recovered"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted_raises():
    async def always_fail():
        raise ConnectionError("permanent")

    with pytest.raises(ConnectionError, match="permanent"):
        await _retry(always_fail, max_retries=2, backoff_base=0.001)


# ── HTTPTransport retry ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_http_transport_retries_on_failure():
    t = HTTPTransport("http://example.com/api", max_retries=2)
    call_count = 0

    async def mock_send(body):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("refused")
        return {"response": "ok"}

    t._do_send = mock_send
    result = await t.send({"test": True})
    assert result == {"response": "ok"}
    assert call_count == 2


# ── WebSocketTransport reconnect ──────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_transport_reconnects():
    t = WebSocketTransport("ws://example.com/ws", max_retries=2)
    connect_count = 0

    async def mock_connect():
        nonlocal connect_count
        connect_count += 1

    t._do_connect = mock_connect

    mock_ws = MagicMock()
    mock_ws.open = False
    t._ws = mock_ws
    t._connected = True

    await t._ensure_connected()
    assert connect_count == 1


# ── StdioTransport restart ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stdio_transport_tracks_restarts():
    t = StdioTransport("echo test", max_restarts=3)
    t._restart_count = 3
    t._proc = MagicMock()
    t._proc.returncode = 1

    with pytest.raises(RuntimeError, match="crashed 3 times"):
        await t._ensure_alive()


# ── Circuit breaker ──────────────────────────────────────────────────


def _make_backend(ok: bool = True) -> _AgentBackend:
    entry = AgentEntry(id="test", url="http://test.local")
    transport = MagicMock()
    formatter = MagicMock()
    be = _AgentBackend(entry, transport, formatter)
    be.ok = ok
    return be


def test_circuit_breaker_closed_by_default():
    be = _make_backend()
    assert be.ok is True
    assert be.should_attempt is True
    assert be._consecutive_failures == 0


def test_circuit_breaker_stays_closed_under_threshold():
    be = _make_backend()
    for _ in range(CIRCUIT_FAILURE_THRESHOLD - 1):
        be.record_failure("err")
    assert be.ok is True
    assert be.should_attempt is True


def test_circuit_breaker_opens_at_threshold():
    be = _make_backend()
    for _ in range(CIRCUIT_FAILURE_THRESHOLD):
        be.record_failure("err")
    assert be.ok is False
    assert be.should_attempt is False


def test_circuit_breaker_half_open_after_cooldown():
    be = _make_backend()
    for _ in range(CIRCUIT_FAILURE_THRESHOLD):
        be.record_failure("err")
    assert be.should_attempt is False

    be._circuit_open_since = time.monotonic() - CIRCUIT_COOLDOWN_SECS - 1
    assert be.should_attempt is True


def test_circuit_breaker_resets_on_success():
    be = _make_backend()
    for _ in range(CIRCUIT_FAILURE_THRESHOLD):
        be.record_failure("err")
    assert be.ok is False

    be.record_success()
    assert be.ok is True
    assert be._consecutive_failures == 0
    assert be.should_attempt is True


def test_circuit_breaker_reopen_after_failed_probe():
    be = _make_backend()
    for _ in range(CIRCUIT_FAILURE_THRESHOLD):
        be.record_failure("err")

    be._circuit_open_since = time.monotonic() - CIRCUIT_COOLDOWN_SECS - 1
    assert be.should_attempt is True

    be.record_failure("still down")
    assert be.ok is False
    assert be.should_attempt is False
