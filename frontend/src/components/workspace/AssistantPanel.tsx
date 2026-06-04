import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAppStore } from "../../lib/app-store";
import { requestCopilotChat } from "../../lib/copilot-api";
import type { TaskSpace, TraceNode, WorkflowStepKey, WorkflowStepStatus } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { deriveWorkflowSteps } from "../../lib/workflow";
import { ChevronToggleIcon } from "../common/AppIcons";
import { extractTokenUsage, useTaskEvents } from "../../lib/useTaskEvents";
import { adaptEvents } from "../../lib/trace-adapter";
import { TraceNodeView } from "./TraceNodeView";
import { selectPreferredRun } from "../../lib/run-state";

type AssistantPanelProps = {
  taskSpace: TaskSpace;
  taskId: string | null;
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

function summarizeTraceNodes(nodes: TraceNode[]): {
  summary: string;
  stage: string | undefined;
  status: "idle" | "running" | "completed" | "failed";
  highlights: string[];
} {
  if (nodes.length === 0) {
    return {
      summary: "暂无执行轨迹",
      stage: undefined,
      status: "idle",
      highlights: [],
    };
  }

  const latest = nodes[nodes.length - 1];
  const stage = `${latest.stage}｜${latest.action}`;
  const failed = nodes.some((node) => node.status === "error");
  const running = nodes.some((node) => node.status === "running");
  const status = failed ? "failed" : running ? "running" : "completed";
  const highlights = nodes
    .slice(-5)
    .map((node) => `${node.stage}｜${node.action}：${node.description}`)
    .filter((line) => line.trim().length > 0);

  const summary = highlights[highlights.length - 1] ?? `${latest.stage}｜${latest.action}`;
  return { summary, stage, status, highlights };
}

function CopilotTraceStrip({
  summary,
  stage,
  status,
  highlights,
  onOpenHistory,
  lang,
}: {
  summary: string;
  stage?: string;
  status: "idle" | "running" | "completed" | "failed";
  highlights: string[];
  onOpenHistory: () => void;
  lang: "zh" | "en";
}) {
  const statusLabel = status === "running"
    ? (lang === "zh" ? "执行中" : "Running")
    : status === "completed"
      ? (lang === "zh" ? "已完成" : "Completed")
      : status === "failed"
        ? (lang === "zh" ? "失败" : "Failed")
        : (lang === "zh" ? "待执行" : "Idle");

  return (
    <section className="copilot-trace-strip">
      <div className="copilot-trace-strip-head">
        <div>
          <strong>{lang === "zh" ? "当前执行" : "Current Trace"}</strong>
          <p>{summary}</p>
        </div>
        <button type="button" className="copilot-trace-history-link" onClick={onOpenHistory}>
          {lang === "zh" ? "查看历史" : "Open History"}
        </button>
      </div>
      <div className="copilot-trace-strip-meta">
        <span>{statusLabel}</span>
        <span>{stage ?? (lang === "zh" ? "暂无阶段" : "No stage")}</span>
      </div>
      {highlights.length > 0 ? (
        <div className="copilot-trace-strip-list">
          {highlights.map((item) => (
            <div key={item} className="copilot-trace-strip-item">
              {item}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function AssistantPanel({ taskSpace, taskId, onToggleCollapse, onSwitchTab }: AssistantPanelProps) {
  const { t, lang } = useLang();
  const { state } = useAppStore();
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const streamRef = useRef<HTMLElement | null>(null);
  const traceEvents = useTaskEvents(taskId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

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
    () => selectPreferredRun(state.moduleRuns.filter((item) => item.taskSpaceId === taskSpace.id)),
    [state.moduleRuns, taskSpace.id]
  );

  const traceNodes = useMemo(() => {
    if (!taskId || traceEvents.length === 0) return [];
    return adaptEvents(traceEvents, lang);
  }, [taskId, traceEvents, lang]);

  const tokenUsage = useMemo(() => extractTokenUsage(traceEvents), [traceEvents]);

  const traceContext = useMemo(() => summarizeTraceNodes(traceNodes), [traceNodes]);

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
        task_id: taskId,
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
          latest_artifacts: artifacts.slice(0, 5).map((item) => toFileName(item.path)),
          trace_summary: traceContext.summary,
          trace_stage: traceContext.stage,
          trace_status: traceContext.status,
          trace_highlights: traceContext.highlights,
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
          <CopilotTraceStrip
            summary={traceContext.summary}
            stage={traceContext.stage}
            status={traceContext.status}
            highlights={traceContext.highlights}
            onOpenHistory={() => onSwitchTab?.("timeline")}
            lang={lang}
          />
          {taskId && traceNodes.length > 0 ? (
            <section className="copilot-trace-embedded">
              <header className="copilot-trace-embedded-head">
                <div>
                  <strong>{lang === "zh" ? "执行流详情" : "Execution Flow"}</strong>
                  <p>
                    {lang === "zh"
                      ? `展示当前任务的阶段、工具调用、结果摘要与中间产物。累计 tokens：${tokenUsage.total.total_tokens}`
                      : `Shows stages, tool calls, outputs, and intermediate results. Total tokens: ${tokenUsage.total.total_tokens}`}
                  </p>
                </div>
                <button type="button" className="copilot-trace-history-link" onClick={() => onSwitchTab?.("timeline")}>
                  {lang === "zh" ? "在工作区打开" : "Open in Workspace"}
                </button>
              </header>
              <div className="copilot-trace-embedded-body">
                <div className="trace-timeline-line trace-timeline-line-embedded">
                  {traceNodes.map((node) => (
                    <TraceNodeView key={node.id} node={node} lang={lang} />
                  ))}
                </div>
              </div>
            </section>
          ) : null}
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
