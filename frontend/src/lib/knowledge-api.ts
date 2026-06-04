const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const toStringRecord = (value: unknown): Record<string, string> => {
  if (!isRecord(value)) return {};

  const output: Record<string, string> = {};
  for (const [key, item] of Object.entries(value)) {
    if (typeof item === "string") {
      output[key] = item;
    }
  }
  return output;
};

const toStringList = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];

const toStringRecordList = (value: unknown): Record<string, string>[] =>
  Array.isArray(value) ? value.map(toStringRecord) : [];

const parseErrorMessage = (data: unknown): string => {
  if (!isRecord(data)) return "Request failed";
  if (typeof data.detail === "string") return data.detail;
  return "Request failed";
};

async function requestJson(url: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(url, { cache: "no-store", ...init });
  const data: unknown = await response.json();
  if (!response.ok) {
    throw new Error(parseErrorMessage(data));
  }
  return data;
}

export type KnowledgeSummary = {
  source_count: number;
  case_count: number;
};

export type KnowledgeSyncMeta = {
  synced_at: string;
  cache_refreshed: boolean;
  sources_csv_path: string;
  cases_csv_path: string;
  spec_asset_manifest_path: string;
  sources_csv_exists: boolean;
  cases_csv_exists: boolean;
  spec_asset_manifest_exists: boolean;
  sources_csv_mtime: string;
  cases_csv_mtime: string;
  spec_asset_manifest_mtime: string;
  manifest_total_files: number;
  manifest_frontend_visible_files: number;
  manifest_migrated_files: number;
};

export type KnowledgeSourceOptions = {
  categories: string[];
  jurisdictions: string[];
  usages: string[];
};

export type KnowledgeCaseOptions = {
  jurisdictions: string[];
  scenarios: string[];
};

export type KnowledgeIndexData = {
  summary: KnowledgeSummary;
  sync_meta: KnowledgeSyncMeta;
  source_options: KnowledgeSourceOptions;
  case_options: KnowledgeCaseOptions;
  sources: Record<string, string>[];
  cases: Record<string, string>[];
};

export type KnowledgeDetailData = {
  item: Record<string, string>;
  preview: string;
};

export type KnowledgeCitationData = {
  query: string;
  matched: Record<string, string> | null;
  preview: string;
};

const parseKnowledgeIndexData = (data: unknown): KnowledgeIndexData => {
  if (!isRecord(data)) {
    throw new Error("Invalid knowledge index payload");
  }

  const summaryRaw = isRecord(data.summary) ? data.summary : {};
  const syncMetaRaw = isRecord(data.sync_meta) ? data.sync_meta : {};
  const sourceOptionsRaw = isRecord(data.source_options) ? data.source_options : {};
  const caseOptionsRaw = isRecord(data.case_options) ? data.case_options : {};

  return {
    summary: {
      source_count: typeof summaryRaw.source_count === "number" ? summaryRaw.source_count : 0,
      case_count: typeof summaryRaw.case_count === "number" ? summaryRaw.case_count : 0,
    },
    sync_meta: {
      synced_at: typeof syncMetaRaw.synced_at === "string" ? syncMetaRaw.synced_at : "",
      cache_refreshed: syncMetaRaw.cache_refreshed === true,
      sources_csv_path: typeof syncMetaRaw.sources_csv_path === "string" ? syncMetaRaw.sources_csv_path : "",
      cases_csv_path: typeof syncMetaRaw.cases_csv_path === "string" ? syncMetaRaw.cases_csv_path : "",
      spec_asset_manifest_path: typeof syncMetaRaw.spec_asset_manifest_path === "string" ? syncMetaRaw.spec_asset_manifest_path : "",
      sources_csv_exists: syncMetaRaw.sources_csv_exists === true,
      cases_csv_exists: syncMetaRaw.cases_csv_exists === true,
      spec_asset_manifest_exists: syncMetaRaw.spec_asset_manifest_exists === true,
      sources_csv_mtime: typeof syncMetaRaw.sources_csv_mtime === "string" ? syncMetaRaw.sources_csv_mtime : "",
      cases_csv_mtime: typeof syncMetaRaw.cases_csv_mtime === "string" ? syncMetaRaw.cases_csv_mtime : "",
      spec_asset_manifest_mtime: typeof syncMetaRaw.spec_asset_manifest_mtime === "string" ? syncMetaRaw.spec_asset_manifest_mtime : "",
      manifest_total_files: typeof syncMetaRaw.manifest_total_files === "number" ? syncMetaRaw.manifest_total_files : 0,
      manifest_frontend_visible_files: typeof syncMetaRaw.manifest_frontend_visible_files === "number" ? syncMetaRaw.manifest_frontend_visible_files : 0,
      manifest_migrated_files: typeof syncMetaRaw.manifest_migrated_files === "number" ? syncMetaRaw.manifest_migrated_files : 0,
    },
    source_options: {
      categories: toStringList(sourceOptionsRaw.categories),
      jurisdictions: toStringList(sourceOptionsRaw.jurisdictions),
      usages: toStringList(sourceOptionsRaw.usages),
    },
    case_options: {
      jurisdictions: toStringList(caseOptionsRaw.jurisdictions),
      scenarios: toStringList(caseOptionsRaw.scenarios),
    },
    sources: toStringRecordList(data.sources),
    cases: toStringRecordList(data.cases)
  };
};

export async function fetchKnowledgeIndex(): Promise<KnowledgeIndexData> {
  const data = await requestJson("/api/v1/knowledge/index");
  return parseKnowledgeIndexData(data);
}

