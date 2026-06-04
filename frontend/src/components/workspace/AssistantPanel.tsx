import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAppStore } from "../../lib/app-store";
import { requestCopilotChat } from "../../lib/copilot-api";
import type { RunSession, StageNode, TaskSpace, WorkflowStepKey, WorkflowStepStatus } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { deriveWorkflowSteps } from "../../lib/workflow";
import { ChevronToggleIcon } from "../common/AppIcons";

type AssistantPanelProps = {
  taskSpace: TaskSpace;
  onToggleCollapse: () => void;
  onSwitchTab?: (tab: string) => void;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system_run";
  createdAt: string;
  text: string;
  eventType?: string;
  eventSeq?: number;
};

const toFileName = (value: string): string => {
  const normalized = value.replace(/\\/g, "/");
  const chunks = normalized.split("/");
  return chunks[chunks.length - 1] || value;
};

/** ── ThinkingBlock: Claude-style expandable thinking process ── */
const THINKING_ICONS: Record<string, string> = {
  pending: "○",
  running: "⊙",
  done: "✓",
};

function ThinkingBlock({ session, onToggle, lang }: { session: RunSession; onToggle: () => void; lang: "zh" | "en" }) {
  const [collapsed, setCollapsed] = useState(session.isComplete);
  const runningCount = session.stages.filter((s) => s.status === "running").length;
  const doneCount = session.stages.filter((s) => s.status === "done").length;
  const totalCount = session.stages.length;

  useEffect(() => {
    if (session.isComplete) {
      // Auto-collapse after 2s when complete
      const t = setTimeout(() => setCollapsed(true), 2000);
      return () => clearTimeout(t);
    }
    setCollapsed(false);
  }, [session.isComplete]);

  const headerText = session.isComplete
    ? lang === "zh"
      ? `思考过程已完成（${doneCount} 个阶段${session.totalDurationMs ? `，${(session.totalDurationMs / 1000).toFixed(1)}s` : ""}）`
      : `Thinking complete (${doneCount} stages${session.totalDurationMs ? `, ${(session.totalDurationMs / 1000).toFixed(1)}s` : ""})`
    : lang === "zh"
      ? `思考中...（${runningCount} 运行，${doneCount}/${totalCount} 完成）`
      : `Thinking... (${runningCount} running, ${doneCount}/${totalCount} done)`;

  return (
    <article
      className="assistant-msg assistant-copilot-msg assistant-chat-bubble system_run thinking-block"
      style={{ borderLeft: "3px solid #7c3aed", background: "rgba(124, 58, 237, 0.04)", cursor: "default" }}
    >
      <div
        className="thinking-header"
        onClick={() => setCollapsed((c) => !c)}
        style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: "6px", padding: "4px 0", fontSize: "0.85em", userSelect: "none" }}
      >
        <span style={{ fontSize: "0.7em", transition: "transform 0.2s", transform: collapsed ? "rotate(-90deg)" : "none" }}>▼</span>
        <span style={{ fontWeight: 600, color: "#7c3aed" }}>
          {session.isComplete ? "🧠" : runningCount > 0 ? "🧠" : "🧠"}
        </span>
        <span style={{ color: "#6b7280" }}>{headerText}</span>
        <span
          style={{ fontSize: "0.75em", color: "#3b82f6", marginLeft: "auto", cursor: "pointer", textDecoration: "underline" }}
          onClick={(e) => { e.stopPropagation(); onToggle(); }}
        >
          {lang === "zh" ? "查看详情" : "View details"}
        </span>
      </div>
      {!collapsed && (
        <div className="thinking-stages" style={{ marginTop: "6px", display: "flex", flexDirection: "column", gap: "3px" }}>
          {session.stages.map((stage) => (
            <div
              key={stage.id}
              className={`thinking-stage thinking-stage-${stage.status}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "0.82em",
                padding: "2px 0",
                color: stage.status === "done" ? "#374151" : stage.status === "running" ? "#1e40af" : "#9ca3af",
                animation: stage.status === "running" ? "pulse 1.5s infinite" : "none",
              }}
            >
              <span style={{
                width: "18px",
                textAlign: "center",
                fontWeight: 700,
                color: stage.status === "done" ? "#059669" : stage.status === "running" ? "#2563eb" : "#9ca3af",
              }}>
                {stage.status === "running" ? "⊙" : stage.status === "done" ? "✓" : "○"}
              </span>
              <span style={{ flex: 1 }}>{stage.name}</span>
              {stage.summary && (
                <span style={{ color: "#6b7280", fontSize: "0.85em", maxWidth: "260px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {stage.summary}
                </span>
              )}
              {stage.status === "running" && (
                <span style={{ fontSize: "0.7em", color: "#2563eb", animation: "spin 1s linear infinite" }}>⟳</span>
              )}
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

export function AssistantPanel({ taskSpace, onToggleCollapse, onSwitchTab }: AssistantPanelProps) {
  const { t, lang } = useLang();
  const { state } = useAppStore();
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const streamRef = useRef<HTMLElement | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      createdAt: new Date().toISOString(),
      text: t("copilotWelcome")
    }
  ]);

  // 从 store 获取当前 workspace 的活跃 RunSession（实时思考过程）
  const activeSession = useMemo<RunSession | null>(() => {
    const sessions = state.runSessions.filter((s) => s.taskSpaceId === taskSpace.id);
    if (sessions.length === 0) return null;
    // 返回最近的 session（可能有多个历史 session，取最新）
    return sessions[0] ?? null;
  }, [state.runSessions, taskSpace.id]);

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

  useEffect(() => {
    const stream = streamRef.current;
    if (!stream) return;
    stream.scrollTop = stream.scrollHeight;
  }, [messages, isSending]);

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
        messages: historyForModel
          .filter((item): item is ChatMessage & { role: "user" | "assistant" } => item.role === "user" || item.role === "assistant")
          .map((item) => ({
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
      <button className="workspace-side-toggle workspace-side-toggle-right" onClick={onToggleCollapse} aria-label="collapse-right-sidebar">
        <ChevronToggleIcon direction="right" width="16" height="16" />
      </button>

      <section className="assistant-mode-shell assistant-mode-shell-copilot assistant-mode-shell-chat assistant-chat-shell">
        <section className="assistant-chat-topbar assistant-chat-topbar-compact">
          <h4>{t("copilotChatTitle")}</h4>
          <span className="assistant-online-dot assistant-online-dot-compact">
            {lang === "zh" ? "在线" : "Online"}
          </span>
        </section>

        <section ref={streamRef} className="assistant-stream assistant-copilot-stream assistant-copilot-stream-redesign assistant-chat-stream" aria-live="polite">
          {messages.map((item) => (
            <article
              key={item.id}
              className={`assistant-msg assistant-copilot-msg assistant-copilot-msg-redesign assistant-chat-bubble ${item.role}`}
            >
              <div className="assistant-msg-content markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {item.text}
                </ReactMarkdown>
              </div>
            </article>
          ))}
          {activeSession ? (
            <ThinkingBlock
              session={activeSession}
              onToggle={() => onSwitchTab?.("timeline")}
              lang={lang}
            />
          ) : null}
          {isSending ? <p className="assistant-thinking-note">{t("copilotThinking")}</p> : null}
        </section>

        <section className="assistant-copilot-composer assistant-chat-composer">
          <div className="assistant-command assistant-copilot-command assistant-copilot-command-redesign">
            <input
              className="resource-search"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={lang === "zh" ? "输入消息..." : "Type a message..."}
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
        </section>
      </section>
    </aside>
  );
}
