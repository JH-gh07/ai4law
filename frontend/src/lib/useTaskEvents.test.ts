/**
 * useTaskEvents 模块
 *
 * 函数：
 * - extractTokenUsage: 从运行事件中提取令牌使用情况的函数，接收一个 RunEvent 数组作为参数，返回一个 TokenUsageBreakdown 对象。
 * - mergeRunEvents: 合并运行事件的函数，接收两个 RunEvent 数组作为参数，返回一个合并后的 RunEvent 数组。
 * - useTaskEvents: 自定义 Hook，用于订阅任务事件流，接收一个任务 ID 作为参数，返回一个 RunEvent 数组。
 *
 * 类型：
 * - RunEvent: 运行事件类型，包含事件 ID、任务 ID、序列号、相关 ID、事件类型、时间戳、摘要、详细信息和日志级别等属性。
 * - TokenUsage: 令牌使用情况类型，包含提示令牌数、完成令牌数和总令牌数等属性。
 * - TokenUsageBreakdown: 令牌使用情况细分类型，包含总计、Copilot 和工作流的令牌使用情况。
 */
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchStreamToken, fetchTaskEvents } from "../api/events";
import { extractTokenUsage, mergeRunEvents, type RunEvent, useTaskEvents } from "./useTaskEvents";

vi.mock("../api/events", () => ({
  fetchStreamToken: vi.fn(),
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
  static instances: FakeEventSource[] = [];

  constructor(readonly url: string) {
    FakeEventSource.instances.push(this);
  }

  close() {
    this.readyState = FakeEventSource.CLOSED;
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("EventSource", FakeEventSource);
  vi.mocked(fetchTaskEvents).mockResolvedValue({ events: [], latest_seq: 0 });
  vi.mocked(fetchStreamToken).mockResolvedValue({
    stream_token: "stream-token-1",
    expires_at: "2026-08-06T00:05:00Z",
  });
  FakeEventSource.instances = [];
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

describe("extractTokenUsage", () => {
  it("reads the canonical nested LLM usage contract", () => {
    const llmEvent = event("llm-event", 3, "model returned");
    llmEvent.event_type = "tool_result";
    llmEvent.detail = {
      llm: {
        channel: "workflow",
        prompt_tokens: 11,
        completion_tokens: 7,
        total_tokens: 18,
      },
    };

    expect(extractTokenUsage([llmEvent]).total).toEqual({
      prompt_tokens: 11,
      completion_tokens: 7,
      total_tokens: 18,
    });
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

  it("requests a fresh stream token after an SSE connection fails", async () => {
    vi.mocked(fetchStreamToken)
      .mockResolvedValueOnce({ stream_token: "stream-token-1", expires_at: "2026-08-06T00:05:00Z" })
      .mockResolvedValueOnce({ stream_token: "stream-token-2", expires_at: "2026-08-06T00:10:00Z" });
    const hook = renderHook(() => useTaskEvents("reconnect-task"));

    await act(async () => {
      await Promise.resolve();
    });
    expect(FakeEventSource.instances[0]?.url).toContain("stream-token-1");

    await act(async () => {
      const first = FakeEventSource.instances[0];
      first.readyState = FakeEventSource.CLOSED;
      first.onerror?.();
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(fetchStreamToken).toHaveBeenCalledTimes(2);
    expect(FakeEventSource.instances[1]?.url).toContain("stream-token-2");
    hook.unmount();
  });

  it("does not reconnect a task that already has a terminal event", async () => {
    const firstMount = renderHook(() => useTaskEvents("completed-task"));
    await act(async () => {
      await Promise.resolve();
    });
    const source = FakeEventSource.instances[0];
    await act(async () => {
      source.onmessage?.({
        data: JSON.stringify({
          event_id: "completed-event",
          task_id: "completed-task",
          seq: 9,
          event_type: "status",
          timestamp: "2026-08-06T00:00:09Z",
          summary: "completed",
          detail: { state: "COMPLETED" },
          level: "audit",
        }),
      } as MessageEvent);
    });
    firstMount.unmount();

    const secondMount = renderHook(() => useTaskEvents("completed-task"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(fetchStreamToken).toHaveBeenCalledTimes(1);
    expect(fetchTaskEvents).not.toHaveBeenCalled();
    secondMount.unmount();
  });
});
