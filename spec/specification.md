# Agent Interaction Protocol (AIP) Specification

**Version:** 1.0.0
**Status:** Draft
**Date:** 2026-03-12

---

## Abstract

The Agent Interaction Protocol (AIP) is an open standard for structured communication between autonomous AI agents. It defines a unified wire format for agent-to-agent messaging and a discovery mechanism for agent status and capabilities. AIP is transport-agnostic, governance-aware, and designed for recursive multi-agent topologies.

AIP is to agent collaboration what HTTP is to web communication: a universal, composable protocol that any system can implement regardless of language, framework, or deployment model.

---

## 1. Introduction

### 1.1 Motivation

As AI agents become increasingly autonomous and collaborative, the ecosystem lacks a standard protocol for agents to communicate with each other. Existing protocols address model-to-tool connections (MCP) or model-to-API integration, but none provide a first-class standard for **agent-to-agent interaction** with built-in governance, discovery, and observability.

AIP fills this gap by defining:

- **Messaging Protocol** — a structured JSON envelope for agent-to-agent and human-to-agent communication via `POST /v1/aip`.
- **Status Protocol** — a self-describing discovery mechanism via `GET /v1/status` that enables zero-configuration agent discovery.

### 1.2 Design Goals

| Goal | Description |
|------|-------------|
| **Unified** | Humans, coordinators, and workers use the same wire format. No protocol branching. |
| **Addressable** | Same-host and cross-host addressing without a central registry. |
| **Discoverable** | A single `GET /status` call reveals all downstream agent endpoints. |
| **Recursive** | Any node can return its own status plus all subordinates as a recursive tree. |
| **Governance-aware** | Approval workflows, authority weights, and constraints are first-class protocol fields. |
| **Observable** | Trace IDs, correlation IDs, latency, and error codes built into every message. |
| **Evolvable** | New fields and actions are additive and backward-compatible. |
| **Transport-agnostic** | Specified over HTTP+JSON; extensible to WebSocket, gRPC, or message queues. |

### 1.3 Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

### 1.4 Terminology

| Term | Definition |
|------|-----------|
| **Agent** | An autonomous entity that can send and receive AIP messages. May be an AI model, a service, or a human proxy. |
| **Coordinator** | An agent that decomposes tasks and delegates to other agents. |
| **Worker** | An agent that executes tasks and reports results. |
| **Group** | A collection of agents under a common coordinator, forming a logical unit. |
| **Message** | A single AIP JSON envelope sent via `POST /aip`. |
| **Status** | A JSON document describing an agent's identity, lifecycle, and capabilities, served via `GET /status`. |

---

## 2. Transport Layer

### 2.1 Default Transport: HTTP + JSON

The default transport for AIP is HTTP with JSON request and response bodies.

- Messaging endpoint: `POST /v{major}/aip`
- Status endpoint: `GET /v{major}/status`
- Content-Type: `application/json`
- Character encoding: UTF-8

For protocol version `1.x`, the endpoints are:

- `POST /v1/aip`
- `GET /v1/status`

Implementations MAY support additional transports (WebSocket, gRPC, NATS, etc.) provided the message semantics defined in this specification are preserved.

### 2.2 URL Path Versioning

AIP uses **URL path versioning** to enable safe, independent evolution of the protocol — following the same pattern as OpenAI (`/v1/...`), Stripe, and other widely adopted APIs.

**Rules:**

- The path prefix MUST be `/v{MAJOR}` where `{MAJOR}` is the protocol major version number (e.g., `/v1`, `/v2`).
- The major version in the URL path MUST correspond to the `version` field in the message envelope. A `v1` endpoint MUST accept messages with `"version": "1.x"`.
- Servers MAY serve multiple major versions simultaneously (e.g., `/v1/aip` and `/v2/aip`) during migration periods.
- When a new major version is released, the previous major version SHOULD remain available for at least 12 months with a deprecation notice.
- Servers SHOULD return HTTP `410 Gone` for sunset versions.
- Discovery endpoints (`GET /v1/status`) MUST include a `supported_versions` field listing all active major versions.

**Backward Compatibility:**

For backward compatibility with pre-versioned deployments, servers MAY also accept requests at the unversioned paths (`/aip`, `/status`). When unversioned paths are supported, they MUST behave identically to the latest stable major version. Implementations SHOULD log a deprecation warning for unversioned access.

### 2.3 Streaming (Server-Sent Events)

AIP supports **streaming responses** via Server-Sent Events (SSE). Streaming is the **default** response mode for `POST /v1/aip` — this enables real-time progress updates for long-running agent tasks.

**Request header to control streaming:**

| Header | Value | Behavior |
|--------|-------|----------|
| `Accept: text/event-stream` | (default) | Server streams SSE events as the task progresses, ending with a final `AIPAck`. |
| `Accept: application/json` | opt-out | Server returns a single JSON `AIPAck` (non-streaming, synchronous mode). |

Clients MAY also pass the query parameter `?stream=false` to disable streaming.

**SSE Event Types:**

| Event | Data | Description |
|-------|------|-------------|
| `status` | `{"task_id": "...", "state": "working", "progress": 0.3}` | Task progress update. |
| `message` | Partial `AIPMessage` JSON | Intermediate result or partial output from the agent. |
| `artifact` | `{"artifact_id": "...", "name": "...", "mime_type": "...", "uri": "..."}` | An artifact produced during task execution. |
| `error` | `{"error_code": "...", "error_message": "..."}` | An error occurred during processing. |
| `done` | Full `AIPAck` JSON | Final acknowledgment. Stream ends after this event. |

**SSE Format (per the W3C SSE specification):**

```
event: status
data: {"task_id":"task-001","state":"working","progress":0.3}

event: message
data: {"intent":"Partial result: API endpoint list complete"}

event: done
data: {"ok":true,"message_id":"msg-001","to":"agent-backend","status":"received","task_id":"task-001"}

```

**Server requirements:**

- Servers MUST support streaming as the default mode.
- Servers MUST support `Accept: application/json` for non-streaming clients.
- If the server does not support streaming, it MUST return a single `AIPAck` with `Content-Type: application/json` regardless of the request `Accept` header.
- Servers MUST send `event: done` as the last SSE event before closing the stream.

### 2.4 HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Message accepted. Response body is an `AIPAck` (JSON) or SSE stream. |
| `400` | Routing error (e.g., `to` does not match the receiving agent). |
| `401` | Authentication required. |
| `403` | Forbidden (insufficient authority or approval). |
| `422` | Message validation failed. |
| `429` | Rate limited. |
| `503` | Upstream or forwarding target unavailable. |

### 2.5 TLS

Implementations SHOULD use TLS for cross-network communication. Same-host communication MAY use plain HTTP.

---

## 3. Addressing and Discovery

### 3.1 Address Resolution

An agent's address is determined by the URL of the request target. The message body does not carry the receiver's address for same-host communication. For cross-host routing, the `to_base_url` field in the message provides the target agent's base URL.

**Resolution priority** (highest to lowest):

1. `to_base_url` field in the message body
2. `base_url` from a previously fetched `GET /status` response
3. Implementation-specific default address resolution

### 3.2 Self-Describing Status

Every AIP-compliant agent MUST expose `GET /v1/status` and SHOULD include the following discovery fields in its response:

| Field | Type | Description |
|-------|------|-------------|
| `base_url` | string \| null | The base URL where this agent can be reached. |
| `endpoints.aip` | string \| null | Full URL of the messaging endpoint. |
| `endpoints.status` | string \| null | Full URL of the status endpoint. |

This enables **zero-configuration discovery**: a caller fetches status once and knows where to send subsequent messages.

### 3.3 No Central Registry Required

AIP does not require a central service registry. Agents discover each other through status endpoints. A coordinator agent's status response includes information about its subordinates, enabling recursive discovery of entire agent topologies.

---

## 4. Messaging Protocol

### 4.1 Message Envelope (`AIPMessage`)

Every AIP message is a JSON object with the following fields, organized into four layers.

#### 4.1.1 Protocol Layer

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `version` | string | REQUIRED | `"1.0"` | Protocol version. |
| `message_id` | string | REQUIRED | (UUID) | Globally unique message identifier. |
| `correlation_id` | string \| null | OPTIONAL | `null` | Links request-response pairs across messages. |
| `trace_id` | string \| null | OPTIONAL | `null` | End-to-end distributed trace identifier. |
| `parent_task_id` | string \| null | OPTIONAL | `null` | Identifier of the parent task that spawned this message. |
| `from` | string | REQUIRED | — | Sender identifier. Agent ID or `"user"`. |
| `to` | string | REQUIRED | — | Receiver agent ID. Use `"*"` for broadcast. |
| `from_role` | string \| null | OPTIONAL | `null` | Sender's role (e.g., `"coordinator"`, `"engineer"`, `"user"`). |
| `to_role` | string \| null | OPTIONAL | `null` | Expected role of the receiver. |
| `to_host` | string \| null | OPTIONAL | `null` | Target host hint. |
| `to_base_url` | string \| null | OPTIONAL | `null` | Full base URL for cross-host routing. |
| `route_scope` | string | OPTIONAL | `"local"` | `"local"` or `"remote"`. Indicates routing intent. |

#### 4.1.2 Execution Layer

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `action` | string | REQUIRED | — | The action to perform. See Section 4.2. |
| `intent` | string | REQUIRED | — | Human-readable description of what the sender wants. |
| `payload` | object | OPTIONAL | `{}` | Structured data for the action. Schema is action-dependent. |
| `expected_output` | string \| null | OPTIONAL | `null` | Description of the expected result or deliverable. |
| `constraints` | array[string] | OPTIONAL | `[]` | Policy, deadline, or context constraints. |
| `priority` | string | OPTIONAL | `"normal"` | One of: `"low"`, `"normal"`, `"high"`, `"urgent"`. |
| `status` | string | OPTIONAL | `"Pending"` | Message lifecycle: `"Pending"`, `"InProgress"`, `"Completed"`, `"Failed"`. |

#### 4.1.3 Governance Layer

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `authority_weight` | integer | OPTIONAL | `50` | Sender's authority level (0-100). Used for routing, ordering, and policy decisions. |
| `requires_approval` | boolean | OPTIONAL | `false` | Whether this action requires human approval before execution. |
| `approval_state` | string | OPTIONAL | `"not_required"` | One of: `"not_required"`, `"waiting_human"`, `"approved"`, `"rejected"`. |

#### 4.1.4 Callback Layer

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `callback_url` | string \| null | OPTIONAL | `null` | Webhook URL where the receiver should POST task results upon completion. |
| `callback_secret` | string \| null | OPTIONAL | `null` | Shared secret for HMAC-SHA256 signature verification of callback payloads. |

When `callback_url` is set:

1. The receiver MUST `POST` the final `AIPTask` (or `AIPMessage` with `status: "Completed"` or `"Failed"`) to the callback URL when the task reaches a terminal state.
2. The callback payload MUST be a valid JSON body with `Content-Type: application/json`.
3. If `callback_secret` is set, the receiver MUST include an `X-AIP-Signature` header containing the HMAC-SHA256 hex digest of the raw request body, computed with the shared secret: `HMAC-SHA256(callback_secret, body)`.
4. The receiver SHOULD retry callback delivery up to 3 times with exponential backoff on 5xx responses or timeouts.
5. The receiver MUST NOT retry on 4xx responses.

**Example message with callback:**

```json
{
  "version": "1.0",
  "message_id": "msg-001",
  "from": "orchestrator",
  "to": "agent-backend",
  "action": "assign_task",
  "intent": "Design the order service API",
  "callback_url": "https://orchestrator.example.com/v1/webhooks/task-results",
  "callback_secret": "whsec_a1b2c3d4e5f6..."
}
```

**Callback delivery:**

```http
POST https://orchestrator.example.com/v1/webhooks/task-results
Content-Type: application/json
X-AIP-Signature: sha256=5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a...
X-AIP-Event: task.completed
```

```json
{
  "task_id": "task-001",
  "message_id": "msg-001",
  "state": "completed",
  "from": "orchestrator",
  "to": "agent-backend",
  "action": "assign_task",
  "intent": "Design the order service API",
  "artifacts": [...]
}
```

#### 4.1.5 Observability Layer

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `retries` | integer | OPTIONAL | `0` | Number of delivery retries attempted. |
| `latency_ms` | integer \| null | OPTIONAL | `null` | Processing latency in milliseconds. |
| `error_code` | string \| null | OPTIONAL | `null` | Machine-readable error code. |
| `error_message` | string \| null | OPTIONAL | `null` | Human-readable error description. |
| `created_at` | string | OPTIONAL | (now) | ISO 8601 UTC timestamp of message creation. |
| `updated_at` | string | OPTIONAL | (now) | ISO 8601 UTC timestamp of last update. |

### 4.2 Standard Actions

Implementations MUST support the following standard actions. Custom actions are allowed and SHOULD use a namespaced prefix (e.g., `x-myorg/custom_action`).

| Action | Description |
|--------|-------------|
| `assign_task` | Delegate a task to another agent. |
| `submit_report` | Submit a result or progress report. |
| `request_context` | Request information or context from another agent. |
| `request_artifact_review` | Request review of a produced artifact. |
| `request_approval` | Request human or supervisor approval. |
| `publish_status` | Broadcast a status update. |
| `handoff` | Transfer responsibility for a task to another agent. |
| `escalate` | Escalate an issue to a higher-authority agent. |
| `tool_result` | Return the result of a tool invocation. |
| `sync_skill_registry` | Synchronize capability/skill metadata between agents. |
| `user_instruction` | A directive from a human user. |

### 4.3 Acknowledgment (`AIPAck`)

Every `POST /v1/aip` handler MUST return an `AIPAck` on success:

```json
{
  "ok": true,
  "message_id": "8e9930a2-8b58-44ad-a642-4cc1f136cc5d",
  "to": "agent-backend",
  "status": "received",
  "correlation_id": "corr-001"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ok` | boolean | REQUIRED | `true` if the message was accepted. |
| `message_id` | string | REQUIRED | Echoed `message_id` from the request. |
| `to` | string | REQUIRED | The agent that received the message. |
| `status` | string | REQUIRED | `"received"`, `"queued"`, `"rejected"`. |
| `task_id` | string \| null | OPTIONAL | Task identifier if the message triggered a task (see Section 6). |
| `correlation_id` | string \| null | OPTIONAL | Echoed `correlation_id` if present. |

