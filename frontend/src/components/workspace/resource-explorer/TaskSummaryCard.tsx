import { StatusBadge } from "./StatusBadge";
import type { TaskSummaryData } from "./types";
import { useLang } from "../../../lib/language";

type TaskSummaryCardProps = {
  summary: TaskSummaryData;
};

export function TaskSummaryCard({ summary }: TaskSummaryCardProps) {
  const { lang } = useLang();
  const progressValue = Math.max(0, Math.min(100, summary.progress));

  return (
    <section className="rx-summary">
      <div className="rx-summary-head">
        <h3>{lang === "zh" ? "当前任务" : "Current Task"}</h3>
        <StatusBadge status={summary.status} />
      </div>
      <strong className="rx-summary-name">{summary.name}</strong>
      <div className="rx-summary-tags">
        <span>{summary.jurisdiction}</span>
        <span>{summary.flow}</span>
        <span>{summary.module}</span>
        <span>{summary.runBatch}</span>
      </div>
      <div className="rx-summary-progress">
        <label>{lang === "zh" ? "进度" : "Progress"} {progressValue}%</label>
        <div className="rx-progress-track">
          <span style={{ width: `${progressValue}%` }} />
        </div>
      </div>
      {summary.blockedReason ? <p className="rx-summary-blocked">{summary.blockedReason}</p> : null}
    </section>
  );
}
