# 执行转录流 → Agent 执行历史记录面板 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前的"执行流"改造成紧凑的 Agent 执行历史记录面板（Agent Trace History），支持语义化事件聚合、紧凑 timeline 布局、可展开命令/结果块、历史回看。

**Architecture:** 前端纯客户端改造 —— 在 `useTaskEvents` hook 返回的 `RunEvent[]` 之上增加语义聚合层（event→TraceNode adapter），将底层原始事件映射为语义化节点，渲染紧凑 timeline。不涉及后端改动。

**Tech Stack:** React 18+ / TypeScript / 纯 CSS（沿用项目现有 CSS 体系）

---

## 文件映射

### 新增
| 文件 | 职责 |
|------|------|
| `frontend/src/lib/trace-adapter.ts` | 原始事件 → 语义节点适配器（event→TraceNode mapping + grouping） |
| `frontend/src/components/workspace/TraceNodeView.tsx` | 单个语义节点渲染（dot + 阶段名/动作 + 描述 + CALL/RESULT 可展开块） |
| `frontend/src/components/workspace/TraceExpandableBlock.tsx` | 可展开内容块（CALL/INPUT/QUERY/RESULT/OUTPUT/ERROR） |
| `frontend/src/components/workspace/TraceRunHeader.tsx` | 顶部紧凑任务概览条 |

### 修改
| 文件 | 改动 |
|------|------|
| `frontend/src/components/workspace/ExecutionTimeline.tsx` | 完全重写 —— 不再渲染 raw events，改为消费 TraceNode[] |
| `frontend/src/lib/domain.ts` | 新增 TraceNode / TraceBlock 类型定义 |

### 删除
无。`useTaskEvents.ts` 保持不变，继续提供底层事件流。

---

## 架构总览

```
useTaskEvents(taskId) → RunEvent[]
        │
        ▼
trace-adapter.ts: adaptEvents(events) → TraceNode[]
   ┌── 1. 映射：event_type → stage + action label
   ├── 2. 聚合：tool_start + tool_result → 一个 Tool 节点
   ├── 3. 聚合：相邻 thought → 合并到前一个节点描述
   └── 4. 排序：按 seq 保序
        │
        ▼
ExecutionTimeline.tsx ← 消费 TraceNode[]
   ├── TraceRunHeader     ← 紧凑任务概览
   ├── TraceNodeView[0]   ← AgentTraceTimeline
   ├── TraceNodeView[1]
   │   ├── TraceExpandableBlock (CALL)
   │   └── TraceExpandableBlock (RESULT)
   ├── TraceNodeView[2]
   └── ...
```

---

## 关键类型定义

### TraceNode（领域模型中新增）

```typescript
// frontend/src/lib/domain.ts 新增

export type TraceStage =
  | "Task"
  | "LLM"
  | "RAG"
  | "Tool"
  | "Parser"
  | "Generator"
  | "Review";

export type TraceBlockType = "CALL" | "INPUT" | "QUERY" | "RESULT" | "OUTPUT" | "ERROR";

export type TraceBlock = {
  label: TraceBlockType;
  content: string;
  language?: "text" | "json" | "markdown";
  preview?: string;       // 折叠时显示的前几行
  isTruncated?: boolean;
};

export type TraceNode = {
  id: string;
  stage: TraceStage;
  action: string;          // "请求模型生成" / "检索参考规则" / "解析上传文档"
  description: string;     // 一句话说明
  status: "pending" | "running" | "success" | "error";
  timestamp: string;
  durationMs?: number;
  input?: TraceBlock;
  output?: TraceBlock;
  icon?: string;           // emoji 覆盖（默认按 stage 选取）
};
```

### 事件 → 语义映射表

```typescript
// trace-adapter.ts

const EVENT_TO_SEMANTIC: Record<string, { stage: TraceStage; action: string }> = {
  status:        { stage: "Task",      action: "任务状态变更" },
  thought:       { stage: "LLM",       action: "思路摘要" },
  tool_start:    { stage: "Tool",      action: "调用工具" },
  tool_result:   { stage: "Tool",      action: "返回结果" },
  intermediate:  { stage: "Review",    action: "中间结果" },
  warning:       { stage: "Task",      action: "警告" },
  final:         { stage: "Task",      action: "执行完成" },
  final_brief:   { stage: "Review",    action: "结果简报" },
};
```

