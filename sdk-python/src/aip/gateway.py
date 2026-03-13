"""AIP Gateway — host multiple agents behind a single port.

    aip bridge --config gateway.yaml

One process, one port, N agents. Each agent gets its own:
- Transport (HTTP, WebSocket, stdio)
- Status endpoint    GET  /v1/agents/{id}/status
- Message endpoint   POST /v1/agents/{id}/aip
- Health tracking and independent heartbeat

The gateway also exposes:
- GET  /v1/agents     — discover all hosted agents
- GET  /v1/status     — GroupStatus (all agents)
- POST /v1/aip        — route by the `to` field in the message
- GET  /health        — gateway health check

YAML config format:

    platform: https://hive.example.com
    secret: sk-xxx
    namespace: my-team
    port: 9090

    agents:
      - id: coder
        url: http://127.0.0.1:18789/v1/chat/completions
        format: openai
        secret: gw-token-xxx
        name: OpenClaw Coder
        tags: [coding, agent]
        color: "#10B981"
"""

from __future__ import annotations

import asyncio
import json
import logging
import platform as platform_mod
import socket
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from aip.bridge import (
    Formatter,
    Transport,
    _register_once,
    build_formatter,
    build_transport,
)

log = logging.getLogger("aip.gateway")

CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_COOLDOWN_SECS = 30.0

__all__ = ["AgentEntry", "GatewayConfig", "load_config", "run_gateway"]


# ── Configuration ─────────────────────────────────────────────────────


@dataclass
class AgentEntry:
    """One agent backend in the gateway."""

    id: str
    url: str
    format: str = "generic"
    secret: str | None = None
    name: str | None = None
    role: str = "worker"
    namespace: str | None = None
    tags: list[str] = field(default_factory=list)
    icon_url: str | None = None
    color: str | None = None
    timeout: float = 120
    protocol: str | None = None


@dataclass
class GatewayConfig:
    """Multi-agent gateway configuration."""

    agents: list[AgentEntry]
    platform_url: str | None = None
    secret: str | None = None
    namespace: str = "default"
    port: int = 9090
    host: str = "0.0.0.0"
    public_url: str | None = None
    heartbeat_interval: int = 10


