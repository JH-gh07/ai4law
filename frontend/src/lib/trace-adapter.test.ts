import { describe, expect, it } from "vitest";
import { adaptEvents } from "./trace-adapter";
import type { RunEvent } from "./useTaskEvents";


function toolEvent(
  eventId: string,
  seq: number,
  eventType: "tool_start" | "tool_result",
  correlationId: string,
  tool: string,
): RunEvent {
  return {
    event_id: eventId,
    task_id: "task-1",
    seq,
    event_type: eventType,
    correlation_id: correlationId,
    timestamp: `2026-08-06T00:00:0${seq}Z`,
    summary: `${tool} ${eventType}`,
    detail: { tool },
    level: "audit",
  };
}


describe("adaptEvents", () => {
  it("pairs interleaved tool events by correlation id", () => {
    const nodes = adaptEvents(
      [
        toolEvent("start-a", 1, "tool_start", "call-a", "tool-a"),
        toolEvent("start-b", 2, "tool_start", "call-b", "tool-b"),
        toolEvent("result-a", 3, "tool_result", "call-a", "tool-a"),
        toolEvent("result-b", 4, "tool_result", "call-b", "tool-b"),
      ],
      "en",
    );

    expect(nodes).toHaveLength(2);
    expect(nodes[0].rawEventIds).toEqual(["start-a", "result-a"]);
    expect(nodes[1].rawEventIds).toEqual(["start-b", "result-b"]);
  });
});
