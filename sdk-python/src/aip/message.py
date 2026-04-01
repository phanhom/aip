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


class AckStatus(str, Enum):
    """Acknowledgment acceptance status (spec Section 4.3)."""

    received = "received"
    queued = "queued"
    rejected = "rejected"


class Lifecycle(str, Enum):
    """Agent lifecycle states (spec Section 5.3)."""

    idle = "idle"
    starting = "starting"
    running = "running"
    blocked = "blocked"
    degraded = "degraded"
    failed = "failed"


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
    chat = "chat"


class AIPErrorCode:
    """Standard error code registry (aip/ namespace).

    Use these constants instead of raw strings for type safety and discoverability.
    """

    # Protocol errors
    INVALID_VERSION = "aip/protocol/invalid_version"
    UNSUPPORTED_VERSION = "aip/protocol/unsupported_version"
    INVALID_MESSAGE = "aip/protocol/invalid_message"
    ROUTING_FAILED = "aip/protocol/routing_failed"
    AGENT_NOT_FOUND = "aip/protocol/agent_not_found"
    AGENT_UNAVAILABLE = "aip/protocol/agent_unavailable"
    IDEMPOTENCY_CONFLICT = "aip/protocol/idempotency_conflict"
    IDEMPOTENCY_CONCURRENT = "aip/protocol/idempotency_concurrent"

    # Execution errors
    UNKNOWN_ACTION = "aip/execution/unknown_action"
    INVALID_PAYLOAD = "aip/execution/invalid_payload"
    TASK_FAILED = "aip/execution/task_failed"
    TASK_TIMEOUT = "aip/execution/task_timeout"
    TASK_NOT_FOUND = "aip/execution/task_not_found"
    TASK_NOT_CANCELABLE = "aip/execution/task_not_cancelable"
    CAPACITY_EXCEEDED = "aip/execution/capacity_exceeded"
    INPUT_REQUIRED = "aip/execution/input_required"

    # Governance errors
    AUTHORITY_INSUFFICIENT = "aip/governance/authority_insufficient"
    APPROVAL_REQUIRED = "aip/governance/approval_required"
    APPROVAL_REJECTED = "aip/governance/approval_rejected"
    CONSTRAINT_VIOLATED = "aip/governance/constraint_violated"
    POLICY_DENIED = "aip/governance/policy_denied"

    # Auth errors
    UNAUTHENTICATED = "aip/auth/unauthenticated"
    UNAUTHORIZED = "aip/auth/unauthorized"
    TOKEN_EXPIRED = "aip/auth/token_expired"
    INVALID_TOKEN = "aip/auth/invalid_token"

    # Rate limiting errors
    RATE_LIMIT_EXCEEDED = "aip/ratelimit/exceeded"
    QUOTA_EXHAUSTED = "aip/ratelimit/quota_exhausted"


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

    authority_weight: int = Field(default=50, ge=0, le=100)
    requires_approval: bool = False
    approval_state: ApprovalState = ApprovalState.not_required

    callback_url: str | None = None
    callback_secret: str | None = None

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
    status: AckStatus = AckStatus.received
    task_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    correlation_id: str | None = None


class TaskState(str, Enum):
    """Task lifecycle states."""

    submitted = "submitted"
    working = "working"
    input_required = "input-required"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"


class Artifact(BaseModel):
    """A file, document, or structured data produced during task execution."""

    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str | None = None
    mime_type: str = "application/json"
    uri: str | None = None
    inline_data: str | None = None
    metadata: dict[str, Any] | None = None


class AIPTask(BaseModel):
    """A long-running task tracked by the agent."""

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    message_id: str
    trace_id: str | None = None
    correlation_id: str | None = None
    parent_task_id: str | None = None
    state: TaskState = TaskState.submitted
    from_agent: str = Field(..., alias="from")
    to: str
    action: AIPAction | str
    intent: str
    progress: float | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    model_config = {"populate_by_name": True}

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")


class Skill(BaseModel):
    """Structured skill descriptor for rich agent discovery."""

    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    input_modes: list[str] = Field(default_factory=lambda: ["application/json"])
    output_modes: list[str] = Field(default_factory=lambda: ["application/json"])
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    examples: list[dict[str, Any]] = Field(default_factory=list)


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
