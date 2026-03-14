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

**Agent-to-Agent** (implemented by each agent):

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/aip` | Send a message (SSE streaming by default) |
| `GET /v1/status` | Discover agent identity, skills, and capabilities |
| `GET /v1/tasks/{id}` | Query task state, progress, and artifacts |
| `POST /v1/tasks/{id}/cancel` | Cancel a running task |
| `POST /v1/tasks/{id}/send` | Send follow-up input into a task |
| `POST /v1/artifacts` | Upload a file (multipart/form-data, any type/size) |
| `GET /v1/artifacts/{id}` | Download artifact content |

**Observability & Cost** (implemented by the platform or agent):

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/traces` | Emit trace events (batch) |
| `GET /v1/traces` | Query trace events (filter by agent, type, time) |
| `GET /v1/usage` | Aggregated LLM usage and cost summary |

**Platform Registry** (implemented by the management platform):

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/registry/agents` | Register an external agent (one API call to join) |
| `GET /v1/registry/agents` | List/search registered agents |
| `PATCH /v1/registry/agents/{id}` | Update agent registration (URL, creds) |
| `DELETE /v1/registry/agents/{id}` | Deregister an agent |
| `POST /v1/registry/agents/{id}/heartbeat` | Agent heartbeat (liveness signal, with platform commands) |
| `POST /v1/registry/agents/{id}/probe` | Platform-initiated health check ("click retry") |
| `PUT /v1/registry/agents/{id}/assignment` | Update platform-assigned role, scope, constraints |

**Multi-Agent Gateway** (one process hosting N agents):

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/agents` | Discover all hosted agents |
| `GET /v1/agents/{id}/status` | Status of a specific hosted agent |
| `POST /v1/agents/{id}/aip` | Send message to a specific hosted agent |

## Zero-Config Agent Discovery

The platform can add **any agent by URL** — no bridge process, no sidecar, no extra install on the agent machine. The platform auto-detects the protocol, builds a capability profile, and handles all translation server-side.

```bash
# Add an OpenClaw instance — just its URL, nothing else
curl -X POST https://platform.example.com/v1/registry/agents \
  -H "Content-Type: application/json" \
  -d '{ "base_url": "http://192.168.1.10:3000" }'
```

The platform probes the URL, discovers it's OpenAI-compatible, and registers it. Done — visible in the dashboard, ready to receive tasks.

### Supported Protocol Profiles

| Profile | Auto-detected via | Covers |
|---------|------------------|--------|
| `aip` | `GET /v1/status` returns AgentStatus | Native AIP agents |
| `openai` | `GET /v1/models` returns model list | OpenClaw, Ollama, vLLM, LiteLLM, LM Studio, LocalAI, OpenRouter |
| `a2a` | `GET /.well-known/agent.json` | Google A2A protocol agents |
| `anthropic` | `POST /v1/messages` responds | Anthropic Claude API |

Or skip auto-detection with a hint: `{ "base_url": "...", "protocol": "openai" }`.

### Python SDK

```python
from aip import discover

result = await discover("http://192.168.1.10:3000")
print(result.protocol)       # "openai"
print(result.models)         # ["openclaw-v1"]
status = result.to_agent_status(namespace="my-team")
```

## One-Line Bridge

For agents behind NAT, on different networks, or when you want a local AIP endpoint — use the bridge:

```bash
pip install aip-protocol[bridge] && aip bridge --agent <url> --platform <url> --secret <key>
```

The bridge auto-detects the protocol from the URL scheme, exposes `GET /v1/status` + `POST /v1/aip`, registers with the platform, and starts heartbeating — all automatically.

### Real-World Examples

**OpenClaw** (local, port 18789, OpenAI-compatible):

```bash
aip bridge \
  --agent http://127.0.0.1:18789/v1/chat/completions \
  --api-format openai \
  --agent-secret "$OPENCLAW_GATEWAY_TOKEN" \
  --platform https://hive.example.com --secret sk-xxx \
  --name "OpenClaw" --tags coding,agent --color "#10B981"
```

**Ollama** (local LLM, port 11434):

```bash
aip bridge \
  --agent http://localhost:11434/v1/chat/completions \
  --api-format openai \
  --platform https://hive.example.com --secret sk-xxx \
  --name "Ollama Llama3" --tags llm,local
```

**Dify** (self-hosted or cloud):

