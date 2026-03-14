# AIP — What's Done, What's Not, What's Next

> **Target**: the most adopted agent-to-agent protocol on the planet.
> Agents talk to agents. Agents report to humans. Humans watch it all on a multi-agent platform.
> Any external agent can plug in with one API call.

---

## The 30-second picture

```
                          ┌──────────────────────────────────┐
                          │     AIP Management Platform      │
   Human (browser)────────│  /v1/registry/agents  (register) │
                          │  /v1/status?scope=group (view)   │
                          └──────┬────────┬────────┬─────────┘
                                 │        │        │
          ┌──────────────────────┘        │        └──────────────────────┐
          ▼                               ▼                              ▼
   ┌─────────────┐                ┌──────────────┐              ┌──────────────┐
   │ Coordinator  │  POST /v1/aip │ AIP Adapter   │  native API │  Open Claw   │
   │ (native AIP) │◄────────────►│ (thin wrapper) │◄───────────►│  Manus, etc. │
   └──┬───┬───┬──┘               └──────────────┘              └──────────────┘
      │   │   │
      ▼   ▼   ▼                  ← each has GET /v1/status (presentation, skills, auth)
   Backend  Frontend  QA         ← each sends heartbeats to platform
```

---

## How an external agent joins the platform

### Step 1: Agent (or its adapter) registers — ONE API call

```bash
curl -X POST https://platform.example.com/v1/registry/agents \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "https://my-agent.example.com",
    "namespace": "acme-corp"
  }'
```

The platform probes `GET https://my-agent.example.com/v1/status`, validates it, and responds:

```json
{
  "agent_id": "my-agent",
  "base_url": "https://my-agent.example.com",
  "namespace": "acme-corp",
  "registered_at": "2026-03-12T10:00:00Z",
  "status": "active",
  "heartbeat_interval_seconds": 10,
  "heartbeat_url": "https://platform.example.com/v1/registry/agents/my-agent/heartbeat"
}
```

Done. The agent is now visible in the platform dashboard.

### Step 2: Agent sends heartbeats (stays alive)

```bash
curl -X POST https://platform.example.com/v1/registry/agents/my-agent/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"ok": true, "lifecycle": "running", "pending_tasks": 2}'
```

Miss 3× interval → degraded. Miss 10× → failed.

### Step 3: Platform and other agents can now talk to it

```bash
curl -N http://my-agent.example.com/v1/aip \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"version":"1.0","message_id":"msg-001","from":"coordinator","to":"my-agent","action":"assign_task","intent":"Analyze Q1 sales data"}'
```

---

## For agents that DON'T speak AIP natively (the adapter pattern)

```
┌──────────────┐     AIP protocol     ┌──────────────┐     Native API     ┌───────────────┐
│  AIP Platform │◄───────────────────►│  AIP Adapter   │◄────────────────►│  Any Agent     │
│               │  /v1/aip, /v1/status│  (your code)   │  /chat, /run     │  (OpenAI, etc.)│
└──────────────┘                      └──────────────┘                    └───────────────┘
```

See `examples/adapter-python/adapter.py` — a complete, copy-paste-ready adapter.
Edit 3 functions, run it, your agent is on AIP:

```python
def get_agent_skills():       # ✏️ what can your agent do?
def get_agent_presentation(): # ✏️ how should it look in UIs?
async def call_external_agent(intent, payload):  # ✏️ translate AIP → your agent's API
```

```bash
EXTERNAL_AGENT_URL=http://localhost:5000 \
PLATFORM_URL=https://platform.example.com \
python adapter.py
```

It auto-registers with the platform and starts heartbeating. Zero config.

---

## Real interaction examples

### Human tells coordinator to do something (SSE streaming)

```bash
curl -N http://coordinator.example.com/v1/aip \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"version":"1.0","message_id":"msg-001","from":"user","to":"coordinator","from_role":"user","action":"user_instruction","intent":"Design the order service API","priority":"high"}'
```

```
event: status
data: {"task_id":"task-001","state":"working","progress":0.3}

event: artifact
data: {"artifact_id":"art-001","name":"orders-api.yaml","mime_type":"application/yaml","uri":"https://coordinator.example.com/v1/artifacts/art-001"}

event: done
data: {"ok":true,"message_id":"msg-001","to":"coordinator","status":"received","task_id":"task-001"}
```

### Dashboard fetches all agent cards

```bash
curl http://platform.example.com/v1/registry/agents?namespace=acme-corp
```

Returns list of agents, each with `cached_status` containing full `presentation` (display_name, icon, color, tagline, provider) — ready to render as cards.

### Upload a file

```bash
curl -X POST http://agent.example.com/v1/artifacts -F "file=@report.pdf" -F "task_id=task-001"
```

### Agent needs human approval

```json
{ "action": "request_approval", "requires_approval": true, "approval_state": "waiting_human" }
```

---

## Completion status

### P0 — Without these, nobody adopts it

| # | Gap | Status |
|---|-----|--------|
| 1 | No streaming | ✅ SSE default + JSON opt-out |
| 2 | No task lifecycle | ✅ Full Task API + 6-state machine |
| 3 | Weak agent cards | ✅ Skill schema with I/O schemas |
| 4 | Python-only SDK | ✅ Python + Go + Java + JS/TS |

### P1 — Blocks enterprise and platform adoption

