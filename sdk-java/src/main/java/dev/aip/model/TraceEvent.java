package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

@JsonInclude(NON_NULL)
public record TraceEvent(
        @JsonProperty("event_id") String eventId,
        @JsonProperty("trace_id") String traceId,
        @JsonProperty("span_id") String spanId,
        @JsonProperty("parent_span_id") String parentSpanId,
        @JsonProperty("parent_event_id") String parentEventId,
        @JsonProperty("agent_id") String agentId,
        @JsonProperty("trace_type") String traceType,
        @JsonProperty("severity") String severity,
        @JsonProperty("timestamp") String timestamp,
        @JsonProperty("duration_ms") Integer durationMs,
        @JsonProperty("task_id") String taskId,
        @JsonProperty("message_id") String messageId,
        @JsonProperty("correlation_id") String correlationId,
        @JsonProperty("summary") String summary,
        @JsonProperty("payload") Map<String, Object> payload,
        @JsonProperty("metadata") Map<String, Object> metadata,
        @JsonProperty("tags") List<String> tags,
        @JsonProperty("namespace") String namespace
) {}
