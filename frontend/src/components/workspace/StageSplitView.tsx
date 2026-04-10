import { useMemo } from "react";
import type { ModuleRun, TaskSpace } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { extractInsight } from "../../lib/workspace";
import { ModuleRunPanel, type RunOutput } from "./ModuleRunPanel";

type StageSplitViewProps = {
  taskSpace: TaskSpace;
  onRunDone: (output: RunOutput) => void;
  latestRun: ModuleRun | null;
};

type PreviewChapter = {
  chapterNo?: number;
  title: string;
  content: string;
  riskLevel?: string;
  citations: string[];
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const toString = (value: unknown): string | undefined => (typeof value === "string" ? value : undefined);
const toFileName = (value: string): string => {
  const normalized = value.replace(/\\/g, "/");
  const chunks = normalized.split("/");
  return chunks[chunks.length - 1] || value;
};

const RECOMMENDED_PATH_LABEL: Record<string, { zh: string; en: string }> = {
  security_assessment: { zh: "安全评估路径", en: "Security Assessment Path" },
  scc_or_certification: { zh: "标准合同备案/认证路径", en: "SCC Filing / Certification Path" },
  exemption: { zh: "豁免路径", en: "Exemption Path" }
};

const readChapters = (response: unknown): PreviewChapter[] => {
  if (!isRecord(response) || !Array.isArray(response.chapters)) return [];
  return response.chapters
    .filter(isRecord)
    .map((item) => ({
      chapterNo: typeof item.chapter_no === "number" ? item.chapter_no : undefined,
      title: toString(item.title) ?? "未命名章节",
      content: toString(item.content) ?? "",
      riskLevel: toString(item.risk_level),
      citations: Array.isArray(item.citations)
        ? item.citations.filter((citation): citation is string => typeof citation === "string")
        : []
    }));
};

const readRegulations = (response: unknown): Array<{ title: string; article?: string; snippet?: string }> => {
  if (!isRecord(response) || !Array.isArray(response.regulations)) return [];
  return response.regulations
    .filter(isRecord)
    .map((item) => ({
      title: toString(item.title) ?? "Regulation",
      article: toString(item.article),
      snippet: toString(item.snippet)
    }));
};

export function StageSplitView({ taskSpace, onRunDone, latestRun }: StageSplitViewProps) {
  const { t, lang } = useLang();
  const copy = lang === "zh"
    ? {
      outputFilesTitle: "已生成文件",
      chapterTitle: "报告章节",
      regulationTitle: "相关法规依据",
      recommendedPathLabel: "建议路径"
    }
    : {
      outputFilesTitle: "Generated Files",
      chapterTitle: "Report Chapters",
      regulationTitle: "Relevant Legal Basis",
      recommendedPathLabel: "Suggested Path"
    };
  const insight = extractInsight(latestRun?.response);
  const reportFileName = insight.reportPath ? toFileName(insight.reportPath) : "";
  const recommendedPathLabel = insight.recommendedPath
    ? (RECOMMENDED_PATH_LABEL[insight.recommendedPath]?.[lang] ?? insight.recommendedPath)
    : "";
  const previewChapters = useMemo(() => readChapters(latestRun?.response), [latestRun?.response]);
  const previewRegulations = useMemo(() => readRegulations(latestRun?.response), [latestRun?.response]);

  return (
    <section className="stage-split" data-guide="workspace-center">
      <div className="stage-shell layout-split">
        <section className="stage-pane">
          <div className="stage-pane-head">
            <span>{t("runPanel")}</span>
          </div>
          <section className="plugin-view plugin-view-run">
            <ModuleRunPanel onRunDone={onRunDone} taskSpace={taskSpace} />
          </section>
        </section>

        <section className="stage-pane">
          <div className="stage-pane-head">
            <span>{t("resultPanel")}</span>
          </div>
          <section className="plugin-view">
            {latestRun ? (
              <>
                <div className="preview-meta">
                  <p>{t("fieldModule")}: {latestRun.module.toUpperCase()}</p>
                  <p>{t("fieldStatus")}: {latestRun.success ? t("statusSuccess") : t("statusFailed")}</p>
                  {reportFileName ? <p>{t("fieldReport")}: {reportFileName}</p> : null}
                  {insight.riskLevel ? <p>{t("fieldRisk")}: {insight.riskLevel}</p> : null}
                  {recommendedPathLabel ? <p>{copy.recommendedPathLabel}: {recommendedPathLabel}</p> : null}
                  {latestRun.error ? <p>{t("fieldError")}: {latestRun.error}</p> : null}
                </div>

                {Object.entries(insight.outputFiles).length > 0 ? (
                  <section className="preview-output-files">
                    <div className="runner-title">{copy.outputFilesTitle}</div>
                    {Object.entries(insight.outputFiles).map(([kind, path]) => (
                      <article key={`${kind}-${path}`} className="preview-output-item">
                        <strong>{kind}</strong>
                        <p>{toFileName(path)}</p>
                      </article>
                    ))}
                  </section>
                ) : null}

                {previewChapters.length > 0 ? (
                  <section className="preview-chapter-list">
                    <div className="runner-title">{copy.chapterTitle}</div>
                    {previewChapters.map((chapter, index) => (
                      <article key={`${chapter.chapterNo ?? index}-${chapter.title}`} className="preview-chapter-card">
                        <header>
                          <strong>
                            {chapter.chapterNo ? `第${chapter.chapterNo}章` : `章节 ${index + 1}`} · {chapter.title}
                          </strong>
                          {chapter.riskLevel ? (
                            <span className={`preview-risk-badge level-${chapter.riskLevel.toLowerCase()}`}>
                              {chapter.riskLevel}
                            </span>
                          ) : null}
                        </header>
                        {chapter.content ? <p>{chapter.content}</p> : <p className="resource-empty">该章节暂无内容。</p>}
                        {chapter.citations.length > 0 ? (
                          <div className="preview-citation-row">
                            {chapter.citations.map((citation) => (
                              <span key={citation} className="preview-citation-chip">{citation}</span>
                            ))}
                          </div>
                        ) : null}
                      </article>
                    ))}
                  </section>
                ) : null}

                {previewRegulations.length > 0 ? (
                  <section className="preview-regulation-list">
                    <div className="runner-title">{copy.regulationTitle}</div>
                    {previewRegulations.map((item, index) => (
                      <article key={`${item.title}-${item.article ?? ""}-${index}`} className="preview-regulation-item">
                        <strong>{item.title}{item.article ? ` · ${item.article}` : ""}</strong>
                        {item.snippet ? <p>{item.snippet}</p> : null}
                      </article>
                    ))}
                  </section>
                ) : null}
              </>
            ) : (
              <p className="resource-empty">{t("previewEmpty")}</p>
            )}
          </section>
        </section>
      </div>
    </section>
  );
}