export async function syncKnowledgeIndex(): Promise<KnowledgeIndexData> {
  const data = await requestJson("/api/v1/knowledge/sync", { method: "POST" });
  return parseKnowledgeIndexData(data);
}

export async function fetchKnowledgeSourceDetail(sourceId: string): Promise<KnowledgeDetailData> {
  const data = await requestJson(`/api/v1/knowledge/sources/${encodeURIComponent(sourceId)}`);
  if (!isRecord(data)) {
    throw new Error("Invalid source detail payload");
  }
  return {
    item: toStringRecord(data.item),
    preview: typeof data.preview === "string" ? data.preview : ""
  };
}

export async function fetchKnowledgeCaseDetail(caseId: string): Promise<KnowledgeDetailData> {
  const data = await requestJson(`/api/v1/knowledge/cases/${encodeURIComponent(caseId)}`);
  if (!isRecord(data)) {
    throw new Error("Invalid case detail payload");
  }
  return {
    item: toStringRecord(data.item),
    preview: typeof data.preview === "string" ? data.preview : ""
  };
}

export type KnowledgeSearchItem = {
  id: string;
  title: string;
  article: string;
  content: string;
  jurisdiction: string;
  path: string;
  doc_type: string;
  source_url: string;
  keywords: string[];
};

export type KnowledgeSearchData = {
  query: string;
  jurisdiction: string | null;
  path: string | null;
  mode: string;
  top_k: number;
  hit_count: number;
  items: KnowledgeSearchItem[];
};

const parseSearchItem = (item: unknown): KnowledgeSearchItem => {
  const r = isRecord(item) ? item : {};
  return {
    id: typeof r.id === "string" ? r.id : "",
    title: typeof r.title === "string" ? r.title : "",
    article: typeof r.article === "string" ? r.article : "",
    content: typeof r.content === "string" ? r.content : "",
    jurisdiction: typeof r.jurisdiction === "string" ? r.jurisdiction : "",
    path: typeof r.path === "string" ? r.path : "",
    doc_type: typeof r.doc_type === "string" ? r.doc_type : "",
    source_url: typeof r.source_url === "string" ? r.source_url : "",
    keywords: toStringList(r.keywords),
  };
};

export async function fetchKnowledgeSearch(params: {
  q: string;
  jurisdiction?: string;
  path?: string;
  top_k?: number;
  mode?: string;
}): Promise<KnowledgeSearchData> {
  const searchParams = new URLSearchParams();
  searchParams.set("q", params.q);
  if (params.jurisdiction) searchParams.set("jurisdiction", params.jurisdiction);
  if (params.path) searchParams.set("path", params.path);
  if (params.top_k !== undefined) searchParams.set("top_k", String(params.top_k));
  if (params.mode) searchParams.set("mode", params.mode);

  const data = await requestJson(`/api/v1/knowledge/search?${searchParams.toString()}`);
  if (!isRecord(data)) throw new Error("Invalid search response");

  return {
    query: typeof data.query === "string" ? data.query : params.q,
    jurisdiction: typeof data.jurisdiction === "string" ? data.jurisdiction : null,
    path: typeof data.path === "string" ? data.path : null,
    mode: typeof data.mode === "string" ? data.mode : "hybrid",
    top_k: typeof data.top_k === "number" ? data.top_k : 8,
    hit_count: typeof data.hit_count === "number" ? data.hit_count : 0,
    items: Array.isArray(data.items) ? data.items.map(parseSearchItem) : [],
  };
}

export async function fetchKnowledgeCitation(query: string): Promise<KnowledgeCitationData> {
  const data = await requestJson(`/api/v1/knowledge/citation?query=${encodeURIComponent(query)}`);
  if (!isRecord(data)) {
    throw new Error("Invalid citation payload");
  }

  return {
    query: typeof data.query === "string" ? data.query : query,
    matched: isRecord(data.matched) ? toStringRecord(data.matched) : null,
    preview: typeof data.preview === "string" ? data.preview : ""
  };
}

export interface ArticleDetail {
  source_id: string;
  title: string;
  article_no: string;
  article_content: string;
  prev_article_no: string | null;
  prev_article_content: string;
  next_article_no: string | null;
  next_article_content: string;
  source_url: string;
  authority_level: string;
  binding_force: string;
  jurisdiction: string;
  doc_type: string;
}

export async function fetchArticleDetail(
  sourceId: string,
  articleNo: string,
): Promise<ArticleDetail> {
  const data = await requestJson(
    `/api/v1/knowledge/sources/${encodeURIComponent(sourceId)}/articles/${encodeURIComponent(articleNo)}`,
  );
  if (!isRecord(data)) {
    throw new Error("Invalid article detail payload");
  }
  return {
    source_id: typeof data.source_id === "string" ? data.source_id : "",
    title: typeof data.title === "string" ? data.title : "",
    article_no: typeof data.article_no === "string" ? data.article_no : "",
    article_content: typeof data.article_content === "string" ? data.article_content : "",
    prev_article_no: typeof data.prev_article_no === "string" ? data.prev_article_no : null,
    prev_article_content: typeof data.prev_article_content === "string" ? data.prev_article_content : "",
    next_article_no: typeof data.next_article_no === "string" ? data.next_article_no : null,
    next_article_content: typeof data.next_article_content === "string" ? data.next_article_content : "",
    source_url: typeof data.source_url === "string" ? data.source_url : "",
    authority_level: typeof data.authority_level === "string" ? data.authority_level : "medium",
    binding_force: typeof data.binding_force === "string" ? data.binding_force : "recommended",
    jurisdiction: typeof data.jurisdiction === "string" ? data.jurisdiction : "cn",
    doc_type: typeof data.doc_type === "string" ? data.doc_type : "law",
  };
}
