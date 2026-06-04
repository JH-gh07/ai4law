import { useEffect, useRef, useState, useCallback } from "react";

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

function connectSSE(taskId: string): EventSource {
  const es = new EventSource(`/api/v1/events/task/${taskId}/stream`);

  es.onmessage = (e) => {
    if (!e.data || e.data.startsWith(":")) return;
    try {
      const event: RunEvent = JSON.parse(e.data);
      const buffer = eventBuffers.get(taskId) ?? [];
      buffer.push(event);
      eventBuffers.set(taskId, buffer);
      const subs = listeners.get(taskId);
      if (subs) {
        for (const cb of subs) cb([...buffer]);
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
        const res = await fetch(`/api/v1/events/task/${taskId}/events?since=${latestSeq}`);
        const data = await res.json();
        if (data.events && data.events.length > 0) {
          const buffer = eventBuffers.get(taskId) ?? [];
          for (const e of data.events) {
            const exists = buffer.some((b) => b.seq === e.seq);
            if (!exists) buffer.push(e);
          }
          eventBuffers.set(taskId, buffer);
          latestSeq = data.latest_seq ?? latestSeq;
          const subs = listeners.get(taskId);
          if (subs) {
            for (const cb of subs) cb([...buffer]);
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
  const pollingCleanup = useRef<(() => void) | null>(null);

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

    // ════════════════════════════════════════════════════════════
    // 修复：Fallback polling 条件扩展。
    //
    // 旧逻辑：只在 3 秒内 buffer 为空时启动轮询。
    //         如果 SSE 先收到事件后断开，buffer 非空 → 不回退。
    //
    // 新逻辑：每 5 秒检查一次 SSE 的 readyState。
    //         如果 EventSource 不存在或已 CLOSED → 启动 HTTP 轮询
    //         作为兜底，确保后续事件不丢失。
    // ════════════════════════════════════════════════════════════
    const SSE_CHECK_INTERVAL_MS = 5000;
    const INITIAL_FALLBACK_DELAY_MS = 3000;

    let sseCheckTimer: ReturnType<typeof setInterval> | null = null;

    const fallbackTimer = setTimeout(() => {
      const buffer = eventBuffers.get(taskId);
      if (!buffer || buffer.length === 0) {
        // SSE 一直没收到事件 → 启动轮询
        const bufferNow = eventBuffers.get(taskId) ?? [];
        pollingCleanup.current = startPolling(taskId, bufferNow.length > 0 ? bufferNow[bufferNow.length - 1].seq : 0);
      } else {
        // SSE 收到过事件，但需要持续检查 SSE 是否断连
        sseCheckTimer = setInterval(() => {
          const es = eventSources.get(taskId);
          if (!es || es.readyState === EventSource.CLOSED) {
            // SSE 已关闭 → 启动轮询从最后一个已知 seq 开始
            const currentBuffer = eventBuffers.get(taskId) ?? [];
            const lastSeq = currentBuffer.length > 0 ? currentBuffer[currentBuffer.length - 1].seq : 0;
            if (!pollingCleanup.current) {
              pollingCleanup.current = startPolling(taskId, lastSeq);
            }
            if (sseCheckTimer) clearInterval(sseCheckTimer);
            sseCheckTimer = null;
          }
        }, SSE_CHECK_INTERVAL_MS);
      }
    }, INITIAL_FALLBACK_DELAY_MS);

    return () => {
      clearTimeout(fallbackTimer);
      if (sseCheckTimer) clearInterval(sseCheckTimer);
      listeners.get(taskId)?.delete(setEventsAndNotify);
      if (pollingCleanup.current) {
        pollingCleanup.current();
        pollingCleanup.current = null;
      }
      // 不删除 eventSources — EventSource 由 onerror 中 readyState===CLOSED 的检测来管理
    };
  }, [taskId, setEventsAndNotify]);

  return events;
}
