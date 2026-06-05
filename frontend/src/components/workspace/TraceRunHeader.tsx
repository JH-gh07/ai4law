import type { Language } from "../../lib/i18n";
import { getTraceI18n, getTraceLocale } from "../../lib/trace-i18n";

type Props = {
  lang: Language;
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

function fmtTime(iso: string | undefined, lang: Language): string {
  if (!iso) return "--";
  return new Date(iso).toLocaleTimeString(getTraceLocale(lang), { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function fmtCount(value: number | undefined, lang: Language): string {
  if (!value || value <= 0) return "--";
  return value.toLocaleString(getTraceLocale(lang));
}

export function TraceRunHeader({
  lang,
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
  const t = getTraceI18n(lang);
  const liveCompletedAt = completedAt ?? (status === "running" ? new Date().toISOString() : undefined);
  const durationMs =
    startedAt && liveCompletedAt
      ? Math.max(0, new Date(liveCompletedAt).getTime() - new Date(startedAt).getTime())
      : null;
  const durationLabel = durationMs != null ? `${Math.round(durationMs / 1000)}s` : "--";
  const workspaceLabel = moduleLabel.trim().length > 0 ? moduleLabel : t.workspace;

  return (
    <div className="trace-run-header">
      <div className="trace-run-header-left">
        <div className="trace-run-title-group">
          <span className="trace-run-module">{workspaceLabel}</span>
          <span className="trace-run-title">{t.executionHistory}</span>
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
        <span>{t.started} {fmtTime(startedAt, lang)}</span>
        <span className="trace-run-sep">·</span>
        <span>{status === "running" ? t.latest : t.completed} {fmtTime(completedAt ?? liveCompletedAt, lang)}</span>
        <span className="trace-run-sep">·</span>
        <span>{t.duration} {durationLabel}</span>
        <span className="trace-run-sep">·</span>
        <span>{t.events} {eventCount}</span>
        <span className="trace-run-sep">·</span>
        <span>{t.nodes} {nodeCount}</span>
        <span className="trace-run-sep">·</span>
        <span>{t.workflowTokens} {fmtCount(workflowTotalTokens, lang)}</span>
        <span className="trace-run-sep">·</span>
        <span>{t.workflowInput} {fmtCount(workflowPromptTokens, lang)}</span>
        <span className="trace-run-sep">·</span>
        <span>{t.workflowOutput} {fmtCount(workflowCompletionTokens, lang)}</span>
        <span className="trace-run-sep">·</span>
        <span>{t.copilotTokens} {fmtCount(copilotTotalTokens, lang)}</span>
        <span className="trace-run-sep">·</span>
        <span>{t.copilotInput} {fmtCount(copilotPromptTokens, lang)}</span>
        <span className="trace-run-sep">·</span>
        <span>{t.copilotOutput} {fmtCount(copilotCompletionTokens, lang)}</span>
        <span className="trace-run-sep">·</span>
        <span>{t.totalTokens} {fmtCount(totalTokens, lang)}</span>
        <span className="trace-run-sep">·</span>
        <span>{t.totalInput} {fmtCount(totalPromptTokens, lang)}</span>
        <span className="trace-run-sep">·</span>
        <span>{t.totalOutput} {fmtCount(totalCompletionTokens, lang)}</span>
      </div>
    </div>
  );
}
