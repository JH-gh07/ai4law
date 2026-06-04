type Props = {
  moduleLabel: string;
  status: "running" | "completed" | "failed" | "empty";
  taskId: string | null;
  startedAt?: string;
  completedAt?: string;
  nodeCount: number;
  eventCount: number;
};

function fmtTime(iso?: string): string {
  if (!iso) return "--";
  return new Date(iso).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function TraceRunHeader({ moduleLabel, status, taskId, startedAt, completedAt, nodeCount, eventCount }: Props) {
  const liveCompletedAt = completedAt ?? (status === "running" ? new Date().toISOString() : undefined);
  const durationMs =
    startedAt && liveCompletedAt
      ? Math.max(0, new Date(liveCompletedAt).getTime() - new Date(startedAt).getTime())
      : null;
  const durationLabel = durationMs != null ? `${Math.round(durationMs / 1000)}s` : "--";
  const workspaceLabel = moduleLabel.trim().length > 0 ? moduleLabel : "workspace";

  return (
    <div className="trace-run-header">
      <div className="trace-run-header-left">
        <div className="trace-run-title-group">
          <span className="trace-run-module">{workspaceLabel}</span>
          <span className="trace-run-title">执行历史记录</span>
        </div>
        <span className={`trace-run-badge badge-${status}`}>
          {status === "running"
            ? "RUNNING"
            : status === "completed"
              ? "COMPLETED"
              : status === "failed"
                ? "FAILED"
                : "--"}
        </span>
        {taskId ? <code className="trace-run-id">{taskId.slice(0, 12)}…</code> : null}
      </div>
      <div className="trace-run-header-right">
        <span>开始 {fmtTime(startedAt)}</span>
        <span className="trace-run-sep">·</span>
        <span>{status === "running" ? "最近" : "完成"} {fmtTime(completedAt ?? liveCompletedAt)}</span>
        <span className="trace-run-sep">·</span>
        <span>用时 {durationLabel}</span>
        <span className="trace-run-sep">·</span>
        <span>事件 {eventCount}</span>
        <span className="trace-run-sep">·</span>
        <span>节点 {nodeCount}</span>
      </div>
    </div>
  );
}
