import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAppStore } from "../../lib/app-store";
import { requestCopilotChat } from "../../lib/copilot-api";
import type { TaskSpace, WorkflowStepKey, WorkflowStepStatus } from "../../lib/domain";
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

  // 从 store 获取当前 workspace 的系统消息，过滤后注入聊天流
  const systemMessages = useMemo(
    () => state.systemMessages.filter((m) => m.taskSpaceId === taskSpace.id),
    [state.systemMessages, taskSpace.id]
  );

  const lastSystemMsgId = useRef<string | null>(null);

  useEffect(() => {
    const newOnes = systemMessages.filter(
      (m) => lastSystemMsgId.current === null || m.id > (lastSystemMsgId.current ?? "")
    );
    if (newOnes.length === 0) return;
    lastSystemMsgId.current = newOnes[newOnes.length - 1].id;

    // 去重：跳过已经存在于 messages 中的
    setMessages((prev) => {
      const existingIds = new Set(prev.map((m) => m.id));
      const toAdd = newOnes
        .filter((m) => !existingIds.has(m.id))
        .map((m) => ({
          id: m.id,
          role: "system_run" as const,
          createdAt: m.createdAt,
          text: m.text,
          eventType: m.eventType,
          eventSeq: m.eventSeq,
        }));
      return [...prev, ...toAdd];
    });
  }, [systemMessages]);

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
              {...(item.eventType === "thought" || item.eventType === "tool_start"
                ? { style: { cursor: "pointer" }, onClick: () => onSwitchTab?.("timeline") }
                : {})}
            >
              <div className="assistant-msg-content markdown-content">
                {item.role === "system_run" ? (
                  <span style={{ fontSize: "0.85em", opacity: 0.85, borderLeft: "3px solid #7c3aed", paddingLeft: "8px", display: "block" }}>
                    {item.text}
                  </span>
                ) : (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {item.text}
                  </ReactMarkdown>
                )}
              </div>
            </article>
          ))}
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
