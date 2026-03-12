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
    supported_versions: list[str] = Field(default_factory=lambda: ["1.0"])
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
