package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * Status document for a single agent. Full status model with presentation,
 * namespace, skills, authentication, and rate limits.
 */
@JsonInclude(NON_NULL)
public record AgentStatus(
        @JsonProperty("agent_id") String agentId,
        @JsonProperty("role") String role,
        @JsonProperty("namespace") String namespace,
        @JsonProperty("presentation") Presentation presentation,
        @JsonProperty("superior") String superior,
        @JsonProperty("authority_weight") Integer authorityWeight,
        @JsonProperty("lifecycle") String lifecycle,
        @JsonProperty("port") Integer port,
        @JsonProperty("ok") Boolean ok,
        @JsonProperty("base_url") String baseUrl,
        @JsonProperty("endpoints") StatusEndpoints endpoints,
        @JsonProperty("capabilities") List<String> capabilities,
        @JsonProperty("skills") List<Skill> skills,
        @JsonProperty("supported_versions") List<String> supportedVersions,
        @JsonProperty("authentication") AuthenticationInfo authentication,
        @JsonProperty("rate_limits") RateLimitInfo rateLimits,
        @JsonProperty("pending_tasks") Integer pendingTasks,
        @JsonProperty("recent_errors") Integer recentErrors,
        @JsonProperty("waiting_for_approval") Boolean waitingForApproval,
        @JsonProperty("last_message_at") String lastMessageAt,
        @JsonProperty("last_seen_at") String lastSeenAt,
        @JsonProperty("metadata") Map<String, Object> metadata,
        @JsonProperty("work") WorkSnapshot work
) {}
