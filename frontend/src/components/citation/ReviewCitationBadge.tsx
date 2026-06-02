/**
 * ReviewCitationBadge — inline citation display for review module results.
 *
 * Converts review StructuredCitation format to a compact badge with
 * hover preview. Click opens a modal with full citation details.
 */
import { useState } from "react";
import { ModalShell } from "../common/ModalShell";

// ── Types ────────────────────────────────────────────────────────────────

export interface ReviewCitation {
  source_id?: string;
  source_title?: string;
  article?: string;
  snippet?: string;
  relevance_score?: number;
  source_type?: string;
  effective_date?: string | null;
}

interface Props {
  citations: ReviewCitation[];
}

// ── Helpers ──────────────────────────────────────────────────────────────

const TYPE_LABEL: Record<string, string> = {
  statute: "法律",
  regulation: "法规",
  standard: "标准",
  guideline: "指南",
  case: "案例",
};

function formatCitation(c: ReviewCitation): string {
  const title = c.source_title || "";
  const article = c.article || "";
  if (title && article) return `《${title}》${article}`;
  if (title) return `《${title}》`;
  return article || c.source_id || "";
}

// ── Component ────────────────────────────────────────────────────────────

export function ReviewCitationBadge({ citations }: Props) {
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  if (!citations.length) return null;

  return (
    <span className="review-citation-group">
      <span className="review-citation-label">法规依据：</span>
      {citations.map((c, i) => {
        const label = formatCitation(c);
        const typeLabel = TYPE_LABEL[c.source_type || ""] || "法规";
        return (
          <span key={i} className="review-citation-item">
            <button
              type="button"
              className="review-citation-badge"
              title={c.snippet || label}
              onClick={() => setOpenIdx(i)}
            >
              {label}
            </button>
            {/* Modal on click */}
            {openIdx === i && (
              <ModalShell
                title={label}
                subtitle={`${typeLabel} · 来源引用`}
                onClose={() => setOpenIdx(null)}
              >
                <dl className="citation-detail-grid">
                  {c.source_id && (<div><dt>来源 ID</dt><dd><code>{c.source_id}</code></dd></div>)}
                  {c.source_title && (<div><dt>法规名称</dt><dd>{c.source_title}</dd></div>)}
                  {c.article && (<div><dt>条款</dt><dd>{c.article}</dd></div>)}
                  {c.snippet && (<div className="citation-detail-full"><dt>原文摘录</dt><dd className="citation-detail-quote">{c.snippet}</dd></div>)}
                  {c.source_type && (<div><dt>类型</dt><dd>{typeLabel}</dd></div>)}
                  {c.effective_date && (<div><dt>生效日期</dt><dd>{c.effective_date}</dd></div>)}
                  {c.relevance_score != null && (<div><dt>相关度</dt><dd>{(c.relevance_score * 100).toFixed(0)}%</dd></div>)}
                </dl>
              </ModalShell>
            )}
          </span>
        );
      })}
    </span>
  );
}
