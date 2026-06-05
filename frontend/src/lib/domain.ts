export type Jurisdiction = "CN" | "EU" | "US";

export type LaunchMode = "rapid" | "draft" | "matrix";

export type ModuleKey =
  | "diagnosis"
  | "assessment"
  | "review"
  | "scc"
  | "pipia"
  | "bcr"
  | "dpia"
  | "tia"
  | "cn_flow"
  | "cpra"
  | "us_14117"
  | "eu_scc";

export type RunMode = "sync" | "async";

export type WorkspaceStyleKey =
  | "cn_diagnosis"
  | "cn_assessment"
  | "cn_pipia"
  | "cn_document_review"
  | "eu_scc"
  | "eu_bcr"
  | "eu_dpia"
  | "eu_tia"
  | "us_14117"
  | "us_cpra";

export type TaskSpace = {
  id: string;
  name: string;
  mode: LaunchMode;
  jurisdiction: Jurisdiction;
  taskTemplateId: string;
  module: ModuleKey;
  workspaceStyle: WorkspaceStyleKey;
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
  errorCode?: string;
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
  leftWidth: number;
  rightWidth: number;
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
  source?: "task_create" | "replay";
  targetTaskId?: string;
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

export type SystemMessage = {
  id: string;
  taskSpaceId: string;
  text: string;
  createdAt: string;
  eventType?: string;
  eventSeq?: number;
};

export type StageNodeStatus = "pending" | "running" | "done";
export type StageNode = {
  id: string;
  name: string;
  status: StageNodeStatus;
  startedAt?: string;
  completedAt?: string;
  summary?: string;
  detail?: Record<string, unknown> | null;
  command?: string;
  icon?: string;
};

export type RunSession = {
  id: string;
  taskSpaceId: string;
  taskId: string;
  module: string;
  startedAt: string;
  stages: StageNode[];
  isComplete: boolean;
  completedAt?: string;
  totalDurationMs?: number;
  collapsed?: boolean;
};

// ═══════════════════════════════════════════════════════════════════════
// Agent Trace History — 语义化执行轨迹
// ═══════════════════════════════════════════════════════════════════════

export type TraceStage =
  | "Task"
  | "LLM"
  | "RAG"
  | "Tool"
  | "Parser"
  | "Generator"
  | "Review";

export type TraceBlockType = "CALL" | "INPUT" | "QUERY" | "RESULT" | "OUTPUT" | "ERROR";

export type TraceBlock = {
  label: TraceBlockType;
  content: string;
  language?: "text" | "json" | "markdown";
  preview?: string;
  isTruncated?: boolean;
  summary?: string;
};

export type TraceNode = {
  id: string;
  stage: TraceStage;
  action: string;
  description: string;
  detail?: string;
  status: "pending" | "running" | "success" | "error";
  timestamp: string;
  durationMs?: number;
  input?: TraceBlock;
  output?: TraceBlock;
  icon?: string;
  badge?: string;
  rawEventIds?: string[];
};
