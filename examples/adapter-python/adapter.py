#!/usr/bin/env python3
"""AIP Adapter — wrap ANY agent into an AIP-compliant endpoint.

    pip install aip-protocol fastapi uvicorn httpx
    python adapter.py

This adapter sits between your AIP platform and any external agent that
doesn't natively speak AIP. It:

  1. Exposes GET  /v1/status  — returns a proper AIP AgentStatus
  2. Exposes POST /v1/aip     — accepts AIP messages, translates them to
     the external agent's native API, streams results back as SSE
  3. Auto-registers with an AIP platform (if PLATFORM_URL is set)
  4. Sends heartbeats to keep the registration alive

To adapt YOUR agent, edit the three functions marked with ✏️ below.
Everything else is generic AIP plumbing.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from aip import (
    AIPAck,
    AIPMessage,
    AgentStatus,
    Presentation,
    Provider,
    SkillDescriptor,
    StatusEndpoints,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [adapter] %(message)s")
log = logging.getLogger("aip-adapter")

# ── Configuration ──────────────────────────────────────────────────────

AGENT_ID = os.getenv("AGENT_ID", "my-external-agent")
AGENT_ROLE = os.getenv("AGENT_ROLE", "assistant")
BASE_URL = os.getenv("BASE_URL", "http://localhost:9000")
EXTERNAL_AGENT_URL = os.getenv("EXTERNAL_AGENT_URL", "http://localhost:5000")
PLATFORM_URL = os.getenv("PLATFORM_URL", "")  # e.g. https://platform.example.com
NAMESPACE = os.getenv("NAMESPACE", "default")

app = FastAPI(title=f"AIP Adapter — {AGENT_ID}")
http = httpx.AsyncClient(timeout=120)
task_counter = 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✏️  EDIT THESE THREE FUNCTIONS TO MATCH YOUR EXTERNAL AGENT'S API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_agent_skills() -> list[SkillDescriptor]:
    """✏️ Describe what your external agent can do."""
    return [
        SkillDescriptor(
            id="general-chat",
            name="General Assistant",
            description="Answers questions and performs tasks via natural language",
            tags=["general", "chat", "reasoning"],
            input_modes=["application/json", "text/plain"],
            output_modes=["application/json", "text/plain"],
        ),
    ]


def get_agent_presentation() -> Presentation:
    """✏️ How this agent appears in dashboards and UIs."""
    return Presentation(
        display_name="My External Agent",
        tagline="A powerful AI assistant wrapped for AIP",
        color="#8B5CF6",
        locale="en",
        categories=["general", "assistant"],
        provider=Provider(name="Your Org"),
    )


async def call_external_agent(intent: str, payload: dict) -> dict:
    """✏️ Translate an AIP message into your agent's native API call.

    This example assumes the external agent has a POST /v1/chat endpoint
    that accepts {"message": "..."} and returns {"response": "..."}.

    Replace this with whatever your agent's API looks like:
    - OpenAI Assistants API
    - A custom REST endpoint
    - A gRPC call
    - A WebSocket message
    """
    body = {"message": intent}
    if payload:
        body["context"] = payload

    resp = await http.post(f"{EXTERNAL_AGENT_URL}/v1/chat", json=body)
    resp.raise_for_status()
    return resp.json()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AIP PROTOCOL ENDPOINTS (generic — no need to edit)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/v1/status")
async def status():
    return AgentStatus(
        agent_id=AGENT_ID,
        role=AGENT_ROLE,
        namespace=NAMESPACE,
        presentation=get_agent_presentation(),
        lifecycle="running",
        ok=True,
        base_url=BASE_URL,
        endpoints=StatusEndpoints(
            aip=f"{BASE_URL}/v1/aip",
            status=f"{BASE_URL}/v1/status",
        ),
        skills=get_agent_skills(),
        supported_versions=["1.0"],
        pending_tasks=task_counter,
        last_seen_at=datetime.now(timezone.utc).isoformat(),
    ).model_dump()


@app.post("/v1/aip")
async def receive_message(request: Request):
    global task_counter
    body = await request.json()
    msg = AIPMessage(**body)

    accept = request.headers.get("accept", "text/event-stream")

    if "text/event-stream" in accept:
        return StreamingResponse(
            _stream_response(msg),
            media_type="text/event-stream",
        )

    task_counter += 1
    try:
        result = await call_external_agent(msg.intent, msg.payload or {})
        task_counter -= 1
        return AIPAck(
            ok=True,
            message_id=msg.message_id,
            to=AGENT_ID,
            status="received",
            correlation_id=msg.correlation_id,
        ).model_dump()
    except Exception as e:
        task_counter -= 1
        return JSONResponse(status_code=500, content={
            "ok": False,
            "message_id": msg.message_id,
            "to": AGENT_ID,
            "status": "rejected",
            "error_code": "aip/execution/task_failed",
            "error_message": str(e),
        })


async def _stream_response(msg: AIPMessage):
    global task_counter
    task_id = f"task-{msg.message_id[:8]}"
    task_counter += 1

    yield f"event: status\ndata: {json.dumps({'task_id': task_id, 'state': 'working', 'progress': 0.0})}\n\n"

    try:
        result = await call_external_agent(msg.intent, msg.payload or {})

        yield f"event: status\ndata: {json.dumps({'task_id': task_id, 'state': 'working', 'progress': 0.8})}\n\n"

        yield f"event: message\ndata: {json.dumps({'intent': result.get('response', str(result))})}\n\n"

        ack = {
            "ok": True,
            "message_id": msg.message_id,
            "to": AGENT_ID,
            "status": "received",
            "task_id": task_id,
        }
        yield f"event: done\ndata: {json.dumps(ack)}\n\n"

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error_code': 'aip/execution/task_failed', 'error_message': str(e)})}\n\n"

    task_counter -= 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AUTO-REGISTRATION + HEARTBEAT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

heartbeat_url: str | None = None
heartbeat_interval: int = 10


@app.on_event("startup")
async def on_startup():
    global heartbeat_url, heartbeat_interval

    if not PLATFORM_URL:
        log.info("No PLATFORM_URL set — skipping auto-registration")
        return

    log.info("Registering with platform at %s ...", PLATFORM_URL)
    try:
        resp = await http.post(f"{PLATFORM_URL}/v1/registry/agents", json={
            "base_url": BASE_URL,
            "namespace": NAMESPACE,
        })
        resp.raise_for_status()
        data = resp.json()
        heartbeat_url = data.get("heartbeat_url")
        heartbeat_interval = data.get("heartbeat_interval_seconds", 10)
        log.info("Registered as %s — heartbeat every %ds", data.get("agent_id"), heartbeat_interval)

        asyncio.create_task(_heartbeat_loop())
    except Exception as e:
        log.error("Registration failed: %s", e)


async def _heartbeat_loop():
    while heartbeat_url:
        await asyncio.sleep(heartbeat_interval)
        try:
            await http.post(heartbeat_url, json={
                "ok": True,
                "lifecycle": "running",
                "pending_tasks": task_counter,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            log.warning("Heartbeat failed: %s", e)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
