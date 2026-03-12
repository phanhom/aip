package aip

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

const (
	defaultAPIVersion = "v1"
	defaultTimeout    = 30 * time.Second
)

// ClientOption configures the AIP client.
type ClientOption func(*Client)

// WithAPIVersion sets the API version path segment (default: "v1").
func WithAPIVersion(v string) ClientOption {
	return func(c *Client) { c.APIVersion = v }
}

// WithHTTPClient sets a custom *http.Client.
func WithHTTPClient(hc *http.Client) ClientOption {
	return func(c *Client) { c.HTTPClient = hc }
}

// WithTimeout sets the client timeout.
func WithTimeout(d time.Duration) ClientOption {
	return func(c *Client) { c.Timeout = d }
}

// Client is the AIP HTTP client.
type Client struct {
	BaseURL    string
	APIVersion string
	HTTPClient *http.Client
	Timeout    time.Duration
}

// NewClient creates a new AIP client. baseURL should not include a trailing slash.
func NewClient(baseURL string, opts ...ClientOption) *Client {
	c := &Client{
		BaseURL:    strings.TrimSuffix(baseURL, "/"),
		APIVersion: defaultAPIVersion,
		HTTPClient: &http.Client{Timeout: defaultTimeout},
		Timeout:    defaultTimeout,
	}
	for _, opt := range opts {
		opt(c)
	}
	if c.HTTPClient.Timeout == 0 {
		c.HTTPClient.Timeout = c.Timeout
	}
	return c
}

// SendOptions configures per-request behavior.
type SendOptions struct {
	IdempotencyKey string
}

// Send sends a message via POST /v1/aip and returns the acknowledgment (non-streaming, JSON).
func (c *Client) Send(ctx context.Context, msg *AIPMessage, opts ...SendOptions) (*AIPAck, error) {
	body, err := json.Marshal(msg)
	if err != nil {
		return nil, fmt.Errorf("marshal message: %w", err)
	}
	req, err := c.newRequest(ctx, http.MethodPost, "/aip", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	if len(opts) > 0 && opts[0].IdempotencyKey != "" {
		req.Header.Set("Idempotency-Key", opts[0].IdempotencyKey)
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("unexpected status %d: %s", resp.StatusCode, string(b))
	}

	var ack AIPAck
	if err := json.NewDecoder(resp.Body).Decode(&ack); err != nil {
		return nil, fmt.Errorf("decode ack: %w", err)
	}
	return &ack, nil
}

// SendStream sends a message via POST /v1/aip with Accept: text/event-stream and returns an EventStream.
func (c *Client) SendStream(ctx context.Context, msg *AIPMessage) (*EventStream, error) {
	body, err := json.Marshal(msg)
	if err != nil {
		return nil, fmt.Errorf("marshal message: %w", err)
	}
	req, err := c.newRequest(ctx, http.MethodPost, "/aip", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "text/event-stream")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, fmt.Errorf("unexpected status %d: %s", resp.StatusCode, string(b))
	}

	if !strings.HasPrefix(resp.Header.Get("Content-Type"), "text/event-stream") {
		resp.Body.Close()
		return nil, fmt.Errorf("expected text/event-stream, got %s", resp.Header.Get("Content-Type"))
	}

	return newEventStream(resp.Body), nil
}

// GetStatus fetches agent status from GET /v1/status.
func (c *Client) GetStatus(ctx context.Context) (*AgentStatus, error) {
	req, err := c.newRequest(ctx, http.MethodGet, "/status", nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("unexpected status %d: %s", resp.StatusCode, string(b))
	}

	var status AgentStatus
	if err := json.NewDecoder(resp.Body).Decode(&status); err != nil {
		return nil, fmt.Errorf("decode status: %w", err)
	}
	return &status, nil
}

// GetTask fetches a task from GET /v1/tasks/{id}.
func (c *Client) GetTask(ctx context.Context, taskID string) (*AIPTask, error) {
	path := "/tasks/" + url.PathEscape(taskID)
	req, err := c.newRequest(ctx, http.MethodGet, path, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("unexpected status %d: %s", resp.StatusCode, string(b))
	}

	var task AIPTask
	if err := json.NewDecoder(resp.Body).Decode(&task); err != nil {
		return nil, fmt.Errorf("decode task: %w", err)
	}
	return &task, nil
}

// CancelTask cancels a task via POST /v1/tasks/{id}/cancel.
func (c *Client) CancelTask(ctx context.Context, taskID string) (*AIPTask, error) {
	path := "/tasks/" + url.PathEscape(taskID) + "/cancel"
	req, err := c.newRequest(ctx, http.MethodPost, path, nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("unexpected status %d: %s", resp.StatusCode, string(b))
	}

	var task AIPTask
	if err := json.NewDecoder(resp.Body).Decode(&task); err != nil {
		return nil, fmt.Errorf("decode task: %w", err)
	}
	return &task, nil
}

// SendToTask sends a follow-up message into an existing task via POST /v1/tasks/{id}/send.
func (c *Client) SendToTask(ctx context.Context, taskID string, msg *AIPMessage) (*AIPAck, error) {
	body, err := json.Marshal(msg)
	if err != nil {
		return nil, fmt.Errorf("marshal message: %w", err)
	}
	path := "/tasks/" + url.PathEscape(taskID) + "/send"
	req, err := c.newRequest(ctx, http.MethodPost, path, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("unexpected status %d: %s", resp.StatusCode, string(b))
	}

	var ack AIPAck
	if err := json.NewDecoder(resp.Body).Decode(&ack); err != nil {
		return nil, fmt.Errorf("decode ack: %w", err)
	}
	return &ack, nil
}

func (c *Client) newRequest(ctx context.Context, method, path string, body io.Reader) (*http.Request, error) {
	u := c.BaseURL + "/" + c.APIVersion + path
	req, err := http.NewRequestWithContext(ctx, method, u, body)
	if err != nil {
		return nil, err
	}
	return req, nil
}

// SSEEvent represents a single Server-Sent Event.
type SSEEvent struct {
	Event string
	Data  string
}

// EventStream reads SSE events from a response body.
type EventStream struct {
	r     io.ReadCloser
	scan  *bufio.Scanner
	event string
	data  strings.Builder
}

func newEventStream(r io.ReadCloser) *EventStream {
	return &EventStream{
		r:    r,
		scan: bufio.NewScanner(r),
	}
}

// Next returns the next SSE event, or io.EOF when the stream ends.
func (es *EventStream) Next() (*SSEEvent, error) {
	es.event = ""
	es.data.Reset()

	for es.scan.Scan() {
		line := es.scan.Text()
		if line == "" {
			if es.event != "" || es.data.Len() > 0 {
				return &SSEEvent{Event: es.event, Data: strings.TrimSpace(es.data.String())}, nil
			}
			continue
		}
		if strings.HasPrefix(line, "event: ") {
			es.event = strings.TrimSpace(line[7:])
			continue
		}
		if strings.HasPrefix(line, "data: ") {
			if es.data.Len() > 0 {
				es.data.WriteByte('\n')
			}
			es.data.WriteString(line[6:])
			continue
		}
	}

	if err := es.scan.Err(); err != nil {
		return nil, err
	}
	if es.event != "" || es.data.Len() > 0 {
		return &SSEEvent{Event: es.event, Data: strings.TrimSpace(es.data.String())}, nil
	}
	return nil, io.EOF
}

// Close closes the underlying response body.
func (es *EventStream) Close() error {
	if es.r != nil {
		return es.r.Close()
	}
	return nil
}
