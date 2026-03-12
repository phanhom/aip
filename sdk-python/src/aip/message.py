"""AIP message models: the core wire format for agent-to-agent communication."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AIPStatus(str, Enum):
    """Message lifecycle status."""

    pending = "Pending"
    in_progress = "InProgress"
    completed = "Completed"
    failed = "Failed"


class AIPPriority(str, Enum):
    """Message priority levels."""

    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"


class RouteScope(str, Enum):
    """Routing intent: local (same host) or remote (cross-host)."""

    local = "local"
    remote = "remote"


class ApprovalState(str, Enum):
    """Governance approval workflow state."""

    not_required = "not_required"
    waiting_human = "waiting_human"
    approved = "approved"
    rejected = "rejected"


class AIPAction(str, Enum):
    """Standard protocol actions. Custom actions should use x-<org>/<name> prefix."""

    assign_task = "assign_task"
    request_context = "request_context"
    request_artifact_review = "request_artifact_review"
    submit_report = "submit_report"
    request_approval = "request_approval"
    publish_status = "publish_status"
    handoff = "handoff"
    escalate = "escalate"
    tool_result = "tool_result"
    sync_skill_registry = "sync_skill_registry"
    user_instruction = "user_instruction"


class AIPMessage(BaseModel):
    """AIP message envelope — the universal wire format for agent communication.

    Organized into four layers:
    - Protocol: version, addressing, routing
    - Execution: action, intent, payload, constraints
    - Governance: authority, approval
    - Observability: trace IDs, retries, latency, errors
    """

    version: str = "1.0"
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str | None = None
    trace_id: str | None = None
    parent_task_id: str | None = None

    from_agent: str = Field(..., alias="from")
    to: str
    from_role: str | None = None
    to_role: str | None = None
    to_host: str | None = None
    to_base_url: str | None = None
    route_scope: RouteScope = RouteScope.local

    action: AIPAction | str
    intent: str
    payload: dict[str, Any] = Field(default_factory=dict)
    expected_output: str | None = None
    constraints: list[str] = Field(default_factory=list)
    priority: AIPPriority = AIPPriority.normal
    status: AIPStatus = AIPStatus.pending

    authority_weight: int = 50
    requires_approval: bool = False
    approval_state: ApprovalState = ApprovalState.not_required

    retries: int = 0
    latency_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None

    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    model_config = {"populate_by_name": True}

    def touch(self, status: AIPStatus) -> None:
        """Update status and timestamp after handling."""
        self.status = status
        self.updated_at = _utc_now()

    def to_wire(self) -> dict[str, Any]:
        """Serialize for JSON transport, preserving the ``from`` alias."""
        return self.model_dump(by_alias=True, mode="json")


class AIPAck(BaseModel):
    """Standard acknowledgment returned by POST /aip handlers."""

    ok: bool = True
    message_id: str
    to: str
    status: str = "received"
    correlation_id: str | None = None


def build_message(
    *,
    from_agent: str,
    to: str,
    action: AIPAction | str,
    intent: str,
    payload: dict[str, Any] | None = None,
    **extra: Any,
) -> AIPMessage:
    """Create a valid AIP message with sensible defaults.

    >>> msg = build_message(from_agent="user", to="backend", action="assign_task", intent="Do X")
    >>> msg.to_wire()["from"]
    'user'
    """
    return AIPMessage(
        from_agent=from_agent,
        to=to,
        action=action,
        intent=intent,
        payload=payload or {},
        **extra,
    )
