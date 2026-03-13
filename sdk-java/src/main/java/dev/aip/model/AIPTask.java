package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * A long-running task tracked by the agent.
 */
@JsonInclude(NON_NULL)
public record AIPTask(
        @JsonProperty("task_id") String taskId,
        @JsonProperty("message_id") String messageId,
        @JsonProperty("state") TaskState state,
        @JsonProperty("from") String from,
        @JsonProperty("to") String to,
        @JsonProperty("action") String action,
        @JsonProperty("intent") String intent,
        @JsonProperty("progress") Double progress,
        @JsonProperty("artifacts") List<Artifact> artifacts,
        @JsonProperty("history") List<Map<String, Object>> history,
        @JsonProperty("error_code") String errorCode,
        @JsonProperty("error_message") String errorMessage,
        @JsonProperty("trace_id") String traceId,
        @JsonProperty("correlation_id") String correlationId,
        @JsonProperty("parent_task_id") String parentTaskId,
        @JsonProperty("metadata") Map<String, Object> metadata,
        @JsonProperty("created_at") String createdAt,
        @JsonProperty("updated_at") String updatedAt
) {}
