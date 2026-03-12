# aip-protocol — Python SDK

Official Python SDK for the **Agent Interaction Protocol (AIP)**.

```bash
pip install aip-protocol
```

## Quick Start

```python
from aip import AIPAction, build_message, send

# Build a message
msg = build_message(
    from_agent="user",
    to="agent-backend",
    action=AIPAction.assign_task,
    intent="Design the order service API",
    payload={"instruction": "Define REST endpoints and schemas"},
)

# Inspect wire format
print(msg.to_wire())

# Send to an AIP-compliant agent
ack = send(base_url="http://localhost:8000", message=msg)
print(ack)  # {"ok": true, "message_id": "...", "to": "agent-backend", "status": "received"}
```

## Async Support

```python
from aip import async_send, build_message, AIPAction

msg = build_message(from_agent="user", to="backend", action=AIPAction.assign_task, intent="Do X")
ack = await async_send(base_url="http://localhost:8000", message=msg)
```

## Batch Sending

```python
from aip import send_batch, build_message, AIPAction

messages = [
    ("http://agent-a:8000", build_message(from_agent="coord", to="a", action=AIPAction.assign_task, intent="Task A")),
    ("http://agent-b:8000", build_message(from_agent="coord", to="b", action=AIPAction.assign_task, intent="Task B")),
]
results = send_batch(messages)
```

## Status Models

```python
from aip import AgentStatus, StatusEndpoints

status = AgentStatus(
    agent_id="my-agent",
    role="backend_engineer",
    lifecycle="running",
    ok=True,
    base_url="http://localhost:8000",
    endpoints=StatusEndpoints(
        aip="http://localhost:8000/aip",
        status="http://localhost:8000/status",
    ),
    capabilities=["assign_task", "submit_report"],
)
print(status.model_dump())
```

## Reliability

The send layer includes:
- Exponential backoff with jitter
- Configurable timeout and max retries
- Automatic retry on 5xx, timeout, and connection errors
- No retry on 4xx client errors
- Optional idempotency key

```python
from aip import SendParams, send

params = SendParams(timeout=10.0, max_retries=3)
ack = send("http://localhost:8000", msg, params=params)
```

## Logging

Set `AIP_LOG=1` for protocol-level logs, or pass your own logger:

```python
import logging
my_logger = logging.getLogger("myapp")
ack = send("http://localhost:8000", msg, logger=my_logger, log_extra={"trace_id": "abc"})
```

## Links

- [AIP Specification](https://github.com/aip-protocol/aip/tree/main/spec)
- [JSON Schemas](https://github.com/aip-protocol/aip/tree/main/spec/schemas)
- [Examples](https://github.com/aip-protocol/aip/tree/main/examples)
