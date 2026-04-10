import { useMemo } from "react";
import { useAppStore } from "../../lib/app-store";
import type { ModuleRun, TaskSpace } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { extractArtifacts, extractConsistencyIssues, extractEvidenceHits } from "../../lib/workspace";
import { AssistantPanel } from "./AssistantPanel";
import { ResourcePanel } from "./ResourcePanel";
import { StageSplitView } from "./StageSplitView";
import type { RunOutput } from "./ModuleRunPanel";

type WorkspaceShellProps = {
  taskSpace: TaskSpace;
};

export function WorkspaceShell({ taskSpace }: WorkspaceShellProps) {
  const { t } = useLang();
  const { state, dispatch } = useAppStore();
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

  const panelClass = useMemo(() => {
    let cls = "workspace-grid ";
    cls += state.panelState.leftOpen ? "left-open " : "left-hide ";
    cls += state.panelState.rightOpen ? "right-open" : "right-hide";
    return cls;
  }, [state.panelState.leftOpen, state.panelState.rightOpen]);

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

  return (
    <section className={`workspace-shell workspace-style-${taskSpace.workspaceStyle}`}>
      <header className="workspace-header workspace-header-compact">
        <div className="workspace-header-left">
          <div className="workspace-header-title-row">
            <span className="workspace-kicker">{t("activeTask")}</span>
            <strong className="workspace-inline-title">{taskSpace.name}</strong>
          </div>
          <div className="workspace-chip-row">
            <span className="workspace-data-chip">{taskSpace.jurisdiction}</span>
            <span className="workspace-data-chip">{taskSpace.mode.toUpperCase()}</span>
            <span className="workspace-data-chip">{taskSpace.module.toUpperCase()}</span>
            {state.panelState.topOpen ? (
              <>
                <span className="workspace-data-chip">{t("tasksStatRuns")}: {taskRuns.length}</span>
                <span className="workspace-data-chip">{t("copilotContextIssues")}: {taskIssues.length}</span>
                <span className="workspace-data-chip">{t("copilotContextEvidence")}: {taskEvidence.length}</span>
                <span className="workspace-data-chip">{t("copilotContextArtifacts")}: {taskArtifacts.length}</span>
              </>
            ) : null}
          </div>
        </div>

        <div className="workspace-header-tabs">
          <button
            className={`tab-btn ${state.panelState.primaryPlugin === "run" ? "active" : ""}`}
            onClick={() => dispatch({ type: "set_panel_state", payload: { primaryPlugin: "run" } })}
          >
            {t("pluginRun")}
          </button>
          <button
            className={`tab-btn ${state.panelState.primaryPlugin === "preview" ? "active" : ""}`}
            onClick={() => dispatch({ type: "set_panel_state", payload: { primaryPlugin: "preview" } })}
          >
            {t("pluginPreview")}
          </button>
          <button
            className={`tab-btn ${state.panelState.primaryPlugin === "evidence" ? "active" : ""}`}
            onClick={() => dispatch({ type: "set_panel_state", payload: { primaryPlugin: "evidence" } })}
          >
            {t("pluginEvidence")}
          </button>
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
      </header>

      <div className={panelClass}>
        {state.panelState.leftOpen ? <ResourcePanel taskSpace={taskSpace} /> : null}

        <main className="pane center-pane">
          <StageSplitView taskSpace={taskSpace} onRunDone={onRunDone} latestRun={latestRun} />
        </main>

        {state.panelState.rightOpen ? <AssistantPanel taskSpace={taskSpace} /> : null}
      </div>
    </section>
  );
}
