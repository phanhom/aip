/**
 * Agent Interaction Protocol (AIP) — Helper utilities.
 */

import type { AIPMessage } from "./types.js";

export interface BuildMessageParams {
  from: string;
  to: string;
  action: string;
  intent: string;
  payload?: Record<string, unknown>;
  [key: string]: unknown;
}

/**
 * Build an AIPMessage from common parameters.
 * Generates message_id via crypto.randomUUID().
 */
export function buildMessage(params: BuildMessageParams): AIPMessage {
  const { from, to, action, intent, payload, ...rest } = params;

  const message: AIPMessage = {
    version: "1.0",
    message_id: crypto.randomUUID(),
    from,
    to,
    action,
    intent,
    ...rest,
  };

  if (payload !== undefined) {
    message.payload = payload;
  }

  return message;
}
