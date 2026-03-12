# AIP Java SDK

Java SDK for the [Agent Interaction Protocol (AIP)](https://aip-protocol.dev) — open standard for agent-to-agent communication.

## Requirements

- Java 17+
- Maven 3.6+

## Installation

Add to your `pom.xml`:

```xml
<dependency>
    <groupId>dev.aip-protocol</groupId>
    <artifactId>aip-sdk</artifactId>
    <version>1.0.0</version>
</dependency>
```

## Quick Start

```java
import dev.aip.client.AIPClient;
import dev.aip.model.AIPMessage;
import dev.aip.model.AIPAck;
import dev.aip.model.AgentStatus;
import dev.aip.model.AIPTask;
import dev.aip.model.TaskState;

// Create client
AIPClient client = new AIPClient("https://agent.example.com");

// Build and send a message
AIPMessage msg = AIPMessage.builder("user", "agent-backend", "assign_task", "Design the order service REST API")
    .payload(Map.of("instruction", "Create OpenAPI spec for orders"))
    .build();

AIPAck ack = client.send(msg);
System.out.println("Accepted: " + ack.ok() + ", task: " + ack.taskId());

// Agent discovery
AgentStatus status = client.getStatus();
System.out.println("Agent: " + status.agentId() + ", role: " + status.role());

// Task lifecycle
AIPTask task = client.getTask(ack.taskId());
if (task.state() == TaskState.WORKING) {
    task = client.cancelTask(ack.taskId());
}
```

## SSE Streaming

```java
import dev.aip.client.SSEEvent;
import java.util.stream.Stream;

Stream<SSEEvent> stream = client.sendStream(msg);
stream.forEach(event -> System.out.println(event.eventType() + ": " + event.data()));
```

## License

Apache-2.0
