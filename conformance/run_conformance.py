#!/usr/bin/env python3
"""AIP Conformance Test Suite.

Validates that a target server correctly implements the Agent Interaction Protocol.

Usage:
    pip install httpx
    python run_conformance.py --target http://localhost:8000
    python run_conformance.py --target http://localhost:8000 --api-version v1

Tests:
    1. GET /v1/status returns valid AgentStatus
    2. POST /v1/aip accepts a valid message and returns AIPAck
    3. POST /v1/aip rejects malformed messages with 422
    4. POST /v1/aip with wrong "to" returns 400
    5. Status response includes discovery endpoints
"""

from __future__ import annotations

import argparse
import json
import sys
from uuid import uuid4

import httpx

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"


def log(status: str, name: str, detail: str = ""):
    print(f"  [{status}] {name}" + (f"  — {detail}" if detail else ""))


def make_message(to: str, action: str = "request_context") -> dict:
    return {
        "version": "1.0",
        "message_id": str(uuid4()),
        "from": "conformance-tester",
        "to": to,
        "from_role": "tester",
        "action": action,
        "intent": "Conformance test message",
        "payload": {"test": True},
        "priority": "normal",
    }


def test_status(client: httpx.Client, base: str, api_version: str) -> dict | None:
    """Test 1: GET /v1/status returns valid AgentStatus."""
    try:
        r = client.get(f"{base}/{api_version}/status")
        if r.status_code != 200:
            log(FAIL, "GET /status", f"Expected 200, got {r.status_code}")
            return None
        data = r.json()
        required = ["agent_id", "role"]
        missing = [f for f in required if f not in data]
        if missing:
            log(FAIL, f"GET /{api_version}/status", f"Missing required fields: {missing}")
            return None
        log(PASS, f"GET /{api_version}/status", f"agent_id={data['agent_id']} role={data['role']}")
        return data
    except Exception as e:
        log(FAIL, f"GET /{api_version}/status", str(e))
        return None


def test_send_valid(client: httpx.Client, base: str, agent_id: str, api_version: str):
    """Test 2: POST /v1/aip accepts valid message."""
    msg = make_message(to=agent_id)
    try:
        r = client.post(f"{base}/{api_version}/aip", json=msg)
        if r.status_code != 200:
            log(FAIL, "POST /v1/aip (valid)", f"Expected 200, got {r.status_code}: {r.text[:200]}")
            return
        ack = r.json()
        if not ack.get("ok"):
            log(FAIL, "POST /v1/aip (valid)", f"ack.ok is not true: {ack}")
            return
        if ack.get("message_id") != msg["message_id"]:
            log(FAIL, "POST /v1/aip (valid)", "ack.message_id does not match request")
            return
        log(PASS, "POST /v1/aip (valid)", f"status={ack.get('status')}")
    except Exception as e:
        log(FAIL, "POST /v1/aip (valid)", str(e))


def test_send_malformed(client: httpx.Client, base: str, api_version: str):
    """Test 3: POST /v1/aip rejects malformed message with 422."""
    bad = {"version": "1.0", "message_id": str(uuid4())}
    try:
        r = client.post(f"{base}/{api_version}/aip", json=bad)
        if r.status_code == 422:
            log(PASS, "POST /v1/aip (malformed)", "Correctly rejected with 422")
        else:
            log(FAIL, "POST /v1/aip (malformed)", f"Expected 422, got {r.status_code}")
    except Exception as e:
        log(FAIL, "POST /v1/aip (malformed)", str(e))


def test_send_wrong_target(client: httpx.Client, base: str, api_version: str):
    """Test 4: POST /v1/aip with wrong 'to' returns 400."""
    msg = make_message(to="nonexistent-agent-xyz-12345")
    try:
        r = client.post(f"{base}/{api_version}/aip", json=msg)
        if r.status_code == 400:
            log(PASS, "POST /v1/aip (wrong target)", "Correctly rejected with 400")
        elif r.status_code == 200:
            log(SKIP, "POST /v1/aip (wrong target)", "Server accepted (may support broadcast)")
        else:
            log(FAIL, "POST /v1/aip (wrong target)", f"Expected 400, got {r.status_code}")
    except Exception as e:
        log(FAIL, "POST /v1/aip (wrong target)", str(e))


def test_status_discovery(status: dict):
    """Test 5: Status includes discovery endpoints."""
    endpoints = status.get("endpoints")
    if endpoints and (endpoints.get("aip") or endpoints.get("status")):
        log(PASS, "Status discovery", f"endpoints={json.dumps(endpoints)}")
    elif status.get("base_url"):
        log(PASS, "Status discovery", f"base_url={status['base_url']} (endpoints not set)")
    else:
        log(SKIP, "Status discovery", "No base_url or endpoints (RECOMMENDED but not required)")


def main():
    parser = argparse.ArgumentParser(description="AIP Conformance Test Suite")
    parser.add_argument("--target", required=True, help="Base URL of the AIP agent to test")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds")
    parser.add_argument("--api-version", default="v1", help="API version prefix (default: v1)")
    args = parser.parse_args()

    base = args.target.rstrip("/")
    api_ver = args.api_version.strip("/")
    print(f"\nAIP Conformance Tests — target: {base}/{api_ver}\n")

    with httpx.Client(timeout=args.timeout) as client:
        status = test_status(client, base, api_ver)
        if status is None:
            print(f"\nGET /{api_ver}/status failed — cannot continue.\n")
            sys.exit(1)

        agent_id = status["agent_id"]
        test_send_valid(client, base, agent_id, api_ver)
        test_send_malformed(client, base, api_ver)
        test_send_wrong_target(client, base, api_ver)
        test_status_discovery(status)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
