package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * Work-in-progress snapshot for operational visibility.
 */
@JsonInclude(NON_NULL)
public record WorkSnapshot(
        @JsonProperty("tasks") List<Map<String, Object>> tasks,
        @JsonProperty("reports") List<Map<String, Object>> reports,
        @JsonProperty("recent_messages") List<Map<String, Object>> recentMessages,
        @JsonProperty("last_seen") String lastSeen,
        @JsonProperty("pending_tasks") Integer pendingTasks
) {}
