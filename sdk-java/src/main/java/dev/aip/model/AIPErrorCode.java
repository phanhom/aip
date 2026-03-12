package dev.aip.model;

/**
 * Standard AIP error code registry (aip/ namespace).
 *
 * <p>Use these constants instead of raw strings for type safety and discoverability.
 * Custom error codes should use the {@code x-<org>/<category>/<error>} prefix.
 */
public final class AIPErrorCode {
    private AIPErrorCode() {}

    // Protocol errors
    public static final String INVALID_VERSION = "aip/protocol/invalid_version";
    public static final String UNSUPPORTED_VERSION = "aip/protocol/unsupported_version";
    public static final String INVALID_MESSAGE = "aip/protocol/invalid_message";
    public static final String ROUTING_FAILED = "aip/protocol/routing_failed";
    public static final String AGENT_NOT_FOUND = "aip/protocol/agent_not_found";
    public static final String AGENT_UNAVAILABLE = "aip/protocol/agent_unavailable";
    public static final String IDEMPOTENCY_CONFLICT = "aip/protocol/idempotency_conflict";
    public static final String IDEMPOTENCY_CONCURRENT = "aip/protocol/idempotency_concurrent";

    // Execution errors
    public static final String UNKNOWN_ACTION = "aip/execution/unknown_action";
    public static final String INVALID_PAYLOAD = "aip/execution/invalid_payload";
    public static final String TASK_FAILED = "aip/execution/task_failed";
    public static final String TASK_TIMEOUT = "aip/execution/task_timeout";
    public static final String TASK_NOT_FOUND = "aip/execution/task_not_found";
    public static final String TASK_NOT_CANCELABLE = "aip/execution/task_not_cancelable";
    public static final String CAPACITY_EXCEEDED = "aip/execution/capacity_exceeded";
    public static final String INPUT_REQUIRED = "aip/execution/input_required";

    // Governance errors
    public static final String AUTHORITY_INSUFFICIENT = "aip/governance/authority_insufficient";
    public static final String APPROVAL_REQUIRED = "aip/governance/approval_required";
    public static final String APPROVAL_REJECTED = "aip/governance/approval_rejected";
    public static final String CONSTRAINT_VIOLATED = "aip/governance/constraint_violated";
    public static final String POLICY_DENIED = "aip/governance/policy_denied";

    // Auth errors
    public static final String UNAUTHENTICATED = "aip/auth/unauthenticated";
    public static final String UNAUTHORIZED = "aip/auth/unauthorized";
    public static final String TOKEN_EXPIRED = "aip/auth/token_expired";
    public static final String INVALID_TOKEN = "aip/auth/invalid_token";

    // Rate limiting errors
    public static final String RATE_LIMIT_EXCEEDED = "aip/ratelimit/exceeded";
    public static final String QUOTA_EXHAUSTED = "aip/ratelimit/quota_exhausted";
}
