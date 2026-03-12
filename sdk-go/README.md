# AIP Go SDK

Go client for the [Agent Interaction Protocol (AIP)](https://github.com/aip-protocol/aip) — open standard for agent-to-agent communication.

## Installation

```bash
go get github.com/aip-protocol/aip/sdk-go
```

## Quick Start

```go
package main

import (
	"context"
	"fmt"
	"io"
	"log"

	"github.com/aip-protocol/aip/sdk-go"
)

func main() {
	client := aip.NewClient("https://agent.example.com")

	// Build a message
	msg, err := aip.BuildMessage("user", "agent-backend", aip.ActionAssignTask, "Design the order service REST API",
		aip.WithPayload(map[string]interface{}{
			"instruction": "Create OpenAPI spec for orders",
			"deliverables": []string{"openapi/orders.yaml"},
		}),
	)
	if err != nil {
		log.Fatal(err)
	}

	// Send (non-streaming)
	ack, err := client.Send(context.Background(), msg)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Ack: ok=%v task_id=%s\n", ack.OK, ack.TaskID)

	// Or stream SSE events
	stream, err := client.SendStream(context.Background(), msg)
	if err != nil {
		log.Fatal(err)
	}
	defer stream.Close()
	for {
		ev, err := stream.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Fatal(err)
		}
		fmt.Printf("Event %s: %s\n", ev.Event, ev.Data)
	}

	// Agent discovery
	status, err := client.GetStatus(context.Background())
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Agent %s (%s): ok=%v\n", status.AgentID, status.Role, status.OK)

	// Task lifecycle
	task, _ := client.GetTask(context.Background(), ack.TaskID)
	_, _ = client.CancelTask(context.Background(), ack.TaskID)
	_, _ = client.SendToTask(context.Background(), ack.TaskID, msg)
}
```

## API Overview

| Method | Description |
|--------|-------------|
| `NewClient(baseURL, opts...)` | Create client; optional `WithAPIVersion`, `WithHTTPClient`, `WithTimeout` |
| `Send(ctx, msg)` | POST /v1/aip — non-streaming, returns `AIPAck` |
| `SendStream(ctx, msg)` | POST /v1/aip with SSE — returns `*EventStream` |
| `GetStatus(ctx)` | GET /v1/status — agent discovery |
| `GetTask(ctx, taskID)` | GET /v1/tasks/{id} |
| `CancelTask(ctx, taskID)` | POST /v1/tasks/{id}/cancel |
| `SendToTask(ctx, taskID, msg)` | POST /v1/tasks/{id}/send |

## Dependencies

Standard library only — no external dependencies.
