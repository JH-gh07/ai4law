/**
 * trace-adapter.ts
 *
 * 将底层 RunEvent 原始事件流转换为可长期回看的 Agent Trace History。
 * 目标不是直出 raw event，而是按“用户能理解的动作节点”聚合、翻译、压缩。
 */

import type { RunEvent } from "./useTaskEvents";
import type { TraceBlock, TraceNode, TraceStage } from "./domain";

type SemanticMapping = {
  stage: TraceStage;
  action: string;
  icon: string;
  badge?: string;
};

const EVENT_TO_SEMANTIC: Record<RunEvent["event_type"], SemanticMapping> = {
  status: { stage: "Task", action: "任务状态更新", icon: "●", badge: "TASK" },
  thought: { stage: "LLM", action: "判断摘要", icon: "◌", badge: "THOUGHT" },
  tool_start: { stage: "Tool", action: "调用工具", icon: "●", badge: "CALL" },
  tool_result: { stage: "Tool", action: "返回结果", icon: "●", badge: "RESULT" },
  intermediate: { stage: "Review", action: "中间结果", icon: "●", badge: "INTERMEDIATE" },
  warning: { stage: "Review", action: "风险提示", icon: "●", badge: "WARNING" },
  final: { stage: "Task", action: "工作流完成", icon: "●", badge: "FINAL" },
  final_brief: { stage: "Review", action: "客户简报", icon: "●", badge: "BRIEF" },
};

function readString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : undefined;
}

function shorten(value: string | undefined, limit = 120): string | undefined {
  if (!value) return undefined;
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
}

function stringify(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

function isScalar(value: unknown): value is string | number | boolean {
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean";
}

function normalizeWhitespace(value: string | undefined): string | undefined {
  if (!value) return undefined;
  return value.replace(/\s+/g, " ").trim();
}

function summarizeArray(value: unknown): string | undefined {
  if (!Array.isArray(value) || value.length === 0) return undefined;
  const preview = value
    .slice(0, 3)
    .map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object") {
        const record = item as Record<string, unknown>;
        return readString(record.title)
          ?? readString(record.name)
          ?? readString(record.id)
          ?? stringify(item);
      }
      return String(item);
    })
    .join("；");
  return value.length > 3 ? `${preview} 等 ${value.length} 项` : preview;
}

function formatDetailValue(value: unknown, indent = "  "): string[] {
  if (value == null) return ["null"];
  if (typeof value === "string") {
    const lines = value.split("\n").map((line) => line.trimEnd()).filter((line) => line.length > 0);
    return lines.length > 0 ? lines : [value];
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return [String(value)];
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return ["[]"];
    if (value.every((item) => isScalar(item))) {
      return [value.map((item) => String(item)).join(" | ")];
    }
    return value.slice(0, 6).map((item) => {
      if (typeof item === "string") return `- ${item}`;
      if (item && typeof item === "object") {
        const record = item as Record<string, unknown>;
        const summary = readString(record.title)
          ?? readString(record.name)
          ?? readString(record.id)
          ?? normalizeWhitespace(JSON.stringify(item));
        return `- ${summary ?? stringify(item)}`;
      }
      return `- ${String(item)}`;
    });
  }
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const entries = Object.entries(record);
    if (entries.length === 0) return ["{}"];
    return entries.slice(0, 8).flatMap(([key, nested]) => {
      const nestedLines = formatDetailValue(nested, `${indent}  `);
      if (nestedLines.length === 1) return [`${key}: ${nestedLines[0]}`];
      return [`${key}:`, ...nestedLines.map((line) => `${indent}${line}`)];
    });
  }
  return [String(value)];
}

