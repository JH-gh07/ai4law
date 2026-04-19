import { useEffect, useMemo, useState } from "react";

import { useLang } from "../lib/language";
import {
  fetchKnowledgeCaseDetail,
  fetchKnowledgeCitation,
  fetchKnowledgeIndex,
  fetchKnowledgeSearch,
  fetchKnowledgeSourceDetail,
  syncKnowledgeIndex,
  type KnowledgeSearchItem,
} from "../lib/knowledge-api";

type KnowledgeRow = Record<string, string>;
type KnowledgeTab = "sources" | "cases" | "citation" | "articles";

const splitModules = (value: string): string[] =>
  value
    .split("|")
    .map((item) => item.trim())
    .filter(Boolean);

const includesWithSelection = (value: string, selected: string[]) => selected.includes(value);

const toggleValue = (items: string[], value: string): string[] =>
  items.includes(value) ? items.filter((item) => item !== value) : [...items, value];

const rowText = (row: KnowledgeRow, key: string, fallback = "-"): string => row[key] || fallback;
const toFileName = (value: string): string => value.replace(/\\/g, "/").split("/").pop() || value;

export function EvidenceCenterPage() {
  const { lang } = useLang();

  const copy = lang === "zh"
    ? {
      title: "知识库中心",
      searchPlaceholder: "搜索标题、来源机构、路径…",
      searchNow: "搜索",
      sourceTab: "法规与指南",
      caseTab: "实践案例",
      citationTab: "引用联动演示",
      p0Only: "P0 条目",
      citationLinked: "已引用条目",
      sourceStat: "法规/指南条目",
      caseStat: "实践案例条目",
      p0Stat: "P0 法规条目",
      currentStat: "当前命中",
      sourceListTitle: "法规与指南索引",
      sourceDetailTitle: "条目详情",
      caseListTitle: "实践案例索引",
      caseDetailTitle: "案例详情",
      sourceFilterLayer: "按 layer 过滤",
      sourceFilterPath: "按 path 过滤",
      sourceFilterPriority: "按优先级过滤",
      caseFilterModule: "按模块过滤",
      caseFilterPriority: "按优先级过滤",
      selectAll: "全选",
      clearAll: "清空",
      openSource: "打开来源链接",
      openCase: "打开案例来源",
      snapshotPath: "快照路径",
      previewTitle: "本地快照文本预览",
      casePreviewTitle: "案例快照文本预览",
      citationInputLabel: "输入引用文本",
      citationPlaceholder: "例如：数据出境安全评估办法第4条",
      citationSummaryTitle: "结构化匹配详情",
      sourceId: "source_id",
      layer: "层级",
      path: "路径",
      noData: "暂无数据。",
      loading: "加载中…",
      matchEmpty: "未匹配到知识库条目。",
      optionsEmpty: "暂无可选项"
      ,
      syncNow: "同步后端知识库",
      syncing: "同步中…",
      syncAt: "最近同步",
      syncMode: "同步模式",
      syncSourceFile: "法规源文件",
      syncCaseFile: "案例源文件",
      syncStatus: "文件状态",
      syncReady: "已加载",
      syncMissing: "缺失",
      syncForced: "强制刷新缓存",
      syncNormal: "常规读取",
      articlesTab: "条文检索",
      articlesPlaceholder: "输入关键词检索法规条文，如：标准合同备案",
      articlesFilterJurisdiction: "法域",
      articlesFilterPath: "路径",
      articlesSearching: "检索中…",
      articlesEmpty: "未检索到相关条文。",
      articlesHitCount: "命中条文",
      articlesDetailTitle: "条文详情",
      articlesContentLabel: "条文内容",
      articlesSourceLink: "查看来源",
    }
    : {
      title: "Knowledge Center",
      searchPlaceholder: "Search title, source org, path...",
      searchNow: "Search",
      sourceTab: "Regulations & Guidance",
      caseTab: "Practice Cases",
      citationTab: "Citation Linkage Demo",
      p0Only: "P0 Items",
      citationLinked: "Cited Items",
      sourceStat: "Regulation/Guide Items",
      caseStat: "Practice Case Items",
      p0Stat: "P0 Regulation Items",
      currentStat: "Matched Items",
      sourceListTitle: "Regulations & Guidance Index",
      sourceDetailTitle: "Entry Detail",
      caseListTitle: "Practice Case Index",
      caseDetailTitle: "Case Detail",
      sourceFilterLayer: "Filter by layer",
      sourceFilterPath: "Filter by path",
      sourceFilterPriority: "Filter by priority",
      caseFilterModule: "Filter by module",
      caseFilterPriority: "Filter by priority",
      selectAll: "Select All",
      clearAll: "Clear",
      openSource: "Open Source Link",
      openCase: "Open Case Source",
      snapshotPath: "Snapshot Path",
      previewTitle: "Local Snapshot Preview",
      casePreviewTitle: "Case Snapshot Preview",
      citationInputLabel: "Enter citation text",
      citationPlaceholder: "e.g. Data Export Security Assessment Measures Article 4",
      citationSummaryTitle: "Structured Match Detail",
      sourceId: "source_id",
      layer: "Layer",
      path: "Path",
      noData: "No data.",
      loading: "Loading...",
      matchEmpty: "No knowledge entry matched.",
      optionsEmpty: "No options"
      ,
      syncNow: "Sync Backend Knowledge",
      syncing: "Syncing...",
      syncAt: "Last Synced",
      syncMode: "Sync Mode",
      syncSourceFile: "Source File",
      syncCaseFile: "Case File",
      syncStatus: "File Status",
      syncReady: "Loaded",
      syncMissing: "Missing",
      syncForced: "Forced Cache Refresh",
      syncNormal: "Normal Read",
      articlesTab: "Article Search",
      articlesPlaceholder: "Search regulation articles, e.g. standard contract filing",
      articlesFilterJurisdiction: "Jurisdiction",
      articlesFilterPath: "Path",
      articlesSearching: "Searching...",
      articlesEmpty: "No articles found.",
      articlesHitCount: "Articles Found",
      articlesDetailTitle: "Article Detail",
      articlesContentLabel: "Content",
      articlesSourceLink: "View Source",
    };

  const [tab, setTab] = useState<KnowledgeTab>("sources");
  const [keyword, setKeyword] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [sources, setSources] = useState<KnowledgeRow[]>([]);
  const [cases, setCases] = useState<KnowledgeRow[]>([]);
  const [sourceLayerOptions, setSourceLayerOptions] = useState<string[]>([]);
  const [sourcePathOptions, setSourcePathOptions] = useState<string[]>([]);
  const [sourcePriorityOptions, setSourcePriorityOptions] = useState<string[]>([]);
  const [caseModuleOptions, setCaseModuleOptions] = useState<string[]>([]);
  const [casePriorityOptions, setCasePriorityOptions] = useState<string[]>([]);
  const [summary, setSummary] = useState({ source_count: 0, case_count: 0, p0_source_count: 0 });
  const [syncMeta, setSyncMeta] = useState({
    synced_at: "",
    cache_refreshed: false,
    sources_csv_path: "",
    cases_csv_path: "",
    sources_csv_exists: false,
    cases_csv_exists: false,
    sources_csv_mtime: "",
    cases_csv_mtime: ""
  });
  const [syncing, setSyncing] = useState(false);

  const [selectedLayers, setSelectedLayers] = useState<string[]>([]);
  const [selectedPaths, setSelectedPaths] = useState<string[]>([]);
  const [selectedSourcePriority, setSelectedSourcePriority] = useState<string[]>([]);
  const [selectedModules, setSelectedModules] = useState<string[]>([]);
  const [selectedCasePriority, setSelectedCasePriority] = useState<string[]>([]);

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

  const applyKnowledgeIndexData = (
    data: Awaited<ReturnType<typeof fetchKnowledgeIndex>>
  ): void => {
    setSources(data.sources);
    setCases(data.cases);
    setSummary(data.summary);
    setSyncMeta(data.sync_meta);

    setSourceLayerOptions(data.source_options.layers);
    setSourcePathOptions(data.source_options.paths);
    setSourcePriorityOptions(data.source_options.priorities);
    setCaseModuleOptions(data.case_options.modules);
    setCasePriorityOptions(data.case_options.priorities);

    setSelectedLayers(data.source_options.layers);
    setSelectedPaths(data.source_options.paths);
    setSelectedSourcePriority(data.source_options.priorities);
    setSelectedModules(data.case_options.modules);
    setSelectedCasePriority(data.case_options.priorities);
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

  const filteredSources = useMemo(() => {
    const token = keyword.trim().toLowerCase();
    return sources
      .filter((item) => includesWithSelection(rowText(item, "layer", ""), selectedLayers))
      .filter((item) => includesWithSelection(rowText(item, "path", ""), selectedPaths))
      .filter((item) => includesWithSelection(rowText(item, "usage_priority", ""), selectedSourcePriority))
      .filter((item) => {
        if (!token) return true;
        return `${rowText(item, "title")} ${rowText(item, "source_org")} ${rowText(item, "path")}`
          .toLowerCase()
          .includes(token);
      });
  }, [keyword, selectedLayers, selectedPaths, selectedSourcePriority, sources]);

  const filteredCases = useMemo(() => {
    const token = keyword.trim().toLowerCase();
    return cases
      .filter((item) => {
        const modules = splitModules(rowText(item, "expected_module", ""));
        return modules.some((module) => selectedModules.includes(module));
      })
      .filter((item) => includesWithSelection(rowText(item, "priority", ""), selectedCasePriority))
      .filter((item) => {
        if (!token) return true;
        return `${rowText(item, "case_title")} ${rowText(item, "source_org")} ${rowText(item, "case_type")}`
          .toLowerCase()
          .includes(token);
      });
  }, [cases, keyword, selectedCasePriority, selectedModules]);

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
  const syncFileStatusLabel = `${syncMeta.sources_csv_exists ? copy.syncReady : copy.syncMissing} / ${syncMeta.cases_csv_exists ? copy.syncReady : copy.syncMissing}`;

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
            <div className="k">{copy.p0Stat}</div>
            <div className="v">{summary.p0_source_count}</div>
          </article>
          <article className="kc-status-item">
            <div className="k">{copy.currentStat}</div>
            <div className="v">{currentMatches}</div>
          </article>
          <article className="kc-status-item">
            <div className="k">{copy.syncAt}</div>
            <div className="v">{syncTimeLabel}</div>
          </article>
        </div>
      </section>

      <section className="kc-main-grid">
        <aside className="kc-col">
          <header className="kc-col-head">
            <span>{tab === "sources" ? copy.sourceListTitle : tab === "cases" ? copy.caseListTitle : tab === "articles" ? copy.articlesTab : copy.citationTab}</span>
            <small>{copy.currentStat}: {currentMatches}</small>
          </header>
          <div className="kc-col-body">
            {tab === "sources" ? (
              <>
                <div className="knowledge-filter-grid">
                  <div className="knowledge-filter-group">
                    <small>{copy.sourceFilterLayer}</small>
                    <div className="knowledge-chip-row">
                      {sourceLayerOptions.map((option) => (
                        <button key={option} className={`chip-btn ${selectedLayers.includes(option) ? "active" : ""}`} onClick={() => setSelectedLayers((prev) => toggleValue(prev, option))}>
                          {option}
                        </button>
                      ))}
                      {sourceLayerOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
                    </div>
                    <div className="knowledge-filter-actions">
                      <button className="ghost-btn" onClick={() => setSelectedLayers(sourceLayerOptions)}>{copy.selectAll}</button>
                      <button className="ghost-btn" onClick={() => setSelectedLayers([])}>{copy.clearAll}</button>
                    </div>
                  </div>
                  <div className="knowledge-filter-group">
                    <small>{copy.sourceFilterPath}</small>
                    <div className="knowledge-chip-row">
                      {sourcePathOptions.map((option) => (
                        <button key={option} className={`chip-btn ${selectedPaths.includes(option) ? "active" : ""}`} onClick={() => setSelectedPaths((prev) => toggleValue(prev, option))}>
                          {option}
                        </button>
                      ))}
                      {sourcePathOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
                    </div>
                    <div className="knowledge-filter-actions">
                      <button className="ghost-btn" onClick={() => setSelectedPaths(sourcePathOptions)}>{copy.selectAll}</button>
                      <button className="ghost-btn" onClick={() => setSelectedPaths([])}>{copy.clearAll}</button>
                    </div>
                  </div>
                  <div className="knowledge-filter-group">
                    <small>{copy.sourceFilterPriority}</small>
                    <div className="knowledge-chip-row">
                      {sourcePriorityOptions.map((option) => (
                        <button key={option} className={`chip-btn ${selectedSourcePriority.includes(option) ? "active" : ""}`} onClick={() => setSelectedSourcePriority((prev) => toggleValue(prev, option))}>
                          {option}
                        </button>
                      ))}
                      {sourcePriorityOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
                    </div>
                    <div className="knowledge-filter-actions">
                      <button className="ghost-btn" onClick={() => setSelectedSourcePriority(sourcePriorityOptions)}>{copy.selectAll}</button>
                      <button className="ghost-btn" onClick={() => setSelectedSourcePriority([])}>{copy.clearAll}</button>
                    </div>
                  </div>
                </div>
                <div className="evidence-hit-scroll kc-list-scroll">
                  {filteredSources.map((row) => {
                    const sourceId = rowText(row, "source_id");
                    return (
                      <article key={sourceId} className={`evidence-hit-item ${selectedSource?.source_id === sourceId ? "active" : ""}`} onClick={() => setSelectedSourceId(sourceId)}>
                        <small>{rowText(row, "layer")} · {rowText(row, "path")}</small>
                        <strong>{rowText(row, "title")}</strong>
                        <p>{rowText(row, "source_org")}</p>
                      </article>
                    );
                  })}
                  {filteredSources.length === 0 ? <p className="resource-empty">{copy.noData}</p> : null}
                </div>
              </>
            ) : null}

            {tab === "cases" ? (
              <>
                <div className="knowledge-filter-grid">
                  <div className="knowledge-filter-group">
                    <small>{copy.caseFilterModule}</small>
                    <div className="knowledge-chip-row">
                      {caseModuleOptions.map((option) => (
                        <button key={option} className={`chip-btn ${selectedModules.includes(option) ? "active" : ""}`} onClick={() => setSelectedModules((prev) => toggleValue(prev, option))}>
                          {option}
                        </button>
                      ))}
                      {caseModuleOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
                    </div>
                    <div className="knowledge-filter-actions">
                      <button className="ghost-btn" onClick={() => setSelectedModules(caseModuleOptions)}>{copy.selectAll}</button>
                      <button className="ghost-btn" onClick={() => setSelectedModules([])}>{copy.clearAll}</button>
                    </div>
                  </div>
                  <div className="knowledge-filter-group">
                    <small>{copy.caseFilterPriority}</small>
                    <div className="knowledge-chip-row">
                      {casePriorityOptions.map((option) => (
                        <button key={option} className={`chip-btn ${selectedCasePriority.includes(option) ? "active" : ""}`} onClick={() => setSelectedCasePriority((prev) => toggleValue(prev, option))}>
                          {option}
                        </button>
                      ))}
                      {casePriorityOptions.length === 0 ? <span className="chip-empty">{copy.optionsEmpty}</span> : null}
                    </div>
                    <div className="knowledge-filter-actions">
                      <button className="ghost-btn" onClick={() => setSelectedCasePriority(casePriorityOptions)}>{copy.selectAll}</button>
                      <button className="ghost-btn" onClick={() => setSelectedCasePriority([])}>{copy.clearAll}</button>
                    </div>
                  </div>
                </div>
                <div className="evidence-hit-scroll kc-list-scroll">
                  {filteredCases.map((row) => {
                    const caseId = rowText(row, "case_id");
                    return (
                      <article key={caseId} className={`evidence-hit-item ${selectedCase?.case_id === caseId ? "active" : ""}`} onClick={() => setSelectedCaseId(caseId)}>
                        <small>{rowText(row, "case_type")} · {rowText(row, "priority")}</small>
                        <strong>{rowText(row, "case_title")}</strong>
                        <p>{rowText(row, "expected_module")}</p>
                      </article>
                    );
                  })}
                  {filteredCases.length === 0 ? <p className="resource-empty">{copy.noData}</p> : null}
                </div>
              </>
            ) : null}

            {tab === "articles" ? (
              <>
                <div className="knowledge-filter-grid">
                  <div className="knowledge-filter-group">
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
                  <div className="knowledge-filter-group">
                    <small>{copy.articlesFilterPath}</small>
                    <div className="knowledge-chip-row">
                      {["assessment", "scc", "all"].map((p) => (
                        <button
                          key={p}
                          className={`chip-btn ${articlesPath === p ? "active" : ""}`}
                          onClick={() => setArticlesPath((prev) => prev === p ? "" : p)}
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>
                  <label className="field-wrap" style={{ marginTop: "0.5rem" }}>
                    <input
                      placeholder={copy.articlesPlaceholder}
                      value={articlesQuery}
                      onChange={(e) => setArticlesQuery(e.target.value)}
                    />
                  </label>
                </div>
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
                      <small>{item.jurisdiction.toUpperCase()} · {item.usage_priority}</small>
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
                      <div className="citation-kv-row"><span>{copy.sourceId}</span><strong>{rowText(citationMatch, "source_id")}</strong></div>
                      <div className="citation-kv-row"><span>{copy.layer}</span><strong>{rowText(citationMatch, "layer")}</strong></div>
                      <div className="citation-kv-row"><span>{copy.path}</span><strong>{rowText(citationMatch, "path")}</strong></div>
                    </div>
                    <p className="citation-title">{rowText(citationMatch, "title")}</p>
                    <small>{copy.snapshotPath}: <code>{rowText(citationMatch, "snapshot_path", "-")}</code></small>
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
                    <span>{selectedArticle.path}</span>
                    <span>{selectedArticle.usage_priority}</span>
                    {selectedArticle.doc_type ? <span>{selectedArticle.doc_type}</span> : null}
                  </div>
                  <h4>{selectedArticle.title}</h4>
                  <p style={{ fontWeight: 600, marginBottom: "0.25rem" }}>{selectedArticle.article}</p>
                  <div className="knowledge-preview-block">
                    <strong>{copy.articlesContentLabel}</strong>
                    <p style={{ whiteSpace: "pre-wrap" }}>{selectedArticle.content}</p>
                  </div>
                  {selectedArticle.source_url ? (
                    <a className="ghost-btn link-btn" href={selectedArticle.source_url} target="_blank" rel="noreferrer">
                      {copy.articlesSourceLink}
                    </a>
                  ) : null}
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
                    <span>{rowText(selectedSource, "source_id")}</span>
                    <span>{rowText(selectedSource, "layer")}</span>
                    <span>{rowText(selectedSource, "path")}</span>
                    <span>{rowText(selectedSource, "usage_priority")}</span>
                  </div>
                  <h4>{rowText(selectedSource, "title")}</h4>
                  <p>{rowText(selectedSource, "notes", "-")}</p>
                  {selectedSource.url ? <a className="ghost-btn link-btn" href={selectedSource.url} target="_blank" rel="noreferrer">{copy.openSource}</a> : null}
                  <small>{copy.snapshotPath}: <code>{rowText(selectedSource, "snapshot_path", "-")}</code></small>
                  {sourcePreview ? <div className="knowledge-preview-block"><strong>{copy.previewTitle}</strong><p>{sourcePreview}</p></div> : null}
                </article>
              ) : <p className="resource-empty">{copy.noData}</p>
            ) : null}

            {!loading && tab === "cases" ? (
              selectedCase ? (
                <article className="evidence-detail-card">
                  <div className="evidence-detail-meta">
                    <span>{rowText(selectedCase, "case_id")}</span>
                    <span>{rowText(selectedCase, "priority")}</span>
                    <span>{rowText(selectedCase, "jurisdiction")}</span>
                  </div>
                  <h4>{rowText(selectedCase, "case_title")}</h4>
                  <p>{rowText(selectedCase, "limitations", "-")}</p>
                  <p>{rowText(selectedCase, "available_artifacts", "-")}</p>
                  {selectedCase.url ? <a className="ghost-btn link-btn" href={selectedCase.url} target="_blank" rel="noreferrer">{copy.openCase}</a> : null}
                  <small>{copy.snapshotPath}: <code>{rowText(selectedCase, "snapshot_path", "-")}</code></small>
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
            <span>{lang === "zh" ? "联动与状态" : "Linkage & Status"}</span>
          </header>
          <div className="kc-col-body">
            <section className="kc-sync-box">
              <div className="kc-sync-row"><small>{copy.syncAt}</small><strong>{syncTimeLabel}</strong></div>
              <div className="kc-sync-row"><small>{copy.syncMode}</small><strong>{syncMeta.cache_refreshed ? copy.syncForced : copy.syncNormal}</strong></div>
              <div className="kc-sync-row"><small>{copy.syncSourceFile}</small><strong>{syncMeta.sources_csv_path ? toFileName(syncMeta.sources_csv_path) : "-"}</strong></div>
              <div className="kc-sync-row"><small>{copy.syncCaseFile}</small><strong>{syncMeta.cases_csv_path ? toFileName(syncMeta.cases_csv_path) : "-"}</strong></div>
              <div className="kc-sync-row"><small>{copy.syncStatus}</small><strong>{syncFileStatusLabel}</strong></div>
            </section>

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
                  <div className="citation-kv-row"><span>{copy.sourceId}</span><strong>{rowText(citationMatch, "source_id")}</strong></div>
                  <div className="citation-kv-row"><span>{copy.layer}</span><strong>{rowText(citationMatch, "layer")}</strong></div>
                  <div className="citation-kv-row"><span>{copy.path}</span><strong>{rowText(citationMatch, "path")}</strong></div>
                </div>
                <p className="citation-title">{rowText(citationMatch, "title")}</p>
                <small>{copy.snapshotPath}: <code>{rowText(citationMatch, "snapshot_path", "-")}</code></small>
              </article>
            ) : null}
            {!citationLoading && !citationMatch ? <article className="citation-empty-card"><p>{copy.matchEmpty}</p></article> : null}
          </div>
        </aside>
      </section>
    </section>
  );
}
