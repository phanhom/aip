package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * Discoverable endpoints for an agent.
 */
@JsonInclude(NON_NULL)
public record StatusEndpoints(
        @JsonProperty("aip") String aip,
        @JsonProperty("status") String status
) {}
