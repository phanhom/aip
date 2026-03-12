package dev.aip.client;

/**
 * Simple Server-Sent Event representation.
 */
public record SSEEvent(
        String eventType,
        String data
) {
    public SSEEvent {
        eventType = eventType != null ? eventType : "message";
        data = data != null ? data : "";
    }
}