```bash
aip bridge \
  --agent https://api.dify.ai/v1/chat-messages \
  --api-format dify \
  --agent-secret "app-YOUR_DIFY_API_KEY" \
  --platform https://hive.example.com --secret sk-xxx \
  --name "Dify Workflow" --tags workflow,chat
```

**Coze** (ByteDance, cloud):

```bash
aip bridge \
  --agent https://api.coze.com/open_api/v2/chat \
  --api-format coze \
  --agent-secret "$COZE_ACCESS_TOKEN" \
  --platform https://hive.example.com --secret sk-xxx \
  --name "Coze Bot" --tags bot,chat
```

**Any OpenAI-compatible server** (vLLM, LiteLLM, LocalAI, LM Studio, etc.):

```bash
aip bridge \
  --agent http://192.168.1.100:8000/v1/chat/completions \
  --api-format openai \
  --platform https://hive.example.com --secret sk-xxx \
  --name "GPU Server" --tags llm,inference
```

**Custom HTTP agent** (any REST endpoint):

```bash
aip bridge \
  --agent http://localhost:8080/chat \
  --platform https://hive.example.com --secret sk-xxx
```

**Subprocess** (stdin/stdout JSONL — wrap any CLI tool):

```bash
aip bridge \
  --agent "stdio:python my_agent.py" \
  --platform https://hive.example.com --secret sk-xxx \
  --name "Local Script"
```

**Behind NAT / tunnel** (ngrok, Cloudflare Tunnel, frp, etc.):

```bash
aip bridge \
  --agent http://localhost:8080 \
  --platform https://hive.example.com --secret sk-xxx \
  --public-url https://my-agent.ngrok.io
```

**Standalone mode** (no platform, just expose as AIP endpoint):

```bash
aip bridge --agent http://localhost:11434/v1/chat/completions --api-format openai --port 9090
```

### Environment Variables

All flags work as `AIP_BRIDGE_*` env vars — ideal for servers, Docker, and CI:

```bash
export AIP_BRIDGE_AGENT=http://127.0.0.1:18789/v1/chat/completions
export AIP_BRIDGE_API_FORMAT=openai
export AIP_BRIDGE_AGENT_SECRET=gw-token-xxx
export AIP_BRIDGE_PLATFORM=https://hive.example.com
export AIP_BRIDGE_SECRET=sk-xxx
export AIP_BRIDGE_NAME="OpenClaw"
aip bridge
```

### Compatibility Matrix

| Agent / Platform | `--api-format` | `--agent` URL | Notes |
|-----------------|---------------|---------------|-------|
| **OpenClaw** | `openai` | `http://127.0.0.1:18789/v1/chat/completions` | Set `--agent-secret` to gateway token |
| **Ollama** | `openai` | `http://localhost:11434/v1/chat/completions` | No auth needed for local |
| **vLLM** | `openai` | `http://host:8000/v1/chat/completions` | OpenAI-compatible |
| **LiteLLM** | `openai` | `http://host:4000/v1/chat/completions` | OpenAI-compatible proxy |
| **LM Studio** | `openai` | `http://localhost:1234/v1/chat/completions` | OpenAI-compatible |
| **LocalAI** | `openai` | `http://localhost:8080/v1/chat/completions` | OpenAI-compatible |
| **Dify** | `dify` | `https://api.dify.ai/v1/chat-messages` | Or self-hosted URL |
| **Coze** | `coze` | `https://api.coze.com/open_api/v2/chat` | Or `api.coze.cn` for China |
| **OpenAI API** | `openai` | `https://api.openai.com/v1/chat/completions` | Direct OpenAI access |
| **Anthropic API** | `anthropic` | `https://api.anthropic.com/v1/messages` | Direct Claude access |
| **Custom REST** | `generic` | `http://host:port/your/endpoint` | Expects `{"message":...}` → `{"response":...}` |
| **Custom WebSocket** | `generic` | `ws://host:port/ws` | JSON over WebSocket |
| **Subprocess** | `generic` | `stdio:python agent.py` | JSONL over stdin/stdout |
| **Any other** | `raw` | any URL | Passes AIP fields through unchanged |

<details>
<summary>All flags reference</summary>

