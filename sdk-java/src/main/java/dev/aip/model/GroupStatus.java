package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

@JsonInclude(NON_NULL)
public record GroupStatus(
        @JsonProperty("ok") boolean ok,
        @JsonProperty("service") String service,
        @JsonProperty("namespace") String namespace,
        @JsonProperty("root_agent_id") String rootAgentId,
        @JsonProperty("timestamp") String timestamp,
        @JsonProperty("topology") Map<String, List<String>> topology,
        @JsonProperty("waiting_for_approval") Boolean waitingForApproval,
        @JsonProperty("agents") List<AgentStatus> agents
) {}
