/**
 * Agent Interaction Protocol (AIP) — JavaScript/TypeScript SDK
 * @see https://aip-protocol.dev
 */

export {
  AIPClient,
  type AIPClientOptions,
  type SendOptions,
} from "./client.js";
export { buildMessage, type BuildMessageParams } from "./helpers.js";
export {
  AIP_ERROR_CODES,
  type AIPAck,
  type AIPMessage,
  type AIPPriority,
  type AgentStatus,
  type AgentUsageBreakdown,
  type ApprovalState,
  type Artifact,
  type Authentication,
  type GroupStatus,
  type LLMUsage,
  type ModelUsageBreakdown,
  type OAuth2Config,
  type Presentation,
  type Provider,
  type RateLimitInfo,
  type RecursiveStatusNode,
  type Skill,
  type SSEEvent,
  type StatusEndpoints,
  type StatusScope,
  type AIPTask,
  type TaskState,
  type TraceEvent,
  type TraceSeverity,
  type TraceType,
  type MessageStatus,
  type AckStatus,
  type RouteScope,
  type UsageSummary,
  type WorkSnapshot,
} from "./types.js";
