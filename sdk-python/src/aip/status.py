"""AIP status protocol models — agent discovery, health, and group topology."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StatusScope(str, Enum):
    """Supported status query scopes."""

    self_scope = "self"
    subtree = "subtree"
    group = "group"


class StatusEndpoints(BaseModel):
    """Discoverable endpoints for an AIP-compliant agent."""

    aip: str | None = None
    status: str | None = None


class WorkSnapshot(BaseModel):
    """Work-in-progress snapshot for operational visibility."""

    tasks: list[dict[str, Any]] = Field(default_factory=list)
    reports: list[dict[str, Any]] = Field(default_factory=list)
    recent_messages: list[dict[str, Any]] = Field(default_factory=list)
    last_seen: str | None = None
    pending_tasks: int = 0


class SkillDescriptor(BaseModel):
    """Structured skill descriptor for rich agent discovery (aligned with A2A Agent Card)."""

    id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    input_modes: list[str] = Field(default_factory=lambda: ["application/json"])
    output_modes: list[str] = Field(default_factory=lambda: ["application/json"])
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    examples: list[dict[str, Any]] = Field(default_factory=list)


class AuthenticationInfo(BaseModel):
    """Authentication schemes supported by this agent."""

    schemes: list[str] = Field(default_factory=list)
    oauth2: dict[str, Any] | None = None


class RateLimitInfo(BaseModel):
    """Rate limiting and quota information for client self-regulation."""

    max_requests_per_minute: int | None = None
    max_requests_per_day: int | None = None
    max_concurrent_tasks: int | None = None
    remaining_requests: int | None = None
    remaining_tasks: int | None = None
    reset_at: datetime | None = None


class AgentStatus(BaseModel):
    """Status document for a single AIP-compliant agent.

    Returned by GET /status?scope=self and used as elements in group/subtree responses.
    """

    agent_id: str
    role: str
    superior: str | None = None
    authority_weight: int | None = None
    lifecycle: str | None = None
    port: int | None = None
    ok: bool = True
    base_url: str | None = None
    endpoints: StatusEndpoints | None = None
    capabilities: list[str] = Field(default_factory=list)
    skills: list[SkillDescriptor] = Field(default_factory=list)
    supported_versions: list[str] = Field(default_factory=lambda: ["1.0"])
    authentication: AuthenticationInfo | None = None
    rate_limits: RateLimitInfo | None = None
    pending_tasks: int = 0
    recent_errors: int = 0
    waiting_for_approval: bool = False
    last_message_at: datetime | None = None
    last_seen_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    work: WorkSnapshot | None = None


class RecursiveStatusNode(BaseModel):
    """Recursive status tree: agent plus all direct and indirect subordinates."""

    self: AgentStatus
    subordinates: list["RecursiveStatusNode"] = Field(default_factory=list)


class GroupStatus(BaseModel):
    """Flat group-wide status document, optimized for dashboards and monitoring."""

    ok: bool = True
    service: str = "aip"
    root_agent_id: str
    timestamp: datetime = Field(default_factory=_utc_now)
    topology: dict[str, list[str]] = Field(default_factory=dict)
    waiting_for_approval: bool = False
    agents: list[AgentStatus] = Field(default_factory=list)


RecursiveStatusNode.model_rebuild()
