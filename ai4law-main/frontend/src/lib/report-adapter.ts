import type {
  ConsistencyIssue,
  EvidenceHit,
  ModuleRun,
  OutputArtifact,
  ReportReviewSnapshot,
  TaskSpace,
  TraceLink
} from "./domain";
import { extractInsight } from "./workspace";

type RemoteReportMetadata = {
  risk_level?: string;
  version?: string;
  summary?: string;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const safeLower = (value: string) => value.toLowerCase();

const createVersion = (date: string) => {
  const day = date.slice(0, 10).replace(/-/g, "");
  return `Draft-${day}`;
};

export function buildReportSnapshots(
  taskSpace: TaskSpace,
  artifacts: OutputArtifact[],
  moduleRuns: ModuleRun[],
  issues: ConsistencyIssue[],
  evidenceHits: EvidenceHit[]
): ReportReviewSnapshot[] {
  const taskArtifacts = artifacts
    .filter((artifact) => artifact.taskSpaceId === taskSpace.id)
    .filter((artifact) => ["report", "docx", "pdf", "html", "md"].includes(safeLower(artifact.kind)));

  const snapshots = taskArtifacts.map((artifact) => {
    const relatedRuns = moduleRuns
      .filter((run) => run.taskSpaceId === taskSpace.id && run.module === artifact.module)
      .sort((a, b) => ((b.finishedAt ?? b.startedAt) < (a.finishedAt ?? a.startedAt) ? -1 : 1));
    const latestRun = relatedRuns[0];
    const insight = extractInsight(latestRun?.response);

    return {
      id: `${taskSpace.id}-${artifact.id}`,
      taskSpaceId: taskSpace.id,
      module: artifact.module,
      artifactId: artifact.id,
      artifactKind: artifact.kind,
      artifactPath: artifact.path,
      generatedAt: artifact.createdAt,
      draftStatus: "draft",
      version: createVersion(artifact.createdAt),
      riskLevel: insight.riskLevel ?? "N/A",
      issueCount: issues.filter((issue) => issue.taskSpaceId === taskSpace.id && issue.module === artifact.module).length,
      evidenceCount: evidenceHits.filter((hit) => hit.taskSpaceId === taskSpace.id && hit.module === artifact.module).length,
      runId: latestRun?.id
    } satisfies ReportReviewSnapshot;
  });

  return snapshots.sort((a, b) => (a.generatedAt < b.generatedAt ? 1 : -1));
}

export function buildTraceLinks(
  snapshot: ReportReviewSnapshot,
  moduleRuns: ModuleRun[],
  issues: ConsistencyIssue[],
  evidenceHits: EvidenceHit[]
): TraceLink[] {
  const links: TraceLink[] = [];

  for (const run of moduleRuns.filter((item) => item.taskSpaceId === snapshot.taskSpaceId && item.module === snapshot.module)) {
    links.push({
      id: `${snapshot.id}-run-${run.id}`,
      snapshotId: snapshot.id,
      taskSpaceId: snapshot.taskSpaceId,
      module: snapshot.module,
      targetType: "run",
      targetId: run.id,
      title: `${run.module.toUpperCase()} · ${run.success ? "SUCCESS" : "FAILED"}`,
      excerpt: run.error
    });
  }

  for (const issue of issues.filter((item) => item.taskSpaceId === snapshot.taskSpaceId && item.module === snapshot.module)) {
    links.push({
      id: `${snapshot.id}-issue-${issue.id}`,
      snapshotId: snapshot.id,
      taskSpaceId: snapshot.taskSpaceId,
      module: snapshot.module,
      targetType: "issue",
      targetId: issue.id,
      title: issue.message,
      excerpt: issue.severity.toUpperCase()
    });
  }

  for (const hit of evidenceHits.filter((item) => item.taskSpaceId === snapshot.taskSpaceId && item.module === snapshot.module)) {
    links.push({
      id: `${snapshot.id}-evidence-${hit.id}`,
      snapshotId: snapshot.id,
      taskSpaceId: snapshot.taskSpaceId,
      module: snapshot.module,
      targetType: "evidence",
      targetId: hit.id,
      title: hit.title,
      excerpt: hit.snippet
    });
  }

  return links.slice(0, 120);
}

export async function fetchReportMetadata(taskId: string): Promise<RemoteReportMetadata | null> {
  try {
    const response = await fetch(`/api/v1/reports/${taskId}/metadata`);
    if (!response.ok) return null;
    const data: unknown = await response.json();
    if (!isRecord(data)) return null;
    return {
      risk_level: typeof data.risk_level === "string" ? data.risk_level : undefined,
      version: typeof data.version === "string" ? data.version : undefined,
      summary: typeof data.summary === "string" ? data.summary : undefined
    };
  } catch {
    return null;
  }
}
