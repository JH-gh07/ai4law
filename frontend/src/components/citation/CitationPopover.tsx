import type { CitationDetail } from "../../lib/citation-api";

const TYPE_LABELS: Record<string, string> = {
  law_article: "法律条文",
  official_guide: "官方指南",
  template_requirement: "模板要求",
  standard_clause: "标准条款",
  user_material: "用户材料",
};

const AUTHORITY_LABELS: Record<string, string> = {
  high: "高权威",
  medium: "中权威",
  low: "参考",
};

interface Props {
  footnoteNumber: number;
  citation: CitationDetail;
}

export function CitationPopover({ footnoteNumber, citation }: Props) {
  const snippet =
    citation.quote_text.length > 120
      ? citation.quote_text.slice(0, 120) + "…"
      : citation.quote_text;

  return (
    <span className="citation-marker group relative inline-flex">
      <sup className="citation-sup">[{footnoteNumber}]</sup>
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
      </span>
    </span>
  );
}
