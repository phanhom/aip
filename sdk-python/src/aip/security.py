"""AIP callback security — HMAC-SHA256 signing and verification.

Per spec Section 4.1.4, when ``callback_url`` and ``callback_secret`` are set,
the receiver MUST sign callback payloads with HMAC-SHA256 and include the
signature in the ``X-AIP-Signature`` header.

Usage (signing a callback before sending):

    from aip.security import sign_callback

    body = json.dumps(task_result).encode()
    signature = sign_callback(body, callback_secret)
    httpx.post(callback_url, content=body, headers={
        "X-AIP-Signature": signature,
        "X-AIP-Event": "task.completed",
        "Content-Type": "application/json",
    })

Usage (verifying an incoming callback):

    from aip.security import verify_callback

    body = await request.body()
    sig = request.headers.get("X-AIP-Signature", "")
    if not verify_callback(body, my_secret, sig):
        return Response(status_code=401)
"""

from __future__ import annotations

import hashlib
import hmac

SIGNATURE_HEADER = "X-AIP-Signature"
EVENT_HEADER = "X-AIP-Event"


def sign_callback(body: bytes, secret: str) -> str:
    """Compute the ``X-AIP-Signature`` header value for a callback payload.

    Returns ``sha256=<hex_digest>``.
    """
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_callback(body: bytes, secret: str, signature: str) -> bool:
    """Verify an ``X-AIP-Signature`` header against the payload.

    Uses constant-time comparison to prevent timing attacks.
    """
    expected = sign_callback(body, secret)
    return hmac.compare_digest(expected, signature)
