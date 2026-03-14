package aip

import (
	"crypto/rand"
	"fmt"
	"time"
)

// Standard action constants.
const (
	ActionAssignTask            = "assign_task"
	ActionSubmitReport          = "submit_report"
	ActionRequestContext        = "request_context"
	ActionRequestArtifactReview = "request_artifact_review"
	ActionRequestApproval       = "request_approval"
	ActionPublishStatus         = "publish_status"
	ActionHandoff               = "handoff"
	ActionEscalate              = "escalate"
	ActionToolResult            = "tool_result"
	ActionSyncSkillRegistry     = "sync_skill_registry"
	ActionUserInstruction       = "user_instruction"
)

// Priority constants.
const (
	PriorityLow    = "low"
	PriorityNormal = "normal"
	PriorityHigh   = "high"
	PriorityUrgent = "urgent"
)

// Message status constants.
const (
	StatusPending   = "Pending"
	StatusInProgress = "InProgress"
	StatusCompleted = "Completed"
	StatusFailed    = "Failed"
)

// Approval state constants.
const (
	ApprovalNotRequired  = "not_required"
	ApprovalWaitingHuman = "waiting_human"
	ApprovalApproved     = "approved"
	ApprovalRejected     = "rejected"
)

// Route scope constants.
const (
	RouteScopeLocal  = "local"
	RouteScopeRemote = "remote"
)

// Status scope constants.
const (
	StatusScopeSelf    = "self"
	StatusScopeSubtree = "subtree"
	StatusScopeColony  = "colony"
)

// Task state constants.
const (
	TaskStateSubmitted      = "submitted"
	TaskStateWorking        = "working"
	TaskStateInputRequired  = "input-required"
	TaskStateCompleted      = "completed"
	TaskStateFailed         = "failed"
	TaskStateCanceled       = "canceled"
)

// Ack status constants.
const (
	AckStatusReceived = "received"
	AckStatusQueued   = "queued"
	AckStatusRejected = "rejected"
)

// Standard error codes (aip/ namespace).
const (
	ErrInvalidVersion       = "aip/protocol/invalid_version"
	ErrUnsupportedVersion   = "aip/protocol/unsupported_version"
	ErrInvalidMessage       = "aip/protocol/invalid_message"
	ErrRoutingFailed        = "aip/protocol/routing_failed"
	ErrAgentNotFound        = "aip/protocol/agent_not_found"
	ErrAgentUnavailable     = "aip/protocol/agent_unavailable"
	ErrIdempotencyConflict  = "aip/protocol/idempotency_conflict"
	ErrIdempotencyConcurrent = "aip/protocol/idempotency_concurrent"

	ErrUnknownAction     = "aip/execution/unknown_action"
	ErrInvalidPayload    = "aip/execution/invalid_payload"
	ErrTaskFailed        = "aip/execution/task_failed"
	ErrTaskTimeout       = "aip/execution/task_timeout"
	ErrTaskNotFound      = "aip/execution/task_not_found"
	ErrTaskNotCancelable = "aip/execution/task_not_cancelable"
	ErrCapacityExceeded  = "aip/execution/capacity_exceeded"
	ErrInputRequired     = "aip/execution/input_required"

	ErrAuthorityInsufficient = "aip/governance/authority_insufficient"
	ErrApprovalRequired      = "aip/governance/approval_required"
	ErrApprovalRejected      = "aip/governance/approval_rejected"
	ErrConstraintViolated    = "aip/governance/constraint_violated"
	ErrPolicyDenied          = "aip/governance/policy_denied"

	ErrUnauthenticated = "aip/auth/unauthenticated"
	ErrUnauthorized    = "aip/auth/unauthorized"
	ErrTokenExpired    = "aip/auth/token_expired"
	ErrInvalidToken    = "aip/auth/invalid_token"

	ErrRateLimitExceeded = "aip/ratelimit/exceeded"
	ErrQuotaExhausted    = "aip/ratelimit/quota_exhausted"
)

