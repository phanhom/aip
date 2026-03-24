"""Tests for SSE parsing and streaming helpers."""

from aip.send import SSEEvent, _build_sse_event, _parse_sse_lines


class TestSSEParsing:
    def test_single_event(self):
        lines = [
            "event: status",
            'data: {"task_id":"t1","state":"working"}',
            "",
        ]
        events = list(_parse_sse_lines(lines))
        assert len(events) == 1
        assert events[0].event == "status"
        assert events[0].data["task_id"] == "t1"

    def test_multiple_events(self):
        lines = [
            "event: status",
            'data: {"state":"working"}',
            "",
            "event: message",
            'data: {"intent":"partial result"}',
            "",
            "event: done",
            'data: {"ok":true,"message_id":"m1","to":"a","status":"received"}',
            "",
        ]
        events = list(_parse_sse_lines(lines))
        assert len(events) == 3
        assert events[0].event == "status"
        assert events[1].event == "message"
        assert events[2].event == "done"
        assert events[2].data["ok"] is True

    def test_comment_lines_ignored(self):
        lines = [
            ": this is a comment",
            "event: status",
            'data: {"ok":true}',
            "",
        ]
        events = list(_parse_sse_lines(lines))
        assert len(events) == 1
        assert events[0].event == "status"

    def test_default_event_type(self):
        lines = [
            'data: {"value":1}',
            "",
        ]
        events = list(_parse_sse_lines(lines))
        assert events[0].event == "message"

    def test_multiline_data(self):
        lines = [
            "event: message",
            "data: line1",
            "data: line2",
            "",
        ]
        events = list(_parse_sse_lines(lines))
        assert len(events) == 1
        assert events[0].data == {"raw": "line1\nline2"}

    def test_no_trailing_blank_line(self):
        lines = [
            "event: done",
            'data: {"ok":true}',
        ]
        events = list(_parse_sse_lines(lines))
        assert len(events) == 1
        assert events[0].event == "done"

    def test_empty_lines_between_events(self):
        lines = [
            "event: a",
            'data: {"x":1}',
            "",
            "",
            "event: b",
            'data: {"x":2}',
            "",
        ]
        events = list(_parse_sse_lines(lines))
        assert len(events) == 2

    def test_invalid_json_becomes_raw(self):
        lines = [
            "data: not valid json",
            "",
        ]
        events = list(_parse_sse_lines(lines))
        assert events[0].data == {"raw": "not valid json"}


class TestSSEEvent:
    def test_dataclass(self):
        e = SSEEvent(event="done", data={"ok": True})
        assert e.event == "done"
        assert e.data["ok"] is True


class TestBuildSSEEvent:
    def test_valid_json(self):
        e = _build_sse_event("status", '{"state":"working"}')
        assert e.event == "status"
        assert e.data["state"] == "working"

    def test_invalid_json(self):
        e = _build_sse_event("error", "broken json {")
        assert e.data == {"raw": "broken json {"}