function formatDetailContent(detail: Record<string, unknown>): string {
  const priority = [
    "tool",
    "agent",
    "provider",
    "model",
    "task",
    "query",
    "context",
    "category",
    "state",
    "error",
    "count",
    "hit_count",
    "issues_count",
    "chapter_count",
    "artifact_path",
    "preview",
    "files",
    "risks",
    "notices",
    "next_steps",
    "stats",
    "system",
    "user",
    "content",
  ];

  const orderedEntries = Object.entries(detail)
    .filter(([key, value]) => key !== "raw_name" && value !== undefined && value !== null && value !== "")
    .sort(([left], [right]) => {
      const leftIndex = priority.indexOf(left);
      const rightIndex = priority.indexOf(right);
      if (leftIndex === -1 && rightIndex === -1) return left.localeCompare(right);
      if (leftIndex === -1) return 1;
      if (rightIndex === -1) return -1;
      return leftIndex - rightIndex;
    });

  return orderedEntries
    .flatMap(([key, value]) => {
      const lines = formatDetailValue(value);
      if (lines.length === 1) return `${key}: ${lines[0]}`;
      return [`${key}:`, ...lines.map((line) => `  ${line}`)];
    })
    .join("\n");
}

function computeDuration(startIso: string, endIso: string): number | undefined {
  const s = new Date(startIso).getTime();
  const e = new Date(endIso).getTime();
  if (isNaN(s) || isNaN(e) || e < s) return undefined;
  return e - s;
}

function semanticFromDetail(event: RunEvent): SemanticMapping {
  const detail = event.detail ?? {};
  const tool = readString(detail.tool);
  const agent = readString(detail.agent);
  const category = readString(detail.category);
  const rawName = readString(detail.raw_name);
  const summary = event.summary;

  if (event.event_type === "status") {
    return {
      stage: "Task",
      action: /开始|创建|启动/.test(summary) ? "创建并启动任务" : /完成|结束/.test(summary) ? "任务完成" : "任务状态更新",
      icon: "●",
      badge: "TASK",
    };
  }

  if (tool || agent) {
    const name = tool || agent || "";

    if (/retriev|rag|search|检索|citation/i.test(name) || /检索|引用|命中/.test(summary)) {
      return { stage: "RAG", action: "检索法规与依据", icon: "●", badge: "RAG" };
    }
    if (/parse|extract|document_structure|attachment/i.test(name) || /解析|提取|文档结构/.test(summary)) {
      return { stage: "Parser", action: "解析输入与附件", icon: "●", badge: "PARSER" };
    }
    if (/chapter|draft|generation|render/i.test(name) || /章节生成|报告渲染|外部草拟|生成/.test(summary)) {
      return { stage: "Generator", action: "生成报告内容", icon: "●", badge: "GEN" };
    }
    if (/consistency|review|qa|evidence|verify/i.test(name) || /一致性|审查|证据|校验/.test(summary)) {
      return { stage: "Review", action: "审查与校验", icon: "●", badge: "REVIEW" };
    }
    if (/llm|chat/i.test(name)) {
      return { stage: "LLM", action: "请求模型生成", icon: "●", badge: "LLM" };
    }
    return { stage: "Tool", action: shorten(name, 40) ?? "调用工具", icon: "●", badge: "TOOL" };
  }

  if (rawName) {
    if (/per_issue_rag|agent_rag_reformulation/i.test(rawName)) {
      return { stage: "RAG", action: /reformulation/i.test(rawName) ? "重构检索查询" : "按问题补充检索", icon: "●", badge: "RAG" };
    }
    if (/retrieval_hits|rag_plans|rag_hit/i.test(rawName)) {
      return { stage: "RAG", action: /plans/i.test(rawName) ? "规划检索策略" : "检索法规与依据", icon: "●", badge: "RAG" };
    }
    if (/parsed_document_raw|profile_extracted|facts_built|transfer_chain_raw/i.test(rawName)) {
      return { stage: "Parser", action: "提取结构化事实", icon: "●", badge: "PARSER" };
    }
    if (/issues_built/i.test(rawName)) {
      return { stage: "Review", action: "生成问题清单", icon: "●", badge: "REVIEW" };
    }
    if (/evidence_built/i.test(rawName)) {
      return { stage: "Review", action: "构建证据链", icon: "●", badge: "REVIEW" };
    }
    if (/context_pack_built/i.test(rawName)) {
      return { stage: "Generator", action: "构建生成上下文", icon: "●", badge: "GEN" };
    }
    if (/agent_external_draft|chapters_generated|generate_chapters|render/i.test(rawName)) {
      return { stage: "Generator", action: "生成报告章节", icon: "●", badge: "GEN" };
    }
    if (/agent_internal_review|agent_consistency_repair|report_review|alignment|repair_pass|agent_repair_check|agent_chapter_consistency/i.test(rawName)) {
      return { stage: "Review", action: "执行一致性审查", icon: "●", badge: "REVIEW" };
    }
    if (/agent_rule_boundary|rule_engine_result/i.test(rawName)) {
      return { stage: "Review", action: "执行规则边界分析", icon: "●", badge: "REVIEW" };
    }
    if (/agent_dpia_need|path_diagnosis|need_detection_rule|need_diagnosis_enriched/i.test(rawName)) {
      return { stage: "LLM", action: "生成判断与路径分析", icon: "●", badge: "LLM" };
    }
    if (/agent_processing_activity|agent_risk_assessment|agent_mitigation_mapping|agent_dpo_consultation|agent_clause_semantic|agent_tia_effectiveness|agent_remediation|agent_evidence_priority/i.test(rawName)) {
      return { stage: "Generator", action: "生成专项分析结果", icon: "●", badge: "GEN" };
    }
  }

  if (category) {
    if (/artifact|output|report/i.test(category)) {
      return { stage: "Generator", action: "生成中间产物", icon: "●", badge: "OUTPUT" };
    }
    if (/retrieval|rag/i.test(category)) {
      return { stage: "RAG", action: "输出检索结果", icon: "●", badge: "RAG" };
    }
    return { stage: "Review", action: shorten(category, 32) ?? "中间结果", icon: "●", badge: "INTERMEDIATE" };
  }

  const base = EVENT_TO_SEMANTIC[event.event_type];
  return base ?? { stage: "Task", action: event.event_type, icon: "●" };
}

