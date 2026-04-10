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

async function requestJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  const data: unknown = await response.json();
  if (!response.ok) {
    throw new Error(parseErrorMessage(data));
  }
  return data;
}

export type KnowledgeSummary = {
  source_count: number;
  case_count: number;
  p0_source_count: number;
};

export type KnowledgeSourceOptions = {
  layers: string[];
  paths: string[];
  priorities: string[];
};

export type KnowledgeCaseOptions = {
  modules: string[];
  priorities: string[];
};

export type KnowledgeIndexData = {
  summary: KnowledgeSummary;
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

export async function fetchKnowledgeIndex(): Promise<KnowledgeIndexData> {
  const data = await requestJson("/api/v1/knowledge/index");
  if (!isRecord(data)) {
    throw new Error("Invalid knowledge index payload");
  }

  const summaryRaw = isRecord(data.summary) ? data.summary : {};
  const sourceOptionsRaw = isRecord(data.source_options) ? data.source_options : {};
  const caseOptionsRaw = isRecord(data.case_options) ? data.case_options : {};

  return {
    summary: {
      source_count: typeof summaryRaw.source_count === "number" ? summaryRaw.source_count : 0,
      case_count: typeof summaryRaw.case_count === "number" ? summaryRaw.case_count : 0,
      p0_source_count: typeof summaryRaw.p0_source_count === "number" ? summaryRaw.p0_source_count : 0
    },
    source_options: {
      layers: toStringList(sourceOptionsRaw.layers),
      paths: toStringList(sourceOptionsRaw.paths),
      priorities: toStringList(sourceOptionsRaw.priorities)
    },
    case_options: {
      modules: toStringList(caseOptionsRaw.modules),
      priorities: toStringList(caseOptionsRaw.priorities)
    },
    sources: toStringRecordList(data.sources),
    cases: toStringRecordList(data.cases)
  };
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
