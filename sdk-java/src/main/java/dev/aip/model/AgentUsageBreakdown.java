package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

@JsonInclude(NON_NULL)
public record AgentUsageBreakdown(
        @JsonProperty("agent_id") String agentId,
        @JsonProperty("requests") int requests,
        @JsonProperty("total_tokens") int totalTokens,
        @JsonProperty("estimated_cost_usd") double estimatedCostUsd,
        @JsonProperty("by_model") List<ModelUsageBreakdown> byModel
) {}
