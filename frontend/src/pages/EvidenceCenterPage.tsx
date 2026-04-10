import { useEffect, useMemo, useState } from "react";

import { useLang } from "../lib/language";
import {
  fetchKnowledgeCaseDetail,
  fetchKnowledgeCitation,
  fetchKnowledgeIndex,
  fetchKnowledgeSourceDetail
} from "../lib/knowledge-api";

type KnowledgeRow = Record<string, string>;
type KnowledgeTab = "sources" | "cases" | "citation";

const splitModules = (value: string): string[] =>
  value
    .split("|")
    .map((item) => item.trim())
    .filter(Boolean);

const includesWithSelection = (value: string, selected: string[]) => selected.includes(value);

const toggleValue = (items: string[], value: string): string[] =>
  items.includes(value) ? items.filter((item) => item !== value) : [...items, value];

const rowText = (row: KnowledgeRow, key: string, fallback = "-"): string => row[key] || fallback;

export function EvidenceCenterPage() {
  const { lang } = useLang();

  const copy = lang === "zh"
    ? {
      title: "知识库中心",
      searchPlaceholder: "搜索标题、来源机构、路径…",
      sourceTab: "法规与指南",
      caseTab: "实践案例",
      citationTab: "引用联动演示",
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
    }
    : {
      title: "Knowledge Center",
      searchPlaceholder: "Search title, source org, path...",
      sourceTab: "Regulations & Guidance",
      caseTab: "Practice Cases",
      citationTab: "Citation Linkage Demo",
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

  useEffect(() => {
    let isActive = true;

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const data = await fetchKnowledgeIndex();
        if (!isActive) return;

        setSources(data.sources);
        setCases(data.cases);
        setSummary(data.summary);

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

  const currentMatches = tab === "sources" ? filteredSources.length : tab === "cases" ? filteredCases.length : citationMatch ? 1 : 0;

  return (
    <section className="page-shell evidence-page">
      <div className="page-header evidence-header">
        <h2>{copy.title}</h2>
        <input
          className="resource-search"
          placeholder={copy.searchPlaceholder}
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
      </div>

      <section className="evidence-metrics">
        <article className="evidence-metric-card">
          <span>{copy.sourceStat}</span>
          <strong>{summary.source_count}</strong>
        </article>
        <article className="evidence-metric-card">
          <span>{copy.caseStat}</span>
          <strong>{summary.case_count}</strong>
        </article>
        <article className="evidence-metric-card">
          <span>{copy.p0Stat}</span>
          <strong>{summary.p0_source_count}</strong>
        </article>
        <article className="evidence-metric-card">
          <span>{copy.currentStat}</span>
          <strong>{currentMatches}</strong>
        </article>
      </section>

      <section className="evidence-tabbar">
        <button className={`tab-btn ${tab === "sources" ? "active" : ""}`} onClick={() => setTab("sources")}>
          {copy.sourceTab}
        </button>
        <button className={`tab-btn ${tab === "cases" ? "active" : ""}`} onClick={() => setTab("cases")}>
          {copy.caseTab}
        </button>
        <button className={`tab-btn ${tab === "citation" ? "active" : ""}`} onClick={() => setTab("citation")}>
          {copy.citationTab}
        </button>
      </section>

      <div className="evidence-panel">
        {error ? <p className="resource-empty">{error}</p> : null}
        {loading ? <p className="resource-empty">{copy.loading}</p> : null}

        {!loading && tab === "sources" ? (
          <div className="evidence-hits-layout">
            <aside className="evidence-hit-list">
              <h3>{copy.sourceListTitle}</h3>
              <div className="knowledge-filter-grid">
                <div className="knowledge-filter-group">
                  <small>{copy.sourceFilterLayer}</small>
                  <div className="knowledge-chip-row">
                    {sourceLayerOptions.map((option) => (
                      <button
                        key={option}
                        className={`chip-btn ${selectedLayers.includes(option) ? "active" : ""}`}
                        onClick={() => setSelectedLayers((prev) => toggleValue(prev, option))}
                      >
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
                      <button
                        key={option}
                        className={`chip-btn ${selectedPaths.includes(option) ? "active" : ""}`}
                        onClick={() => setSelectedPaths((prev) => toggleValue(prev, option))}
                      >
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
                      <button
                        key={option}
                        className={`chip-btn ${selectedSourcePriority.includes(option) ? "active" : ""}`}
                        onClick={() => setSelectedSourcePriority((prev) => toggleValue(prev, option))}
                      >
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

              <div className="evidence-hit-scroll">
                {filteredSources.map((row) => {
                  const sourceId = rowText(row, "source_id");
                  return (
                    <article
                      key={sourceId}
                      className={`evidence-hit-item ${selectedSource?.source_id === sourceId ? "active" : ""}`}
                      onClick={() => setSelectedSourceId(sourceId)}
                    >
                      <small>{rowText(row, "layer")} · {rowText(row, "path")}</small>
                      <strong>{rowText(row, "title")}</strong>
                      <p>{rowText(row, "source_org")}</p>
                    </article>
                  );
                })}
                {filteredSources.length === 0 ? <p className="resource-empty">{copy.noData}</p> : null}
              </div>
            </aside>

            <main className="evidence-hit-detail">
              <h3>{copy.sourceDetailTitle}</h3>
              {selectedSource ? (
                <article className="evidence-detail-card">
                  <div className="evidence-detail-meta">
                    <span>{rowText(selectedSource, "source_id")}</span>
                    <span>{rowText(selectedSource, "layer")}</span>
                    <span>{rowText(selectedSource, "path")}</span>
                    <span>{rowText(selectedSource, "usage_priority")}</span>
                  </div>
                  <h4>{rowText(selectedSource, "title")}</h4>
                  <p>{rowText(selectedSource, "notes", "-")}</p>
                  {selectedSource.url ? (
                    <a className="ghost-btn link-btn" href={selectedSource.url} target="_blank" rel="noreferrer">
                      {copy.openSource}
                    </a>
                  ) : null}
                  <small>{copy.snapshotPath}: <code>{rowText(selectedSource, "snapshot_path", "-")}</code></small>
                  {sourcePreview ? (
                    <div className="knowledge-preview-block">
                      <strong>{copy.previewTitle}</strong>
                      <p>{sourcePreview}</p>
                    </div>
                  ) : null}
                </article>
              ) : (
                <p className="resource-empty">{copy.noData}</p>
              )}
            </main>
          </div>
        ) : null}

        {!loading && tab === "cases" ? (
          <div className="evidence-hits-layout">
            <aside className="evidence-hit-list">
              <h3>{copy.caseListTitle}</h3>
              <div className="knowledge-filter-grid">
                <div className="knowledge-filter-group">
                  <small>{copy.caseFilterModule}</small>
                  <div className="knowledge-chip-row">
                    {caseModuleOptions.map((option) => (
                      <button
                        key={option}
                        className={`chip-btn ${selectedModules.includes(option) ? "active" : ""}`}
                        onClick={() => setSelectedModules((prev) => toggleValue(prev, option))}
                      >
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
                      <button
                        key={option}
                        className={`chip-btn ${selectedCasePriority.includes(option) ? "active" : ""}`}
                        onClick={() => setSelectedCasePriority((prev) => toggleValue(prev, option))}
                      >
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

              <div className="evidence-hit-scroll">
                {filteredCases.map((row) => {
                  const caseId = rowText(row, "case_id");
                  return (
                    <article
                      key={caseId}
                      className={`evidence-hit-item ${selectedCase?.case_id === caseId ? "active" : ""}`}
                      onClick={() => setSelectedCaseId(caseId)}
                    >
                      <small>{rowText(row, "case_type")} · {rowText(row, "priority")}</small>
                      <strong>{rowText(row, "case_title")}</strong>
                      <p>{rowText(row, "expected_module")}</p>
                    </article>
                  );
                })}
                {filteredCases.length === 0 ? <p className="resource-empty">{copy.noData}</p> : null}
              </div>
            </aside>

            <main className="evidence-hit-detail">
              <h3>{copy.caseDetailTitle}</h3>
              {selectedCase ? (
                <article className="evidence-detail-card">
                  <div className="evidence-detail-meta">
                    <span>{rowText(selectedCase, "case_id")}</span>
                    <span>{rowText(selectedCase, "priority")}</span>
                    <span>{rowText(selectedCase, "jurisdiction")}</span>
                  </div>
                  <h4>{rowText(selectedCase, "case_title")}</h4>
                  <p>{rowText(selectedCase, "limitations", "-")}</p>
                  <p>{rowText(selectedCase, "available_artifacts", "-")}</p>
                  {selectedCase.url ? (
                    <a className="ghost-btn link-btn" href={selectedCase.url} target="_blank" rel="noreferrer">
                      {copy.openCase}
                    </a>
                  ) : null}
                  <small>{copy.snapshotPath}: <code>{rowText(selectedCase, "snapshot_path", "-")}</code></small>
                  {casePreview ? (
                    <div className="knowledge-preview-block">
                      <strong>{copy.casePreviewTitle}</strong>
                      <p>{casePreview}</p>
                    </div>
                  ) : null}
                </article>
              ) : (
                <p className="resource-empty">{copy.noData}</p>
              )}
            </main>
          </div>
        ) : null}

        {!loading && tab === "citation" ? (
          <div className="evidence-citation-panel">
            <article className="citation-query-card">
              <label className="field-wrap">
                <span>{copy.citationInputLabel}</span>
                <input
                  value={citationQuery}
                  placeholder={copy.citationPlaceholder}
                  onChange={(event) => setCitationQuery(event.target.value)}
                />
              </label>
            </article>

            <div className="citation-result-grid">
              {citationLoading ? (
                <article className="citation-empty-card">
                  <p>{copy.loading}</p>
                </article>
              ) : null}

              {!citationLoading && citationMatch ? (
                <article className="citation-match-card">
                  <h4>{copy.citationSummaryTitle}</h4>
                  <div className="citation-kv-grid">
                    <div className="citation-kv-row">
                      <span>{copy.sourceId}</span>
                      <strong>{rowText(citationMatch, "source_id")}</strong>
                    </div>
                    <div className="citation-kv-row">
                      <span>{copy.layer}</span>
                      <strong>{rowText(citationMatch, "layer")}</strong>
                    </div>
                    <div className="citation-kv-row">
                      <span>{copy.path}</span>
                      <strong>{rowText(citationMatch, "path")}</strong>
                    </div>
                  </div>
                  <p className="citation-title">{rowText(citationMatch, "title")}</p>
                  <small>{copy.snapshotPath}: <code>{rowText(citationMatch, "snapshot_path", "-")}</code></small>
                </article>
              ) : null}

              {!citationLoading && !citationMatch ? (
                <article className="citation-empty-card">
                  <p>{copy.matchEmpty}</p>
                </article>
              ) : null}

              {!citationLoading && citationPreview ? (
                <article className="citation-preview-card">
                  <strong>{copy.previewTitle}</strong>
                  <p>{citationPreview}</p>
                </article>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
