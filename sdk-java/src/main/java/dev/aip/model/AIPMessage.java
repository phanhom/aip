package dev.aip.model;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

import static com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL;

/**
 * AIP message envelope — the universal wire format for agent communication.
 */
@JsonInclude(NON_NULL)
public final class AIPMessage {
    @JsonProperty("version")
    private final String version;

    @JsonProperty("message_id")
    private final String messageId;

    @JsonProperty("correlation_id")
    private final String correlationId;

    @JsonProperty("trace_id")
    private final String traceId;

    @JsonProperty("parent_task_id")
    private final String parentTaskId;

    @JsonProperty("from")
    private final String from;

    @JsonProperty("to")
    private final String to;

    @JsonProperty("from_role")
    private final String fromRole;

    @JsonProperty("to_role")
    private final String toRole;

    @JsonProperty("to_host")
    private final String toHost;

    @JsonProperty("to_base_url")
    private final String toBaseUrl;

    @JsonProperty("route_scope")
    private final String routeScope;

    @JsonProperty("action")
    private final String action;

    @JsonProperty("intent")
    private final String intent;

    @JsonProperty("payload")
    private final Map<String, Object> payload;

    @JsonProperty("expected_output")
    private final String expectedOutput;

    @JsonProperty("constraints")
    private final List<String> constraints;

    @JsonProperty("priority")
    private final String priority;

    @JsonProperty("status")
    private final String status;

    @JsonProperty("authority_weight")
    private final Integer authorityWeight;

    @JsonProperty("requires_approval")
    private final Boolean requiresApproval;

    @JsonProperty("approval_state")
    private final String approvalState;

    @JsonProperty("callback_url")
    private final String callbackUrl;

    @JsonProperty("callback_secret")
    private final String callbackSecret;

    @JsonProperty("retries")
    private final Integer retries;

    @JsonProperty("latency_ms")
    private final Integer latencyMs;

    @JsonProperty("error_code")
    private final String errorCode;

    @JsonProperty("error_message")
    private final String errorMessage;

    @JsonProperty("created_at")
    private final String createdAt;

    @JsonProperty("updated_at")
    private final String updatedAt;

