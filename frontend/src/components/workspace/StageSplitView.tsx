import { useMemo } from "react";
import type { ModuleRun, TaskSpace } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { findTaskTemplate, getTaskTemplateInputHint, getTaskTemplateOutputHint } from "../../lib/task-templates";
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

type WorkspaceBlueprint = {
  process: string[];
  checklist: string[];
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

const BLUEPRINTS: Record<
  string,
  { zh: WorkspaceBlueprint; en: WorkspaceBlueprint }
> = {
  cn_diagnosis: {
    zh: {
      process: [
        "先做法定门槛与豁免判断，再进入强制评估触发项。",
        "无法直接二选一时，输出“标准合同/认证”并进入二次分流。",
        "输出建议路径、理由摘要与下一步动作清单。"
      ],
      checklist: [
        "是否完成重要数据判断",
        "是否完成豁免情形核验",
        "是否完成人数门槛确认"
      ]
    },
    en: {
      process: [
        "Complete exemption and threshold diagnosis before route decision.",
        "Return SCC/certification bundle when direct split is unavailable.",
        "Output path recommendation, rationale summary, and next actions."
      ],
      checklist: [
        "Important data check completed",
        "Exemption checks completed",
        "Volume thresholds confirmed"
      ]
    }
  },
  cn_assessment: {
    zh: {
      process: [
        "采集主体信息、自评估过程、场景、数据清单与链路材料。",
        "执行一致性校验（场景-数据项-接收方-法律文件映射）。",
        "按章节输出《数据出境风险自评估报告》草案。"
      ],
      checklist: [
        "主体信息是否完整",
        "数据项是否完成场景内去重",
        "链路与接收方是否可追溯"
      ]
    },
    en: {
      process: [
        "Collect entity profile, assessment process, scenarios, datasets, and transfer chain evidence.",
        "Run consistency checks across scenario-data-recipient-legal mappings.",
        "Generate a chaptered risk self-assessment draft report."
      ],
      checklist: [
        "Entity profile completed",
        "Dataset deduplicated by scenario",
        "Transfer chain and recipient traceable"
      ]
    }
  },
  cn_pipia: {
    zh: {
      process: [
        "围绕处理活动与跨境说明构建 PIPIA 事实基础。",
        "识别个人信息种类、敏感程度、权利保障与应急机制。",
        "输出《个人信息保护影响评估（PIPIA）》草案。"
      ],
      checklist: [
        "处理者与接收方信息是否齐全",
        "个人信息与敏感信息范围是否明确",
        "告知、同意、DSAR 与应急机制是否覆盖"
      ]
    },
    en: {
      process: [
        "Build PIPIA evidence base from processing and transfer context.",
        "Assess PI categories, sensitivity, rights safeguards, and incident readiness.",
        "Generate a structured PIPIA draft for review."
      ],
      checklist: [
        "Controller and recipient details complete",
        "PI and SPI scope clarified",
        "Notice/consent/DSAR/emergency mechanisms covered"
      ]
    }
  },
  cn_document_review: {
    zh: {
      process: [
        "上传合同或政策文本并补充审查范围。",
        "自动抽取条款并标注高/中/低风险问题。",
        "输出文档合规审查结论、问题清单与修订建议。"
      ],
      checklist: [
        "文档版本与适用范围是否明确",
        "是否包含出境告知与权利条款",
        "是否存在高风险缺失条款"
      ]
    },
    en: {
      process: [
        "Upload contract/policy text and define review scope.",
        "Extract clauses and classify high/medium/low risks.",
        "Output compliance review conclusion, issue list, and remediation advice."
      ],
      checklist: [
        "Document version and scope identified",
        "Transfer notice and rights clauses present",
        "High-risk gaps detected"
      ]
    }
  }
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
  const taskTemplate = useMemo(() => findTaskTemplate(taskSpace.taskTemplateId), [taskSpace.taskTemplateId]);
  const blueprint = useMemo<WorkspaceBlueprint | null>(() => {
    if (!taskTemplate) return null;
    return BLUEPRINTS[taskTemplate.id]?.[lang] ?? null;
  }, [lang, taskTemplate]);
  const copy = lang === "zh"
    ? {
      outputFilesTitle: "已生成文件",
      chapterTitle: "报告章节",
      regulationTitle: "相关法规依据",
      recommendedPathLabel: "建议路径",
      inputTitle: "任务输入",
      processTitle: "处理逻辑",
      outputTitle: "任务输出",
      checklistTitle: "核验清单"
    }
    : {
      outputFilesTitle: "Generated Files",
      chapterTitle: "Report Chapters",
      regulationTitle: "Relevant Legal Basis",
      recommendedPathLabel: "Suggested Path",
      inputTitle: "Task Input",
      processTitle: "Processing Logic",
      outputTitle: "Task Output",
      checklistTitle: "Checklist"
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
      {taskTemplate ? (
        <section className="workspace-task-blueprint">
          <article className="workspace-task-blueprint-card">
            <strong>{copy.inputTitle}</strong>
            <p>{getTaskTemplateInputHint(taskTemplate, lang)}</p>
          </article>
          <article className="workspace-task-blueprint-card">
            <strong>{copy.processTitle}</strong>
            <ul>
              {(blueprint?.process ?? []).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
          <article className="workspace-task-blueprint-card">
            <strong>{copy.outputTitle}</strong>
            <p>{getTaskTemplateOutputHint(taskTemplate, lang)}</p>
            {(blueprint?.checklist?.length ?? 0) > 0 ? (
              <>
                <div className="workspace-task-blueprint-subtitle">{copy.checklistTitle}</div>
                <ul>
                  {blueprint?.checklist.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            ) : null}
          </article>
        </section>
      ) : null}
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
