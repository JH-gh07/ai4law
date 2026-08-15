/**
 * trace-adapter.ts
 *
 * 将底层 RunEvent 原始事件流转换为可长期回看的 Agent Trace History。
 * 目标不是直出 raw event，而是按“用户能理解的动作节点”聚合、翻译、压缩。
 */

import type { RunEvent } from "./useTaskEvents";
import type { TraceBlock, TraceNode, TraceStage } from "./domain";
import { getTraceI18n, type TraceLang } from "./trace-i18n";

type SemanticMapping = {
  stage: TraceStage;
  action: string;
  icon: string;
  badge?: string;
};

function createEventToSemantic(lang: TraceLang): Record<RunEvent["event_type"], SemanticMapping> {
  const t = getTraceI18n(lang);
  return {
    status: { stage: "Task", action: t.actions.taskStatusUpdate, icon: "●", badge: "TASK" },
    thought: { stage: "LLM", action: t.actions.thoughtSummary, icon: "◌", badge: "THOUGHT" },
    tool_start: { stage: "Tool", action: t.actions.invokeTool, icon: "●", badge: "CALL" },
    tool_result: { stage: "Tool", action: t.actions.returnResult, icon: "●", badge: "RESULT" },
    intermediate: { stage: "Review", action: t.actions.intermediateResult, icon: "●", badge: "INTERMEDIATE" },
    warning: { stage: "Review", action: t.actions.warning, icon: "●", badge: "WARNING" },
    final: { stage: "Task", action: t.actions.workflowCompleted, icon: "●", badge: "FINAL" },
    final_brief: { stage: "Review", action: t.actions.clientBrief, icon: "●", badge: "BRIEF" },
  };
}

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

