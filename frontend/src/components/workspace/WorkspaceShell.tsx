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

  const latestRun = useMemo<ModuleRun | null>(() => {
    return state.moduleRuns.find((item) => item.taskSpaceId === taskSpace.id) ?? null;
  }, [state.moduleRuns, taskSpace.id]);

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

  return (
    <section className="workspace-shell">
      {state.panelState.topOpen ? (
        <div className="workspace-top">
          <div>
            <div className="text-xs tracking-[0.2em] text-scientific-700/70">{t("activeTask")}</div>
            <h3 className="font-display text-2xl text-ink">{taskSpace.name}</h3>
          </div>
          <div className="text-sm text-scientific-800/70">{taskSpace.jurisdiction} · {taskSpace.mode.toUpperCase()}</div>
        </div>
      ) : null}

      <div className="workspace-toolbar">
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
