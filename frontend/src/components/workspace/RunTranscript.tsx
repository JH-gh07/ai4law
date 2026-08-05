import { useMemo, useEffect, useRef, useState } from "react";
import { fetchTaskManifest, type RunManifest } from "../../api/events";
import { useLang } from "../../lib/language";
import { extractTokenUsage, useTaskEvents } from "../../lib/useTaskEvents";
import { adaptEvents } from "../../lib/trace-adapter";
import { TraceRunHeader } from "./TraceRunHeader";
import { TraceNodeView } from "./TraceNodeView";
import type { TraceNode } from "../../lib/domain";

type Props = {
  taskId: string | null;
  moduleLabel?: string;
};

export function RunTranscript({ taskId, moduleLabel = "" }: Props) {
  const { lang } = useLang();
  const events = useTaskEvents(taskId);
  const [manifest, setManifest] = useState<RunManifest | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  // 语义聚合: 原始事件 -> 语义节点
  const nodes: TraceNode[] = useMemo(() => {
    if (events.length === 0) return [];
    return adaptEvents(events, lang);
  }, [events, lang]);

  const tokenUsage = useMemo(() => extractTokenUsage(events), [events]);

  // 自动滚动到最新（仅在运行中且用户在底部附近）
  const prevNodeCount = useRef(0);
  const terminalEvent = [...events]
    .reverse()
    .find((event) => event.event_type === "final" || event.event_type === "final_brief");
  const latestState = [...events]
    .reverse()
    .find((event) => event.event_type === "status" && typeof event.detail?.state === "string");
  const latestStateValue =
    typeof latestState?.detail?.state === "string" ? latestState.detail.state.toLowerCase() : null;
  const manifestState = manifest?.status?.toLowerCase() ?? null;
  const effectiveState = latestStateValue ?? manifestState;
  const hasFailureState = effectiveState != null && /(fail|error|cancel|timeout|aborted)/i.test(effectiveState);
  const hasFailureSummary = [...events]
    .reverse()
    .some((event) => /失败|异常|报错|中止|超时|failed|error/i.test(event.summary));
  const hasFinal = events.some((event) => event.event_type === "final");
  const isRunning = events.length > 0 && !hasFinal && !hasFailureState;

  const runStatus = !taskId
    ? "empty" as const
    : hasFailureState || hasFailureSummary
      ? "failed" as const
      : hasFinal || manifestState === "completed" || manifestState === "succeeded"
        ? "completed" as const
        : events.length > 0 || manifestState
          ? "running" as const
          : "empty" as const;

  const firstTs = manifest?.created_at ?? events[0]?.timestamp ?? nodes[0]?.timestamp;
  const lastTs = manifest?.updated_at ?? terminalEvent?.timestamp ?? nodes[nodes.length - 1]?.timestamp;
  const manifestTokens = manifest?.observability?.tokens;

  useEffect(() => {
    if (!taskId) {
      setManifest(null);
      return;
    }
    setManifest(null);
    let canceled = false;
    void fetchTaskManifest(taskId)
      .then((value) => {
        if (!canceled) setManifest(value);
      })
      .catch(() => {
        if (!canceled) setManifest(null);
      });
    return () => {
      canceled = true;
    };
  }, [taskId, latestStateValue]);

  useEffect(() => {
    if (!bodyRef.current) return;
    const el = bodyRef.current;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    if (isRunning && nodes.length > prevNodeCount.current && atBottom) {
      el.scrollTop = el.scrollHeight;
    }
    prevNodeCount.current = nodes.length;
  }, [nodes.length, isRunning]);

  return (
    <section className="execution-timeline">
      <TraceRunHeader
        lang={lang}
        moduleLabel={moduleLabel}
        status={runStatus}
        taskId={taskId}
        startedAt={firstTs}
        completedAt={runStatus === "completed" || runStatus === "failed" ? lastTs : undefined}
        durationMs={manifest?.duration_ms}
        nodeCount={nodes.length}
        eventCount={events.length}
        workflowPromptTokens={tokenUsage.workflow.prompt_tokens}
        workflowCompletionTokens={tokenUsage.workflow.completion_tokens}
        workflowTotalTokens={tokenUsage.workflow.total_tokens}
        copilotPromptTokens={tokenUsage.copilot.prompt_tokens}
        copilotCompletionTokens={tokenUsage.copilot.completion_tokens}
        copilotTotalTokens={tokenUsage.copilot.total_tokens}
        totalPromptTokens={manifestTokens?.prompt_tokens ?? tokenUsage.total.prompt_tokens}
        totalCompletionTokens={manifestTokens?.completion_tokens ?? tokenUsage.total.completion_tokens}
        totalTokens={manifestTokens?.total_tokens ?? tokenUsage.total.total_tokens}
      />

      <div className="trace-timeline-body" ref={bodyRef}>
        {!taskId ? (
          <p className="trace-empty">
            {lang === "zh"
              ? "启动一次异步执行后，这里会显示 Agent 的执行轨迹。"
              : "Start an async run to see the agent execution trace here."}
          </p>
        ) : nodes.length === 0 ? (
          <p className="trace-empty">
            {lang === "zh"
              ? "暂无执行记录，任务开始后这里会显示 Agent 的执行轨迹。"
              : "No execution records yet. Agent trace will appear here once the task starts."}
          </p>
        ) : (
          <div className="trace-timeline-line">
            {nodes.map((node) => (
              <TraceNodeView key={node.id} node={node} lang={lang} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
