import { useCallback, useEffect, useState } from "react";
import { fetchStreamToken, fetchTaskEvents, getTaskEventStreamUrl } from "../api/events";

export type RunEvent = {
  event_id: string;
  task_id: string;
  seq: number;
  correlation_id?: string | null;
  event_type:
    | "status"
    | "thought"
    | "tool_start"
    | "tool_result"
    | "intermediate"
    | "warning"
    | "final"
    | "final_brief";
  timestamp: string;
  summary: string;
  detail?: Record<string, unknown> | null;
  level: "audit" | "debug";
};

export type TokenUsage = {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
};

export type TokenUsageBreakdown = {
  total: TokenUsage;
  copilot: TokenUsage;
  workflow: TokenUsage;
};

function addUsage(target: TokenUsage, prompt: number, completion: number, total: number): TokenUsage {
  return {
    prompt_tokens: target.prompt_tokens + prompt,
    completion_tokens: target.completion_tokens + completion,
    total_tokens: target.total_tokens + total,
  };
}

export function extractTokenUsage(events: RunEvent[]): TokenUsageBreakdown {
  return events.reduce<TokenUsageBreakdown>(
    (acc, event) => {
      const nested = event.detail?.llm;
      const nestedRecord = nested && typeof nested === "object"
        ? nested as Record<string, unknown>
        : null;
      const legacyUsage = event.detail?.usage;
      const record = nestedRecord ?? (
        event.detail?.tool === "llm_chat" && legacyUsage && typeof legacyUsage === "object"
          ? legacyUsage as Record<string, unknown>
          : null
      );
      if (!record) return acc;
      const prompt = typeof record.prompt_tokens === "number" ? record.prompt_tokens : 0;
      const completion = typeof record.completion_tokens === "number" ? record.completion_tokens : 0;
      const total = typeof record.total_tokens === "number" ? record.total_tokens : prompt + completion;
      const channelValue = nestedRecord?.channel ?? event.detail?.channel;
      const channel = channelValue === "copilot" ? "copilot" : "workflow";
      return {
        total: addUsage(acc.total, prompt, completion, total),
        copilot: channel === "copilot" ? addUsage(acc.copilot, prompt, completion, total) : acc.copilot,
        workflow: channel === "workflow" ? addUsage(acc.workflow, prompt, completion, total) : acc.workflow,
      };
    },
    {
      total: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
      copilot: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
      workflow: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
    }
  );
}

// ---------------------------------------------------------------------------
// Global SSE / polling registry (module-level singletons)
// ---------------------------------------------------------------------------

const eventSources = new Map<string, EventSource>();
const listeners = new Map<string, Set<(events: RunEvent[]) => void>>();
const eventBuffers = new Map<string, RunEvent[]>();
const pollingCleanups = new Map<string, () => void>();
const pendingConnections = new Set<string>();
const reconnectTimers = new Map<string, ReturnType<typeof setTimeout>>();
const MAX_BUFFERED_EVENTS = 500;

function eventIdentity(event: RunEvent): string {
  return event.event_id || `${event.task_id}:${event.seq}`;
}

export function mergeRunEvents(current: RunEvent[], incoming: RunEvent[]): RunEvent[] {
  const seen = new Set<string>();
  const merged: RunEvent[] = [];

  for (const event of [...current, ...incoming]) {
    const identity = eventIdentity(event);
    if (seen.has(identity)) continue;
    seen.add(identity);
    merged.push(event);
  }

  return merged;
}

function latestKnownSeq(taskId: string): number {
  return (eventBuffers.get(taskId) ?? []).reduce((latest, event) => Math.max(latest, event.seq), -1);
}

function isTerminalEvent(event: RunEvent): boolean {
  const state = typeof event.detail?.state === "string"
    ? event.detail.state.toUpperCase()
    : "";
  return event.event_type === "status"
    && ["COMPLETED", "FAILED", "CANCELED", "CANCELLED"].includes(state);
}

function hasTerminalEvent(taskId: string): boolean {
  return (eventBuffers.get(taskId) ?? []).some(isTerminalEvent);
}

function stopPolling(taskId: string): void {
  pollingCleanups.get(taskId)?.();
  pollingCleanups.delete(taskId);
}

function ensurePolling(taskId: string): void {
  if (pollingCleanups.has(taskId)) return;
  pollingCleanups.set(taskId, startPolling(taskId, latestKnownSeq(taskId)));
}

function stopTaskTransport(taskId: string): void {
  const source = eventSources.get(taskId);
  eventSources.delete(taskId);
  source?.close();
  stopPolling(taskId);
  const reconnectTimer = reconnectTimers.get(taskId);
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimers.delete(taskId);
}