### 聚合规则（核心逻辑）

```
tool_start + tool_result → 合并为一个 Tool 节点
    tool_start.summary → node.description
    tool_start.detail → node.input (CALL)
    tool_result.summary → 追加到 node.description
    tool_result.detail → node.output (RESULT)

thought 事件 → 不独立成节点
    如果紧接着一个 tool_start 之前 → 设为该 tool 节点的描述前缀
    如果独立出现 → 独立成 LLM 节点

intermediate → Review 节点
    summary → description
    detail → output (RESULT)

warning → Task 节点
    summary → description
    detail → output (ERROR)

final → Task 节点
    summary → description

final_brief → Review 节点
    detail.conclusion/files/risks → output (RESULT)

连续多个同类型 tool_start（无 tool_result 匹配） → 各自成节点
```

---

## 任务拆分

### Task 1: 新增领域类型 (TraceNode / TraceBlock)

**Files:** Modify `frontend/src/lib/domain.ts`

**Step 1:** 在 `domain.ts` 末尾（`RunSession` 定义之后）添加：

```typescript
// ═══════════════════════════════════════════════════════════════════════
// Agent Trace History — 语义化执行轨迹
// ═══════════════════════════════════════════════════════════════════════

export type TraceStage =
  | "Task"
  | "LLM"
  | "RAG"
  | "Tool"
  | "Parser"
  | "Generator"
  | "Review";

export type TraceBlockType = "CALL" | "INPUT" | "QUERY" | "RESULT" | "OUTPUT" | "ERROR";

export type TraceBlock = {
  label: TraceBlockType;
  content: string;
  language?: "text" | "json" | "markdown";
  preview?: string;
  isTruncated?: boolean;
};

export type TraceNode = {
  id: string;
  stage: TraceStage;
  action: string;
  description: string;
  status: "pending" | "running" | "success" | "error";
  timestamp: string;
  durationMs?: number;
  input?: TraceBlock;
  output?: TraceBlock;
  icon?: string;
};
```

**Step 2: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add frontend/src/lib/domain.ts
git commit -m "feat(domain): add TraceNode/TraceBlock types for semantic agent trace history"
```

---

### Task 2: 事件 → 语义节点适配器

**Files:** Create `frontend/src/lib/trace-adapter.ts`

**Complete file content:**

```typescript
/**
 * trace-adapter.ts —— 将底层 RunEvent 原始事件流转换为语义化 TraceNode 列表。
 *
 * 核心逻辑：
 *   1. event_type → stage + action 映射
 *   2. tool_start + tool_result → 合并为一个 Tool 节点
 *   3. thought → 不独立成节点（合并到后续 tool 节点描述）
 *   4. intermediate / warning 各自成节点
 */

import type { RunEvent } from "./useTaskEvents";
import type { TraceNode, TraceBlock, TraceStage } from "./domain";

// ── 事件 → 语义映射 ──────────────────────────────────────────────────

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

// ── detail → TraceBlock ───────────────────────────────────────────────

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
  return {
    label,
    content,
    language: "json",
    preview,
    isTruncated: lines.length > maxPreviewLines,
  };
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
  return {
    label,
    content: text,
    language: "text",
    preview,
    isTruncated: lines.length > maxPreviewLines,
  };
}

// ── 聚合适配器 ────────────────────────────────────────────────────────

