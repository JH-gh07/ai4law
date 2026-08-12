/**
 * 知识库中心页面组件
 * 该组件用于展示知识库中心的内容，包括法规、案例、引用联动和条文检索等功能。
 * 用户可以通过该页面搜索和浏览知识库条目，查看法规和案例的详细信息，以及进行引用联动和条文检索。
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useLang } from "../lib/language";
import { formatLegalLocator } from "../lib/legal-locator";
import { KnowledgeContentRenderer } from "../components/citation/KnowledgeContentRenderer";
import {
  fetchArticleDetail,
  fetchKnowledgeCaseDetail,
  fetchKnowledgeCitation,
  fetchKnowledgeIndex,
  fetchKnowledgeSearch,
  fetchKnowledgeSourceDetail,
  syncKnowledgeIndex,
  type ArticleDetail,
  type KnowledgeSearchItem,
} from "../api/knowledge";

type KnowledgeRow = Record<string, string>;
type KnowledgeTab = "sources" | "cases" | "citation" | "articles";

const includesWithSelection = (value: string, selected: string[]) => selected.includes(value);

const toggleValue = (items: string[], value: string): string[] =>
  items.includes(value) ? items.filter((item) => item !== value) : [...items, value];

const rowText = (row: KnowledgeRow, key: string, fallback = "-"): string => row[key] || fallback;

const ARTICLE_SCENARIO_OPTIONS = [
  { value: "all", zh: "通用法规", en: "General Sources" },
  { value: "assessment", zh: "评估申报", en: "Assessment Filing" },
  { value: "cn_flow", zh: "路径判断", en: "Path Diagnosis" },
  { value: "scc", zh: "标准合同", en: "Standard Contract" },
  { value: "bcr", zh: "BCR", en: "BCR" },
  { value: "tia", zh: "TIA", en: "TIA" },
  { value: "dpia", zh: "DPIA", en: "DPIA" },
  { value: "cpra", zh: "美国州法", en: "US State Privacy" },
];

const articleScenarioLabel = (value: string, lang: "zh" | "en"): string => {
  const matched = ARTICLE_SCENARIO_OPTIONS.find((item) => item.value === value);
  if (matched) return lang === "zh" ? matched.zh : matched.en;
  return value;
};

const articleScenarioSummary = (value: string, lang: "zh" | "en"): string => {
  const parts = value.split("|").map((item) => item.trim()).filter(Boolean);
  if (parts.length === 0) return lang === "zh" ? "通用法规" : "General Sources";
  return parts.map((item) => articleScenarioLabel(item, lang)).join(" / ");
};

export function EvidenceCenterPage() {// 知识库中心页面组件
  const { lang } = useLang();

  const copy = lang === "zh"
    ? {
      title: "知识库中心",
      searchPlaceholder: "搜索法规、案例、模板或适用主题…",
      searchNow: "搜索",
      sourceTab: "法规与依据",
      caseTab: "典型案例",
      citationTab: "引用联动",
      citationLinked: "引用联动",
      sourceStat: "依据条目",
      caseStat: "案例条目",
      currentStat: "当前命中",
      sourceListTitle: "法规、指南与模板",
      sourceDetailTitle: "知识详情",
      caseListTitle: "典型案例列表",
      caseDetailTitle: "案例详情",
      sourceFilterCategory: "按内容分类",
      sourceFilterJurisdiction: "按适用法域",
      sourceFilterUsage: "按使用方式",
      caseFilterJurisdiction: "按法域过滤",
      caseFilterScenario: "按适用场景过滤",
      selectAll: "全选",
      clearAll: "清空",
      openSource: "查看官方来源",
      openInLawReader: "在法规阅读器中查看",
      openCase: "打开案例来源",
      previewTitle: "内容预览",
      casePreviewTitle: "案例内容预览",
      citationInputLabel: "输入引用文本",
      citationPlaceholder: "例如：数据出境安全评估办法第4条",
      citationSummaryTitle: "引用识别结果",
      category: "内容分类",
      usage: "使用方式",
      suitableFor: "适用场景",
      authority: "权威级别",
      bindingForce: "约束力",
      reportUsage: "正式报告使用",
      publisher: "发布机构",
      summaryTitle: "内容简介",
      noData: "暂无数据。",
      loading: "加载中…",
      matchEmpty: "未匹配到知识库条目。",
      optionsEmpty: "暂无可选项",
      syncNow: "同步知识内容",
      syncing: "同步中…",
      syncAt: "最近更新",
      syncStatus: "内容状态",
      syncReady: "内容可用",
      syncMissing: "部分内容缺失",
      manifestTotal: "纳入同步范围",
      manifestMigrated: "已迁移落盘",
      manifestVisible: "前端可见",
      articlesTab: "条文检索",
      articlesPlaceholder: "输入关键词检索法规条文，如：标准合同备案",
      articlesFilterJurisdiction: "法域",
      articlesFilterPath: "适用主题",
      articlesSearching: "检索中…",
      articlesEmpty: "未检索到相关条文。",
      articlesHitCount: "命中条文",
      articlesDetailTitle: "条文详情",
      articlesContentLabel: "条文内容",
      articlesSourceLink: "查看来源",
      articlesBrowseSource: "进入法规阅读页",
      userGuideTitle: "使用说明",
      citationHint: "输入报告或页面中的引用文本，系统会为你定位对应知识条目。",
      citationPreviewTitle: "关联依据摘要",
    }
    : {
      title: "Knowledge Center",
      searchPlaceholder: "Search laws, cases, templates, or topics...",
      searchNow: "Search",
      sourceTab: "Legal Sources",
      caseTab: "Cases",
      citationTab: "Citation Linkage",
      citationLinked: "Citation Linkage",
      sourceStat: "Source Items",
      caseStat: "Case Items",
      currentStat: "Matched Items",
      sourceListTitle: "Laws, Guidance, and Templates",
      sourceDetailTitle: "Knowledge Detail",
      caseListTitle: "Case List",
      caseDetailTitle: "Case Detail",
      sourceFilterCategory: "Filter by category",
      sourceFilterJurisdiction: "Filter by jurisdiction",
      sourceFilterUsage: "Filter by usage",
      caseFilterJurisdiction: "Filter by jurisdiction",
      caseFilterScenario: "Filter by scenario",
      selectAll: "Select All",
      clearAll: "Clear",
      openSource: "Open Official Source",
      openInLawReader: "Open in Law Reader",
      openCase: "Open Case Source",
      previewTitle: "Preview",
      casePreviewTitle: "Case Preview",
      citationInputLabel: "Enter citation text",
      citationPlaceholder: "e.g. Data Export Security Assessment Measures Article 4",
      citationSummaryTitle: "Citation Match",
      category: "Category",
      usage: "Usage",
      suitableFor: "Suitable For",
      authority: "Authority",
      bindingForce: "Binding Force",
      reportUsage: "Report Usage",
      publisher: "Publisher",
      summaryTitle: "Summary",
      noData: "No data.",
      loading: "Loading...",
      matchEmpty: "No knowledge entry matched.",
      optionsEmpty: "No options",
      syncNow: "Sync Knowledge",
      syncing: "Syncing...",
      syncAt: "Last Updated",
      syncStatus: "Content Status",
      syncReady: "Ready",
      syncMissing: "Partially Missing",
      manifestTotal: "Tracked Assets",
      manifestMigrated: "Migrated Assets",
      manifestVisible: "Frontend Visible",
      articlesTab: "Article Search",
      articlesPlaceholder: "Search regulation articles, e.g. standard contract filing",
      articlesFilterJurisdiction: "Jurisdiction",
      articlesFilterPath: "Topic",
      articlesSearching: "Searching...",
      articlesEmpty: "No articles found.",
      articlesHitCount: "Articles Found",
      articlesDetailTitle: "Article Detail",
      articlesContentLabel: "Content",
      articlesSourceLink: "View Source",
      articlesBrowseSource: "Open Law Reader",
      userGuideTitle: "How to Use",
      citationHint: "Paste a citation from a report or page and the system will locate the matching knowledge entry.",
      citationPreviewTitle: "Linked Source Summary",
    };

  const [tab, setTab] = useState<KnowledgeTab>("sources");
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [sources, setSources] = useState<KnowledgeRow[]>([]);
  const [cases, setCases] = useState<KnowledgeRow[]>([]);
  const [sourceCategoryOptions, setSourceCategoryOptions] = useState<string[]>([]);
  const [sourceJurisdictionOptions, setSourceJurisdictionOptions] = useState<string[]>([]);
  const [sourceUsageOptions, setSourceUsageOptions] = useState<string[]>([]);
  const [caseJurisdictionOptions, setCaseJurisdictionOptions] = useState<string[]>([]);
  const [caseScenarioOptions, setCaseScenarioOptions] = useState<string[]>([]);
  const [summary, setSummary] = useState({ source_count: 0, case_count: 0 });
  const [syncMeta, setSyncMeta] = useState({
    synced_at: "",
    cache_refreshed: false,
    sources_csv_path: "",
    cases_csv_path: "",
    spec_asset_manifest_path: "",
    sources_csv_exists: false,
    cases_csv_exists: false,
    spec_asset_manifest_exists: false,
    sources_csv_mtime: "",
    cases_csv_mtime: "",
    spec_asset_manifest_mtime: "",
    manifest_total_files: 0,
    manifest_frontend_visible_files: 0,
    manifest_migrated_files: 0,
  });
  const [syncing, setSyncing] = useState(false);

  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedSourceJurisdictions, setSelectedSourceJurisdictions] = useState<string[]>([]);
  const [selectedUsages, setSelectedUsages] = useState<string[]>([]);
  const [selectedCaseJurisdictions, setSelectedCaseJurisdictions] = useState<string[]>([]);
  const [selectedScenarios, setSelectedScenarios] = useState<string[]>([]);

  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [sourcePreview, setSourcePreview] = useState("");
  const [casePreview, setCasePreview] = useState("");

  const [citationQuery, setCitationQuery] = useState("数据出境安全评估办法第4条");
  const [citationMatch, setCitationMatch] = useState<KnowledgeRow | null>(null);
  const [citationPreview, setCitationPreview] = useState("");
  const [citationLoading, setCitationLoading] = useState(false);

  const [articlesQuery, setArticlesQuery] = useState("");
  const [articlesJurisdiction, setArticlesJurisdiction] = useState<string>("");
  const [articlesPath, setArticlesPath] = useState<string>("");
  const [articlesResults, setArticlesResults] = useState<KnowledgeSearchItem[]>([]);
  const [articlesLoading, setArticlesLoading] = useState(false);
  const [articlesHitCount, setArticlesHitCount] = useState(0);
  const [selectedArticleId, setSelectedArticleId] = useState<string>("");

  // URL query parameter support for direct citation navigation.
  // ?source=xxx  → auto-expand the source detail panel
  // &article=yyy  → fetch and display the specific article content
  const [searchParams] = useSearchParams();
  const [urlArticleDetail, setUrlArticleDetail] = useState<ArticleDetail | null>(null);
  const [urlArticleLoading, setUrlArticleLoading] = useState(false);
  const urlArticleRef = useRef<HTMLDivElement>(null);

  const applyKnowledgeIndexData = (
    data: Awaited<ReturnType<typeof fetchKnowledgeIndex>>
  ): void => {
    setSources(data.sources);
    setCases(data.cases);
    setSummary(data.summary);
    setSyncMeta(data.sync_meta);

    setSourceCategoryOptions(data.source_options.categories);
    setSourceJurisdictionOptions(data.source_options.jurisdictions);
    setSourceUsageOptions(data.source_options.usages);
    setCaseJurisdictionOptions(data.case_options.jurisdictions);
    setCaseScenarioOptions(data.case_options.scenarios);

    setSelectedCategories(data.source_options.categories);
    setSelectedSourceJurisdictions(data.source_options.jurisdictions);
    setSelectedUsages(data.source_options.usages);
    setSelectedCaseJurisdictions(data.case_options.jurisdictions);
    setSelectedScenarios(data.case_options.scenarios);
  };

  useEffect(() => {
    let isActive = true;

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await fetchKnowledgeIndex();
        if (!isActive) return;
        applyKnowledgeIndexData(data);
      } catch (err) {
        if (!isActive) return;
        setError(err instanceof Error ? err.message : "Failed to load knowledge index.");
      } finally {
        if (isActive) setLoading(false);
      }
    };

    void load();
    return () => {
      isActive = false;
    };
  }, []);

  // ── URL query parameter handling ──────────────────────────────────────────
  // When the page is opened with ?source=CN-LAW-003&article=13 (from a
  // citation click in a report), auto-expand the matching source and fetch
  // the article detail.

  useEffect(() => {
    const sourceParam = searchParams.get("source");
    const articleParam = searchParams.get("article");

    if (!sourceParam || loading) return;

    // Switch to sources tab and select the requested source.
    setTab("sources");
    setSelectedSourceId(sourceParam);

    if (articleParam) {
      setUrlArticleLoading(true);
      setUrlArticleDetail(null);
      fetchArticleDetail(sourceParam, articleParam)
        .then((detail) => {
          setUrlArticleDetail(detail);
          setUrlArticleLoading(false);
        })
        .catch(() => {
          setUrlArticleDetail(null);
          setUrlArticleLoading(false);
        });
    }
  }, [searchParams, loading]);

  // Auto-scroll to the article content when it renders.
  useEffect(() => {
    if (urlArticleDetail && urlArticleRef.current) {
      urlArticleRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [urlArticleDetail]);

  // ── end URL params ────────────────────────────────────────────────────────

  const filteredSources = useMemo(() => {
    const token = keyword.trim().toLowerCase();
    return sources
      .filter((item) => includesWithSelection(rowText(item, "category", ""), selectedCategories))
      .filter((item) => includesWithSelection(rowText(item, "jurisdiction", ""), selectedSourceJurisdictions))
      .filter((item) => includesWithSelection(rowText(item, "usage", ""), selectedUsages))
      .filter((item) => {
        if (!token) return true;
        return `${rowText(item, "title")} ${rowText(item, "publisher")} ${rowText(item, "summary")} ${rowText(item, "suitable_for")}`
          .toLowerCase()
          .includes(token);
      });
  }, [keyword, selectedCategories, selectedSourceJurisdictions, selectedUsages, sources]);

  const filteredCases = useMemo(() => {
    const token = keyword.trim().toLowerCase();
    return cases
      .filter((item) => includesWithSelection(rowText(item, "jurisdiction", ""), selectedCaseJurisdictions))
      .filter((item) => includesWithSelection(rowText(item, "suitable_for", ""), selectedScenarios))
      .filter((item) => {
        if (!token) return true;
        return `${rowText(item, "title")} ${rowText(item, "publisher")} ${rowText(item, "summary")} ${rowText(item, "suitable_for")}`
          .toLowerCase()
          .includes(token);
      });
  }, [cases, keyword, selectedCaseJurisdictions, selectedScenarios]);

  const selectedSource = useMemo(
    () => filteredSources.find((item) => rowText(item, "source_id") === selectedSourceId) ?? filteredSources[0] ?? null,
    [filteredSources, selectedSourceId]
  );
  const selectedCase = useMemo(
    () => filteredCases.find((item) => rowText(item, "case_id") === selectedCaseId) ?? filteredCases[0] ?? null,
    [filteredCases, selectedCaseId]
  );

  useEffect(() => {
    const sourceId = selectedSource?.source_id;
    if (!sourceId) {
      setSourcePreview("");
      return;
    }

    let isActive = true;
    void fetchKnowledgeSourceDetail(sourceId)
      .then((data) => {
        if (isActive) setSourcePreview(data.preview);
      })
      .catch(() => {
        if (isActive) setSourcePreview("");
      });

    return () => {
      isActive = false;
    };
  }, [selectedSource?.source_id]);

  useEffect(() => {
    const caseId = selectedCase?.case_id;
    if (!caseId) {
      setCasePreview("");
      return;
    }

    let isActive = true;
    void fetchKnowledgeCaseDetail(caseId)
      .then((data) => {
        if (isActive) setCasePreview(data.preview);
      })
      .catch(() => {
        if (isActive) setCasePreview("");
      });

    return () => {
      isActive = false;
    };
  }, [selectedCase?.case_id]);

  useEffect(() => {
    const query = citationQuery.trim();
    if (!query) {
      setCitationMatch(null);
      setCitationPreview("");
      return;
    }

    let isActive = true;
    const timer = globalThis.setTimeout(() => {
      setCitationLoading(true);
      void fetchKnowledgeCitation(query)
        .then((data) => {
          if (!isActive) return;
          setCitationMatch(data.matched);
          setCitationPreview(data.preview);
        })
        .catch(() => {
          if (!isActive) return;
          setCitationMatch(null);
          setCitationPreview("");
        })
        .finally(() => {
          if (isActive) setCitationLoading(false);
        });
    }, 260);

    return () => {
      isActive = false;
      globalThis.clearTimeout(timer);
    };
  }, [citationQuery]);

  useEffect(() => {
    const query = articlesQuery.trim();
    if (!query) {
      setArticlesResults([]);
      setArticlesHitCount(0);
      return;
    }

    let isActive = true;
    const timer = globalThis.setTimeout(() => {
      setArticlesLoading(true);
      void fetchKnowledgeSearch({
        q: query,
        jurisdiction: articlesJurisdiction || undefined,
        path: articlesPath || undefined,
        top_k: 8,
      })
        .then((data) => {
          if (!isActive) return;
          setArticlesResults(data.items);
          setArticlesHitCount(data.hit_count);
          setSelectedArticleId(data.items[0]?.id ?? "");
        })
        .catch(() => {
          if (!isActive) return;
          setArticlesResults([]);
          setArticlesHitCount(0);
        })
        .finally(() => {
          if (isActive) setArticlesLoading(false);
        });
    }, 300);

    return () => {
      isActive = false;
      globalThis.clearTimeout(timer);
    };
  }, [articlesQuery, articlesJurisdiction, articlesPath]);

  const selectedArticle = articlesResults.find((item) => item.id === selectedArticleId) ?? articlesResults[0] ?? null;

  const currentMatches = tab === "sources" ? filteredSources.length : tab === "cases" ? filteredCases.length : tab === "articles" ? articlesHitCount : citationMatch ? 1 : 0;
  const syncTimeLabel = syncMeta.synced_at
    ? new Date(syncMeta.synced_at).toLocaleString(lang === "zh" ? "zh-CN" : "en-US", { hour12: false })
    : "-";
  const syncFileStatusLabel = syncMeta.sources_csv_exists && syncMeta.cases_csv_exists && syncMeta.spec_asset_manifest_exists
    ? copy.syncReady
    : copy.syncMissing;

  const handleSyncNow = async () => {
    setSyncing(true);
    setError("");
    try {
      const data = await syncKnowledgeIndex();
      applyKnowledgeIndexData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <section className="page-shell evidence-page kc-page">
      <section className="kc-hero">
        <div className="kc-hero-title-row">
          <h2>{copy.title}</h2>
          <div className="kc-search-row">
            <input
              className="resource-search kc-search-input"
              placeholder={copy.searchPlaceholder}
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
            />
            <button className="kc-btn primary" type="button">{copy.searchNow}</button>
          </div>
          <button className="kc-btn" onClick={() => void handleSyncNow()} disabled={loading || syncing}>
            {syncing ? copy.syncing : copy.syncNow}
          </button>
        </div>

        <div className="kc-quick-entry-row">
          <button className={`quick-chip ${tab === "sources" ? "active" : ""}`} onClick={() => setTab("sources")}>{copy.sourceTab}</button>
          <button className={`quick-chip ${tab === "cases" ? "active" : ""}`} onClick={() => setTab("cases")}>{copy.caseTab}</button>
          <button className={`quick-chip ${tab === "articles" ? "active" : ""}`} onClick={() => setTab("articles")}>{copy.articlesTab}</button>
          <button className={`quick-chip ${tab === "citation" ? "active" : ""}`} onClick={() => setTab("citation")}>{copy.citationLinked}</button>
        </div>

        <div className="kc-status-row">
          <article className="kc-status-item">
            <div className="k">{copy.sourceStat}</div>
            <div className="v">{summary.source_count}</div>
          </article>
          <article className="kc-status-item">
            <div className="k">{copy.caseStat}</div>
            <div className="v">{summary.case_count}</div>
          </article>
          <article className="kc-status-item">
            <div className="k">{copy.currentStat}</div>
            <div className="v">{currentMatches}</div>
          </article>
          <article className="kc-status-item">
            <div className="k">{copy.syncAt}</div>
            <div className="v">{syncTimeLabel}</div>
          </article>
          <article className="kc-status-item">
            <div className="k">{copy.manifestTotal}</div>
            <div className="v">{syncMeta.manifest_total_files}</div>
          </article>
          <article className="kc-status-item">
            <div className="k">{copy.manifestMigrated}</div>
            <div className="v">{syncMeta.manifest_migrated_files}</div>
          </article>
          <article className="kc-status-item">
            <div className="k">{copy.manifestVisible}</div>
            <div className="v">{syncMeta.manifest_frontend_visible_files}</div>
          </article>
        </div>
      </section>

      {tab !== "citation" ? (
        <section className="kc-filter-bar">
          {tab === "sources" ? (
            <>
              <div className="knowledge-filter-group kc-filter-group-h">
                <small>{copy.sourceFilterCategory}</small>
                <div className="knowledge-chip-row">
                  {sourceCategoryOptions.map((option) => (
                    <button key={option} className={`chip-btn ${selectedCategories.includes(option) ? "active" : ""}`}
                      onClick={() => setSelectedCategories((prev) => toggleValue(prev, option))}>
                      {option}
                    </button>
                  ))}
                  {sourceCategoryOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
                </div>
                <div className="knowledge-filter-actions">
                  <button className="ghost-btn" onClick={() => setSelectedCategories(sourceCategoryOptions)}>{copy.selectAll}</button>
                  <button className="ghost-btn" onClick={() => setSelectedCategories([])}>{copy.clearAll}</button>
                </div>
              </div>
              <div className="knowledge-filter-group kc-filter-group-h">
                <small>{copy.sourceFilterJurisdiction}</small>
                <div className="knowledge-chip-row">
                  {sourceJurisdictionOptions.map((option) => (
                    <button key={option} className={`chip-btn ${selectedSourceJurisdictions.includes(option) ? "active" : ""}`}
                      onClick={() => setSelectedSourceJurisdictions((prev) => toggleValue(prev, option))}>
                      {option}
                    </button>
                  ))}
                  {sourceJurisdictionOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
                </div>
                <div className="knowledge-filter-actions">
                  <button className="ghost-btn" onClick={() => setSelectedSourceJurisdictions(sourceJurisdictionOptions)}>{copy.selectAll}</button>
                  <button className="ghost-btn" onClick={() => setSelectedSourceJurisdictions([])}>{copy.clearAll}</button>
                </div>
              </div>
              <div className="knowledge-filter-group kc-filter-group-h">
                <small>{copy.sourceFilterUsage}</small>
                <div className="knowledge-chip-row">
                  {sourceUsageOptions.map((option) => (
                    <button key={option} className={`chip-btn ${selectedUsages.includes(option) ? "active" : ""}`}
                      onClick={() => setSelectedUsages((prev) => toggleValue(prev, option))}>
                      {option}
                    </button>
                  ))}
                  {sourceUsageOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
                </div>
                <div className="knowledge-filter-actions">
                  <button className="ghost-btn" onClick={() => setSelectedUsages(sourceUsageOptions)}>{copy.selectAll}</button>
                  <button className="ghost-btn" onClick={() => setSelectedUsages([])}>{copy.clearAll}</button>
                </div>
              </div>
            </>
          ) : tab === "cases" ? (
            <>
              <div className="knowledge-filter-group kc-filter-group-h">
                <small>{copy.caseFilterJurisdiction}</small>
                <div className="knowledge-chip-row">
                  {caseJurisdictionOptions.map((option) => (
                    <button key={option} className={`chip-btn ${selectedCaseJurisdictions.includes(option) ? "active" : ""}`}
                      onClick={() => setSelectedCaseJurisdictions((prev) => toggleValue(prev, option))}>
                      {option}
                    </button>
                  ))}
                  {caseJurisdictionOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
                </div>
                <div className="knowledge-filter-actions">
                  <button className="ghost-btn" onClick={() => setSelectedCaseJurisdictions(caseJurisdictionOptions)}>{copy.selectAll}</button>
                  <button className="ghost-btn" onClick={() => setSelectedCaseJurisdictions([])}>{copy.clearAll}</button>
                </div>
              </div>
              <div className="knowledge-filter-group kc-filter-group-h">
                <small>{copy.caseFilterScenario}</small>
                <div className="knowledge-chip-row">
                  {caseScenarioOptions.map((option) => (
                    <button key={option} className={`chip-btn ${selectedScenarios.includes(option) ? "active" : ""}`}
                      onClick={() => setSelectedScenarios((prev) => toggleValue(prev, option))}>
                      {option}
                    </button>
                  ))}
                  {caseScenarioOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
                </div>
                <div className="knowledge-filter-actions">
                  <button className="ghost-btn" onClick={() => setSelectedScenarios(caseScenarioOptions)}>{copy.selectAll}</button>
                  <button className="ghost-btn" onClick={() => setSelectedScenarios([])}>{copy.clearAll}</button>
                </div>
              </div>
            </>
          ) : tab === "articles" ? (
            <>
              <div className="knowledge-filter-group kc-filter-group-h">
                <small>{copy.articlesFilterJurisdiction}</small>
                <div className="knowledge-chip-row">
                  {["cn", "eu", "us"].map((jur) => (
                    <button
                      key={jur}
                      className={`chip-btn ${articlesJurisdiction === jur ? "active" : ""}`}
                      onClick={() => setArticlesJurisdiction((prev) => prev === jur ? "" : jur)}
                    >
                      {jur.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
              <div className="knowledge-filter-group kc-filter-group-h">
                <small>{copy.articlesFilterPath}</small>
                <div className="knowledge-chip-row">
                  {ARTICLE_SCENARIO_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      className={`chip-btn ${articlesPath === option.value ? "active" : ""}`}
                      onClick={() => setArticlesPath((prev) => prev === option.value ? "" : option.value)}
                    >
                      {lang === "zh" ? option.zh : option.en}
                    </button>
                  ))}
                </div>
              </div>
              <div className="knowledge-filter-group kc-filter-group-h" style={{ minWidth: "220px" }}>
                <small>{copy.articlesPlaceholder}</small>
                <input
                  className="resource-search"
                  placeholder={copy.articlesPlaceholder}
                  value={articlesQuery}
                  onChange={(e) => setArticlesQuery(e.target.value)}
                />
              </div>
            </>
          ) : null}
        </section>
      ) : null}

      <section className="kc-main-grid">
        <aside className="kc-col">
          <header className="kc-col-head">
            <span>{tab === "sources" ? copy.sourceListTitle : tab === "cases" ? copy.caseListTitle : tab === "articles" ? copy.articlesTab : copy.citationTab}</span>
            <small>{copy.currentStat}: {currentMatches}</small>
          </header>
          <div className="kc-col-body">
            {tab === "sources" ? (
              <>
                <div className="evidence-hit-scroll kc-list-scroll">
                  {filteredSources.map((row) => {
                    const sourceId = rowText(row, "source_id");
                    return (
                      <article key={sourceId} className={`evidence-hit-item ${selectedSource?.source_id === sourceId ? "active" : ""}`} onClick={() => setSelectedSourceId(sourceId)}>
                        <small>{rowText(row, "category")} · {rowText(row, "jurisdiction")}</small>
                        <strong>{rowText(row, "title")}</strong>
                        <p>{rowText(row, "summary")}</p>
                      </article>
                    );
                  })}
                  {filteredSources.length === 0 ? <p className="resource-empty">{copy.noData}</p> : null}
                </div>
              </>
            ) : null}

            {tab === "cases" ? (
              <>
                <div className="evidence-hit-scroll kc-list-scroll">
                  {filteredCases.map((row) => {
                    const caseId = rowText(row, "case_id");
                    return (
                      <article key={caseId} className={`evidence-hit-item ${selectedCase?.case_id === caseId ? "active" : ""}`} onClick={() => setSelectedCaseId(caseId)}>
                        <small>{rowText(row, "jurisdiction")} · {rowText(row, "suitable_for")}</small>
                        <strong>{rowText(row, "title")}</strong>
                        <p>{rowText(row, "summary")}</p>
                      </article>
                    );
                  })}
                  {filteredCases.length === 0 ? <p className="resource-empty">{copy.noData}</p> : null}
                </div>
              </>
            ) : null}

            {tab === "articles" ? (
              <>
                <div className="evidence-hit-scroll kc-list-scroll">
                  {articlesLoading ? <p className="resource-empty">{copy.articlesSearching}</p> : null}
                  {!articlesLoading && articlesQuery.trim() && articlesResults.length === 0 ? (
                    <p className="resource-empty">{copy.articlesEmpty}</p>
                  ) : null}
                  {articlesResults.map((item) => (
                    <article
                      key={item.id}
                      className={`evidence-hit-item ${selectedArticle?.id === item.id ? "active" : ""}`}
                      onClick={() => setSelectedArticleId(item.id)}
                    >
                      <small>
                        {item.jurisdiction.toUpperCase()} · {articleScenarioSummary(item.path, lang)}
                      </small>
                      <strong>{item.title}</strong>
                      <p>{item.article}</p>
                    </article>
                  ))}
                </div>
              </>
            ) : null}

            {tab === "citation" ? (
              <div className="evidence-citation-panel">
                <article className="citation-query-card">
                  <label className="field-wrap">
                    <span>{copy.citationInputLabel}</span>
                    <input value={citationQuery} placeholder={copy.citationPlaceholder} onChange={(event) => setCitationQuery(event.target.value)} />
                  </label>
                </article>
                {!citationLoading && !citationMatch ? <article className="citation-empty-card"><p>{copy.matchEmpty}</p></article> : null}
                {!citationLoading && citationMatch ? (
                  <article className="citation-match-card">
                    <h4>{copy.citationSummaryTitle}</h4>
                    <div className="citation-kv-grid">
                      <div className="citation-kv-row"><span>{copy.category}</span><strong>{rowText(citationMatch, "category")}</strong></div>
                      <div className="citation-kv-row"><span>{copy.authority}</span><strong>{rowText(citationMatch, "authority")}</strong></div>
                      <div className="citation-kv-row"><span>{copy.reportUsage}</span><strong>{rowText(citationMatch, "report_usage")}</strong></div>
                    </div>
                    <p className="citation-title">{rowText(citationMatch, "title")}</p>
                    <p>{rowText(citationMatch, "summary")}</p>
                    {citationPreview ? (
                      <div className="knowledge-preview-block">
                        <strong>{copy.citationPreviewTitle}</strong>
                        <p>{citationPreview}</p>
                      </div>
                    ) : null}
                  </article>
                ) : null}
              </div>
            ) : null}
          </div>
        </aside>

        <main className="kc-col">
          <header className="kc-col-head">
            <span>{tab === "sources" ? copy.sourceDetailTitle : tab === "cases" ? copy.caseDetailTitle : tab === "articles" ? copy.articlesDetailTitle : copy.previewTitle}</span>
          </header>
          <div className="kc-col-body">
            {loading ? <p className="resource-empty">{copy.loading}</p> : null}
            {error ? <p className="resource-empty">{error}</p> : null}

            {tab === "articles" ? (
              selectedArticle ? (
                <article className="evidence-detail-card">
                  <div className="evidence-detail-meta">
                    <span>{selectedArticle.jurisdiction.toUpperCase()}</span>
                    <span>{articleScenarioSummary(selectedArticle.path, lang)}</span>
                  </div>
                  <h4>{selectedArticle.title}</h4>
                  <p style={{ fontWeight: 600, marginBottom: "0.25rem" }}>{selectedArticle.article}</p>
                  <div className="knowledge-preview-block">
                    <strong>{copy.articlesContentLabel}</strong>
                    <KnowledgeContentRenderer content={selectedArticle.content} variant="evidence" />
                  </div>
                  <div className="knowledge-chip-row" style={{ marginTop: "0.75rem" }}>
                    <a
                      className="ghost-btn link-btn"
                      href={`/knowledge/laws/${encodeURIComponent(selectedArticle.id.split("::")[0])}?article=${encodeURIComponent(selectedArticle.article.replace(/^第|条$/g, "").trim())}`}
                    >
                      {copy.articlesBrowseSource}
                    </a>
                    {selectedArticle.source_url ? (
                      <a className="ghost-btn link-btn" href={selectedArticle.source_url} target="_blank" rel="noreferrer">
                        {copy.articlesSourceLink}
                      </a>
                    ) : null}
                  </div>
                  {selectedArticle.keywords.length > 0 ? (
                    <div className="knowledge-chip-row" style={{ marginTop: "0.75rem" }}>
                      {selectedArticle.keywords.map((kw) => (
                        <span key={kw} className="chip-btn" style={{ cursor: "default" }}>{kw}</span>
                      ))}
                    </div>
                  ) : null}
                </article>
              ) : articlesQuery.trim() ? (
                <p className="resource-empty">{copy.articlesEmpty}</p>
              ) : (
                <p className="resource-empty">{copy.articlesPlaceholder}</p>
              )
            ) : null}

            {!loading && tab === "sources" ? (
              selectedSource ? (
                <article className="evidence-detail-card">
                  <div className="evidence-detail-meta">
                    <span>{rowText(selectedSource, "category")}</span>
                    <span>{rowText(selectedSource, "jurisdiction")}</span>
                  </div>
                  <h4>{rowText(selectedSource, "title")}</h4>
                  <div className="citation-kv-grid">
                    <div className="citation-kv-row"><span>{copy.publisher}</span><strong>{rowText(selectedSource, "publisher")}</strong></div>
                    <div className="citation-kv-row"><span>{copy.authority}</span><strong>{rowText(selectedSource, "authority")}</strong></div>
                    <div className="citation-kv-row"><span>{copy.bindingForce}</span><strong>{rowText(selectedSource, "binding_force")}</strong></div>
                    <div className="citation-kv-row"><span>{copy.suitableFor}</span><strong>{rowText(selectedSource, "suitable_for")}</strong></div>
                    <div className="citation-kv-row"><span>{copy.usage}</span><strong>{rowText(selectedSource, "usage")}</strong></div>
                    <div className="citation-kv-row"><span>{copy.reportUsage}</span><strong>{rowText(selectedSource, "report_usage")}</strong></div>
                  </div>
                  <div className="knowledge-preview-block">
                    <strong>{copy.summaryTitle}</strong>
                    <p>{rowText(selectedSource, "summary", "-")}</p>
                  </div>

                  {/* Article detail from ?article= query param */}
                  {urlArticleLoading ? (
                    <div className="knowledge-preview-block"><p>{copy.loading}</p></div>
                  ) : urlArticleDetail ? (
                    <div ref={urlArticleRef} className="knowledge-preview-block" style={{ borderLeft: "3px solid var(--color-primary, #2563eb)", paddingLeft: "0.75rem" }}>
                      <strong>{formatLegalLocator(urlArticleDetail.article_no)}</strong>
                      <KnowledgeContentRenderer content={urlArticleDetail.article_content} variant="evidence" />
                      {urlArticleDetail.source_url ? (
                        <a className="ghost-btn link-btn" href={urlArticleDetail.source_url} target="_blank" rel="noreferrer" style={{ marginTop: "0.5rem" }}>
                          {copy.openSource}
                        </a>
                      ) : null}
                    </div>
                  ) : null}

                  {selectedSource.external_url || selectedSource.url ? <a className="ghost-btn link-btn" href={selectedSource.external_url || selectedSource.url} target="_blank" rel="noreferrer">{copy.openSource}</a> : null}
                  {selectedSource.knowledge_url ? <a className="ghost-btn link-btn" href={selectedSource.knowledge_url}>{copy.openInLawReader}</a> : null}
                  {sourcePreview ? <div className="knowledge-preview-block"><strong>{copy.previewTitle}</strong><p>{sourcePreview}</p></div> : null}
                </article>
              ) : <p className="resource-empty">{copy.noData}</p>
            ) : null}

            {!loading && tab === "cases" ? (
              selectedCase ? (
                <article className="evidence-detail-card">
                  <div className="evidence-detail-meta">
                    <span>{rowText(selectedCase, "jurisdiction")}</span>
                    <span>{rowText(selectedCase, "suitable_for")}</span>
                  </div>
                  <h4>{rowText(selectedCase, "title")}</h4>
                  <div className="citation-kv-grid">
                    <div className="citation-kv-row"><span>{copy.publisher}</span><strong>{rowText(selectedCase, "publisher")}</strong></div>
                    <div className="citation-kv-row"><span>{copy.suitableFor}</span><strong>{rowText(selectedCase, "suitable_for")}</strong></div>
                    <div className="citation-kv-row"><span>{copy.usage}</span><strong>{rowText(selectedCase, "usage")}</strong></div>
                  </div>
                  <div className="knowledge-preview-block">
                    <strong>{copy.summaryTitle}</strong>
                    <p>{rowText(selectedCase, "summary", "-")}</p>
                  </div>
                  <div className="knowledge-preview-block">
                    <strong>{lang === "zh" ? "适用限制" : "Limitations"}</strong>
                    <p>{rowText(selectedCase, "limitations", "-")}</p>
                  </div>
                  {selectedCase.url ? <a className="ghost-btn link-btn" href={selectedCase.url} target="_blank" rel="noreferrer">{copy.openCase}</a> : null}
                  {casePreview ? <div className="knowledge-preview-block"><strong>{copy.casePreviewTitle}</strong><p>{casePreview}</p></div> : null}
                </article>
              ) : <p className="resource-empty">{copy.noData}</p>
            ) : null}

            {!loading && tab === "citation" ? (
              <>
                {citationLoading ? <article className="citation-empty-card"><p>{copy.loading}</p></article> : null}
                {!citationLoading && citationPreview ? (
                  <article className="citation-preview-card">
                    <strong>{copy.previewTitle}</strong>
                    <p>{citationPreview}</p>
                  </article>
                ) : null}
              </>
            ) : null}
          </div>
        </main>

        <aside className="kc-col">
          <header className="kc-col-head">
            <span>{lang === "zh" ? "引用与说明" : "Citation & Guidance"}</span>
          </header>
          <div className="kc-col-body">
            <section className="kc-sync-box">
              <div className="kc-sync-row"><small>{copy.syncAt}</small><strong>{syncTimeLabel}</strong></div>
              <div className="kc-sync-row"><small>{copy.syncStatus}</small><strong>{syncFileStatusLabel}</strong></div>
            </section>

            <article className="knowledge-preview-block">
              <strong>{copy.userGuideTitle}</strong>
              <p>{copy.citationHint}</p>
            </article>

            <article className="citation-query-card">
              <label className="field-wrap">
                <span>{copy.citationInputLabel}</span>
                <input value={citationQuery} placeholder={copy.citationPlaceholder} onChange={(event) => setCitationQuery(event.target.value)} />
              </label>
            </article>

            {citationLoading ? <article className="citation-empty-card"><p>{copy.loading}</p></article> : null}
            {!citationLoading && citationMatch ? (
              <article className="citation-match-card">
                <h4>{copy.citationSummaryTitle}</h4>
                <div className="citation-kv-grid">
                  <div className="citation-kv-row"><span>{copy.category}</span><strong>{rowText(citationMatch, "category")}</strong></div>
                  <div className="citation-kv-row"><span>{copy.usage}</span><strong>{rowText(citationMatch, "usage")}</strong></div>
                  <div className="citation-kv-row"><span>{copy.reportUsage}</span><strong>{rowText(citationMatch, "report_usage")}</strong></div>
                </div>
                <p className="citation-title">{rowText(citationMatch, "title")}</p>
                <p>{rowText(citationMatch, "summary")}</p>
              </article>
            ) : null}
            {!citationLoading && !citationMatch ? <article className="citation-empty-card"><p>{copy.matchEmpty}</p></article> : null}
          </div>
        </aside>
      </section>
    </section>
  );
}
