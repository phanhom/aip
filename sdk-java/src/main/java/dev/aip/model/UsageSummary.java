package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

@JsonInclude(NON_NULL)
public record UsageSummary(
        @JsonProperty("namespace") String namespace,
        @JsonProperty("since") String since,
        @JsonProperty("until") String until,
        @JsonProperty("total_tokens") int totalTokens,
        @JsonProperty("total_cost_usd") double totalCostUsd,
        @JsonProperty("total_invocations") int totalInvocations,
        @JsonProperty("by_model") List<ModelUsageBreakdown> byModel,
        @JsonProperty("by_agent") List<AgentUsageBreakdown> byAgent
) {}
