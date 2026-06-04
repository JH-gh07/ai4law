import type { RunEvent } from "./useTaskEvents";

export type RunTranscriptBrief = {
  conclusion?: string;
  files?: string[];
  risks?: Array<{ severity: string; count: number }>;
  next_steps?: string[];
  stats?: Record<string, unknown>;
  notices?: string[];
};

export type RunTranscriptRow = {
  id: string;
  kind: "summary" | "tool" | "intermediate" | "warning" | "brief" | "final";
  label: string;
  summary: string;
  timestamp: string;
  detail?: Record<string, unknown> | null;
  resultSummary?: string;
  resultDetail?: Record<string, unknown> | null;
  state?: "running" | "done";
  brief?: RunTranscriptBrief | null;
};

export type RunTranscriptSnapshot = {
  rows: RunTranscriptRow[];
  statusText: string;
  currentStage: string;
  startedAt: string | null;
  completedAt: string | null;
  eventCount: number;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

function toolLabel(event: RunEvent): string {
  const tool = typeof event.detail?.tool === "string" ? event.detail.tool : null;
  const agent = typeof event.detail?.agent === "string" ? event.detail.agent : null;
  if (tool) return tool;
  if (agent) return agent;
  return event.summary;
}

function statusTextFromEvents(events: RunEvent[]): string {
  const finalEvent = [...events].reverse().find((event) => event.event_type === "final");
  if (finalEvent) {
    return "COMPLETED";
  }

  const lastStatus = [...events].reverse().find((event) => event.event_type === "status");
  const state = typeof lastStatus?.detail?.state === "string" ? lastStatus.detail.state.toUpperCase() : null;
  return state ?? (events.length > 0 ? "RUNNING" : "IDLE");
}

function currentStageFromRows(rows: RunTranscriptRow[]): string {
  const activeTool = [...rows].reverse().find((row) => row.kind === "tool" && row.state === "running");
  if (activeTool) return activeTool.label;

  const lastRelevant = [...rows].reverse().find((row) => row.kind !== "brief" && row.kind !== "final");
  return lastRelevant?.label ?? "等待执行";
}

export function buildRunTranscript(events: RunEvent[]): RunTranscriptSnapshot {
  const rows: RunTranscriptRow[] = [];
  const openToolRows: number[] = [];

  for (const event of events) {
    if (event.event_type === "tool_start") {
      rows.push({
        id: event.event_id,
        kind: "tool",
        label: toolLabel(event),
        summary: event.summary,
        timestamp: event.timestamp,
        detail: event.detail ?? null,
        state: "running",
      });
      openToolRows.push(rows.length - 1);
      continue;
    }

    if (event.event_type === "tool_result") {
      const lastToolIndex = openToolRows.pop();
      if (lastToolIndex !== undefined) {
        const current = rows[lastToolIndex];
        rows[lastToolIndex] = {
          ...current,
          state: "done",
          resultSummary: event.summary,
          resultDetail: event.detail ?? null,
          timestamp: event.timestamp,
        };
      } else {
        rows.push({
          id: event.event_id,
          kind: "tool",
          label: toolLabel(event),
          summary: event.summary,
          timestamp: event.timestamp,
          resultSummary: event.summary,
          resultDetail: event.detail ?? null,
          state: "done",
        });
      }
      continue;
    }

    if (event.event_type === "thought") {
      rows.push({
        id: event.event_id,
        kind: "summary",
        label: "分析摘要",
        summary: event.summary,
        timestamp: event.timestamp,
        detail: event.detail ?? null,
      });
      continue;
    }

    if (event.event_type === "status") {
      rows.push({
        id: event.event_id,
        kind: "summary",
        label: "运行状态",
        summary: event.summary,
        timestamp: event.timestamp,
        detail: event.detail ?? null,
      });
      continue;
    }

    if (event.event_type === "intermediate") {
      rows.push({
        id: event.event_id,
        kind: "intermediate",
        label: typeof event.detail?.category === "string" ? event.detail.category : "中间产物",
        summary: event.summary,
        timestamp: event.timestamp,
        detail: event.detail ?? null,
      });
      continue;
    }

    if (event.event_type === "warning") {
      rows.push({
        id: event.event_id,
        kind: "warning",
        label: "注意事项",
        summary: event.summary,
        timestamp: event.timestamp,
        detail: event.detail ?? null,
      });
      continue;
    }

    if (event.event_type === "final_brief") {
      rows.push({
        id: event.event_id,
        kind: "brief",
        label: "最终简报",
        summary: event.summary,
        timestamp: event.timestamp,
        detail: event.detail ?? null,
        brief: isRecord(event.detail) ? (event.detail as RunTranscriptBrief) : null,
      });
      continue;
    }

    if (event.event_type === "final") {
      rows.push({
        id: event.event_id,
        kind: "final",
        label: "执行完成",
        summary: event.summary,
        timestamp: event.timestamp,
        detail: event.detail ?? null,
      });
    }
  }

  return {
    rows,
    statusText: statusTextFromEvents(events),
    currentStage: currentStageFromRows(rows),
    startedAt: events[0]?.timestamp ?? null,
    completedAt: [...events].reverse().find((event) => event.event_type === "final")?.timestamp ?? null,
    eventCount: events.length,
  };
}