function detailToBlock(
  label: TraceBlock["label"],
  detail: Record<string, unknown> | null | undefined,
  maxPreviewLines = 8,
): TraceBlock | undefined {
  if (!detail || Object.keys(detail).length === 0) return undefined;
  const content = formatDetailContent(detail);
  const lines = content.split("\n");
  const preview = lines.length > maxPreviewLines
    ? lines.slice(0, maxPreviewLines).join("\n") + "\n..."
    : content;
  return {
    label,
    content,
    language: "text",
    preview,
    isTruncated: lines.length > maxPreviewLines,
    summary: summarizeDetail(detail),
  };
}

function textToBlock(
  label: TraceBlock["label"],
  text: string | undefined,
  maxPreviewLines = 8,
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
    summary: shorten(text.replace(/\s+/g, " "), 120),
  };
}

function summarizeDetail(detail: Record<string, unknown> | null | undefined): string | undefined {
  if (!detail) return undefined;

  const tool = readString(detail.tool);
  const agent = readString(detail.agent);
  const category = readString(detail.category);
  const rawName = readString(detail.raw_name);
  const state = readString(detail.state);
  const error = readString(detail.error);
  const module = readString(detail.module);
  const company = readString(detail.company);
  const preview = readString(detail.preview);
  const artifactPath = readString(detail.artifact_path);

  const countKeys = [
    "count",
    "hit_count",
    "issues_count",
    "output_files_count",
    "chapter_count",
    "gap_count",
  ] as const;

  const countFragments = countKeys
    .map((key) => detail[key])
    .filter((value) => typeof value === "number")
    .map((value) => `${value} 项`);

  const filesSummary = summarizeArray(detail.files);
  const risksSummary = summarizeArray(detail.risks);
  const issuesSummary = summarizeArray(detail.issues);
  const hitsSummary = summarizeArray(detail.hits);

  const parts = [
    tool || agent,
    category,
    state,
    module,
    company,
    preview,
    artifactPath,
    filesSummary,
    risksSummary,
    issuesSummary,
    hitsSummary,
    ...countFragments,
  ]
    .filter((item): item is string => !!item && item.trim().length > 0)
    .slice(0, 4);

  if (error) {
    parts.unshift(`错误：${error}`);
  }
  if (parts.length > 0) return parts.join(" · ");
  return rawName;
}

