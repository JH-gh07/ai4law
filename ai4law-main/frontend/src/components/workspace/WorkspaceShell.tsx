import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent
} from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "../../lib/app-store";
import type { ModuleRun, TaskSpace, WorkflowStepKey } from "../../lib/domain";
import { useLang } from "../../lib/language";
import {
  findTaskTemplate,
  getTaskTemplateInputHint,
  getTaskTemplateOutputHint,
  getTaskTemplateSubtitle,
  getTaskTemplateTitle
} from "../../lib/task-templates";
import { deriveWorkflowSteps } from "../../lib/workflow";
import { extractArtifacts, extractConsistencyIssues, extractEvidenceHits, extractInsight } from "../../lib/workspace";
import { AssistantPanel } from "./AssistantPanel";
import { ResourcePanel } from "./ResourcePanel";
import { StageSplitView } from "./StageSplitView";
import { WorkspacePromptModal } from "../common/WorkspacePromptModal";
import type { RunOutput } from "./ModuleRunPanel";
import { ChevronToggleIcon } from "../common/AppIcons";

type WorkspaceShellProps = {
  taskSpace: TaskSpace;
};

const LEFT_PANEL_MIN = 220;
const LEFT_PANEL_MAX = 520;
const RIGHT_PANEL_MIN = 260;
const RIGHT_PANEL_MAX = 560;
const CENTER_PANEL_MIN = 360;
const RESIZER_WIDTH = 10;
const REPORT_ARTIFACT_KINDS = new Set(["report", "html", "pdf", "docx", "md"]);

type WorkspaceTopTabId = "details" | "canvas" | "docs" | "terminal" | "report";
type WorkspaceTopTab = {
  id: WorkspaceTopTabId;
  key: "workspaceTabDetails" | "workspaceTabCanvas" | "workspaceTabDocs" | "workspaceTabTerminal" | "workspaceTabReport";
  closable: boolean;
};
type ResponseChapter = {
  title: string;
  content: string;
};

type ReportPreviewSection = {
  title: string;
  content: string;
};

const WORKSPACE_TABS: WorkspaceTopTab[] = [
  { id: "details", key: "workspaceTabDetails", closable: false },
  { id: "canvas", key: "workspaceTabCanvas", closable: true },
  { id: "docs", key: "workspaceTabDocs", closable: true },
  { id: "terminal", key: "workspaceTabTerminal", closable: true },
  { id: "report", key: "workspaceTabReport", closable: true }
];

const clamp = (value: number, min: number, max: number): number => Math.min(max, Math.max(min, value));

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const readString = (value: unknown): string | undefined => (typeof value === "string" ? value : undefined);
const toFileName = (value: string): string => {
  const normalized = value.replace(/\\/g, "/");
  const chunks = normalized.split("/");
  return chunks[chunks.length - 1] || value;
};

const readResponseChapters = (response: unknown): ResponseChapter[] => {
  if (!isRecord(response) || !Array.isArray(response.chapters)) return [];
  return response.chapters
    .filter(isRecord)
    .map((item) => ({
      title: readString(item.title) ?? "Untitled",
      content: readString(item.content) ?? ""
    }))
    .filter((item) => item.content.trim().length > 0);
};

const readStringList = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];

const buildFallbackPreviewSections = (response: unknown, lang: "zh" | "en"): ReportPreviewSection[] => {
  if (!isRecord(response)) return [];

  const result = isRecord(response.result) ? response.result : {};
  const sections: ReportPreviewSection[] = [];
  const pushSection = (title: string, lines: string[]) => {
    const cleaned = lines.map((item) => item.trim()).filter((item) => item.length > 0);
    if (cleaned.length === 0) return;
    sections.push({ title, content: cleaned.join("\n") });
  };

  const summary = readString(result.summary);
  if (summary) {
    sections.push({
      title: lang === "zh" ? "执行摘要" : "Executive Summary",
      content: summary
    });
  }

  const hitRules = readStringList(result.hit_rules);
  pushSection(
    lang === "zh" ? "命中规则与判断依据" : "Applied Rules and Basis",
    hitRules
  );

  const citations = Array.isArray(result.citations)
    ? result.citations
        .filter(isRecord)
        .map((item) => [readString(item.source), readString(item.article), readString(item.note)].filter(Boolean).join(" | "))
        .filter((item): item is string => item.trim().length > 0)
    : [];
  pushSection(
    lang === "zh" ? "引用法规与条文" : "Citations",
    citations
  );

  const nextActions = readStringList(result.next_actions);
  pushSection(
    lang === "zh" ? "建议下一步" : "Recommended Next Steps",
    nextActions.map((item, index) => `${index + 1}. ${item}`)
  );

  const consistencyIssues = readStringList(response.consistency_issues);
  pushSection(
    lang === "zh" ? "一致性提示" : "Consistency Notes",
    consistencyIssues
  );

  return sections;
};

