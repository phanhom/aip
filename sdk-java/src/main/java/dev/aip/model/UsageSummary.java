package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

@JsonInclude(NON_NULL)
public record UsageSummary(
        @JsonProperty("period_start") String periodStart,
        @JsonProperty("period_end") String periodEnd,
        @JsonProperty("namespace") String namespace,
        @JsonProperty("total_requests") int totalRequests,
        @JsonProperty("total_prompt_tokens") int totalPromptTokens,
        @JsonProperty("total_completion_tokens") int totalCompletionTokens,
        @JsonProperty("total_tokens") int totalTokens,
        @JsonProperty("total_cached_tokens") int totalCachedTokens,
        @JsonProperty("total_estimated_cost_usd") double totalEstimatedCostUsd,
        @JsonProperty("by_model") List<ModelUsageBreakdown> byModel,
        @JsonProperty("by_agent") List<AgentUsageBreakdown> byAgent
) {}