function chooseInputLabel(sem: SemanticMapping): TraceBlock["label"] {
  if (sem.stage === "RAG") return "QUERY";
  if (sem.stage === "Parser") return "INPUT";
  return "CALL";
}

function chooseOutputLabel(
  sem: SemanticMapping,
  detail: Record<string, unknown> | null | undefined,
  status: TraceNode["status"],
  eventType: RunEvent["event_type"],
): TraceBlock["label"] {
  if (status === "error" || readString(detail?.error)) return "ERROR";
  if (eventType === "warning") return "ERROR";
  if (sem.stage === "Parser" || eventType === "intermediate" || eventType === "final_brief") return "OUTPUT";
  return "RESULT";
}

function buildHumanDetail(
  lines: Array<string | undefined>,
): string | undefined {
  const normalized = lines
    .map((line) => normalizeWhitespace(line))
    .filter((line, index, arr): line is string => !!line && arr.indexOf(line) === index);
  return normalized.length > 0 ? normalized.join("\n") : undefined;
}

function summaryLine(event: RunEvent, fallback: string): string {
  return shorten(normalizeWhitespace(event.summary), 120) ?? fallback;
}

function rawEventIds(...events: Array<RunEvent | null | undefined>): string[] {
  return events
    .map((event) => event?.event_id)
    .filter((eventId): eventId is string => typeof eventId === "string" && eventId.length > 0);
}

function makeNode(event: RunEvent, sem: SemanticMapping, overrides: Partial<TraceNode> = {}): TraceNode {
  return {
    id: `tn-${event.task_id}-${event.seq}`,
    stage: sem.stage,
    action: overrides.action ?? sem.action,
    description: overrides.description ?? shorten(event.summary, 96) ?? "",
    detail: overrides.detail,
    status: overrides.status ?? "success",
    timestamp: event.timestamp,
    icon: sem.icon,
    badge: overrides.badge ?? sem.badge,
    rawEventIds: overrides.rawEventIds ?? rawEventIds(event),
    ...overrides,
  };
}

function mergeTool(toolStart: RunEvent, toolResult: RunEvent, thought: RunEvent | null): TraceNode {
  const sem = semanticFromDetail(toolStart);
  const toolName = readString(toolStart.detail?.tool) ?? readString(toolStart.detail?.agent);
  const callSummary = summarizeDetail(toolStart.detail);
  const resultSummary = summarizeDetail(toolResult.detail);
  const status = readString(toolResult.detail?.error) ? "error" : "success";

  return makeNode(toolStart, sem, {
    action: sem.action,
    description: thought?.summary
      ? summaryLine(thought, sem.action)
      : summaryLine(toolStart, sem.action),
    detail: buildHumanDetail([
      toolName ? `调用对象：${toolName}` : undefined,
      callSummary ? `调用摘要：${callSummary}` : undefined,
      resultSummary ? `结果摘要：${resultSummary}` : undefined,
    ]),
    status,
    durationMs: computeDuration(toolStart.timestamp, toolResult.timestamp),
    input: toolStart.detail ? detailToBlock(chooseInputLabel(sem), toolStart.detail) : undefined,
    output: toolResult.detail
      ? detailToBlock(chooseOutputLabel(sem, toolResult.detail, status, toolResult.event_type), toolResult.detail)
      : textToBlock(chooseOutputLabel(sem, null, status, toolResult.event_type), toolResult.summary),
    rawEventIds: rawEventIds(toolStart, thought, toolResult),
  });
}

function flushToolStart(event: RunEvent): TraceNode {
  const sem = semanticFromDetail(event);
  const toolName = readString(event.detail?.tool) ?? readString(event.detail?.agent);
  return makeNode(event, sem, {
    description: summaryLine(event, sem.action),
    detail: buildHumanDetail([
      toolName ? `调用对象：${toolName}` : undefined,
      summarizeDetail(event.detail) ? `调用摘要：${summarizeDetail(event.detail)}` : undefined,
    ]),
    status: "running",
    input: event.detail ? detailToBlock(chooseInputLabel(sem), event.detail) : undefined,
  });
}