// Default protocol version.
const DefaultVersion = "1.0"

// AIPMessage is the Agent Interaction Protocol message envelope.
type AIPMessage struct {
	Version          string                 `json:"version"`
	MessageID        string                 `json:"message_id"`
	CorrelationID    string                 `json:"correlation_id,omitempty"`
	TraceID          string                 `json:"trace_id,omitempty"`
	ParentTaskID     string                 `json:"parent_task_id,omitempty"`
	From             string                 `json:"from"`
	To               string                 `json:"to"`
	FromRole         string                 `json:"from_role,omitempty"`
	ToRole           string                 `json:"to_role,omitempty"`
	ToHost           string                 `json:"to_host,omitempty"`
	ToBaseURL        string                 `json:"to_base_url,omitempty"`
	RouteScope       string                 `json:"route_scope,omitempty"`
	Action           string                 `json:"action"`
	Intent           string                 `json:"intent"`
	Payload          map[string]interface{} `json:"payload,omitempty"`
	ExpectedOutput   string                 `json:"expected_output,omitempty"`
	Constraints      []string               `json:"constraints,omitempty"`
	Priority         string                 `json:"priority,omitempty"`
	Status           string                 `json:"status,omitempty"`
	AuthorityWeight  int                    `json:"authority_weight,omitempty"`
	RequiresApproval bool                   `json:"requires_approval,omitempty"`
	ApprovalState    string                 `json:"approval_state,omitempty"`
	CallbackURL      string                 `json:"callback_url,omitempty"`
	CallbackSecret   string                 `json:"callback_secret,omitempty"`
	Retries          int                    `json:"retries,omitempty"`
	LatencyMs        *int                   `json:"latency_ms,omitempty"`
	ErrorCode        string                 `json:"error_code,omitempty"`
	ErrorMessage     string                 `json:"error_message,omitempty"`
	CreatedAt        string                 `json:"created_at,omitempty"`
	UpdatedAt        string                 `json:"updated_at,omitempty"`
}

// AIPAck is the acknowledgment returned by POST /aip handlers.
type AIPAck struct {
	OK            bool   `json:"ok"`
	MessageID     string `json:"message_id"`
	To            string `json:"to"`
	Status        string `json:"status"`
	TaskID        string `json:"task_id,omitempty"`
	ErrorCode     string `json:"error_code,omitempty"`
	ErrorMessage  string `json:"error_message,omitempty"`
	CorrelationID string `json:"correlation_id,omitempty"`
}

// RateLimitInfo holds rate limiting and quota information for client self-regulation.
type RateLimitInfo struct {
	MaxRequestsPerMinute *int    `json:"max_requests_per_minute,omitempty"`
	MaxRequestsPerDay    *int    `json:"max_requests_per_day,omitempty"`
	MaxConcurrentTasks   *int    `json:"max_concurrent_tasks,omitempty"`
	RemainingRequests    *int    `json:"remaining_requests,omitempty"`
	RemainingTasks       *int    `json:"remaining_tasks,omitempty"`
	ResetAt              *string `json:"reset_at,omitempty"`
}

