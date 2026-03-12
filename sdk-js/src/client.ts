/**
 * Agent Interaction Protocol (AIP) — HTTP client.
 * Uses native fetch API (Node.js 18+ and browsers).
 */

import type {
  AIPAck,
  AIPMessage,
  AgentStatus,
  AIPTask,
  SSEEvent,
} from "./types.js";

export interface SendOptions {
  /** Idempotency key (UUID v4) for deduplication. */
  idempotencyKey?: string;
}

export interface AIPClientOptions {
  /** API version path segment (default: "v1"). */
  apiVersion?: string;
  /** Additional headers for all requests. */
  headers?: Record<string, string>;
}

export class AIPClient {
  private readonly baseUrl: string;
  private readonly apiVersion: string;
  private readonly headers: Record<string, string>;

  constructor(baseUrl: string, options?: AIPClientOptions) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.apiVersion = options?.apiVersion ?? "v1";
    this.headers = options?.headers ?? {};
  }

  /**
   * Send a message (non-streaming). Uses Accept: application/json.
   */
  async send(message: AIPMessage, options?: SendOptions): Promise<AIPAck> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (options?.idempotencyKey) {
      headers["Idempotency-Key"] = options.idempotencyKey;
    }
    const res = await this.request("POST", "/aip", {
      body: JSON.stringify(message),
      headers,
    });
    return (await res.json()) as AIPAck;
  }

  /**
   * Send a message with SSE streaming. Yields events as they arrive.
   */
  async *sendStream(message: AIPMessage): AsyncGenerator<SSEEvent> {
    const res = await this.request("POST", "/aip", {
      body: JSON.stringify(message),
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
    });

    if (!res.body) {
      throw new Error("Response body is not readable");
    }

    yield* this.parseSSE(res.body);
  }

  /**
   * Get agent status (discovery).
   */
  async getStatus(): Promise<AgentStatus> {
    const res = await this.request("GET", "/status");
    return (await res.json()) as AgentStatus;
  }

  /**
   * Get task by ID.
   */
  async getTask(taskId: string): Promise<AIPTask> {
    const res = await this.request("GET", `/tasks/${encodeURIComponent(taskId)}`);
    return (await res.json()) as AIPTask;
  }

  /**
   * Cancel a task.
   */
  async cancelTask(taskId: string): Promise<AIPTask> {
    const res = await this.request(
      "POST",
      `/tasks/${encodeURIComponent(taskId)}/cancel`
    );
    return (await res.json()) as AIPTask;
  }

  /**
   * Send a follow-up message into an existing task context.
   */
  async sendToTask(taskId: string, message: AIPMessage): Promise<AIPAck> {
    const res = await this.request(
      "POST",
      `/tasks/${encodeURIComponent(taskId)}/send`,
      {
        body: JSON.stringify(message),
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
      }
    );
    return (await res.json()) as AIPAck;
  }

  private async request(
    method: string,
    path: string,
    init?: RequestInit
  ): Promise<Response> {
    const url = `${this.baseUrl}/${this.apiVersion}${path}`;
    const headers = new Headers(this.headers);

    if (init?.headers) {
      const reqHeaders = new Headers(init.headers);
      reqHeaders.forEach((v, k) => headers.set(k, v));
    }

    const res = await fetch(url, {
      ...init,
      method,
      headers,
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`AIP request failed: ${res.status} ${res.statusText}\n${text}`);
    }

    return res;
  }

  private async *parseSSE(
    stream: ReadableStream<Uint8Array>
  ): AsyncGenerator<SSEEvent> {
    const reader = stream.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let currentEvent = "";
    let currentData = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            currentData = line.slice(6);
          } else if (line === "") {
            if (currentData !== "" || currentEvent !== "") {
              yield { event: currentEvent || "message", data: currentData };
              currentEvent = "";
              currentData = "";
            }
          }
        }
      }

      if (currentData !== "" || currentEvent !== "") {
        yield { event: currentEvent || "message", data: currentData };
      }
    } finally {
      reader.releaseLock();
    }
  }
}
