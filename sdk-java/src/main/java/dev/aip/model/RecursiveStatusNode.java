package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * Recursive status tree node: agent plus all direct and indirect subordinates.
 */
@JsonInclude(NON_NULL)
public record RecursiveStatusNode(
        @JsonProperty("self") AgentStatus self,
        @JsonProperty("subordinates") List<RecursiveStatusNode> subordinates
) {}
