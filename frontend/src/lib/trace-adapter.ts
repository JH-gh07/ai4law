/**
 * trace-adapter.ts -- 将底层 RunEvent 原始事件流转换为语义化 TraceNode 列表。
 *
 * 核心逻辑:
 *   1. event_type -> stage + action 映射
 *   2. tool_start + tool_result -> 合并为一个 Tool 节点
 *   3. thought -> 不独立成节点（合并到后续 tool 节点描述）
 *   4. intermediate / warning / final 各自成节点
 */

import type { RunEvent } from "./useTaskEvents";
import type { TraceNode, TraceBlock, TraceStage } from "./domain";

// -- 事件 -> 语义映射 --------------------------------------------------

type SemanticMapping = {
  stage: TraceStage;
  action: string;
  icon: string;
};

const EVENT_TO_SEMANTIC: Record<RunEvent["event_type"], SemanticMapping> = {
  status:        { stage: "Task",      action: "任务状态",   icon: "●" },
  thought:       { stage: "LLM",       action: "思路摘要",   icon: "💭" },
  tool_start:    { stage: "Tool",      action: "调用",       icon: "🔧" },
  tool_result:   { stage: "Tool",      action: "返回",       icon: "●" },
  intermediate:  { stage: "Review",    action: "中间结果",   icon: "📊" },
  warning:       { stage: "Review",    action: "警告",       icon: "⚠️" },
  final:         { stage: "Task",      action: "完成",       icon: "●" },
  final_brief:   { stage: "Review",    action: "简报",       icon: "📝" },
};

// -- detail -> TraceBlock ----------------------------------------------

function detailToBlock(
  label: TraceBlock["label"],
  detail: Record<string, unknown> | null | undefined,
  maxPreviewLines = 6,
): TraceBlock | undefined {
  if (!detail || Object.keys(detail).length === 0) return undefined;
  const content = JSON.stringify(detail, null, 2);
  const lines = content.split("\n");
  const preview = lines.length > maxPreviewLines
    ? lines.slice(0, maxPreviewLines).join("\n") + "\n..."
    : content;
  return { label, content, language: "json", preview, isTruncated: lines.length > maxPreviewLines };
}

function textToBlock(
  label: TraceBlock["label"],
  text: string | undefined,
  maxPreviewLines = 6,
): TraceBlock | undefined {
  if (!text || text.trim().length === 0) return undefined;
  const lines = text.split("\n");
  const preview = lines.length > maxPreviewLines
    ? lines.slice(0, maxPreviewLines).join("\n") + "\n..."
    : text;
  return { label, content: text, language: "text", preview, isTruncated: lines.length > maxPreviewLines };
}

// -- 聚合适配器 --------------------------------------------------------

export function adaptEvents(rawEvents: RunEvent[]): TraceNode[] {
  const nodes: TraceNode[] = [];
  let pendingToolStart: RunEvent | null = null;
  let pendingThought: RunEvent | null = null;

  for (const event of rawEvents) {
    // 跳过 seq <= 0 的状态事件（由 InMemoryTaskManager 发布，不在 trace 流中展示）
    if (event.event_type === "status" && event.seq <= 0) continue;

    const sem = EVENT_TO_SEMANTIC[event.event_type]
      ?? { stage: "Task" as TraceStage, action: event.event_type, icon: "●" };

    switch (event.event_type) {

      case "tool_start": {
        if (pendingToolStart) nodes.push(flushToolStart(pendingToolStart));
        pendingToolStart = event;
        break;
      }

      case "tool_result": {
        if (pendingToolStart) {
          nodes.push(mergeTool(pendingToolStart, event, pendingThought));
          pendingToolStart = null;
        } else {
          nodes.push(standaloneNode(event, sem));
        }
        pendingThought = null;
        break;
      }

      case "thought": {
        if (pendingThought) nodes.push(standaloneNode(pendingThought, EVENT_TO_SEMANTIC["thought"]));
        pendingThought = event;
        break;
      }

      case "intermediate":
      case "warning": {
        if (pendingToolStart) { nodes.push(flushToolStart(pendingToolStart)); pendingToolStart = null; }
        if (pendingThought) { nodes.push(standaloneNode(pendingThought, EVENT_TO_SEMANTIC["thought"])); pendingThought = null; }
        nodes.push(intermediateNode(event, sem));
        break;
      }

      case "final": {
        if (pendingToolStart) { nodes.push(flushToolStart(pendingToolStart)); pendingToolStart = null; }
        if (pendingThought) { nodes.push(standaloneNode(pendingThought, EVENT_TO_SEMANTIC["thought"])); pendingThought = null; }
        nodes.push(finalNode(event, sem));
        break;
      }

      case "final_brief": {
        nodes.push(briefNode(event, sem));
        break;
      }

      case "status": {
        if (pendingToolStart) { nodes.push(flushToolStart(pendingToolStart)); pendingToolStart = null; }
        if (pendingThought) { nodes.push(standaloneNode(pendingThought, EVENT_TO_SEMANTIC["thought"])); pendingThought = null; }
        nodes.push(bareNode(event, sem));
        break;
      }

      default:
        break;
    }
  }

  // Flush remaining pending
  if (pendingToolStart) nodes.push(flushToolStart(pendingToolStart));
  if (pendingThought) nodes.push(standaloneNode(pendingThought, EVENT_TO_SEMANTIC["thought"]));

  return nodes;
}

