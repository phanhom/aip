"""AIP client functions — high-level API for all spec-defined endpoints.

Covers every endpoint category:
    - Status:    fetch_status / async_fetch_status
    - Tasks:     get_task, cancel_task, send_to_task  (+ async variants)
    - Artifacts: upload_artifact, get_artifact        (+ async variants)
    - Registry:  register_agent, heartbeat, deregister_agent (+ async variants)
    - Traces:    emit_traces, query_traces            (+ async variants)
    - Usage:     get_usage / async_get_usage
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT = 30.0
DEFAULT_API_VERSION = "v1"


def _url(base: str, version: str, path: str) -> str:
    return f"{base.rstrip('/')}/{version}/{path.lstrip('/')}"


# ── Status ────────────────────────────────────────────────────────────


def fetch_status(
    base_url: str,
    *,
    scope: str = "self",
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """GET /v1/status — fetch agent status and capabilities."""
    import httpx

    url = _url(base_url, api_version, "status")
    params = {"scope": scope} if scope != "self" else {}
    with httpx.Client(timeout=timeout) as client:
        r = client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()


async def async_fetch_status(
    base_url: str,
    *,
    scope: str = "self",
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """GET /v1/status (async)."""
    import httpx

    url = _url(base_url, api_version, "status")
    params = {"scope": scope} if scope != "self" else {}
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()


# ── Tasks ─────────────────────────────────────────────────────────────


def get_task(
    base_url: str,
    task_id: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """GET /v1/tasks/{task_id} — retrieve task state, artifacts, and history."""
    import httpx

    url = _url(base_url, api_version, f"tasks/{task_id}")
    with httpx.Client(timeout=timeout) as client:
        r = client.get(url, headers=headers)
        r.raise_for_status()
        return r.json()


async def async_get_task(
    base_url: str,
    task_id: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """GET /v1/tasks/{task_id} (async)."""
    import httpx

    url = _url(base_url, api_version, f"tasks/{task_id}")
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        return r.json()


def cancel_task(
    base_url: str,
    task_id: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """POST /v1/tasks/{task_id}/cancel — request task cancellation."""
    import httpx

    url = _url(base_url, api_version, f"tasks/{task_id}/cancel")
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, headers=headers)
        r.raise_for_status()
        return r.json()


async def async_cancel_task(
    base_url: str,
    task_id: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """POST /v1/tasks/{task_id}/cancel (async)."""
    import httpx

    url = _url(base_url, api_version, f"tasks/{task_id}/cancel")
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, headers=headers)
        r.raise_for_status()
        return r.json()


def send_to_task(
    base_url: str,
    task_id: str,
    message: Any,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """POST /v1/tasks/{task_id}/send — send a follow-up message into a task."""
    import httpx

    body = message.to_wire() if hasattr(message, "to_wire") else message
    url = _url(base_url, api_version, f"tasks/{task_id}/send")
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=body, headers=headers)
        r.raise_for_status()
        return r.json()


async def async_send_to_task(
    base_url: str,
    task_id: str,
    message: Any,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """POST /v1/tasks/{task_id}/send (async)."""
    import httpx

    body = message.to_wire() if hasattr(message, "to_wire") else message
    url = _url(base_url, api_version, f"tasks/{task_id}/send")
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, json=body, headers=headers)
        r.raise_for_status()
        return r.json()


# ── Artifacts ─────────────────────────────────────────────────────────


def upload_artifact(
    base_url: str,
    file: str | Path | bytes,
    *,
    name: str | None = None,
    description: str | None = None,
    task_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    timeout: float = 120.0,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """POST /v1/artifacts — upload a file (multipart/form-data).

    ``file`` can be a path string, Path object, or raw bytes.
    """
    import httpx

    url = _url(base_url, api_version, "artifacts")
    files, data = _prepare_artifact_upload(file, name, description, task_id, metadata)
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, files=files, data=data, headers=headers)
        r.raise_for_status()
        return r.json()


async def async_upload_artifact(
    base_url: str,
    file: str | Path | bytes,
    *,
    name: str | None = None,
    description: str | None = None,
    task_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    timeout: float = 120.0,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """POST /v1/artifacts (async)."""
    import httpx

    url = _url(base_url, api_version, "artifacts")
    files, data = _prepare_artifact_upload(file, name, description, task_id, metadata)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, files=files, data=data, headers=headers)
        r.raise_for_status()
        return r.json()


def get_artifact(
    base_url: str,
    artifact_id: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> bytes:
    """GET /v1/artifacts/{artifact_id} — download artifact content as bytes."""
    import httpx

    url = _url(base_url, api_version, f"artifacts/{artifact_id}")
    with httpx.Client(timeout=timeout) as client:
        r = client.get(url, headers=headers)
        r.raise_for_status()
        return r.content


async def async_get_artifact(
    base_url: str,
    artifact_id: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> bytes:
    """GET /v1/artifacts/{artifact_id} (async)."""
    import httpx

    url = _url(base_url, api_version, f"artifacts/{artifact_id}")
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        return r.content


def _prepare_artifact_upload(file, name, description, task_id, metadata):
    import json as _json

    if isinstance(file, (str, Path)):
        p = Path(file)
        file_tuple = ("file", (p.name, p.read_bytes()))
        name = name or p.name
    elif isinstance(file, bytes):
        file_tuple = ("file", (name or "upload", file))
    else:
        raise TypeError(f"file must be str, Path, or bytes, got {type(file).__name__}")

    data: dict[str, str] = {}
    if name:
        data["name"] = name
    if description:
        data["description"] = description
    if task_id:
        data["task_id"] = task_id
    if metadata:
        data["metadata"] = _json.dumps(metadata)
    return {"file": file_tuple}, data


# ── Registry ──────────────────────────────────────────────────────────


def register_agent(
    platform_url: str,
    base_url: str,
    *,
    namespace: str | None = None,
    protocol: str = "auto",
    credentials: dict[str, Any] | None = None,
    assignment: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """POST /v1/registry/agents — register with a management platform."""
    import httpx

    url = _url(platform_url, api_version, "registry/agents")
    body: dict[str, Any] = {"base_url": base_url, "protocol": protocol}
    if namespace:
        body["namespace"] = namespace
    if credentials:
        body["credentials"] = credentials
    if assignment:
        body["assignment"] = assignment
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=body, headers=headers)
        r.raise_for_status()
        return r.json()


async def async_register_agent(
    platform_url: str,
    base_url: str,
    *,
    namespace: str | None = None,
    protocol: str = "auto",
    credentials: dict[str, Any] | None = None,
    assignment: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """POST /v1/registry/agents (async)."""
    import httpx

    url = _url(platform_url, api_version, "registry/agents")
    body: dict[str, Any] = {"base_url": base_url, "protocol": protocol}
    if namespace:
        body["namespace"] = namespace
    if credentials:
        body["credentials"] = credentials
    if assignment:
        body["assignment"] = assignment
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, json=body, headers=headers)
        r.raise_for_status()
        return r.json()


def heartbeat(
    heartbeat_url: str,
    *,
    ok: bool = True,
    lifecycle: str = "running",
    pending_tasks: int = 0,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """POST /v1/registry/agents/{id}/heartbeat — send liveness signal."""
    import httpx

    body = {
        "ok": ok,
        "lifecycle": lifecycle,
        "pending_tasks": pending_tasks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with httpx.Client(timeout=timeout) as client:
        r = client.post(heartbeat_url, json=body, headers=headers)
        r.raise_for_status()
        return r.json()


async def async_heartbeat(
    heartbeat_url: str,
    *,
    ok: bool = True,
    lifecycle: str = "running",
    pending_tasks: int = 0,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """POST /v1/registry/agents/{id}/heartbeat (async)."""
    import httpx

    body = {
        "ok": ok,
        "lifecycle": lifecycle,
        "pending_tasks": pending_tasks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(heartbeat_url, json=body, headers=headers)
        r.raise_for_status()
        return r.json()


def deregister_agent(
    platform_url: str,
    agent_id: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> None:
    """DELETE /v1/registry/agents/{id} — graceful deregistration."""
    import httpx

    url = _url(platform_url, api_version, f"registry/agents/{agent_id}")
    with httpx.Client(timeout=timeout) as client:
        r = client.delete(url, headers=headers)
        r.raise_for_status()


async def async_deregister_agent(
    platform_url: str,
    agent_id: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> None:
    """DELETE /v1/registry/agents/{id} (async)."""
    import httpx

    url = _url(platform_url, api_version, f"registry/agents/{agent_id}")
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.delete(url, headers=headers)
        r.raise_for_status()


# ── Traces ────────────────────────────────────────────────────────────


def emit_traces(
    base_url: str,
    events: list[dict[str, Any]],
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """POST /v1/traces — emit a batch of trace events."""
    import httpx

    url = _url(base_url, api_version, "traces")
    body = {"events": events}
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=body, headers=headers)
        r.raise_for_status()
        return r.json()


async def async_emit_traces(
    base_url: str,
    events: list[dict[str, Any]],
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """POST /v1/traces (async)."""
    import httpx

    url = _url(base_url, api_version, "traces")
    body = {"events": events}
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, json=body, headers=headers)
        r.raise_for_status()
        return r.json()


def query_traces(
    base_url: str,
    *,
    agent_id: str | None = None,
    trace_id: str | None = None,
    trace_type: str | None = None,
    task_id: str | None = None,
    severity: str | None = None,
    namespace: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 100,
    offset: int = 0,
    order: str = "desc",
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """GET /v1/traces — query trace events with filters."""
    import httpx

    url = _url(base_url, api_version, "traces")
    params = _build_trace_params(
        agent_id, trace_id, trace_type, task_id, severity,
        namespace, since, until, limit, offset, order,
    )
    with httpx.Client(timeout=timeout) as client:
        r = client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()


async def async_query_traces(
    base_url: str,
    *,
    agent_id: str | None = None,
    trace_id: str | None = None,
    trace_type: str | None = None,
    task_id: str | None = None,
    severity: str | None = None,
    namespace: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 100,
    offset: int = 0,
    order: str = "desc",
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """GET /v1/traces (async)."""
    import httpx

    url = _url(base_url, api_version, "traces")
    params = _build_trace_params(
        agent_id, trace_id, trace_type, task_id, severity,
        namespace, since, until, limit, offset, order,
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()


# ── Usage ─────────────────────────────────────────────────────────────


def get_usage(
    base_url: str,
    *,
    namespace: str | None = None,
    agent_id: str | None = None,
    model: str | None = None,
    since: str | None = None,
    until: str | None = None,
    group_by: str = "model",
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """GET /v1/usage — aggregated LLM usage and cost summary."""
    import httpx

    url = _url(base_url, api_version, "usage")
    params = _build_usage_params(namespace, agent_id, model, since, until, group_by)
    with httpx.Client(timeout=timeout) as client:
        r = client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()


async def async_get_usage(
    base_url: str,
    *,
    namespace: str | None = None,
    agent_id: str | None = None,
    model: str | None = None,
    since: str | None = None,
    until: str | None = None,
    group_by: str = "model",
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    """GET /v1/usage (async)."""
    import httpx

    url = _url(base_url, api_version, "usage")
    params = _build_usage_params(namespace, agent_id, model, since, until, group_by)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()


# ── Internal helpers ──────────────────────────────────────────────────


def _build_trace_params(
    agent_id, trace_id, trace_type, task_id, severity,
    namespace, since, until, limit, offset, order,
) -> dict[str, Any]:
    params: dict[str, Any] = {"limit": limit, "offset": offset, "order": order}
    if agent_id:
        params["agent_id"] = agent_id
    if trace_id:
        params["trace_id"] = trace_id
    if trace_type:
        params["trace_type"] = trace_type
    if task_id:
        params["task_id"] = task_id
    if severity:
        params["severity"] = severity
    if namespace:
        params["namespace"] = namespace
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    return params


def _build_usage_params(namespace, agent_id, model, since, until, group_by) -> dict[str, Any]:
    params: dict[str, Any] = {"group_by": group_by}
    if namespace:
        params["namespace"] = namespace
    if agent_id:
        params["agent_id"] = agent_id
    if model:
        params["model"] = model
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    return params