def load_config(path: str) -> GatewayConfig:
    """Load gateway config from YAML or JSON file."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")

    if p.suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            raise SystemExit(
                "YAML config requires PyYAML.\n"
                "Install with: pip install aip-protocol[bridge]"
            )
        raw = yaml.safe_load(text)
    else:
        raw = json.loads(text)

    agents = []
    for a in raw.get("agents", []):
        agents.append(
            AgentEntry(
                id=a["id"],
                url=a["url"],
                format=a.get("format", "generic"),
                secret=a.get("secret"),
                name=a.get("name"),
                role=a.get("role", "worker"),
                namespace=a.get("namespace"),
                tags=a.get("tags", []),
                icon_url=a.get("icon"),
                color=a.get("color"),
                timeout=a.get("timeout", 120),
                protocol=a.get("protocol"),
            )
        )

    return GatewayConfig(
        agents=agents,
        platform_url=raw.get("platform"),
        secret=raw.get("secret"),
        namespace=raw.get("namespace", "default"),
        port=raw.get("port", 9090),
        host=raw.get("host", "0.0.0.0"),
        public_url=raw.get("public_url"),
        heartbeat_interval=raw.get("heartbeat", 10),
    )


# ── Runtime state per agent ───────────────────────────────────────────


class _AgentBackend:
    """Runtime state per agent with circuit breaker.

    State machine:
        CLOSED  (ok=True)  — normal operation
        OPEN    (ok=False)  — consecutive failures >= threshold, reject fast
        HALF_OPEN           — cooldown expired, allow one probe request

    On success: reset to CLOSED.
    On failure: increment counter. If >= threshold, move to OPEN.
    After CIRCUIT_COOLDOWN_SECS in OPEN: move to HALF_OPEN (allow one try).
    """

    __slots__ = (
        "entry",
        "transport",
        "formatter",
        "task_count",
        "ok",
        "last_error",
        "_consecutive_failures",
        "_circuit_open_since",
    )

    def __init__(self, entry: AgentEntry, transport: Transport, formatter: Formatter):
        self.entry = entry
        self.transport = transport
        self.formatter = formatter
        self.task_count: int = 0
        self.ok: bool = True
        self.last_error: str | None = None
        self._consecutive_failures: int = 0
        self._circuit_open_since: float = 0.0

    def record_success(self):
        if self._consecutive_failures > 0:
            log.info(
                "Agent '%s' recovered after %d failures",
                self.entry.id,
                self._consecutive_failures,
            )
        self._consecutive_failures = 0
        self._circuit_open_since = 0.0
        self.ok = True
        self.last_error = None

    def record_failure(self, error: str):
        self._consecutive_failures += 1
        self.last_error = error
        if self._consecutive_failures >= CIRCUIT_FAILURE_THRESHOLD:
            self.ok = False
            self._circuit_open_since = time.monotonic()

    @property
    def should_attempt(self) -> bool:
        """True if we should try sending (CLOSED or HALF_OPEN)."""
        if self.ok:
            return True
        elapsed = time.monotonic() - self._circuit_open_since
        if elapsed >= CIRCUIT_COOLDOWN_SECS:
            return True
        return False


# ── Gateway runner ────────────────────────────────────────────────────


def run_gateway(cfg: GatewayConfig) -> None:
    """Start the multi-agent gateway. Blocks until terminated."""
    try:
        import uvicorn
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse, StreamingResponse
    except ImportError:
        raise SystemExit(
            "Gateway requires FastAPI + Uvicorn.\n"
            "Install with: pip install aip-protocol[bridge]"
        )

    if not cfg.agents:
        raise SystemExit("No agents configured. Add at least one agent.")

    ids = [a.id for a in cfg.agents]
    dupes = {x for x in ids if ids.count(x) > 1}
    if dupes:
        raise SystemExit(f"Duplicate agent IDs: {dupes}")

    hostname = platform_mod.node() or socket.gethostname()
    base_url = cfg.public_url or f"http://{hostname}:{cfg.port}"

    backends: dict[str, _AgentBackend] = {}
    for entry in cfg.agents:
        transport = build_transport(
            entry.url,
            protocol=entry.protocol,
            agent_secret=entry.secret,
            timeout=entry.timeout,
        )
        formatter = build_formatter(entry.format)
        backends[entry.id] = _AgentBackend(entry, transport, formatter)

    bg_tasks: list[asyncio.Task] = []

    @asynccontextmanager
    async def lifespan(_app):
        for aid, be in backends.items():
            try:
                await be.transport.connect()
                log.info("Agent '%s' connected → %s", aid, be.entry.url)
            except Exception as e:
                be.record_failure(str(e))
                log.error("Agent '%s' connect failed: %s", aid, e)

        _print_banner(cfg, base_url, backends)

        if cfg.platform_url:
            for aid, be in backends.items():
                bg_tasks.append(
                    asyncio.create_task(
                        _register_agent_with_retry(
                            cfg, aid, be, base_url, bg_tasks
                        )
                    )
                )

        bg_tasks.append(asyncio.create_task(_health_probe_loop(backends)))

        yield

        for t in bg_tasks:
            t.cancel()
        if cfg.platform_url:
            await _deregister_all(cfg, backends)
        for be in backends.values():
            await be.transport.close()

    app = FastAPI(title=f"AIP Gateway — {hostname}", lifespan=lifespan)

    # ── helpers ────────────────────────────────────────────────────

    def _agent_status(aid: str, be: _AgentBackend) -> dict:
        ns = be.entry.namespace or cfg.namespace
        name = be.entry.name or aid
        presentation: dict = {"display_name": name, "categories": be.entry.tags}
        if be.entry.icon_url:
            presentation["icon_url"] = be.entry.icon_url
        if be.entry.color:
            presentation["color"] = be.entry.color
        return {
            "agent_id": aid,
            "role": be.entry.role,
            "namespace": ns,
            "presentation": presentation,
            "lifecycle": "running" if be.ok else "failed",
            "ok": be.ok,
            "base_url": base_url,
            "endpoints": {
                "aip": f"{base_url}/v1/agents/{aid}/aip",
                "status": f"{base_url}/v1/agents/{aid}/status",
            },
            "supported_versions": ["1.0"],
            "pending_tasks": be.task_count,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            **({"error_message": be.last_error} if be.last_error else {}),
        }

    # ── gateway-level endpoints ────────────────────────────────────

    @app.get("/health")
    async def health():
        per_agent = {aid: "running" if be.ok else "failed" for aid, be in backends.items()}
        return {"ok": all(be.ok for be in backends.values()), "agents": per_agent}

    @app.get("/v1/agents")
    async def list_agents():
        return [_agent_status(aid, be) for aid, be in backends.items()]

    @app.get("/v1/status")
    async def group_status():
        return {
            "ok": all(be.ok for be in backends.values()),
            "service": "aip",
            "namespace": cfg.namespace,
            "root_agent_id": f"gateway-{hostname}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents": [_agent_status(aid, be) for aid, be in backends.items()],
        }

    @app.post("/v1/aip")
    async def route_aip(request: Request):
        body = await request.json()
        target = body.get("to", "")
        if target not in backends:
            return JSONResponse(
                status_code=404,
                content={
                    "ok": False,
                    "error_code": "aip/protocol/agent_not_found",
                    "error_message": (
                        f"No agent '{target}' on this gateway. "
                        f"Available: {list(backends.keys())}"
                    ),
                },
            )
        return await _handle_aip(target, request, body)

    # ── per-agent endpoints ────────────────────────────────────────

    @app.get("/v1/agents/{agent_id}/status")
    async def agent_status(agent_id: str):
        if agent_id not in backends:
            return JSONResponse(status_code=404, content={
                "ok": False,
                "error_code": "aip/protocol/agent_not_found",
                "error_message": f"No agent '{agent_id}' on this gateway.",
            })
        return _agent_status(agent_id, backends[agent_id])

    @app.get("/v1/agents/{agent_id}/tasks/{task_id}")
    async def agent_task(agent_id: str, task_id: str):
        return JSONResponse(status_code=501, content={
            "error_code": "aip/execution/task_not_found",
            "error_message": "Task storage not implemented in gateway bridge.",
        })

    @app.post("/v1/agents/{agent_id}/aip")
    async def agent_aip(agent_id: str, request: Request):
        if agent_id not in backends:
            return JSONResponse(status_code=404, content={
                "ok": False,
                "error_code": "aip/protocol/agent_not_found",
                "error_message": f"No agent '{agent_id}' on this gateway.",
            })
        body = await request.json()
        return await _handle_aip(agent_id, request, body)

    # ── shared message handler ─────────────────────────────────────

    async def _handle_aip(agent_id: str, request: Request, body: dict):
        be = backends[agent_id]
        if not be.should_attempt:
            return JSONResponse(status_code=503, content={
                "ok": False,
                "error_code": "aip/protocol/agent_unavailable",
                "error_message": (
                    f"Agent '{agent_id}' circuit open "
                    f"({be._consecutive_failures} failures): {be.last_error}"
                ),
            })

        intent = body.get("intent", "")
        payload = body.get("payload")
        accept = request.headers.get("accept", "text/event-stream")

        if "text/event-stream" in accept:
            return StreamingResponse(
                _sse(be, intent, payload, body, agent_id),
                media_type="text/event-stream",
            )

        be.task_count += 1
        try:
            result = await be.transport.send(
                be.formatter.encode(intent, payload)
            )
            text = be.formatter.decode_response(result)
            be.record_success()
            return {
                "ok": True,
                "message_id": body.get("message_id", ""),
                "to": agent_id,
                "status": "received",
                "intent": text,
            }
        except Exception as e:
            be.record_failure(str(e))
            return JSONResponse(status_code=502, content={
                "ok": False,
                "message_id": body.get("message_id", ""),
                "to": agent_id,
                "status": "rejected",
                "error_code": "aip/execution/task_failed",
                "error_message": str(e),
            })
        finally:
            be.task_count -= 1

    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")


# ── SSE helper ────────────────────────────────────────────────────────


async def _sse(be: _AgentBackend, intent, payload, raw_msg, agent_id):
    task_id = f"task-{raw_msg.get('message_id', 'x')[:8]}"
    yield (
        f"event: status\n"
        f"data: {json.dumps({'task_id': task_id, 'state': 'working', 'progress': 0.0})}\n\n"
    )
    try:
        result = await be.transport.send(be.formatter.encode(intent, payload))
        text = be.formatter.decode_response(result)
        be.record_success()
        yield f"event: message\ndata: {json.dumps({'intent': text})}\n\n"
        done = {
            "ok": True,
            "message_id": raw_msg.get("message_id", ""),
            "to": agent_id,
            "status": "received",
            "task_id": task_id,
        }
        yield f"event: done\ndata: {json.dumps(done)}\n\n"
    except Exception as e:
        be.record_failure(str(e))
        err = {
            "error_code": "aip/execution/task_failed",
            "error_message": str(e),
        }
        yield f"event: error\ndata: {json.dumps(err)}\n\n"


# ── Platform registration with retry ─────────────────────────────────


async def _register_agent_with_retry(
    cfg: GatewayConfig,
    agent_id: str,
    be: _AgentBackend,
    gateway_url: str,
    bg_tasks: list,
):
    """Register one agent with exponential backoff, then start heartbeat."""
    ns = be.entry.namespace or cfg.namespace
    endpoints = {
        "aip": f"{gateway_url}/v1/agents/{agent_id}/aip",
        "status": f"{gateway_url}/v1/agents/{agent_id}/status",
    }
    delay = 1.0
    max_delay = 60.0
    while True:
        try:
            hb_url = await _register_once(
                cfg.platform_url,
                agent_id,
                gateway_url,
                ns,
                cfg.secret,
                endpoints=endpoints,
            )
            if hb_url:
                bg_tasks.append(
                    asyncio.create_task(
                        _heartbeat_loop(
                            hb_url,
                            cfg.secret,
                            cfg.heartbeat_interval,
                            lambda _be=be: _be.task_count,
                        )
                    )
                )
            return
        except asyncio.CancelledError:
            return
        except Exception as e:
            log.warning(
                "Registration of '%s' failed: %s — retrying in %.0fs",
                agent_id,
                e,
                delay,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)


async def _heartbeat_loop(url, secret, interval, get_tasks):
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


async def _deregister_all(cfg: GatewayConfig, backends: dict):
    """Best-effort deregistration of all agents on shutdown."""
    import httpx

    headers = {"Authorization": f"Bearer {cfg.secret}"} if cfg.secret else {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            for aid in backends:
                try:
                    await client.delete(
                        f"{cfg.platform_url}/v1/registry/agents/{aid}",
                        headers=headers,
                    )
                    log.info("Deregistered '%s' from platform", aid)
                except Exception:
                    pass
    except Exception:
        pass


async def _health_probe_loop(backends: dict[str, _AgentBackend]):
    """Periodically probe failed agents to see if they've recovered."""
    while True:
        await asyncio.sleep(CIRCUIT_COOLDOWN_SECS)
        for aid, be in backends.items():
            if be.ok:
                continue
            elapsed = time.monotonic() - be._circuit_open_since
            if elapsed < CIRCUIT_COOLDOWN_SECS:
                continue
            try:
                await be.transport.connect()
                be.record_success()
                log.info(
                    "Health probe: agent '%s' is back online", aid
                )
            except asyncio.CancelledError:
                return
            except Exception as e:
                be.record_failure(str(e))
                log.debug(
                    "Health probe: agent '%s' still down: %s", aid, e
                )


