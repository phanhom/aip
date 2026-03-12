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

- **Messaging Protocol** — a structured JSON envelope for agent-to-agent and human-to-agent communication via `POST /aip`.
- **Status Protocol** — a self-describing discovery mechanism via `GET /status` that enables zero-configuration agent discovery.

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

- Messaging endpoint: `POST /aip`
- Status endpoint: `GET /status`
- Content-Type: `application/json`
- Character encoding: UTF-8

Implementations MAY support additional transports (WebSocket, gRPC, NATS, etc.) provided the message semantics defined in this specification are preserved.

### 2.2 HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Message accepted. Response body is an `AIPAck`. |
| `400` | Routing error (e.g., `to` does not match the receiving agent). |
| `401` | Authentication required. |
| `403` | Forbidden (insufficient authority or approval). |
| `422` | Message validation failed. |
| `429` | Rate limited. |
| `503` | Upstream or forwarding target unavailable. |

### 2.3 TLS

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

Every AIP-compliant agent MUST expose `GET /status` and SHOULD include the following discovery fields in its response:

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

#### 4.1.4 Observability Layer

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

Every `POST /aip` handler MUST return an `AIPAck` on success:

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
| `correlation_id` | string \| null | OPTIONAL | Echoed `correlation_id` if present. |

### 4.4 Human as Sender

Humans are not a special protocol branch. A human sends messages using the same `AIPMessage` format:

- `from`: `"user"` (or a user-specific identifier)
- `from_role`: `"user"` (RECOMMENDED)

Receivers distinguish human messages via `from_role` for display, permissions, and audit — not via a separate protocol path.

---

## 5. Status Protocol

### 5.1 `GET /status`

Every AIP-compliant agent MUST implement `GET /status`. The response describes the agent's identity, health, capabilities, and optionally its subordinates.

### 5.2 Query Scopes

| Scope | Applicable To | Description |
|-------|---------------|-------------|
| `self` | Any agent | Returns only the current agent's status. |
| `subtree` | Any agent | Returns the agent and all its subordinates as a recursive tree. |
| `group` | Coordinator | Returns a flat aggregate view of the entire group. |

The scope is specified via query parameter: `GET /status?scope=self`.

- Workers SHOULD default to `scope=self`.
- Coordinators SHOULD default to `scope=group`.
- Coordinators SHOULD support `GET /status?scope=subtree&root=<agent_id>`.

### 5.3 Agent Status (`AgentStatus`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_id` | string | REQUIRED | Unique identifier for this agent. |
| `role` | string | REQUIRED | Agent's role in the group. |
| `superior` | string \| null | OPTIONAL | Agent ID of the direct superior. |
| `authority_weight` | integer \| null | OPTIONAL | Agent's authority weight (0-100). |
| `lifecycle` | string \| null | OPTIONAL | One of: `"idle"`, `"starting"`, `"running"`, `"blocked"`, `"degraded"`, `"failed"`. |
| `port` | integer \| null | OPTIONAL | Service port. |
| `ok` | boolean | OPTIONAL | `true` if the agent is healthy. Default: `true`. |
| `base_url` | string \| null | OPTIONAL | Agent's base URL for discovery. |
| `endpoints` | object \| null | OPTIONAL | `{ "aip": "...", "status": "..." }` |
| `capabilities` | array[string] | OPTIONAL | List of supported actions or skills. |
| `supported_versions` | array[string] | OPTIONAL | Protocol versions this agent supports. |
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
| `root_agent_id` | string | Root coordinator agent ID. |
| `timestamp` | string | ISO 8601 generation timestamp. |
| `topology` | object | Map of agent_id to list of direct subordinate IDs. |
| `waiting_for_approval` | boolean | Whether any agent in the group is blocked on approval. |
| `agents` | array[AgentStatus] | Flat list of all agent statuses. |

---

## 6. Governance

### 6.1 Approval Workflow

AIP provides first-class support for human-in-the-loop governance:

- Any message that may affect production environments SHOULD set `requires_approval: true`.
- Agents MUST NOT execute production-impacting actions unless `approval_state` is `"approved"`.
- The `approval_state` field tracks the lifecycle: `"not_required"` → `"waiting_human"` → `"approved"` | `"rejected"`.

### 6.2 Authority Weight

The `authority_weight` field (0-100) represents organizational authority. It is advisory, not enforced by the protocol, but implementations MAY use it for:

- Routing decisions (prefer higher-authority sources)
- Task prioritization
- Approval policy (auto-approve if `authority_weight >= threshold`)

---

## 7. Reliability

### 7.1 Retry Semantics

Implementations SHOULD retry on transient failures (5xx, timeout, connection errors) with exponential backoff and jitter. Implementations MUST NOT retry on 4xx client errors.

