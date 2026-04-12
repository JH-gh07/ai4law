import type { WorkflowStepKey } from "../../../lib/domain";

export type ExplorerStatus =
  | "missing"
  | "uploaded"
  | "parsed"
  | "optional"
  | "in_progress"
  | "pending"
  | "pending_generation"
  | "blocked"
  | "opened"
  | "collapsed"
  | "failed"
  | "completed"
  | "editing";

export type ResourceItemKind = "input" | "step" | "runtime" | "output" | "workspace";

export type ResourceItemData = {
  id: string;
  label: string;
  status: ExplorerStatus;
  meta?: string;
  hint?: string;
  highlight?: boolean;
  blocked?: boolean;
  stepKey?: WorkflowStepKey;
  workspaceTabId?: string;
  uploadKey?: string;
  kind: ResourceItemKind;
};

export type ResourceSectionData = {
  id: string;
  title: string;
  items: ResourceItemData[];
  collapsible?: boolean;
  defaultOpen?: boolean;
};

export type TaskSummaryData = {
  name: string;
  jurisdiction: string;
  flow: string;
  module: string;
  status: ExplorerStatus;
  progress: number;
  runBatch: string;
  blockedReason?: string;
};

export type ResourceExplorerData = {
  taskSummary: TaskSummaryData;
  sections: {
    inputMaterials: ResourceSectionData;
    taskSteps: ResourceSectionData;
    runtimeResources: ResourceSectionData;
    outputArtifacts: ResourceSectionData;
    workspaceViews: ResourceSectionData;
  };
};

export type ResourceExplorerHandlers = {
  onOpenResource: (item: ResourceItemData) => void;
  onGoToStep: (item: ResourceItemData) => void;
  onSwitchWorkspace: (item: ResourceItemData) => void;
  onUploadMissingItem: (item: ResourceItemData) => void;
};
