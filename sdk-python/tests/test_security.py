"""Tests for AIP callback security (HMAC-SHA256)."""

import json

from aip.security import SIGNATURE_HEADER, sign_callback, verify_callback


class TestCallbackSigning:
    def test_sign_returns_sha256_prefix(self):
        body = b'{"task_id": "task-001", "state": "completed"}'
        sig = sign_callback(body, "my-secret")
        assert sig.startswith("sha256=")
        assert len(sig) == 7 + 64  # "sha256=" + 64 hex chars

    def test_verify_valid_signature(self):
        body = json.dumps({"task_id": "t1"}).encode()
        secret = "test-secret-key"
        sig = sign_callback(body, secret)
        assert verify_callback(body, secret, sig) is True

    def test_verify_wrong_secret(self):
        body = b'{"ok": true}'
        sig = sign_callback(body, "correct-secret")
        assert verify_callback(body, "wrong-secret", sig) is False

    def test_verify_tampered_body(self):
        secret = "s3cret"
        original = b'{"action": "deploy"}'
        sig = sign_callback(original, secret)
        tampered = b'{"action": "delete"}'
        assert verify_callback(tampered, secret, sig) is False

    def test_verify_wrong_format(self):
        body = b"test"
        assert verify_callback(body, "key", "not-a-valid-sig") is False

    def test_deterministic(self):
        body = b"hello"
        sig1 = sign_callback(body, "k")
        sig2 = sign_callback(body, "k")
        assert sig1 == sig2

    def test_header_constant(self):
        assert SIGNATURE_HEADER == "X-AIP-Signature"
