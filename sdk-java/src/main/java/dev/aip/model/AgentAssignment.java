package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * Platform-assigned identity and constraints for an agent.
 * Represents the "job description" the platform gives an agent,
 * separate from its native profile (role, skills, tools).
 */
@JsonInclude(NON_NULL)
public record AgentAssignment(
        @JsonProperty("assigned_role") String assignedRole,
        @JsonProperty("team") String team,
        @JsonProperty("scope") String scope,
        @JsonProperty("granted_tools") List<String> grantedTools,
        @JsonProperty("granted_skills") List<Skill> grantedSkills,
        @JsonProperty("constraints") List<String> constraints,
        @JsonProperty("supervisor") String supervisor,
        @JsonProperty("priority") String priority,
        @JsonProperty("assigned_at") String assignedAt,
        @JsonProperty("metadata") Map<String, Object> metadata
) {}
