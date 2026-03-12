#!/usr/bin/env python3
"""AIP Conformance Test Suite.

Validates that a target server correctly implements the Agent Interaction Protocol.

Usage:
    pip install httpx
    python run_conformance.py --target http://localhost:8000

Tests:
    1. GET /status returns valid AgentStatus
    2. POST /aip accepts a valid message and returns AIPAck
    3. POST /aip rejects malformed messages with 422
    4. POST /aip with wrong "to" returns 400
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


def test_status(client: httpx.Client, base: str) -> dict | None:
    """Test 1: GET /status returns valid AgentStatus."""
    try:
        r = client.get(f"{base}/status")
        if r.status_code != 200:
            log(FAIL, "GET /status", f"Expected 200, got {r.status_code}")
            return None
        data = r.json()
        required = ["agent_id", "role"]
        missing = [f for f in required if f not in data]
        if missing:
            log(FAIL, "GET /status", f"Missing required fields: {missing}")
            return None
        log(PASS, "GET /status", f"agent_id={data['agent_id']} role={data['role']}")
        return data
    except Exception as e:
        log(FAIL, "GET /status", str(e))
        return None


def test_send_valid(client: httpx.Client, base: str, agent_id: str):
    """Test 2: POST /aip accepts valid message."""
    msg = make_message(to=agent_id)
    try:
        r = client.post(f"{base}/aip", json=msg)
        if r.status_code != 200:
            log(FAIL, "POST /aip (valid)", f"Expected 200, got {r.status_code}: {r.text[:200]}")
            return
        ack = r.json()
        if not ack.get("ok"):
            log(FAIL, "POST /aip (valid)", f"ack.ok is not true: {ack}")
            return
        if ack.get("message_id") != msg["message_id"]:
            log(FAIL, "POST /aip (valid)", "ack.message_id does not match request")
            return
        log(PASS, "POST /aip (valid)", f"status={ack.get('status')}")
    except Exception as e:
        log(FAIL, "POST /aip (valid)", str(e))


def test_send_malformed(client: httpx.Client, base: str):
    """Test 3: POST /aip rejects malformed message with 422."""
    bad = {"version": "1.0", "message_id": str(uuid4())}
    try:
        r = client.post(f"{base}/aip", json=bad)
        if r.status_code == 422:
            log(PASS, "POST /aip (malformed)", "Correctly rejected with 422")
        else:
            log(FAIL, "POST /aip (malformed)", f"Expected 422, got {r.status_code}")
    except Exception as e:
        log(FAIL, "POST /aip (malformed)", str(e))


def test_send_wrong_target(client: httpx.Client, base: str):
    """Test 4: POST /aip with wrong 'to' returns 400."""
    msg = make_message(to="nonexistent-agent-xyz-12345")
    try:
        r = client.post(f"{base}/aip", json=msg)
        if r.status_code == 400:
            log(PASS, "POST /aip (wrong target)", "Correctly rejected with 400")
        elif r.status_code == 200:
            log(SKIP, "POST /aip (wrong target)", "Server accepted (may support broadcast)")
        else:
            log(FAIL, "POST /aip (wrong target)", f"Expected 400, got {r.status_code}")
    except Exception as e:
        log(FAIL, "POST /aip (wrong target)", str(e))


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
    args = parser.parse_args()

    base = args.target.rstrip("/")
    print(f"\nAIP Conformance Tests — target: {base}\n")

    with httpx.Client(timeout=args.timeout) as client:
        status = test_status(client, base)
        if status is None:
            print("\nGET /status failed — cannot continue.\n")
            sys.exit(1)

        agent_id = status["agent_id"]
        test_send_valid(client, base, agent_id)
        test_send_malformed(client, base)
        test_send_wrong_target(client, base)
        test_status_discovery(status)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
