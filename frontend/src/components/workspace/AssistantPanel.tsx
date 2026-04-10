import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "../../lib/app-store";
import type { TaskSpace } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { deriveWorkflowSteps } from "../../lib/workflow";

type AssistantPanelProps = {
  taskSpace: TaskSpace;
};

type StreamItem = {
  id: string;
  createdAt: string;
  title: string;
  detail: string;
};

export function AssistantPanel({ taskSpace }: AssistantPanelProps) {
  const { t } = useLang();
  const navigate = useNavigate();
  const { state, dispatch } = useAppStore();
  const [command, setCommand] = useState("");
  const [localLogs, setLocalLogs] = useState<StreamItem[]>([]);

  const issues = useMemo(
    () => state.issues.filter((item) => item.taskSpaceId === taskSpace.id).slice(0, 12),
    [state.issues, taskSpace.id]
  );

  const runs = useMemo(
    () => state.moduleRuns.filter((item) => item.taskSpaceId === taskSpace.id).slice(0, 12),
    [state.moduleRuns, taskSpace.id]
  );

  const artifacts = useMemo(
    () => state.artifacts.filter((item) => item.taskSpaceId === taskSpace.id).slice(0, 12),
    [state.artifacts, taskSpace.id]
  );

  const latestRun = useMemo(
    () => state.moduleRuns.find((item) => item.taskSpaceId === taskSpace.id) ?? null,
    [state.moduleRuns, taskSpace.id]
  );

  const workflowSteps = useMemo(
    () => deriveWorkflowSteps(taskSpace, latestRun, state.artifacts, state.evidenceHits, state.issues),
    [latestRun, state.artifacts, state.evidenceHits, state.issues, taskSpace]
  );
  const currentStep = workflowSteps.find((step) => step.status !== "done") ?? workflowSteps[workflowSteps.length - 1];
  const stepLabelMap = {
    input_validation: t("workflowInputValidation"),
    execution: t("workflowExecution"),
    evidence_binding: t("workflowEvidence"),
    consistency_check: t("workflowConsistency"),
    report_export: t("workflowExport")
  } as const;
  const statusLabelMap = {
    pending: t("workflowPending"),
    running: t("workflowRunning"),
    blocked: t("workflowBlocked"),
    done: t("workflowDone")
  } as const;
  const nextActionLabel = useMemo(() => {
    if (!currentStep) return t("assistantNoEvents");
    if (currentStep.key === "input_validation") return t("runNow");
    if (currentStep.key === "execution") return t("focusRun");
    if (currentStep.key === "evidence_binding") return t("assistantOpenEvidence");
    if (currentStep.key === "consistency_check") return t("onboardingReplay");
    return t("assistantOpenReports");
  }, [currentStep, t]);

  const stream = useMemo<StreamItem[]>(() => {
    const runEvents: StreamItem[] = runs.map((run) => ({
      id: `run-${run.id}`,
      createdAt: run.finishedAt ?? run.startedAt,
      title: run.success ? t("timelineRunSuccess") : t("timelineRunFailed"),
      detail: `${run.module.toUpperCase()} · ${run.success ? t("statusSuccess") : run.error ?? t("statusFailed")}`
    }));

    const issueEvents: StreamItem[] = issues.map((issue) => ({
      id: `issue-${issue.id}`,
      createdAt: issue.createdAt,
      title: t("timelineIssue"),
      detail: `[${issue.module.toUpperCase()}] ${issue.message}`
    }));

    const artifactEvents: StreamItem[] = artifacts.map((artifact) => ({
      id: `artifact-${artifact.id}`,
      createdAt: artifact.createdAt,
      title: t("timelineArtifact"),
      detail: `${artifact.kind} · ${artifact.path}`
    }));

    return [...localLogs, ...runEvents, ...issueEvents, ...artifactEvents]
      .sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1))
      .slice(0, 30);
  }, [runs, issues, artifacts, localLogs, t]);

  const runAction = (action: "split" | "run" | "preview" | "reports" | "evidence" | "guide") => {
    if (action === "split") {
      dispatch({ type: "set_panel_state", payload: { stageLayout: "split", focusMode: "split" } });
      return;
    }
    if (action === "run") {
      dispatch({
        type: "set_panel_state",
        payload: { stageLayout: "single", primaryPlugin: "run", focusMode: "run" }
      });
      return;
    }
    if (action === "preview") {
      dispatch({
        type: "set_panel_state",
        payload: { stageLayout: "single", primaryPlugin: "preview", focusMode: "preview" }
      });
      return;
    }
    if (action === "reports") {
      navigate("/reports");
      return;
    }
    if (action === "evidence") {
      navigate("/evidence");
      return;
    }
    dispatch({ type: "set_onboarding", payload: { active: true, stepIndex: 0 } });
  };

  const handleCommand = () => {
    const text = command.trim();
    if (!text) return;
    const now = new Date().toISOString();

    if (text.includes("分屏") || text.includes("split")) {
      runAction("split");
    } else if (text.includes("运行") || text.includes("run")) {
      runAction("run");
    } else if (text.includes("预览") || text.includes("preview")) {
      runAction("preview");
    } else if (text.includes("报告") || text.includes("report")) {
      runAction("reports");
    } else if (text.includes("证据") || text.includes("evidence")) {
      runAction("evidence");
    } else if (text.includes("引导") || text.includes("guide")) {
      runAction("guide");
    }

    setLocalLogs((prev) => [
      {
        id: `local-${now}`,
        createdAt: now,
        title: t("assistantCommand"),
        detail: text
      },
      ...prev
    ]);
    setCommand("");
  };

  return (
    <aside className="pane assistant-pane" data-guide="workspace-right">
      <div className="pane-title">{t("rightTitle")}</div>

      <section className="assistant-section assistant-status">
        <h4>{t("assistantStatus")}</h4>
        <span className="assistant-online-dot">{t("assistantOnline")}</span>
      </section>

      <section className="assistant-section assistant-workflow">
        <h4>{t("assistantCurrentStep")}</h4>
        <p className="assistant-current-step">
          {currentStep ? `${stepLabelMap[currentStep.key]} · ${statusLabelMap[currentStep.status]}` : t("workflowPending")}
        </p>
        <div className="assistant-current-meta">
          <span>{t("assistantNextAction")}: {nextActionLabel}</span>
          <span>{t("assistantBlocker")}: {currentStep?.reason ?? t("assistantNoBlocker")}</span>
        </div>
      </section>

      <section className="assistant-section">
        <h4>{t("assistantActions")}</h4>
        <div className="assistant-actions-grid">
          <button className="pill-btn" onClick={() => runAction("split")}>{t("splitMode")}</button>
          <button className="pill-btn" onClick={() => runAction("run")}>{t("focusRun")}</button>
          <button className="pill-btn" onClick={() => runAction("preview")}>{t("focusPreview")}</button>
          <button className="pill-btn" onClick={() => runAction("reports")}>{t("assistantOpenReports")}</button>
          <button className="pill-btn" onClick={() => runAction("evidence")}>{t("assistantOpenEvidence")}</button>
          <button className="pill-btn" onClick={() => runAction("guide")}>{t("onboardingReplay")}</button>
        </div>
      </section>

      <section className="assistant-section">
        <div className="assistant-command">
          <input
            className="resource-search"
            value={command}
            onChange={(event) => setCommand(event.target.value)}
            placeholder={t("assistantCmdPlaceholder")}
          />
          <button className="pill-btn-primary" onClick={handleCommand}>{t("assistantSend")}</button>
        </div>
      </section>

      <section className="assistant-section">
        <h4>{t("pluginTimeline")}</h4>
        <div className="assistant-stream">
          {stream.map((item) => (
            <article key={item.id} className="assistant-msg">
              <small>{new Date(item.createdAt).toLocaleString()}</small>
              <strong>{item.title}</strong>
              <p>{item.detail}</p>
            </article>
          ))}
          {stream.length === 0 ? <p className="assistant-msg">{t("assistantNoEvents")}</p> : null}
        </div>
      </section>
    </aside>
  );
}
