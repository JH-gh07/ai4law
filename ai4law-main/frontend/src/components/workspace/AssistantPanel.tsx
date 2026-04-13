import { useMemo, useState } from "react";
import { useAppStore } from "../../lib/app-store";
import { requestCopilotChat } from "../../lib/copilot-api";
import type { TaskSpace, WorkflowStepKey, WorkflowStepStatus } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { findTaskTemplate, getTaskTemplateTitle } from "../../lib/task-templates";
import { deriveWorkflowSteps } from "../../lib/workflow";

type AssistantPanelProps = {
  taskSpace: TaskSpace;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  createdAt: string;
  text: string;
};

type StatusEvent = {
  id: string;
  label: string;
  detail: string;
};

const toFileName = (value: string): string => {
  const normalized = value.replace(/\\/g, "/");
  const chunks = normalized.split("/");
  return chunks[chunks.length - 1] || value;
};

export function AssistantPanel({ taskSpace }: AssistantPanelProps) {
  const { t, lang } = useLang();
  const { state } = useAppStore();
  const taskTemplate = findTaskTemplate(taskSpace.taskTemplateId);
  const [viewMode, setViewMode] = useState<"status" | "copilot">("status");
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      createdAt: new Date().toISOString(),
      text: t("copilotWelcome")
    }
  ]);

  const issues = useMemo(
    () => state.issues.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.issues, taskSpace.id]
  );

  const runs = useMemo(
    () => state.moduleRuns.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.moduleRuns, taskSpace.id]
  );

  const artifacts = useMemo(
    () => state.artifacts.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.artifacts, taskSpace.id]
  );

  const evidenceCount = useMemo(
    () => state.evidenceHits.filter((item) => item.taskSpaceId === taskSpace.id).length,
    [state.evidenceHits, taskSpace.id]
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

  const stepLabelMap: Record<WorkflowStepKey, string> = {
    input_validation: t("workflowInputValidation"),
    execution: t("workflowExecution"),
    evidence_binding: t("workflowEvidence"),
    consistency_check: t("workflowConsistency"),
    report_export: t("workflowExport")
  };
  const statusLabelMap: Record<WorkflowStepStatus, string> = {
    pending: t("workflowPending"),
    running: t("workflowRunning"),
    blocked: t("workflowBlocked"),
    done: t("workflowDone")
  };

  const nextActionText = useMemo(() => {
    if (!currentStep) return t("assistantNoBlocker");
    if (currentStep.key === "input_validation") return t("assistantActionInput");
    if (currentStep.key === "execution") return t("assistantActionExecution");
    if (currentStep.key === "evidence_binding") return t("assistantActionEvidence");
    if (currentStep.key === "consistency_check") return t("assistantActionConsistency");
    return t("assistantActionExport");
  }, [currentStep, t]);

  const statusEvents = useMemo<StatusEvent[]>(() => {
    const events: StatusEvent[] = workflowSteps.map((step) => ({
      id: step.key,
      label: `${stepLabelMap[step.key]} · ${statusLabelMap[step.status]}`,
      detail: step.reason ?? t("workflowNoReason")
    }));

    if (latestRun) {
      events.unshift({
        id: `run-${latestRun.id}`,
        label: latestRun.success ? t("timelineRunSuccess") : t("timelineRunFailed"),
        detail: `${latestRun.module.toUpperCase()} · ${latestRun.success ? t("statusOk") : latestRun.error ?? t("statusFail")}`
      });
    }

    if (issues.length > 0) {
      events.unshift({
        id: "issue-total",
        label: `${t("timelineIssue")} · ${issues.length}`,
        detail: issues[0]?.message ?? t("workflowNoReason")
      });
    }

    if (artifacts.length > 0) {
      events.unshift({
        id: "artifact-total",
        label: `${t("timelineArtifact")} · ${artifacts.length}`,
        detail: artifacts[0]?.path ? toFileName(artifacts[0].path) : t("workflowNoReason")
      });
    }

    return events.slice(0, 8);
  }, [artifacts, issues, latestRun, statusLabelMap, stepLabelMap, t, workflowSteps]);

  const submitPrompt = async (prompt?: string, action?: string) => {
    const text = (prompt ?? input).trim();
    if (!text || isSending) return;

    const now = new Date().toISOString();
    const userMsg: ChatMessage = {
      id: `user-${now}`,
      role: "user",
      createdAt: now,
      text
    };
    const historyForModel = [...messages, userMsg];
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsSending(true);

    try {
      const response = await requestCopilotChat({
        prompt: text,
        action,
        task_space: {
          id: taskSpace.id,
          name: taskSpace.name,
          jurisdiction: taskSpace.jurisdiction,
          module: taskSpace.module,
          mode: taskSpace.mode,
          workspace_style: taskSpace.workspaceStyle
        },
        context: {
          current_step: currentStep ? `${stepLabelMap[currentStep.key]} · ${statusLabelMap[currentStep.status]}` : undefined,
          blocker: currentStep?.reason,
          runs_count: runs.length,
          issues_count: issues.length,
          evidence_count: evidenceCount,
          artifact_count: artifacts.length,
          top_issues: issues.slice(0, 5).map((item) => `[${item.severity}] ${item.message}`),
          latest_artifacts: artifacts
            .slice(0, 5)
            .map((item) => (item.path ? toFileName(item.path) : item.kind))
        },
        messages: historyForModel.map((item) => ({
          role: item.role,
          content: item.text
        }))
      });

      const replyMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        createdAt: new Date().toISOString(),
        text: response.reply || t("copilotEmptyReply")
      };
      setMessages((prev) => [...prev, replyMsg]);
    } catch (error) {
      const detail = error instanceof Error ? error.message : t("copilotRequestFailed");
      const replyMsg: ChatMessage = {
        id: `assistant-error-${Date.now()}`,
        role: "assistant",
        createdAt: new Date().toISOString(),
        text: `${t("copilotRequestFailed")} ${detail}`
      };
      setMessages((prev) => [...prev, replyMsg]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <aside className="pane assistant-pane assistant-copilot-pane" data-guide="workspace-right">
      <div className="pane-title">{t("copilotPaneTitle")}</div>
      <div className="assistant-view-switch">
        <button
          className={`tab-btn ${viewMode === "status" ? "active" : ""}`}
          onClick={() => setViewMode("status")}
        >
          {t("assistantStatus")}
        </button>
        <button
          className={`tab-btn ${viewMode === "copilot" ? "active" : ""}`}
          onClick={() => setViewMode("copilot")}
        >
          Copilot
        </button>
      </div>

      {viewMode === "status" ? (
        <section className="assistant-mode-shell assistant-mode-shell-status">
          <section className="assistant-section assistant-status">
            <h4>{t("assistantStatus")}</h4>
            <span className="assistant-online-dot">{t("copilotOnline")}</span>
          </section>

          <section className="assistant-section assistant-flow-card">
            <h4>{t("copilotContextTitle")}</h4>
            <div className="assistant-flow-row">
              <strong>{t("copilotContextTask")}</strong>
              <span>{taskTemplate ? getTaskTemplateTitle(taskTemplate, lang) : taskSpace.name}</span>
            </div>
            <div className="assistant-flow-row">
              <strong>{t("assistantCurrentStep")}</strong>
              <span>{currentStep ? `${stepLabelMap[currentStep.key]} · ${statusLabelMap[currentStep.status]}` : t("workflowPending")}</span>
            </div>
            <div className="assistant-flow-row">
              <strong>{t("assistantBlocker")}</strong>
              <span>{currentStep?.reason ?? t("assistantNoBlocker")}</span>
            </div>
            <div className="assistant-flow-row">
              <strong>{t("assistantNextAction")}</strong>
              <span>{nextActionText}</span>
            </div>
            <div className="assistant-flow-row assistant-flow-row-compact">
              <strong>{t("copilotContextRuns")}</strong>
              <span>{runs.length} · {t("copilotContextIssues")}: {issues.length} · {t("copilotContextEvidence")}: {evidenceCount}</span>
            </div>
          </section>

          <section className="assistant-section assistant-stream-shell">
            <h4>{t("assistantStatus")}</h4>
            <div className="assistant-flow-list assistant-status-stream">
              {statusEvents.map((event) => (
                <article key={event.id} className="assistant-flow-item">
                  <strong>{event.label}</strong>
                  <p>{event.detail}</p>
                </article>
              ))}
            </div>
          </section>
        </section>
      ) : (
        <section className="assistant-mode-shell assistant-mode-shell-copilot">
          <section className="assistant-section assistant-copilot-chat">
            <h4>{t("copilotChatTitle")}</h4>
            <div className="assistant-stream assistant-copilot-stream">
              {messages.map((item) => (
                <article key={item.id} className={`assistant-msg assistant-copilot-msg ${item.role}`}>
                  <small>{new Date(item.createdAt).toLocaleString()}</small>
                  <p>{item.text}</p>
                </article>
              ))}
              {messages.length === 0 ? <p className="assistant-msg">{t("copilotNoMessages")}</p> : null}
            </div>
          </section>

          <section className="assistant-section">
            <div className="assistant-command assistant-copilot-command">
              <input
                className="resource-search"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder={t("copilotInputPlaceholder")}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !isSending) {
                    event.preventDefault();
                    submitPrompt();
                  }
                }}
              />
              <button className="pill-btn-primary" onClick={() => submitPrompt()} disabled={isSending}>
                {isSending ? t("copilotSending") : t("copilotSend")}
              </button>
            </div>
            {isSending ? <p className="assistant-msg">{t("copilotThinking")}</p> : null}
          </section>
        </section>
      )}
    </aside>
  );
}
