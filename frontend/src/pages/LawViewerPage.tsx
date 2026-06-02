import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  fetchArticleDetail,
  fetchKnowledgeSourceDetail,
  type ArticleDetail,
} from "../lib/knowledge-api";
import { useLang } from "../lib/language";

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

const DOC_TYPE_LABELS: Record<string, string> = {
  law: "法律",
  regulation: "行政法规",
  guideline: "官方指南",
  standard: "标准规范",
  template: "模板文件",
};

/**
 * Plan B — LawViewerPage
 *
 * Standalone full-law browser for the knowledge base. Shows a complete law document
 * with article-level navigation, metadata, and the target article scrolled into view.
 *
 * Route: /knowledge/laws/:sourceId?article=39
 */
export function LawViewerPage() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const [searchParams] = useSearchParams();
  const targetArticle = searchParams.get("article") || "";
  const navigate = useNavigate();
  const { lang } = useLang();

  const [sourceMeta, setSourceMeta] = useState<Record<string, string> | null>(null);
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const targetRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!sourceId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      fetchKnowledgeSourceDetail(sourceId),
      targetArticle
        ? fetchArticleDetail(sourceId, targetArticle)
        : Promise.resolve(null),
    ])
      .then(([sourceData, articleData]) => {
        if (cancelled) return;
        setSourceMeta(sourceData.item);
        setArticle(articleData);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sourceId, targetArticle]);

  // Scroll to target article after render
  useEffect(() => {
    if (targetRef.current) {
      targetRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [article]);

  const t = (zh: string, en: string) => (lang === "zh" ? zh : en);

  if (!sourceId) {
    return (
      <div className="law-viewer-page">
        <p className="law-viewer-error">{t("缺少来源 ID。", "Missing source ID.")}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="law-viewer-page">
        <p className="law-viewer-status">{t("加载法规中…", "Loading law document…")}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="law-viewer-page">
        <p className="law-viewer-error">{error}</p>
      </div>
    );
  }

  if (!sourceMeta) {
    return (
      <div className="law-viewer-page">
        <p className="law-viewer-error">
          {t("未找到该法规。", "Law document not found.")}
        </p>
      </div>
    );
  }

  const title = sourceMeta.title || sourceId;
  const sourceUrl = sourceMeta.url || "";
  const authorityLevel = sourceMeta.authority_level || "medium";
  const bindingForce = sourceMeta.binding_force || "recommended";
  const jurisdiction = sourceMeta.jurisdiction || "cn";
  const docType = sourceMeta.doc_type || "law";
  const publishDate = sourceMeta.publish_date || "";
  const effectiveDate = sourceMeta.effective_date || "";
  const sourceOrg = sourceMeta.source_org || "";

  return (
    <div className="law-viewer-page">
      <div className="law-viewer-container">
        <header className="law-viewer-header">
          <button
            className="law-viewer-back"
            onClick={() => navigate(-1)}
          >
            ← {t("返回", "Back")}
          </button>

          <h1 className="law-viewer-title">{title}</h1>

          <div className="law-viewer-meta-grid">
            {sourceOrg && (
              <div className="law-viewer-meta-item">
                <dt>{t("发布机构", "Source Org")}</dt>
                <dd>{sourceOrg}</dd>
              </div>
            )}
            {publishDate && (
              <div className="law-viewer-meta-item">
                <dt>{t("发布日期", "Publish Date")}</dt>
                <dd>{publishDate}</dd>
              </div>
            )}
            {effectiveDate && (
              <div className="law-viewer-meta-item">
                <dt>{t("生效日期", "Effective Date")}</dt>
                <dd>{effectiveDate}</dd>
              </div>
            )}
            <div className="law-viewer-meta-item">
              <dt>{t("法域", "Jurisdiction")}</dt>
              <dd className="law-viewer-jurisdiction">
                {jurisdiction.toUpperCase()}
              </dd>
            </div>
            <div className="law-viewer-meta-item">
              <dt>{t("文件类型", "Doc Type")}</dt>
              <dd>
                <span className={`citation-type-badge citation-type-${docType}`}>
                  {DOC_TYPE_LABELS[docType] ?? docType}
                </span>
              </dd>
            </div>
            <div className="law-viewer-meta-item">
              <dt>{t("权威等级", "Authority")}</dt>
              <dd>
                <span className={`citation-authority-badge citation-authority-${authorityLevel}`}>
                  {AUTHORITY_LABELS[authorityLevel] ?? authorityLevel}
                </span>
              </dd>
            </div>
            <div className="law-viewer-meta-item">
              <dt>{t("约束力", "Binding Force")}</dt>
              <dd>
                <span className="citation-binding-badge">
                  {BINDING_LABELS[bindingForce] ?? bindingForce}
                </span>
              </dd>
            </div>
          </div>

          {sourceUrl && (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="law-viewer-source-link"
            >
              {t("在官方来源查看完整文件", "View official source")} ↗
            </a>
          )}
        </header>

        <div className="law-viewer-content">
          {article ? (
            <article className="law-viewer-articles">
              {article.prev_article_no && article.prev_article_content && (
                <section className="law-viewer-article law-viewer-article-context">
                  <h3>{t("第", "Article ")}{article.prev_article_no}{t("条", "")}</h3>
                  <p>{article.prev_article_content}</p>
                </section>
              )}

              <section
                ref={targetRef}
                className="law-viewer-article law-viewer-article-target"
              >
                <h3>
                  {t("第", "Article ")}{article.article_no}{t("条", "")}
                  <span className="law-viewer-article-highlight-badge">
                    {t("引用条文", "Cited Article")}
                  </span>
                </h3>
                <p>{article.article_content}</p>
              </section>

              {article.next_article_no && article.next_article_content && (
                <section className="law-viewer-article law-viewer-article-context">
                  <h3>{t("第", "Article ")}{article.next_article_no}{t("条", "")}</h3>
                  <p>{article.next_article_content}</p>
                </section>
              )}
            </article>
          ) : (
            <p className="law-viewer-preview-text">
              {(sourceMeta as Record<string, string>).snapshot_path
                ? t("法规全文已加载。请选择条文查看。", "Full text loaded. Select an article to view.")
                : t("该法规暂无本地快照文本。", "No local snapshot available for this law.")}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
