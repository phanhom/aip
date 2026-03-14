"""AIP Bridge — universal agent-to-AIP gateway.

Connect any agent to an AIP platform with one command:

    aip bridge --agent http://localhost:8080 --platform https://hive.example.com --secret sk-xxx

Protocols auto-detected from URL scheme:
    http(s)://  → HTTP POST
    ws(s)://    → WebSocket
    stdio:cmd   → Subprocess stdin/stdout (JSONL)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform as platform_mod
import socket
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse

log = logging.getLogger("aip.bridge")

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 1.0
DEFAULT_BACKOFF_MAX = 30.0


# ── Retry helper ──────────────────────────────────────────────────────


async def _retry(
    coro_factory,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_base: float = DEFAULT_BACKOFF_BASE,
    backoff_max: float = DEFAULT_BACKOFF_MAX,
    label: str = "operation",
):
    """Call coro_factory() up to max_retries+1 times with exponential backoff."""
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                delay = min(backoff_base * (2**attempt), backoff_max)
                log.warning(
                    "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                    label,
                    attempt + 1,
                    max_retries + 1,
                    e,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                log.error(
                    "%s failed after %d attempts: %s",
                    label,
                    max_retries + 1,
                    e,
                )
    raise last_exc  # type: ignore[misc]


# ── Transports ────────────────────────────────────────────────────────


class Transport(ABC):
    """Wire-level adapter for reaching the external agent."""

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def send(self, body: dict) -> dict: ...

    @abstractmethod
    def send_stream(self, body: dict) -> AsyncIterator[dict]: ...

    async def close(self) -> None:
        pass


class HTTPTransport(Transport):
    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 120,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = None

    async def connect(self):
        import httpx

        self._client = httpx.AsyncClient(
            timeout=self.timeout, headers=self.headers
        )

    async def _do_send(self, body: dict) -> dict:
        resp = await self._client.post(self.url, json=body)
        resp.raise_for_status()
        return resp.json()

    async def send(self, body: dict) -> dict:
        return await _retry(
            lambda: self._do_send(body),
            max_retries=self.max_retries,
            label=f"HTTP POST {self.url}",
        )

    async def send_stream(self, body: dict) -> AsyncIterator[dict]:
        async with self._client.stream("POST", self.url, json=body) as resp:
            resp.raise_for_status()
            buf = ""
            async for chunk in resp.aiter_text():
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if line == "[DONE]":
                        return
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        yield {"text": line}

    async def close(self):
        if self._client:
            await self._client.aclose()


class WebSocketTransport(Transport):
    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.url = url
        self.headers = headers or {}
        self.max_retries = max_retries
        self._ws = None
        self._connected = False

    async def connect(self):
        try:
            import websockets  # noqa: F401
        except ImportError:
            raise ImportError(
                "WebSocket support requires 'websockets'. "
                "Install with: pip install aip-protocol[bridge,ws]"
            )
        await self._do_connect()

    async def _do_connect(self):
        import websockets

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = await websockets.connect(
            self.url, additional_headers=self.headers
        )
        self._connected = True
        log.info("WebSocket connected: %s", self.url)

    async def _ensure_connected(self):
        if self._connected and self._ws and self._ws.open:
            return
        log.warning("WebSocket disconnected, reconnecting: %s", self.url)
        await _retry(
            self._do_connect,
            max_retries=self.max_retries,
            label=f"WS reconnect {self.url}",
        )

    async def send(self, body: dict) -> dict:
        async def _do():
            await self._ensure_connected()
            await self._ws.send(json.dumps(body))
            raw = await self._ws.recv()
            text = raw if isinstance(raw, str) else raw.decode()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"response": text}

        return await _retry(
            _do,
            max_retries=self.max_retries,
            label=f"WS send {self.url}",
        )

    async def send_stream(self, body: dict) -> AsyncIterator[dict]:
        await self._ensure_connected()
        await self._ws.send(json.dumps(body))
        async for raw in self._ws:
            text = raw if isinstance(raw, str) else raw.decode()
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = {"text": text}
            yield data
            if data.get("done") or data.get("type") == "message_stop":
                return

    async def close(self):
        self._connected = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass


class StdioTransport(Transport):
    """Subprocess communicating via JSONL on stdin/stdout. Auto-restarts on crash."""

    def __init__(
        self,
        command: str,
        env_extra: dict[str, str] | None = None,
        max_restarts: int = 5,
    ):
        self.command = command
        self.env_extra = env_extra or {}
        self.max_restarts = max_restarts
        self._proc: asyncio.subprocess.Process | None = None
        self._restart_count = 0

    async def connect(self):
        await self._start_process()

    async def _start_process(self):
        env = os.environ.copy()
        env.update(self.env_extra)
        self._proc = await asyncio.create_subprocess_shell(
            self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        log.info(
            "Subprocess started: pid=%d cmd=%s (restarts=%d)",
            self._proc.pid,
            self.command,
            self._restart_count,
        )

    async def _ensure_alive(self):
        if self._proc and self._proc.returncode is None:
            return
        if self._restart_count >= self.max_restarts:
            raise RuntimeError(
                f"Subprocess crashed {self._restart_count} times, "
                f"giving up: {self.command}"
            )
        self._restart_count += 1
        log.warning(
            "Subprocess died (exit=%s), restarting (%d/%d): %s",
            self._proc.returncode if self._proc else "?",
            self._restart_count,
            self.max_restarts,
            self.command,
        )
        await self._start_process()

    async def send(self, body: dict) -> dict:
        await self._ensure_alive()
        self._proc.stdin.write((json.dumps(body) + "\n").encode())
        await self._proc.stdin.drain()
        line = await self._proc.stdout.readline()
        if not line:
            raise RuntimeError("Agent subprocess closed stdout unexpectedly")
        return json.loads(line.decode())

    async def send_stream(self, body: dict) -> AsyncIterator[dict]:
        await self._ensure_alive()
        body["stream"] = True
        self._proc.stdin.write((json.dumps(body) + "\n").encode())
        await self._proc.stdin.drain()
        while True:
            line = await self._proc.stdout.readline()
            if not line:
                return
            data = json.loads(line.decode())
            yield data
            if data.get("done"):
                return

    async def close(self):
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._proc.kill()


# ── Formatters ────────────────────────────────────────────────────────


class Formatter:
    """Translates AIP intent/payload ↔ agent-native request/response."""

    def encode(self, intent: str, payload: dict | None) -> dict:
        body: dict = {"message": intent}
        if payload:
            body["context"] = payload
        return body

    def decode_response(self, data: dict) -> str:
        for key in ("response", "text", "content", "result", "output", "answer"):
            if key in data:
                return str(data[key])
        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message") or choices[0].get("delta", {})
            if c := msg.get("content"):
                return c
        return json.dumps(data)

    def decode_chunk(self, data: dict) -> str | None:
        for key in ("text", "content", "delta", "response", "chunk"):
            if key in data:
                return str(data[key])
        choices = data.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            return delta.get("content")
        return None


class OpenAIFormatter(Formatter):
    """For OpenAI-compatible chat completion APIs (LiteLLM, Ollama, vLLM, etc.)."""

    def __init__(self, model: str = "default"):
        self.model = model

    def encode(self, intent: str, payload: dict | None) -> dict:
        messages = list(payload.get("messages", [])) if payload else []
        messages.append({"role": "user", "content": intent})
        return {"model": self.model, "messages": messages}


class AnthropicFormatter(Formatter):
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model

    def encode(self, intent: str, payload: dict | None) -> dict:
        messages = list(payload.get("messages", [])) if payload else []
        messages.append({"role": "user", "content": intent})
        return {"model": self.model, "messages": messages, "max_tokens": 4096}

    def decode_response(self, data: dict) -> str:
        content = data.get("content", [])
        if content and isinstance(content, list):
            parts = [b.get("text", "") for b in content if b.get("type") == "text"]
            if parts:
                return "".join(parts)
        return super().decode_response(data)


class DifyFormatter(Formatter):
    """For Dify.ai chat applications (POST /v1/chat-messages)."""

    def __init__(self, user: str = "aip-bridge"):
        self.user = user

    def encode(self, intent: str, payload: dict | None) -> dict:
        body: dict = {
            "query": intent,
            "response_mode": "blocking",
            "user": self.user,
            "inputs": {},
        }
        if payload:
            cid = payload.get("conversation_id")
            if cid:
                body["conversation_id"] = cid
            if payload.get("inputs"):
                body["inputs"] = payload["inputs"]
        return body

    def decode_response(self, data: dict) -> str:
        if "answer" in data:
            return data["answer"]
        return super().decode_response(data)


class CozeFormatter(Formatter):
    """For Coze (ByteDance) bots (POST /open_api/v2/chat)."""

    def __init__(self, bot_id: str = "", user: str = "aip-bridge"):
        self.bot_id = bot_id
        self.user = user

    def encode(self, intent: str, payload: dict | None) -> dict:
        body: dict = {
            "query": intent,
            "stream": False,
            "user": self.user,
        }
        if self.bot_id:
            body["bot_id"] = self.bot_id
        if payload:
            if payload.get("bot_id"):
                body["bot_id"] = payload["bot_id"]
            if payload.get("conversation_id"):
                body["conversation_id"] = payload["conversation_id"]
        return body

    def decode_response(self, data: dict) -> str:
        messages = data.get("messages", [])
        if messages:
            for m in reversed(messages):
                if m.get("role") == "assistant" and m.get("type") == "answer":
                    return m.get("content", "")
            return messages[-1].get("content", json.dumps(data))
        if "answer" in data:
            return data["answer"]
        return super().decode_response(data)


class RawFormatter(Formatter):
    """Passes the full AIP message fields through without transformation."""

    def encode(self, intent: str, payload: dict | None) -> dict:
        return {"intent": intent, "payload": payload or {}}

    def decode_response(self, data: dict) -> str:
        return data.get("intent", data.get("response", json.dumps(data)))


# ── Factory helpers ───────────────────────────────────────────────────


def detect_protocol(url: str) -> tuple[str, str]:
    """Return (protocol_name, cleaned_url) from an agent URL."""
    if url.startswith(("stdio:", "cmd:")):
        prefix = "stdio:" if url.startswith("stdio:") else "cmd:"
        return "stdio", url[len(prefix):]
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme in ("ws", "wss"):
        return "ws", url
    if scheme in ("http", "https"):
        return "http", url
    if not scheme:
        return "http", f"http://{url}"
    return "http", url


def build_transport(
    agent_url: str,
    *,
    protocol: str | None = None,
    agent_secret: str | None = None,
    timeout: float = 120,
) -> Transport:
    if protocol:
        proto, clean = protocol, agent_url
        if proto == "stdio" and agent_url.startswith(("stdio:", "cmd:")):
            _, clean = detect_protocol(agent_url)
    else:
        proto, clean = detect_protocol(agent_url)

    headers = {"Authorization": f"Bearer {agent_secret}"} if agent_secret else {}
    env = {"AIP_SECRET": agent_secret} if agent_secret else {}

    match proto:
        case "http":
            return HTTPTransport(clean, headers=headers, timeout=timeout)
        case "ws":
            return WebSocketTransport(clean, headers=headers)
        case "stdio":
            return StdioTransport(clean, env_extra=env)
        case _:
            raise ValueError(
                f"Unsupported protocol '{proto}'. "
                "Supported: http, ws, stdio. "
                "Use --protocol to override auto-detection."
            )


def build_formatter(api_format: str = "generic", **kw) -> Formatter:
    match api_format:
        case "openai":
            return OpenAIFormatter(model=kw.get("model", "default"))
        case "anthropic":
            return AnthropicFormatter(
                model=kw.get("model", "claude-sonnet-4-20250514"),
            )
        case "dify":
            return DifyFormatter(user=kw.get("user", "aip-bridge"))
        case "coze":
            return CozeFormatter(
                bot_id=kw.get("bot_id", ""),
                user=kw.get("user", "aip-bridge"),
            )
        case "raw":
            return RawFormatter()
        case _:
            return Formatter()


# ── Bridge configuration ──────────────────────────────────────────────


@dataclass
class BridgeConfig:
    agent_url: str
    platform_url: str | None = None
    secret: str | None = None
    agent_secret: str | None = None
    agent_id: str | None = None
    name: str | None = None
    namespace: str = "default"
    role: str = "worker"
    tags: list[str] = field(default_factory=list)
    icon_url: str | None = None
    color: str | None = None
    port: int = 9090
    host: str = "0.0.0.0"
    public_url: str | None = None
    protocol: str | None = None
    api_format: str = "generic"
    timeout: float = 120
    heartbeat_interval: int = 10


# ── Bridge runner ─────────────────────────────────────────────────────


def _resolve_identity(cfg: BridgeConfig) -> tuple[str, str, str]:
    hostname = platform_mod.node() or socket.gethostname()
    agent_id = cfg.agent_id or f"bridge-{hostname}-{cfg.port}"
    display_name = cfg.name or f"Agent @ {hostname}"
    base_url = cfg.public_url or f"http://{hostname}:{cfg.port}"
    return agent_id, display_name, base_url


def run_bridge(cfg: BridgeConfig) -> None:
    """Start the AIP bridge server. Blocks until terminated."""
    try:
        import uvicorn  # noqa: F401
        from fastapi import FastAPI, Request  # noqa: F401
        from fastapi.responses import JSONResponse, StreamingResponse  # noqa: F401
    except ImportError:
        raise SystemExit(
            "Bridge requires FastAPI + Uvicorn.\n"
            "Install with: pip install aip-protocol[bridge]"
        )

    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, StreamingResponse

    agent_id, display_name, base_url = _resolve_identity(cfg)
    transport = build_transport(
        cfg.agent_url,
        protocol=cfg.protocol,
        agent_secret=cfg.agent_secret,
        timeout=cfg.timeout,
    )
    formatter = build_formatter(cfg.api_format)
    proto_name = cfg.protocol or detect_protocol(cfg.agent_url)[0]
    task_count = 0
    bg_tasks: list[asyncio.Task] = []

    @asynccontextmanager
    async def lifespan(_app):
        await transport.connect()
        _print_banner(cfg, agent_id, display_name, base_url, proto_name)
        if cfg.platform_url:
            bg_tasks.append(
                asyncio.create_task(
                    _register_with_retry(cfg, agent_id, base_url, bg_tasks)
                )
            )
        yield
        for t in bg_tasks:
            t.cancel()
        if cfg.platform_url:
            await _deregister(cfg, agent_id)
        await transport.close()

    app = FastAPI(title=f"AIP Bridge — {agent_id}", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/v1/status")
    async def get_status():
        presentation: dict = {
            "display_name": display_name,
            "categories": cfg.tags or [],
        }
        if cfg.icon_url:
            presentation["icon_url"] = cfg.icon_url
        if cfg.color:
            presentation["color"] = cfg.color
        return {
            "agent_id": agent_id,
            "role": cfg.role,
            "namespace": cfg.namespace,
            "presentation": presentation,
            "lifecycle": "running",
            "ok": True,
            "base_url": base_url,
            "endpoints": {
                "aip": f"{base_url}/v1/aip",
                "status": f"{base_url}/v1/status",
            },
            "supported_versions": ["1.0"],
            "pending_tasks": task_count,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
        }

    @app.post("/v1/aip")
    async def post_aip(request: Request):
        nonlocal task_count
        body = await request.json()
        intent = body.get("intent", "")
        payload = body.get("payload")
        accept = request.headers.get("accept", "text/event-stream")

        if "text/event-stream" in accept:
            return StreamingResponse(
                _sse(transport, formatter, intent, payload, body, agent_id),
                media_type="text/event-stream",
            )

        task_count += 1
        try:
            result = await transport.send(formatter.encode(intent, payload))
            text = formatter.decode_response(result)
            return {
                "ok": True,
                "message_id": body.get("message_id", ""),
                "to": agent_id,
                "status": "received",
                "intent": text,
            }
        except Exception as e:
            return JSONResponse(
                status_code=502,
                content={
                    "ok": False,
                    "message_id": body.get("message_id", ""),
                    "to": agent_id,
                    "status": "rejected",
                    "error_code": "aip/execution/task_failed",
                    "error_message": str(e),
                },
            )
        finally:
            task_count -= 1

    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")


# ── Internal helpers ──────────────────────────────────────────────────


async def _sse(transport, formatter, intent, payload, raw_msg, agent_id):
    task_id = f"task-{raw_msg.get('message_id', 'x')[:8]}"
    yield (
        f"event: status\n"
        f"data: {json.dumps({'task_id': task_id, 'state': 'working', 'progress': 0.0})}\n\n"
    )
    try:
        result = await transport.send(formatter.encode(intent, payload))
        text = formatter.decode_response(result)
        yield f"event: message\ndata: {json.dumps({'intent': text})}\n\n"
        done_payload = {
            "ok": True,
            "message_id": raw_msg.get("message_id", ""),
            "to": agent_id,
            "status": "received",
            "task_id": task_id,
        }
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
    except Exception as e:
        err = {
            "error_code": "aip/execution/task_failed",
            "error_message": str(e),
        }
        yield f"event: error\ndata: {json.dumps(err)}\n\n"


async def _register_once(
    platform_url: str,
    agent_id: str,
    base_url: str,
    namespace: str,
    secret: str | None,
    endpoints: dict[str, str] | None = None,
) -> str | None:
    """Single registration attempt. Returns heartbeat_url or None."""
    import httpx

    headers = {"Authorization": f"Bearer {secret}"} if secret else {}
    body: dict = {
        "agent_id": agent_id,
        "base_url": base_url,
        "namespace": namespace,
        "protocol": "aip",
    }
    if endpoints:
        body["endpoints"] = endpoints
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{platform_url}/v1/registry/agents",
            json=body,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        log.info("Registered with platform: agent_id=%s", agent_id)
        return data.get("heartbeat_url")


async def _register_with_retry(
    cfg: BridgeConfig,
    agent_id: str,
    base_url: str,
    bg_tasks: list,
):
    """Register with exponential backoff, then start heartbeat."""
    delay = 1.0
    max_delay = 60.0
    while True:
        try:
            hb_url = await _register_once(
                cfg.platform_url,
                agent_id,
                base_url,
                cfg.namespace,
                cfg.secret,
            )
            if hb_url:
                bg_tasks.append(
                    asyncio.create_task(
                        _heartbeat_loop(
                            hb_url,
                            cfg.secret,
                            cfg.heartbeat_interval,
                            lambda: 0,
                        )
                    )
                )
            return
        except asyncio.CancelledError:
            return
        except Exception as e:
            log.warning(
                "Registration failed: %s — retrying in %.0fs", e, delay
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)


async def _deregister(cfg: BridgeConfig, agent_id: str):
    """Best-effort deregistration on shutdown."""
    if not cfg.platform_url:
        return
    import httpx

    headers = {"Authorization": f"Bearer {cfg.secret}"} if cfg.secret else {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.delete(
                f"{cfg.platform_url}/v1/registry/agents/{agent_id}",
                headers=headers,
            )
            log.info("Deregistered from platform: %s", agent_id)
    except Exception as e:
        log.debug("Deregistration failed (best-effort): %s", e)


async def _heartbeat_loop(
    url: str, secret: str | None, interval: int, get_tasks
):
    """Heartbeat with exponential backoff on consecutive failures."""
    import httpx

    headers = {"Authorization": f"Bearer {secret}"} if secret else {}
    consecutive_failures = 0
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        while True:
            if consecutive_failures > 0:
                backoff = min(interval * (2**consecutive_failures), 120)
                await asyncio.sleep(backoff)
            else:
                await asyncio.sleep(interval)
            try:
                await client.post(
                    url,
                    json={
                        "ok": True,
                        "lifecycle": "running",
                        "pending_tasks": get_tasks(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                if consecutive_failures > 0:
                    log.info(
                        "Heartbeat recovered after %d failures",
                        consecutive_failures,
                    )
                consecutive_failures = 0
            except asyncio.CancelledError:
                return
            except Exception as e:
                consecutive_failures += 1
                log.warning(
                    "Heartbeat failed (%d consecutive): %s",
                    consecutive_failures,
                    e,
                )


def _print_banner(cfg, agent_id, display_name, base_url, proto):
    W = 58
    proto_label = {"http": "HTTP", "ws": "WebSocket", "stdio": "Subprocess"}.get(proto, proto)

    def row(label: str, value: str) -> str:
        v = str(value)[: W - 16]
        return f"  ║  {label:<12}{v:<{W - 16}}  ║"

    lines = [
        "",
        f"  ╔{'═' * W}╗",
        f"  ║{'AIP Bridge':^{W}}║",
        f"  ╠{'═' * W}╣",
        row("Agent", cfg.agent_url),
        row("Protocol", proto_label),
        row("Bridge", base_url),
        row("ID", agent_id),
        row("Name", display_name),
        row("Namespace", cfg.namespace),
    ]
    if cfg.platform_url:
        lines.append(row("Platform", cfg.platform_url))
    if cfg.secret:
        masked = "••••" + cfg.secret[-4:] if len(cfg.secret) > 4 else "••••"
        lines.append(row("Auth", masked))
    lines += [
        f"  ╠{'═' * W}╣",
        row("GET", f"{base_url}/v1/status"),
        row("POST", f"{base_url}/v1/aip"),
        f"  ╚{'═' * W}╝",
        "",
    ]
    print("\n".join(lines))