export function adaptEvents(rawEvents: RunEvent[]): TraceNode[] {
  const nodes: TraceNode[] = [];
  let pendingToolStart: RunEvent | null = null;
  let pendingThought: RunEvent | null = null;

  for (const event of rawEvents) {
    // 跳过 seq <= 0 的状态事件（由 InMemoryTaskManager 发布，不在 trace 流中展示）
    if (event.event_type === "status" && event.seq <= 0) continue;

    const sem = EVENT_TO_SEMANTIC[event.event_type] ?? { stage: "Task" as TraceStage, action: event.event_type, icon: "●" };

    switch (event.event_type) {

      case "tool_start": {
        // 如果有前一个 tool_start 未被匹配，先 flush 成独立节点
        if (pendingToolStart) {
          nodes.push(flushToolStart(pendingToolStart));
        }
        pendingToolStart = event;
        break;
      }

      case "tool_result": {
        if (pendingToolStart) {
          // 合并 tool_start + tool_result
          nodes.push(mergeTool(pendingToolStart, event, pendingThought));
          pendingToolStart = null;
        } else {
          // 孤立的 tool_result（没有匹配的 tool_start）
          nodes.push(standaloneNode(event, sem));
        }
        pendingThought = null;
        break;
      }

      case "thought": {
        // 暂存，可能合并到后续 tool_start
        if (pendingThought) {
          nodes.push(standaloneNode(pendingThought, EVENT_TO_SEMANTIC["thought"]));
        }
        pendingThought = event;
        break;
      }

      case "intermediate":
      case "warning": {
        // 先 flush 任何 pending
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
        // final_brief 合并到最近的 final 节点或独立成节点
        nodes.push(briefNode(event, sem));
        break;
      }

      case "status": {
        // seq > 0 的 status（由 generate_report 发布，如 "开始 CPRA 合规诊断"）
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

// ── 节点构造 helpers ──────────────────────────────────────────────────

function makeNode(
  event: RunEvent,
  sem: SemanticMapping,
  overrides: Partial<TraceNode> = {},
): TraceNode {
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
    input: toolStart.detail
      ? detailToBlock("CALL", { tool: toolName, ...toolStart.detail })
      : undefined,
    output: toolResult.detail
      ? detailToBlock("RESULT", toolResult.detail)
      : textToBlock("RESULT", toolResult.summary),
  };
}

function flushToolStart(event: RunEvent): TraceNode {
  const sem = EVENT_TO_SEMANTIC["tool_start"];
  const toolName = event.detail?.tool
    ? String(event.detail.tool)
    : event.detail?.agent
      ? String(event.detail.agent)
      : "";
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
  const category = event.detail?.category
    ? String(event.detail.category)
    : undefined;
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
```

**Commit:**
```bash
git add frontend/src/lib/trace-adapter.ts
git commit -m "feat(trace): add event→TraceNode semantic adapter with tool_start/tool_result grouping"
```

---

### Task 3: TraceRunHeader — 紧凑任务概览条

**Files:** Create `frontend/src/components/workspace/TraceRunHeader.tsx`

```tsx
import type { TraceNode } from "../../lib/domain";

type Props = {
  moduleLabel: string;
  status: "running" | "completed" | "failed" | "empty";
  taskId: string | null;
  startedAt?: string;
  completedAt?: string;
  nodeCount: number;
};

function fmtTime(iso?: string): string {
  if (!iso) return "--";
  return new Date(iso).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function fmtDuration(ms?: number): string {
  if (!ms) return "--";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function TraceRunHeader({ moduleLabel, status, taskId, startedAt, completedAt, nodeCount }: Props) {
  return (
    <div className="trace-run-header">
      <div className="trace-run-header-left">
        <span className="trace-run-module">{moduleLabel}</span>
        <span className={`trace-run-badge badge-${status}`}>
          {status === "running" ? "RUNNING" : status === "completed" ? "COMPLETED" : status === "failed" ? "FAILED" : "--"}
        </span>
        {taskId ? <code className="trace-run-id">{taskId.slice(0, 12)}…</code> : null}
      </div>
      <div className="trace-run-header-right">
        <span>开始 {fmtTime(startedAt)}</span>
        <span className="trace-run-sep">·</span>
        <span>完成 {fmtTime(completedAt)}</span>
        <span className="trace-run-sep">·</span>
        <span>事件 {nodeCount}</span>
      </div>
    </div>
  );
}
```

**Commit:**
```bash
git add frontend/src/components/workspace/TraceRunHeader.tsx
git commit -m "feat(frontend): add TraceRunHeader compact status bar"
```

---

### Task 4: TraceExpandableBlock — 可展开内容块

**Files:** Create `frontend/src/components/workspace/TraceExpandableBlock.tsx`

```tsx
import { useState } from "react";
import type { TraceBlock } from "../../lib/domain";

type Props = {
  block: TraceBlock;
};

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

export function TraceExpandableBlock({ block }: Props) {
  const [expanded, setExpanded] = useState(false);
  const needsExpand = block.isTruncated && block.preview;
  const displayContent = expanded || !needsExpand ? block.content : (block.preview ?? block.content);

  return (
    <div className="trace-block">
      <div className="trace-block-head">
        <span className="trace-block-label">{block.label}</span>
        <span className="trace-block-actions">
          <button className="trace-block-copy" onClick={() => copyToClipboard(block.content)} title="复制">
            ⎘
          </button>
          {needsExpand ? (
            <button className="trace-block-expand" onClick={() => setExpanded((v) => !v)}>
              {expanded ? "收起" : "展开更多"}
            </button>
          ) : null}
        </span>
      </div>
      <pre className={`trace-block-content ${block.language === "json" ? "lang-json" : ""}`}>
        {displayContent}
      </pre>
    </div>
  );
}
```

**Commit:**
```bash
git add frontend/src/components/workspace/TraceExpandableBlock.tsx
git commit -m "feat(frontend): add TraceExpandableBlock with copy and expand/collapse"
```

---

### Task 5: TraceNodeView — 单个语义节点渲染

**Files:** Create `frontend/src/components/workspace/TraceNodeView.tsx`

```tsx
import type { TraceNode } from "../../lib/domain";
import { TraceExpandableBlock } from "./TraceExpandableBlock";

const STAGE_COLORS: Record<string, string> = {
  Task: "#6b7280",
  LLM: "#7c3aed",
  RAG: "#2563eb",
  Tool: "#059669",
  Parser: "#ea580c",
  Generator: "#8b5cf6",
  Review: "#0891b2",
};

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function TraceNodeView({ node }: { node: TraceNode }) {
  const color = STAGE_COLORS[node.stage] ?? "#6b7280";

  return (
    <div className={`trace-node trace-node-${node.status}`} style={{ borderLeftColor: color }}>
      {/* dot */}
      <div className="trace-node-dot" style={{ background: node.status === "error" ? "#dc2626" : color }} />

      {/* header */}
      <div className="trace-node-header">
        <span className="trace-node-stage" style={{ color }}>{node.icon} {node.stage}</span>
        <span className="trace-node-action">｜{node.action}</span>
        <span className="trace-node-time">{fmtTime(node.timestamp)}</span>
      </div>

      {/* description */}
      {node.description ? (
        <div className="trace-node-desc">{node.description}</div>
      ) : null}

      {/* duration */}
      {node.durationMs != null && node.durationMs > 0 ? (
        <div className="trace-node-duration">⏱ {(node.durationMs / 1000).toFixed(1)}s</div>
      ) : null}

      {/* input block */}
      {node.input ? <TraceExpandableBlock block={node.input} /> : null}

      {/* output block */}
      {node.output ? <TraceExpandableBlock block={node.output} /> : null}
    </div>
  );
}
```

**Commit:**
```bash
git add frontend/src/components/workspace/TraceNodeView.tsx
git commit -m "feat(frontend): add TraceNodeView with compact dot+label+expandable blocks"
```

---

### Task 6: 重写 ExecutionTimeline

**Files:** Rewrite `frontend/src/components/workspace/ExecutionTimeline.tsx`

**Changes:**

1. 使用 `useMemo` 调用 `adaptEvents(events)` 得到 `TraceNode[]`
2. 顶部改为 `TraceRunHeader`
3. 主体渲染 `TraceNodeView` 列表
4. 空状态文案更新
5. 自滚动到最新节点的行为保留

**核心逻辑：**

```tsx
import { useMemo, useEffect, useRef } from "react";
import { useLang } from "../../lib/language";
import { useTaskEvents } from "../../lib/useTaskEvents";
import { adaptEvents } from "../../lib/trace-adapter";
import { TraceRunHeader } from "./TraceRunHeader";
import { TraceNodeView } from "./TraceNodeView";
import type { TraceNode } from "../../lib/domain";

type Props = {
  taskId: string | null;
  moduleLabel?: string;
};

export function ExecutionTimeline({ taskId, moduleLabel = "" }: Props) {
  const { lang } = useLang();
  const events = useTaskEvents(taskId);
  const bodyRef = useRef<HTMLDivElement>(null);

  // 语义聚合：原始事件 → 语义节点
  const nodes: TraceNode[] = useMemo(() => {
    if (events.length === 0) return [];
    return adaptEvents(events);
  }, [events]);

  // 自动滚动到最新（仅在运行中）
  const prevNodeCount = useRef(0);
  const isRunning = nodes.length > 0 && nodes[nodes.length - 1].status !== "success";
  useEffect(() => {
    if (isRunning && nodes.length > prevNodeCount.current && bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
    prevNodeCount.current = nodes.length;
  }, [nodes.length, isRunning]);

  // 推导运行状态
  const runStatus = events.length === 0
    ? "empty"
    : nodes.some((n) => n.status === "error") ? "failed"
    : events.some((e) => e.event_type === "final") ? "completed"
    : "running";

  const firstTs = nodes[0]?.timestamp;
  const lastTs = nodes[nodes.length - 1]?.timestamp;

  return (
    <section className="execution-timeline">
      <TraceRunHeader
        moduleLabel={moduleLabel}
        status={runStatus}
        taskId={taskId}
        startedAt={firstTs}
        completedAt={runStatus === "completed" ? lastTs : undefined}
        nodeCount={nodes.length}
      />

      <div className="trace-timeline-body" ref={bodyRef}>
        {nodes.length === 0 ? (
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
```

**同时移除不再需要的部分：**
- 删除 `ICON_MAP`, `COLOR_MAP`, `TimelineRow`, `extractStageName`
- 删除 `useAppStore` import（不再 dispatch 到 app-store）
- 删除 `sessionIdRef`, `pendingStagesRef`, `seenSeqs` 等 old refs
- 删除整个 `useEffect` dispatch 桥接逻辑
- 删除 cleanup `useEffect`
- 删除 `taskSpaceId` prop（不再需要）

**Commit:**
```bash
git add frontend/src/components/workspace/ExecutionTimeline.tsx
git commit -m "feat(frontend): rewrite ExecutionTimeline as semantic Agent Trace History"
```

---

### Task 7: WorkspaceShell 调用接口对齐 + RunBrief 修复

**Files:** Modify `frontend/src/components/workspace/WorkspaceShell.tsx`

**当前情况：** `ExecutionTimeline` 现在需要 `moduleLabel` 而非 `taskSpaceId`。

**修改：**

```tsx
// 找到 <ExecutionTimeline ...> 调用处，调整为：
<ExecutionTimeline 
  taskId={latestRun?.asyncTaskId ?? null} 
  moduleLabel={t(`moduleLabel_${moduleKey}`) ?? moduleKey.toUpperCase()}
/>
```

**Commit:**
```bash
git add frontend/src/components/workspace/WorkspaceShell.tsx
git commit -m "fix(frontend): align ExecutionTimeline props to new Agent Trace History API"
```

---

### Task 8: CSS 紧凑样式

**Files:** 在项目的全局 CSS 文件或 workspace 相关 CSS 文件中追加样式。

**核心样式规则：**

```css
/* ── Trace Run Header ── */
.trace-run-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; background: #f9fafb; border-bottom: 1px solid #e5e7eb;
  font-size: 12px; color: #6b7280;
}
.trace-run-module { font-weight: 600; color: #1f2937; margin-right: 8px; }
.trace-run-badge { padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
.badge-running { background: #dbeafe; color: #1d4ed8; }
.badge-completed { background: #d1fae5; color: #065f46; }
.badge-failed { background: #fee2e2; color: #991b1b; }
.badge-empty { background: #f3f4f6; color: #6b7280; }
.trace-run-id { font-size: 10px; color: #9ca3af; margin-left: 6px; }
.trace-run-sep { margin: 0 4px; color: #d1d5db; }
.trace-run-header-right { display: flex; align-items: center; gap: 0; }

/* ── Timeline Body ── */
.trace-timeline-body { flex: 1; overflow-y: auto; padding: 12px 16px; }
.trace-timeline-line { position: relative; padding-left: 18px; }
.trace-timeline-line::before {
  content: ""; position: absolute; left: 6px; top: 0; bottom: 0;
  width: 1px; background: #d1d5db;
}

/* ── Trace Node ── */
.trace-node {
  position: relative; padding: 6px 0 10px 14px;
  border-left: none; font-size: 13px;
}
.trace-node-dot {
  position: absolute; left: -5px; top: 10px;
  width: 8px; height: 8px; border-radius: 50%;
  border: 2px solid white; z-index: 1;
}
.trace-node-error .trace-node-dot { background: #dc2626; }
.trace-node-running .trace-node-dot { animation: pulse-dot 1.5s infinite; }
@keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

.trace-node-header {
  display: flex; align-items: baseline; gap: 2px;
  font-size: 13px; line-height: 1.4;
}
.trace-node-stage { font-weight: 600; }
.trace-node-action { color: #374151; }
.trace-node-time { margin-left: auto; font-size: 11px; color: #9ca3af; white-space: nowrap; }

.trace-node-desc {
  margin-top: 2px; font-size: 12px; color: #6b7280; line-height: 1.4;
}
.trace-node-duration {
  margin-top: 2px; font-size: 11px; color: #9ca3af;
}

/* ── Trace Block (CALL / RESULT / etc) ── */
.trace-block {
  margin-top: 6px; border: 1px solid #e5e7eb; border-radius: 4px;
  overflow: hidden; font-size: 12px;
}
.trace-block-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 3px 8px; background: #f9fafb; border-bottom: 1px solid #e5e7eb;
}
.trace-block-label {
  font-size: 10px; font-weight: 700; color: #6b7280; text-transform: uppercase;
  letter-spacing: 0.05em;
}
.trace-block-actions { display: flex; gap: 4px; }
.trace-block-copy, .trace-block-expand {
  border: none; background: none; font-size: 10px; color: #9ca3af; cursor: pointer; padding: 1px 4px;
}
.trace-block-copy:hover, .trace-block-expand:hover { color: #374151; }

.trace-block-content {
  padding: 6px 8px; margin: 0; font-size: 11px; line-height: 1.45;
  font-family: "SF Mono", "Menlo", "Monaco", monospace;
  white-space: pre; overflow-x: auto; overflow-y: hidden;
  max-height: 140px; overflow-y: auto;
  background: #fafafa; color: #374151;
}
.trace-block-content.lang-json { /* json 可折叠 */ }

/* ── Empty State ── */
.trace-empty {
  text-align: center; padding: 40px 20px; color: #9ca3af; font-size: 13px;
}
```

**Commit:**
```bash
git add frontend/src/index.css   # 或项目实际使用的 CSS 文件路径
git commit -m "style(frontend): add compact Agent Trace History CSS — small fonts, tight spacing, muted colors"
```

---

### Task 9: 端到端验证

**Step 1:** TypeScript check
```bash
cd frontend && npx tsc --noEmit
```

**Step 2:** 启动前端验证
```bash
cd frontend && npm run dev
```

**Step 3:** 验证项：
- [ ] 进入 CPRA workspace，运行一个测试案例
- [ ] "执行流" tab 显示紧凑的历史记录
- [ ] tool_start + tool_result 被合并成一个 Tool 节点
- [ ] 每个节点有 CALL / RESULT 可展开块
- [ ] 字体小、间距紧、颜色弱
- [ ] 横向滚动的 JSON 块不会撑破布局
- [ ] 复制按钮可用
- [ ] 展开/收起可用
- [ ] 自滚动到最新节点
- [ ] 完成后的历史记录保留

**Step 4:** Commit
```bash
git add -A && git commit -m "chore: final verification — Agent Trace History E2E pass"
```

---

## 验证检查清单

- [ ] `TraceNode` 类型定义完整
- [ ] `adaptEvents()` 正确合并 tool_start + tool_result
- [ ] 不显示 `llm_chat_request` / `llm_chat_response` 等原始事件名
- [ ] 节点显示 `Tool｜调用` / `LLM｜思路摘要` 等语义标签
- [ ] 字体 11-13px，间距 12-18px
- [ ] 颜色低饱和（灰蓝系）
- [ ] CALL/RESULT 块可折叠/展开/复制
- [ ] 长 JSON/代码横向滚动，不强制换行
- [ ] 空状态文案："暂无执行记录..."
- [ ] 顶部状态条紧凑（一行显示 module + status + id + 时间）
- [ ] 自滚动在运行中生效，用户手动滚动时暂停
- [ ] TypeScript 零错误