**Recommended defaults:**

| Parameter | Value |
|-----------|-------|
| Timeout | 30 seconds |
| Max retries | 4 (1 initial + 3 retries) |
| Backoff base | 1.0 seconds |
| Backoff max | 60.0 seconds |
| Backoff jitter | ±20% |

### 7.2 Idempotency

Senders MAY include an `Idempotency-Key` HTTP header or an idempotency key in the payload. Receivers SHOULD use this to deduplicate messages.

### 7.3 Message Persistence

Receivers SHOULD persist all incoming AIP messages to a durable log (e.g., JSONL file, database) for auditability and replay.

---

## 8. Observability

### 8.1 Distributed Tracing

AIP messages carry `trace_id` and `correlation_id` fields for end-to-end tracing. Implementations SHOULD propagate these fields through all downstream messages and log entries.

### 8.2 Logging

Implementations SHOULD log:
- Message send/receive events with `message_id`, `action`, and `trace_id`.
- Retry attempts with delay and attempt number.
- Final failure with error type and total attempts.

The protocol library SHOULD expose hooks for custom loggers and structured log fields.

---

## 9. Versioning and Evolution

### 9.1 Version Format

Protocol versions follow semantic versioning: `MAJOR.MINOR`.

- **MAJOR** version changes indicate breaking changes.
- **MINOR** version changes are backward-compatible additions.

### 9.2 Compatibility Rules

- New fields MUST be OPTIONAL with sensible defaults.
- New actions MUST NOT change the semantics of existing actions.
- Receivers MUST ignore unknown fields (forward compatibility).
- Receivers SHOULD NOT reject messages with unknown actions; they MAY respond with an appropriate error in the `AIPAck`.

### 9.3 Version Negotiation

Agents SHOULD declare `supported_versions` in their status response. Senders SHOULD use the highest mutually supported version. If version negotiation is not performed, version `"1.0"` is assumed.

---

## 10. Extension Mechanism

### 10.1 Custom Actions

Implementations MAY define custom actions using a namespaced prefix:

```
x-<organization>/<action_name>
```

Example: `x-acme/deploy_canary`

Custom actions MUST NOT collide with standard actions defined in Section 4.2.

### 10.2 Custom Fields

Implementations MAY add custom fields to `payload` or `metadata` objects. Top-level message fields MUST NOT be extended outside the specification process.

### 10.3 Custom Status Fields

Agents MAY include additional fields in `AgentStatus.metadata` for implementation-specific data.

---

## 11. Security Considerations

### 11.1 Authentication

AIP does not mandate a specific authentication mechanism. Implementations SHOULD support at least one of:

- Bearer token (`Authorization: Bearer <token>`)
- Mutual TLS (mTLS)
- Custom authentication header

### 11.2 Authorization

Implementations SHOULD enforce authorization based on:

- `from` and `from_role` in the message
- `authority_weight` relative to the action's requirements
- `approval_state` for governed actions

### 11.3 Input Validation

Implementations MUST validate all incoming messages against the AIP schema before processing. Messages that fail validation MUST be rejected with HTTP 422.

---

## 12. Examples

### 12.1 User Sends Instruction to Coordinator

```http
POST https://coordinator.example.com/aip
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

### 12.2 Coordinator Assigns Task to Worker

```http
POST https://agent-backend.example.com/aip
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

### 12.3 Worker Submits Report

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

### 12.4 Cross-Host Communication

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

### 12.5 Agent Status Response

```http
GET https://agent-backend.example.com/status
```

```json
{
  "agent_id": "agent-backend",
  "role": "backend_engineer",
  "superior": "coordinator",
  "authority_weight": 78,
  "lifecycle": "running",
  "ok": true,
  "base_url": "https://agent-backend.example.com",
  "endpoints": {
    "aip": "https://agent-backend.example.com/aip",
    "status": "https://agent-backend.example.com/status"
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

## Appendix B: Relationship to Other Protocols

| Protocol | Focus | Relationship to AIP |
|----------|-------|---------------------|
| **MCP** (Model Context Protocol) | Model ↔ Tool connection | Complementary. MCP connects a model to tools; AIP connects agents to agents. An agent may use MCP internally to call tools. |
| **A2A** (Google Agent-to-Agent) | Agent-to-agent task delegation | Overlapping scope. AIP additionally provides governance, recursive status, and organizational authority. |
| **OpenAI Realtime API** | Model ↔ User streaming | Complementary. AIP is for agent-to-agent; OpenAI Realtime is for user-to-model. |

## Appendix C: Reference Implementations

- **Python SDK**: `aip-sdk-python` — reference implementation with sync/async clients
- **Ants**: Multi-agent runtime built on AIP — full reference coordinator/worker system