```
aip bridge [OPTIONS]

Agent connection:
  --agent URL             Agent URL (http://, ws://, stdio:cmd)
  --agent-secret KEY      Auth token for the external agent
  --protocol http|ws|stdio  Override auto-detection
  --api-format FORMAT     generic|openai|anthropic|dify|coze|raw (default: generic)
  --timeout SEC           Agent call timeout (default: 120)

Platform registration:
  --platform URL          AIP platform URL (omit for standalone)
  --secret KEY            Shared secret for platform auth
  --heartbeat SEC         Heartbeat interval (default: 10)

Agent identity:
  --name NAME             Display name (default: hostname)
  --id ID                 Machine identifier (default: bridge-<hostname>-<port>)
  --namespace NS          Logical namespace (default: default)
  --role ROLE             Agent role (default: worker)
  --tags t1,t2            Capability tags
  --icon URL              Icon URL for dashboards
  --color HEX             Brand color (#4A90D9)

Network:
  --port PORT             Local bridge port (default: 9090)
  --host ADDR             Bind address (default: 0.0.0.0)
  --public-url URL        Public URL (for NAT/tunnel/reverse proxy)
```

Every flag has an `AIP_BRIDGE_*` env var equivalent (e.g. `AIP_BRIDGE_AGENT`).

</details>

**Multi-Agent Gateway** (all agents → one port → one platform):

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/agents` | Discover all hosted agents |
| `GET /v1/agents/{id}/status` | Status of a specific agent |
| `POST /v1/agents/{id}/aip` | Send message to a specific agent |

## Multi-Agent Gateway

Run multiple agents behind **one port** — a single process manages transport, health, registration, and routing for all of them.

### Quick Start

```bash
pip install aip-protocol[bridge] && aip bridge --config gateway.yaml
```

### Example `gateway.yaml`

```yaml
platform: https://hive.example.com
secret: sk-xxx
namespace: my-team
port: 9090

agents:
  # OpenClaw coding agent
  - id: coder
    url: http://127.0.0.1:18789/v1/chat/completions
    format: openai
    secret: gw-token-xxx
    name: OpenClaw Coder
    tags: [coding, reasoning]
    color: "#10B981"

  # Local Ollama LLM
  - id: llama
    url: http://localhost:11434/v1/chat/completions
    format: openai
    name: Ollama Llama3
    tags: [llm, general]
    color: "#3B82F6"

  # Dify workflow
  - id: workflow
    url: https://api.dify.ai/v1/chat-messages
    format: dify
    secret: app-xxx
    name: Dify Workflow
    tags: [workflow, automation]
    color: "#8B5CF6"

  # Coze bot
  - id: bot
    url: https://api.coze.com/open_api/v2/chat
    format: coze
    secret: pat-xxx
    name: Coze Bot
    tags: [bot, chat]
    color: "#F59E0B"
```

### What Happens

1. One FastAPI process starts on port 9090.
2. Each agent gets an independent transport, health check, and heartbeat.
3. The platform sees N separate agents — it doesn't know or care they're behind one gateway.
4. If one backend goes down, the others keep running.

### Endpoints

```
GET  /v1/agents              → list all agents with status
GET  /v1/agents/coder/status → specific agent status
POST /v1/agents/coder/aip    → message to coder
GET  /v1/status              → GroupStatus (all agents)
POST /v1/aip                 → route by "to" field
GET  /health                 → {"ok": true, "agents": {"coder":"running","llama":"running",...}}
```

### Per-Agent Config

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `id` | yes | — | Unique agent identifier |
| `url` | yes | — | Backend URL (HTTP, WebSocket, or `stdio:cmd`) |
| `format` | no | `generic` | API format: `generic`, `openai`, `anthropic`, `dify`, `coze`, `raw` |
| `secret` | no | — | Auth token for the backend agent |
| `name` | no | id | Human-readable display name |
| `role` | no | `worker` | Agent role |
| `namespace` | no | (gateway) | Override gateway-level namespace |
| `tags` | no | `[]` | Capability tags |
| `color` | no | — | Brand color hex for dashboards |
| `icon` | no | — | Icon URL |
| `timeout` | no | `120` | Backend call timeout (seconds) |
| `protocol` | no | auto | Force protocol: `http`, `ws`, `stdio` |

### CLI Overrides

Config-file values can be overridden from the command line:

```bash
aip bridge --config gateway.yaml --port 8080 --namespace production --secret sk-prod-xxx
```

---

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
│   ├── minimal-python/            # Simplest AIP agent
│   ├── minimal-typescript/        # TS wire-format example
│   └── adapter-python/            # Wrap ANY agent into AIP (copy & edit 3 functions)
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