| # | Gap | Status |
|---|-----|--------|
| 5 | No auth standard | ✅ AuthenticationInfo |
| 6 | No file transfer | ✅ `POST /v1/artifacts` multipart + inline base64 |
| 7 | No error codes | ✅ 27-code registry |
| 8 | No rate limiting | ✅ RateLimitInfo + headers |
| 9 | No human-facing display | ✅ Presentation (display_name, icon, color, locale, provider) |
| 10 | No multi-tenancy | ✅ namespace + isolation rules |
| 11 | No agent onboarding | ✅ Agent Registry Protocol (register/heartbeat/list) + Adapter Pattern |

### P1.5 — Observability & Cost (new)

| # | Gap | Status |
|---|-----|--------|
| 12 | No trace event standard | ✅ TraceEvent schema + TraceType registry (18 standard types) |
| 13 | No LLM cost tracking | ✅ LLMUsage + UsageSummary + per-model/per-agent breakdown |
| 14 | No trace endpoints | ✅ `POST /v1/traces`, `GET /v1/traces`, `GET /v1/usage` |
| 15 | Task lacks trace linkage | ✅ `trace_id`, `correlation_id`, `parent_task_id` on AIPTask |

### P2 — Developer experience and ecosystem

| # | Gap | Status |
|---|-----|--------|
| 16 | No JSON-RPC compat | ✅ Bidirectional bridge |
| 17 | No payload schemas for standard actions | ⚠️ Per-skill only |
| 18 | No webhooks | ✅ callback_url + HMAC |
| 19 | No docs site / playground | ❌ |
| 20 | No idempotency | ✅ Idempotency-Key |
| 21 | No conformance certification | ❌ |

---

## Scoreboard

```
P0    ████████████████████  4/4
P1    ████████████████████  7/7
P1.5  ████████████████████  4/4   ← observability & cost tracking
P2    ██████████████░░░░░░  4/6
```

**What's left:**

1. Standard action payload schemas
2. Documentation site + interactive playground
3. Conformance test suite expansion + certification badge
4. Polish: callback_secret, RFC 7807, W3C trace alignment, 1.0 GA

---

## All endpoints

```
# Agent-to-Agent (implemented by each agent)
POST   /v1/aip                              Send a message (SSE default)
GET    /v1/status                            Agent discovery + presentation
GET    /v1/tasks/{id}                        Task state
POST   /v1/tasks/{id}/cancel                 Cancel task
POST   /v1/tasks/{id}/send                   Follow-up into task
POST   /v1/artifacts                         Upload file (multipart)
GET    /v1/artifacts/{id}                    Download file

# Observability & Cost (implemented by the platform or agent)
POST   /v1/traces                            Emit trace events (batch)
GET    /v1/traces                            Query trace events (filter/paginate)
GET    /v1/traces/{event_id}                 Get single trace event
GET    /v1/usage                             Aggregated LLM usage & cost summary

# Platform Onboarding (implemented by the management platform)
POST   /v1/registry/agents                   Register (handshake + capability detect)
GET    /v1/registry/agents                   List/search (filter by namespace/role/skill/q)
GET    /v1/registry/agents/{id}              Get record + cached status
PATCH  /v1/registry/agents/{id}              Update (migrate URL, rotate creds)
DELETE /v1/registry/agents/{id}              Deregister (graceful)
POST   /v1/registry/agents/{id}/heartbeat    Heartbeat (10s, with platform commands)
POST   /v1/registry/agents/{id}/probe        Platform-initiated health check ("click retry")
PUT    /v1/registry/agents/{id}/assignment   Update platform-assigned role/scope/constraints

# Multi-Agent Gateway (one process → N agents)
GET    /v1/agents                            Discover all hosted agents
GET    /v1/agents/{id}/status                Status of a specific hosted agent
POST   /v1/agents/{id}/aip                   Send message to a specific hosted agent
```

## Agent onboarding in one picture

```
Agent starts
  │
  ▼
POST /v1/registry/agents { base_url, credentials, mode }
  │
  ├── Platform probes GET {base_url}/v1/status  (mutual auth)
  ├── Validates: schema ✓  version compat ✓  namespace ✓  quota ✓
  ├── Detects capabilities: status, messaging, streaming, tasks, artifacts
  │
  ▼
201 Created { agent_id, heartbeat_url, heartbeat_interval: 10, capabilities_detected }
  │
  ▼
Agent heartbeats every 10s ──► Platform responds with { ack, commands[] }
  │                              commands: refresh_status, drain, shutdown,
  │                                        update_config, re_register, assign
  │
  ▼
Miss 3× ──► degraded     Miss 10× ──► failed (auto-deregister)
Resume  ──► recovered    Platform emits events: agent.registered/.degraded/.failed/.recovered
POST probe ──► instant recovery (platform "click retry" → re-checks agent health)
```

---

## What's new in recent versions

### v1.2.0 — Multi-Agent Gateway
One process on one port hosts N agents. Per-agent routing, discovery, and aggregated GroupStatus.
```bash
aip bridge --config gateway.yaml   # starts gateway with all agents
```

### v1.2.1 — Production Resilience
- HTTP retry with exponential backoff
- WebSocket auto-reconnect
- Stdio subprocess auto-restart
- Circuit breaker pattern in gateway
- Graceful shutdown with deregistration

### v1.3.0 — Probe Endpoint + SDK Sync
- `POST /v1/registry/agents/{id}/probe` — platform "click retry" for instant recovery
- Go, Java, JS/TS SDKs synchronized to full type parity

### v1.4.0 — Agent Assignment Protocol
- `AgentAssignment` schema: `assigned_role`, `team`, `scope`, `granted_tools`, `constraints`, `supervisor`
- Each agent has two identities: native profile + platform assignment
- Three delivery mechanisms: registration response, heartbeat `assign` command, `PUT /assignment` endpoint
- All SDKs updated
