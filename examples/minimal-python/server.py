#!/usr/bin/env python3
"""Minimal AIP-compliant server — the simplest possible agent.

    pip install aip-protocol fastapi uvicorn
    python server.py

This creates an agent that:
  - Accepts AIP messages at POST /aip
  - Exposes status at GET /status
  - Logs incoming messages
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from aip import AIPAck, AIPMessage, AgentStatus, StatusEndpoints

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("aip-agent")

app = FastAPI(title="Minimal AIP Agent")

AGENT_ID = "my-agent"
AGENT_ROLE = "worker"
BASE_URL = "http://localhost:8000"

messages: list[dict] = []


@app.post("/aip")
async def receive_message(request: Request):
    body = await request.json()
    msg = AIPMessage(**body)

    log.info("Received: action=%s from=%s intent=%s", msg.action, msg.from_agent, msg.intent)
    messages.append(msg.to_wire())

    return AIPAck(
        ok=True,
        message_id=msg.message_id,
        to=AGENT_ID,
        status="received",
        correlation_id=msg.correlation_id,
    ).model_dump()


@app.get("/status")
async def get_status():
    return AgentStatus(
        agent_id=AGENT_ID,
        role=AGENT_ROLE,
        lifecycle="running",
        ok=True,
        base_url=BASE_URL,
        endpoints=StatusEndpoints(
            aip=f"{BASE_URL}/aip",
            status=f"{BASE_URL}/status",
        ),
        capabilities=["assign_task", "submit_report", "request_context"],
        supported_versions=["1.0"],
        pending_tasks=len(messages),
        last_message_at=datetime.now(timezone.utc).isoformat() if messages else None,
        last_seen_at=datetime.now(timezone.utc).isoformat(),
    ).model_dump()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
