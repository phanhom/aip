package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * Rate limiting and quota information for client self-regulation.
 */
@JsonInclude(NON_NULL)
public record RateLimitInfo(
        @JsonProperty("max_requests_per_minute") Integer maxRequestsPerMinute,
        @JsonProperty("max_requests_per_day") Integer maxRequestsPerDay,
        @JsonProperty("max_concurrent_tasks") Integer maxConcurrentTasks,
        @JsonProperty("remaining_requests") Integer remainingRequests,
        @JsonProperty("remaining_tasks") Integer remainingTasks,
        @JsonProperty("reset_at") String resetAt
) {}
