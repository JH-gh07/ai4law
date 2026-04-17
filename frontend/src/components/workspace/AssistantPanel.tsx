import { useMemo, useState } from "react";
import { useAppStore } from "../../lib/app-store";
import { requestCopilotChat } from "../../lib/copilot-api";
import type { TaskSpace, WorkflowStepKey, WorkflowStepStatus } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { findTaskTemplate, getTaskTemplateTitle } from "../../lib/task-templates";
import { deriveWorkflowSteps } from "../../lib/workflow";
import { ChevronToggleIcon, SparkleIcon } from "../common/AppIcons";

type AssistantPanelProps = {
  taskSpace: TaskSpace;
  onToggleCollapse: () => void;
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

export function AssistantPanel({ taskSpace, onToggleCollapse }: AssistantPanelProps) {
  const { t, lang } = useLang();
  const { state } = useAppStore();
  const taskTemplate = findTaskTemplate(taskSpace.taskTemplateId);
  const [viewMode, setViewMode] = useState<"status" | "copilot">("copilot");
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
  const progressRatio = workflowSteps.length > 0 ? workflowSteps.filter((step) => step.status === "done").length / workflowSteps.length : 0;

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

    if (artifacts.length > 0) {
      events.unshift({
        id: "artifact-latest",
        label: lang === "zh" ? "最新产物" : "Latest output",
        detail: toFileName(artifacts[0].path)
      });
    }

    if (issues.length > 0) {
      events.unshift({
        id: "issue-latest",
        label: lang === "zh" ? `告警 ${issues.length}` : `Issues ${issues.length}`,
        detail: issues[0]?.message ?? t("workflowNoReason")
      });
    }

    return events.slice(0, 10);
  }, [artifacts, issues, lang, statusLabelMap, stepLabelMap, t, workflowSteps]);

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
          latest_artifacts: artifacts.slice(0, 5).map((item) => toFileName(item.path))
        },
        messages: historyForModel.map((item) => ({
          role: item.role,
          content: item.text
        }))
      });

      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          createdAt: new Date().toISOString(),
          text: response.reply || t("copilotEmptyReply")
        }
      ]);
    } catch (error) {
      const detail = error instanceof Error ? error.message : t("copilotRequestFailed");
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          createdAt: new Date().toISOString(),
          text: `${t("copilotRequestFailed")} ${detail}`
        }
      ]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <aside className="pane assistant-pane assistant-copilot-pane assistant-pane-redesign" data-guide="workspace-right">
      <div className="pane-title">{t("copilotPaneTitle")}</div>
      <button className="workspace-side-toggle workspace-side-toggle-right" onClick={onToggleCollapse} aria-label="collapse-right-sidebar">
        <ChevronToggleIcon direction="right" width="16" height="16" />
      </button>

      <div className="assistant-view-switch assistant-view-switch-redesign">
        <button className={`tab-btn ${viewMode === "status" ? "active" : ""}`} onClick={() => setViewMode("status")}>
          {t("assistantStatus")}
        </button>
        <button className={`tab-btn ${viewMode === "copilot" ? "active" : ""}`} onClick={() => setViewMode("copilot")}>
          Copilot
        </button>
      </div>

      {viewMode === "status" ? (
        <section className="assistant-mode-shell assistant-mode-shell-status">
          <section className="assistant-flow-card assistant-progress-card">
            <div className="assistant-flow-card-head">
              <h4>{lang === "zh" ? "任务进度" : "Task Progress"}</h4>
              <span>{Math.round(progressRatio * 100)}%</span>
            </div>
            <div className="assistant-progress-bar">
              <span style={{ width: `${Math.round(progressRatio * 100)}%` }} />
            </div>
            <div className="assistant-flow-row">
              <strong>{t("assistantCurrentStep")}</strong>
              <span>{currentStep ? `${stepLabelMap[currentStep.key]} · ${statusLabelMap[currentStep.status]}` : t("workflowPending")}</span>
            </div>
            <div className="assistant-flow-row">
              <strong>{t("assistantNextAction")}</strong>
              <span>{nextActionText}</span>
            </div>
          </section>

          <section className="assistant-flow-card">
            <h4>{lang === "zh" ? "工作区上下文" : "Workspace Context"}</h4>
            <div className="assistant-flow-row">
              <strong>{t("copilotContextTask")}</strong>
              <span>{taskTemplate ? getTaskTemplateTitle(taskTemplate, lang) : taskSpace.name}</span>
            </div>
            <div className="assistant-flow-row">
              <strong>{t("assistantBlocker")}</strong>
              <span>{currentStep?.reason ?? t("assistantNoBlocker")}</span>
            </div>
            <div className="assistant-flow-row assistant-flow-row-compact">
              <strong>{lang === "zh" ? "运行概览" : "Runtime"}</strong>
              <span>{runs.length} runs · {issues.length} issues · {evidenceCount} evidence · {artifacts.length} artifacts</span>
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
        <section className="assistant-mode-shell assistant-mode-shell-copilot assistant-mode-shell-chat">
          <section className="assistant-chat-topbar">
            <div>
              <h4>{t("copilotChatTitle")}</h4>
              <p>{lang === "zh" ? "围绕当前任务上下文进行自然交流" : "Chat naturally with live task context"}</p>
            </div>
            <span className="assistant-online-dot">{t("copilotOnline")}</span>
          </section>

          <section className="assistant-stream assistant-copilot-stream assistant-copilot-stream-redesign">
            {messages.map((item) => (
              <article key={item.id} className={`assistant-msg assistant-copilot-msg assistant-copilot-msg-redesign ${item.role}`}>
                <div className="assistant-msg-meta">
                  <span className={`assistant-msg-role role-${item.role}`}>
                    {item.role === "assistant" ? <SparkleIcon width="12" height="12" /> : null}
                    {item.role === "assistant" ? "Copilot" : (lang === "zh" ? "你" : "You")}
                  </span>
                  <small>{new Date(item.createdAt).toLocaleTimeString()}</small>
                </div>
                <p>{item.text}</p>
              </article>
            ))}
          </section>

          <section className="assistant-copilot-composer">
            <div className="assistant-command assistant-copilot-command assistant-copilot-command-redesign">
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
            {isSending ? <p className="assistant-thinking-note">{t("copilotThinking")}</p> : null}
          </section>
        </section>
      )}
    </aside>
  );
}
