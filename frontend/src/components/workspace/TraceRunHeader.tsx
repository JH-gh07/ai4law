type Props = {
  moduleLabel: string;
  status: "running" | "completed" | "failed" | "empty";
  taskId: string | null;
  startedAt?: string;
  completedAt?: string;
  nodeCount: number;
};

function fmtTime(iso?: string): string {
  if (!iso) return "--";
  return new Date(iso).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function TraceRunHeader({ moduleLabel, status, taskId, startedAt, completedAt, nodeCount }: Props) {
  return (
    <div className="trace-run-header">
      <div className="trace-run-header-left">
        <span className="trace-run-module">{moduleLabel}</span>
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
        <span>完成 {fmtTime(completedAt)}</span>
        <span className="trace-run-sep">·</span>
        <span>事件 {nodeCount}</span>
      </div>
    </div>
  );
}
