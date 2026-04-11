import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
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
import type { RunOutput } from "./ModuleRunPanel";

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

const WORKSPACE_TABS: WorkspaceTopTab[] = [
  { id: "details", key: "workspaceTabDetails", closable: false },
  { id: "canvas", key: "workspaceTabCanvas", closable: true },
  { id: "docs", key: "workspaceTabDocs", closable: true },
  { id: "terminal", key: "workspaceTabTerminal", closable: true },
  { id: "report", key: "workspaceTabReport", closable: true }
];

const WORKSPACE_TAB_KEYWORDS: Record<WorkspaceTopTabId, string[]> = {
  details: ["details", "detail", "详情", "运行", "main"],
  canvas: ["canvas", "画布", "流程", "stage"],
  docs: ["doc", "docs", "文档", "资料"],
  terminal: ["terminal", "终端", "日志", "log"],
  report: ["report", "报告", "review", "交付"]
};

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

export function WorkspaceShell({ taskSpace }: WorkspaceShellProps) {
  const { t, lang } = useLang();
  const { state, dispatch } = useAppStore();
  const navigate = useNavigate();
  const gridRef = useRef<HTMLDivElement | null>(null);
  const [isResizing, setIsResizing] = useState(false);
  const [workspaceQuery, setWorkspaceQuery] = useState("");
  const [activeTab, setActiveTab] = useState<WorkspaceTopTabId>("details");
  const [openTabs, setOpenTabs] = useState<WorkspaceTopTabId[]>(["details", "canvas", "report"]);
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
    setOpenTabs(["details", "canvas", "report"]);
    setWorkspaceQuery("");
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

  const openTabByQuery = () => {
    const normalized = workspaceQuery.trim().toLowerCase();
    if (!normalized) return;
    const matched = WORKSPACE_TABS.find((tab) =>
      WORKSPACE_TAB_KEYWORDS[tab.id].some((keyword) => normalized.includes(keyword) || keyword.includes(normalized))
    );
    if (matched) {
      openTab(matched.id);
      setWorkspaceQuery("");
    }
  };

  const onWorkspaceQueryKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      openTabByQuery();
    }
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
    }
  };

  const renameTask = () => {
    const nextName = globalThis.prompt(t("tasksRenamePrompt"), taskSpace.name)?.trim();
    if (!nextName || nextName === taskSpace.name) return;
    dispatch({
      type: "rename_task_space",
      payload: {
        id: taskSpace.id,
        name: nextName,
        updatedAt: new Date().toISOString()
      }
    });
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
          <p>{t("workspaceTabReportDesc")}</p>
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
        {reportArtifacts.length > 0 ? (
          <section className="workspace-report-list">
            {reportArtifacts.map((artifact) => (
              <article key={artifact.id} className="workspace-report-item">
                <strong>{artifact.kind.toUpperCase()}</strong>
                <span>{toFileName(artifact.path)}</span>
              </article>
            ))}
          </section>
        ) : (
          <p className="resource-empty">{t("reportNoData")}</p>
        )}
        {responseChapters.length > 0 ? (
          <section className="workspace-report-chapters">
            {responseChapters.slice(0, 3).map((chapter, index) => (
              <article key={`${chapter.title}-${index}`} className="workspace-report-chapter">
                <strong>{chapter.title}</strong>
                <p>{chapter.content}</p>
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
          <div className="workspace-browser-search">
            <input
              value={workspaceQuery}
              onChange={(event) => setWorkspaceQuery(event.target.value)}
              onKeyDown={onWorkspaceQueryKeyDown}
              placeholder={t("workspaceTabSearchPlaceholder")}
            />
            <button className="pill-btn" onClick={openTabByQuery}>{t("workspaceTabSearchAction")}</button>
          </div>
          <div className="workspace-header-actions">
            <button className="pill-btn" onClick={renameTask}>{t("tasksRenameAction")}</button>
            <button
              className="pill-btn"
              onClick={() => dispatch({ type: "set_panel_state", payload: { topOpen: !state.panelState.topOpen } })}
            >
              {state.panelState.topOpen ? t("topCollapse") : t("topExpand")}
            </button>
            <button
              className="pill-btn"
              onClick={() => dispatch({ type: "set_panel_state", payload: { leftOpen: !state.panelState.leftOpen } })}
            >
              {state.panelState.leftOpen ? t("leftCollapse") : t("leftExpand")}
            </button>
            <button
              className="pill-btn"
              onClick={() => dispatch({ type: "set_panel_state", payload: { rightOpen: !state.panelState.rightOpen } })}
            >
              {state.panelState.rightOpen ? t("rightCollapse") : t("rightExpand")}
            </button>
          </div>
        </div>
      </header>

      {state.panelState.topOpen ? (
        <div className="workspace-header-metrics">
          <span className="workspace-data-chip">{taskSpace.jurisdiction}</span>
          <span className="workspace-data-chip">{taskSpace.mode.toUpperCase()}</span>
          <span className="workspace-data-chip">{taskSpace.module.toUpperCase()}</span>
          <span className="workspace-data-chip">{t("tasksStatRuns")}: {taskRuns.length}</span>
          <span className="workspace-data-chip">{t("copilotContextIssues")}: {taskIssues.length}</span>
          <span className="workspace-data-chip">{t("copilotContextEvidence")}: {taskEvidence.length}</span>
          <span className="workspace-data-chip">{t("copilotContextArtifacts")}: {taskArtifacts.length}</span>
        </div>
      ) : null}

      <div className={panelClass} ref={gridRef} style={{ gridTemplateColumns }}>
        {state.panelState.leftOpen ? (
          <ResourcePanel
            taskSpace={taskSpace}
            tabs={WORKSPACE_TABS.map((tab) => ({ id: tab.id, label: t(tab.key), closable: tab.closable }))}
            openTabs={openTabs}
            activeTab={activeTab}
            tabQuery={workspaceQuery}
            onTabQueryChange={setWorkspaceQuery}
            onTabQuerySubmit={openTabByQuery}
            onActivateTab={(tabId) => setActiveTab(tabId as WorkspaceTopTabId)}
            onOpenTab={(tabId) => openTab(tabId as WorkspaceTopTabId)}
            onCloseTab={(tabId) => closeTab(tabId as WorkspaceTopTabId)}
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
        {state.panelState.rightOpen ? <AssistantPanel taskSpace={taskSpace} /> : null}
      </div>
    </section>
  );
}