// AIPTask represents a task in the AIP lifecycle.
type AIPTask struct {
	TaskID       string                 `json:"task_id"`
	MessageID    string                 `json:"message_id"`
	State        string                 `json:"state"`
	From         string                 `json:"from"`
	To           string                 `json:"to"`
	Action       string                 `json:"action"`
	Intent       string                 `json:"intent"`
	Progress     *float64               `json:"progress,omitempty"`
	Artifacts    []Artifact             `json:"artifacts,omitempty"`
	History      []AIPMessage           `json:"history,omitempty"`
	ErrorCode    string                 `json:"error_code,omitempty"`
	ErrorMessage string                 `json:"error_message,omitempty"`
	TraceID      string                 `json:"trace_id,omitempty"`
	CorrelationID string                `json:"correlation_id,omitempty"`
	ParentTaskID string                 `json:"parent_task_id,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
	CreatedAt    string                 `json:"created_at"`
	UpdatedAt    string                 `json:"updated_at"`
}

// Artifact represents a file, document, or structured data produced by a task.
type Artifact struct {
	ArtifactID   string                 `json:"artifact_id"`
	Name         string                 `json:"name"`
	Description  string                 `json:"description,omitempty"`
	MimeType     string                 `json:"mime_type"`
	URI          string                 `json:"uri,omitempty"`
	InlineData   string                 `json:"inline_data,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}

// Provider identifies the organization or individual operating an agent.
type Provider struct {
	Name string `json:"name"`
	URL  string `json:"url,omitempty"`
}

// Presentation holds human-facing display metadata for dashboards, agent cards, and marketplace UIs.
type Presentation struct {
	DisplayName      string   `json:"display_name"`
	Tagline          string   `json:"tagline,omitempty"`
	Description      string   `json:"description,omitempty"`
	IconURL          string   `json:"icon_url,omitempty"`
	Color            string   `json:"color,omitempty"`
	Locale           string   `json:"locale,omitempty"`
	Categories       []string `json:"categories,omitempty"`
	HomepageURL      string   `json:"homepage_url,omitempty"`
	PrivacyPolicyURL string   `json:"privacy_policy_url,omitempty"`
	TosURL           string   `json:"tos_url,omitempty"`
	Provider         *Provider `json:"provider,omitempty"`
}

// AgentAssignment represents the platform-assigned identity and constraints for an agent.
// It is the "job description" the platform gives, separate from the agent's native profile.
type AgentAssignment struct {
	AssignedRole  string                 `json:"assigned_role,omitempty"`
	Team          string                 `json:"team,omitempty"`
	Scope         string                 `json:"scope,omitempty"`
	GrantedTools  []string               `json:"granted_tools,omitempty"`
	GrantedSkills []Skill                `json:"granted_skills,omitempty"`
	Constraints   []string               `json:"constraints,omitempty"`
	Supervisor    string                 `json:"supervisor,omitempty"`
	Priority      string                 `json:"priority,omitempty"`
	AssignedAt    string                 `json:"assigned_at,omitempty"`
	Metadata      map[string]interface{} `json:"metadata,omitempty"`
}

// AuthenticationInfo describes authentication schemes supported by an agent.
type AuthenticationInfo struct {
	Schemes []string               `json:"schemes,omitempty"`
	OAuth2  map[string]interface{} `json:"oauth2,omitempty"`
}

// Skill describes an agent capability with input/output schemas.
type Skill struct {
	ID           string                 `json:"id"`
	Name         string                 `json:"name"`
	Description  string                 `json:"description"`
	Tags         []string               `json:"tags,omitempty"`
	InputModes   []string               `json:"input_modes,omitempty"`
	OutputModes  []string               `json:"output_modes,omitempty"`
	InputSchema  map[string]interface{} `json:"input_schema,omitempty"`
	OutputSchema map[string]interface{} `json:"output_schema,omitempty"`
	Examples     []map[string]interface{} `json:"examples,omitempty"`
}

// StatusEndpoints holds discoverable endpoint URLs for an agent.
type StatusEndpoints struct {
	AIP    string `json:"aip,omitempty"`
	Status string `json:"status,omitempty"`
}

// AgentStatus is the status document for a single agent.
type AgentStatus struct {
	AgentID            string                 `json:"agent_id"`
	Role               string                 `json:"role"`
	Namespace          string                 `json:"namespace,omitempty"`
	Presentation       *Presentation          `json:"presentation,omitempty"`
	Superior           string                 `json:"superior,omitempty"`
	AuthorityWeight    *int                   `json:"authority_weight,omitempty"`
	Lifecycle          string                 `json:"lifecycle,omitempty"`
	Port               *int                   `json:"port,omitempty"`
	OK                 bool                   `json:"ok,omitempty"`
	BaseURL            string                 `json:"base_url,omitempty"`
	Endpoints          *StatusEndpoints       `json:"endpoints,omitempty"`
	Capabilities       []string               `json:"capabilities,omitempty"`
	Skills             []Skill                `json:"skills,omitempty"`
	SupportedVersions  []string               `json:"supported_versions,omitempty"`
	Authentication     *AuthenticationInfo    `json:"authentication,omitempty"`
	RateLimits         *RateLimitInfo         `json:"rate_limits,omitempty"`
	PendingTasks       int                    `json:"pending_tasks,omitempty"`
	RecentErrors       int                    `json:"recent_errors,omitempty"`
	WaitingForApproval bool                   `json:"waiting_for_approval,omitempty"`
	LastMessageAt      string                 `json:"last_message_at,omitempty"`
	LastSeenAt         string                 `json:"last_seen_at,omitempty"`
	Metadata           map[string]interface{} `json:"metadata,omitempty"`
	Assignment         *AgentAssignment       `json:"assignment,omitempty"`
}

// GroupStatus is the aggregated status for a group of agents.
type GroupStatus struct {
	OK          bool                   `json:"ok"`
	Service     string                 `json:"service,omitempty"`
	Namespace   string                 `json:"namespace,omitempty"`
	RootAgentID string                 `json:"root_agent_id,omitempty"`
	Timestamp   string                 `json:"timestamp,omitempty"`
	Agents      []AgentStatus          `json:"agents,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// RecursiveStatusNode is a tree node for hierarchical agent discovery.
type RecursiveStatusNode struct {
	AgentStatus
	Subordinates []RecursiveStatusNode `json:"subordinates,omitempty"`
}

// Trace type constants for observability.
const (
	TraceTypeMessageSent     = "aip.message.sent"
	TraceTypeMessageReceived = "aip.message.received"
	TraceTypeTaskCreated     = "task.created"
	TraceTypeTaskCompleted   = "task.completed"
	TraceTypeTaskFailed      = "task.failed"
	TraceTypeTaskCanceled    = "task.canceled"
	TraceTypeLLMUsage        = "llm.usage"
	TraceTypeToolCall        = "tool.call"
	TraceTypeToolResult      = "tool.result"
	TraceTypeError           = "error"
	TraceTypeLog             = "log"
	TraceTypeReport          = "report"
	TraceTypeConversation    = "conversation"
	TraceTypeApproval        = "approval.requested"
	TraceTypeApprovalGranted = "approval.granted"
	TraceTypeApprovalDenied  = "approval.denied"
	TraceTypeAgentSpawned    = "agent.spawned"
	TraceTypeAgentTerminated = "agent.terminated"
)

// Trace severity constants (OpenTelemetry-aligned).
const (
	TraceSeverityTrace = "TRACE"
	TraceSeverityDebug = "DEBUG"
	TraceSeverityInfo  = "INFO"
	TraceSeverityWarn  = "WARN"
	TraceSeverityError = "ERROR"
	TraceSeverityFatal = "FATAL"
)

// TraceEvent is a single observable event in the AIP system.
type TraceEvent struct {
	EventID       string                 `json:"event_id"`
	TraceID       string                 `json:"trace_id,omitempty"`
	SpanID        string                 `json:"span_id,omitempty"`
	ParentSpanID  string                 `json:"parent_span_id,omitempty"`
	AgentID       string                 `json:"agent_id"`
	TraceType     string                 `json:"trace_type"`
	Severity      string                 `json:"severity,omitempty"`
	Timestamp     string                 `json:"ts"`
	DurationMs    *float64               `json:"duration_ms,omitempty"`
	TaskID        string                 `json:"task_id,omitempty"`
	MessageID     string                 `json:"message_id,omitempty"`
	CorrelationID string                 `json:"correlation_id,omitempty"`
	Payload       map[string]interface{} `json:"payload,omitempty"`
	Tags          map[string]string      `json:"tags,omitempty"`
}

// LLMUsage tracks token and cost data for a single LLM invocation.
type LLMUsage struct {
	Model             string   `json:"model"`
	PromptTokens      int      `json:"prompt_tokens"`
	CompletionTokens  int      `json:"completion_tokens"`
	TotalTokens       int      `json:"total_tokens"`
	EstimatedCostUSD  *float64 `json:"estimated_cost_usd,omitempty"`
	DurationMs        *float64 `json:"duration_ms,omitempty"`
}

// UsageSummary is an aggregated cost/usage report.
type UsageSummary struct {
	Namespace        string                `json:"namespace,omitempty"`
	Since            string                `json:"since,omitempty"`
	Until            string                `json:"until,omitempty"`
	TotalTokens      int                   `json:"total_tokens"`
	TotalCostUSD     float64               `json:"total_cost_usd"`
	TotalInvocations int                   `json:"total_invocations"`
	ByModel          []ModelUsageBreakdown `json:"by_model,omitempty"`
	ByAgent          []AgentUsageBreakdown `json:"by_agent,omitempty"`
}

// ModelUsageBreakdown is per-model cost data within a UsageSummary.
type ModelUsageBreakdown struct {
	Model            string  `json:"model"`
	PromptTokens     int     `json:"prompt_tokens"`
	CompletionTokens int     `json:"completion_tokens"`
	TotalTokens      int     `json:"total_tokens"`
	TotalCostUSD     float64 `json:"total_cost_usd"`
	Invocations      int     `json:"invocations"`
}

// AgentUsageBreakdown is per-agent cost data within a UsageSummary.
type AgentUsageBreakdown struct {
	AgentID      string  `json:"agent_id"`
	TotalTokens  int     `json:"total_tokens"`
	TotalCostUSD float64 `json:"total_cost_usd"`
	Invocations  int     `json:"invocations"`
}

// BuildMessage creates an AIPMessage with required fields and sensible defaults.
// Generates a new message_id (UUID) and sets created_at/updated_at to current UTC time.
func BuildMessage(from, to, action, intent string, opts ...MessageOption) (*AIPMessage, error) {
	now := time.Now().UTC().Format(time.RFC3339)
	msg := &AIPMessage{
		Version:         DefaultVersion,
		MessageID:       newUUID(),
		From:            from,
		To:              to,
		Action:          action,
		Intent:          intent,
		RouteScope:      RouteScopeLocal,
		Priority:        PriorityNormal,
		Status:          StatusPending,
		AuthorityWeight: 50,
		ApprovalState:   ApprovalNotRequired,
		CreatedAt:       now,
		UpdatedAt:       now,
	}
	for _, opt := range opts {
		opt(msg)
	}
	return msg, nil
}

// MessageOption is a functional option for customizing AIPMessage.
type MessageOption func(*AIPMessage)

// WithPayload sets the message payload.
func WithPayload(p map[string]interface{}) MessageOption {
	return func(m *AIPMessage) { m.Payload = p }
}

// WithCorrelationID sets the correlation ID.
func WithCorrelationID(id string) MessageOption {
	return func(m *AIPMessage) { m.CorrelationID = id }
}

// WithParentTaskID sets the parent task ID.
func WithParentTaskID(id string) MessageOption {
	return func(m *AIPMessage) { m.ParentTaskID = id }
}

// WithPriority sets the message priority.
func WithPriority(p string) MessageOption {
	return func(m *AIPMessage) { m.Priority = p }
}

// WithExpectedOutput sets the expected output description.
func WithExpectedOutput(s string) MessageOption {
	return func(m *AIPMessage) { m.ExpectedOutput = s }
}

// WithConstraints sets the constraints list.
func WithConstraints(c []string) MessageOption {
	return func(m *AIPMessage) { m.Constraints = c }
}

// WithCallbackURL sets the webhook callback URL and optional HMAC secret.
func WithCallbackURL(url, secret string) MessageOption {
	return func(m *AIPMessage) {
		m.CallbackURL = url
		m.CallbackSecret = secret
	}
}

// newUUID generates a UUID v4 using crypto/rand (stdlib only).
func newUUID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return fmt.Sprintf("msg-%d", time.Now().UnixNano())
	}
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
