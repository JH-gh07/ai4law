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

  it("maps control gate raw events to a review node", () => {
    const nodes = adaptEvents(
      [{
        event_id: "control-1",
        task_id: "task-1",
        seq: 5,
        event_type: "warning",
        correlation_id: null,
        timestamp: "2026-08-16T00:00:05Z",
        summary: "引用有效性门需要人工复核",
        detail: {
          raw_name: "control.citation_validity",
          gate: "CITATION_VALIDITY",
          outcome: "ESCALATE",
        },
        level: "audit",
      }],
      "zh",
    );

    expect(nodes).toHaveLength(1);
    expect(nodes[0]).toMatchObject({
      stage: "Review",
      action: "执行控制门判定 · CITATION_VALIDITY · ESCALATE",
      badge: "CONTROL",
      status: "error",
    });
  });
});
