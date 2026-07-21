import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { CitationDetail } from "../../api/citations";
import {
  fetchArticleDetail,
  type ArticleDetail,
} from "../../api/knowledge";

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

const FAILURE_LABELS: Record<string, string> = {
  article_missing: "引用未提供条号，当前只能定位到法规来源。",
  article_not_found: "引用条号未在本地知识库中找到，当前只能定位到法规来源。",
  article_not_unique: "该条号在本地知识库中存在重复记录，暂不能声明精确定位。",
  article_requires_server_resolution: "该条号尚未经过服务端唯一性校验。",
  local_source_not_mapped: "外部来源已经核验，但尚未映射到本地知识库。",
  source_not_found: "引用来源未收入本地知识库，暂时无法定位。",
};

interface Props {
  citation: CitationDetail;
  onClose: () => void;
}

export function CitationArticleDrawer({ citation, onClose }: Props) {
  const navigate = useNavigate();
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const resolutionType = citation.resolution?.resolution_type ?? "unresolved";
  const failureReason = citation.resolution?.failure_reason ?? "source_not_found";

  useEffect(() => {
    setArticle(null);
    setError(null);

    if (resolutionType !== "exact_article") {
      setLoading(false);
      return;
    }
    if (!citation.source_id || !citation.article_no) {
      setLoading(false);
      setError("精确引用缺少知识库来源或条号，请人工复核 CitationMap。");
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
  }, [citation.source_id, citation.article_no, resolutionType]);

  const handleViewFullLaw = () => {
    const targetUrl = citation.knowledge_url;
    if (targetUrl.startsWith("/knowledge/laws/")) {
      navigate(targetUrl);
    }
  };

  return (
    <div
      className="citation-drawer-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="citation-drawer-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="citation-drawer-header">
          <button className="citation-drawer-close" onClick={onClose}>
            ×
          </button>
          <h3 className="citation-drawer-title">
            {citation.title || "依据原文"}
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
            <p className="citation-drawer-status">正在载入依据原文…</p>
          ) : error ? (
            <p className="citation-drawer-error" role="alert">{error}</p>
          ) : article ? (
            <article className="citation-article-view">
              {article.prev_article_no && article.prev_article_content && (
                <section className="citation-article-context">
                  <small>上文</small>
                  <h5>第{article.prev_article_no}条</h5>
                  <p>{article.prev_article_content}</p>
                </section>
              )}

              <section className="citation-article-target">
                <small>当前引用位置</small>
                <h4>第{article.article_no}条</h4>
                <p>{article.article_content}</p>
              </section>

              {article.next_article_no && article.next_article_content && (
                <section className="citation-article-context">
                  <small>下文</small>
                  <h5>第{article.next_article_no}条</h5>
                  <p>{article.next_article_content}</p>
                </section>
              )}
            </article>
          ) : resolutionType === "source_overview" ? (
            <section className="citation-resolution-notice">
              <h4>当前为法规来源级定位</h4>
              <p>{FAILURE_LABELS[failureReason] ?? "当前引用不能唯一定位到具体条文。"}</p>
            </section>
          ) : resolutionType === "external_verified" ? (
            <section className="citation-resolution-notice">
              <h4>外部来源待入库</h4>
              <p>{FAILURE_LABELS[failureReason] ?? "外部来源已核验，但尚未映射到本地对象。"}</p>
            </section>
          ) : (
            <section className="citation-resolution-notice" role="alert">
              <h4>无法解析引用</h4>
              <p>{FAILURE_LABELS[failureReason] ?? "引用来源存在冲突或尚未完成校验。"}</p>
            </section>
          )}
        </div>

        <footer className="citation-drawer-footer">
          {citation.source_url && (
            <a
              href={citation.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="citation-drawer-source-link"
            >
              查看官方发布版本
            </a>
          )}
          {(resolutionType === "exact_article" || resolutionType === "source_overview") &&
            citation.knowledge_url.startsWith("/knowledge/laws/") ? (
              <button
                className="citation-drawer-view-full"
                onClick={handleViewFullLaw}
              >
                {resolutionType === "exact_article" ? "在知识库中继续阅读" : "查看法规概览"}
              </button>
            ) : null}
        </footer>
      </div>
    </div>
  );
}
