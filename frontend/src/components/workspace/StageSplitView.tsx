import { useMemo } from "react";
import { useAppStore } from "../../lib/app-store";
import type { ModuleRun, TaskSpace, WorkflowStepKey, WorkflowStepStatus } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { deriveWorkflowSteps } from "../../lib/workflow";
import { extractInsight } from "../../lib/workspace";
import { ModuleRunPanel, type RunOutput } from "./ModuleRunPanel";

type StageSplitViewProps = {
  taskSpace: TaskSpace;
  onRunDone: (output: RunOutput) => void;
  latestRun: ModuleRun | null;
};

type StagePluginKey = "run" | "preview" | "evidence" | "timeline";

type TimelineEvent = {
  id: string;
  createdAt: string;
  title: string;
  detail: string;
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
  const { t } = useLang();
  const { state, dispatch } = useAppStore();

  const panelState = state.panelState;
  const insight = extractInsight(latestRun?.response);
  const previewChapters = useMemo(() => readChapters(latestRun?.response), [latestRun?.response]);
  const previewRegulations = useMemo(() => readRegulations(latestRun?.response), [latestRun?.response]);

  const evidence = useMemo(
    () => state.evidenceHits.filter((item) => item.taskSpaceId === taskSpace.id).slice(0, 30),
    [state.evidenceHits, taskSpace.id]
  );

  const artifacts = useMemo(
    () => state.artifacts.filter((item) => item.taskSpaceId === taskSpace.id).slice(0, 30),
    [state.artifacts, taskSpace.id]
  );

  const issues = useMemo(
    () => state.issues.filter((item) => item.taskSpaceId === taskSpace.id).slice(0, 30),
    [state.issues, taskSpace.id]
  );

  const runs = useMemo(
    () => state.moduleRuns.filter((item) => item.taskSpaceId === taskSpace.id).slice(0, 30),
    [state.moduleRuns, taskSpace.id]
  );

  const workflowSteps = useMemo(
    () => deriveWorkflowSteps(taskSpace, latestRun, state.artifacts, state.evidenceHits, state.issues),
    [latestRun, state.artifacts, state.evidenceHits, state.issues, taskSpace]
  );

  const activeStep = useMemo(
    () => workflowSteps.find((step) => step.status !== "done") ?? workflowSteps[workflowSteps.length - 1],
    [workflowSteps]
  );
  const activeStepIndex = useMemo(
    () => workflowSteps.findIndex((step) => step.key === activeStep?.key),
    [activeStep?.key, workflowSteps]
  );
  const workflowProgress = useMemo(() => {
    if (workflowSteps.length === 0 || activeStepIndex < 0) return 0;
    return ((activeStepIndex + 1) / workflowSteps.length) * 100;
  }, [activeStepIndex, workflowSteps.length]);

  const timeline = useMemo<TimelineEvent[]>(() => {
    const runEvents = runs.map((run) => ({
      id: `run-${run.id}`,
      createdAt: run.finishedAt ?? run.startedAt,
      title: run.success ? t("timelineRunSuccess") : t("timelineRunFailed"),
      detail: `${run.module.toUpperCase()} · ${run.success ? t("statusOk") : run.error ?? t("statusFail")}`
    }));

    const issueEvents = issues.map((issue) => ({
      id: `issue-${issue.id}`,
      createdAt: issue.createdAt,
      title: t("timelineIssue"),
      detail: `[${issue.module.toUpperCase()}] ${issue.message}`
    }));

    const artifactEvents = artifacts.map((artifact) => ({
      id: `artifact-${artifact.id}`,
      createdAt: artifact.createdAt,
      title: t("timelineArtifact"),
      detail: `${artifact.module.toUpperCase()} · ${artifact.kind} · ${artifact.path}`
    }));

    const evidenceEvents = evidence.map((hit) => ({
      id: `evidence-${hit.id}`,
      createdAt: hit.createdAt,
      title: t("timelineEvidence"),
      detail: `${hit.module.toUpperCase()} · ${hit.title}`
    }));

    return [...runEvents, ...issueEvents, ...artifactEvents, ...evidenceEvents]
      .sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1))
      .slice(0, 40);
  }, [runs, issues, artifacts, evidence, t]);

  const pluginMeta: Record<StagePluginKey, string> = {
    run: t("pluginRun"),
    preview: t("pluginPreview"),
    evidence: t("pluginEvidence"),
    timeline: t("pluginTimeline")
  };

  const workflowLabels: Record<WorkflowStepKey, string> = {
    input_validation: t("workflowInputValidation"),
    execution: t("workflowExecution"),
    evidence_binding: t("workflowEvidence"),
    consistency_check: t("workflowConsistency"),
    report_export: t("workflowExport")
  };

  const workflowStatusLabel: Record<WorkflowStepStatus, string> = {
    pending: t("workflowPending"),
    running: t("workflowRunning"),
    blocked: t("workflowBlocked"),
    done: t("workflowDone")
  };

  const setLayout = (layout: "split" | "single") => {
    dispatch({
      type: "set_panel_state",
      payload: {
        stageLayout: layout,
        focusMode:
          layout === "split"
            ? "split"
            : panelState.primaryPlugin === "run"
              ? "run"
              : "preview"
      }
    });
  };

  const setPreset = (preset: "operate" | "review" | "trace") => {
    if (preset === "operate") {
      dispatch({
        type: "set_panel_state",
        payload: {
          stageLayout: "split",
          primaryPlugin: "run",
          secondaryPlugin: "preview",
          focusMode: "split"
        }
      });
      return;
    }
    if (preset === "review") {
      dispatch({
        type: "set_panel_state",
        payload: {
          stageLayout: "split",
          primaryPlugin: "preview",
          secondaryPlugin: "evidence",
          focusMode: "split"
        }
      });
      return;
    }
    dispatch({
      type: "set_panel_state",
      payload: {
        stageLayout: "split",
        primaryPlugin: "evidence",
        secondaryPlugin: "timeline",
        focusMode: "split"
      }
    });
  };

  const renderPlugin = (plugin: StagePluginKey) => {
    if (plugin === "run") {
      return (
        <section className="plugin-view plugin-view-run">
          <ModuleRunPanel onRunDone={onRunDone} taskSpace={taskSpace} />
        </section>
      );
    }

    if (plugin === "preview") {
      return (
        <section className="plugin-view">
          <div className="runner-title">{t("resultPanel")}</div>
          {latestRun ? (
            <>
              <div className="preview-meta">
                <p>{t("fieldModule")}: {latestRun.module.toUpperCase()}</p>
                <p>{t("fieldStatus")}: {latestRun.success ? t("statusSuccess") : t("statusFailed")}</p>
                {insight.reportPath ? <p>{t("fieldReport")}: <code>{insight.reportPath}</code></p> : null}
                {insight.riskLevel ? <p>{t("fieldRisk")}: {insight.riskLevel}</p> : null}
                {insight.recommendedPath ? <p>{t("fieldPath")}: {insight.recommendedPath}</p> : null}
                {latestRun.error ? <p>{t("fieldError")}: {latestRun.error}</p> : null}
              </div>

              {Object.entries(insight.outputFiles).length > 0 ? (
                <section className="preview-output-files">
                  <div className="runner-title">Output Files</div>
                  {Object.entries(insight.outputFiles).map(([kind, path]) => (
                    <article key={`${kind}-${path}`} className="preview-output-item">
                      <strong>{kind}</strong>
                      <code>{path}</code>
                    </article>
                  ))}
                </section>
              ) : null}

              {previewChapters.length > 0 ? (
                <section className="preview-chapter-list">
                  <div className="runner-title">Chapters</div>
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
                            <code key={citation}>{citation}</code>
                          ))}
                        </div>
                      ) : null}
                    </article>
                  ))}
                </section>
              ) : null}

              {previewRegulations.length > 0 ? (
                <section className="preview-regulation-list">
                  <div className="runner-title">Regulation Hits</div>
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
      );
    }

    if (plugin === "evidence") {
      return (
        <section className="plugin-view">
          <div className="runner-title">{t("evidencePanel")}</div>
          <div className="preview-evidence-list">
            {evidence.map((hit) => (
              <article key={hit.id} className="preview-evidence-item">
                <strong>{hit.title}</strong>
                <p>{hit.snippet}</p>
              </article>
            ))}
            {evidence.length === 0 ? <p className="resource-empty">{t("evidenceEmpty")}</p> : null}
          </div>
        </section>
      );
    }

    return (
      <section className="plugin-view">
        <div className="runner-title">{t("pluginTimeline")}</div>
        <div className="timeline-list">
          {timeline.map((event) => (
            <article key={event.id} className="timeline-item">
              <small>{new Date(event.createdAt).toLocaleString()}</small>
              <strong>{event.title}</strong>
              <p>{event.detail}</p>
            </article>
          ))}
          {timeline.length === 0 ? <p className="resource-empty">{t("timelineEmpty")}</p> : null}
        </div>
      </section>
    );
  };

  const pluginKeys: StagePluginKey[] = ["run", "preview", "evidence", "timeline"];

  return (
    <section className="stage-split" data-guide="workspace-center">
      <section className="workflow-strip">
        <header className="workflow-strip-head">
          <div>
            <div className="pane-title">{t("workflowTitle")}</div>
            <div className="workflow-progress-text">
              {t("workflowProgress")} {Math.max(activeStepIndex + 1, 0)} / {workflowSteps.length}
            </div>
          </div>
          <div className={`workflow-status-pill ${activeStep?.status ?? "pending"}`}>
            {activeStep ? `${workflowLabels[activeStep.key]} · ${workflowStatusLabel[activeStep.status]}` : t("workflowPending")}
          </div>
        </header>
        <div className="workflow-progress-track">
          <span style={{ width: `${workflowProgress}%` }} />
        </div>
        <div className="workflow-step-grid">
          {workflowSteps.map((step) => (
            <article key={step.key} className={`workflow-step-card ${step.status}`}>
              <strong>{workflowLabels[step.key]}</strong>
              <span>{workflowStatusLabel[step.status]}</span>
              <p>{step.reason ?? t("workflowNoReason")}</p>
            </article>
          ))}
        </div>
      </section>

      <div className="stage-toolbar">
        <div className="pane-title">{t("centerTitle")}</div>
        <div className="stage-preset-tabs">
          <button className="pill-btn" onClick={() => setPreset("operate")}>{t("stagePresetOperate")}</button>
          <button className="pill-btn" onClick={() => setPreset("review")}>{t("stagePresetReview")}</button>
          <button className="pill-btn" onClick={() => setPreset("trace")}>{t("stagePresetTrace")}</button>
        </div>
        <div className="stage-layout-actions">
          <button className="pill-btn" onClick={() => setLayout("split")}>{t("splitMode")}</button>
          <button className="pill-btn" onClick={() => setLayout("single")}>{t("singleMode")}</button>
          <button
            className="pill-btn"
            onClick={() =>
              dispatch({
                type: "set_panel_state",
                payload: {
                  primaryPlugin: panelState.secondaryPlugin,
                  secondaryPlugin: panelState.primaryPlugin
                }
              })
            }
          >
            {t("swapMode")}
          </button>
        </div>
      </div>

      <div className={`stage-shell ${panelState.stageLayout === "split" ? "layout-split" : "layout-single"}`}>
        <section className="stage-pane">
          <div className="stage-pane-head">
            <span>{t("primaryPane")}</span>
            <div className="plugin-tabs">
              {pluginKeys.map((pluginKey) => (
                <button
                  key={`primary-${pluginKey}`}
                  className={`tab-btn ${panelState.primaryPlugin === pluginKey ? "active" : ""}`}
                  onClick={() =>
                    dispatch({ type: "set_panel_state", payload: { primaryPlugin: pluginKey } })
                  }
                >
                  {pluginMeta[pluginKey]}
                </button>
              ))}
            </div>
          </div>
          {renderPlugin(panelState.primaryPlugin)}
        </section>

        {panelState.stageLayout === "split" ? (
          <section className="stage-pane">
            <div className="stage-pane-head">
              <span>{t("secondaryPane")}</span>
              <div className="plugin-tabs">
                {pluginKeys.map((pluginKey) => (
                  <button
                    key={`secondary-${pluginKey}`}
                    className={`tab-btn ${panelState.secondaryPlugin === pluginKey ? "active" : ""}`}
                    onClick={() =>
                      dispatch({ type: "set_panel_state", payload: { secondaryPlugin: pluginKey } })
                    }
                  >
                    {pluginMeta[pluginKey]}
                  </button>
                ))}
              </div>
            </div>
            {renderPlugin(panelState.secondaryPlugin)}
          </section>
        ) : null}
      </div>
    </section>
  );
}
