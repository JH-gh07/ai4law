import { useMemo, useEffect, useRef } from "react";
import { useLang } from "../../lib/language";
import { useTaskEvents } from "../../lib/useTaskEvents";
import { adaptEvents } from "../../lib/trace-adapter";
import { TraceNodeView } from "./TraceNodeView";
import type { TraceNode } from "../../lib/domain";

type Props = {
  taskId: string | null;
  moduleLabel?: string;
};

export function RunTranscript({ taskId, moduleLabel = "" }: Props) {
  const { lang } = useLang();
  const events = useTaskEvents(taskId);
  const bodyRef = useRef<HTMLDivElement>(null);

  // 语义聚合: 原始事件 -> 语义节点
  const nodes: TraceNode[] = useMemo(() => {
    if (events.length === 0) return [];
    return adaptEvents(events);
  }, [events]);

  // 自动滚动到最新（仅在运行中且用户在底部附近）
  const prevNodeCount = useRef(0);
  const hasFinal = events.some((e) => e.event_type === "final");
  const isRunning = events.length > 0 && !hasFinal;
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
              <TraceNodeView key={node.id} node={node} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