function standaloneNode(event: RunEvent): TraceNode {
  const sem = semanticFromDetail(event);
  const status = readString(event.detail?.error) ? "error" : "success";
  return makeNode(event, sem, {
    description: summaryLine(event, sem.action),
    detail: summarizeDetail(event.detail),
    status,
    output: event.detail
      ? detailToBlock(chooseOutputLabel(sem, event.detail, status, event.event_type), event.detail)
      : undefined,
  });
}

function intermediateNode(event: RunEvent): TraceNode {
  const sem = semanticFromDetail(event);
  const status = event.event_type === "warning" ? "error" : "success";
  return makeNode(event, sem, {
    description: summaryLine(event, sem.action),
    detail: summarizeDetail(event.detail),
    status,
    output: event.detail
      ? detailToBlock(chooseOutputLabel(sem, event.detail, status, event.event_type), event.detail)
      : undefined,
  });
}

function finalNode(event: RunEvent): TraceNode {
  const sem = semanticFromDetail(event);
  return makeNode(event, sem, {
    description: summaryLine(event, sem.action),
    detail: summarizeDetail(event.detail),
    output: event.detail ? detailToBlock("RESULT", event.detail) : undefined,
  });
}

function briefNode(event: RunEvent): TraceNode {
  const sem = semanticFromDetail(event);
  const conclusion = readString(event.detail?.conclusion);
  return makeNode(event, sem, {
    description: conclusion ?? summaryLine(event, sem.action),
    detail: summarizeDetail(event.detail),
    output: event.detail ? detailToBlock("OUTPUT", event.detail) : undefined,
  });
}

function bareNode(event: RunEvent): TraceNode {
  const sem = semanticFromDetail(event);
  const status = readString(event.detail?.state);
  return makeNode(event, sem, {
    description: status ? `${summaryLine(event, sem.action)} · ${status}` : summaryLine(event, sem.action),
    detail: summarizeDetail(event.detail),
    status: /failed|error|cancel/i.test(status ?? "") ? "error" : "success",
  });
}

export function adaptEvents(rawEvents: RunEvent[]): TraceNode[] {
  const nodes: TraceNode[] = [];
  let pendingToolStart: RunEvent | null = null;
  let pendingThought: RunEvent | null = null;

  for (const event of rawEvents) {
    if (event.event_type === "status" && event.seq <= 0) continue;

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
          nodes.push(standaloneNode(event));
        }
        pendingThought = null;
        break;
      }
      case "thought": {
        if (pendingThought) nodes.push(standaloneNode(pendingThought));
        pendingThought = event;
        break;
      }
      case "intermediate":
      case "warning": {
        if (pendingToolStart) {
          nodes.push(flushToolStart(pendingToolStart));
          pendingToolStart = null;
        }
        if (pendingThought) {
          nodes.push(standaloneNode(pendingThought));
          pendingThought = null;
        }
        nodes.push(intermediateNode(event));
        break;
      }
      case "final": {
        if (pendingToolStart) {
          nodes.push(flushToolStart(pendingToolStart));
          pendingToolStart = null;
        }
        if (pendingThought) {
          nodes.push(standaloneNode(pendingThought));
          pendingThought = null;
        }
        nodes.push(finalNode(event));
        break;
      }
      case "final_brief": {
        nodes.push(briefNode(event));
        break;
      }
      case "status": {
        if (pendingToolStart) {
          nodes.push(flushToolStart(pendingToolStart));
          pendingToolStart = null;
        }
        if (pendingThought) {
          nodes.push(standaloneNode(pendingThought));
          pendingThought = null;
        }
        nodes.push(bareNode(event));
        break;
      }
    }
  }

  if (pendingToolStart) nodes.push(flushToolStart(pendingToolStart));
  if (pendingThought) nodes.push(standaloneNode(pendingThought));

  return nodes;
}