# ── Banner ────────────────────────────────────────────────────────────


def _print_banner(cfg: GatewayConfig, base_url: str, backends: dict[str, _AgentBackend]):
    W = 60

    def row(label: str, value: str) -> str:
        v = str(value)[: W - 16]
        return f"  ║  {label:<12}{v:<{W - 16}}  ║"

    lines = [
        "",
        f"  ╔{'═' * W}╗",
        f"  ║{'AIP Gateway':^{W}}║",
        f"  ╠{'═' * W}╣",
        row("Agents", str(len(backends))),
        row("Port", str(cfg.port)),
        row("Namespace", cfg.namespace),
    ]
    if cfg.platform_url:
        lines.append(row("Platform", cfg.platform_url))
    if cfg.secret:
        masked = "••••" + cfg.secret[-4:] if len(cfg.secret) > 4 else "••••"
        lines.append(row("Auth", masked))
    lines.append(f"  ╠{'═' * W}╣")
    for aid, be in backends.items():
        status = "ok" if be.ok else "FAIL"
        lines.append(row(f"  {aid}", f"[{status}] {be.entry.url}"))
    lines += [
        f"  ╠{'═' * W}╣",
        row("Discovery", f"GET  {base_url}/v1/agents"),
        row("Status", f"GET  {base_url}/v1/status"),
        row("Health", f"GET  {base_url}/health"),
        f"  ╚{'═' * W}╝",
        "",
    ]
    print("\n".join(lines))
