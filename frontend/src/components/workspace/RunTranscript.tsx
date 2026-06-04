import { useMemo } from "react";
import { useLang } from "../../lib/language";
import { buildRunTranscript, type RunTranscriptBrief, type RunTranscriptRow } from "../../lib/run-stream";
import { useTaskEvents } from "../../lib/useTaskEvents";

type Props = {
  taskId: string | null;
  moduleLabel?: string;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

function formatTime(iso: string | null, lang: "zh" | "en"): string {
  if (!iso) return lang === "zh" ? "未开始" : "Not started";
  return new Date(iso).toLocaleTimeString(lang === "zh" ? "zh-CN" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function compactValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(compactValue).join(", ");
  if (isRecord(value)) return JSON.stringify(value);
  return "-";
}

function renderDetailPairs(detail: Record<string, unknown> | null | undefined) {
  if (!detail || Object.keys(detail).length === 0) return null;

  return (
    <div className="run-transcript-meta-grid">
      {Object.entries(detail).map(([key, value]) => (
        <div key={key} className="run-transcript-meta-item">
          <span>{key}</span>
          <strong>{compactValue(value)}</strong>
        </div>
      ))}
    </div>
  );
}

function renderBrief(brief: RunTranscriptBrief | null | undefined) {
  if (!brief) return null;

  return (
    <div className="run-transcript-brief-body">
      {brief.conclusion ? (
        <div className="run-transcript-brief-section">
          <span>结论</span>
          <p>{brief.conclusion}</p>
        </div>
      ) : null}
      {brief.files && brief.files.length > 0 ? (
        <div className="run-transcript-brief-section">
          <span>文件</span>
          <ul>
            {brief.files.map((file) => (
              <li key={file}>
                <code>{file}</code>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {brief.risks && brief.risks.length > 0 ? (
        <div className="run-transcript-brief-section">
          <span>风险</span>
          <div className="run-transcript-brief-badges">
            {brief.risks.map((risk) => (
              <strong key={`${risk.severity}-${risk.count}`}>{risk.severity}: {risk.count}</strong>
            ))}
          </div>
        </div>
      ) : null}
      {brief.next_steps && brief.next_steps.length > 0 ? (
        <div className="run-transcript-brief-section">
          <span>下一步</span>
          <ol>
            {brief.next_steps.map((step, index) => (
              <li key={`${index}-${step}`}>{step}</li>
            ))}
          </ol>
        </div>
      ) : null}
      {brief.notices && brief.notices.length > 0 ? (
        <div className="run-transcript-brief-section">
          <span>注意事项</span>
          <ul>
            {brief.notices.map((notice, index) => (
              <li key={`${index}-${notice}`}>{notice}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {brief.stats && Object.keys(brief.stats).length > 0 ? (
        <div className="run-transcript-brief-section">
          <span>执行统计</span>
          {renderDetailPairs(brief.stats)}
        </div>
      ) : null}
    </div>
  );
}

function TranscriptRowView({ row }: { row: RunTranscriptRow }) {
  return (
    <article className={`run-transcript-row row-${row.kind}`}>
      <div className={`run-transcript-dot ${row.state === "running" ? "is-running" : ""}`} />
      <div className="run-transcript-cardless">
        <div className="run-transcript-row-head">
          <strong>{row.label}</strong>
          <span>{new Date(row.timestamp).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
        </div>
        <p className="run-transcript-row-summary">{row.summary}</p>
        {row.kind === "tool" && row.resultSummary ? (
          <div className="run-transcript-result-block">
            <span>结果</span>
            <p>{row.resultSummary}</p>
            {row.resultDetail && Object.keys(row.resultDetail).length > 0 ? (
              <details className="run-transcript-detail">
                <summary>展开结果详情</summary>
                {renderDetailPairs(row.resultDetail)}
              </details>
            ) : null}
          </div>
        ) : null}
        {row.kind === "brief" ? renderBrief(row.brief) : null}
        {row.detail && row.kind !== "brief" ? (
          <details className="run-transcript-detail">
            <summary>{row.kind === "tool" ? "查看上下文" : "查看详情"}</summary>
            {renderDetailPairs(row.detail)}
          </details>
        ) : null}
      </div>
    </article>
  );
}

export function RunTranscript({ taskId, moduleLabel }: Props) {
  const { lang } = useLang();
  const events = useTaskEvents(taskId);
  const snapshot = useMemo(() => buildRunTranscript(events), [events]);

  if (!taskId) {
    return (
      <section className="run-transcript workspace-tab-page">
        <header className="workspace-tab-head">
          <h3>{lang === "zh" ? "执行流" : "Execution Run"}</h3>
          <p>{lang === "zh" ? "启动一次异步执行后，这里会显示逐行执行流。" : "Start an async run to see the line-by-line transcript here."}</p>
        </header>
      </section>
    );
  }

  return (
    <section className="run-transcript workspace-tab-page">
      <header className="run-transcript-header">
        <div>
          <span>{moduleLabel ? `${moduleLabel.toUpperCase()} workspace` : "Run Workspace"}</span>
          <h3>{lang === "zh" ? "执行转录流" : "Run Transcript"}</h3>
        </div>
        <div className={`run-transcript-status status-${snapshot.statusText.toLowerCase()}`}>
          <strong>{snapshot.statusText}</strong>
          <small>{taskId}</small>
        </div>
      </header>

      <section className="run-transcript-strip">
        <article>
          <span>{lang === "zh" ? "当前阶段" : "Current Stage"}</span>
          <strong>{snapshot.currentStage}</strong>
        </article>
        <article>
          <span>{lang === "zh" ? "开始时间" : "Started"}</span>
          <strong>{formatTime(snapshot.startedAt, lang)}</strong>
        </article>
        <article>
          <span>{lang === "zh" ? "完成时间" : "Completed"}</span>
          <strong>{formatTime(snapshot.completedAt, lang)}</strong>
        </article>
        <article>
          <span>{lang === "zh" ? "事件总数" : "Events"}</span>
          <strong>{snapshot.eventCount}</strong>
        </article>
      </section>

      <section className="run-transcript-body">
        {snapshot.rows.length === 0 ? (
          <p className="resource-empty">
            {lang === "zh" ? "执行已提交，正在等待首条运行消息..." : "Run submitted. Waiting for the first runtime message..."}
          </p>
        ) : (
          snapshot.rows.map((row) => <TranscriptRowView key={row.id} row={row} />)
        )}
      </section>
    </section>
  );
}
