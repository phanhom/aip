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
    AIPMessage,
    AIPPriority,
    AIPStatus,
    ApprovalState,
    RouteScope,
    build_message,
)
from aip.send import (
    SendParams,
    async_send,
    async_send_batch,
    send,
    send_batch,
)
from aip.status import (
    AgentStatus,
    GroupStatus,
    RecursiveStatusNode,
    StatusEndpoints,
    StatusScope,
    WorkSnapshot,
)

__all__ = [
    "__version__",
    "AIPAction",
    "AIPAck",
    "AIPMessage",
    "AIPPriority",
    "AIPStatus",
    "ApprovalState",
    "RouteScope",
    "build_message",
    "SendParams",
    "send",
    "send_batch",
    "async_send",
    "async_send_batch",
    "StatusScope",
    "StatusEndpoints",
    "WorkSnapshot",
    "AgentStatus",
    "RecursiveStatusNode",
    "GroupStatus",
]
