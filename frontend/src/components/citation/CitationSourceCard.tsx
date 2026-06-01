import type { CitationDetail } from "../../lib/citation-api";
import { ModalShell } from "../common/ModalShell";

const TYPE_LABELS: Record<string, string> = {
  law_article: "法律条文",
  official_guide: "官方指南",
  template_requirement: "模板要求",
  standard_clause: "标准条款",
  user_material: "用户材料",
};

const BINDING_LABELS: Record<string, string> = {
  mandatory: "强制",
  recommended: "建议",
  reference: "参考",
};

interface Props {
  citation: CitationDetail;
  onClose: () => void;
}

export function CitationSourceCard({ citation, onClose }: Props) {
  return (
    <ModalShell
      title={citation.title}
      subtitle={`引用依据 · ${TYPE_LABELS[citation.citation_type] ?? citation.citation_type}`}
      onClose={onClose}
    >
      <dl className="citation-detail-grid">
        <div>
          <dt>引用编号</dt>
          <dd>
            <code>{citation.citation_id}</code>
            {citation.footnote_number != null && (
              <span className="citation-footnote-badge">[{citation.footnote_number}]</span>
            )}
          </dd>
        </div>
        {citation.article_no && (
          <div>
            <dt>条款</dt>
            <dd>第{citation.article_no}条</dd>
          </div>
        )}
        <div>
          <dt>类型</dt>
          <dd>
            <span className={`citation-type-badge citation-type-${citation.citation_type}`}>
              {TYPE_LABELS[citation.citation_type] ?? citation.citation_type}
            </span>
          </dd>
        </div>
        <div>
          <dt>权威等级</dt>
          <dd>{citation.authority_level}</dd>
        </div>
        <div>
          <dt>约束力</dt>
          <dd>{BINDING_LABELS[citation.binding_force] ?? citation.binding_force}</dd>
        </div>
        <div>
          <dt>置信度</dt>
          <dd>{(citation.confidence_score * 100).toFixed(0)}%</dd>
        </div>
        {citation.quote_text && (
          <div className="citation-detail-full">
            <dt>原文摘录</dt>
            <dd className="citation-detail-quote">{citation.quote_text}</dd>
          </div>
        )}
        {citation.related_issue_ids.length > 0 && (
          <div>
            <dt>关联问题</dt>
            <dd className="citation-detail-list">
              {citation.related_issue_ids.map((id) => (
                <code key={id}>{id}</code>
              ))}
            </dd>
          </div>
        )}
        {citation.related_fact_ids.length > 0 && (
          <div>
            <dt>关联事实</dt>
            <dd className="citation-detail-list">
              {citation.related_fact_ids.map((id) => (
                <code key={id}>{id}</code>
              ))}
            </dd>
          </div>
        )}
        {citation.related_evidence_ids.length > 0 && (
          <div>
            <dt>关联证据</dt>
            <dd className="citation-detail-list">
              {citation.related_evidence_ids.map((id) => (
                <code key={id}>{id}</code>
              ))}
            </dd>
          </div>
        )}
        <div>
          <dt>来源 ID</dt>
          <dd className="citation-detail-mono">{citation.source_id}</dd>
        </div>
      </dl>
    </ModalShell>
  );
}
