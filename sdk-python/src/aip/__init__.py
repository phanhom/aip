"""AIP — Agent Interaction Protocol.

Open standard for structured agent-to-agent and human-to-agent communication.

    from aip import AIPMessage, build_message, send

Quick start:

    msg = build_message(
        from_agent="user",
        to="agent-backend",
        action="assign_task",
        intent="Design the order service API",
    )
    response = send(base_url="http://localhost:8000", message=msg)
"""

__version__ = "1.7.0"

from aip.bridge import BridgeConfig
from aip.client import (
    async_cancel_task,
    async_deregister_agent,
    async_emit_traces,
    async_fetch_status,
    async_get_artifact,
    async_get_task,
    async_get_usage,
    async_heartbeat,
    async_query_traces,
    async_register_agent,
    async_send_to_task,
    async_upload_artifact,
    cancel_task,
    deregister_agent,
    emit_traces,
    fetch_status,
    get_artifact,
    get_task,
    get_usage,
    heartbeat,
    query_traces,
    register_agent,
    send_to_task,
    upload_artifact,
)
from aip.discovery import DiscoveryError, DiscoveryResult, discover
from aip.gateway import AgentEntry, GatewayConfig
from aip.jsonrpc_bridge import (
    aip_ack_to_jsonrpc,
    aip_to_jsonrpc,
    is_jsonrpc,
    jsonrpc_error_to_aip,
    jsonrpc_to_aip,
)
from aip.message import (
    AckStatus,
    AIPAck,
    AIPAction,
    AIPErrorCode,
    AIPMessage,
    AIPPriority,
    AIPStatus,
    AIPTask,
    ApprovalState,
    Artifact,
    Lifecycle,
    RouteScope,
    Skill,
    TaskState,
    build_message,
)
from aip.observability import (
    AgentUsageBreakdown,
    LLMUsage,
    ModelUsageBreakdown,
    TraceBatch,
    TraceEvent,
    TraceQuery,
    TraceQueryResult,
    TraceSeverity,
    TraceType,
    UsageQuery,
    UsageSummary,
)
from aip.security import (
    EVENT_HEADER,
    SIGNATURE_HEADER,
    sign_callback,
    verify_callback,
)
from aip.send import (
    DEFAULT_API_VERSION,
    SendParams,
    SSEEvent,
    async_send,
    async_send_batch,
    async_send_stream,
    send,
    send_batch,
    send_stream,
)
from aip.status import (
    AgentAssignment,
    AgentStatus,
    AuthenticationInfo,
    GroupStatus,
    Presentation,
    Provider,
    RateLimitInfo,
    RecursiveStatusNode,
    SkillDescriptor,
    StatusEndpoints,
    StatusScope,
    WorkSnapshot,
)

__all__ = [
    "__version__",
    # Message layer
    "AIPAction",
    "AIPAck",
    "AIPErrorCode",
    "AIPMessage",
    "AIPPriority",
    "AIPStatus",
    "AIPTask",
    "AckStatus",
    "ApprovalState",
    "Artifact",
    "Lifecycle",
    "RouteScope",
    "Skill",
    "TaskState",
    "build_message",
    # Transport — send
    "DEFAULT_API_VERSION",
    "SSEEvent",
    "SendParams",
    "send",
    "send_batch",
    "send_stream",
    "async_send",
    "async_send_batch",
    "async_send_stream",
    # Client — status
    "fetch_status",
    "async_fetch_status",
    # Client — tasks
    "get_task",
    "async_get_task",
    "cancel_task",
    "async_cancel_task",
    "send_to_task",
    "async_send_to_task",
    # Client — artifacts
    "upload_artifact",
    "async_upload_artifact",
    "get_artifact",
    "async_get_artifact",
    # Client — registry
    "register_agent",
    "async_register_agent",
    "heartbeat",
    "async_heartbeat",
    "deregister_agent",
    "async_deregister_agent",
    # Client — traces & usage
    "emit_traces",
    "async_emit_traces",
    "query_traces",
    "async_query_traces",
    "get_usage",
    "async_get_usage",
    # Status / Discovery
    "StatusScope",
    "StatusEndpoints",
    "SkillDescriptor",
    "Presentation",
    "Provider",
    "AgentAssignment",
    "AuthenticationInfo",
    "RateLimitInfo",
    "WorkSnapshot",
    "AgentStatus",
    "RecursiveStatusNode",
    "GroupStatus",
    # Observability
    "TraceType",
    "TraceSeverity",
    "TraceEvent",
    "TraceBatch",
    "TraceQuery",
    "TraceQueryResult",
    "LLMUsage",
    "ModelUsageBreakdown",
    "AgentUsageBreakdown",
    "UsageSummary",
    "UsageQuery",
    # Security
    "sign_callback",
    "verify_callback",
    "SIGNATURE_HEADER",
    "EVENT_HEADER",
    # JSON-RPC bridge
    "is_jsonrpc",
    "aip_to_jsonrpc",
    "jsonrpc_to_aip",
    "aip_ack_to_jsonrpc",
    "jsonrpc_error_to_aip",
    # Bridge & Gateway
    "BridgeConfig",
    "AgentEntry",
    "GatewayConfig",
    # Discovery
    "discover",
    "DiscoveryResult",
    "DiscoveryError",
]
