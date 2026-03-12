package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * Authentication schemes supported by this agent.
 */
@JsonInclude(NON_NULL)
public record AuthenticationInfo(
        @JsonProperty("schemes") List<String> schemes,
        @JsonProperty("oauth2") Map<String, Object> oauth2
) {}
