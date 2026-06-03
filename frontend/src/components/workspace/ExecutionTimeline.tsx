import { useMemo } from "react";
import { useLang } from "../../lib/language";
import type { RunEvent } from "../../lib/useTaskEvents";
import { useTaskEvents } from "../../lib/useTaskEvents";

type Props = {
  taskId: string | null;
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

export function ExecutionTimeline({ taskId }: Props) {
  const { lang } = useLang();
  const events = useTaskEvents(taskId);

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
