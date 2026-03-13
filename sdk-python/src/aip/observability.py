"""AIP Observability — standardized trace events and cost tracking.

Defines the wire format for trace events that any AIP-compatible dashboard,
monitoring tool, or analytics pipeline can consume without proprietary adapters.

Endpoints:
    POST /v1/traces          Emit one or more trace events
    GET  /v1/traces          Query trace events (filtered by agent, type, time)
    GET  /v1/traces/{id}     Retrieve a single trace event
    GET  /v1/usage           Aggregated LLM usage / cost summary
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── Trace Types ───────────────────────────────────────────────────────


class TraceType(str, Enum):
    """Standardized trace event types.

    Implementations MAY define custom types using the ``x-<org>/<name>`` prefix.
    """

    aip_message_sent = "aip.message.sent"
    aip_message_received = "aip.message.received"

    task_created = "task.created"
    task_working = "task.working"
    task_completed = "task.completed"
    task_failed = "task.failed"
    task_canceled = "task.canceled"
    task_input_required = "task.input_required"

    llm_request = "llm.request"
    llm_response = "llm.response"
    llm_usage = "llm.usage"

    tool_call = "tool.call"
    tool_result = "tool.result"

    report = "report"
    conversation = "conversation"
    approval = "approval"
    error = "error"
    log = "log"


class TraceSeverity(str, Enum):
    """Log severity levels aligned with OpenTelemetry."""

    trace = "TRACE"
    debug = "DEBUG"
    info = "INFO"
    warn = "WARN"
    error = "ERROR"
    fatal = "FATAL"


# ── Trace Event ───────────────────────────────────────────────────────


class TraceEvent(BaseModel):
    """A single observable event in an agent system.

    Every meaningful action — sending a message, calling an LLM, completing a
    task, logging an error — is represented as a TraceEvent. Events are linked
    via ``trace_id`` (end-to-end workflow) and ``correlation_id`` (request-response).
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str
    agent_id: str
    trace_type: TraceType | str
    severity: TraceSeverity = TraceSeverity.info
    timestamp: datetime = Field(default_factory=_utc_now)

    correlation_id: str | None = None
    parent_event_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None

    task_id: str | None = None
    message_id: str | None = None

    summary: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list)

    duration_ms: int | None = None
    namespace: str | None = None


class TraceBatch(BaseModel):
    """Batch of trace events for bulk emission via POST /v1/traces."""

    events: list[TraceEvent]


class TraceQuery(BaseModel):
    """Query parameters for GET /v1/traces."""

    agent_id: str | None = None
    trace_id: str | None = None
    trace_type: TraceType | str | None = None
    task_id: str | None = None
    severity: TraceSeverity | None = None
    namespace: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    order: str = Field(default="desc", pattern=r"^(asc|desc)$")


class TraceQueryResult(BaseModel):
    """Paginated result from GET /v1/traces."""

    events: list[TraceEvent]
    total: int
    limit: int
    offset: int
    has_more: bool


# ── LLM Usage ─────────────────────────────────────────────────────────


class LLMUsage(BaseModel):
    """Token and cost data for a single LLM invocation.

    Emitted as the ``payload`` of a ``llm.usage`` trace event, or used
    standalone for cost aggregation.
    """

    model: str
    provider: str | None = None

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0

    estimated_cost_usd: float | None = None
    duration_ms: int | None = None

    request_id: str | None = None
    agent_id: str | None = None
    task_id: str | None = None
    trace_id: str | None = None


class ModelUsageBreakdown(BaseModel):
    """Per-model usage within a summary period."""

    model: str
    provider: str | None = None
    requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    estimated_cost_usd: float = 0.0


class AgentUsageBreakdown(BaseModel):
    """Per-agent usage within a summary period."""

    agent_id: str
    requests: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    by_model: list[ModelUsageBreakdown] = Field(default_factory=list)


class UsageSummary(BaseModel):
    """Aggregated LLM usage summary returned by GET /v1/usage.

    Supports time-range queries, per-agent breakdown, and per-model breakdown —
    everything a cost dashboard needs.
    """

    period_start: datetime
    period_end: datetime
    namespace: str | None = None

    total_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cached_tokens: int = 0
    total_estimated_cost_usd: float = 0.0

    by_model: list[ModelUsageBreakdown] = Field(default_factory=list)
    by_agent: list[AgentUsageBreakdown] = Field(default_factory=list)


class UsageQuery(BaseModel):
    """Query parameters for GET /v1/usage."""

    namespace: str | None = None
    agent_id: str | None = None
    model: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    group_by: str = Field(default="model", pattern=r"^(model|agent|hour|day)$")
