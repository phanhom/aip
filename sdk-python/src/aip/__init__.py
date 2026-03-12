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

__version__ = "1.0.0"

from aip.message import (
    AIPAck,
    AIPAction,
    AIPErrorCode,
    AIPMessage,
    AIPPriority,
    AIPStatus,
    AIPTask,
    ApprovalState,
    Artifact,
    RouteScope,
    Skill,
    TaskState,
    build_message,
)
from aip.send import (
    DEFAULT_API_VERSION,
    SendParams,
    async_send,
    async_send_batch,
    send,
    send_batch,
)
from aip.jsonrpc_bridge import (
    aip_ack_to_jsonrpc,
    aip_to_jsonrpc,
    is_jsonrpc,
    jsonrpc_error_to_aip,
    jsonrpc_to_aip,
)
from aip.status import (
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
    "DEFAULT_API_VERSION",
    "AIPAction",
    "AIPAck",
    "AIPErrorCode",
    "AIPMessage",
    "AIPPriority",
    "AIPStatus",
    "AIPTask",
    "ApprovalState",
    "Artifact",
    "RouteScope",
    "Skill",
    "TaskState",
    "build_message",
    "SendParams",
    "send",
    "send_batch",
    "async_send",
    "async_send_batch",
    "StatusScope",
    "StatusEndpoints",
    "SkillDescriptor",
    "Presentation",
    "Provider",
    "AuthenticationInfo",
    "RateLimitInfo",
    "WorkSnapshot",
    "is_jsonrpc",
    "aip_to_jsonrpc",
    "jsonrpc_to_aip",
    "aip_ack_to_jsonrpc",
    "jsonrpc_error_to_aip",
    "AgentStatus",
    "RecursiveStatusNode",
    "GroupStatus",
]
