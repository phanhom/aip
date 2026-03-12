#!/usr/bin/env python3
"""AIP in 5 minutes — send your first agent-to-agent message.

1. pip install aip-protocol
2. python example.py

This example shows:
  - Building an AIP message
  - Serializing to wire format
  - Sending to a target agent (requires a running AIP endpoint)
  - Parsing the acknowledgment
"""

from aip import AIPAction, build_message, send

# ── 1. Build a message ──────────────────────────────────────────────

msg = build_message(
    from_agent="user",
    to="agent-backend",
    action=AIPAction.assign_task,
    intent="Design the order service REST API",
    payload={
        "instruction": "Define REST endpoints, error codes, and schemas",
        "deliverables": ["openapi", "risk_report"],
    },
    priority="high",
)

# ── 2. Inspect the wire format ──────────────────────────────────────

wire = msg.to_wire()
print("Wire format:")
import json

print(json.dumps(wire, indent=2, default=str))

# ── 3. Send to a target agent ──────────────────────────────────────
# Uncomment below when you have an AIP-compliant server running.

# ack = send(base_url="http://localhost:8000", message=msg)
# print(f"\nAck: {ack}")

# ── 4. Build a report message back ─────────────────────────────────

report = build_message(
    from_agent="agent-backend",
    to="user",
    action=AIPAction.submit_report,
    intent="Order service API draft completed",
    payload={
        "summary": "API draft complete, pending auth strategy confirmation",
        "artifacts": ["openapi/orders.yaml"],
        "blockers": ["auth strategy not confirmed"],
    },
    correlation_id=msg.message_id,
    trace_id=msg.trace_id,
    status="Completed",
)

print("\nReport wire format:")
print(json.dumps(report.to_wire(), indent=2, default=str))
