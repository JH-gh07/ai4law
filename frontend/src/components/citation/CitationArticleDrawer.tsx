import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { CitationDetail } from "../../lib/citation-api";
import {
  fetchArticleDetail,
  type ArticleDetail,
} from "../../lib/knowledge-api";

const AUTHORITY_LABELS: Record<string, string> = {
  high: "高权威",
  medium: "中权威",
  low: "参考",
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

/**
 * Plan A — CitationArticleDrawer
 *
 * Side drawer that slides in from the right. Shows the full text of the cited
 * legal article from the knowledge base, with previous/next article context.
 * Includes a "view in standalone page" link to the LawViewerPage (Plan B).
 */
export function CitationArticleDrawer({ citation, onClose }: Props) {
  const navigate = useNavigate();
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!citation.source_id || !citation.article_no) {
      setLoading(false);
      setError("引用缺少知识库来源信息，无法查看原文。");
      return;
    }

    setLoading(true);
    setError(null);

    fetchArticleDetail(citation.source_id, citation.article_no)
      .then((detail) => {
        setArticle(detail);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
        setLoading(false);
      });
  }, [citation.source_id, citation.article_no]);

  const handleViewFullLaw = () => {
    if (citation.source_id) {
      navigate(
        `/knowledge/laws/${encodeURIComponent(citation.source_id)}?article=${encodeURIComponent(citation.article_no)}`,
      );
    }
  };

  return (
    <div className="citation-drawer-backdrop" onClick={onClose}>
      <div
        className="citation-drawer-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="citation-drawer-header">
          <button className="citation-drawer-close" onClick={onClose}>
            ×
          </button>
          <h3 className="citation-drawer-title">
            {citation.title || "引用原文"}
          </h3>
          {citation.article_no && (
            <span className="citation-drawer-article-label">
              第{citation.article_no}条
            </span>
          )}
          <div className="citation-drawer-meta">
            <span className={`citation-authority-badge citation-authority-${citation.authority_level}`}>
              {AUTHORITY_LABELS[citation.authority_level] ?? citation.authority_level}
            </span>
            <span className="citation-binding-badge">
              {BINDING_LABELS[citation.binding_force] ?? citation.binding_force}
            </span>
          </div>
        </header>

        <div className="citation-drawer-body">
          {loading ? (
            <p className="citation-drawer-status">加载条文原文中…</p>
          ) : error ? (
            <p className="citation-drawer-error">{error}</p>
          ) : article ? (
            <article className="citation-article-view">
              {article.prev_article_no && article.prev_article_content && (
                <section className="citation-article-context">
                  <h5>第{article.prev_article_no}条</h5>
                  <p>{article.prev_article_content}</p>
                </section>
              )}

              <section className="citation-article-target">
                <h4>第{article.article_no}条</h4>
                <p>{article.article_content}</p>
              </section>

              {article.next_article_no && article.next_article_content && (
                <section className="citation-article-context">
                  <h5>第{article.next_article_no}条</h5>
                  <p>{article.next_article_content}</p>
                </section>
              )}
            </article>
          ) : null}
        </div>

        <footer className="citation-drawer-footer">
          {citation.source_url && (
            <a
              href={citation.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="citation-drawer-source-link"
            >
              在官方来源查看
            </a>
          )}
          <button
            className="citation-drawer-view-full"
            onClick={handleViewFullLaw}
          >
            在独立页面浏览完整法规
          </button>
        </footer>
      </div>
    </div>
  );
}
