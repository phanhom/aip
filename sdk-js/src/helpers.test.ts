import { describe, it, expect } from "vitest";
import { buildMessage } from "./helpers.js";

describe("buildMessage", () => {
  it("builds message with required fields and generated message_id", () => {
    const msg = buildMessage({
      from: "user",
      to: "agent",
      action: "assign_task",
      intent: "Do something",
    });
    expect(msg.from).toBe("user");
    expect(msg.to).toBe("agent");
    expect(msg.action).toBe("assign_task");
    expect(msg.intent).toBe("Do something");
    expect(msg.version).toBe("1.0");
    expect(msg.message_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    );
  });

  it("includes payload when provided", () => {
    const msg = buildMessage({
      from: "user",
      to: "agent",
      action: "assign_task",
      intent: "Task",
      payload: { key: "value" },
    });
    expect(msg.payload).toEqual({ key: "value" });
  });
});
