import type {
  ConsistencyIssue,
  EvidenceHit,
  ModuleRun,
  OutputArtifact,
  TaskSpace,
  WorkflowStepState
} from "./domain";

const nowIso = () => new Date().toISOString();

export function deriveWorkflowSteps(
  taskSpace: TaskSpace,
  latestRun: ModuleRun | null,
  artifacts: OutputArtifact[],
  evidence: EvidenceHit[],
  issues: ConsistencyIssue[]
): WorkflowStepState[] {
  const relatedArtifacts = artifacts.filter((item) => item.taskSpaceId === taskSpace.id && (!latestRun || item.module === latestRun.module));
  const relatedEvidence = evidence.filter((item) => item.taskSpaceId === taskSpace.id && (!latestRun || item.module === latestRun.module));
  const relatedIssues = issues.filter((item) => item.taskSpaceId === taskSpace.id && (!latestRun || item.module === latestRun.module));
  const baseTime = latestRun?.finishedAt ?? latestRun?.startedAt ?? nowIso();

  const blockedReason = latestRun && !latestRun.success ? latestRun.error ?? "Module run failed." : undefined;

  return [
    {
      key: "input_validation",
      status: latestRun ? "done" : "pending",
      reason: latestRun ? undefined : "No run has started yet.",
      updatedAt: baseTime
    },
    {
      key: "execution",
      status: latestRun ? (latestRun.success ? "done" : "blocked") : "pending",
      reason: blockedReason,
      updatedAt: baseTime
    },
    {
      key: "evidence_binding",
      status: !latestRun ? "pending" : relatedEvidence.length > 0 ? "done" : latestRun.success ? "blocked" : "pending",
      reason: !latestRun ? undefined : relatedEvidence.length === 0 ? "No evidence hits were bound." : undefined,
      updatedAt: baseTime
    },
    {
      key: "consistency_check",
      status: !latestRun ? "pending" : relatedIssues.length > 0 ? "blocked" : latestRun.success ? "done" : "pending",
      reason: relatedIssues[0]?.message,
      updatedAt: baseTime
    },
    {
      key: "report_export",
      status: !latestRun ? "pending" : relatedArtifacts.length > 0 ? "done" : latestRun.success ? "running" : "pending",
      reason: !latestRun ? undefined : relatedArtifacts.length === 0 ? "No report artifact found yet." : undefined,
      updatedAt: baseTime
    }
  ];
}

