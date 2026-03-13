package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

@JsonInclude(NON_NULL)
public record TraceEvent(
        @JsonProperty("event_id") String eventId,
        @JsonProperty("trace_id") String traceId,
        @JsonProperty("span_id") String spanId,
        @JsonProperty("parent_span_id") String parentSpanId,
        @JsonProperty("agent_id") String agentId,
        @JsonProperty("trace_type") String traceType,
        @JsonProperty("severity") String severity,
        @JsonProperty("ts") String timestamp,
        @JsonProperty("duration_ms") Double durationMs,
        @JsonProperty("task_id") String taskId,
        @JsonProperty("message_id") String messageId,
        @JsonProperty("correlation_id") String correlationId,
        @JsonProperty("payload") Map<String, Object> payload,
        @JsonProperty("tags") Map<String, String> tags
) {}
