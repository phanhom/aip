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

## 10. Observability

### 10.1 Distributed Tracing

AIP messages carry `trace_id` and `correlation_id` fields for end-to-end tracing. Implementations SHOULD propagate these fields through all downstream messages and log entries.

### 10.2 Logging

Implementations SHOULD log:
- Message send/receive events with `message_id`, `action`, and `trace_id`.
- Retry attempts with delay and attempt number.
- Final failure with error type and total attempts.

The protocol library SHOULD expose hooks for custom loggers and structured log fields.

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
