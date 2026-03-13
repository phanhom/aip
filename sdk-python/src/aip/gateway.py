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
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from aip.bridge import (
    Formatter,
    Transport,
    build_formatter,
    build_transport,
)

log = logging.getLogger("aip.gateway")

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
    __slots__ = ("entry", "transport", "formatter", "task_count", "ok", "last_error")

    def __init__(self, entry: AgentEntry, transport: Transport, formatter: Formatter):
        self.entry = entry
        self.transport = transport
        self.formatter = formatter
        self.task_count: int = 0
        self.ok: bool = True
        self.last_error: str | None = None


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

    hb_tasks: list[asyncio.Task] = []

    @asynccontextmanager
    async def lifespan(_app):
        for aid, be in backends.items():
            try:
                await be.transport.connect()
                log.info("Agent '%s' connected → %s", aid, be.entry.url)
            except Exception as e:
                be.ok = False
                be.last_error = str(e)
                log.error("Agent '%s' connect failed: %s", aid, e)

        _print_banner(cfg, base_url, backends)

        if cfg.platform_url:
            for aid, be in backends.items():
                if not be.ok:
                    continue
                hb_url = await _register_agent(cfg, aid, be.entry, base_url)
                if hb_url:
                    hb_tasks.append(
                        asyncio.create_task(
                            _heartbeat_loop(
                                hb_url,
                                cfg.secret,
                                cfg.heartbeat_interval,
                                lambda _be=be: _be.task_count,
                            )
                        )
                    )

        yield

        for t in hb_tasks:
            t.cancel()
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
        if not be.ok:
            return JSONResponse(status_code=503, content={
                "ok": False,
                "error_code": "aip/protocol/agent_unavailable",
                "error_message": f"Agent '{agent_id}' is down: {be.last_error}",
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
            result = await be.transport.send(be.formatter.encode(intent, payload))
            text = be.formatter.decode_response(result)
            return {
                "ok": True,
                "message_id": body.get("message_id", ""),
                "to": agent_id,
                "status": "received",
                "intent": text,
            }
        except Exception as e:
            be.ok = False
            be.last_error = str(e)
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
        be.ok = False
        be.last_error = str(e)
        err = {"error_code": "aip/execution/task_failed", "error_message": str(e)}
        yield f"event: error\ndata: {json.dumps(err)}\n\n"


# ── Platform registration ────────────────────────────────────────────


async def _register_agent(
    cfg: GatewayConfig, agent_id: str, entry: AgentEntry, gateway_url: str
) -> str | None:
    import httpx

    ns = entry.namespace or cfg.namespace
    headers = {"Authorization": f"Bearer {cfg.secret}"} if cfg.secret else {}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{cfg.platform_url}/v1/registry/agents",
                json={
                    "agent_id": agent_id,
                    "base_url": gateway_url,
                    "namespace": ns,
                    "endpoints": {
                        "aip": f"{gateway_url}/v1/agents/{agent_id}/aip",
                        "status": f"{gateway_url}/v1/agents/{agent_id}/status",
                    },
                },
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            log.info("Registered agent '%s' with platform", agent_id)
            return data.get("heartbeat_url")
    except Exception as e:
        log.error("Registration failed for '%s': %s", agent_id, e)
        return None


async def _heartbeat_loop(url: str, secret: str | None, interval: int, get_tasks):
    import httpx

    headers = {"Authorization": f"Bearer {secret}"} if secret else {}
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        while True:
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
            except Exception as e:
                log.warning("Heartbeat failed: %s", e)


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