function summarizeArray(value: unknown, lang: TraceLang): string | undefined {
  if (!Array.isArray(value) || value.length === 0) return undefined;
  const t = getTraceI18n(lang);
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
    .join(t.format.listJoiner);
  return value.length > 3 ? `${preview} ${t.format.moreItems(value.length)}` : preview;
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

function extractTokenCount(usage: unknown, key: string): number | undefined {
  if (!usage || typeof usage !== "object") return undefined;
  const u = usage as Record<string, unknown>;
  const val = u[key];
  return typeof val === "number" && val > 0 ? val : undefined;
}

function computeDuration(startIso: string, endIso: string): number | undefined {
  const s = new Date(startIso).getTime();
  const e = new Date(endIso).getTime();
  if (isNaN(s) || isNaN(e) || e < s) return undefined;
  return e - s;
}

function semanticFromDetail(event: RunEvent, lang: TraceLang): SemanticMapping {
  const t = getTraceI18n(lang);
  const eventToSemantic = createEventToSemantic(lang);
  const detail = event.detail ?? {};
  const tool = readString(detail.tool);
  const agent = readString(detail.agent);
  const category = readString(detail.category);
  const rawName = readString(detail.raw_name);
  const summary = event.summary;

  if (event.event_type === "status") {
    return {
      stage: "Task",
      action: /开始|创建|启动/.test(summary)
        ? t.actions.createAndStartTask
        : /完成|结束/.test(summary)
          ? t.actions.taskCompleted
          : t.actions.taskStatusUpdate,
      icon: "●",
      badge: "TASK",
    };
  }

  if (tool || agent) {
    const name = tool || agent || "";

    if (/retriev|rag|search|检索|citation/i.test(name) || /检索|引用|命中/.test(summary)) {
      return { stage: "RAG", action: t.actions.searchLegalReferences, icon: "●", badge: "RAG" };
    }
    if (/parse|extract|document_structure|attachment/i.test(name) || /解析|提取|文档结构/.test(summary)) {
      return { stage: "Parser", action: t.actions.parseInputAttachments, icon: "●", badge: "PARSER" };
    }
    if (/chapter|draft|generation|render/i.test(name) || /章节生成|报告渲染|外部草拟|生成/.test(summary)) {
      return { stage: "Generator", action: t.actions.generateReportContent, icon: "●", badge: "GEN" };
    }
    if (/consistency|review|qa|evidence|verify/i.test(name) || /一致性|审查|证据|校验/.test(summary)) {
      return { stage: "Review", action: t.actions.reviewAndValidate, icon: "●", badge: "REVIEW" };
    }
    if (/llm|chat/i.test(name)) {
      return { stage: "LLM", action: t.actions.requestModelGeneration, icon: "●", badge: "LLM" };
    }
    return { stage: "Tool", action: shorten(name, 40) ?? t.actions.invokeTool, icon: "●", badge: "TOOL" };
  }

  if (rawName) {
    if (/^control\./.test(rawName)) {
      const gate = readString(detail.gate);
      const outcome = readString(detail.outcome);
      const label = [gate, outcome].filter(Boolean).join(" · ");
      return {
        stage: "Review",
        action: label ? `${t.actions.controlGate} · ${label}` : t.actions.controlGate,
        icon: "●",
        badge: outcome === "PASS" ? "CONTROL" : "CONTROL",
      };
    }
    if (/per_issue_rag|agent_rag_reformulation/i.test(rawName)) {
      return {
        stage: "RAG",
        action: /reformulation/i.test(rawName) ? t.actions.reframeRetrievalQuery : t.actions.retrievePerIssue,
        icon: "●",
        badge: "RAG",
      };
    }
    if (/retrieval_hits|rag_plans|rag_hit/i.test(rawName)) {
      return {
        stage: "RAG",
        action: /plans/i.test(rawName) ? t.actions.planRetrievalStrategy : t.actions.searchLegalReferences,
        icon: "●",
        badge: "RAG",
      };
    }
    if (/parsed_document_raw|profile_extracted|facts_built|transfer_chain_raw/i.test(rawName)) {
      return { stage: "Parser", action: t.actions.extractStructuredFacts, icon: "●", badge: "PARSER" };
    }
    if (/issues_built/i.test(rawName)) {
      return { stage: "Review", action: t.actions.buildIssueList, icon: "●", badge: "REVIEW" };
    }
    if (/evidence_built/i.test(rawName)) {
      return { stage: "Review", action: t.actions.buildEvidenceChain, icon: "●", badge: "REVIEW" };
    }
    if (/context_pack_built/i.test(rawName)) {
      return { stage: "Generator", action: t.actions.buildGenerationContext, icon: "●", badge: "GEN" };
    }
    if (/agent_external_draft|chapters_generated|generate_chapters|render/i.test(rawName)) {
      return { stage: "Generator", action: t.actions.generateReportChapters, icon: "●", badge: "GEN" };
    }
    if (/agent_internal_review|agent_consistency_repair|report_review|alignment|repair_pass|agent_repair_check|agent_chapter_consistency/i.test(rawName)) {
      return { stage: "Review", action: t.actions.consistencyReview, icon: "●", badge: "REVIEW" };
    }
    if (/agent_rule_boundary|rule_engine_result/i.test(rawName)) {
      return { stage: "Review", action: t.actions.ruleBoundaryReview, icon: "●", badge: "REVIEW" };
    }
    if (/agent_dpia_need|path_diagnosis|need_detection_rule|need_diagnosis_enriched/i.test(rawName)) {
      return { stage: "LLM", action: t.actions.pathAnalysis, icon: "●", badge: "LLM" };
    }
    if (/agent_processing_activity|agent_risk_assessment|agent_mitigation_mapping|agent_dpo_consultation|agent_clause_semantic|agent_tia_effectiveness|agent_remediation|agent_evidence_priority/i.test(rawName)) {
      return { stage: "Generator", action: t.actions.specializedAnalysis, icon: "●", badge: "GEN" };
    }
  }

  if (category) {
    if (/artifact|output|report/i.test(category)) {
      return { stage: "Generator", action: t.actions.intermediateArtifact, icon: "●", badge: "OUTPUT" };
    }
    if (/retrieval|rag/i.test(category)) {
      return { stage: "RAG", action: t.actions.retrievalOutput, icon: "●", badge: "RAG" };
    }
    return { stage: "Review", action: shorten(category, 32) ?? t.actions.intermediateResult, icon: "●", badge: "INTERMEDIATE" };
  }

  const base = eventToSemantic[event.event_type];
  return base ?? { stage: "Task", action: event.event_type, icon: "●" };
}

function detailToBlock(
  label: TraceBlock["label"],
  detail: Record<string, unknown> | null | undefined,
  lang: TraceLang,
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
    summary: summarizeDetail(detail, lang),
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

function summarizeDetail(detail: Record<string, unknown> | null | undefined, lang: TraceLang): string | undefined {
  if (!detail) return undefined;

  const t = getTraceI18n(lang);
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
    .map((value) => t.format.itemCount(value));

  const filesSummary = summarizeArray(detail.files, lang);
  const risksSummary = summarizeArray(detail.risks, lang);
  const issuesSummary = summarizeArray(detail.issues, lang);
  const hitsSummary = summarizeArray(detail.hits, lang);

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
    parts.unshift(`${t.fields.errorPrefix}${error}`);
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

function buildHumanDetail(lines: Array<string | undefined>): string | undefined {
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

function mergeTool(toolStart: RunEvent, toolResult: RunEvent, thought: RunEvent | null, lang: TraceLang): TraceNode {
  const t = getTraceI18n(lang);
  const sem = semanticFromDetail(toolStart, lang);
  const toolName = readString(toolStart.detail?.tool) ?? readString(toolStart.detail?.agent);
  const callSummary = summarizeDetail(toolStart.detail, lang);
  const resultSummary = summarizeDetail(toolResult.detail, lang);
  const status = readString(toolResult.detail?.error) ? "error" : "success";

  return makeNode(toolStart, sem, {
    action: sem.action,
    description: thought?.summary
      ? summaryLine(thought, sem.action)
      : summaryLine(toolStart, sem.action),
    detail: buildHumanDetail([
      toolName ? `${t.fields.callTarget}${toolName}` : undefined,
      callSummary ? `${t.fields.callSummary}${callSummary}` : undefined,
      resultSummary ? `${t.fields.resultSummary}${resultSummary}` : undefined,
    ]),
    status,
    durationMs: computeDuration(toolStart.timestamp, toolResult.timestamp),
    input: toolStart.detail ? detailToBlock(chooseInputLabel(sem), toolStart.detail, lang) : undefined,
    output: toolResult.detail
      ? detailToBlock(chooseOutputLabel(sem, toolResult.detail, status, toolResult.event_type), toolResult.detail, lang)
      : textToBlock(chooseOutputLabel(sem, null, status, toolResult.event_type), toolResult.summary),
    rawEventIds: rawEventIds(toolStart, thought, toolResult),
    tokenInput: extractTokenCount(toolResult.detail?.llm, "prompt_tokens")
      ?? extractTokenCount(toolResult.detail?.usage, "prompt_tokens")
      ?? extractTokenCount(toolResult.detail?.usage, "input"),
    tokenOutput: extractTokenCount(toolResult.detail?.llm, "completion_tokens")
      ?? extractTokenCount(toolResult.detail?.usage, "completion_tokens")
      ?? extractTokenCount(toolResult.detail?.usage, "output"),
  });
}

function flushToolStart(event: RunEvent, lang: TraceLang): TraceNode {
  const t = getTraceI18n(lang);
  const sem = semanticFromDetail(event, lang);
  const toolName = readString(event.detail?.tool) ?? readString(event.detail?.agent);
  const detailSummary = summarizeDetail(event.detail, lang);
  return makeNode(event, sem, {
    description: summaryLine(event, sem.action),
    detail: buildHumanDetail([
      toolName ? `${t.fields.callTarget}${toolName}` : undefined,
      detailSummary ? `${t.fields.callSummary}${detailSummary}` : undefined,
    ]),
    status: "running",
    input: event.detail ? detailToBlock(chooseInputLabel(sem), event.detail, lang) : undefined,
  });
}

function standaloneNode(event: RunEvent, lang: TraceLang): TraceNode {
  const sem = semanticFromDetail(event, lang);
  const status = readString(event.detail?.error) ? "error" : "success";
  return makeNode(event, sem, {
    description: summaryLine(event, sem.action),
    detail: summarizeDetail(event.detail, lang),
    status,
    output: event.detail
      ? detailToBlock(chooseOutputLabel(sem, event.detail, status, event.event_type), event.detail, lang)
      : undefined,
  });
}

function intermediateNode(event: RunEvent, lang: TraceLang): TraceNode {
  const sem = semanticFromDetail(event, lang);
  const status = event.event_type === "warning" ? "error" : "success";
  return makeNode(event, sem, {
    description: summaryLine(event, sem.action),
    detail: summarizeDetail(event.detail, lang),
    status,
    output: event.detail
      ? detailToBlock(chooseOutputLabel(sem, event.detail, status, event.event_type), event.detail, lang)
      : undefined,
  });
}

function finalNode(event: RunEvent, lang: TraceLang): TraceNode {
  const sem = semanticFromDetail(event, lang);
  return makeNode(event, sem, {
    description: summaryLine(event, sem.action),
    detail: summarizeDetail(event.detail, lang),
    output: event.detail ? detailToBlock("RESULT", event.detail, lang) : undefined,
  });
}

function briefNode(event: RunEvent, lang: TraceLang): TraceNode {
  const sem = semanticFromDetail(event, lang);
  const conclusion = readString(event.detail?.conclusion);
  return makeNode(event, sem, {
    description: conclusion ?? summaryLine(event, sem.action),
    detail: summarizeDetail(event.detail, lang),
    output: event.detail ? detailToBlock("OUTPUT", event.detail, lang) : undefined,
  });
}

function bareNode(event: RunEvent, lang: TraceLang): TraceNode {
  const t = getTraceI18n(lang);
  const sem = semanticFromDetail(event, lang);
  const status = readString(event.detail?.state);
  return makeNode(event, sem, {
    description: status ? t.format.statusWithValue(summaryLine(event, sem.action), status) : summaryLine(event, sem.action),
    detail: summarizeDetail(event.detail, lang),
    status: /failed|error|cancel/i.test(status ?? "") ? "error" : "success",
  });
}

export function adaptEvents(rawEvents: RunEvent[], lang: TraceLang): TraceNode[] {
  const nodes: TraceNode[] = [];
  let pendingToolStart: RunEvent | null = null;
  const correlatedToolStarts = new Map<string, RunEvent>();
  let pendingThought: RunEvent | null = null;

  for (const event of rawEvents) {
    if (event.event_type === "status" && event.seq <= 0) continue;

    switch (event.event_type) {
      case "tool_start": {
        if (event.correlation_id) {
          correlatedToolStarts.set(event.correlation_id, event);
          break;
        }
        if (pendingToolStart) nodes.push(flushToolStart(pendingToolStart, lang));
        pendingToolStart = event;
        break;
      }
      case "tool_result": {
        const correlatedStart = event.correlation_id
          ? correlatedToolStarts.get(event.correlation_id)
          : undefined;
        if (correlatedStart) {
          nodes.push(mergeTool(correlatedStart, event, pendingThought, lang));
          correlatedToolStarts.delete(event.correlation_id!);
        } else if (pendingToolStart) {
          nodes.push(mergeTool(pendingToolStart, event, pendingThought, lang));
          pendingToolStart = null;
        } else {
          nodes.push(standaloneNode(event, lang));
        }
        pendingThought = null;
        break;
      }
      case "thought": {
        if (pendingThought) nodes.push(standaloneNode(pendingThought, lang));
        pendingThought = event;
        break;
      }
      case "intermediate":
      case "warning": {
        if (pendingToolStart) {
          nodes.push(flushToolStart(pendingToolStart, lang));
          pendingToolStart = null;
        }
        if (pendingThought) {
          nodes.push(standaloneNode(pendingThought, lang));
          pendingThought = null;
        }
        nodes.push(intermediateNode(event, lang));
        break;
      }
      case "final": {
        if (pendingToolStart) {
          nodes.push(flushToolStart(pendingToolStart, lang));
          pendingToolStart = null;
        }
        if (pendingThought) {
          nodes.push(standaloneNode(pendingThought, lang));
          pendingThought = null;
        }
        nodes.push(finalNode(event, lang));
        break;
      }
      case "final_brief": {
        nodes.push(briefNode(event, lang));
        break;
      }
      case "status": {
        if (pendingToolStart) {
          nodes.push(flushToolStart(pendingToolStart, lang));
          pendingToolStart = null;
        }
        if (pendingThought) {
          nodes.push(standaloneNode(pendingThought, lang));
          pendingThought = null;
        }
        nodes.push(bareNode(event, lang));
        break;
      }
    }
  }

  if (pendingToolStart) nodes.push(flushToolStart(pendingToolStart, lang));
  for (const pending of correlatedToolStarts.values()) {
    nodes.push(flushToolStart(pending, lang));
  }
  if (pendingThought) nodes.push(standaloneNode(pendingThought, lang));

  return nodes;
}
