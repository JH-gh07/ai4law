import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "../../lib/app-store";
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

type ServiceAction = "due_diligence" | "memo" | "remediation" | "reports" | "evidence";

type StatusEvent = {
  id: string;
  label: string;
  detail: string;
};

export function AssistantPanel({ taskSpace }: AssistantPanelProps) {
  const { t, lang } = useLang();
  const navigate = useNavigate();
  const { state } = useAppStore();
  const taskTemplate = findTaskTemplate(taskSpace.taskTemplateId);
  const [viewMode, setViewMode] = useState<"status" | "copilot">("status");
  const [input, setInput] = useState("");
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

  const suggestions = useMemo(() => {
    const topIssues = issues
      .filter((item) => item.severity === "high")
      .slice(0, 2)
      .map((item) => item.message);
    const list: string[] = [];

    if (topIssues.length > 0) {
      list.push(`优先修复高风险问题：${topIssues.join("；")}`);
      list.push("我可以基于高风险项生成《风险与整改建议清单》初稿。");
    } else {
      list.push(t("copilotNoIssues"));
    }

    if (currentStep?.key === "report_export") {
      list.push("当前已接近交付阶段，建议先生成合规备忘录再导出正式版本。");
    } else if (currentStep?.key === "evidence_binding") {
      list.push("建议先补齐证据命中，再做报告定稿。");
    } else if (currentStep?.key === "execution") {
      list.push("建议先完成本任务模块执行，再生成通用服务文稿。");
    }
    return list.slice(0, 3);
  }, [currentStep?.key, issues, t]);

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
        detail: artifacts[0]?.path ?? t("workflowNoReason")
      });
    }

    return events.slice(0, 8);
  }, [artifacts, issues, latestRun, statusLabelMap, stepLabelMap, t, workflowSteps]);

  const buildReply = (prompt: string): string => {
    const low = prompt.toLowerCase();
    if (low.includes("尽调")) {
      return [
        "尽调提纲已为你准备：",
        "1) 业务场景与跨境链路说明",
        "2) 数据分类分级与处理角色矩阵",
        "3) 法域义务映射与差距清单",
        "4) 补证材料与时间计划"
      ].join("\n");
    }
    if (low.includes("备忘录")) {
      return [
        "合规备忘录建议结构：",
        "1) 背景与结论",
        "2) 适用法域与法律依据",
        "3) 当前状态与风险摘要",
        "4) 本周行动项与责任分工"
      ].join("\n");
    }
    if (low.includes("整改") || low.includes("风险")) {
      const topIssues = issues.slice(0, 3).map((item, idx) => `${idx + 1}. [${item.severity}] ${item.message}`);
      if (topIssues.length === 0) {
        return "当前没有可用风险条目。建议先执行任务模块或补充证据后再生成整改清单。";
      }
      return `整改清单草案：\n${topIssues.join("\n")}\n后续建议：按“必须立即修复/本周修复/持续优化”分层推进。`;
    }
    if (low.includes("下一步") || low.includes("next")) {
      return currentStep
        ? `建议下一步：${stepLabelMap[currentStep.key]}（${statusLabelMap[currentStep.status]}）。${currentStep.reason ?? "当前无阻塞。"}`
        : "当前无阶段信息，可先执行模块并生成报告草案。";
    }
    if (low.includes("报告")) {
      return "可先在右上动作中进入报告中心，再由我给你生成“提交版摘要”和“律师复核版摘要”。";
    }
    return "我已记录你的需求。可以直接说“生成尽调提纲 / 生成备忘录 / 生成整改清单 / 给出下一步动作”。";
  };

  const submitPrompt = (prompt?: string) => {
    const text = (prompt ?? input).trim();
    if (!text) return;

    const now = new Date().toISOString();
    const userMsg: ChatMessage = {
      id: `user-${now}`,
      role: "user",
      createdAt: now,
      text
    };
    const replyMsg: ChatMessage = {
      id: `assistant-${now}`,
      role: "assistant",
      createdAt: new Date(Date.now() + 1).toISOString(),
      text: buildReply(text)
    };
    setMessages((prev) => [...prev, userMsg, replyMsg]);
    setInput("");
  };

  const runServiceAction = (action: ServiceAction) => {
    if (action === "reports") {
      navigate("/reports");
      return;
    }
    if (action === "evidence") {
      navigate("/evidence");
      return;
    }
    if (action === "due_diligence") {
      submitPrompt("生成尽调提纲");
      return;
    }
    if (action === "memo") {
      submitPrompt("生成合规备忘录");
      return;
    }
    submitPrompt("生成风险与整改建议清单");
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
        <section className="assistant-mode-shell">
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

          <section className="assistant-section">
            <h4>{t("copilotServicesTitle")}</h4>
            <div className="assistant-actions-grid assistant-copilot-actions">
              <button className="pill-btn" onClick={() => runServiceAction("reports")}>{t("copilotServiceOpenReports")}</button>
              <button className="pill-btn" onClick={() => runServiceAction("evidence")}>{t("copilotServiceOpenEvidence")}</button>
            </div>
          </section>
        </section>
      ) : (
        <section className="assistant-mode-shell">
          <section className="assistant-section assistant-copilot-suggestions">
            <h4>{t("copilotSuggestionTitle")}</h4>
            <div className="assistant-copilot-suggestion-list">
              {suggestions.map((item) => (
                <article key={item} className="assistant-copilot-suggestion-item">{item}</article>
              ))}
            </div>
          </section>

          <section className="assistant-section">
            <h4>{t("copilotServicesTitle")}</h4>
            <div className="assistant-actions-grid assistant-copilot-actions">
              <button className="pill-btn" onClick={() => runServiceAction("due_diligence")}>{t("copilotServiceDueDiligence")}</button>
              <button className="pill-btn" onClick={() => runServiceAction("memo")}>{t("copilotServiceMemo")}</button>
              <button className="pill-btn" onClick={() => runServiceAction("remediation")}>{t("copilotServiceRemediation")}</button>
            </div>
          </section>

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
                  if (event.key === "Enter") {
                    event.preventDefault();
                    submitPrompt();
                  }
                }}
              />
              <button className="pill-btn-primary" onClick={() => submitPrompt()}>{t("copilotSend")}</button>
            </div>
          </section>
        </section>
      )}
    </aside>
  );
}
