import { useCallback, useEffect, useState } from "react";
import { fetchTaskEvents, getTaskEventStreamUrl } from "../api/events";

export type RunEvent = {
  event_id: string;
  task_id: string;
  seq: number;
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
      if (event.detail?.tool !== "llm_chat") return acc;
      const usage = event.detail?.usage;
      if (!usage || typeof usage !== "object") return acc;
      const record = usage as Record<string, unknown>;
      const prompt = typeof record.prompt_tokens === "number" ? record.prompt_tokens : 0;
      const completion = typeof record.completion_tokens === "number" ? record.completion_tokens : 0;
      const total = typeof record.total_tokens === "number" ? record.total_tokens : prompt + completion;
      const channel = event.detail?.channel === "copilot" ? "copilot" : "workflow";
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

function stopPolling(taskId: string): void {
  pollingCleanups.get(taskId)?.();
  pollingCleanups.delete(taskId);
}

function ensurePolling(taskId: string): void {
  if (pollingCleanups.has(taskId)) return;
  pollingCleanups.set(taskId, startPolling(taskId, latestKnownSeq(taskId)));
}

function connectSSE(taskId: string): EventSource {
  const es = new EventSource(getTaskEventStreamUrl(taskId));

  es.onopen = () => {
    stopPolling(taskId);
  };

  es.onmessage = (e) => {
    if (!e.data || e.data.startsWith(":")) return;
    try {
      const event: RunEvent = JSON.parse(e.data);
      const buffer = eventBuffers.get(taskId) ?? [];
      const merged = mergeRunEvents(buffer, [event]);
      if (merged.length === buffer.length) return;
      eventBuffers.set(taskId, merged);
      const subs = listeners.get(taskId);
      if (subs) {
        for (const cb of subs) cb([...merged]);
      }
    } catch {
      // ignore parse errors
    }
  };

  // ════════════════════════════════════════════════════════════
  // 修复：不手动 close/delete EventSource。
  // 浏览器 EventSource 有内置自动重连机制，在连接意外断开后会
  // 自动重新连接。之前的代码在 onerror 中手动 close() + delete
  // 会阻止这个机制。
  //
  // 正确的做法：记录错误状态供 fallback polling 决策使用，
  // 但让浏览器自己管理重连生命周期。
  // ════════════════════════════════════════════════════════════
  es.onerror = () => {
    // 浏览器会基于 readyState 自动重连。我们只记录错误以便
    // fallback polling 做决策，不干预 EventSource 生命周期。
    // 连接到 CLOSED 状态（非 0/1）时才从 registry 中清理。
    if (es.readyState === EventSource.CLOSED) {
      eventSources.delete(taskId);
      if ((listeners.get(taskId)?.size ?? 0) > 0) ensurePolling(taskId);
    }
  };

  return es;
}

function startPolling(taskId: string, since: number): () => void {
  let active = true;
  let latestSeq = since;

  const poll = async () => {
    while (active) {
      try {
        const data = await fetchTaskEvents<RunEvent>(taskId, latestSeq);
        if (data.events && data.events.length > 0) {
          const buffer = eventBuffers.get(taskId) ?? [];
          const merged = mergeRunEvents(buffer, data.events);
          eventBuffers.set(taskId, merged);
          latestSeq = data.latest_seq ?? latestSeq;
          if (merged.length !== buffer.length) {
            const subs = listeners.get(taskId);
            if (subs) {
              for (const cb of subs) cb([...merged]);
            }
          }
        }
      } catch {
        // retry on next interval
      }
      await new Promise((r) => setTimeout(r, 1500));
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

    // Start SSE if not already connected for this taskId
    if (!eventSources.has(taskId)) {
      const es = connectSSE(taskId);
      eventSources.set(taskId, es);
    }

    // SSE 三秒内未建立时启动 task 级共享轮询；连接恢复后 onopen 自动停止。
    const INITIAL_FALLBACK_DELAY_MS = 3000;

    const fallbackTimer = setTimeout(() => {
      const es = eventSources.get(taskId);
      if (!es || es.readyState !== EventSource.OPEN) ensurePolling(taskId);
    }, INITIAL_FALLBACK_DELAY_MS);

    return () => {
      clearTimeout(fallbackTimer);
      const taskListeners = listeners.get(taskId);
      taskListeners?.delete(setEventsAndNotify);
      if (!taskListeners || taskListeners.size === 0) {
        listeners.delete(taskId);
        stopPolling(taskId);
        eventSources.get(taskId)?.close();
        eventSources.delete(taskId);
      }
    };
  }, [taskId, setEventsAndNotify]);

  return events;
}
