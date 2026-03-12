<p align="center">
  <h1 align="center">Agent Interaction Protocol (AIP)</h1>
  <p align="center">
    <strong>The open standard for agent-to-agent communication.</strong>
  </p>
  <p align="center">
    <a href="spec/specification.md">Specification</a> &middot;
    <a href="sdk-python/">Python SDK</a> &middot;
    <a href="sdk-go/">Go SDK</a> &middot;
    <a href="sdk-java/">Java SDK</a> &middot;
    <a href="sdk-js/">JS/TS SDK</a> &middot;
    <a href="spec/openapi.yaml">OpenAPI</a>
  </p>
</p>

---

## What is AIP?

**AIP (Agent Interaction Protocol)** is an open standard for structured communication between autonomous AI agents. It defines a universal wire format for agent-to-agent messaging, streaming task execution, and a self-describing discovery mechanism.

> **MCP solved "how does an AI call tools."**
> **AIP solves "how do AIs talk to each other."**

AIP is to agent collaboration what HTTP is to web communication: a universal, composable protocol that any system can implement regardless of language, framework, or deployment model.

## Why AIP?

| Problem | AIP's Answer |
|---------|-------------|
| No standard for agent-to-agent messaging | Unified JSON envelope with `POST /v1/aip` |
| Agents can't discover each other | Rich `GET /v1/status` with skills, auth schemes, and recursive topology |
| No streaming for long-running tasks | SSE streaming by default, JSON fallback with `Accept` header switch |
| No task lifecycle management | Full Task API: create, query, cancel, send follow-ups |
| No governance for autonomous agents | Built-in approval workflows, authority weights, constraints |
| No observability across agent networks | First-class trace IDs, correlation IDs, latency tracking |
| Existing protocols are framework-locked | SDKs for Python, Go, Java, and JS/TS |

## Core Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/aip` | Send a message (SSE streaming by default) |
| `GET /v1/status` | Discover agent identity, skills, and capabilities |
| `GET /v1/tasks/{id}` | Query task state, progress, and artifacts |
| `POST /v1/tasks/{id}/cancel` | Cancel a running task |
| `POST /v1/tasks/{id}/send` | Send follow-up input into a task |
| `POST /v1/artifacts` | Upload a file (multipart/form-data, any type/size) |
| `GET /v1/artifacts/{id}` | Download artifact content |

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
print(ack["task_id"])  # Track the task
```

### Go

```go
import aip "github.com/aip-protocol/aip/sdk-go"

client := aip.NewClient("http://localhost:8000")
msg := aip.BuildMessage("user", "agent-backend", aip.ActionAssignTask, "Design the API")
ack, _ := client.Send(ctx, msg)

// Or stream progress:
stream, _ := client.SendStream(ctx, msg)
defer stream.Close()
for {
    event, err := stream.Next()
    if err != nil { break }
    fmt.Println(event.Event, event.Data)
}
```

### JavaScript / TypeScript

```typescript
import { AIPClient, buildMessage } from "@aip-protocol/sdk";

const client = new AIPClient("http://localhost:8000");
const msg = buildMessage({
  from: "user", to: "agent-backend",
  action: "assign_task", intent: "Design the API",
});

// Streaming (default)
for await (const event of client.sendStream(msg)) {
  console.log(event.event, event.data);
}

// Or non-streaming
const ack = await client.send(msg);
```

### Java

```java
var client = new AIPClient("http://localhost:8000");
var msg = AIPMessage.builder("user", "agent-backend", "assign_task", "Design the API").build();
AIPAck ack = client.send(msg);
```

### Any Language (just HTTP + JSON)

```bash
# Streaming (default)
curl -N -X POST http://agent.example.com/v1/aip \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"version":"1.0","message_id":"msg-001","from":"user","to":"agent-backend","action":"assign_task","intent":"Design the API"}'

# Non-streaming
curl -X POST http://agent.example.com/v1/aip \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"version":"1.0","message_id":"msg-001","from":"user","to":"agent-backend","action":"assign_task","intent":"Design the API"}'
```

## Streaming by Default

AIP uses **Server-Sent Events (SSE)** as the default response mode. Long-running agent tasks stream real-time progress:

```
event: status
data: {"task_id":"task-001","state":"working","progress":0.3}

event: message
data: {"intent":"Partial result: endpoint list complete"}

event: artifact
data: {"artifact_id":"art-001","name":"orders-api.yaml","mime_type":"application/yaml","uri":"/artifacts/art-001"}

event: done
data: {"ok":true,"message_id":"msg-001","to":"agent-backend","status":"received","task_id":"task-001"}
```

Opt out of streaming with `Accept: application/json` or `?stream=false`.

## Task Lifecycle

Tasks track long-running agent work with a complete state machine:

```
submitted → working → completed
               ├──→ input-required → working
               ├──→ failed
               └──→ canceled
```

Query, cancel, or send follow-up input at any time via the Task API.

## Rich Agent Discovery

Agents describe their capabilities with **structured skills** (aligned with A2A Agent Card):

```json
{
  "agent_id": "agent-backend",
  "role": "backend_engineer",
  "namespace": "acme-corp",
  "presentation": {
    "display_name": "Backend Engineer",
    "tagline": "Designs and reviews REST APIs with OpenAPI output",
    "icon_url": "https://cdn.example.com/agents/backend-eng.png",
    "color": "#4A90D9",
    "locale": "en",
    "categories": ["engineering", "backend"],
    "provider": { "name": "Acme Corp", "url": "https://acme.example.com" }
  },
  "skills": [
    {
      "id": "api-design",
      "name": "REST API Design",
      "description": "Design RESTful APIs with OpenAPI output",
      "tags": ["backend", "api"],
      "input_modes": ["application/json", "text/plain"],
      "output_modes": ["application/json", "application/yaml"],
      "input_schema": { "type": "object", "properties": { "instruction": { "type": "string" } } }
    }
  ],
  "authentication": { "schemes": ["bearer", "oauth2"] },
  "supported_versions": ["1.0"]
}
```

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
├── sdk-python/                    # Python SDK
├── sdk-go/                        # Go SDK
├── sdk-java/                      # Java SDK
├── sdk-js/                        # JavaScript/TypeScript SDK
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
| **Discovery** | Server manifest | Agent Card | Recursive `GET /status` + Skill schemas |
| **Streaming** | SSE (tool results) | SSE | SSE (default, with opt-out) |
| **Task Management** | None | Task lifecycle | Full Task API (query, cancel, follow-up) |
| **Governance** | None | None | Built-in (approval, authority, constraints) |
| **Topology** | Flat | Flat | Recursive (trees, hierarchies) |
| **Observability** | Minimal | Minimal | First-class (trace, correlation, latency) |
| **SDKs** | Python, TS | Python, Go, JS, Java, .NET | Python, Go, Java, JS/TS |
| **Versioning** | None | JSON-RPC | URL path (`/v1/`) |
| **Transport** | stdio/SSE | HTTP (JSON-RPC 2.0) | HTTP (pluggable to WS, gRPC, MQ) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Proposing protocol changes (RFC process)
- Contributing SDK code
- Adding examples and integrations
- Reporting issues

## License

Apache License 2.0 — see [LICENSE](LICENSE).
