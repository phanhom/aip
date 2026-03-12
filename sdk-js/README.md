# @aip-protocol/sdk

JavaScript/TypeScript SDK for the [Agent Interaction Protocol (AIP)](https://aip-protocol.dev) — an open standard for agent-to-agent and human-to-agent communication.

## Installation

```bash
npm install @aip-protocol/sdk
```

## Requirements

- **Node.js** 18+ (uses native `fetch`)
- **Browsers** with `fetch` and `ReadableStream` support

No runtime dependencies — uses native Web APIs only.

## Quick Start

### Node.js

```typescript
import { AIPClient, buildMessage } from "@aip-protocol/sdk";

const client = new AIPClient("https://agent.example.com");

// Non-streaming: send and get JSON ack
const message = buildMessage({
  from: "user",
  to: "agent-backend",
  action: "assign_task",
  intent: "Design the order service REST API",
  payload: { instruction: "Define REST endpoints", deliverables: ["openapi"] },
});

const ack = await client.send(message);
console.log(ack); // { ok: true, message_id: "...", to: "agent-backend", status: "received", task_id?: "..." }
```

### SSE Streaming

```typescript
const message = buildMessage({
  from: "user",
  to: "agent-backend",
  action: "assign_task",
  intent: "Generate API docs",
});

for await (const event of client.sendStream(message)) {
  if (event.event === "status") {
    const data = JSON.parse(event.data);
    console.log("Progress:", data.progress);
  } else if (event.event === "ack") {
    const ack = JSON.parse(event.data);
    console.log("Done:", ack);
  }
}
```

### Agent Discovery

```typescript
const status = await client.getStatus();
console.log(status.agent_id, status.role, status.capabilities);
```

### Task Lifecycle

```typescript
// Get task
const task = await client.getTask("task-001");

// Cancel task
const canceled = await client.cancelTask("task-001");

// Send follow-up (e.g., answer input-required)
const ack = await client.sendToTask("task-001", buildMessage({
  from: "user",
  to: "agent-backend",
  action: "user_instruction",
  intent: "Use the v2 schema",
}));
```

### Browser

```html
<script type="module">
  import { AIPClient, buildMessage } from "https://esm.sh/@aip-protocol/sdk";

  const client = new AIPClient("https://agent.example.com");
  const message = buildMessage({
    from: "user",
    to: "agent",
    action: "assign_task",
    intent: "Hello from browser",
  });

  const ack = await client.send(message);
  document.body.textContent = JSON.stringify(ack, null, 2);
</script>
```

## API

| Method | Description |
|--------|-------------|
| `send(message)` | Send message, get JSON `AIPAck` |
| `sendStream(message)` | Send message, stream SSE events |
| `getStatus()` | Agent discovery |
| `getTask(taskId)` | Get task state |
| `cancelTask(taskId)` | Cancel task |
| `sendToTask(taskId, message)` | Send follow-up into task |

## License

Apache-2.0