### 4.4 Human as Sender

Humans are not a special protocol branch. A human sends messages using the same `AIPMessage` format:

- `from`: `"user"` (or a user-specific identifier)
- `from_role`: `"user"` (RECOMMENDED)

Receivers distinguish human messages via `from_role` for display, permissions, and audit — not via a separate protocol path.

---

## 5. Status Protocol

### 5.1 `GET /v1/status`

Every AIP-compliant agent MUST implement `GET /v1/status`. The response describes the agent's identity, health, capabilities, and optionally its subordinates.

### 5.2 Query Scopes

| Scope | Applicable To | Description |
|-------|---------------|-------------|
| `self` | Any agent | Returns only the current agent's status. |
| `subtree` | Any agent | Returns the agent and all its subordinates as a recursive tree. |
| `group` | Coordinator | Returns a flat aggregate view of the entire group. |

The scope is specified via query parameter: `GET /v1/status?scope=self`.

- Workers SHOULD default to `scope=self`.
- Coordinators SHOULD default to `scope=group`.
- Coordinators SHOULD support `GET /v1/status?scope=subtree&root=<agent_id>`.

### 5.3 Agent Status (`AgentStatus`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_id` | string | REQUIRED | Unique machine identifier for this agent. |
| `role` | string | REQUIRED | Agent's role in the group. |
| `namespace` | string \| null | OPTIONAL | Logical namespace for multi-tenant isolation (e.g., `"acme-corp"`, `"team-infra"`). Agents in different namespaces are invisible to each other by default. Default: `null`. |
| `presentation` | Presentation \| null | OPTIONAL | Human-facing display metadata for dashboards, agent cards, and marketplace UIs (see 5.10). Default: `null`. |
| `superior` | string \| null | OPTIONAL | Agent ID of the direct superior. |
| `authority_weight` | integer \| null | OPTIONAL | Agent's authority weight (0-100). |
| `lifecycle` | string \| null | OPTIONAL | One of: `"idle"`, `"starting"`, `"running"`, `"blocked"`, `"degraded"`, `"failed"`. |
| `port` | integer \| null | OPTIONAL | Service port. |
| `ok` | boolean | OPTIONAL | `true` if the agent is healthy. Default: `true`. |
| `base_url` | string \| null | OPTIONAL | Agent's base URL for discovery. |
| `endpoints` | object \| null | OPTIONAL | `{ "aip": "...", "status": "..." }` |
| `capabilities` | array[string] | OPTIONAL | List of supported action names (simple discovery). |
| `skills` | array[Skill] | OPTIONAL | Structured skill descriptors with input/output schemas (rich discovery, see 5.7). |
| `supported_versions` | array[string] | OPTIONAL | Protocol versions this agent supports. |
| `authentication` | object \| null | OPTIONAL | Supported auth schemes (see 5.8). |
| `rate_limits` | object \| null | OPTIONAL | Rate limiting and quota information (see 5.9). |
| `pending_tasks` | integer | OPTIONAL | Number of pending tasks. Default: `0`. |
| `recent_errors` | integer | OPTIONAL | Number of recent errors. Default: `0`. |
| `waiting_for_approval` | boolean | OPTIONAL | Whether the agent is blocked on approval. Default: `false`. |
| `last_message_at` | string \| null | OPTIONAL | ISO 8601 timestamp of last AIP message. |
| `last_seen_at` | string \| null | OPTIONAL | ISO 8601 timestamp of last activity. |
| `metadata` | object \| null | OPTIONAL | Implementation-specific metadata. |
| `assignment` | AgentAssignment \| null | OPTIONAL | Platform-assigned role, scope, and constraints (see 5.12). `null` if the agent has no platform assignment. |

### 5.4 Work Snapshot (`WorkSnapshot`)

Agents MAY include a work snapshot for operational visibility:

| Field | Type | Description |
|-------|------|-------------|
| `tasks` | array[object] | Recent task items. |
| `reports` | array[object] | Recent reports. |
| `recent_messages` | array[object] | Recent AIP messages. |
| `last_seen` | string \| null | Last activity timestamp. |
| `pending_tasks` | integer | Number of incomplete tasks. |

### 5.5 Recursive Status (`RecursiveStatusNode`)

For `scope=subtree`, the response is a recursive tree:

```json
{
  "self": { "...AgentStatus..." },
  "subordinates": [
    {
      "self": { "...AgentStatus..." },
      "subordinates": []
    }
  ]
}
```

### 5.6 Group Status (`GroupStatus`)

For `scope=group`, the response is a flat aggregate:

| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | Overall group health. |
| `service` | string | Service identifier. |
| `namespace` | string \| null | Namespace of this agent group. Default: `null`. |
| `root_agent_id` | string | Root coordinator agent ID. |
| `timestamp` | string | ISO 8601 generation timestamp. |
| `topology` | object | Map of agent_id to list of direct subordinate IDs. |
| `waiting_for_approval` | boolean | Whether any agent in the group is blocked on approval. |
| `agents` | array[AgentStatus] | Flat list of all agent statuses. |

### 5.7 Skills (`Skill`)

The `skills` array provides **rich, structured discovery** of an agent's capabilities — analogous to A2A's Agent Card skills. This enables clients to programmatically understand what an agent can do, what inputs it expects, and what outputs it produces.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | REQUIRED | Unique skill identifier (e.g., `"api-design"`, `"code-review"`). |
| `name` | string | REQUIRED | Human-readable skill name. |
| `description` | string | REQUIRED | What this skill does. |
| `tags` | array[string] | OPTIONAL | Categorization tags (e.g., `["backend", "api"]`). |
| `input_modes` | array[string] | OPTIONAL | Accepted input MIME types. Default: `["application/json"]`. |
| `output_modes` | array[string] | OPTIONAL | Produced output MIME types. Default: `["application/json"]`. |
| `input_schema` | object \| null | OPTIONAL | JSON Schema describing expected `payload` structure. |
| `output_schema` | object \| null | OPTIONAL | JSON Schema describing the output `payload` structure. |
| `examples` | array[object] | OPTIONAL | Example input/output pairs for documentation. |

**Example:**

```json
{
  "skills": [
    {
      "id": "api-design",
      "name": "REST API Design",
      "description": "Design RESTful APIs with OpenAPI specification output",
      "tags": ["backend", "api", "openapi"],
      "input_modes": ["application/json", "text/plain"],
      "output_modes": ["application/json", "application/yaml"],
      "input_schema": {
        "type": "object",
        "properties": {
          "instruction": { "type": "string" },
          "deliverables": { "type": "array", "items": { "type": "string" } }
        },
        "required": ["instruction"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "summary": { "type": "string" },
          "artifacts": { "type": "array", "items": { "type": "string" } }
        }
      }
    }
  ]
}
```

The `capabilities` array (simple string list) and `skills` array (structured) MAY coexist. `capabilities` provides backward-compatible simple discovery; `skills` provides rich, machine-readable discovery.

### 5.8 Authentication Schemes

Agents SHOULD declare their supported authentication schemes in the status response:

