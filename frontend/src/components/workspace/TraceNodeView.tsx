import type { TraceNode } from "../../lib/domain";
import type { Language } from "../../lib/i18n";
import { getTraceLocale } from "../../lib/trace-i18n";
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

function fmtTime(iso: string, lang: Language): string {
  return new Date(iso).toLocaleTimeString(getTraceLocale(lang), { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function TraceNodeView({ node, lang }: { node: TraceNode; lang: Language }) {
  const color = STAGE_COLORS[node.stage] ?? "#6b7280";
  const dotColor = node.status === "error" ? "#dc2626" : color;

  return (
    <div className={`trace-node trace-node-${node.status}`}>
      <div className="trace-node-dot" style={{ background: dotColor }} />

      <div className="trace-node-header">
        <span className="trace-node-stage-wrap">
          {node.badge ? <span className="trace-node-badge">{node.badge}</span> : null}
          <span className="trace-node-stage" style={{ color }}>
            {node.stage}
          </span>
          <span className="trace-node-action">｜{node.action}</span>
        </span>
        <span className="trace-node-time">{fmtTime(node.timestamp, lang)}</span>
      </div>

      {node.description ? <div className="trace-node-desc">{node.description}</div> : null}
      {node.detail ? <div className="trace-node-detail">{node.detail}</div> : null}

      {node.durationMs != null && node.durationMs > 0 ? (
        <div className="trace-node-duration">⏱ {(node.durationMs / 1000).toFixed(1)}s</div>
      ) : null}

      {node.tokenInput != null || node.tokenOutput != null ? (
        <div className="trace-node-tokens">
          {node.tokenInput != null ? <span>⬆ {node.tokenInput.toLocaleString()}</span> : null}
          {node.tokenOutput != null ? <span>⬇ {node.tokenOutput.toLocaleString()}</span> : null}
        </div>
      ) : null}

      {node.input ? <TraceExpandableBlock block={node.input} lang={lang} /> : null}
      {node.output ? <TraceExpandableBlock block={node.output} lang={lang} /> : null}
    </div>
  );
}
