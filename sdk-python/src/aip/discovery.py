"""AIP Platform-Side Agent Discovery — probe any URL, detect its protocol, build AgentStatus.

Usage by platform implementations:

    from aip.discovery import discover

    result = await discover("http://192.168.1.10:3000")
    print(result.protocol)       # "openai"
    print(result.agent_status)   # AgentStatus(...)
    print(result.models)         # ["openclaw-v1"]

Or with a protocol hint (skip auto-detection):

    result = await discover("http://192.168.1.10:3000", protocol="openai")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse

log = logging.getLogger("aip.discovery")

PROBE_TIMEOUT = 5.0
DISCOVERY_PROFILES = ("aip", "a2a", "openai")


@dataclass
class DiscoveryResult:
    """Result of probing an agent URL."""

    protocol: str
    base_url: str
    agent_id: str
    display_name: str
    models: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    skills: list[dict] = field(default_factory=list)
    raw_status: dict | None = None
    raw_agent_card: dict | None = None
    health_endpoint: str | None = None
    message_endpoint: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_agent_status(self, **overrides) -> dict:
        """Build a synthetic AgentStatus dict from discovery results."""
        now = datetime.now(timezone.utc).isoformat()
        status: dict = {
            "agent_id": self.agent_id,
            "role": "agent",
            "lifecycle": "running",
            "ok": True,
            "base_url": self.base_url,
            "capabilities": self.capabilities,
            "supported_versions": ["1.0"],
            "presentation": {
                "display_name": self.display_name,
            },
            "last_seen_at": now,
            "metadata": {
                "protocol": self.protocol,
                **self.metadata,
            },
        }
        if self.models:
            status["metadata"]["models"] = self.models
        if self.skills:
            status["skills"] = self.skills
        if self.raw_status:
            return {**status, **self.raw_status, **overrides}
        status.update(overrides)
        return status


async def discover(
    base_url: str,
    *,
    protocol: str | None = None,
    timeout: float = PROBE_TIMEOUT,
    credentials: dict | None = None,
) -> DiscoveryResult:
    """Probe a URL and detect its protocol.

    Args:
        base_url: The agent's root URL.
        protocol: Hint — skip auto-detection and probe only this profile.
                  One of: "auto", "aip", "openai", "anthropic", "a2a", or None (= auto).
        timeout: Per-probe timeout in seconds.
        credentials: Optional ``{"scheme": "bearer", "token": "..."}`` for auth.

    Returns:
        DiscoveryResult with protocol, capabilities, and a to_agent_status() builder.

    Raises:
        DiscoveryError: If no known protocol could be detected.
    """
    import httpx

    base_url = base_url.rstrip("/")
    headers = _build_headers(credentials)
    hint = protocol if protocol and protocol != "auto" else None

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        if hint:
            probe_fn = _PROBE_FUNCTIONS.get(hint)
            if not probe_fn:
                raise DiscoveryError(
                    f"Unknown protocol profile: {hint!r}. "
                    f"Supported: {', '.join(DISCOVERY_PROFILES)}"
                )
            result = await probe_fn(client, base_url)
            if result:
                return result
            raise DiscoveryError(
                f"Agent at {base_url} does not respond to {hint!r} protocol probes."
            )

        for profile_name in DISCOVERY_PROFILES:
            probe_fn = _PROBE_FUNCTIONS[profile_name]
            try:
                result = await probe_fn(client, base_url)
                if result:
                    log.info("Discovered %s protocol at %s", result.protocol, base_url)
                    return result
            except Exception as e:
                log.debug("Probe %s failed for %s: %s", profile_name, base_url, e)

        alive = await _probe_health(client, base_url)
        if alive:
            parsed = urlparse(base_url)
            return DiscoveryResult(
                protocol="unknown",
                base_url=base_url,
                agent_id=_derive_id(base_url),
                display_name=f"Agent @ {parsed.hostname}",
                capabilities=[],
                health_endpoint=alive,
            )

        raise DiscoveryError(
            f"Agent at {base_url} is unreachable or does not expose a known API. "
            f"Tried: {', '.join(DISCOVERY_PROFILES)}, health check."
        )


class DiscoveryError(Exception):
    """Raised when protocol detection fails."""


def _build_headers(credentials: dict | None) -> dict[str, str]:
    if not credentials:
        return {}
    scheme = credentials.get("scheme", "bearer")
    token = credentials.get("token", "")
    header = credentials.get("header", "Authorization")
    if scheme == "bearer":
        return {header: f"Bearer {token}"}
    if scheme == "api_key":
        return {header: token}
    return {header: token}


def _derive_id(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or "unknown"
    port = parsed.port
    return f"{host}-{port}" if port else host


# ── Profile probes ────────────────────────────────────────────────────


async def _probe_aip(client, base_url: str) -> DiscoveryResult | None:
    try:
        resp = await client.get(f"{base_url}/v1/status")
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, dict) or "agent_id" not in data:
            return None
        return DiscoveryResult(
            protocol="aip",
            base_url=base_url,
            agent_id=data["agent_id"],
            display_name=_extract_display_name(data),
            capabilities=data.get("capabilities", []),
            skills=data.get("skills", []),
            raw_status=data,
            health_endpoint=f"{base_url}/v1/status",
            message_endpoint=f"{base_url}/v1/aip",
        )
    except Exception:
        return None


async def _probe_a2a(client, base_url: str) -> DiscoveryResult | None:
    try:
        resp = await client.get(f"{base_url}/.well-known/agent.json")
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, dict):
            return None
        if "name" not in data and "url" not in data:
            return None
        name = data.get("name", "A2A Agent")
        skills = []
        for s in data.get("skills", []):
            skills.append(
                {
                    "id": s.get("id", s.get("name", "skill")),
                    "name": s.get("name", ""),
                    "description": s.get("description", ""),
                    "tags": s.get("tags", []),
                }
            )
        return DiscoveryResult(
            protocol="a2a",
            base_url=base_url,
            agent_id=data.get("url", _derive_id(base_url)),
            display_name=name,
            capabilities=["messaging"],
            skills=skills,
            raw_agent_card=data,
            health_endpoint=f"{base_url}/.well-known/agent.json",
        )
    except Exception:
        return None


async def _probe_openai(client, base_url: str) -> DiscoveryResult | None:
    try:
        resp = await client.get(f"{base_url}/v1/models")
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, dict) or "data" not in data:
            return None
        models_list = data["data"]
        if not isinstance(models_list, list) or not models_list:
            return None
        model_ids = [m.get("id", "unknown") for m in models_list if isinstance(m, dict)]
        first_model = model_ids[0] if model_ids else "default"
        parsed = urlparse(base_url)
        return DiscoveryResult(
            protocol="openai",
            base_url=base_url,
            agent_id=first_model,
            display_name=f"{first_model} @ {parsed.hostname}",
            models=model_ids,
            capabilities=["messaging"],
            health_endpoint=f"{base_url}/v1/models",
            message_endpoint=f"{base_url}/v1/chat/completions",
            metadata={"models": model_ids},
        )
    except Exception:
        return None


async def _probe_health(client, base_url: str) -> str | None:
    for path in ("/health", "/api/health", "/healthz", "/v1/health"):
        try:
            resp = await client.get(f"{base_url}{path}")
            if resp.status_code == 200:
                return f"{base_url}{path}"
        except Exception:
            continue
    return None


_PROBE_FUNCTIONS = {
    "aip": _probe_aip,
    "a2a": _probe_a2a,
    "openai": _probe_openai,
}


def _extract_display_name(status: dict) -> str:
    pres = status.get("presentation")
    if pres and isinstance(pres, dict):
        dn = pres.get("display_name")
        if dn:
            return dn
    return status.get("agent_id", "Unknown Agent")