```json
{
  "authentication": {
    "schemes": ["bearer", "api_key", "oauth2"],
    "oauth2": {
      "token_url": "https://auth.example.com/token",
      "scopes": ["agent:read", "agent:write"]
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `schemes` | array[string] | Supported auth scheme names (`"bearer"`, `"api_key"`, `"oauth2"`, `"mtls"`). |
| `oauth2` | object \| null | OAuth2 configuration if applicable. |
| `oauth2.token_url` | string | Token endpoint URL. |
| `oauth2.scopes` | array[string] | Available OAuth2 scopes. |

### 5.9 Rate Limits (`RateLimitInfo`)

Agents SHOULD declare their rate limits and quota information in the status response to enable clients to self-regulate and avoid `429` responses.

```json
{
  "rate_limits": {
    "max_requests_per_minute": 60,
    "max_requests_per_day": 10000,
    "max_concurrent_tasks": 5,
    "remaining_requests": 42,
    "remaining_tasks": 3,
    "reset_at": "2026-03-12T11:00:00Z"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `max_requests_per_minute` | integer \| null | Maximum `POST /v1/aip` requests per minute. `null` = unlimited. |
| `max_requests_per_day` | integer \| null | Maximum requests per calendar day (UTC). `null` = unlimited. |
| `max_concurrent_tasks` | integer \| null | Maximum simultaneous tasks in non-terminal state. `null` = unlimited. |
| `remaining_requests` | integer \| null | Remaining requests in the current minute window. |
| `remaining_tasks` | integer \| null | Remaining task slots available. |
| `reset_at` | string \| null | ISO 8601 UTC timestamp when the rate limit window resets. |

**HTTP Response Headers:**

When rate limiting is active, servers MUST include these response headers on `429` responses:

| Header | Example | Description |
|--------|---------|-------------|
| `Retry-After` | `30` | Seconds until the client may retry. |
| `X-RateLimit-Limit` | `60` | Request limit for the current window. |
| `X-RateLimit-Remaining` | `0` | Remaining requests in the current window. |
| `X-RateLimit-Reset` | `1741777200` | Unix timestamp when the window resets. |

Servers SHOULD include `X-RateLimit-*` headers on all `200` responses as well, to enable proactive client-side throttling.

### 5.10 Presentation (`Presentation`)

The `presentation` object provides **human-facing display metadata** for dashboards, agent cards, marketplace UIs, and multi-agent platforms where humans observe and interact with agent networks.

Unlike `agent_id` (a machine identifier) and `role` (an organizational label), `presentation` is explicitly designed for end-user rendering. It enables consistent, localized display across any UI without relying on free-form text fields.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `display_name` | string | REQUIRED | Short human-readable name for UI display (e.g., `"Backend Engineer"`, `"Code Reviewer"`). |
| `tagline` | string \| null | OPTIONAL | One-line summary of what this agent does, suitable for subtitle or tooltip. Max 140 characters. |
| `description` | string \| null | OPTIONAL | Longer human-readable description. Markdown MAY be used. |
| `icon_url` | string \| null | OPTIONAL | URL to an avatar or icon image (SHOULD be square, RECOMMENDED 256×256 minimum). |
| `color` | string \| null | OPTIONAL | Brand / accent color as a hex string (e.g., `"#4A90D9"`). UIs MAY use this for badges, borders, or status indicators. |
| `locale` | string | OPTIONAL | BCP 47 language tag indicating the locale of all human-readable text in this status response (e.g., `"en"`, `"zh-CN"`, `"ja"`). Default: `"en"`. |
| `categories` | array[string] | OPTIONAL | UI categorization labels for marketplace-style discovery (e.g., `["engineering", "backend"]`). |
| `homepage_url` | string \| null | OPTIONAL | URL to the agent's documentation or homepage. |
| `privacy_policy_url` | string \| null | OPTIONAL | URL to the agent provider's privacy policy. |
| `tos_url` | string \| null | OPTIONAL | URL to the agent provider's terms of service. |
| `provider` | object \| null | OPTIONAL | Information about the organization or individual that operates this agent. Contains `name` (REQUIRED) and `url` (OPTIONAL). |

**Example:**

```json
{
  "agent_id": "agent-backend",
  "role": "backend_engineer",
  "namespace": "acme-corp",
  "presentation": {
    "display_name": "Backend Engineer",
    "tagline": "Designs and reviews REST APIs with OpenAPI output",
    "description": "Specialized in designing RESTful APIs, generating OpenAPI specs, and performing security reviews on backend services.",
    "icon_url": "https://cdn.example.com/agents/backend-eng.png",
    "color": "#4A90D9",
    "locale": "en",
    "categories": ["engineering", "backend", "api"],
    "homepage_url": "https://docs.example.com/agents/backend",
    "provider": {
      "name": "Acme Corp",
      "url": "https://acme.example.com"
    }
  },
  "lifecycle": "running",
  "ok": true,
  "skills": [...]
}
```

**Localization:**

- The `locale` field declares the language of all human-readable text in the current status response (`display_name`, `tagline`, `description`, skill `name` and `description`, `error_message`, etc.).
- Agents that support multiple locales SHOULD accept the standard HTTP `Accept-Language` header on `GET /v1/status` and return the best-matching locale.
- Agents that do not support locale negotiation MUST return their default locale and declare it in `presentation.locale`.

### 5.11 Namespace

The `namespace` field on `AgentStatus` and `GroupStatus` provides a logical isolation boundary for multi-tenant platforms. It enables a single AIP platform to host agents from different organizations, teams, or environments without collision.

**Rules:**

- Namespace values SHOULD be lowercase alphanumeric with hyphens (e.g., `"acme-corp"`, `"team-infra"`, `"prod"`).
- Agents with different `namespace` values SHOULD be invisible to each other in discovery (`GET /v1/status?scope=group` or `scope=subtree`) unless the platform explicitly enables cross-namespace visibility.
- Messages sent across namespaces SHOULD require explicit cross-namespace authorization.
- If `namespace` is `null`, the agent is in the default namespace.

### 5.12 Agent Assignment (`AgentAssignment`)

An agent has two identities: its **native profile** (self-declared role, skills, tools) and its **platform assignment** (what the organization tells it to do). The `AgentAssignment` object represents the latter.

Think of it as the difference between a person's resume and their job description — the resume is theirs, the job description is the company's.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assigned_role` | string \| null | OPTIONAL | Platform-assigned role, may differ from the agent's self-declared `role`. Example: agent declares `role: "coder"`, platform assigns `assigned_role: "backend-engineer"`. |
| `team` | string \| null | OPTIONAL | Team or department this agent belongs to. Example: `"order-service"`, `"infra"`, `"qa"`. |
| `scope` | string \| null | OPTIONAL | Human-readable description of the agent's work boundaries. Example: `"Order service backend development and maintenance"`. |
| `granted_tools` | array[string] | OPTIONAL | Tools or resources the platform grants to this agent beyond its native capabilities. Example: `["prod-db-readonly", "staging-deploy", "sentry-access"]`. |
| `granted_skills` | array[Skill] | OPTIONAL | Additional skill descriptors the platform injects (same schema as Section 5.7). These are merged with the agent's native `skills` for discovery. |
| `constraints` | array[string] | OPTIONAL | Boundaries the platform imposes. Example: `["No direct production writes", "Max 10 concurrent tasks", "Requires approval for deployments"]`. |
| `supervisor` | string \| null | OPTIONAL | Agent ID of the assigned supervisor (may override the agent's self-declared `superior`). |
| `priority` | string \| null | OPTIONAL | Platform-assigned priority level for this agent's work. Example: `"high"`, `"normal"`, `"low"`. |
| `assigned_at` | string \| null | OPTIONAL | ISO 8601 timestamp of when the assignment was last updated. |
| `metadata` | object \| null | OPTIONAL | Platform-specific extension fields. |

**Example:**

```json
{
  "agent_id": "claw-a",
  "role": "coder",
  "skills": [
    { "id": "python", "name": "Python", "description": "Python development" },
    { "id": "go", "name": "Go", "description": "Go development" }
  ],
  "assignment": {
    "assigned_role": "backend-engineer",
    "team": "order-service",
    "scope": "Order service backend — API design, implementation, and code review",
    "granted_tools": ["prod-db-readonly", "staging-deploy"],
    "constraints": ["No direct production writes", "Max 10 concurrent tasks"],
    "supervisor": "tech-lead-agent",
    "priority": "high",
    "assigned_at": "2026-03-12T10:00:00Z"
  }
}
```

**Semantics:**

- The `assignment` is entirely platform-controlled. Agents MUST NOT modify their own assignment.
- When both `role` and `assigned_role` are present, dashboards SHOULD display `assigned_role` as the primary label and `role` as the secondary ("native") label.
- `granted_skills` are merged with native `skills` for discovery purposes. Callers querying the agent's capabilities see the union of both.
- `constraints` are informational — they describe what the platform expects, but enforcement is the platform's responsibility (not the agent's).
- `assignment` MAY be `null` (the agent has no platform assignment — it operates in its native capacity).

#### 5.12.1 Assignment Delivery

Assignments reach the agent through three mechanisms (platforms MAY use any combination):

1. **Registration response** — the platform includes `assignment` in the `AgentRegistrationResponse` (Section 15.4). The agent stores it locally and reflects it in `GET /v1/status`.

2. **Heartbeat command** — the platform sends an `assign` command in the heartbeat ACK (Section 15.6.3). The agent updates its stored assignment and reflects it in the next status response.

3. **Dedicated endpoint** — `PUT /v1/registry/agents/{agent_id}/assignment` allows the platform (or an authorized caller) to update the assignment at any time. The platform SHOULD also send a `refresh_status` heartbeat command so the agent re-announces its updated status.

#### 5.12.2 Assignment Lifecycle

| Event | Behavior |
|-------|----------|
| Agent registers | Platform MAY include `assignment` in the registration response. |
| Platform updates assignment | Platform sends `assign` command via heartbeat or calls PUT endpoint. |
| Agent re-registers (after restart) | Platform SHOULD re-send the last known assignment. |
| Agent deregisters | Assignment is discarded. |
| Assignment cleared | Platform sends `assign` with empty/null payload — agent reverts to native profile only. |

---

## 6. Task Lifecycle

### 6.1 Overview

AIP provides a **first-class Task model** for managing long-running agent work. When a client sends a message via `POST /v1/aip`, the server MAY create a `Task` to track execution. Tasks have their own lifecycle, independent of individual messages.

### 6.2 Task States

```
submitted ──→ working ──→ completed
                │              
                ├──→ input-required ──→ working
                │
                ├──→ failed
                │
                └──→ canceled
```

| State | Description |
|-------|-------------|
| `submitted` | Task received but not yet started. |
| `working` | Agent is actively executing the task. |
| `input-required` | Agent needs additional input from the sender before continuing. |
| `completed` | Task finished successfully. |
| `failed` | Task failed (see `error_code` and `error_message`). |
| `canceled` | Task was canceled by the sender or a supervisor. |

### 6.3 Task Object (`AIPTask`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | string | REQUIRED | Globally unique task identifier. |
| `message_id` | string | REQUIRED | The originating message that created this task. |
| `trace_id` | string \| null | OPTIONAL | End-to-end trace identifier (propagated from the originating message). |
| `correlation_id` | string \| null | OPTIONAL | Request-response correlation identifier. |
| `parent_task_id` | string \| null | OPTIONAL | Parent task ID for sub-task decomposition. |
| `state` | string | REQUIRED | Current task state (see 6.2). |
| `from` | string | REQUIRED | Agent/user that initiated the task. |
| `to` | string | REQUIRED | Agent responsible for executing the task. |
| `action` | string | REQUIRED | The action being performed. |
| `intent` | string | REQUIRED | Human-readable description of the task. |
| `progress` | number \| null | OPTIONAL | Progress indicator (0.0 to 1.0). |
| `artifacts` | array[Artifact] | OPTIONAL | Artifacts produced by the task (see 6.5). |
| `history` | array[AIPMessage] | OPTIONAL | Ordered list of messages exchanged within this task context. |
| `error_code` | string \| null | OPTIONAL | Machine-readable error code (if `state` is `"failed"`). |
| `error_message` | string \| null | OPTIONAL | Human-readable error (if `state` is `"failed"`). |
| `metadata` | object \| null | OPTIONAL | Implementation-specific metadata. |
| `created_at` | string | REQUIRED | ISO 8601 UTC timestamp. |
| `updated_at` | string | REQUIRED | ISO 8601 UTC timestamp. |

### 6.4 Task Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST /v1/aip` | Create task | Sending a message MAY implicitly create a task. The `AIPAck` includes `task_id`. |
| `GET /v1/tasks/{task_id}` | Get task | Retrieve full task state, artifacts, and history. |
| `POST /v1/tasks/{task_id}/cancel` | Cancel task | Request cancellation. Server responds with updated task. |
| `POST /v1/tasks/{task_id}/send` | Send into task | Send a follow-up message within an existing task context (e.g., answer `input-required`). |
| `POST /v1/artifacts` | Upload artifact | Upload a file via multipart/form-data. Returns an `Artifact` with a server-assigned `uri` (see 6.7). |
| `GET /v1/artifacts/{artifact_id}` | Fetch artifact | Download artifact content. Returns the raw file with the original `Content-Type`. |

**GET /v1/tasks/{task_id} response:**

```json
{
  "task_id": "task-001",
  "message_id": "msg-001",
  "state": "working",
  "from": "user",
  "to": "agent-backend",
  "action": "assign_task",
  "intent": "Design the order service REST API",
  "progress": 0.45,
  "artifacts": [],
  "history": [],
  "created_at": "2026-03-12T10:00:00Z",
  "updated_at": "2026-03-12T10:05:00Z"
}
```

**Cancellation:**

```http
POST /v1/tasks/task-001/cancel
```

Response: The updated `AIPTask` with `"state": "canceled"`.

### 6.5 Artifacts

Tasks MAY produce **artifacts** — files, documents, or structured data generated during execution.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact_id` | string | REQUIRED | Unique artifact identifier. |
| `name` | string | REQUIRED | Human-readable name (e.g., `"orders-api.yaml"`). |
| `description` | string \| null | OPTIONAL | Description of the artifact. |
| `mime_type` | string | REQUIRED | MIME type (e.g., `"application/yaml"`, `"text/plain"`, `"image/png"`). |
| `uri` | string \| null | OPTIONAL | URI to fetch the artifact content. |
| `inline_data` | string \| null | OPTIONAL | Base64-encoded inline content (for small artifacts). |
| `metadata` | object \| null | OPTIONAL | Additional metadata. |

Exactly one of `uri` or `inline_data` MUST be present. Servers SHOULD use `uri` for artifacts larger than 1 MB.

### 6.6 Artifact Upload (`POST /v1/artifacts`)

While `inline_data` (base64) is suitable for small payloads, real-world agent workflows produce and consume files of all types and sizes — PDFs, images, datasets, code archives, model weights, etc. AIP provides a **dedicated artifact upload endpoint** for binary content.

**Request:**

```http
POST /v1/artifacts
Content-Type: multipart/form-data
```

| Part | Type | Required | Description |
|------|------|----------|-------------|
| `file` | binary | REQUIRED | The file content. Any MIME type. |
| `name` | string | OPTIONAL | Human-readable name. Defaults to the uploaded filename. |
| `description` | string | OPTIONAL | Description of the artifact. |
| `task_id` | string | OPTIONAL | Associate this artifact with an existing task. |
| `metadata` | string (JSON) | OPTIONAL | JSON-encoded metadata object. |

**Response (201 Created):**

```json
{
  "artifact_id": "art-a1b2c3",
  "name": "orders-api.yaml",
  "mime_type": "application/yaml",
  "uri": "https://agent.example.com/v1/artifacts/art-a1b2c3",
  "size_bytes": 4096,
  "created_at": "2026-03-12T10:30:00Z"
}
```

**Server requirements:**

- Servers SHOULD support uploads of at least **100 MB** per artifact.
- Servers MUST return `413 Content Too Large` if the upload exceeds the server's size limit.
- Servers MUST return `415 Unsupported Media Type` if the Content-Type is not `multipart/form-data`.
- The server MUST assign a unique `artifact_id` and return a `uri` that can be used to fetch or reference the artifact.
- If `task_id` is provided, the artifact MUST be appended to the task's `artifacts` array.

**Fetch (`GET /v1/artifacts/{artifact_id}`):**

- Servers MUST return the raw file content with the original `Content-Type` header (e.g., `Content-Type: image/png`).
- Servers SHOULD include `Content-Disposition: attachment; filename="<name>"`.
- Servers MUST return `404 Not Found` if the artifact does not exist.

**Referencing uploaded artifacts in messages:**

After uploading, the returned `uri` can be used in any `Artifact` reference within messages, task results, or SSE `artifact` events. This decouples file transfer from the JSON messaging channel.

### 6.7 AIPAck with Task ID

When a task is created, the `AIPAck` MUST include the `task_id`:

```json
{
  "ok": true,
  "message_id": "msg-001",
  "to": "agent-backend",
  "status": "received",
  "task_id": "task-001"
}
```

---

## 7. Governance

### 7.1 Approval Workflow

AIP provides first-class support for human-in-the-loop governance:

- Any message that may affect production environments SHOULD set `requires_approval: true`.
- Agents MUST NOT execute production-impacting actions unless `approval_state` is `"approved"`.
- The `approval_state` field tracks the lifecycle: `"not_required"` → `"waiting_human"` → `"approved"` | `"rejected"`.

### 7.2 Authority Weight

The `authority_weight` field (0-100) represents organizational authority. It is advisory, not enforced by the protocol, but implementations MAY use it for:

- Routing decisions (prefer higher-authority sources)
- Task prioritization
- Approval policy (auto-approve if `authority_weight >= threshold`)

---

## 8. Reliability

### 8.1 Retry Semantics

Implementations SHOULD retry on transient failures (5xx, timeout, connection errors) with exponential backoff and jitter. Implementations MUST NOT retry on 4xx client errors.

**Recommended defaults:**

| Parameter | Value |
|-----------|-------|
| Timeout | 30 seconds |
| Max retries | 4 (1 initial + 3 retries) |
| Backoff base | 1.0 seconds |
| Backoff max | 60.0 seconds |
| Backoff jitter | ±20% |

### 8.2 Idempotency

AIP defines a standard idempotency mechanism to prevent duplicate processing of messages, following the patterns established by Stripe, IETF draft-ietf-httpapi-idempotency-key-header, and other production-grade APIs.

#### 8.2.1 The `Idempotency-Key` Header

| Aspect | Specification |
|--------|---------------|
| **Header name** | `Idempotency-Key` |
| **Format** | UUID v4 string (e.g., `"550e8400-e29b-41d4-a716-446655440000"`) |
| **Scope** | Per client-server pair. The same key from different clients MAY map to different operations. |
| **Required?** | OPTIONAL for senders. Servers SHOULD support it. |

#### 8.2.2 Server Behavior

When a server receives a request with an `Idempotency-Key` header:

1. **First request:** Process normally. Store the response keyed by `(client_id, idempotency_key)` with the original request fingerprint (hash of method + path + body).
2. **Duplicate request (same key, same body):** Return the stored response with HTTP `200` and the header `Idempotency-Replayed: true`. Do NOT re-execute the action.
3. **Conflicting request (same key, different body):** Return HTTP `409 Conflict` with error code `aip/protocol/idempotency_conflict`.
4. **Concurrent request (same key, original still processing):** Return HTTP `409 Conflict` with error code `aip/protocol/idempotency_concurrent`. The client SHOULD wait and retry.

#### 8.2.3 Key Lifetime

- Servers MUST retain idempotency records for at least **24 hours**.
- Servers SHOULD retain records for **72 hours** in production deployments.
- Servers MAY discard records after the retention period. A replayed key after expiry is treated as a new request.
- Servers SHOULD include the `Idempotency-Key-Expiry` response header (ISO 8601 UTC) to indicate when the key record will expire.

#### 8.2.4 Response Headers

| Header | Example | Description |
|--------|---------|-------------|
| `Idempotency-Key` | `550e8400-...` | Echoed from the request. |
| `Idempotency-Replayed` | `true` | Present only when the response is a replay of a previous request. |
| `Idempotency-Key-Expiry` | `2026-03-15T10:00:00Z` | When this idempotency record expires. |

#### 8.2.5 Client Behavior

- Clients SHOULD generate a new UUID v4 for each logically distinct request.
- Clients MUST reuse the same `Idempotency-Key` when retrying a failed request.
- Clients MUST NOT reuse an `Idempotency-Key` for a logically different request.
- The SDK `SendParams.idempotency_key` field maps directly to this header.

### 8.3 Message Persistence

Receivers SHOULD persist all incoming AIP messages to a durable log (e.g., JSONL file, database) for auditability and replay.

---

## 9. Error Codes

### 9.1 Standard Error Code Registry

AIP defines a standard error code registry using the `aip/` namespace. Implementations MUST use these codes for the corresponding error conditions. The `error_code` field in messages, tasks, and SSE error events MUST use codes from this registry for standard conditions.

Error codes follow the format: `aip/<category>/<error_name>`

#### 9.1.1 Protocol Errors (`aip/protocol/`)

Errors in the protocol layer — addressing, routing, version mismatches.

| Code | HTTP | Description |
|------|------|-------------|
| `aip/protocol/invalid_version` | 422 | The `version` field does not match the URL path version. |
| `aip/protocol/unsupported_version` | 422 | The protocol version is not supported by this agent. |
| `aip/protocol/invalid_message` | 422 | The message does not conform to the AIP schema. |
| `aip/protocol/routing_failed` | 400 | The `to` field does not match this agent and cannot be forwarded. |
| `aip/protocol/agent_not_found` | 404 | The target agent does not exist. |
| `aip/protocol/agent_unavailable` | 503 | The target agent is temporarily unavailable. |

#### 9.1.2 Execution Errors (`aip/execution/`)

Errors during action execution — invalid actions, task failures, input problems.

| Code | HTTP | Description |
|------|------|-------------|
| `aip/execution/unknown_action` | 422 | The `action` is not recognized by this agent. |
| `aip/execution/invalid_payload` | 422 | The `payload` does not match the expected schema for this action. |
| `aip/execution/task_failed` | 200* | The task encountered an unrecoverable error during execution. |
| `aip/execution/task_timeout` | 200* | The task exceeded the maximum execution time. |
| `aip/execution/task_not_found` | 404 | The referenced task does not exist. |
| `aip/execution/task_not_cancelable` | 409 | The task is in a terminal state and cannot be canceled. |
| `aip/execution/capacity_exceeded` | 429 | The agent has reached its maximum concurrent task capacity. |
| `aip/execution/input_required` | 200* | The task requires additional input to continue. |

*\* These codes appear in the `error_code` field of a task or SSE event, not as HTTP status codes.*

#### 9.1.3 Governance Errors (`aip/governance/`)

Errors related to authority, approval, and policy constraints.

| Code | HTTP | Description |
|------|------|-------------|
| `aip/governance/authority_insufficient` | 403 | The sender's `authority_weight` is below the required threshold. |
| `aip/governance/approval_required` | 403 | This action requires approval (`requires_approval: true`) but `approval_state` is not `"approved"`. |
| `aip/governance/approval_rejected` | 403 | The approval request was explicitly rejected. |
| `aip/governance/constraint_violated` | 422 | One or more `constraints` cannot be satisfied. |
| `aip/governance/policy_denied` | 403 | A policy rule prevents this action from being executed. |

#### 9.1.4 Authentication & Authorization Errors (`aip/auth/`)

| Code | HTTP | Description |
|------|------|-------------|
| `aip/auth/unauthenticated` | 401 | No valid credentials provided. |
| `aip/auth/unauthorized` | 403 | Valid credentials but insufficient permissions. |
| `aip/auth/token_expired` | 401 | The authentication token has expired. |
| `aip/auth/invalid_token` | 401 | The authentication token is malformed or invalid. |

#### 9.1.5 Rate Limiting Errors (`aip/ratelimit/`)

| Code | HTTP | Description |
|------|------|-------------|
| `aip/ratelimit/exceeded` | 429 | Request rate limit exceeded. See `Retry-After` header. |
| `aip/ratelimit/quota_exhausted` | 429 | Usage quota for the current period is exhausted. |

### 9.2 Custom Error Codes

Implementations MAY define custom error codes using a namespaced prefix:

```
x-<organization>/<category>/<error_name>
```

Example: `x-acme/billing/credits_exhausted`

Custom error codes MUST NOT use the `aip/` prefix.

### 9.3 Error Response Format

When returning an error in a non-streaming response (HTTP 4xx/5xx), the response body SHOULD follow this format:

```json
{
  "ok": false,
  "error_code": "aip/governance/authority_insufficient",
  "error_message": "Authority weight 30 is below the required threshold of 80 for action 'assign_task'.",
  "message_id": "msg-001",
  "to": "agent-backend",
  "status": "rejected"
}
```

For streaming responses, errors are delivered as SSE events:

```
event: error
data: {"error_code":"aip/execution/task_failed","error_message":"Compilation failed with 3 errors"}
```

---

## 10. Observability and Cost Tracking

### 10.1 Overview

AIP defines a standard **trace event** format so that any dashboard, monitoring tool, or analytics pipeline can consume observability data from any AIP-compliant agent without proprietary adapters. This section covers:

- **Distributed tracing** — linking events across agents and tasks
- **Trace events** — the standard event schema and type registry
- **LLM usage** — token and cost tracking
- **Endpoints** — how to emit and query trace data

### 10.2 Distributed Tracing

AIP messages carry `trace_id` and `correlation_id` for end-to-end tracing:

| Field | Scope | Purpose |
|-------|-------|---------|
| `trace_id` | Workflow | Links all messages, tasks, and events in a single user-initiated workflow |
| `correlation_id` | Request-response | Links a specific request to its response |
| `parent_task_id` | Task hierarchy | Links a sub-task to its parent |
| `span_id` | Span | Unique identifier for one unit of work (OpenTelemetry compatible) |

Implementations MUST propagate `trace_id` through all downstream messages, task creations, and trace events. Implementations SHOULD propagate `correlation_id` and generate a new `span_id` per unit of work.

### 10.3 Trace Event Schema

A **TraceEvent** is a single observable event. Every meaningful action — sending a message, calling an LLM, completing a task, logging an error — SHOULD be emitted as a `TraceEvent`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | string | Yes | Unique event identifier (UUID recommended) |
| `trace_id` | string | Yes | End-to-end trace identifier |
| `agent_id` | string | Yes | Agent that emitted this event |
| `trace_type` | string | Yes | Event type from the registry (Section 10.4) |
| `severity` | string | No | `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL` (default: `INFO`) |
| `timestamp` | string | Yes | ISO 8601 timestamp |
| `correlation_id` | string | No | Request-response correlation |
| `parent_event_id` | string | No | Causal parent event |
| `span_id` | string | No | OpenTelemetry span ID |
| `parent_span_id` | string | No | Parent span ID |
| `task_id` | string | No | Associated task |
| `message_id` | string | No | Associated message |
| `summary` | string | No | Human-readable summary |
| `payload` | object | No | Type-specific data (e.g., `LLMUsage` for `llm.usage`) |
| `metadata` | object | No | Extension fields |
| `tags` | array | No | Searchable tags |
| `duration_ms` | integer | No | Duration of the operation |
| `namespace` | string | No | Logical namespace |

Example:

```json
{
  "event_id": "evt-a1b2c3",
  "trace_id": "tr-workflow-789",
  "agent_id": "agent-backend",
  "trace_type": "llm.usage",
  "severity": "INFO",
  "timestamp": "2026-03-12T10:30:00Z",
  "task_id": "task-456",
  "summary": "GPT-4o completion for API design",
  "payload": {
    "model": "gpt-4o",
    "provider": "openai",
    "prompt_tokens": 1200,
    "completion_tokens": 850,
    "total_tokens": 2050,
    "estimated_cost_usd": 0.035,
    "duration_ms": 2300
  },
  "duration_ms": 2300,
  "namespace": "acme-corp"
}
```

### 10.4 Trace Type Registry

Standard trace types. Implementations MAY define custom types using the `x-<org>/<name>` prefix.

| Type | When to emit |
|------|-------------|
| `aip.message.sent` | Agent sends an AIP message |
| `aip.message.received` | Agent receives an AIP message |
| `task.created` | New task is created |
| `task.working` | Task transitions to working state |
| `task.completed` | Task completes successfully |
| `task.failed` | Task fails |
| `task.canceled` | Task is canceled |
| `task.input_required` | Task needs user/agent input |
| `llm.request` | LLM API call initiated |
| `llm.response` | LLM API call returned |
| `llm.usage` | LLM token/cost summary (may combine request+response) |
| `tool.call` | Agent invokes a tool |
| `tool.result` | Tool returns a result |
| `report` | Agent submits a work report |
| `conversation` | Conversation message (human or agent) |
| `approval` | Approval state change |
| `error` | Error occurrence |
| `log` | General log entry |

### 10.5 LLM Usage Schema

The `llm.usage` trace event payload MUST use this structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | Model identifier (e.g., `gpt-4o`, `claude-sonnet-4-20250514`) |
| `provider` | string | No | Provider name (e.g., `openai`, `anthropic`) |
| `prompt_tokens` | integer | Yes | Input tokens |
| `completion_tokens` | integer | Yes | Output tokens |
| `total_tokens` | integer | Yes | Total tokens (`prompt + completion`) |
| `cached_tokens` | integer | No | Tokens served from cache (default: 0) |
| `estimated_cost_usd` | number | No | Estimated cost in USD |
| `duration_ms` | integer | No | LLM call latency |
| `request_id` | string | No | Provider's request ID |
| `agent_id` | string | No | Agent that made the call |
| `task_id` | string | No | Associated task |
| `trace_id` | string | No | Associated trace |

### 10.6 Usage Summary

Platforms SHOULD aggregate LLM usage data and expose it via `GET /v1/usage`:

| Field | Type | Description |
|-------|------|-------------|
| `period_start` | string | ISO 8601 start of period |
| `period_end` | string | ISO 8601 end of period |
| `namespace` | string | Namespace filter (if applied) |
| `total_requests` | integer | Total LLM calls |
| `total_prompt_tokens` | integer | Total input tokens |
| `total_completion_tokens` | integer | Total output tokens |
| `total_tokens` | integer | Grand total tokens |
| `total_cached_tokens` | integer | Total cached tokens |
| `total_estimated_cost_usd` | number | Total estimated cost |
| `by_model` | array | Per-model breakdown |
| `by_agent` | array | Per-agent breakdown |

### 10.7 Trace Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/traces` | Emit one or more trace events (batch) |
| `GET` | `/v1/traces` | Query trace events |
| `GET` | `/v1/traces/{event_id}` | Retrieve a single event |
| `GET` | `/v1/usage` | Aggregated LLM usage summary |

**POST /v1/traces** — Emit events:

```json
{
  "events": [
    { "event_id": "...", "trace_id": "...", "agent_id": "...", "trace_type": "llm.usage", "timestamp": "...", "payload": { ... } }
  ]
}
```

Response: `200 OK` with `{ "accepted": <count> }`.

**GET /v1/traces** — Query events:

| Parameter | Type | Description |
|-----------|------|-------------|
| `agent_id` | string | Filter by agent |
| `trace_id` | string | Filter by trace |
| `trace_type` | string | Filter by type |
| `task_id` | string | Filter by task |
| `severity` | string | Minimum severity |
| `namespace` | string | Filter by namespace |
| `since` | string | ISO 8601 start time |
| `until` | string | ISO 8601 end time |
| `limit` | integer | Max results (default: 100, max: 1000) |
| `offset` | integer | Pagination offset |
| `order` | string | `asc` or `desc` (default: `desc`) |

Response: paginated `TraceQueryResult`.

**GET /v1/usage** — Aggregated cost:

| Parameter | Type | Description |
|-----------|------|-------------|
| `namespace` | string | Filter by namespace |
| `agent_id` | string | Filter by agent |
| `model` | string | Filter by model |
| `since` | string | Period start |
| `until` | string | Period end |
| `group_by` | string | `model`, `agent`, `hour`, or `day` |

Response: `UsageSummary` object.

### 10.8 Logging

Implementations SHOULD log:
- Message send/receive events with `message_id`, `action`, and `trace_id`.
- Retry attempts with delay and attempt number.
- Final failure with error type and total attempts.

The protocol library SHOULD expose hooks for custom loggers and structured log fields. Implementations SHOULD emit corresponding `TraceEvent` objects for all logged events to enable cross-system observability.

---

## 11. Versioning and Evolution

### 11.1 Version Format

Protocol versions follow semantic versioning: `MAJOR.MINOR`.

- **MAJOR** version changes indicate breaking changes and a new URL path prefix (e.g., `/v2`).
- **MINOR** version changes are backward-compatible additions within the same URL path.

### 11.2 URL Path Versioning

The protocol uses URL path versioning as the primary version indicator (see Section 2.2). The URL path version (`/v1`) and the envelope `version` field (`"1.0"`) MUST be consistent:

| URL Path | Envelope `version` | Valid? |
|----------|-------------------|--------|
| `/v1/aip` | `"1.0"` | Yes |
| `/v1/aip` | `"1.1"` | Yes (minor upgrade, same major) |
| `/v1/aip` | `"2.0"` | No — MUST use `/v2/aip` |

### 11.3 Compatibility Rules

- New fields MUST be OPTIONAL with sensible defaults.
- New actions MUST NOT change the semantics of existing actions.
- Receivers MUST ignore unknown fields (forward compatibility).
- Receivers SHOULD NOT reject messages with unknown actions; they MAY respond with an appropriate error in the `AIPAck`.

### 11.4 Version Negotiation

Agents SHOULD declare `supported_versions` in their status response. Senders SHOULD use the highest mutually supported version. If version negotiation is not performed, version `"1.0"` (path `/v1`) is assumed.

### 11.5 Deprecation Policy

When a new major version is introduced:

1. The previous version SHOULD remain available for at least **12 months**.
2. Servers SHOULD include a `Deprecation` response header (RFC 8594) on deprecated version endpoints.
3. After the deprecation period, servers SHOULD return HTTP `410 Gone` with a JSON body indicating the migration path.
4. The `GET /v1/status` response SHOULD include a `deprecation_notice` field in `metadata` when the version is deprecated.

---

## 12. Extension Mechanism

### 12.1 Custom Actions

Implementations MAY define custom actions using a namespaced prefix:

```
x-<organization>/<action_name>
```

Example: `x-acme/deploy_canary`

Custom actions MUST NOT collide with standard actions defined in Section 4.2.

### 12.2 Custom Fields

Implementations MAY add custom fields to `payload` or `metadata` objects. Top-level message fields MUST NOT be extended outside the specification process.

### 12.3 Custom Status Fields

Agents MAY include additional fields in `AgentStatus.metadata` for implementation-specific data.

---

## 13. Security Considerations

### 13.1 Authentication

AIP does not mandate a specific authentication mechanism. Implementations SHOULD support at least one of:

- Bearer token (`Authorization: Bearer <token>`)
- Mutual TLS (mTLS)
- Custom authentication header

### 13.2 Authorization

Implementations SHOULD enforce authorization based on:

- `from` and `from_role` in the message
- `authority_weight` relative to the action's requirements
- `approval_state` for governed actions

### 13.3 Input Validation

Implementations MUST validate all incoming messages against the AIP schema before processing. Messages that fail validation MUST be rejected with HTTP 422.

---

## 14. Examples

### 14.1 User Sends Instruction to Coordinator

```http
POST https://coordinator.example.com/v1/aip
Content-Type: application/json
```

```json
{
  "version": "1.0",
  "message_id": "msg-001",
  "from": "user",
  "to": "coordinator",
  "from_role": "user",
  "action": "user_instruction",
  "intent": "Design the order service API and provide a risk assessment",
  "payload": {
    "instruction": "Define the REST API endpoints, error codes, and schemas for the order service"
  },
  "expected_output": "OpenAPI draft and risk summary",
  "constraints": ["start in test environment", "production requires human approval"],
  "priority": "high"
}
```

**Response:**

```json
{
  "ok": true,
  "message_id": "msg-001",
  "to": "coordinator",
  "status": "received"
}
```

### 14.2 Coordinator Assigns Task to Worker

```http
POST https://agent-backend.example.com/v1/aip
Content-Type: application/json
```

```json
{
  "version": "1.0",
  "message_id": "msg-002",
  "correlation_id": "corr-001",
  "trace_id": "trace-001",
  "parent_task_id": "task-001",
  "from": "coordinator",
  "to": "agent-backend",
  "from_role": "coordinator",
  "to_role": "backend_engineer",
  "action": "assign_task",
  "intent": "Design the order service REST API",
  "payload": {
    "instruction": "Design REST API, error codes, and schema, then report back",
    "deliverables": ["openapi", "risk_report"]
  },
  "expected_output": "OpenAPI draft and risk summary",
  "constraints": ["test first", "do not deploy to production"],
  "priority": "high",
  "authority_weight": 95
}
```

### 14.3 Worker Submits Report

```json
{
  "version": "1.0",
  "message_id": "msg-003",
  "correlation_id": "corr-001",
  "trace_id": "trace-001",
  "from": "agent-backend",
  "to": "coordinator",
  "from_role": "backend_engineer",
  "action": "submit_report",
  "intent": "Order service API draft completed",
  "payload": {
    "summary": "API draft complete, pending auth strategy confirmation",
    "artifacts": ["openapi/orders.yaml"],
    "blockers": ["auth strategy not confirmed"]
  },
  "status": "Completed"
}
```

### 14.4 Cross-Host Communication

```json
{
  "version": "1.0",
  "message_id": "msg-004",
  "from": "agent-explorer",
  "to": "agent-backend",
  "to_base_url": "https://backend.us-east.example.com",
  "route_scope": "remote",
  "action": "request_context",
  "intent": "Request order API design assumptions",
  "payload": {
    "topic": "order API assumptions"
  }
}
```

### 14.5 Agent Status Response

```http
GET https://agent-backend.example.com/v1/status
```

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
    "provider": {
      "name": "Acme Corp",
      "url": "https://acme.example.com"
    }
  },
  "superior": "coordinator",
  "authority_weight": 78,
  "lifecycle": "running",
  "ok": true,
  "base_url": "https://agent-backend.example.com",
  "endpoints": {
    "aip": "https://agent-backend.example.com/v1/aip",
    "status": "https://agent-backend.example.com/v1/status"
  },
  "capabilities": ["assign_task", "submit_report", "request_context"],
  "supported_versions": ["1.0"],
  "pending_tasks": 2,
  "recent_errors": 0,
  "waiting_for_approval": false,
  "last_message_at": "2026-03-12T10:30:00Z",
  "last_seen_at": "2026-03-12T10:35:00Z"
}
```

---

## Appendix A: JSON Schema

Machine-readable JSON Schema files for all protocol types are available in the `schemas/` directory:

- `message.schema.json` — AIPMessage
- `ack.schema.json` — AIPAck
- `status.schema.json` — AgentStatus, RecursiveStatusNode, GroupStatus

## Appendix B: JSON-RPC 2.0 Compatibility Bridge

AIP uses a custom four-layer envelope rather than JSON-RPC 2.0. However, for interoperability with A2A and other JSON-RPC-based systems, AIP defines a standard bidirectional mapping.

### B.1 AIP → JSON-RPC 2.0

An AIP message maps to a JSON-RPC 2.0 request as follows:

| AIP Field | JSON-RPC 2.0 Field | Mapping |
|-----------|-------------------|---------|
| (constant) | `jsonrpc` | Always `"2.0"` |
| `message_id` | `id` | Direct mapping |
| `action` | `method` | `"aip/{action}"` (e.g., `"aip/assign_task"`) |
| All other fields | `params` | Nested as a single `params` object |

**Example:**

AIP message:
```json
{
  "version": "1.0",
  "message_id": "msg-001",
  "from": "user",
  "to": "agent-backend",
  "action": "assign_task",
  "intent": "Design the API",
  "authority_weight": 80
}
```

Mapped JSON-RPC 2.0:
```json
{
  "jsonrpc": "2.0",
  "id": "msg-001",
  "method": "aip/assign_task",
  "params": {
    "version": "1.0",
    "from": "user",
    "to": "agent-backend",
    "intent": "Design the API",
    "authority_weight": 80
  }
}
```

### B.2 JSON-RPC 2.0 → AIP

| JSON-RPC 2.0 Field | AIP Field | Mapping |
|-------------------|-----------|---------|
| `id` | `message_id` | Direct mapping |
| `method` | `action` | Strip `"aip/"` prefix |
| `params.*` | Top-level fields | Flatten into AIP envelope |

### B.3 AIPAck → JSON-RPC 2.0 Response

```json
{
  "jsonrpc": "2.0",
  "id": "msg-001",
  "result": {
    "ok": true,
    "to": "agent-backend",
    "status": "received",
    "task_id": "task-001"
  }
}
```

### B.4 Error → JSON-RPC 2.0 Error

AIP error codes map to JSON-RPC 2.0 error codes:

| AIP Error Category | JSON-RPC Code | JSON-RPC Message |
|-------------------|--------------|-----------------|
| `aip/protocol/invalid_message` | `-32600` | Invalid Request |
| `aip/execution/unknown_action` | `-32601` | Method not found |
| `aip/execution/invalid_payload` | `-32602` | Invalid params |
| `aip/protocol/*` (other) | `-32600` | Invalid Request |
| `aip/execution/*` (other) | `-32000` | Server error |
| `aip/governance/*` | `-32001` | Governance error |
| `aip/auth/*` | `-32002` | Authentication error |

The `data` field of the JSON-RPC error object carries the full AIP error details:

```json
{
  "jsonrpc": "2.0",
  "id": "msg-001",
  "error": {
    "code": -32001,
    "message": "Governance error",
    "data": {
      "error_code": "aip/governance/authority_insufficient",
      "error_message": "Authority weight 30 is below threshold 80"
    }
  }
}
```

### B.5 Bridge Implementation

SDK implementations SHOULD provide a bridge module that:

1. Accepts incoming JSON-RPC 2.0 requests and converts them to `AIPMessage` objects.
2. Converts outgoing `AIPAck` / `AIPTask` to JSON-RPC 2.0 responses.
3. Handles JSON-RPC batch requests (`[{...}, {...}]`) by mapping to `send_batch`.
4. Passes through JSON-RPC notifications (no `id`) as fire-and-forget AIP messages.

This enables an AIP agent to serve both native AIP clients and JSON-RPC 2.0 clients (including A2A) on the same endpoint by content-sniffing the `jsonrpc` field.

## 15. Agent Onboarding Protocol

### 15.1 Overview

Sections 2–14 define how agents talk to each other. This section defines how any agent — regardless of its origin, framework, or native protocol — **joins an AIP management platform** and becomes a first-class participant in a multi-agent network.

The Agent Onboarding Protocol covers the complete lifecycle:

```
┌─────────┐     ┌───────────┐     ┌─────────┐     ┌───────────┐     ┌────────────┐
│ Register │────►│ Handshake │────►│  Active  │────►│ Degraded/ │────►│ Deregister │
│          │     │ (verify)  │     │ (heart-  │     │  Failed   │     │            │
└─────────┘     └───────────┘     │  beating)│     └───────────┘     └────────────┘
                                  └──────────┘
```

### 15.2 Onboarding Modes

An agent joins the platform in one of three modes, depending on its capabilities:

| Mode | Agent implements | How it joins | Capability level |
|------|------------------|--------------|------------------|
| **Native** | `GET /v1/status` + `POST /v1/aip` | Registers directly | Full |
| **Adapted** | Any HTTP API | Via an AIP adapter (sidecar/function) that translates | Full (through adapter) |
| **Declared** | Nothing accessible | Platform operator manually declares the agent | Discovery-only (no messaging) |

All three modes use the same registry endpoints. The platform treats them identically after onboarding.

### 15.3 Registry Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST /v1/registry/agents` | Register | Agent (or adapter, or operator) announces the agent. |
| `GET /v1/registry/agents` | List | List registered agents, filterable. |
| `GET /v1/registry/agents/{agent_id}` | Get | Get a single registration record + cached status. |
| `PATCH /v1/registry/agents/{agent_id}` | Update | Update registration (e.g., new base_url after migration). |
| `DELETE /v1/registry/agents/{agent_id}` | Deregister | Gracefully remove the agent. |
| `POST /v1/registry/agents/{agent_id}/heartbeat` | Heartbeat | Agent signals liveness + lightweight metrics. |

These endpoints are implemented by the **platform**, not by individual agents.

### 15.4 Registration (`POST /v1/registry/agents`)

#### 15.4.1 Request

```json
{
  "base_url": "https://my-agent.example.com",
  "protocol": "auto",
  "namespace": "acme-corp",
  "credentials": {
    "platform_to_agent": {
      "scheme": "bearer",
      "token": "agent-secret-xyz"
    },
    "agent_to_platform": {
      "scheme": "bearer",
      "token": "platform-secret-abc"
    }
  },
  "tags": ["gpu", "reasoning", "code-generation"],
  "mode": "native"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `base_url` | string | REQUIRED | Agent's root URL. Platform will probe this URL to detect capabilities (see Section 17). |
| `protocol` | string | OPTIONAL | Protocol hint: `"auto"` (default), `"aip"`, `"openai"`, `"anthropic"`, `"a2a"`. See Section 17. |
| `namespace` | string \| null | OPTIONAL | Requested namespace. Platform MAY override. Default: `null` (default namespace). |
| `credentials` | object \| null | OPTIONAL | Mutual authentication credentials (see 15.4.2). |
| `tags` | array[string] | OPTIONAL | Additional discovery tags. |
| `mode` | string | OPTIONAL | One of `"native"`, `"adapted"`, `"declared"`. Default: `"native"`. |
| `metadata` | object \| null | OPTIONAL | Arbitrary key-value pairs for the platform. |

#### 15.4.2 Mutual Authentication (`credentials`)

Registration establishes a **two-way trust** between platform and agent:

| Field | Purpose |
|-------|---------|
| `credentials.platform_to_agent` | Token the **platform** uses when calling the agent's endpoints. The agent validates this on incoming requests. |
| `credentials.agent_to_platform` | Token the **agent** uses when calling the platform (heartbeat, callbacks). The platform validates this on incoming requests. |

Each credential contains:

| Field | Type | Description |
|-------|------|-------------|
| `scheme` | string | `"bearer"`, `"api_key"`, `"hmac"`. |
| `token` | string | The secret value. |
| `header` | string \| null | Custom header name (for `api_key` scheme). Default: `Authorization`. |

If `credentials` is omitted, the platform and agent communicate without authentication (suitable for same-network / development use).

#### 15.4.3 Handshake Sequence

When the platform receives a registration request:

```
Agent/Adapter                         Platform
     │                                    │
     │  POST /v1/registry/agents          │
     │  { base_url, credentials, ... }    │
     │──────────────────────────────────►│
     │                                    │
     │     ┌──────────────────────────┐   │
     │     │ 1. Validate request      │   │
     │     │ 2. Probe GET {base_url}/ │   │
     │     │    v1/status             │   │
     │◄────│    (with platform_to_    │   │
     │     │     agent credential)    │   │
     │────►│ 3. Validate AgentStatus  │   │
     │     │ 4. Check version compat  │   │
     │     │ 5. Check namespace quota │   │
     │     │ 6. Store registration    │   │
     │     └──────────────────────────┘   │
     │                                    │
     │  201 Created                       │
     │  { agent_id, heartbeat_url,        │
     │    heartbeat_interval, ... }       │
     │◄──────────────────────────────────│
     │                                    │
     │  POST heartbeat (every 10s)        │
     │──────────────────────────────────►│
     │  { ack: true }                     │
     │◄──────────────────────────────────│
```

**Handshake validation steps (server MUST perform in order):**

1. **Schema validation** — request conforms to the registration schema.
2. **Protocol discovery** — if `protocol` is `"auto"` or omitted, run the auto-detection sequence (Section 17.3). If a specific protocol is given, probe only that profile. For `"aip"`, this means `GET {base_url}/v1/status`; for `"openai"`, `GET {base_url}/v1/models`; etc.
3. **AgentStatus construction** — for native AIP agents, validate that the response contains at least `agent_id` and `role`. For non-AIP agents, build a synthetic AgentStatus (Section 17.2).
4. **Version compatibility** — `supported_versions` in the status response includes at least one version the platform supports (AIP-native only).
5. **Namespace authorization** — the caller is allowed to register in the requested namespace.
6. **Quota check** — the namespace has not reached its agent limit.
7. **Duplicate check** — no existing active registration with the same `agent_id` in this namespace.

If any step fails, the platform returns the appropriate error code (see 15.10) and does NOT create the registration.

#### 15.4.4 Registration Response (201 Created)

```json
{
  "agent_id": "my-agent",
  "base_url": "https://my-agent.example.com",
  "namespace": "acme-corp",
  "mode": "native",
  "protocol_detected": "aip",
  "registered_at": "2026-03-12T10:00:00Z",
  "status": "active",
  "heartbeat_interval_seconds": 10,
  "heartbeat_url": "https://platform.example.com/v1/registry/agents/my-agent/heartbeat",
  "platform_aip_url": "https://platform.example.com/v1/aip",
  "capabilities_detected": ["streaming", "tasks", "artifacts"],
  "cached_status": { "...full AgentStatus from probe..." },
  "assignment": {
    "assigned_role": "backend-engineer",
    "team": "order-service",
    "scope": "Order service backend",
    "granted_tools": ["prod-db-readonly"],
    "constraints": ["No direct production writes"],
    "supervisor": "tech-lead-agent",
    "assigned_at": "2026-03-12T10:00:00Z"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | string | The agent's ID (from its AgentStatus or auto-detected). |
| `base_url` | string | Echoed back. |
| `protocol_detected` | string | Protocol profile detected or confirmed: `"aip"`, `"openai"`, `"a2a"`, `"unknown"`. See Section 17. |
| `namespace` | string | Assigned namespace (may differ from requested). |
| `mode` | string | Onboarding mode. |
| `registered_at` | string | ISO 8601 timestamp. |
| `status` | string | `"active"`, `"degraded"`, or `"failed"`. |
| `heartbeat_interval_seconds` | integer | How often the agent should heartbeat. Default: `10`. |
| `heartbeat_url` | string | Full URL for heartbeat POSTs. |
| `platform_aip_url` | string | The platform's AIP messaging endpoint — agents can send messages here. |
| `capabilities_detected` | array[string] | What the platform detected the agent supports (see 15.5). |
| `cached_status` | AgentStatus | The full AgentStatus from the probe. |
| `assignment` | AgentAssignment \| null | OPTIONAL. Initial assignment for this agent (see 5.12). `null` or omitted if no assignment. |

### 15.5 Capability Detection

During the handshake, the platform probes the agent to determine its capability level. This enables the platform to know **exactly** what it can ask this agent to do.

| Capability | How detected | Meaning |
|------------|-------------|---------|
| `status` | `GET /v1/status` returns 200 | Agent supports discovery. |
| `messaging` | `POST /v1/aip` with a `request_context` ping returns 200 | Agent accepts AIP messages. |
| `streaming` | `POST /v1/aip` with `Accept: text/event-stream` returns SSE | Agent supports SSE streaming. |
| `tasks` | `GET /v1/tasks/nonexistent` returns 404 (not 405/501) | Agent implements the Task API. |
| `artifacts` | `POST /v1/artifacts` returns 415 or 201 (not 405/501) | Agent supports file upload. |
| `callbacks` | `callback_url` field is echoed in AIPAck | Agent supports webhook callbacks. |

The `capabilities_detected` array in the registration response tells the agent (and platform operators) exactly what works. The platform SHOULD NOT send streaming requests to agents without the `streaming` capability.

### 15.6 Heartbeat (`POST /v1/registry/agents/{agent_id}/heartbeat`)

#### 15.6.1 Request

```json
{
  "ok": true,
  "lifecycle": "running",
  "pending_tasks": 3,
  "recent_errors": 0,
  "metrics": {
    "cpu_percent": 45.2,
    "memory_mb": 1024,
    "avg_response_ms": 230
  },
  "timestamp": "2026-03-12T10:05:00Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ok` | boolean | OPTIONAL | Agent is healthy. Default: `true`. |
| `lifecycle` | string | OPTIONAL | Current lifecycle state. |
| `pending_tasks` | integer | OPTIONAL | Number of in-flight tasks. |
| `recent_errors` | integer | OPTIONAL | Error count since last heartbeat. |
| `metrics` | object \| null | OPTIONAL | Custom operational metrics (cpu, memory, latency, etc.). |
| `timestamp` | string | REQUIRED | ISO 8601 UTC timestamp. |

#### 15.6.2 Response

```json
{
  "ack": true,
  "next_heartbeat_at": "2026-03-12T10:05:10Z",
  "commands": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ack` | boolean | `true` if heartbeat accepted. |
| `next_heartbeat_at` | string | When to send the next heartbeat. |
| `commands` | array[Command] | Platform-to-agent commands (see 15.6.3). |

#### 15.6.3 Platform Commands via Heartbeat

The heartbeat response MAY include **commands** — instructions from the platform to the agent. This enables the platform to control agents without initiating a separate connection.

| Command `type` | Description | Payload |
|----------------|-------------|---------|
| `refresh_status` | Agent should re-announce its status (e.g., after a skill update). | `{}` |
| `drain` | Agent should stop accepting new tasks and finish existing ones. | `{ "reason": "..." }` |
| `shutdown` | Agent should gracefully shut down and deregister. | `{ "reason": "...", "deadline": "..." }` |
| `update_config` | Platform pushes configuration to the agent. | `{ "config": { ... } }` |
| `re_register` | Agent should re-register (e.g., after platform migration). | `{ "new_platform_url": "..." }` |
| `assign` | Platform pushes or updates the agent's assignment (see 5.12). Agent MUST store the assignment and reflect it in `GET /v1/status`. | `AgentAssignment` object (see 5.12). Send `null` to clear. |

```json
{
  "ack": true,
  "next_heartbeat_at": "2026-03-12T10:05:10Z",
  "commands": [
    { "type": "drain", "payload": { "reason": "Platform maintenance at 11:00 UTC" } }
  ]
}
```

Agents SHOULD process commands and reflect the result in the next heartbeat. Agents MAY ignore commands they don't understand.

#### 15.6.4 Timeout and Lifecycle Rules

| Condition | Platform action |
|-----------|-----------------|
| Heartbeat received, `ok: true` | Status: `active`, lifecycle from heartbeat. |
| Heartbeat received, `ok: false` | Status: `active`, lifecycle: `degraded`. |
| No heartbeat for **3× interval** (30s at 10s interval) | Probe `GET {base_url}/v1/status`. If reachable: `degraded`. If unreachable: `failed`. |
| No heartbeat for **10× interval** (100s at 10s interval) | Status: `failed`. Platform MAY auto-deregister. Platform MUST emit event `agent.failed`. |
| Heartbeat resumes after failure | Status: `active`. Platform MUST emit event `agent.recovered`. |

### 15.7 Platform Events (Webhooks)

The platform SHOULD emit events when agent status changes. Platform operators and other agents can subscribe to these events.

| Event | Trigger |
|-------|---------|
| `agent.registered` | New agent successfully registered. |
| `agent.deregistered` | Agent removed from registry. |
| `agent.degraded` | Agent health dropped to degraded. |
| `agent.failed` | Agent is unreachable / heartbeat timeout. |
| `agent.recovered` | Agent came back from degraded/failed to active. |
| `agent.status_changed` | Any change in the cached AgentStatus (new skills, lifecycle change, etc.). |

Events are delivered as AIP messages to subscribers:

```json
{
  "version": "1.0",
  "message_id": "evt-001",
  "from": "platform",
  "to": "subscriber-agent",
  "action": "publish_status",
  "intent": "Agent agent-backend is now degraded",
  "payload": {
    "event": "agent.degraded",
    "agent_id": "agent-backend",
    "namespace": "acme-corp",
    "previous_status": "active",
    "current_status": "degraded",
    "reason": "heartbeat_timeout"
  }
}
```

### 15.8 Listing and Search (`GET /v1/registry/agents`)

| Parameter | Type | Description |
|-----------|------|-------------|
| `namespace` | string | Filter by namespace. |
| `role` | string | Filter by role. |
| `lifecycle` | string | Filter by lifecycle state. |
| `status` | string | Filter by registration status (`active`, `degraded`, `failed`). |
| `mode` | string | Filter by onboarding mode (`native`, `adapted`, `declared`). |
| `category` | string | Filter by `presentation.categories` value. |
| `skill` | string | Filter by skill ID or tag. |
| `ok` | boolean | Filter by health. |
| `q` | string | Free-text search across display_name, tagline, description, skill names. |
| `sort` | string | Sort field: `registered_at`, `last_heartbeat_at`, `agent_id`. Default: `registered_at`. |
| `order` | string | `asc` or `desc`. Default: `desc`. |
| `limit` | integer | Page size. Default: `50`. Max: `200`. |
| `offset` | integer | Pagination offset. Default: `0`. |

**Response:**

```json
{
  "agents": [
    {
      "agent_id": "agent-backend",
      "base_url": "https://my-agent.example.com",
      "namespace": "acme-corp",
      "mode": "native",
      "status": "active",
      "capabilities_detected": ["status", "messaging", "streaming", "tasks", "artifacts"],
      "registered_at": "2026-03-12T10:00:00Z",
      "last_heartbeat_at": "2026-03-12T10:05:30Z",
      "cached_status": { "...full AgentStatus with presentation, skills, auth..." }
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

### 15.9 Update (`PATCH /v1/registry/agents/{agent_id}`)

Used when an agent migrates to a new URL, changes namespace, or rotates credentials.

```json
{
  "base_url": "https://new-host.example.com",
  "credentials": {
    "platform_to_agent": { "scheme": "bearer", "token": "new-token" }
  }
}
```

The platform MUST re-probe `GET {new_base_url}/v1/status` before accepting the update. Returns `200 OK` with the updated `AgentRegistrationRecord`.

### 15.10 Deregistration (`DELETE /v1/registry/agents/{agent_id}`)

Graceful removal. The platform:

1. Returns `204 No Content`.
2. Stops expecting heartbeats.
3. Emits `agent.deregistered` event.
4. Removes the agent from discovery results.
5. Does NOT cancel in-flight tasks (the caller is responsible for draining first).

Agents SHOULD call this endpoint before shutting down. If they don't, the heartbeat timeout mechanism handles it.

### 15.11 Probe (`POST /v1/registry/agents/{agent_id}/probe`)

Platform-initiated health check — the "click retry" action. Used when a human operator or automated system wants to **immediately** verify whether a failed agent has recovered, without waiting for the next heartbeat.

**Request:** Empty body (`{}`). The platform uses its own stored `base_url` and credentials.

**Platform behavior:**

1. Look up the agent's `base_url` and `platform_to_agent` credential from the registry.
2. Call `GET {base_url}/v1/status` with a **5-second timeout**.
3. If the agent responds with a valid `AgentStatus`:
   - Update the agent's cached status.
   - Set lifecycle to the value from the response (typically `running`).
   - Mark as `active`.
   - Reset heartbeat tracking (expect next heartbeat within 1× interval).
   - Emit `agent.recovered` event if previously `failed` or `degraded`.
   - Return `200 OK` with the fresh `AgentStatus`.
4. If the agent does not respond or returns an error:
   - Keep the agent's current failed status.
   - Return `422` with error code `aip/registry/unreachable`.

**Success response (200):**

```json
{
  "agent_id": "claw-a",
  "status": "active",
  "lifecycle": "running",
  "probed_at": "2026-03-12T12:00:00Z",
  "cached_status": { "...fresh AgentStatus from probe..." }
}
```

**Failure response (422):**

```json
{
  "error_code": "aip/registry/unreachable",
  "error_message": "Agent claw-a did not respond within 5s at http://192.168.1.10:9090",
  "probed_at": "2026-03-12T12:00:00Z"
}
```

**Design notes:**

- The probe endpoint is idempotent — calling it on a healthy agent is harmless (it refreshes the cached status).
- Rate limiting: Platforms SHOULD limit probe frequency to prevent abuse (e.g., max 1 probe per agent per 5 seconds).
- The probe does NOT re-register the agent. Registration data (credentials, namespace, endpoints) remains unchanged.

### 15.12 Assignment (`PUT /v1/registry/agents/{agent_id}/assignment`)

Update the platform assignment for a registered agent. This is the imperative API for Section 5.12 — use it when the platform reassigns an agent at any time.

**Request:**

```json
{
  "assigned_role": "backend-engineer",
  "team": "order-service",
  "scope": "Order service backend — API design, implementation, code review",
  "granted_tools": ["prod-db-readonly", "staging-deploy"],
  "granted_skills": [
    { "id": "deploy", "name": "Deployment", "description": "Deploy to staging env" }
  ],
  "constraints": ["No direct production writes", "Max 10 concurrent tasks"],
  "supervisor": "tech-lead-agent",
  "priority": "high",
  "metadata": {}
}
```

The request body is a full `AgentAssignment` object. To clear the assignment, send an empty object `{}` — the platform resets all fields to their defaults (no assignment).

**Response (200 OK):**

```json
{
  "agent_id": "claw-a",
  "assignment": {
    "assigned_role": "backend-engineer",
    "team": "order-service",
    "scope": "Order service backend — API design, implementation, code review",
    "granted_tools": ["prod-db-readonly", "staging-deploy"],
    "constraints": ["No direct production writes", "Max 10 concurrent tasks"],
    "supervisor": "tech-lead-agent",
    "priority": "high",
    "assigned_at": "2026-03-12T14:30:00Z"
  }
}
```

**Error responses:**

| Code | HTTP | Description |
|------|------|-------------|
| `aip/registry/not_found` | 404 | Agent ID not found in registry. |
| `aip/registry/namespace_denied` | 403 | Caller not authorized for this agent's namespace. |

**Platform behavior after updating:**

1. Store the new assignment in the registry.
2. On the agent's next heartbeat ACK, include an `assign` command with the updated assignment so the agent reflects it locally.
3. Optionally also include a `refresh_status` command so the agent re-announces via `GET /v1/status`.

### 15.13 Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `aip/registry/unreachable` | 422 | Platform could not reach `{base_url}/v1/status` during handshake. |
| `aip/registry/invalid_status` | 422 | Status response did not conform to AgentStatus schema. |
| `aip/registry/version_incompatible` | 422 | No mutually supported protocol version. |
| `aip/registry/duplicate` | 409 | An agent with this `agent_id` is already registered in this namespace. |
| `aip/registry/namespace_denied` | 403 | Caller is not authorized for the requested namespace. |
| `aip/registry/quota_exceeded` | 429 | Namespace has reached its maximum agent count. |
| `aip/registry/auth_failed` | 401 | The provided credentials could not be validated. |
| `aip/registry/not_found` | 404 | Agent not found in registry (for heartbeat/update/delete). |

---

## 16. Multi-Agent Gateway

A single host frequently runs multiple agents — a coding agent, a search agent, a review agent, etc. Rather than burning one port per agent, AIP defines a **gateway** pattern: one process, one port, N agents, with standard discovery, routing, and isolation semantics.

### 16.1 URL Convention

A gateway exposes both **gateway-level** and **per-agent** endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/agents` | `GET` | List all hosted agents (discovery) |
| `/v1/agents/{agent_id}/status` | `GET` | AgentStatus for a specific agent |
| `/v1/agents/{agent_id}/aip` | `POST` | Send AIPMessage to a specific agent |
| `/v1/status` | `GET` | GroupStatus aggregating all hosted agents |
| `/v1/aip` | `POST` | Route message using the `to` field |
| `/health` | `GET` | Gateway health check |

Single-agent hosts MAY omit the `/v1/agents/` prefix and serve only the standard `/v1/status` and `/v1/aip` endpoints. Multi-agent hosts MUST implement both layers.

### 16.2 Discovery (`GET /v1/agents`)

Returns an array of `AgentStatus` objects — one per hosted agent.

```json
[
  {
    "agent_id": "coder",
    "role": "coder",
    "namespace": "my-team",
    "lifecycle": "running",
    "ok": true,
    "presentation": { "display_name": "OpenClaw Coder", "color": "#10B981" },
    "endpoints": {
      "aip": "https://gw.example.com/v1/agents/coder/aip",
      "status": "https://gw.example.com/v1/agents/coder/status"
    }
  },
  {
    "agent_id": "llama",
    "role": "assistant",
    "namespace": "my-team",
    "lifecycle": "running",
    "ok": true,
    "presentation": { "display_name": "Ollama Llama3", "color": "#3B82F6" }
  }
]
```

### 16.3 Message Routing (`POST /v1/aip`)

When a gateway receives a message at the root `/v1/aip`:

1. Inspect the `to` field in the AIPMessage.
2. If `to` matches a hosted `agent_id`, route to that agent's backend.
3. If `to` does not match any hosted agent, return error `aip/protocol/agent_not_found` with HTTP 404.

```json
{
  "ok": false,
  "error_code": "aip/protocol/agent_not_found",
  "error_message": "No agent 'unknown-id' on this gateway. Available: [coder, llama]"
}
```

Callers MAY bypass routing by using the per-agent path `/v1/agents/{agent_id}/aip` directly.

### 16.4 Aggregated Status (`GET /v1/status`)

Returns a `GroupStatus` where:
- `ok` is `true` only if ALL hosted agents are healthy.
- `agents` contains the full `AgentStatus` array.

```json
{
  "ok": true,
  "service": "aip",
  "namespace": "my-team",
  "root_agent_id": "gateway-hostname",
  "timestamp": "2026-03-12T12:00:00Z",
  "agents": [ ... ]
}
```

### 16.5 Platform Registration

When a gateway registers with a platform, it MUST register each agent independently. The registration payload MUST include explicit `endpoints` so the platform knows the per-agent paths:

```json
{
  "agent_id": "coder",
  "base_url": "https://gw.example.com",
  "namespace": "my-team",
  "endpoints": {
    "aip": "https://gw.example.com/v1/agents/coder/aip",
    "status": "https://gw.example.com/v1/agents/coder/status"
  }
}
```

Each agent maintains its own heartbeat. The platform treats each as an independent agent — it has no concept of "gateway" vs "standalone."

### 16.6 Isolation Requirements

| Requirement | Description |
|-------------|-------------|
| **Fault isolation** | If one backend is unreachable, the gateway MUST continue serving all other agents. The failed agent's status reports `ok: false, lifecycle: "failed"`. |
| **Independent state** | Each agent has its own task counter, error state, and lifecycle. A failure in agent A MUST NOT affect agent B. |
| **Namespace inheritance** | Agents inherit the gateway's `namespace` unless the agent-specific config overrides it. |
| **Graceful shutdown** | On SIGTERM, the gateway SHOULD: (1) stop accepting new connections, (2) drain in-flight requests with a reasonable timeout, (3) deregister each agent from the platform, (4) close all backend connections. |

### 16.7 Hot Reload (OPTIONAL)

Implementations MAY support configuration reload without restart. The recommended mechanism is `SIGHUP`:

1. Re-read the config file.
2. Connect new agents, remove deleted agents.
3. For changed agents: gracefully drain the old backend, then switch to the new one.
4. Log which agents were added/removed/changed.

### 16.8 Gateway Configuration (Informative)

A gateway is typically configured via a YAML file:

```yaml
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
    tags: [coding, reasoning]
    color: "#10B981"

  - id: llama
    url: http://localhost:11434/v1/chat/completions
    format: openai
    name: Ollama Llama3
    tags: [llm, general]
    color: "#3B82F6"

  - id: workflow
    url: https://api.dify.ai/v1/chat-messages
    format: dify
    secret: app-xxx
    name: Dify Workflow
    tags: [workflow, automation]
    color: "#8B5CF6"
```

The reference implementation launches the gateway with:

```
aip bridge --config gateway.yaml
```

### 16.9 Edge Cases and Operational Considerations

| Scenario | Required Behavior |
|----------|-------------------|
| Duplicate agent IDs in config | MUST reject at startup with a clear error. |
| Backend responds but with errors | Set `ok: false` and `last_error` on that agent. Keep serving requests (which will return 503 for that agent). |
| Platform unavailable at startup | Log a warning, continue in standalone mode. Retry registration in the background. |
| Agent added at runtime (hot reload) | Connect transport, probe health, register with platform, start heartbeat. |
| Agent removed at runtime | Stop heartbeat, deregister from platform, drain in-flight, close transport. |
| All agents down | `GET /v1/status` returns `ok: false`. `GET /health` returns `{"ok": false, "agents": {...}}`. The gateway itself stays up. |
| Message to non-existent agent | Return `aip/protocol/agent_not_found` with HTTP 404 and list available agent IDs. |
| Large number of agents (100+) | Implementations SHOULD use connection pooling and async I/O. Per-agent timeouts prevent one slow agent from blocking others. |

---

## 17. Platform-Side Agent Discovery

### 17.1 Motivation

Section 15 defines how agents register with a platform via `POST /v1/registry/agents`. That flow assumes the agent (or a bridge process) initiates registration and speaks AIP natively — exposing `GET /v1/status` and `POST /v1/aip`.

Many real-world agents do NOT speak AIP. They expose OpenAI-compatible chat/completions, Google A2A agent cards, or other common APIs. Requiring every such agent to run a sidecar bridge process adds operational friction.

**Platform-Side Agent Discovery** inverts the responsibility: the **platform** probes a URL, auto-detects the agent's native protocol, builds a synthetic `AgentStatus`, and handles all protocol translation server-side. The agent machine runs exactly what it already runs — nothing more.

### 17.2 Protocol Profiles

A **protocol profile** defines how the platform interacts with a specific class of agents. Each profile specifies:

1. **Detection** — which endpoint to probe and what a valid response looks like.
2. **Status mapping** — how to construct an `AgentStatus` from the native response.
3. **Message translation** — how to convert `POST /v1/aip` messages to the native API.
4. **Health probe** — how to periodically check the agent is alive.

The following profiles are RECOMMENDED for platform implementations. Platforms MAY support additional profiles.

| Profile | Detection Probe | Message Endpoint | Health Probe |
|---------|----------------|------------------|-------------|
| `aip` | `GET {url}/v1/status` returns valid `AgentStatus` | `POST {url}/v1/aip` (native) | `GET {url}/v1/status` |
| `openai` | `GET {url}/v1/models` returns `{ data: [...] }` | `POST {url}/v1/chat/completions` | `GET {url}/v1/models` |
| `anthropic` | `POST {url}/v1/messages` with minimal payload returns 200/400 (not 404) | `POST {url}/v1/messages` | `GET {url}/v1/models` or TCP connect |
| `a2a` | `GET {url}/.well-known/agent.json` returns valid agent card | Per A2A spec | `GET {url}/.well-known/agent.json` |

#### 17.2.1 Profile: `aip` (Native)

No translation required. The platform communicates directly using the AIP protocol. This is the standard flow described in Section 15.

#### 17.2.2 Profile: `openai` (OpenAI-Compatible)

Covers: OpenClaw, Ollama, vLLM, LiteLLM, LM Studio, LocalAI, OpenRouter, and any server implementing the OpenAI chat/completions API.

**Detection:**

```
GET {base_url}/v1/models
→ 200 { "data": [{ "id": "model-name", ... }, ...] }
```

A 200 response with a JSON object containing a `data` array of model objects confirms the agent speaks OpenAI-compatible API.

**Status mapping:**

| AIP field | Source |
|-----------|--------|
| `agent_id` | First model's `id`, or hostname-derived |
| `role` | `"agent"` |
| `lifecycle` | `"running"` |
| `ok` | `true` |
| `capabilities` | `["messaging"]` (add `"streaming"` if SSE is supported) |
| `presentation.display_name` | Derived from model ID or hostname |
| `supported_versions` | `["1.0"]` |
| `metadata.protocol` | `"openai"` |
| `metadata.models` | Array of available model IDs |

**Message translation (AIP → OpenAI):**

```
AIPMessage { intent, payload }
→ POST {base_url}/v1/chat/completions
  { "model": "<first_model>", "messages": [{"role": "user", "content": "<intent>"}] }
```

If `payload.messages` is present, they are prepended as conversation history.

**Health probe:**

```
GET {base_url}/v1/models → 200 = healthy
```

#### 17.2.3 Profile: `a2a` (Google Agent-to-Agent)

**Detection:**

```
GET {base_url}/.well-known/agent.json
→ 200 { "name": "...", "description": "...", "skills": [...], ... }
```

**Status mapping:**

| AIP field | Source |
|-----------|--------|
| `agent_id` | Agent card `url` or `name` (slugified) |
| `role` | `"agent"` |
| `presentation.display_name` | Agent card `name` |
| `presentation.description` | Agent card `description` |
| `skills` | Mapped from agent card `skills` |
| `metadata.protocol` | `"a2a"` |

### 17.3 Auto-Detection Algorithm

When an agent is registered with `protocol: "auto"` (or protocol omitted), the platform MUST run the following detection sequence. The platform stops at the first successful probe.

```
1. GET {base_url}/v1/status
   → Valid AgentStatus?  → protocol = "aip"

2. GET {base_url}/.well-known/agent.json
   → Valid agent card?   → protocol = "a2a"

3. GET {base_url}/v1/models
   → JSON with data[]?   → protocol = "openai"

4. GET {base_url}/health  (or GET {base_url}/api/health)
   → 200?                → protocol = "unknown" (health-only, no messaging)

5. TCP connect to {host}:{port}
   → Success?            → protocol = "unknown" (alive but no known API)

6. All probes fail       → Return 422 "Agent unreachable"
```

Each probe MUST use a timeout of **5 seconds**. The total discovery sequence SHOULD complete within **15 seconds**.

### 17.4 Registration with Protocol Hint

The `POST /v1/registry/agents` request (Section 15.4) is extended with an OPTIONAL `protocol` field:

```json
{
  "base_url": "http://192.168.1.10:3000",
  "protocol": "auto",
  "namespace": "acme-corp",
  "tags": ["coding", "agent"]
}
```

| Value | Behavior |
|-------|----------|
| `"auto"` (default) | Platform runs the full detection sequence (17.3). |
| `"aip"` | Platform probes `GET {url}/v1/status` only. Fails if not AIP-native. |
| `"openai"` | Platform probes `GET {url}/v1/models` only. Translates messages accordingly. |
| `"anthropic"` | Platform uses Anthropic messages API. |
| `"a2a"` | Platform probes `GET {url}/.well-known/agent.json`. |
| _(other)_ | Platform-specific custom profile. |

When `protocol` is not `"aip"`, the platform constructs a synthetic `AgentStatus` from the discovery result (see 17.2). This status is stored as `cached_status` in the registration record.

The registration response includes the detected protocol:

```json
{
  "agent_id": "openclaw-coder",
  "base_url": "http://192.168.1.10:3000",
  "protocol_detected": "openai",
  "status": "active",
  "capabilities_detected": ["messaging"],
  "cached_status": { "...synthetic AgentStatus..." },
  "...other standard fields..."
}
```

### 17.5 Server-Side Translation

When the platform receives an AIP message destined for a non-AIP agent (via `POST /v1/aip` with routing, or via the platform's message router), the platform MUST translate the message according to the agent's protocol profile.

**Translation rules:**

1. The platform extracts `intent` and `payload` from the `AIPMessage`.
2. The platform encodes them using the profile's message translation rules (17.2).
3. The platform sends the translated request to the agent's `base_url`.
4. The platform decodes the native response and wraps it in an `AIPAck` or SSE stream.

Platforms MUST preserve `message_id`, `correlation_id`, and `trace_id` across translation boundaries. These fields SHOULD be stored in the platform's trace system even though the native agent does not use them.

### 17.6 Health Monitoring for Non-AIP Agents

For agents registered with a non-AIP protocol, the platform MUST periodically health-check using the profile's health probe (17.2) instead of expecting heartbeats.

| Parameter | Value |
|-----------|-------|
| Probe interval | Same as `heartbeat_interval_seconds` (default: 10s). |
| Probe timeout | 5 seconds. |
| Degraded threshold | 3 consecutive probe failures. |
| Failed threshold | 10 consecutive probe failures. |

The same lifecycle rules from Section 15.6.4 apply. The platform MUST emit the same events (`agent.degraded`, `agent.failed`, `agent.recovered`).

### 17.7 Example: Adding an OpenClaw Agent Without a Bridge

**Machine A** runs OpenClaw on port 3000. No AIP bridge, no sidecar, no extra process.

**Platform admin** (or automation) runs:

```bash
curl -X POST https://platform.example.com/v1/registry/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $PLATFORM_SECRET" \
  -d '{
    "base_url": "http://192.168.1.10:3000",
    "namespace": "dev-team",
    "tags": ["coding", "agent"],
    "credentials": {
      "platform_to_agent": {
        "scheme": "bearer",
        "token": "openclaw-gateway-token"
      }
    }
  }'
```

**What the platform does:**

1. Probes `GET http://192.168.1.10:3000/v1/status` → 404 (not AIP).
2. Probes `GET http://192.168.1.10:3000/.well-known/agent.json` → 404 (not A2A).
3. Probes `GET http://192.168.1.10:3000/v1/models` → 200 `{ "data": [{ "id": "openclaw-v1" }] }` → **OpenAI-compatible**.
4. Builds synthetic `AgentStatus`:
   ```json
   {
     "agent_id": "openclaw-v1",
     "role": "agent",
     "namespace": "dev-team",
     "presentation": {
       "display_name": "openclaw-v1 @ 192.168.1.10",
       "categories": ["coding", "agent"]
     },
     "lifecycle": "running",
     "ok": true,
     "base_url": "http://192.168.1.10:3000",
     "capabilities": ["messaging"],
     "supported_versions": ["1.0"],
     "metadata": {
       "protocol": "openai",
       "models": ["openclaw-v1"]
     }
   }
   ```
5. Returns 201 with the registration, including `"protocol_detected": "openai"`.
6. Starts health-checking `GET /v1/models` every 10 seconds.

**Result:** The agent appears in the platform dashboard immediately. Other agents can send it tasks. The platform translates AIP → OpenAI chat/completions transparently.

### 17.8 Protocol Profile Extensibility

Platforms MAY define custom protocol profiles beyond those listed in 17.2. Custom profiles MUST use a namespaced identifier (e.g., `x-myplatform/custom-agent`).

A platform that detects an unknown protocol SHOULD still register the agent with `protocol: "unknown"` and `capabilities: []`. The agent will be visible in the registry (for monitoring) but will not accept messages until a profile is configured.

---

## 18. Standard Action Payload Schemas

### 18.1 Overview

Section 4.2 defines the standard action names. This section defines the RECOMMENDED `payload` structure for each action. Implementations SHOULD follow these schemas for standard actions to ensure interoperability across platforms.

All fields in action payloads are OPTIONAL unless stated otherwise. Receivers MUST accept payloads with additional fields they do not understand (forward-compatible).

### 18.2 `assign_task`

A coordinator delegates a unit of work to another agent.

```json
{
  "instruction": "Design the order service REST API with OpenAPI output",
  "deliverables": ["openapi", "risk_report"],
  "deadline": "2026-03-14T18:00:00Z",
  "context": {
    "project": "e-commerce-backend",
    "requirements_url": "https://docs.example.com/requirements/orders"
  },
  "budget": {
    "max_tokens": 100000,
    "max_cost_usd": 5.00
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `instruction` | string | REQUIRED. The task description in natural language. |
| `deliverables` | array[string] | OPTIONAL. Expected output artifact types or names. |
| `deadline` | string (ISO 8601) | OPTIONAL. Soft deadline for completion. |
| `context` | object | OPTIONAL. Arbitrary context for the task (project info, references, etc.). |
| `budget` | object | OPTIONAL. Resource constraints: `max_tokens`, `max_cost_usd`, `max_duration_seconds`. |
| `parent_task_id` | string | OPTIONAL. Links this sub-task to a parent task for decomposition tracking. |
| `tools` | array[string] | OPTIONAL. Tools the assignee is authorized to use for this task. |

### 18.3 `submit_report`

An agent delivers work results back to its requester.

```json
{
  "summary": "Order service API draft complete. 12 endpoints defined.",
  "status": "completed",
  "artifacts": [
    { "artifact_id": "art-001", "name": "orders-api.yaml", "mime_type": "application/yaml" }
  ],
  "metrics": {
    "tokens_used": 45000,
    "duration_seconds": 120,
    "estimated_cost_usd": 2.30
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `summary` | string | REQUIRED. Human-readable summary of the work done. |
| `status` | string | OPTIONAL. `"completed"`, `"partial"`, `"failed"`. Default: `"completed"`. |
| `artifacts` | array[Artifact] | OPTIONAL. Produced artifacts (files, data). |
| `metrics` | object | OPTIONAL. Execution metrics: `tokens_used`, `duration_seconds`, `estimated_cost_usd`. |
| `issues` | array[string] | OPTIONAL. Problems encountered during execution. |
| `next_steps` | array[string] | OPTIONAL. Suggested follow-up actions. |

### 18.4 `request_context`

An agent requests information or resources from another agent.

```json
{
  "question": "What are the current database schema constraints for the orders table?",
  "scope": "technical",
  "format": "text/plain",
  "urgency": "normal"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `question` | string | REQUIRED. The information request in natural language. |
| `scope` | string | OPTIONAL. Narrows the context domain: `"technical"`, `"business"`, `"operational"`. |
| `format` | string | OPTIONAL. Preferred response format MIME type. |
| `references` | array[string] | OPTIONAL. URIs to relevant resources the respondent should consider. |

### 18.5 `request_approval`

An agent requests sign-off before proceeding.

```json
{
  "action_description": "Deploy order-service v2.1.0 to production",
  "risk_level": "high",
  "impact": "Affects all active orders. Estimated 2-minute downtime.",
  "rollback_plan": "Revert to v2.0.3 via blue-green deployment",
  "evidence": [
    { "artifact_id": "art-002", "name": "test-report.html", "mime_type": "text/html" }
  ],
  "deadline": "2026-03-14T16:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `action_description` | string | REQUIRED. What is being approved. |
| `risk_level` | string | OPTIONAL. `"low"`, `"medium"`, `"high"`, `"critical"`. |
| `impact` | string | OPTIONAL. Human-readable impact assessment. |
| `rollback_plan` | string | OPTIONAL. How to undo the action if it goes wrong. |
| `evidence` | array[Artifact] | OPTIONAL. Supporting evidence (test reports, analysis). |
| `deadline` | string (ISO 8601) | OPTIONAL. Approval needed by this time. |
| `options` | array[string] | OPTIONAL. Available choices beyond approve/reject (e.g., `"approve_with_conditions"`). |

### 18.6 `user_instruction`

A human user gives a directive to an agent.

```json
{
  "instruction": "Focus on the payment integration first, skip the email notifications for now",
  "context": {
    "conversation_id": "conv-001",
    "thread": "backend-api-design"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `instruction` | string | REQUIRED. The human's directive in natural language. |
| `context` | object | OPTIONAL. Conversation context, thread references, etc. |
| `attachments` | array[Artifact] | OPTIONAL. Files or images the user is sharing. |

### 18.7 `handoff`

Transfer responsibility for a task to another agent.

```json
{
  "task_id": "task-001",
  "reason": "Requires frontend expertise beyond my capabilities",
  "context_summary": "API design is 80% complete. Remaining: frontend integration testing.",
  "artifacts": [
    { "artifact_id": "art-003", "name": "api-draft.yaml", "mime_type": "application/yaml" }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | REQUIRED. The task being handed off. |
| `reason` | string | REQUIRED. Why the handoff is happening. |
| `context_summary` | string | OPTIONAL. Summary of work done so far. |
| `artifacts` | array[Artifact] | OPTIONAL. In-progress artifacts to transfer. |

### 18.8 `escalate`

Escalate an issue to a higher-authority agent.

```json
{
  "task_id": "task-001",
  "severity": "high",
  "reason": "Conflicting requirements between API spec and database constraints",
  "attempted_resolution": "Tried normalizing the schema but breaks backward compatibility",
  "suggested_action": "Decision needed: break backward compatibility or add migration layer"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | OPTIONAL. Related task. |
| `severity` | string | REQUIRED. `"low"`, `"medium"`, `"high"`, `"critical"`. |
| `reason` | string | REQUIRED. What went wrong or needs attention. |
| `attempted_resolution` | string | OPTIONAL. What the agent already tried. |
| `suggested_action` | string | OPTIONAL. What the agent thinks should happen. |

### 18.9 `publish_status`

Broadcast a status update (used by platforms for event distribution).

```json
{
  "event": "agent.degraded",
  "agent_id": "agent-backend",
  "previous_status": "active",
  "current_status": "degraded",
  "reason": "3 consecutive heartbeat failures",
  "timestamp": "2026-03-12T10:05:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `event` | string | REQUIRED. Event type (e.g., `"agent.registered"`, `"agent.failed"`). |
| `agent_id` | string | REQUIRED. Affected agent. |
| `previous_status` | string | OPTIONAL. Status before the event. |
| `current_status` | string | OPTIONAL. Status after the event. |
| `reason` | string | OPTIONAL. Human-readable explanation. |
| `timestamp` | string (ISO 8601) | OPTIONAL. When the event occurred. |

### 18.10 Schema Enforcement

- Senders SHOULD validate their payloads against these schemas before sending.
- Receivers MUST NOT reject a message solely because the payload contains unknown fields.
- Receivers MAY return `aip/execution/invalid_payload` if REQUIRED fields are missing.
- The `instruction` field (present in `assign_task`, `user_instruction`) is the minimum viable payload — agents SHOULD be able to act on `instruction` alone.

---

## 19. Message Routing

### 19.1 Scope

This section defines how AIP messages are routed between agents. Routing is a **platform responsibility** — the protocol defines the rules, platforms implement them.

Individual agents are NOT required to implement routing. An agent only needs to handle messages addressed to itself.

### 19.2 Routing Model

AIP uses a **hub-and-spoke** model: agents connect to a platform, and the platform routes messages between them.

```
Agent A ──► Platform ──► Agent B
              │
              └──► Agent C
```

There is no requirement for agents to connect directly to each other. The platform acts as the message bus.

### 19.3 Routing Fields

The `AIPMessage` contains several fields that inform routing decisions:

| Field | Purpose |
|-------|---------|
| `to` | REQUIRED. Target agent ID. The platform resolves this to a registered agent. |
| `to_role` | OPTIONAL. If `to` is not found, route to any agent matching this role. |
| `to_host` | OPTIONAL. Target hostname for cross-host routing. |
| `to_base_url` | OPTIONAL. Direct URL override — bypass registry lookup. |
| `route_scope` | OPTIONAL. `"local"` (same host) or `"remote"` (cross-host). Default: `"local"`. |

### 19.4 Routing Algorithm

When a platform receives `POST /v1/aip`, it MUST apply the following routing logic:

1. **Direct match**: If `to` matches a registered `agent_id`, route to that agent.
2. **Role match**: If no direct match and `to_role` is set, route to any healthy agent with that role in the same namespace.
3. **URL override**: If `to_base_url` is set, send directly to that URL (skip registry).
4. **Self-handling**: If `to` matches the platform's own ID, the platform handles the message itself.
5. **Not found**: If no match, return `aip/protocol/agent_not_found`.

### 19.5 Delivery Semantics

| Requirement | Rule |
|-------------|------|
| **At-least-once** | The platform MUST attempt delivery at least once. |
| **Idempotency** | The platform SHOULD deduplicate messages using `message_id` + `Idempotency-Key`. |
| **Ordering** | Messages with the same `correlation_id` SHOULD be delivered in order. The platform MAY relax this for messages with different `correlation_id` values. |
| **Timeout** | If the target agent does not respond within 120 seconds (or the platform's configured timeout), the platform MUST return `aip/protocol/agent_unavailable`. |
| **Retry** | For transient failures (5xx, timeout), the platform SHOULD retry with exponential backoff (max 3 attempts). |

### 19.6 Response Forwarding

When the platform routes a message to Agent B on behalf of Agent A:

1. The platform forwards Agent B's response (AIPAck or SSE stream) back to Agent A.
2. The platform MUST NOT modify the response content, but MAY add trace metadata.
3. If Agent B returns an SSE stream, the platform MUST forward the stream events to Agent A as-is.
4. The platform SHOULD record the exchange in its trace system (Section 10).

### 19.7 Namespace Isolation

Messages are routed within namespace boundaries:

- An agent in namespace `"team-a"` can only send to agents in `"team-a"` by default.
- Cross-namespace messaging requires explicit platform policy (`route_scope: "remote"` or a platform-level ACL).
- The platform MUST enforce namespace isolation unless explicitly configured otherwise.

### 19.8 Callback Routing

When an `AIPMessage` includes `callback_url`:

1. The platform routes the message to the target agent normally.
2. When the task completes (or reaches a terminal state), the target agent (or the platform) sends the result to the `callback_url` via `POST`.
3. If `callback_secret` is set, the callback payload MUST be signed with HMAC-SHA256 using the secret, with the signature in the `X-AIP-Signature` header.

---

## 20. Error Response Format (RFC 7807)

### 20.1 Motivation

AIP error responses (Section 9.3) use `AIPAck` with `ok: false`. For richer error reporting — especially for platform-level errors that are not part of a message exchange — AIP RECOMMENDS RFC 7807 Problem Details format.

### 20.2 Problem Details Object

Platforms and agents MAY return errors in RFC 7807 format with `Content-Type: application/problem+json`:

```json
{
  "type": "https://aip-protocol.dev/errors/aip/protocol/agent_not_found",
  "title": "Agent Not Found",
  "status": 404,
  "detail": "No agent with ID 'agent-backend' is registered in namespace 'acme-corp'.",
  "instance": "/v1/registry/agents/agent-backend",
  "aip_error_code": "aip/protocol/agent_not_found",
  "trace_id": "abc-123"
}
```

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `type` | string (URI) | RFC 7807 | URI identifying the error type. RECOMMENDED: `https://aip-protocol.dev/errors/{error_code}`. |
| `title` | string | RFC 7807 | Short human-readable summary. |
| `status` | integer | RFC 7807 | HTTP status code. |
| `detail` | string | RFC 7807 | Human-readable explanation specific to this occurrence. |
| `instance` | string | RFC 7807 | URI reference to the specific request that caused the error. |
| `aip_error_code` | string | AIP extension | The AIP error code from Section 9.1. |
| `trace_id` | string | AIP extension | Trace ID for correlating with the observability system. |

### 20.3 Compatibility

- AIP messages (POST /v1/aip) SHOULD continue to use `AIPAck` with `ok: false` for backward compatibility.
- Platform endpoints (registry, traces, usage) MAY use RFC 7807 for error responses.
- Clients SHOULD check `Content-Type` to determine the error format.
- Returning RFC 7807 is OPTIONAL but RECOMMENDED for new platform implementations.

---

## Appendix C: Relationship to Other Protocols

(See also Appendix B for JSON-RPC 2.0 interoperability.)

| Protocol | Focus | Relationship to AIP |
|----------|-------|---------------------|
| **MCP** (Model Context Protocol) | Model ↔ Tool connection | Complementary. MCP connects a model to tools; AIP connects agents to agents. An agent may use MCP internally to call tools. |
| **A2A** (Google Agent-to-Agent) | Agent-to-agent task delegation | Overlapping scope. AIP additionally provides governance, recursive status, and organizational authority. |
| **OpenAI Realtime API** | Model ↔ User streaming | Complementary. AIP is for agent-to-agent; OpenAI Realtime is for user-to-model. |

## Appendix D: Reference Implementations

- **Python SDK**: `sdk-python/` — reference implementation with sync/async/streaming clients
- **Go SDK**: `sdk-go/` — Go implementation with streaming and task management
- **Java SDK**: `sdk-java/` — Java implementation with streaming and task management
- **JS/TS SDK**: `sdk-js/` — JavaScript/TypeScript implementation with streaming and task management
- **Ants**: Multi-agent runtime built on AIP — full reference coordinator/worker system