export function WorkspaceShell({ taskSpace }: WorkspaceShellProps) {
  const { t, lang } = useLang();
  const { state, dispatch } = useAppStore();
  const navigate = useNavigate();
  const gridRef = useRef<HTMLDivElement | null>(null);
  const [isResizing, setIsResizing] = useState(false);
  const [renameDraft, setRenameDraft] = useState(taskSpace.name);
  const [renameModalOpen, setRenameModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<WorkspaceTopTabId>("details");
  const [openTabs, setOpenTabs] = useState<WorkspaceTopTabId[]>(["details", "report"]);
  const taskRuns = useMemo(
    () => state.moduleRuns.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.moduleRuns, taskSpace.id]
  );
  const taskIssues = useMemo(
    () => state.issues.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.issues, taskSpace.id]
  );
  const taskEvidence = useMemo(
    () => state.evidenceHits.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.evidenceHits, taskSpace.id]
  );
  const taskArtifacts = useMemo(
    () => state.artifacts.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.artifacts, taskSpace.id]
  );

  const latestRun = useMemo<ModuleRun | null>(() => {
    return taskRuns[0] ?? null;
  }, [taskRuns]);
  const taskTemplate = useMemo(() => findTaskTemplate(taskSpace.taskTemplateId), [taskSpace.taskTemplateId]);
  const workflowSteps = useMemo(
    () => deriveWorkflowSteps(taskSpace, latestRun, state.artifacts, state.evidenceHits, state.issues),
    [latestRun, state.artifacts, state.evidenceHits, state.issues, taskSpace]
  );
  const reportArtifacts = useMemo(
    () => taskArtifacts.filter((item) => REPORT_ARTIFACT_KINDS.has(item.kind.toLowerCase())),
    [taskArtifacts]
  );
  const responseInsight = useMemo(() => extractInsight(latestRun?.response), [latestRun?.response]);
  const responseChapters = useMemo(() => readResponseChapters(latestRun?.response), [latestRun?.response]);
  const reportPreviewSections = useMemo<ReportPreviewSection[]>(() => {
    if (responseChapters.length > 0) {
      return responseChapters.map((chapter) => ({ title: chapter.title, content: chapter.content }));
    }
    return buildFallbackPreviewSections(latestRun?.response, lang);
  }, [lang, latestRun?.response, responseChapters]);
  const terminalLines = useMemo(() => {
    const lines: string[] = [];
    lines.push(`[workspace] ${taskSpace.name} (${taskSpace.id})`);
    lines.push(`[module] ${taskSpace.module.toUpperCase()} · ${taskSpace.jurisdiction} · ${taskSpace.mode.toUpperCase()}`);
    lines.push(`[time] ${new Date(taskSpace.updatedAt).toLocaleString()}`);
    lines.push("");

    if (taskRuns.length === 0) {
      lines.push("[info] No module run yet. Start from Details tab.");
    } else {
      taskRuns.slice(0, 10).forEach((run) => {
        const at = run.finishedAt ?? run.startedAt;
        lines.push(
          `[run] ${new Date(at).toLocaleString()} ${run.module.toUpperCase()} ${run.success ? "SUCCESS" : "FAILED"}`
        );
        if (run.error) lines.push(`       error: ${run.error}`);
      });
    }

    if (taskIssues.length > 0) {
      lines.push("");
      lines.push(`[issue] total=${taskIssues.length}`);
      taskIssues.slice(0, 6).forEach((item) => lines.push(`  - [${item.severity}] ${item.message}`));
    }
    if (taskEvidence.length > 0) {
      lines.push("");
      lines.push(`[evidence] total=${taskEvidence.length}`);
      taskEvidence.slice(0, 6).forEach((item) => lines.push(`  - ${item.title}`));
    }
    if (taskArtifacts.length > 0) {
      lines.push("");
      lines.push(`[artifact] total=${taskArtifacts.length}`);
      taskArtifacts.slice(0, 8).forEach((item) => lines.push(`  - ${item.kind}: ${toFileName(item.path)}`));
    }

    return lines.join("\n");
  }, [taskArtifacts, taskEvidence, taskIssues, taskRuns, taskSpace.id, taskSpace.jurisdiction, taskSpace.mode, taskSpace.module, taskSpace.name, taskSpace.updatedAt]);
  const closedTabs = useMemo(
    () => WORKSPACE_TABS.filter((item) => !openTabs.includes(item.id)),
    [openTabs]
  );
  const stepLabelMap: Record<WorkflowStepKey, string> = {
    input_validation: t("workflowInputValidation"),
    execution: t("workflowExecution"),
    evidence_binding: t("workflowEvidence"),
    consistency_check: t("workflowConsistency"),
    report_export: t("workflowExport")
  };
  const statusLabelMap = {
    pending: t("workflowPending"),
    running: t("workflowRunning"),
    blocked: t("workflowBlocked"),
    done: t("workflowDone")
  } as const;

  const panelClass = useMemo(() => {
    let cls = "workspace-grid ";
    cls += state.panelState.leftOpen ? "left-open " : "left-hide ";
    cls += state.panelState.rightOpen ? "right-open" : "right-hide";
    if (isResizing) cls += " is-resizing";
    return cls;
  }, [isResizing, state.panelState.leftOpen, state.panelState.rightOpen]);

  const gridTemplateColumns = useMemo(() => {
    if (state.panelState.leftOpen && state.panelState.rightOpen) {
      return `${state.panelState.leftWidth}px ${RESIZER_WIDTH}px minmax(0, 1fr) ${RESIZER_WIDTH}px ${state.panelState.rightWidth}px`;
    }
    if (state.panelState.leftOpen) {
      return `${state.panelState.leftWidth}px ${RESIZER_WIDTH}px minmax(0, 1fr)`;
    }
    if (state.panelState.rightOpen) {
      return `minmax(0, 1fr) ${RESIZER_WIDTH}px ${state.panelState.rightWidth}px`;
    }
    return "minmax(0, 1fr)";
  }, [
    state.panelState.leftOpen,
    state.panelState.leftWidth,
    state.panelState.rightOpen,
    state.panelState.rightWidth
  ]);

  useEffect(() => {
    setActiveTab("details");
    setOpenTabs(["details", "report"]);
    setRenameDraft(taskSpace.name);
    setRenameModalOpen(false);
  }, [taskSpace.id]);

  const openTab = (tabId: WorkspaceTopTabId) => {
    setOpenTabs((prev) => (prev.includes(tabId) ? prev : [...prev, tabId]));
    setActiveTab(tabId);
  };

  const closeTab = (tabId: WorkspaceTopTabId) => {
    if (tabId === "details") return;
    setOpenTabs((prev) => {
      if (!prev.includes(tabId)) return prev;
      const idx = prev.indexOf(tabId);
      const next = prev.filter((item) => item !== tabId);
      setActiveTab((current) => {
        if (current !== tabId) return current;
        const fallback = next[idx] ?? next[idx - 1] ?? "details";
        return fallback;
      });
      return next;
    });
  };

  const startResize = (side: "left" | "right", startX: number) => {
    const gridWidth = gridRef.current?.getBoundingClientRect().width ?? 0;
    if (!gridWidth) return;

    setIsResizing(true);
    const startLeftWidth = state.panelState.leftWidth;
    const startRightWidth = state.panelState.rightWidth;

    const maxLeftByCenter =
      gridWidth
      - (state.panelState.rightOpen ? state.panelState.rightWidth : 0)
      - CENTER_PANEL_MIN
      - (state.panelState.rightOpen ? RESIZER_WIDTH * 2 : RESIZER_WIDTH);
    const maxRightByCenter =
      gridWidth
      - (state.panelState.leftOpen ? state.panelState.leftWidth : 0)
      - CENTER_PANEL_MIN
      - (state.panelState.leftOpen ? RESIZER_WIDTH * 2 : RESIZER_WIDTH);

    const handlePointerMove = (event: PointerEvent) => {
      const delta = event.clientX - startX;
      if (side === "left") {
        const maxWidth = clamp(maxLeftByCenter, LEFT_PANEL_MIN, LEFT_PANEL_MAX);
        const nextLeftWidth = clamp(startLeftWidth + delta, LEFT_PANEL_MIN, maxWidth);
        dispatch({ type: "set_panel_state", payload: { leftWidth: nextLeftWidth } });
      } else {
        const maxWidth = clamp(maxRightByCenter, RIGHT_PANEL_MIN, RIGHT_PANEL_MAX);
        const nextRightWidth = clamp(startRightWidth - delta, RIGHT_PANEL_MIN, maxWidth);
        dispatch({ type: "set_panel_state", payload: { rightWidth: nextRightWidth } });
      }
    };

    const stopPointerMove = () => {
      setIsResizing(false);
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopPointerMove);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopPointerMove);
  };

  const onLeftResizerPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    startResize("left", event.clientX);
  };

  const onRightResizerPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    startResize("right", event.clientX);
  };

  const onRunDone = (output: RunOutput) => {
    const now = new Date().toISOString();
    const run: ModuleRun = {
      id: `${output.module}-${now}`,
      taskSpaceId: taskSpace.id,
      module: output.module,
      runMode: output.runMode,
      startedAt: now,
      finishedAt: now,
      success: output.success,
      request: output.request,
      response: output.response,
      error: output.error,
      asyncTaskId: output.asyncTaskId,
      asyncState: output.asyncState
    };

    dispatch({ type: "append_run", payload: run });
    dispatch({ type: "touch_task_space", payload: { id: taskSpace.id, updatedAt: now } });

    if (output.response) {
      dispatch({ type: "append_artifacts", payload: extractArtifacts(taskSpace.id, output.module, output.response) });
      dispatch({ type: "append_evidence", payload: extractEvidenceHits(taskSpace.id, output.module, output.response) });
      dispatch({ type: "append_issues", payload: extractConsistencyIssues(taskSpace.id, output.module, output.response) });
      setOpenTabs((prev) => (prev.includes("report") ? prev : [...prev, "report"]));
      setActiveTab("report");
    }
  };

  const renameTask = () => {
    setRenameDraft(taskSpace.name);
    setRenameModalOpen(true);
  };

  const submitRenameTask = () => {
    const nextName = renameDraft.trim();
    if (!nextName || nextName === taskSpace.name) {
      setRenameModalOpen(false);
      return;
    }
    dispatch({
      type: "rename_task_space",
      payload: {
        id: taskSpace.id,
        name: nextName,
        updatedAt: new Date().toISOString()
      }
    });
    setRenameModalOpen(false);
  };

  const renderTabSurface = () => {
    if (activeTab === "details") {
      return <StageSplitView taskSpace={taskSpace} onRunDone={onRunDone} latestRun={latestRun} />;
    }

    if (activeTab === "canvas") {
      return (
        <section className="workspace-tab-page workspace-tab-canvas">
          <header className="workspace-tab-head">
            <h3>{t("workspaceTabCanvasTitle")}</h3>
            <p>{t("workspaceTabCanvasDesc")}</p>
          </header>
          <section className="workspace-canvas-flow">
            {workflowSteps.map((step) => (
              <article key={step.key} className={`workspace-canvas-step step-${step.status}`}>
                <strong>{stepLabelMap[step.key]}</strong>
                <span>{statusLabelMap[step.status]}</span>
                <p>{step.reason ?? t("workflowNoReason")}</p>
              </article>
            ))}
          </section>
          <section className="workspace-canvas-metrics">
            <article className="workspace-canvas-metric">
              <span>{t("tasksStatRuns")}</span>
              <strong>{taskRuns.length}</strong>
            </article>
            <article className="workspace-canvas-metric">
              <span>{t("copilotContextIssues")}</span>
              <strong>{taskIssues.length}</strong>
            </article>
            <article className="workspace-canvas-metric">
              <span>{t("copilotContextEvidence")}</span>
              <strong>{taskEvidence.length}</strong>
            </article>
            <article className="workspace-canvas-metric">
              <span>{t("copilotContextArtifacts")}</span>
              <strong>{taskArtifacts.length}</strong>
            </article>
          </section>
        </section>
      );
    }

    if (activeTab === "docs") {
      return (
        <section className="workspace-tab-page workspace-tab-docs">
          <header className="workspace-tab-head">
            <h3>{t("workspaceTabDocsTitle")}</h3>
            <p>{t("workspaceTabDocsDesc")}</p>
          </header>
          <section className="workspace-doc-brief">
            <article>
              <strong>{t("taskTemplateLabel")}</strong>
              <p>{taskTemplate ? getTaskTemplateTitle(taskTemplate, lang) : taskSpace.module.toUpperCase()}</p>
            </article>
            <article>
              <strong>{t("moduleInputLabel")}</strong>
              <p>{taskTemplate ? getTaskTemplateInputHint(taskTemplate, lang) : "-"}</p>
            </article>
            <article>
              <strong>{t("moduleOutputLabel")}</strong>
              <p>{taskTemplate ? getTaskTemplateOutputHint(taskTemplate, lang) : "-"}</p>
            </article>
            <article>
              <strong>{t("workspaceUpdatedAt")}</strong>
              <p>{new Date(taskSpace.updatedAt).toLocaleString()}</p>
            </article>
          </section>
          <section className="workspace-doc-list">
            {taskArtifacts.length > 0 ? (
              taskArtifacts.map((artifact) => (
                <article key={artifact.id} className="workspace-doc-item">
                  <strong>{artifact.kind.toUpperCase()}</strong>
                  <span>{toFileName(artifact.path)}</span>
                </article>
              ))
            ) : (
              <p className="resource-empty">{t("noArtifacts")}</p>
            )}
          </section>
        </section>
      );
    }

    if (activeTab === "terminal") {
      return (
        <section className="workspace-tab-page workspace-tab-terminal">
          <header className="workspace-tab-head">
            <h3>{t("workspaceTabTerminalTitle")}</h3>
            <p>{t("workspaceTabTerminalDesc")}</p>
          </header>
          <section className="workspace-terminal-shell">
            <pre className="workspace-terminal-log">{terminalLines}</pre>
          </section>
        </section>
      );
    }

    return (
      <section className="workspace-tab-page workspace-tab-report">
        <header className="workspace-tab-head">
          <h3>{t("workspaceTabReportTitle")}</h3>
          <p>{reportPreviewSections.length > 0 ? (lang === "zh" ? "报告生成完成后会自动进入这里，优先展示可直接阅读的正文内容，再附带导出文件。" : "Generated reports land here automatically with readable in-page content before exported files.") : t("workspaceTabReportDesc")}</p>
        </header>
        <section className="workspace-report-kpi-row">
          <article>
            <span>{t("reportIssueCount")}</span>
            <strong>{taskIssues.length}</strong>
          </article>
          <article>
            <span>{t("reportEvidenceCount")}</span>
            <strong>{taskEvidence.length}</strong>
          </article>
          <article>
            <span>{t("reportDownloadHint")}</span>
            <strong>{reportArtifacts.length}</strong>
          </article>
          <article>
            <span>{t("fieldRisk")}</span>
            <strong>{responseInsight.riskLevel ?? t("workflowPending")}</strong>
          </article>
        </section>
        {reportPreviewSections.length > 0 ? (
          <section className="workspace-report-chapters">
            {reportPreviewSections.map((section, index) => (
              <article key={`${section.title}-${index}`} className="workspace-report-chapter workspace-report-preview-block">
                <strong>{section.title}</strong>
                <div className="workspace-report-richtext">
                  {section.content
                    .split("\n")
                    .filter((line) => line.trim().length > 0)
                    .map((line, lineIndex) => (
                      <p key={`${section.title}-${lineIndex}`}>{line}</p>
                    ))}
                </div>
              </article>
            ))}
          </section>
        ) : (
          <p className="resource-empty">{t("reportNoData")}</p>
        )}
        {reportArtifacts.length > 0 ? (
          <section className="workspace-report-list">
            {reportArtifacts.map((artifact) => (
              <article key={artifact.id} className="workspace-report-item">
                <strong>{artifact.kind.toUpperCase()}</strong>
                <span>{toFileName(artifact.path)}</span>
              </article>
            ))}
          </section>
        ) : null}
      </section>
    );
  };

  return (
    <section className={`workspace-shell workspace-style-${taskSpace.workspaceStyle}`}>
      <header className="workspace-header workspace-header-compact">
        <div className="workspace-browser-left">
          <button
            type="button"
            className="workspace-browser-app workspace-browser-app-link"
            onClick={() => navigate("/")}
            aria-label={t("navHome")}
          >
            AI4Law
          </button>
          <span className="workspace-browser-sep">/</span>
          <span className="workspace-browser-task">{taskSpace.name}</span>
          <span className="workspace-browser-sep">/</span>
          <span className="workspace-browser-module">{taskTemplate ? getTaskTemplateSubtitle(taskTemplate, lang) : taskSpace.module.toUpperCase()}</span>
        </div>

        <div className="workspace-browser-tabs">
          {openTabs.map((tabId) => {
            const tab = WORKSPACE_TABS.find((item) => item.id === tabId);
            if (!tab) return null;
            return (
              <button
                key={tab.id}
                className={`workspace-browser-tab ${activeTab === tab.id ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span>{t(tab.key)}</span>
                {tab.closable ? (
                  <span
                    className="workspace-browser-tab-close"
                    role="button"
                    aria-label={`close-${tab.id}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      closeTab(tab.id);
                    }}
                  >
                    ×
                  </span>
                ) : null}
              </button>
            );
          })}
          {closedTabs.map((tab) => (
            <button
              key={`add-${tab.id}`}
              className="workspace-browser-tab-add"
              onClick={() => openTab(tab.id)}
            >
              + {t(tab.key)}
            </button>
          ))}
        </div>

        <div className="workspace-browser-actions">
          <div className="workspace-header-actions">
            <button className="pill-btn" onClick={renameTask}>{t("tasksRenameAction")}</button>
          </div>
        </div>
      </header>

      <div className={panelClass} ref={gridRef} style={{ gridTemplateColumns }}>
        {state.panelState.leftOpen ? (
          <ResourcePanel
            taskSpace={taskSpace}
            onToggleCollapse={() => dispatch({ type: "set_panel_state", payload: { leftOpen: false } })}
          />
        ) : null}
        {state.panelState.leftOpen ? (
          <div
            className="workspace-resizer workspace-resizer-left"
            role="separator"
            aria-orientation="vertical"
            onPointerDown={onLeftResizerPointerDown}
          />
        ) : null}

        <main className="pane center-pane">
          {!state.panelState.leftOpen ? (
            <button
              className="workspace-floating-toggle workspace-floating-toggle-left"
              onClick={() => dispatch({ type: "set_panel_state", payload: { leftOpen: true } })}
              aria-label="expand-left-sidebar"
            >
              <ChevronToggleIcon direction="right" width="16" height="16" />
            </button>
          ) : null}
          {!state.panelState.rightOpen ? (
            <button
              className="workspace-floating-toggle workspace-floating-toggle-right"
              onClick={() => dispatch({ type: "set_panel_state", payload: { rightOpen: true } })}
              aria-label="expand-right-sidebar"
            >
              <ChevronToggleIcon direction="left" width="16" height="16" />
            </button>
          ) : null}
          {renderTabSurface()}
        </main>

        {state.panelState.rightOpen ? (
          <div
            className="workspace-resizer workspace-resizer-right"
            role="separator"
            aria-orientation="vertical"
            onPointerDown={onRightResizerPointerDown}
          />
        ) : null}
        {state.panelState.rightOpen ? (
          <AssistantPanel
            taskSpace={taskSpace}
            onToggleCollapse={() => dispatch({ type: "set_panel_state", payload: { rightOpen: false } })}
          />
        ) : null}
      </div>

      <WorkspacePromptModal
        open={renameModalOpen}
        title={t("tasksRenameTitle")}
        description={t("tasksRenameDesc")}
        valueLabel={t("tasksNameField")}
        value={renameDraft}
        valuePlaceholder={t("tasksRenamePrompt")}
        onValueChange={setRenameDraft}
        confirmText={t("tasksRenameConfirmAction")}
        cancelText={t("cancelBtn")}
        confirmDisabled={renameDraft.trim().length === 0}
        onCancel={() => setRenameModalOpen(false)}
        onConfirm={submitRenameTask}
      />
    </section>
  );
}
