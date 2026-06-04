import { useEffect, useRef } from "react";
import { useLang } from "../../lib/language";
import type { RunEvent } from "../../lib/useTaskEvents";
import { useTaskEvents } from "../../lib/useTaskEvents";
import { useAppStore } from "../../lib/app-store";

type Props = {
  taskId: string | null;
  taskSpaceId: string;
  moduleLabel?: string;
};

const ICON_MAP: Record<RunEvent["event_type"], string> = {
  status: "●",
  thought: "💭",
  tool_start: "🔧",
  tool_result: "✅",
  intermediate: "📊",
  warning: "⚠️",
  final: "🏁",
  final_brief: "📝",
};

const COLOR_MAP: Record<RunEvent["event_type"], string> = {
  status: "#6b7280",
  thought: "#7c3aed",
  tool_start: "#2563eb",
  tool_result: "#059669",
  intermediate: "#ea580c",
  warning: "#dc2626",
  final: "#9333ea",
  final_brief: "#d946ef",
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function TimelineRow({ event }: { event: RunEvent }) {
  const icon = ICON_MAP[event.event_type] ?? "●";
  const color = COLOR_MAP[event.event_type] ?? "#6b7280";

  return (
    <div className="timeline-row" style={{ borderLeftColor: color }}>
      <div className="timeline-icon" style={{ color }}>
        {icon}
      </div>
      <div className="timeline-content">
        <div className="timeline-summary">{event.summary}</div>
        <div className="timeline-time">{formatTime(event.timestamp)}</div>
        {event.detail && Object.keys(event.detail).length > 0 && (
          <details className="timeline-detail">
            <summary>详情</summary>
            <pre>{JSON.stringify(event.detail, null, 2)}</pre>
          </details>
        )}
      </div>
    </div>
  );
}

/** Extract a short stage name from a tool_start/tool_result summary */
function extractStageName(summary: string): string {
  // "附件事实提取器" → "附件事实提取"
  // "差距分析规则引擎" → "差距分析"
  // "事实合并器" → "事实合并"
  // "CPRA 事实提取" → "事实提取"
  const trimmed = summary.replace(/^(CPRA |SCC |DPIA |BCR |TIA |EU |US )/, "");
  if (trimmed.length <= 12) return trimmed;
  return trimmed.slice(0, 12) + "…";
}

export function ExecutionTimeline({ taskId, taskSpaceId, moduleLabel }: Props) {
  const { lang } = useLang();
  const events = useTaskEvents(taskId);
  const { dispatch } = useAppStore();
  const sessionIdRef = useRef<string | null>(null);
  const pendingStagesRef = useRef<string[]>([]);  // stack of running stage IDs
  const seenSeqs = useRef(new Set<number>());

  // ── 将 SSE 事件流桥接为 RunSession + StageNode 生命周期 ──
  useEffect(() => {
    if (!taskId || events.length === 0) return;

    // Find new events we haven't processed yet
    const newEvents = events.filter((e) => !seenSeqs.current.has(e.seq));
    if (newEvents.length === 0) return;

    for (const event of newEvents) {
      seenSeqs.current.add(event.seq);

      switch (event.event_type) {

        case "status": {
          // Begin a new run session
          if (sessionIdRef.current) break; // only one session per timeline mount
          const sessionId = `run-${taskId}`;
          sessionIdRef.current = sessionId;
          dispatch({
            type: "begin_run_session",
            payload: {
              id: sessionId,
              taskSpaceId,
              taskId,
              module: moduleLabel ?? "",
              startedAt: event.timestamp,
              stages: [],
              isComplete: false,
              collapsed: false,
            },
          });
          break;
        }

        case "tool_start": {
          const sessionId = sessionIdRef.current;
          if (!sessionId) break;
          const stageId = `stage-${taskId}-${event.seq}`;
          pendingStagesRef.current.push(stageId);

          const agentName = event.detail?.agent
            ? String(event.detail.agent)
            : event.detail?.tool
              ? String(event.detail.tool)
              : extractStageName(event.summary);
          const command = event.detail?.tool ? String(event.detail.tool) : event.detail?.agent ? String(event.detail.agent) : undefined;

          dispatch({
            type: "begin_run_session",
            payload: {
              id: sessionId,
              taskSpaceId,
              taskId,
              module: moduleLabel ?? "",
              startedAt: event.timestamp,
              stages: [{
                id: stageId,
                name: agentName,
                status: "running",
                startedAt: event.timestamp,
                command,
                icon: "🔧",
              }],
              isComplete: false,
              collapsed: false,
            },
          });
          break;
        }

        case "tool_result": {
          const stageId = pendingStagesRef.current.pop();
          if (!stageId) break;
          const sessionId = sessionIdRef.current;
          if (!sessionId) break;
          dispatch({
            type: "stage_done",
            payload: {
              sessionId,
              stageId,
              summary: event.summary,
              detail: event.detail ?? null,
              completedAt: event.timestamp,
            },
          });
          break;
        }

        case "thought": {
          const sessionId = sessionIdRef.current;
          if (!sessionId) break;
          const runningStageId = pendingStagesRef.current[pendingStagesRef.current.length - 1];
          if (!runningStageId) break;
          dispatch({
            type: "stage_done",
            payload: {
              sessionId,
              stageId: runningStageId,
              summary: event.summary,
              completedAt: event.timestamp,
            },
          });
          break;
        }

        case "final": {
          const sessionId = sessionIdRef.current;
          if (!sessionId) break;
          dispatch({
            type: "finish_run_session",
            payload: {
              sessionId,
              completedAt: event.timestamp,
              totalDurationMs: event.detail?.total_duration_ms
                ? Number(event.detail.total_duration_ms)
                : undefined,
            },
          });
          break;
        }

        case "warning": {
          // Warning creates a stage that immediately completes with a warning icon
          const sessionId = sessionIdRef.current;
          if (!sessionId) break;
          const stageId = `stage-${taskId}-${event.seq}`;
          dispatch({
            type: "begin_run_session",
            payload: {
              id: sessionId,
              taskSpaceId,
              taskId,
              module: moduleLabel ?? "",
              startedAt: event.timestamp,
              stages: [{
                id: stageId,
                name: event.summary,
                status: "done",
                startedAt: event.timestamp,
                completedAt: event.timestamp,
                summary: event.summary,
                icon: "⚠️",
              }],
              isComplete: false,
              collapsed: false,
            },
          });
          break;
        }

        case "final_brief":
          // Already handled by `final` → `finish_run_session`
          break;

        case "intermediate":
          // Intermediate snapshots just create a done stage
          {
            const sessionId = sessionIdRef.current;
            if (!sessionId) break;
            const stageId = `stage-${taskId}-${event.seq}`;
            dispatch({
              type: "begin_run_session",
              payload: {
                id: sessionId,
                taskSpaceId,
                taskId,
                module: moduleLabel ?? "",
                startedAt: event.timestamp,
                stages: [{
                  id: stageId,
                  name: extractStageName(event.summary),
                  status: "done",
                  startedAt: event.timestamp,
                  completedAt: event.timestamp,
                  summary: event.summary,
                  icon: "📊",
                }],
                isComplete: false,
                collapsed: false,
              },
            });
          }
          break;
      }
    }
  }, [events, taskId, taskSpaceId, dispatch, moduleLabel]);

  // Cleanup on unmount — clear session
  useEffect(() => {
    return () => {
      if (sessionIdRef.current && taskId) {
        sessionIdRef.current = null;
        pendingStagesRef.current = [];
        seenSeqs.current.clear();
      }
    };
  }, [taskId]);

  const isConnected = events.length > 0;

  return (
    <section className="execution-timeline">
      <header className="workspace-tab-head">
        <h3>{lang === "zh" ? "执行流" : "Execution Timeline"}</h3>
        <p>
          <span className={`timeline-status-dot ${isConnected ? "connected" : "waiting"}`} />
          {isConnected
            ? lang === "zh"
              ? `实时连接 · ${events.length} 个事件`
              : `Connected · ${events.length} events`
            : lang === "zh"
              ? "等待事件..."
              : "Waiting for events..."}
        </p>
      </header>
      <div className="timeline-body">
        {events.length === 0 ? (
          <p className="resource-empty">
            {lang === "zh"
              ? "尚未收到执行事件。启动模块运行后将在此展示实时执行流。"
              : "No execution events yet. Start a module run to see the live timeline."}
          </p>
        ) : (
          events.map((e) => <TimelineRow key={e.seq ? `${e.task_id}-${e.seq}` : e.event_id} event={e} />)
        )}
      </div>
    </section>
  );
}
