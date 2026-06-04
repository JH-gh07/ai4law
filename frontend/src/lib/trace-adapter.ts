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
    if (/retrieval_hits|rag_plans|rag_hit/i.test(rawName)) {
      return { stage: "RAG", action: /plans/i.test(rawName) ? "规划检索策略" : "检索法规与依据", icon: "●", badge: "RAG" };
    }
    if (/parsed_document_raw|profile_extracted|facts_built|transfer_chain_raw/i.test(rawName)) {
      return { stage: "Parser", action: "提取结构化事实", icon: "●", badge: "PARSER" };
    }
    if (/agent_external_draft|chapters_generated|generate_chapters|render/i.test(rawName)) {
      return { stage: "Generator", action: "生成报告章节", icon: "●", badge: "GEN" };
    }
    if (/agent_internal_review|agent_consistency_repair|report_review|alignment/i.test(rawName)) {
      return { stage: "Review", action: "执行一致性审查", icon: "●", badge: "REVIEW" };
    }
    if (/agent_dpia_need|path_diagnosis|need_detection_rule|need_diagnosis_enriched/i.test(rawName)) {
      return { stage: "LLM", action: "生成判断与路径分析", icon: "●", badge: "LLM" };
    }
    if (/agent_processing_activity|agent_risk_assessment|agent_mitigation_mapping|agent_dpo_consultation|agent_clause_semantic|agent_tia_effectiveness|agent_remediation/i.test(rawName)) {
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
    rawName,
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
  return parts.length > 0 ? parts.join(" · ") : undefined;
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
    ...overrides,
  };
}

function mergeTool(toolStart: RunEvent, toolResult: RunEvent, thought: RunEvent | null): TraceNode {
  const sem = semanticFromDetail(toolStart);
  const toolName = readString(toolStart.detail?.tool) ?? readString(toolStart.detail?.agent);
  const callSummary = summarizeDetail(toolStart.detail);
  const resultSummary = summarizeDetail(toolResult.detail);

  return makeNode(toolStart, sem, {
    action: sem.action,
    description: toolName
      ? `${toolName}${callSummary ? ` · ${callSummary}` : ""}`
      : (callSummary ?? shorten(toolStart.summary, 96) ?? sem.action),
    detail: thought?.summary
      ? `判断依据：${thought.summary}${resultSummary ? `\n结果摘要：${resultSummary}` : ""}`
      : resultSummary,
    status: readString(toolResult.detail?.error) ? "error" : "success",
    durationMs: computeDuration(toolStart.timestamp, toolResult.timestamp),
    input: toolStart.detail ? detailToBlock("CALL", toolStart.detail) : undefined,
    output: toolResult.detail ? detailToBlock("RESULT", toolResult.detail) : textToBlock("RESULT", toolResult.summary),
  });
}

function flushToolStart(event: RunEvent): TraceNode {
  const sem = semanticFromDetail(event);
  const toolName = readString(event.detail?.tool) ?? readString(event.detail?.agent);
  return makeNode(event, sem, {
    description: toolName
      ? `${toolName}${summarizeDetail(event.detail) ? ` · ${summarizeDetail(event.detail)}` : ""}`
      : (summarizeDetail(event.detail) ?? shorten(event.summary, 96) ?? sem.action),
    status: "running",
    input: event.detail ? detailToBlock("CALL", event.detail) : undefined,
  });
}

function standaloneNode(event: RunEvent): TraceNode {
  const sem = semanticFromDetail(event);
  return makeNode(event, sem, {
    description: summarizeDetail(event.detail) ?? shorten(event.summary, 96) ?? sem.action,
    detail: !event.detail ? undefined : shorten(event.summary, 120),
    output: event.detail ? detailToBlock(event.event_type === "thought" ? "OUTPUT" : "RESULT", event.detail) : undefined,
  });
}

function intermediateNode(event: RunEvent): TraceNode {
  const sem = semanticFromDetail(event);
  return makeNode(event, sem, {
    description: summarizeDetail(event.detail) ?? shorten(event.summary, 96) ?? sem.action,
    detail: shorten(event.summary, 120),
    output: event.detail ? detailToBlock("OUTPUT", event.detail) : undefined,
  });
}

function finalNode(event: RunEvent): TraceNode {
  const sem = semanticFromDetail(event);
  return makeNode(event, sem, {
    description: shorten(event.summary, 96) ?? sem.action,
    detail: summarizeDetail(event.detail),
    output: event.detail ? detailToBlock("RESULT", event.detail) : undefined,
  });
}

function briefNode(event: RunEvent): TraceNode {
  const sem = semanticFromDetail(event);
  const conclusion = readString(event.detail?.conclusion);
  return makeNode(event, sem, {
    description: conclusion ?? shorten(event.summary, 96) ?? sem.action,
    detail: summarizeDetail(event.detail),
    output: event.detail ? detailToBlock("OUTPUT", event.detail) : undefined,
  });
}

function bareNode(event: RunEvent): TraceNode {
  const sem = semanticFromDetail(event);
  const status = readString(event.detail?.state);
  return makeNode(event, sem, {
    description: status ? `${event.summary} · ${status}` : (shorten(event.summary, 96) ?? sem.action),
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
