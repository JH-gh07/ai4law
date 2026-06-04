// frontend/src/components/workspace/RunBrief.tsx
import { useMemo } from "react";
import { useLang } from "../../lib/language";
import { useTaskEvents } from "../../lib/useTaskEvents";

type Props = {
  taskId: string | null;
};

type BriefDetail = {
  conclusion?: string;
  files?: string[];
  risks?: Array<{ severity: string; count: number }>;
  next_steps?: string[];
  stats?: Record<string, unknown>;
};

export function RunBrief({ taskId }: Props) {
  const { lang } = useLang();
  const events = useTaskEvents(taskId);

  const briefEvent = useMemo(() => {
    return events.find((e) => e.event_type === "final_brief") ?? null;
  }, [events]);

  const finalEvent = useMemo(() => {
    return events.find((e) => e.event_type === "final") ?? null;
  }, [events]);

  const brief: BriefDetail | null = (briefEvent?.detail as BriefDetail) ?? null;
  const isComplete = finalEvent !== null;

  if (!isComplete) {
    return (
      <section className="run-brief">
        <header className="workspace-tab-head">
          <h3>{lang === "zh" ? "结果简报" : "Run Brief"}</h3>
          <p>{lang === "zh" ? "等待执行完成..." : "Waiting for execution to complete..."}</p>
        </header>
      </section>
    );
  }

  return (
    <section className="run-brief">
      <header className="workspace-tab-head">
        <h3>{lang === "zh" ? "结果简报" : "Run Brief"}</h3>
        <p>{lang === "zh" ? "执行完成，以下是本次运行摘要。" : "Run complete. Summary below."}</p>
      </header>

      <div className="brief-sections">
        <article className="brief-section brief-conclusion">
          <h4>{lang === "zh" ? "📋 执行结论" : "📋 Conclusion"}</h4>
          <p>{brief?.conclusion ?? finalEvent?.summary ?? "-"}</p>
        </article>

        {brief?.files && brief.files.length > 0 && (
          <article className="brief-section brief-files">
            <h4>{lang === "zh" ? "📁 生成文件" : "📁 Generated Files"}</h4>
            <ul>
              {brief.files.map((f) => (
                <li key={f}>
                  <code>{f}</code>
                </li>
              ))}
            </ul>
          </article>
        )}

        {brief?.risks && brief.risks.length > 0 && (
          <article className="brief-section brief-risks">
            <h4>{lang === "zh" ? "⚠️ 风险提示" : "⚠️ Risk Summary"}</h4>
            <div className="brief-risk-badges">
              {brief.risks.map((r) => (
                <span key={r.severity} className={`risk-badge risk-${r.severity.toLowerCase()}`}>
                  {r.severity}: {r.count}
                </span>
              ))}
            </div>
          </article>
        )}

        {brief?.next_steps && brief.next_steps.length > 0 && (
          <article className="brief-section brief-next">
            <h4>{lang === "zh" ? "👉 建议下一步" : "👉 Recommended Next Steps"}</h4>
            <ol>
              {brief.next_steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          </article>
        )}

        {brief?.stats && (
          <article className="brief-section brief-stats">
            <h4>{lang === "zh" ? "📊 执行统计" : "📊 Execution Stats"}</h4>
            <div className="brief-stats-grid">
              {Object.entries(brief.stats).map(([key, value]) => (
                <div key={key} className="brief-stat-item">
                  <span className="brief-stat-label">{key}</span>
                  <strong>{String(value)}</strong>
                </div>
              ))}
            </div>
          </article>
        )}
      </div>
    </section>
  );
}
