"""Tests for AIP message models."""

import pytest
from pydantic import ValidationError

from aip import (
    AckStatus,
    AIPAction,
    AIPMessage,
    AIPPriority,
    AIPStatus,
    ApprovalState,
    Lifecycle,
    build_message,
)
from aip.message import AIPAck


class TestBuildMessage:
    def test_minimal(self):
        msg = build_message(
            from_agent="user",
            to="agent-backend",
            action=AIPAction.assign_task,
            intent="Do something",
        )
        assert msg.to == "agent-backend"
        assert msg.action == AIPAction.assign_task
        assert msg.intent == "Do something"
        assert msg.version == "1.0"
        assert msg.priority == AIPPriority.normal
        assert msg.status == AIPStatus.pending

    def test_with_extras(self):
        msg = build_message(
            from_agent="coordinator",
            to="agent-backend",
            action=AIPAction.assign_task,
            intent="Build API",
            payload={"instruction": "design REST API"},
            priority=AIPPriority.high,
            authority_weight=95,
        )
        assert msg.payload == {"instruction": "design REST API"}
        assert msg.priority == AIPPriority.high
        assert msg.authority_weight == 95

    def test_custom_action_string(self):
        msg = build_message(
            from_agent="user",
            to="agent-x",
            action="x-acme/deploy_canary",
            intent="Deploy canary build",
        )
        assert msg.action == "x-acme/deploy_canary"


class TestAIPMessageWire:
    def test_to_wire_uses_from_alias(self):
        msg = build_message(
            from_agent="user",
            to="backend",
            action=AIPAction.user_instruction,
            intent="Hello",
        )
        wire = msg.to_wire()
        assert "from" in wire
        assert wire["from"] == "user"
        assert "from_agent" not in wire

    def test_to_wire_roundtrip(self):
        msg = build_message(
            from_agent="coordinator",
            to="worker",
            action=AIPAction.assign_task,
            intent="Do X",
            trace_id="trace-123",
            correlation_id="corr-456",
        )
        wire = msg.to_wire()
        restored = AIPMessage(**wire)
        assert restored.from_agent == "coordinator"
        assert restored.trace_id == "trace-123"
        assert restored.correlation_id == "corr-456"

    def test_message_id_auto_generated(self):
        msg1 = build_message(from_agent="a", to="b", action=AIPAction.escalate, intent="x")
        msg2 = build_message(from_agent="a", to="b", action=AIPAction.escalate, intent="x")
        assert msg1.message_id != msg2.message_id

    def test_touch_updates_status(self):
        msg = build_message(from_agent="a", to="b", action=AIPAction.assign_task, intent="x")
        assert msg.status == AIPStatus.pending
        old_updated = msg.updated_at
        msg.touch(AIPStatus.completed)
        assert msg.status == AIPStatus.completed
        assert msg.updated_at >= old_updated


class TestApprovalState:
    def test_values(self):
        assert ApprovalState.not_required == "not_required"
        assert ApprovalState.waiting_human == "waiting_human"
        assert ApprovalState.approved == "approved"
        assert ApprovalState.rejected == "rejected"


class TestAckStatus:
    def test_values(self):
        assert AckStatus.received == "received"
        assert AckStatus.queued == "queued"
        assert AckStatus.rejected == "rejected"

    def test_ack_default(self):
        ack = AIPAck(message_id="m1", to="agent-a")
        assert ack.status == AckStatus.received
        assert ack.status == "received"

    def test_ack_from_string(self):
        ack = AIPAck(message_id="m1", to="agent-a", status="queued")
        assert ack.status == AckStatus.queued

    def test_ack_rejected_with_error(self):
        ack = AIPAck(
            ok=False,
            message_id="m1",
            to="agent-a",
            status="rejected",
            error_code="aip/protocol/invalid_message",
            error_message="Bad payload",
        )
        assert ack.status == AckStatus.rejected
        assert not ack.ok


class TestAuthorityWeightValidation:
    def test_default_is_50(self):
        msg = build_message(from_agent="a", to="b", action="assign_task", intent="x")
        assert msg.authority_weight == 50

    def test_valid_range(self):
        msg = build_message(
            from_agent="a", to="b", action="assign_task",
            intent="x", authority_weight=0,
        )
        assert msg.authority_weight == 0
        msg2 = build_message(
            from_agent="a", to="b", action="assign_task",
            intent="x", authority_weight=100,
        )
        assert msg2.authority_weight == 100

    def test_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            build_message(
                from_agent="a", to="b", action="assign_task",
                intent="x", authority_weight=-1,
            )

    def test_above_100_rejected(self):
        with pytest.raises(ValidationError):
            build_message(
                from_agent="a", to="b", action="assign_task",
                intent="x", authority_weight=101,
            )


class TestLifecycle:
    def test_values(self):
        assert Lifecycle.idle == "idle"
        assert Lifecycle.starting == "starting"
        assert Lifecycle.running == "running"
        assert Lifecycle.blocked == "blocked"
        assert Lifecycle.degraded == "degraded"
        assert Lifecycle.failed == "failed"
