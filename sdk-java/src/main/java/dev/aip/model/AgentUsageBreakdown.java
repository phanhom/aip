package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AgentUsageBreakdown(
        @JsonProperty("agent_id") String agentId,
        @JsonProperty("total_tokens") int totalTokens,
        @JsonProperty("total_cost_usd") double totalCostUsd,
        @JsonProperty("invocations") int invocations
) {}
