import type { ConsistencyIssue, EvidenceHit, ModuleKey, OutputArtifact } from "./domain";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const readString = (value: unknown): string | undefined => (typeof value === "string" ? value : undefined);

export type ResponseInsight = {
  reportPath?: string;
  outputFiles: Record<string, string>;
  riskLevel?: string;
  recommendedPath?: string;
  consistencyIssues: string[];
};

export function extractInsight(response: unknown): ResponseInsight {
  if (!isRecord(response)) {
    return { outputFiles: {}, consistencyIssues: [] };
  }

  const resultRecord = isRecord(response.result) ? response.result : {};

  const outputFiles: Record<string, string> = {};
  if (isRecord(response.output_files)) {
    for (const [key, value] of Object.entries(response.output_files)) {
      if (typeof value === "string") {
        outputFiles[key] = value;
      }
    }
  }

  const consistencyIssuesRaw = response.consistency_issues;
  const consistencyIssues = Array.isArray(consistencyIssuesRaw)
    ? consistencyIssuesRaw.filter((item): item is string => typeof item === "string")
    : [];

  return {
    reportPath: readString(response.report_path),
    outputFiles,
    riskLevel: readString(response.risk_level) ?? readString(resultRecord.risk_level),
    recommendedPath: readString(response.recommended_path),
    consistencyIssues
  };
}

export function extractArtifacts(taskSpaceId: string, module: ModuleKey, response: unknown): OutputArtifact[] {
  const insight = extractInsight(response);
  const now = new Date().toISOString();
  const entries: OutputArtifact[] = [];
  const seenPaths = new Set<string>();

  const appendArtifact = (kind: string, path: string | undefined) => {
    const normalizedPath = path?.trim();
    if (!normalizedPath || seenPaths.has(normalizedPath)) {
      return;
    }
    seenPaths.add(normalizedPath);
    entries.push({
      id: `${module}-${kind}-${now}`,
      taskSpaceId,
      module,
      kind,
      path: normalizedPath,
      createdAt: now
    });
  };

  appendArtifact("report", insight.reportPath);

  for (const [kind, path] of Object.entries(insight.outputFiles)) {
    appendArtifact(kind, path);
  }

  return entries;
}

export function extractConsistencyIssues(
  taskSpaceId: string,
  module: ModuleKey,
  response: unknown
): ConsistencyIssue[] {
  const insight = extractInsight(response);
  const now = new Date().toISOString();
  return insight.consistencyIssues.map((message, idx) => ({
    id: `${module}-issue-${idx}-${now}`,
    taskSpaceId,
    module,
    severity: message.toLowerCase().includes("high") ? "high" : "medium",
    message,
    createdAt: now
  }));
}

export function extractEvidenceHits(taskSpaceId: string, module: ModuleKey, response: unknown): EvidenceHit[] {
  if (!isRecord(response)) {
    return [];
  }

  const now = new Date().toISOString();
  const hits: EvidenceHit[] = [];

  if (Array.isArray(response.regulations)) {
    for (const regulation of response.regulations) {
      if (!isRecord(regulation)) continue;
      const title = readString(regulation.title) ?? "Regulation";
      const article = readString(regulation.article) ?? "";
      const snippet = readString(regulation.snippet) ?? "";
      hits.push({
        id: `${module}-reg-${title}-${article}-${now}`,
        taskSpaceId,
        module,
        source: "regulation",
        title: `${title}${article}`,
        snippet,
        createdAt: now
      });
    }
  }

  if (Array.isArray(response.chapters)) {
    for (const chapter of response.chapters) {
      if (!isRecord(chapter)) continue;
      const chapterTitle = readString(chapter.title) ?? "chapter";
      const citations = Array.isArray(chapter.citations)
        ? chapter.citations.filter((item): item is string => typeof item === "string")
        : [];
      for (const citation of citations) {
        hits.push({
          id: `${module}-citation-${chapterTitle}-${citation}-${now}`,
          taskSpaceId,
          module,
          source: "citation",
          title: citation,
          snippet: chapterTitle,
          createdAt: now
        });
      }
    }
  }

  return hits;
}
