package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record ModelUsageBreakdown(
        @JsonProperty("model") String model,
        @JsonProperty("prompt_tokens") int promptTokens,
        @JsonProperty("completion_tokens") int completionTokens,
        @JsonProperty("total_tokens") int totalTokens,
        @JsonProperty("total_cost_usd") double totalCostUsd,
        @JsonProperty("invocations") int invocations
) {}
