type Props = {
  moduleLabel: string;
  status: "running" | "completed" | "failed" | "empty";
  taskId: string | null;
  startedAt?: string;
  completedAt?: string;
  nodeCount: number;
  eventCount: number;
  workflowPromptTokens?: number;
  workflowCompletionTokens?: number;
  workflowTotalTokens?: number;
  copilotPromptTokens?: number;
  copilotCompletionTokens?: number;
  copilotTotalTokens?: number;
  totalPromptTokens?: number;
  totalCompletionTokens?: number;
  totalTokens?: number;
};

function fmtTime(iso?: string): string {
  if (!iso) return "--";
  return new Date(iso).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function fmtCount(value?: number): string {
  if (!value || value <= 0) return "--";
  return value.toLocaleString("zh-CN");
}

export function TraceRunHeader({
  moduleLabel,
  status,
  taskId,
  startedAt,
  completedAt,
  nodeCount,
  eventCount,
  workflowPromptTokens,
  workflowCompletionTokens,
  workflowTotalTokens,
  copilotPromptTokens,
  copilotCompletionTokens,
  copilotTotalTokens,
  totalPromptTokens,
  totalCompletionTokens,
  totalTokens,
}: Props) {
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
        <span className="trace-run-sep">·</span>
        <span>模块 Token {fmtCount(workflowTotalTokens)}</span>
        <span className="trace-run-sep">·</span>
        <span>模块输入 {fmtCount(workflowPromptTokens)}</span>
        <span className="trace-run-sep">·</span>
        <span>模块输出 {fmtCount(workflowCompletionTokens)}</span>
        <span className="trace-run-sep">·</span>
        <span>Copilot Token {fmtCount(copilotTotalTokens)}</span>
        <span className="trace-run-sep">·</span>
        <span>Copilot 输入 {fmtCount(copilotPromptTokens)}</span>
        <span className="trace-run-sep">·</span>
        <span>Copilot 输出 {fmtCount(copilotCompletionTokens)}</span>
        <span className="trace-run-sep">·</span>
        <span>总 Token {fmtCount(totalTokens)}</span>
        <span className="trace-run-sep">·</span>
        <span>总输入 {fmtCount(totalPromptTokens)}</span>
        <span className="trace-run-sep">·</span>
        <span>总输出 {fmtCount(totalCompletionTokens)}</span>
      </div>
    </div>
  );
}
