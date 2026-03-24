"""AIP status protocol models — agent discovery, health, and group topology."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from aip.message import Lifecycle, Skill, _utc_now

SkillDescriptor = Skill


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


class Provider(BaseModel):
    """Organization or individual that operates an agent."""

    name: str
    url: str | None = None


class Presentation(BaseModel):
    """Human-facing display metadata for dashboards, agent cards, and marketplace UIs."""

    display_name: str
    tagline: str | None = Field(default=None, max_length=140)
    description: str | None = None
    icon_url: str | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    locale: str = Field(default="en", pattern=r"^[a-z]{2}(-[A-Z]{2})?$")
    categories: list[str] = Field(default_factory=list)
    homepage_url: str | None = None
    privacy_policy_url: str | None = None
    tos_url: str | None = None
    provider: Provider | None = None


class AgentAssignment(BaseModel):
    """Platform-assigned identity and constraints.

    Represents the "job description" the platform gives an agent,
    separate from its native profile (role, skills, tools).
    """

    assigned_role: str | None = None
    team: str | None = None
    scope: str | None = None
    granted_tools: list[str] = Field(default_factory=list)
    granted_skills: list[Skill] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    supervisor: str | None = None
    priority: str | None = None
    assigned_at: datetime | None = None
    metadata: dict[str, Any] | None = None


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
    namespace: str | None = None
    presentation: Presentation | None = None
    superior: str | None = None
    authority_weight: int | None = None
    lifecycle: Lifecycle | None = None
    port: int | None = None
    ok: bool = True
    base_url: str | None = None
    endpoints: StatusEndpoints | None = None
    capabilities: list[str] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    supported_versions: list[str] = Field(default_factory=lambda: ["1.0"])
    authentication: AuthenticationInfo | None = None
    rate_limits: RateLimitInfo | None = None
    pending_tasks: int = 0
    recent_errors: int = 0
    waiting_for_approval: bool = False
    last_message_at: datetime | None = None
    last_seen_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    assignment: AgentAssignment | None = None
    work: WorkSnapshot | None = None


class RecursiveStatusNode(BaseModel):
    """Recursive status tree: agent plus all direct and indirect subordinates."""

    self: AgentStatus
    subordinates: list["RecursiveStatusNode"] = Field(default_factory=list)


class GroupStatus(BaseModel):
    """Flat group-wide status document, optimized for dashboards and monitoring."""

    ok: bool = True
    service: str = "aip"
    namespace: str | None = None
    root_agent_id: str
    timestamp: datetime = Field(default_factory=_utc_now)
    topology: dict[str, list[str]] = Field(default_factory=dict)
    waiting_for_approval: bool = False
    agents: list[AgentStatus] = Field(default_factory=list)


RecursiveStatusNode.model_rebuild()
