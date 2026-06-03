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

  es.onerror = () => {
    es.close();
    eventSources.delete(taskId);
  };

  return es;
}

function startPolling(taskId: string, since: number): () => void {
  let active = true;
  const poll = async () => {
    while (active) {
      try {
        const res = await fetch(`/api/v1/events/task/${taskId}/events?since=${since}`);
        const data = await res.json();
        if (data.events.length > 0) {
          const buffer = eventBuffers.get(taskId) ?? [];
          for (const e of data.events) {
            const exists = buffer.some((b) => b.seq === e.seq);
            if (!exists) buffer.push(e);
          }
          eventBuffers.set(taskId, buffer);
          since = data.latest_seq;
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
  poll();
  return () => {
    active = false;
  };
}

export function useTaskEvents(taskId: string | null): RunEvent[] {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const pollingCleanup = useRef<(() => void) | null>(null);

  const setEventsAndNotify = useCallback((newEvents: RunEvent[]) => {
    setEvents(newEvents);
  }, []);

  useEffect(() => {
    if (!taskId) return;

    if (!listeners.has(taskId)) {
      listeners.set(taskId, new Set());
    }
    listeners.get(taskId)!.add(setEventsAndNotify);

    const existing = eventBuffers.get(taskId);
    if (existing && existing.length > 0) {
      setEvents([...existing]);
    }

    if (!eventSources.has(taskId)) {
      const es = connectSSE(taskId);
      eventSources.set(taskId, es);
    }

    const fallbackTimer = setTimeout(() => {
      const buffer = eventBuffers.get(taskId);
      if (!buffer || buffer.length === 0) {
        pollingCleanup.current = startPolling(taskId, 0);
      }
    }, 3000);

    return () => {
      clearTimeout(fallbackTimer);
      listeners.get(taskId)?.delete(setEventsAndNotify);
      if (pollingCleanup.current) {
        pollingCleanup.current();
        pollingCleanup.current = null;
      }
    };
  }, [taskId, setEventsAndNotify]);

  return events;
}
