"""AIP ↔ JSON-RPC 2.0 bidirectional bridge.

Enables AIP agents to interoperate with JSON-RPC 2.0 clients (including Google A2A)
by translating between the two wire formats.

    from aip.jsonrpc_bridge import aip_to_jsonrpc, jsonrpc_to_aip, is_jsonrpc

Usage in a server that accepts both formats:

    body = await request.json()
    if is_jsonrpc(body):
        msg = jsonrpc_to_aip(body)
        ack = handle(msg)
        return aip_ack_to_jsonrpc(ack, request_id=body["id"])
    else:
        msg = AIPMessage(**body)
        return handle(msg)
"""

from __future__ import annotations

from typing import Any


JSONRPC_VERSION = "2.0"
AIP_METHOD_PREFIX = "aip/"

_AIP_ERROR_TO_JSONRPC: dict[str, int] = {
    "aip/protocol/invalid_message": -32600,
    "aip/protocol/invalid_version": -32600,
    "aip/protocol/unsupported_version": -32600,
    "aip/protocol/routing_failed": -32600,
    "aip/execution/unknown_action": -32601,
    "aip/execution/invalid_payload": -32602,
    "aip/governance/": -32001,
    "aip/auth/": -32002,
}


def is_jsonrpc(body: dict[str, Any]) -> bool:
    """Check if a parsed JSON body is a JSON-RPC 2.0 request."""
    return body.get("jsonrpc") == JSONRPC_VERSION and "method" in body


def aip_to_jsonrpc(message: dict[str, Any]) -> dict[str, Any]:
    """Convert an AIP message (wire format) to a JSON-RPC 2.0 request."""
    action = message.get("action", "")
    method = f"{AIP_METHOD_PREFIX}{action}" if not action.startswith(AIP_METHOD_PREFIX) else action

    params = {k: v for k, v in message.items() if k not in ("message_id", "action")}

    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": message.get("message_id"),
        "method": method,
        "params": params,
    }


def jsonrpc_to_aip(request: dict[str, Any]) -> dict[str, Any]:
    """Convert a JSON-RPC 2.0 request to an AIP message (wire format dict)."""
    method: str = request.get("method", "")
    action = method.removeprefix(AIP_METHOD_PREFIX) if method.startswith(AIP_METHOD_PREFIX) else method

    params: dict[str, Any] = request.get("params", {})
    if not isinstance(params, dict):
        params = {}

    aip_msg = {**params, "action": action, "message_id": request.get("id")}

    if "version" not in aip_msg:
        aip_msg["version"] = "1.0"

    return aip_msg


def aip_ack_to_jsonrpc(ack: dict[str, Any], request_id: Any = None) -> dict[str, Any]:
    """Convert an AIPAck (wire format) to a JSON-RPC 2.0 response."""
    rid = request_id or ack.get("message_id")

    if ack.get("ok", True):
        result = {k: v for k, v in ack.items() if k != "ok" and v is not None}
        return {"jsonrpc": JSONRPC_VERSION, "id": rid, "result": result}

    error_code = ack.get("error_code", "")
    rpc_code = _resolve_jsonrpc_code(error_code)

    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": rid,
        "error": {
            "code": rpc_code,
            "message": ack.get("error_message", "Unknown error"),
            "data": {
                "error_code": error_code,
                "error_message": ack.get("error_message"),
            },
        },
    }


def jsonrpc_error_to_aip(error_response: dict[str, Any]) -> dict[str, Any]:
    """Convert a JSON-RPC 2.0 error response to AIP error fields."""
    error = error_response.get("error", {})
    data = error.get("data", {})

    return {
        "ok": False,
        "message_id": error_response.get("id"),
        "error_code": data.get("error_code", f"jsonrpc/error/{error.get('code', -32603)}"),
        "error_message": data.get("error_message") or error.get("message", "Unknown error"),
        "status": "rejected",
    }


def _resolve_jsonrpc_code(aip_error_code: str) -> int:
    """Map an AIP error code to the closest JSON-RPC 2.0 numeric error code."""
    if aip_error_code in _AIP_ERROR_TO_JSONRPC:
        return _AIP_ERROR_TO_JSONRPC[aip_error_code]

    for prefix, code in _AIP_ERROR_TO_JSONRPC.items():
        if prefix.endswith("/") and aip_error_code.startswith(prefix):
            return code

    return -32000
