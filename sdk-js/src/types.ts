/**
 * Agent Interaction Protocol (AIP) — TypeScript type definitions.
 * @see https://aip-protocol.dev
 */

/** Task lifecycle states. */
export type TaskState =
  | "submitted"
  | "working"
  | "input-required"
  | "completed"
  | "failed"
  | "canceled";

/** Message priority levels. */
export type AIPPriority = "low" | "normal" | "high" | "urgent";

/** Approval workflow states. */
export type ApprovalState =
  | "not_required"
  | "waiting_human"
  | "approved"
  | "rejected";

/** Message lifecycle status. */
export type MessageStatus = "Pending" | "InProgress" | "Completed" | "Failed";

/** Ack acceptance status. */
export type AckStatus = "received" | "queued" | "rejected";

/** Route scope: local (same host) or remote (cross-host). */
export type RouteScope = "local" | "remote";

/** Server-Sent Event envelope. */
export interface SSEEvent {
  event: string;
  data: string;
}

/** Standard AIP error codes. */
export const AIP_ERROR_CODES = {
  // Protocol
  INVALID_VERSION: "aip/protocol/invalid_version",
  UNSUPPORTED_VERSION: "aip/protocol/unsupported_version",
  INVALID_MESSAGE: "aip/protocol/invalid_message",
  ROUTING_FAILED: "aip/protocol/routing_failed",
  AGENT_NOT_FOUND: "aip/protocol/agent_not_found",
  AGENT_UNAVAILABLE: "aip/protocol/agent_unavailable",
  IDEMPOTENCY_CONFLICT: "aip/protocol/idempotency_conflict",
  IDEMPOTENCY_CONCURRENT: "aip/protocol/idempotency_concurrent",
  // Execution
  UNKNOWN_ACTION: "aip/execution/unknown_action",
  INVALID_PAYLOAD: "aip/execution/invalid_payload",
  TASK_FAILED: "aip/execution/task_failed",
  TASK_TIMEOUT: "aip/execution/task_timeout",
  TASK_NOT_FOUND: "aip/execution/task_not_found",
  TASK_NOT_CANCELABLE: "aip/execution/task_not_cancelable",
  CAPACITY_EXCEEDED: "aip/execution/capacity_exceeded",
  INPUT_REQUIRED: "aip/execution/input_required",
  // Governance
  AUTHORITY_INSUFFICIENT: "aip/governance/authority_insufficient",
  APPROVAL_REQUIRED: "aip/governance/approval_required",
  APPROVAL_REJECTED: "aip/governance/approval_rejected",
  CONSTRAINT_VIOLATED: "aip/governance/constraint_violated",
  POLICY_DENIED: "aip/governance/policy_denied",
  // Auth
  UNAUTHENTICATED: "aip/auth/unauthenticated",
  UNAUTHORIZED: "aip/auth/unauthorized",
  TOKEN_EXPIRED: "aip/auth/token_expired",
  INVALID_TOKEN: "aip/auth/invalid_token",
  // Rate limiting
  RATE_LIMIT_EXCEEDED: "aip/ratelimit/exceeded",
  QUOTA_EXHAUSTED: "aip/ratelimit/quota_exhausted",
} as const;

/** Rate limiting and quota information. */
export interface RateLimitInfo {
  max_requests_per_minute?: number | null;
  max_requests_per_day?: number | null;
  max_concurrent_tasks?: number | null;
  remaining_requests?: number | null;
  remaining_tasks?: number | null;
  reset_at?: string | null;
}

/** AIP message envelope — wire format for agent-to-agent communication. */
export interface AIPMessage {
  version: string;
  message_id: string;
  from: string;
  to: string;
  action: string;
  intent: string;
  correlation_id?: string | null;
  trace_id?: string | null;
  parent_task_id?: string | null;
  from_role?: string | null;
  to_role?: string | null;
  to_host?: string | null;
  to_base_url?: string | null;
  route_scope?: RouteScope;
  payload?: Record<string, unknown>;
  expected_output?: string | null;
  constraints?: string[];
  priority?: AIPPriority;
  status?: MessageStatus;
  authority_weight?: number;
  requires_approval?: boolean;
  approval_state?: ApprovalState;
  callback_url?: string | null;
  callback_secret?: string | null;
  retries?: number;
  latency_ms?: number | null;
  error_code?: string | null;
  error_message?: string | null;
  created_at?: string;
  updated_at?: string;
}

