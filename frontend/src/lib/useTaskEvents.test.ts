import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchTaskEvents } from "../api/events";
import { mergeRunEvents, type RunEvent, useTaskEvents } from "./useTaskEvents";

vi.mock("../api/events", () => ({
  fetchTaskEvents: vi.fn(),
  getTaskEventStreamUrl: (taskId: string) => `/events/${taskId}`,
}));

class FakeEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;

  readyState = FakeEventSource.CONNECTING;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  onopen: (() => void) | null = null;

  close() {
    this.readyState = FakeEventSource.CLOSED;
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("EventSource", FakeEventSource);
  vi.mocked(fetchTaskEvents).mockResolvedValue({ events: [], latest_seq: 0 });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

function event(eventId: string, seq: number, summary: string): RunEvent {
  return {
    event_id: eventId,
    task_id: "task-1",
    seq,
    event_type: "status",
    timestamp: "2026-07-21T00:00:00Z",
    summary,
    level: "audit",
  };
}

describe("mergeRunEvents", () => {
  it("drops replayed events with the same event id while preserving arrival order", () => {
    const first = event("event-1", 1, "first");
    const second = event("event-2", 2, "second");

    expect(mergeRunEvents([first], [first, second])).toEqual([first, second]);
  });

  it("falls back to task and sequence identity for legacy events without an event id", () => {
    const first = event("", 1, "first");
    const replay = event("", 1, "replayed first");

    expect(mergeRunEvents([first], [replay])).toEqual([first]);
  });
});

describe("useTaskEvents", () => {
  it("shares one fallback polling loop across multiple subscribers", async () => {
    const first = renderHook(() => useTaskEvents("shared-task"));
    const second = renderHook(() => useTaskEvents("shared-task"));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(fetchTaskEvents).toHaveBeenCalledTimes(1);

    first.unmount();
    second.unmount();
  });
});
