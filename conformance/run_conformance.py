#!/usr/bin/env python3
"""AIP Conformance Test Suite.

Validates that a target server correctly implements the Agent Interaction Protocol.

Usage:
    pip install httpx
    python run_conformance.py --target http://localhost:8000
    python run_conformance.py --target http://localhost:8000 --level full

Levels:
    basic   — Tests 1–8:  status + messaging fundamentals (minimum for compliance)
    full    — Tests 1–22: all endpoints including tasks, artifacts, streaming, discovery
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from uuid import uuid4

import httpx

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"
INFO = "\033[94mINFO\033[0m"

passed = 0
failed = 0
skipped = 0


def log(status: str, name: str, detail: str = ""):
    global passed, failed, skipped
    if status == PASS:
        passed += 1
    elif status == FAIL:
        failed += 1
    elif status == SKIP:
        skipped += 1
    print(f"  [{status}] {name}" + (f"  — {detail}" if detail else ""))


def msg(to: str, action: str = "request_context", **extra) -> dict:
    m = {
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
    m.update(extra)
    return m


# ═══════════════════════════════════════════════════════════════════════
#  BASIC LEVEL — Status + Messaging (minimum for AIP compliance)
# ═══════════════════════════════════════════════════════════════════════


def t01_status_returns_valid(c: httpx.Client, base: str, v: str) -> dict | None:
    """GET /v1/status returns valid AgentStatus with required fields."""
    try:
        r = c.get(f"{base}/{v}/status")
        if r.status_code != 200:
            log(FAIL, "T01 GET /status", f"Expected 200, got {r.status_code}")
            return None
        data = r.json()
        for f in ["agent_id", "role"]:
            if f not in data:
                log(FAIL, "T01 GET /status", f"Missing required field: {f}")
                return None
        log(PASS, "T01 GET /status", f"agent_id={data['agent_id']} role={data['role']}")
        return data
    except Exception as e:
        log(FAIL, "T01 GET /status", str(e))
        return None


def t02_status_valid_lifecycle(status: dict):
    """AgentStatus.lifecycle is a valid enum value."""
    lc = status.get("lifecycle")
    valid = {None, "idle", "starting", "running", "blocked", "degraded", "failed"}
    if lc in valid:
        log(PASS, "T02 lifecycle enum", f"lifecycle={lc!r}")
    else:
        log(FAIL, "T02 lifecycle enum", f"Invalid lifecycle: {lc!r}")


def t03_status_ok_boolean(status: dict):
    """AgentStatus.ok is a boolean."""
    ok = status.get("ok")
    if isinstance(ok, bool) or ok is None:
        log(PASS, "T03 ok is boolean", f"ok={ok}")
    else:
        log(FAIL, "T03 ok is boolean", f"ok is {type(ok).__name__}: {ok!r}")


def t04_status_endpoints_or_baseurl(status: dict):
    """Status includes discovery info (endpoints or base_url)."""
    ep = status.get("endpoints")
    bu = status.get("base_url")
    if ep and (ep.get("aip") or ep.get("status")):
        log(PASS, "T04 discovery endpoints", f"endpoints={json.dumps(ep)}")
    elif bu:
        log(PASS, "T04 discovery base_url", f"base_url={bu}")
    else:
        log(SKIP, "T04 discovery", "No endpoints or base_url (RECOMMENDED)")


def t05_status_supported_versions(status: dict):
    """AgentStatus.supported_versions includes at least one version."""
    sv = status.get("supported_versions", [])
    if isinstance(sv, list) and len(sv) > 0:
        log(PASS, "T05 supported_versions", f"{sv}")
    else:
        log(SKIP, "T05 supported_versions", "Not set or empty (RECOMMENDED)")


def t06_send_valid(c: httpx.Client, base: str, agent_id: str, v: str):
    """POST /v1/aip accepts a valid message and returns AIPAck."""
    m = msg(to=agent_id)
    try:
        r = c.post(
            f"{base}/{v}/aip", json=m,
            headers={"Accept": "application/json"},
        )
        if r.status_code != 200:
            log(FAIL, "T06 POST /aip (valid)", f"Expected 200, got {r.status_code}")
            return
        ack = r.json()
        if not ack.get("ok"):
            log(FAIL, "T06 POST /aip (valid)", f"ok is not true: {ack}")
            return
        for f in ["message_id", "to", "status"]:
            if f not in ack:
                log(FAIL, "T06 POST /aip (valid)", f"AIPAck missing field: {f}")
                return
        if ack["status"] not in ("received", "queued"):
            log(FAIL, "T06 POST /aip (valid)", f"Unexpected ack status: {ack['status']}")
            return
        log(PASS, "T06 POST /aip (valid)", f"status={ack['status']}")
    except Exception as e:
        log(FAIL, "T06 POST /aip (valid)", str(e))


def t07_send_malformed(c: httpx.Client, base: str, v: str):
    """POST /v1/aip rejects malformed message (missing required fields)."""
    bad = {"version": "1.0", "message_id": str(uuid4())}
    try:
        r = c.post(f"{base}/{v}/aip", json=bad, headers={"Accept": "application/json"})
        if r.status_code == 422:
            log(PASS, "T07 POST /aip (malformed)", "Correctly rejected with 422")
        elif r.status_code == 400:
            log(PASS, "T07 POST /aip (malformed)", "Rejected with 400 (acceptable)")
        else:
            log(FAIL, "T07 POST /aip (malformed)", f"Expected 422, got {r.status_code}")
    except Exception as e:
        log(FAIL, "T07 POST /aip (malformed)", str(e))


def t08_send_wrong_target(c: httpx.Client, base: str, v: str):
    """POST /v1/aip with nonexistent 'to' returns 400 or 404."""
    m = msg(to="nonexistent-agent-xyz-99999")
    try:
        r = c.post(f"{base}/{v}/aip", json=m, headers={"Accept": "application/json"})
        if r.status_code in (400, 404):
            log(PASS, "T08 POST /aip (wrong to)", f"Correctly rejected with {r.status_code}")
        elif r.status_code == 200:
            log(SKIP, "T08 POST /aip (wrong to)", "Server accepted (may support broadcast)")
        else:
            log(FAIL, "T08 POST /aip (wrong to)", f"Expected 400/404, got {r.status_code}")
    except Exception as e:
        log(FAIL, "T08 POST /aip (wrong to)", str(e))


# ═══════════════════════════════════════════════════════════════════════
#  FULL LEVEL — Tasks, Artifacts, Streaming, Idempotency, Discovery
# ═══════════════════════════════════════════════════════════════════════


def t09_status_presentation(status: dict):
    """AgentStatus.presentation has required display_name if present."""
    pres = status.get("presentation")
    if pres is None:
        log(SKIP, "T09 presentation", "Not set (OPTIONAL)")
        return
    if isinstance(pres, dict) and "display_name" in pres:
        log(PASS, "T09 presentation", f"display_name={pres['display_name']!r}")
    else:
        log(FAIL, "T09 presentation", "presentation present but missing display_name")


def t10_status_skills_schema(status: dict):
    """Skills have required id/name/description if present."""
    skills = status.get("skills", [])
    if not skills:
        log(SKIP, "T10 skills schema", "No skills declared")
        return
    for i, s in enumerate(skills):
        for f in ["id", "name", "description"]:
            if f not in s:
                log(FAIL, "T10 skills schema", f"Skill [{i}] missing {f}")
                return
    log(PASS, "T10 skills schema", f"{len(skills)} skill(s) valid")


def t11_ack_echoes_message_id(c: httpx.Client, base: str, agent_id: str, v: str):
    """AIPAck.message_id matches the request message_id."""
    m = msg(to=agent_id)
    try:
        r = c.post(f"{base}/{v}/aip", json=m, headers={"Accept": "application/json"})
        if r.status_code != 200:
            log(SKIP, "T11 ack message_id", f"POST returned {r.status_code}")
            return
        ack = r.json()
        if ack.get("message_id") == m["message_id"]:
            log(PASS, "T11 ack message_id", "Echoed correctly")
        else:
            log(FAIL, "T11 ack message_id", f"Expected {m['message_id']}, got {ack.get('message_id')}")
    except Exception as e:
        log(FAIL, "T11 ack message_id", str(e))


def t12_ack_correlation_id(c: httpx.Client, base: str, agent_id: str, v: str):
    """AIPAck echoes correlation_id when provided."""
    cid = f"corr-{uuid4()}"
    m = msg(to=agent_id, correlation_id=cid)
    try:
        r = c.post(f"{base}/{v}/aip", json=m, headers={"Accept": "application/json"})
        if r.status_code != 200:
            log(SKIP, "T12 correlation_id echo", f"POST returned {r.status_code}")
            return
        ack = r.json()
        if ack.get("correlation_id") == cid:
            log(PASS, "T12 correlation_id echo", "Echoed correctly")
        else:
            log(SKIP, "T12 correlation_id echo", "Not echoed (OPTIONAL)")
    except Exception as e:
        log(FAIL, "T12 correlation_id echo", str(e))


def t13_idempotency_key(c: httpx.Client, base: str, agent_id: str, v: str):
    """Idempotency-Key header produces consistent results on replay."""
    m = msg(to=agent_id)
    idem_key = str(uuid4())
    headers = {"Accept": "application/json", "Idempotency-Key": idem_key}
    try:
        r1 = c.post(f"{base}/{v}/aip", json=m, headers=headers)
        r2 = c.post(f"{base}/{v}/aip", json=m, headers=headers)
        if r1.status_code == 200 and r2.status_code == 200:
            log(PASS, "T13 idempotency", "Both requests returned 200")
        elif r2.status_code == 409:
            log(PASS, "T13 idempotency", "Duplicate detected (409)")
        else:
            log(SKIP, "T13 idempotency", f"First={r1.status_code}, Second={r2.status_code}")
    except Exception as e:
        log(FAIL, "T13 idempotency", str(e))


def t14_task_api(c: httpx.Client, base: str, v: str):
    """GET /v1/tasks/{nonexistent} returns 404 (not 405)."""
    try:
        r = c.get(f"{base}/{v}/tasks/nonexistent-task-xyz")
        if r.status_code == 404:
            log(PASS, "T14 task API", "GET /tasks returns 404 for unknown task")
        elif r.status_code == 405:
            log(SKIP, "T14 task API", "Task API not implemented (405)")
        else:
            log(SKIP, "T14 task API", f"Returned {r.status_code}")
    except Exception as e:
        log(FAIL, "T14 task API", str(e))


def t15_artifacts_endpoint(c: httpx.Client, base: str, v: str):
    """POST /v1/artifacts returns 415 or 201 (not 405)."""
    try:
        r = c.post(f"{base}/{v}/artifacts", content=b"test", headers={"Content-Type": "text/plain"})
        if r.status_code in (201, 415, 422):
            log(PASS, "T15 artifacts", f"Artifacts endpoint responds ({r.status_code})")
        elif r.status_code == 405:
            log(SKIP, "T15 artifacts", "Artifacts not implemented (405)")
        else:
            log(SKIP, "T15 artifacts", f"Returned {r.status_code}")
    except Exception as e:
        log(FAIL, "T15 artifacts", str(e))


def t16_sse_streaming(c: httpx.Client, base: str, agent_id: str, v: str):
    """POST /v1/aip with Accept: text/event-stream returns SSE."""
    m = msg(to=agent_id)
    try:
        with c.stream(
            "POST", f"{base}/{v}/aip", json=m,
            headers={"Accept": "text/event-stream"},
        ) as r:
            if r.status_code != 200:
                log(SKIP, "T16 SSE streaming", f"Returned {r.status_code}")
                return
            ct = r.headers.get("content-type", "")
            if "text/event-stream" in ct:
                events = []
                for line in r.iter_lines():
                    if line.startswith("event:"):
                        events.append(line.split(":", 1)[1].strip())
                    if len(events) >= 3 or (events and events[-1] == "done"):
                        break
                log(PASS, "T16 SSE streaming", f"Events received: {events[:5]}")
            elif "application/json" in ct:
                log(SKIP, "T16 SSE streaming", "Server returned JSON (no streaming support)")
            else:
                log(SKIP, "T16 SSE streaming", f"Content-Type: {ct}")
    except Exception as e:
        log(FAIL, "T16 SSE streaming", str(e))


def t17_error_code_format(c: httpx.Client, base: str, v: str):
    """Error responses include properly formatted error_code."""
    bad = {"version": "1.0", "message_id": str(uuid4())}
    try:
        r = c.post(f"{base}/{v}/aip", json=bad, headers={"Accept": "application/json"})
        if r.status_code in (400, 422):
            data = r.json()
            ec = data.get("error_code", "")
            if ec and ec.startswith("aip/"):
                log(PASS, "T17 error_code format", f"error_code={ec}")
            elif ec:
                log(FAIL, "T17 error_code format", f"Non-standard code: {ec}")
            else:
                log(SKIP, "T17 error_code format", "No error_code in response")
        else:
            log(SKIP, "T17 error_code format", f"Server returned {r.status_code}")
    except Exception as e:
        log(FAIL, "T17 error_code format", str(e))


def t18_content_type_json(c: httpx.Client, base: str, v: str):
    """Responses have Content-Type: application/json."""
    try:
        r = c.get(f"{base}/{v}/status")
        ct = r.headers.get("content-type", "")
        if "application/json" in ct:
            log(PASS, "T18 Content-Type", f"{ct}")
        else:
            log(FAIL, "T18 Content-Type", f"Expected application/json, got: {ct}")
    except Exception as e:
        log(FAIL, "T18 Content-Type", str(e))


def t19_status_scope_self(c: httpx.Client, base: str, v: str):
    """GET /v1/status?scope=self returns single agent status."""
    try:
        r = c.get(f"{base}/{v}/status", params={"scope": "self"})
        if r.status_code != 200:
            log(SKIP, "T19 scope=self", f"Returned {r.status_code}")
            return
        data = r.json()
        if "agent_id" in data:
            log(PASS, "T19 scope=self", f"agent_id={data['agent_id']}")
        else:
            log(FAIL, "T19 scope=self", "Missing agent_id in response")
    except Exception as e:
        log(FAIL, "T19 scope=self", str(e))


def t20_status_scope_group(c: httpx.Client, base: str, v: str):
    """GET /v1/status?scope=group returns GroupStatus or single status."""
    try:
        r = c.get(f"{base}/{v}/status", params={"scope": "group"})
        if r.status_code != 200:
            log(SKIP, "T20 scope=group", f"Returned {r.status_code}")
            return
        data = r.json()
        if "agents" in data and "root_agent_id" in data:
            log(PASS, "T20 scope=group", f"GroupStatus with {len(data['agents'])} agent(s)")
        elif "agent_id" in data:
            log(PASS, "T20 scope=group", "Returns self (worker agent, acceptable)")
        else:
            log(FAIL, "T20 scope=group", "Unrecognized response format")
    except Exception as e:
        log(FAIL, "T20 scope=group", str(e))


def t21_health_endpoint(c: httpx.Client, base: str):
    """GET /health returns 200 (RECOMMENDED)."""
    try:
        r = c.get(f"{base}/health")
        if r.status_code == 200:
            log(PASS, "T21 /health", "OK")
        elif r.status_code == 404:
            log(SKIP, "T21 /health", "Not implemented (RECOMMENDED)")
        else:
            log(SKIP, "T21 /health", f"Returned {r.status_code}")
    except Exception as e:
        log(FAIL, "T21 /health", str(e))


def t22_assign_task_payload(c: httpx.Client, base: str, agent_id: str, v: str):
    """assign_task with standard payload is accepted."""
    m = msg(
        to=agent_id,
        action="assign_task",
        intent="Conformance test: assign_task with standard payload",
        payload={
            "instruction": "Run conformance test task",
            "deliverables": ["test_report"],
        },
    )
    try:
        r = c.post(f"{base}/{v}/aip", json=m, headers={"Accept": "application/json"})
        if r.status_code == 200:
            ack = r.json()
            if ack.get("ok"):
                log(PASS, "T22 assign_task payload", "Accepted")
            else:
                log(FAIL, "T22 assign_task payload", f"ok=false: {ack}")
        else:
            log(SKIP, "T22 assign_task payload", f"Returned {r.status_code}")
    except Exception as e:
        log(FAIL, "T22 assign_task payload", str(e))


# ═══════════════════════════════════════════════════════════════════════
#  Runner
# ═══════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(description="AIP Conformance Test Suite")
    parser.add_argument("--target", required=True, help="Base URL of the AIP agent")
    parser.add_argument("--timeout", type=float, default=15.0, help="Request timeout")
    parser.add_argument("--api-version", default="v1", help="API version prefix")
    parser.add_argument(
        "--level", default="full", choices=["basic", "full"],
        help="Test level: basic (8 tests) or full (22 tests)",
    )
    args = parser.parse_args()

    base = args.target.rstrip("/")
    v = args.api_version.strip("/")
    print(f"\n{'═' * 60}")
    print(f"  AIP Conformance Tests — {args.level} level")
    print(f"  Target: {base}/{v}")
    print(f"{'═' * 60}\n")
    print("  BASIC — Status & Messaging\n")

    with httpx.Client(timeout=args.timeout) as c:
        status = t01_status_returns_valid(c, base, v)
        if status is None:
            print(f"\n  GET /{v}/status failed — cannot continue.\n")
            sys.exit(1)

        agent_id = status["agent_id"]
        t02_status_valid_lifecycle(status)
        t03_status_ok_boolean(status)
        t04_status_endpoints_or_baseurl(status)
        t05_status_supported_versions(status)
        t06_send_valid(c, base, agent_id, v)
        t07_send_malformed(c, base, v)
        t08_send_wrong_target(c, base, v)

        if args.level == "full":
            print(f"\n  FULL — Tasks, Artifacts, Streaming, Discovery\n")
            t09_status_presentation(status)
            t10_status_skills_schema(status)
            t11_ack_echoes_message_id(c, base, agent_id, v)
            t12_ack_correlation_id(c, base, agent_id, v)
            t13_idempotency_key(c, base, agent_id, v)
            t14_task_api(c, base, v)
            t15_artifacts_endpoint(c, base, v)
            t16_sse_streaming(c, base, agent_id, v)
            t17_error_code_format(c, base, v)
            t18_content_type_json(c, base, v)
            t19_status_scope_self(c, base, v)
            t20_status_scope_group(c, base, v)
            t21_health_endpoint(c, base)
            t22_assign_task_payload(c, base, agent_id, v)

    print(f"\n{'═' * 60}")
    print(f"  Results: {passed} passed, {failed} failed, {skipped} skipped")
    level_label = "BASIC" if args.level == "basic" else "FULL"
    total = passed + failed
    if failed == 0 and total > 0:
        print(f"  Verdict: \033[92mCOMPLIANT ({level_label})\033[0m")
    elif failed <= 2:
        print(f"  Verdict: \033[93mPARTIALLY COMPLIANT\033[0m")
    else:
        print(f"  Verdict: \033[91mNON-COMPLIANT\033[0m")
    print(f"{'═' * 60}\n")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