/** Acknowledgment returned by POST /v1/aip handlers. */
export interface AIPAck {
  ok: boolean;
  message_id: string;
  to: string;
  status: AckStatus;
  task_id?: string;
  error_code?: string | null;
  error_message?: string | null;
  correlation_id?: string | null;
}

/** Artifact produced during task execution. */
export interface Artifact {
  artifact_id: string;
  name: string;
  description?: string | null;
  mime_type: string;
  uri?: string | null;
  inline_data?: string | null;
  metadata?: Record<string, unknown> | null;
}

/** Structured skill descriptor for agent discovery. */
export interface Skill {
  id: string;
  name: string;
  description: string;
  tags?: string[];
  input_modes?: string[];
  output_modes?: string[];
  input_schema?: Record<string, unknown> | null;
  output_schema?: Record<string, unknown> | null;
  examples?: Record<string, unknown>[];
}

/** Organization or individual that operates an agent. */
export interface Provider {
  name: string;
  url?: string | null;
}

/** Human-facing display metadata for dashboards, agent cards, and marketplace UIs. */
export interface Presentation {
  display_name: string;
  tagline?: string | null;
  description?: string | null;
  icon_url?: string | null;
  /** Hex color, e.g. "#4A90D9". */
  color?: string | null;
  /** BCP 47 language tag, e.g. "en", "zh-CN". */
  locale?: string;
  categories?: string[];
  homepage_url?: string | null;
  privacy_policy_url?: string | null;
  tos_url?: string | null;
  provider?: Provider | null;
}

/** Platform-assigned identity and constraints for an agent. */
export interface AgentAssignment {
  /** Platform-assigned role (may differ from the agent's self-declared role). */
  assigned_role?: string | null;
  /** Team or department this agent belongs to. */
  team?: string | null;
  /** Human-readable description of the agent's work boundaries. */
  scope?: string | null;
  /** Tools or resources the platform grants beyond the agent's native capabilities. */
  granted_tools?: string[];
  /** Additional skill descriptors the platform injects (merged with native skills). */
  granted_skills?: Skill[];
  /** Boundaries or rules the platform imposes on this agent. */
  constraints?: string[];
  /** Agent ID of the assigned supervisor. */
  supervisor?: string | null;
  /** Platform-assigned priority level (e.g., "high", "normal", "low"). */
  priority?: string | null;
  /** ISO 8601 timestamp of when the assignment was last updated. */
  assigned_at?: string | null;
  /** Platform-specific extension fields. */
  metadata?: Record<string, unknown> | null;
}

/** OAuth2 configuration for agent authentication. */
export interface OAuth2Config {
  token_url: string;
  scopes?: string[];
}

/** Authentication schemes declared by an agent. */
export interface Authentication {
  schemes?: string[];
  oauth2?: OAuth2Config | null;
}

/** Discoverable endpoints for an agent. */
export interface StatusEndpoints {
  aip?: string | null;
  status?: string | null;
  [key: string]: unknown;
}

/** Work-in-progress snapshot. */
export interface WorkSnapshot {
  tasks?: unknown[];
  reports?: unknown[];
  recent_messages?: unknown[];
  last_seen?: string | null;
  pending_tasks?: number;
  [key: string]: unknown;
}

