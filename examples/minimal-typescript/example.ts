/**
 * AIP in 5 minutes — TypeScript example.
 *
 * This shows the AIP wire format in TypeScript. No SDK needed —
 * AIP is just JSON over HTTP, so any language can implement it.
 *
 *   npx tsx example.ts
 */

interface AIPMessage {
  version: string;
  message_id: string;
  from: string;
  to: string;
  from_role?: string;
  to_role?: string;
  to_base_url?: string;
  route_scope?: "local" | "remote";
  action: string;
  intent: string;
  payload?: Record<string, unknown>;
  expected_output?: string;
  constraints?: string[];
  priority?: "low" | "normal" | "high" | "urgent";
  status?: "Pending" | "InProgress" | "Completed" | "Failed";
  authority_weight?: number;
  requires_approval?: boolean;
  approval_state?: "not_required" | "waiting_human" | "approved" | "rejected";
  trace_id?: string;
  correlation_id?: string;
  created_at?: string;
  updated_at?: string;
}

interface AIPAck {
  ok: boolean;
  message_id: string;
  to: string;
  status: "received" | "queued" | "rejected";
  correlation_id?: string;
}

// ── Build a message ─────────────────────────────────────────────────

const message: AIPMessage = {
  version: "1.0",
  message_id: crypto.randomUUID(),
  from: "user",
  to: "agent-backend",
  from_role: "user",
  action: "assign_task",
  intent: "Design the order service REST API",
  payload: {
    instruction: "Define REST endpoints, error codes, and schemas",
    deliverables: ["openapi", "risk_report"],
  },
  priority: "high",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

console.log("AIP Message:");
console.log(JSON.stringify(message, null, 2));

// ── Send to an AIP agent ────────────────────────────────────────────

async function sendAIP(baseUrl: string, msg: AIPMessage, apiVersion = "v1"): Promise<AIPAck> {
  const res = await fetch(`${baseUrl}/${apiVersion}/aip`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(msg),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json() as Promise<AIPAck>;
}

// Uncomment to send:
// const ack = await sendAIP("http://localhost:8000", message);
// console.log("Ack:", ack);