    private AIPMessage(Builder builder) {
        this.version = builder.version;
        this.messageId = builder.messageId;
        this.correlationId = builder.correlationId;
        this.traceId = builder.traceId;
        this.parentTaskId = builder.parentTaskId;
        this.from = builder.from;
        this.to = builder.to;
        this.fromRole = builder.fromRole;
        this.toRole = builder.toRole;
        this.toHost = builder.toHost;
        this.toBaseUrl = builder.toBaseUrl;
        this.routeScope = builder.routeScope;
        this.action = builder.action;
        this.intent = builder.intent;
        this.payload = builder.payload;
        this.expectedOutput = builder.expectedOutput;
        this.constraints = builder.constraints;
        this.priority = builder.priority;
        this.status = builder.status;
        this.authorityWeight = builder.authorityWeight;
        this.requiresApproval = builder.requiresApproval;
        this.approvalState = builder.approvalState;
        this.callbackUrl = builder.callbackUrl;
        this.callbackSecret = builder.callbackSecret;
        this.retries = builder.retries;
        this.latencyMs = builder.latencyMs;
        this.errorCode = builder.errorCode;
        this.errorMessage = builder.errorMessage;
        this.createdAt = builder.createdAt;
        this.updatedAt = builder.updatedAt;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static Builder builder(String from, String to, String action, String intent) {
        return new Builder().from(from).to(to).action(action).intent(intent);
    }

    public String version() { return version; }
    public String messageId() { return messageId; }
    public String correlationId() { return correlationId; }
    public String traceId() { return traceId; }
    public String parentTaskId() { return parentTaskId; }
    public String from() { return from; }
    public String to() { return to; }
    public String fromRole() { return fromRole; }
    public String toRole() { return toRole; }
    public String toHost() { return toHost; }
    public String toBaseUrl() { return toBaseUrl; }
    public String routeScope() { return routeScope; }
    public String action() { return action; }
    public String intent() { return intent; }
    public Map<String, Object> payload() { return payload; }
    public String expectedOutput() { return expectedOutput; }
    public List<String> constraints() { return constraints; }
    public String priority() { return priority; }
    public String status() { return status; }
    public Integer authorityWeight() { return authorityWeight; }
    public Boolean requiresApproval() { return requiresApproval; }
    public String approvalState() { return approvalState; }
    public String callbackUrl() { return callbackUrl; }
    public String callbackSecret() { return callbackSecret; }
    public Integer retries() { return retries; }
    public Integer latencyMs() { return latencyMs; }
    public String errorCode() { return errorCode; }
    public String errorMessage() { return errorMessage; }
    public String createdAt() { return createdAt; }
    public String updatedAt() { return updatedAt; }

    public static class Builder {
        private String version = "1.0";
        private String messageId;
        private String correlationId;
        private String traceId;
        private String parentTaskId;
        private String from;
        private String to;
        private String fromRole;
        private String toRole;
        private String toHost;
        private String toBaseUrl;
        private String routeScope = "local";
        private String action;
        private String intent;
        private Map<String, Object> payload;
        private String expectedOutput;
        private List<String> constraints;
        private String priority = "normal";
        private String status = "Pending";
        private Integer authorityWeight = 50;
        private Boolean requiresApproval = false;
        private String approvalState = "not_required";
        private String callbackUrl;
        private String callbackSecret;
        private Integer retries = 0;
        private Integer latencyMs;
        private String errorCode;
        private String errorMessage;
        private String createdAt;
        private String updatedAt;

        public Builder version(String version) { this.version = version; return this; }
        public Builder messageId(String messageId) { this.messageId = messageId; return this; }
        public Builder correlationId(String correlationId) { this.correlationId = correlationId; return this; }
        public Builder traceId(String traceId) { this.traceId = traceId; return this; }
        public Builder parentTaskId(String parentTaskId) { this.parentTaskId = parentTaskId; return this; }
        public Builder from(String from) { this.from = from; return this; }
        public Builder to(String to) { this.to = to; return this; }
        public Builder fromRole(String fromRole) { this.fromRole = fromRole; return this; }
        public Builder toRole(String toRole) { this.toRole = toRole; return this; }
        public Builder toHost(String toHost) { this.toHost = toHost; return this; }
        public Builder toBaseUrl(String toBaseUrl) { this.toBaseUrl = toBaseUrl; return this; }
        public Builder routeScope(String routeScope) { this.routeScope = routeScope; return this; }
        public Builder action(String action) { this.action = action; return this; }
        public Builder intent(String intent) { this.intent = intent; return this; }
        public Builder payload(Map<String, Object> payload) { this.payload = payload; return this; }
        public Builder expectedOutput(String expectedOutput) { this.expectedOutput = expectedOutput; return this; }
        public Builder constraints(List<String> constraints) { this.constraints = constraints; return this; }
        public Builder priority(String priority) { this.priority = priority; return this; }
        public Builder status(String status) { this.status = status; return this; }
        public Builder authorityWeight(Integer authorityWeight) { this.authorityWeight = authorityWeight; return this; }
        public Builder requiresApproval(Boolean requiresApproval) { this.requiresApproval = requiresApproval; return this; }
        public Builder approvalState(String approvalState) { this.approvalState = approvalState; return this; }
        public Builder callbackUrl(String callbackUrl) { this.callbackUrl = callbackUrl; return this; }
        public Builder callbackSecret(String callbackSecret) { this.callbackSecret = callbackSecret; return this; }
        public Builder retries(Integer retries) { this.retries = retries; return this; }
        public Builder latencyMs(Integer latencyMs) { this.latencyMs = latencyMs; return this; }
        public Builder errorCode(String errorCode) { this.errorCode = errorCode; return this; }
        public Builder errorMessage(String errorMessage) { this.errorMessage = errorMessage; return this; }
        public Builder createdAt(String createdAt) { this.createdAt = createdAt; return this; }
        public Builder updatedAt(String updatedAt) { this.updatedAt = updatedAt; return this; }

        public AIPMessage build() {
            if (messageId == null) {
                messageId = java.util.UUID.randomUUID().toString();
            }
            if (payload == null) {
                payload = java.util.Collections.emptyMap();
            }
            if (constraints == null) {
                constraints = java.util.Collections.emptyList();
            }
            return new AIPMessage(this);
        }
    }
}