/** Status document for a single agent. */
export interface AgentStatus {
  agent_id: string;
  role: string;
  namespace?: string | null;
  presentation?: Presentation | null;
  superior?: string | null;
  authority_weight?: number | null;
  lifecycle?: "idle" | "starting" | "running" | "blocked" | "degraded" | "failed" | null;
  port?: number | null;
  ok?: boolean;
  base_url?: string | null;
  endpoints?: StatusEndpoints | null;
  capabilities?: string[];
  skills?: Skill[];
  supported_versions?: string[];
  rate_limits?: RateLimitInfo | null;
  pending_tasks?: number;
  recent_errors?: number;
  waiting_for_approval?: boolean;
  last_message_at?: string | null;
  last_seen_at?: string | null;
  metadata?: Record<string, unknown> | null;
  assignment?: AgentAssignment | null;
  work?: WorkSnapshot | null;
  authentication?: Authentication;
  [key: string]: unknown;
}

/** Task object — tracks long-running agent work. */
export interface AIPTask {
  task_id: string;
  message_id: string;
  state: TaskState;
  from: string;
  to: string;
  action: string;
  intent: string;
  progress?: number | null;
  artifacts?: Artifact[];
  history?: AIPMessage[];
  error_code?: string | null;
  error_message?: string | null;
  trace_id?: string | null;
  correlation_id?: string | null;
  parent_task_id?: string | null;
  metadata?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

/** Status scope for hierarchical queries. */
export type StatusScope = "self" | "subtree" | "group";

/** Aggregated status for a group of agents. */
export interface GroupStatus {
  ok: boolean;
  service?: string;
  namespace?: string | null;
  root_agent_id: string;
  timestamp?: string;
  topology?: Record<string, string[]>;
  waiting_for_approval?: boolean;
  agents: AgentStatus[];
}

/** Tree node for recursive/hierarchical agent discovery. */
export interface RecursiveStatusNode {
  self: AgentStatus;
  subordinates?: RecursiveStatusNode[];
}

/** Standard trace event types. */
export type TraceType =
  | "aip.message.sent"
  | "aip.message.received"
  | "task.created"
  | "task.working"
  | "task.completed"
  | "task.failed"
  | "task.canceled"
  | "task.input_required"
  | "llm.request"
  | "llm.response"
  | "llm.usage"
  | "tool.call"
  | "tool.result"
  | "error"
  | "log"
  | "report"
  | "conversation"
  | "approval"
  | "agent.spawned"
  | "agent.terminated";

/** Trace severity levels (OpenTelemetry-aligned). */
export type TraceSeverity = "TRACE" | "DEBUG" | "INFO" | "WARN" | "ERROR" | "FATAL";

/** Single observable event in the AIP system. */
export interface TraceEvent {
  event_id: string;
  trace_id: string;
  span_id?: string | null;
  parent_span_id?: string | null;
  parent_event_id?: string | null;
  agent_id: string;
  trace_type: TraceType;
  severity?: TraceSeverity;
  timestamp: string;
  duration_ms?: number | null;
  task_id?: string | null;
  message_id?: string | null;
  correlation_id?: string | null;
  summary?: string | null;
  payload?: Record<string, unknown>;
  metadata?: Record<string, unknown> | null;
  tags?: string[];
  namespace?: string | null;
}

/** LLM invocation token and cost data. */
export interface LLMUsage {
  model: string;
  provider?: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cached_tokens?: number;
  estimated_cost_usd?: number | null;
  duration_ms?: number | null;
  request_id?: string | null;
  agent_id?: string | null;
  task_id?: string | null;
  trace_id?: string | null;
}

/** Per-model breakdown in a usage summary. */
export interface ModelUsageBreakdown {
  model: string;
  provider?: string | null;
  requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cached_tokens?: number;
  estimated_cost_usd: number;
}

/** Per-agent breakdown in a usage summary. */
export interface AgentUsageBreakdown {
  agent_id: string;
  requests: number;
  total_tokens: number;
  estimated_cost_usd: number;
  by_model?: ModelUsageBreakdown[];
}

/** Aggregated LLM usage and cost summary. */
export interface UsageSummary {
  period_start: string;
  period_end: string;
  namespace?: string | null;
  total_requests?: number;
  total_prompt_tokens?: number;
  total_completion_tokens?: number;
  total_tokens?: number;
  total_cached_tokens?: number;
  total_estimated_cost_usd?: number;
  by_model?: ModelUsageBreakdown[];
  by_agent?: AgentUsageBreakdown[];
}
