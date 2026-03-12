<p align="center">
  <h1 align="center">Agent Interaction Protocol (AIP)</h1>
  <p align="center">
    <strong>The open standard for agent-to-agent communication.</strong>
  </p>
  <p align="center">
    <a href="spec/specification.md">Specification</a> &middot;
    <a href="sdk-python/">Python SDK</a> &middot;
    <a href="examples/">Examples</a> &middot;
    <a href="spec/schemas/">JSON Schemas</a> &middot;
    <a href="spec/openapi.yaml">OpenAPI</a>
  </p>
</p>

---

## What is AIP?

**AIP (Agent Interaction Protocol)** is an open standard for structured communication between autonomous AI agents. It defines a universal wire format for agent-to-agent messaging and a self-describing discovery mechanism.

> **MCP solved "how does an AI call tools."**
> **AIP solves "how do AIs talk to each other."**

AIP is to agent collaboration what HTTP is to web communication: a universal, composable protocol that any system can implement regardless of language, framework, or deployment model.

## Why AIP?

| Problem | AIP's Answer |
|---------|-------------|
| No standard for agent-to-agent messaging | Unified JSON envelope with `POST /aip` |
| Agents can't discover each other | Self-describing `GET /status` with recursive topology |
| No governance for autonomous agents | Built-in approval workflows, authority weights, constraints |
| No observability across agent networks | First-class trace IDs, correlation IDs, latency tracking |
| Existing protocols are framework-locked | Transport-agnostic, language-agnostic, framework-agnostic |

## Two Endpoints, One Protocol

AIP is intentionally minimal. Every AIP-compliant agent implements exactly two endpoints:

| Endpoint | Purpose |
|----------|---------|
| `POST /aip` | Send a structured message to an agent |
| `GET /status` | Discover agent identity, health, and capabilities |

That's it. No complex handshakes, no session management, no proprietary transports.

## Quick Start

### Python

```bash
pip install aip-protocol
```

```python
from aip import AIPAction, build_message, send

msg = build_message(
    from_agent="user",
    to="agent-backend",
    action=AIPAction.assign_task,
    intent="Design the order service API",
)

ack = send(base_url="http://localhost:8000", message=msg)
```

### Any Language (just HTTP + JSON)

```bash
curl -X POST http://agent.example.com/aip \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.0",
    "message_id": "msg-001",
    "from": "user",
    "to": "agent-backend",
    "action": "assign_task",
    "intent": "Design the order service API",
    "payload": {"instruction": "Define REST endpoints and schemas"}
  }'
```

## Message Format

Every AIP message is a JSON envelope with four layers:

```
┌─────────────────────────────────────────────────┐
│  Protocol Layer                                  │
│  version, message_id, from, to, route_scope     │
├─────────────────────────────────────────────────┤
│  Execution Layer                                 │
│  action, intent, payload, constraints, priority  │
├─────────────────────────────────────────────────┤
│  Governance Layer                                │
│  authority_weight, approval_state                │
├─────────────────────────────────────────────────┤
│  Observability Layer                             │
│  trace_id, correlation_id, latency_ms, errors   │
└─────────────────────────────────────────────────┘
```

## Discovery

Any AIP agent can be discovered via `GET /status`:

```json
{
  "agent_id": "agent-backend",
  "role": "backend_engineer",
  "lifecycle": "running",
  "ok": true,
  "base_url": "https://agent-backend.example.com",
  "endpoints": {
    "aip": "https://agent-backend.example.com/aip",
    "status": "https://agent-backend.example.com/status"
  },
  "capabilities": ["assign_task", "submit_report"],
  "supported_versions": ["1.0"]
}
```

Coordinators return recursive topology — discover an entire agent network from a single status call.

## Standard Actions

| Action | Description |
|--------|-------------|
| `assign_task` | Delegate a task to another agent |
| `submit_report` | Submit a result or progress report |
| `request_context` | Request information from another agent |
| `request_approval` | Request human or supervisor approval |
| `handoff` | Transfer task responsibility |
| `escalate` | Escalate an issue to a higher authority |
| `user_instruction` | A directive from a human user |
| ... | [Full list in the specification](spec/specification.md#42-standard-actions) |

Custom actions are supported with `x-<org>/<name>` prefix.

## Governance Built In

Unlike other protocols, AIP treats governance as a first-class concern:

- **`authority_weight`** — organizational authority level (0-100)
- **`requires_approval`** — flag actions that need human sign-off
- **`approval_state`** — track the approval lifecycle
- **`constraints`** — attach policy and deadline constraints to any message

## Repository Structure

```
aip/
├── spec/                          # Protocol specification
│   ├── specification.md           # Full spec (RFC-style)
│   ├── openapi.yaml               # OpenAPI 3.1 description
│   └── schemas/                   # JSON Schema files
│       ├── message.schema.json
│       ├── ack.schema.json
│       └── status.schema.json
├── sdk-python/                    # Python SDK (reference implementation)
│   ├── src/aip/                   # Package source
│   ├── tests/                     # Test suite
│   └── pyproject.toml
├── examples/                      # Quick-start examples
│   ├── minimal-python/
│   └── minimal-typescript/
├── conformance/                   # Conformance test suite
├── LICENSE
├── CONTRIBUTING.md
└── README.md
```

## Comparison with Other Protocols

| | MCP | Google A2A | AIP |
|---|---|---|---|
| **Focus** | Model ↔ Tool | Agent ↔ Agent | Agent ↔ Agent |
| **Discovery** | Server manifest | Agent Card | Recursive `GET /status` |
| **Governance** | None | None | Built-in (approval, authority, constraints) |
| **Topology** | Flat | Flat | Recursive (trees, hierarchies) |
| **Status** | None | Task status | Full agent lifecycle + work snapshot |
| **Observability** | Minimal | Minimal | First-class (trace, correlation, latency) |
| **Transport** | stdio/SSE | HTTP | HTTP (pluggable to WS, gRPC, MQ) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Proposing protocol changes (RFC process)
- Contributing SDK code
- Adding examples and integrations
- Reporting issues

## License

Apache License 2.0 — see [LICENSE](LICENSE).
