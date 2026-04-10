export type Jurisdiction = "CN" | "EU" | "US";

export type LaunchMode = "rapid" | "draft" | "matrix";

export type ModuleKey =
  | "diagnosis"
  | "assessment"
  | "scc"
  | "pipia"
  | "bcr"
  | "dpia"
  | "tia"
  | "cn_flow"
  | "cpra";

export type RunMode = "sync" | "async";

export type TaskSpace = {
  id: string;
  name: string;
  mode: LaunchMode;
  jurisdiction: Jurisdiction;
  createdAt: string;
  updatedAt: string;
};

export type ModuleRun = {
  id: string;
  taskSpaceId: string;
  module: ModuleKey;
  runMode: RunMode;
  startedAt: string;
  finishedAt?: string;
  success: boolean;
  request: unknown;
  response?: unknown;
  error?: string;
  asyncTaskId?: string;
  asyncState?: string;
};

export type OutputArtifact = {
  id: string;
  taskSpaceId: string;
  module: ModuleKey;
  kind: string;
  path: string;
  createdAt: string;
};

export type EvidenceHit = {
  id: string;
  taskSpaceId: string;
  module: ModuleKey;
  source: string;
  title: string;
  snippet: string;
  createdAt: string;
};

export type ConsistencyIssue = {
  id: string;
  taskSpaceId: string;
  module: ModuleKey;
  severity: "high" | "medium" | "low";
  message: string;
  createdAt: string;
};

export type PanelState = {
  leftOpen: boolean;
  rightOpen: boolean;
  topOpen: boolean;
  focusMode: "split" | "run" | "preview";
  stageLayout: "split" | "single";
  primaryPlugin: "run" | "preview" | "evidence" | "timeline";
  secondaryPlugin: "run" | "preview" | "evidence" | "timeline";
};

export type OnboardingState = {
  active: boolean;
  stepIndex: number;
  completed: boolean;
};

export type WorkflowStepKey =
  | "input_validation"
  | "execution"
  | "evidence_binding"
  | "consistency_check"
  | "report_export";

export type WorkflowStepStatus = "pending" | "running" | "blocked" | "done";

export type WorkflowStepState = {
  key: WorkflowStepKey;
  status: WorkflowStepStatus;
  reason?: string;
  updatedAt: string;
};

export type ReportReviewSnapshot = {
  id: string;
  taskSpaceId: string;
  module: ModuleKey;
  artifactId: string;
  artifactKind: string;
  artifactPath: string;
  generatedAt: string;
  draftStatus: "draft";
  version: string;
  riskLevel: string;
  issueCount: number;
  evidenceCount: number;
  runId?: string;
};

export type TraceLinkTargetType = "run" | "evidence" | "issue";

export type TraceLink = {
  id: string;
  snapshotId: string;
  taskSpaceId: string;
  module: ModuleKey;
  targetType: TraceLinkTargetType;
  targetId: string;
  title: string;
  excerpt?: string;
};