function publishTaskEvents(taskId: string, incoming: RunEvent[]): void {
  const buffer = eventBuffers.get(taskId) ?? [];
  const merged = mergeRunEvents(buffer, incoming);
  const reachedTerminalState = incoming.some(isTerminalEvent);
  if (merged.length !== buffer.length) {
    const bounded = merged.slice(-MAX_BUFFERED_EVENTS);
    eventBuffers.set(taskId, bounded);
    const subs = listeners.get(taskId);
    if (subs) {
      for (const cb of subs) cb([...bounded]);
    }
  }
  if (reachedTerminalState) stopTaskTransport(taskId);
}

function scheduleReconnect(taskId: string): void {
  if (
    reconnectTimers.has(taskId)
    || hasTerminalEvent(taskId)
    || (listeners.get(taskId)?.size ?? 0) === 0
  ) return;
  ensurePolling(taskId);
  const timer = setTimeout(() => {
    reconnectTimers.delete(taskId);
    void ensureSSE(taskId);
  }, 1000);
  reconnectTimers.set(taskId, timer);
}

async function ensureSSE(taskId: string): Promise<void> {
  if (
    eventSources.has(taskId)
    || pendingConnections.has(taskId)
    || hasTerminalEvent(taskId)
    || (listeners.get(taskId)?.size ?? 0) === 0
  ) return;

  pendingConnections.add(taskId);
  try {
    const { stream_token } = await fetchStreamToken(taskId);
    if ((listeners.get(taskId)?.size ?? 0) === 0) return;

    const es = new EventSource(
      `${getTaskEventStreamUrl(taskId)}?token=${encodeURIComponent(stream_token)}&since=${latestKnownSeq(taskId)}`,
    );
    es.onopen = () => {
      stopPolling(taskId);
    };
    es.onmessage = (message) => {
      if (!message.data || message.data.startsWith(":")) return;
      try {
        publishTaskEvents(taskId, [JSON.parse(message.data) as RunEvent]);
      } catch {
        // Ignore malformed transport frames; polling remains the recovery path.
      }
    };
    es.onerror = () => {
      if (eventSources.get(taskId) !== es) return;
      es.close();
      eventSources.delete(taskId);
      scheduleReconnect(taskId);
    };
    eventSources.set(taskId, es);
  } catch {
    scheduleReconnect(taskId);
  } finally {
    pendingConnections.delete(taskId);
  }
}


function startPolling(taskId: string, since: number): () => void {
  let active = true;
  let latestSeq = since;

  const poll = async () => {
    while (active) {
      let delayMs = 1500;
      try {
        const data = await fetchTaskEvents<RunEvent>(taskId, latestSeq);
        if (data.events && data.events.length > 0) {
          latestSeq = data.latest_seq ?? latestSeq;
          publishTaskEvents(taskId, data.events);
          delayMs = data.has_more ? 0 : 1500;
        }
      } catch {
        // retry on next interval
      }
      await new Promise((r) => setTimeout(r, delayMs));
    }
  };
  void poll();
  return () => {
    active = false;
  };
}

// ---------------------------------------------------------------------------
// useTaskEvents — React hook
// ---------------------------------------------------------------------------

export function useTaskEvents(taskId: string | null): RunEvent[] {
  const [events, setEvents] = useState<RunEvent[]>([]);

  const setEventsAndNotify = useCallback((newEvents: RunEvent[]) => {
    setEvents(newEvents);
  }, []);

  useEffect(() => {
    if (!taskId) return;

    // Register listener
    if (!listeners.has(taskId)) {
      listeners.set(taskId, new Set());
    }
    listeners.get(taskId)!.add(setEventsAndNotify);

    const existing = eventBuffers.get(taskId);
    if (existing && existing.length > 0) {
      setEvents([...existing]);
    }

    void ensureSSE(taskId);

    // 3 秒后如果 SSE 还未建立 (token 请求慢 / 失败)，启动 polling fallback
    const INITIAL_FALLBACK_DELAY_MS = 3000;

    const fallbackTimer = setTimeout(() => {
      if (hasTerminalEvent(taskId)) return;
      const es = eventSources.get(taskId);
      if (!es || es.readyState !== EventSource.OPEN) ensurePolling(taskId);
    }, INITIAL_FALLBACK_DELAY_MS);

    return () => {
      clearTimeout(fallbackTimer);
      const taskListeners = listeners.get(taskId);
      taskListeners?.delete(setEventsAndNotify);
      if (!taskListeners || taskListeners.size === 0) {
        listeners.delete(taskId);
        stopTaskTransport(taskId);
      }
    };
  }, [taskId, setEventsAndNotify]);

  return events;
}
