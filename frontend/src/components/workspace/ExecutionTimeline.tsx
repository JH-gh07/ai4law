import { useEffect, useRef } from "react";
import { useLang } from "../../lib/language";
import type { RunEvent } from "../../lib/useTaskEvents";
import { useTaskEvents } from "../../lib/useTaskEvents";
import { useAppStore } from "../../lib/app-store";

type Props = {
  taskId: string | null;
  taskSpaceId: string;
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

export function ExecutionTimeline({ taskId, taskSpaceId }: Props) {
  const { lang } = useLang();
  const events = useTaskEvents(taskId);
  const { dispatch } = useAppStore();
  const lastDispatchTime = useRef(0);

  // 将 thought/tool_start/warning/final 事件桥接为 Copilot 系统消息（有频率控制）
  useEffect(() => {
    if (events.length === 0) return;
    const latest = events[events.length - 1];
    if (latest.event_type === "tool_result" || latest.event_type === "intermediate") return; // skip noisy types

    const now = Date.now();
    if (now - lastDispatchTime.current < 1000) return; // max 1 per second
    lastDispatchTime.current = now;

    const msg = {
      id: `sys-${taskId}-${latest.seq}`,
      taskSpaceId,
      text: latest.summary,
      createdAt: new Date().toISOString(),
      eventType: latest.event_type,
      eventSeq: latest.seq,
    };
    dispatch({ type: "append_system_message", payload: msg });
  }, [events, taskId, taskSpaceId, dispatch]);

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