// -- 节点构造 helpers ------------------------------------------------

function makeNode(event: RunEvent, sem: SemanticMapping, overrides: Partial<TraceNode> = {}): TraceNode {
  return {
    id: `tn-${event.task_id}-${event.seq}`,
    stage: sem.stage,
    action: overrides.action ?? sem.action,
    description: event.summary,
    status: "success",
    timestamp: event.timestamp,
    icon: sem.icon,
    ...overrides,
  };
}

function mergeTool(
  toolStart: RunEvent,
  toolResult: RunEvent,
  thought: RunEvent | null,
): TraceNode {
  const sem = EVENT_TO_SEMANTIC["tool_start"];
  const toolName = toolStart.detail?.tool
    ? String(toolStart.detail.tool)
    : toolStart.detail?.agent
      ? String(toolStart.detail.agent)
      : "";

  const desc = thought
    ? `${thought.summary} → ${toolStart.summary} → ${toolResult.summary}`
    : `${toolStart.summary} → ${toolResult.summary}`;

  return {
    id: `tn-${toolStart.task_id}-${toolStart.seq}`,
    stage: sem.stage,
    action: toolName || sem.action,
    description: desc,
    status: "success",
    timestamp: toolStart.timestamp,
    durationMs: computeDuration(toolStart.timestamp, toolResult.timestamp),
    icon: "🔧",
    input: toolStart.detail ? detailToBlock("CALL", { tool: toolName || undefined, ...toolStart.detail }) : undefined,
    output: toolResult.detail ? detailToBlock("RESULT", toolResult.detail) : textToBlock("RESULT", toolResult.summary),
  };
}

function flushToolStart(event: RunEvent): TraceNode {
  const sem = EVENT_TO_SEMANTIC["tool_start"];
  const toolName = event.detail?.tool
    ? String(event.detail.tool)
    : event.detail?.agent ? String(event.detail.agent) : "";
  return {
    id: `tn-${event.task_id}-${event.seq}`,
    stage: sem.stage,
    action: toolName || sem.action,
    description: event.summary,
    status: "running",
    timestamp: event.timestamp,
    icon: "🔧",
    input: event.detail ? detailToBlock("CALL", event.detail) : undefined,
  };
}

function standaloneNode(event: RunEvent, sem: SemanticMapping): TraceNode {
  return makeNode(event, sem);
}

function intermediateNode(event: RunEvent, sem: SemanticMapping): TraceNode {
  const category = event.detail?.category ? String(event.detail.category) : undefined;
  return {
    ...makeNode(event, sem, { action: category ?? sem.action }),
    output: event.detail ? detailToBlock("RESULT", event.detail) : undefined,
  };
}

function finalNode(event: RunEvent, sem: SemanticMapping): TraceNode {
  return {
    ...makeNode(event, sem),
    output: event.detail ? detailToBlock("RESULT", event.detail) : undefined,
  };
}

function briefNode(event: RunEvent, sem: SemanticMapping): TraceNode {
  return {
    ...makeNode(event, sem),
    output: event.detail ? detailToBlock("RESULT", event.detail) : undefined,
  };
}

function bareNode(event: RunEvent, sem: SemanticMapping): TraceNode {
  return makeNode(event, sem);
}

function computeDuration(startIso: string, endIso: string): number | undefined {
  const s = new Date(startIso).getTime();
  const e = new Date(endIso).getTime();
  if (isNaN(s) || isNaN(e) || e < s) return undefined;
  return e - s;
}
