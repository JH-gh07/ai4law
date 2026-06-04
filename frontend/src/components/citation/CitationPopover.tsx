import type { CitationDetail } from "../../lib/citation-api";

const TYPE_LABELS: Record<string, string> = {
  law_article: "法律条文",
  official_guide: "官方指南",
  template_requirement: "模板要求",
  standard_clause: "标准条款",
  case_reference: "案例参考",
  user_material: "用户材料",
};

const AUTHORITY_LABELS: Record<string, string> = {
  high: "高权威",
  medium: "中权威",
  low: "参考",
};

const SOURCE_KIND_LABELS: Record<string, string> = {
  law_article: "L1 法规证据层",
  regulation: "L1 法规证据层",
  official_guide: "L2 官方指南",
  template_requirement: "L4 模板约束",
  standard_clause: "L2 标准条款",
  case_reference: "L3 案例参考",
  user_material: "用户材料",
};

interface Props {
  footnoteNumber: number;
  citation: CitationDetail;
  onClickSource?: (citation: CitationDetail) => void;
  label?: string;
}

export function CitationPopover({ footnoteNumber, citation, onClickSource, label }: Props) {
  const snippet =
    citation.quote_text.length > 120
      ? citation.quote_text.slice(0, 120) + "…"
      : citation.quote_text;

  const confidencePct = (citation.confidence_score * 100).toFixed(0);
  const thresholdPct = (citation.confidence_threshold * 100).toFixed(0);
  const confidencePassed = citation.confidence_score >= citation.confidence_threshold;

  return (
    <span className="citation-marker group relative inline-flex">
      <sup
        className="citation-sup"
        onClick={(e) => {
          e.stopPropagation();
          onClickSource?.(citation);
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            e.stopPropagation();
            onClickSource?.(citation);
          }
        }}
      >
        {label ?? `[${footnoteNumber}] 引用`}
      </sup>
      <span className="citation-popover">
        <span className="citation-popover-header">
          <strong>{citation.title}</strong>
          {citation.article_no && (
            <span className="citation-article">第{citation.article_no}条</span>
          )}
        </span>
        {snippet && (
          <span className="citation-popover-snippet">{snippet}</span>
        )}
        <span className="citation-popover-badges">
          <span className={`citation-type-badge citation-type-${citation.citation_type}`}>
            {TYPE_LABELS[citation.citation_type] ?? citation.citation_type}
          </span>
          <span className={`citation-authority-badge citation-authority-${citation.authority_level}`}>
            {AUTHORITY_LABELS[citation.authority_level] ?? citation.authority_level}
          </span>
        </span>
        <span className="citation-popover-governance">
          {citation.can_jump && (
            <span className="citation-governance-ok">↗ 点击跳转知识库</span>
          )}
          {!citation.can_jump && (
            <span className="citation-governance-warning">无法精确跳转知识库</span>
          )}
          {citation.source_kind && (
            <span className="citation-source-kind-label">
              {SOURCE_KIND_LABELS[citation.source_kind] ?? citation.source_kind}
            </span>
          )}
          {citation.can_enter_external_report && citation.external_report_allowed && confidencePassed && (
            <span className="citation-governance-ok">✅ 可对外引用</span>
          )}
          {citation.can_enter_external_report && !citation.external_report_allowed && (
            <span className="citation-governance-warning">⚠️ 仅供内部审查（置信度不足）</span>
          )}
          {!citation.can_enter_external_report && (
            <span className="citation-governance-blocked">🔴 禁止进入对外文书</span>
          )}
          {!confidencePassed && citation.can_enter_external_report && (
            <span className="citation-governance-low-confidence">
              🟡 置信度 {confidencePct}% &lt; 阈值 {thresholdPct}%【待验证】
            </span>
          )}
        </span>
      </span>
    </span>
  );
}
