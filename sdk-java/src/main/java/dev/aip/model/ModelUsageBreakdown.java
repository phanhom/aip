package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

@JsonInclude(NON_NULL)
public record ModelUsageBreakdown(
        @JsonProperty("model") String model,
        @JsonProperty("provider") String provider,
        @JsonProperty("requests") int requests,
        @JsonProperty("prompt_tokens") int promptTokens,
        @JsonProperty("completion_tokens") int completionTokens,
        @JsonProperty("total_tokens") int totalTokens,
        @JsonProperty("cached_tokens") int cachedTokens,
        @JsonProperty("estimated_cost_usd") double estimatedCostUsd
) {}
