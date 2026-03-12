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
  type ApprovalState,
  type Artifact,
  type Authentication,
  type OAuth2Config,
  type Presentation,
  type Provider,
  type RateLimitInfo,
  type Skill,
  type SSEEvent,
  type StatusEndpoints,
  type AIPTask,
  type TaskState,
  type MessageStatus,
  type AckStatus,
  type RouteScope,
  type WorkSnapshot,
} from "./types.js";
