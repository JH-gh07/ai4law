import type { ModuleRun, TaskSpace, WorkflowStepState } from "../../../lib/domain";
import type { ResourceExplorerData, ResourceItemData } from "./types";

type BuildResourceExplorerDataInput = {
  taskSpace: TaskSpace;
  latestRun: ModuleRun | null;
  workflowSteps: WorkflowStepState[];
  openTabs: Array<{ id: string; label: string }>;
  closedTabs: Array<{ id: string; label: string }>;
  evidenceCount: number;
  issueCount: number;
  artifactCount: number;
};

const STEP_KEY_ORDER = ["input_validation", "execution", "evidence_binding", "consistency_check", "report_export"] as const;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const hasAnyAttachment = (value: unknown): boolean => {
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "string") return value.trim().length > 0;
  return false;
};

const hasUploadByKey = (request: unknown, keys: string[]): boolean => {
  if (!isRecord(request)) return false;
  for (const [key, value] of Object.entries(request)) {
    if (!keys.some((keyword) => key.toLowerCase().includes(keyword))) continue;
    if (hasAnyAttachment(value)) return true;
    if (isRecord(value) && Object.values(value).some((item) => hasAnyAttachment(item))) return true;
  }
  return false;
};

const toRunBatch = (latestRun: ModuleRun | null, fallbackModule: string): string => {
  if (!latestRun) return `${fallbackModule.toLowerCase()}-2026`;
  const runId = latestRun.id;
  const hit = runId.match(/^([a-z_]+)-/i);
  return hit ? `${hit[1]}-2026` : `${fallbackModule.toLowerCase()}-2026`;
};

const deriveSummaryStatus = (inputMaterials: ResourceItemData[], latestRun: ModuleRun | null): "failed" | "in_progress" | "completed" => {
  const hasMissingCritical = inputMaterials.some((item) => item.kind === "input" && item.status === "missing" && item.id === "data_inventory");
  if (hasMissingCritical) return "failed";
  if (latestRun && !latestRun.success) return "failed";
  if (latestRun) return "in_progress";
  return "in_progress";
};

const stepStatusToExplorerStatus = (status: WorkflowStepState["status"]): ResourceItemData["status"] => {
  if (status === "blocked") return "failed";
  if (status === "done") return "completed";
  if (status === "running") return "in_progress";
  return "pending";
};

export function buildResourceExplorerData({
  taskSpace,
  latestRun,
  workflowSteps,
  openTabs,
  closedTabs,
  evidenceCount,
  issueCount,
  artifactCount
}: BuildResourceExplorerDataInput): ResourceExplorerData {
  const request = latestRun?.request;

  const hasDataInventory = hasUploadByKey(request, ["data_inventory", "datainventory", "data_inventory_files"]);
  const hasExternalEntities = hasUploadByKey(request, ["entity", "external"]);
  const hasInternalMaterials = hasUploadByKey(request, ["internal", "access", "material"]);

  const inputMaterials: ResourceItemData[] = [
    {
      id: "data_inventory",
      kind: "input",
      label: "数据清单（data_inventory）",
      status: hasDataInventory ? "uploaded" : "missing",
      hint: hasDataInventory ? "已检测到上传文件。" : "请上传数据清单附件（data_inventory）",
      highlight: !hasDataInventory,
      blocked: !hasDataInventory,
      uploadKey: "data_inventory"
    },
    {
      id: "external_entities",
      kind: "input",
      label: "外部实体清单",
      status: hasExternalEntities ? "uploaded" : "pending",
      hint: hasExternalEntities ? "已上传，可继续下一步。" : "建议上传以完成实体核验。",
      uploadKey: "external_entities"
    },
    {
      id: "internal_access",
      kind: "input",
      label: "内部访问与材料",
      status: hasInternalMaterials ? "uploaded" : "pending",
      hint: hasInternalMaterials ? "已上传，可用于访问边界审查。" : "尚未上传，后续一致性检查可能受影响。",
      uploadKey: "internal_access"
    },
    {
      id: "attachments",
      kind: "input",
      label: "附件上传",
      status: "optional",
      hint: "可选补充合同台账、组织架构、股权结构等材料。",
      uploadKey: "attachments"
    }
  ];

  const stepByKey = new Map(workflowSteps.map((step) => [step.key, step]));
  const taskSteps: ResourceItemData[] = [
    {
      id: "step_1",
      kind: "step",
      label: "1. 出境数据清单",
      status: !hasDataInventory ? "in_progress" : stepStatusToExplorerStatus(stepByKey.get("input_validation")?.status ?? "pending"),
      hint: !hasDataInventory ? "当前步骤缺少关键材料。" : "可继续到外部实体清单。",
      stepKey: "input_validation",
      highlight: !hasDataInventory
    },
    {
      id: "step_2",
      kind: "step",
      label: "2. 外部实体清单",
      status: "pending",
      hint: "待处理",
      stepKey: "execution"
    },
    {
      id: "step_3",
      kind: "step",
      label: "3. 内部访问与材料",
      status: "pending",
      hint: "待处理",
      stepKey: "evidence_binding"
    },
    {
      id: "step_4",
      kind: "step",
      label: "4. 附件上传",
      status: "pending",
      hint: "待处理",
      stepKey: "consistency_check"
    }
  ];

  const runtimeResources: ResourceItemData[] = [
    {
      id: "runtime_draft",
      kind: "runtime",
      label: "当前表单草稿",
      status: "editing",
      hint: "编辑中",
      meta: "点击可回到运行表单。"
    },
    {
      id: "runtime_evidence",
      kind: "runtime",
      label: "证据绑定",
      status: evidenceCount > 0 ? "completed" : "pending",
      hint: evidenceCount > 0 ? `已绑定 ${evidenceCount} 条` : "0，待处理"
    },
    {
      id: "runtime_consistency",
      kind: "runtime",
      label: "一致性检查",
      status: issueCount > 0 ? "failed" : "pending",
      hint: issueCount > 0 ? `存在 ${issueCount} 条告警` : "待处理"
    },
    {
      id: "runtime_logs",
      kind: "runtime",
      label: "运行日志",
      status: "opened",
      hint: "可查看"
    }
  ];

  const outputArtifacts: ResourceItemData[] = [
    {
      id: "output_report",
      kind: "output",
      label: "14117 风险评估结论报告",
      status: artifactCount > 0 ? "completed" : "pending_generation",
      hint: artifactCount > 0 ? "已生成，可进入报告审阅。" : "待生成"
    },
    {
      id: "output_checklist",
      kind: "output",
      label: "核验清单",
      status: "pending_generation",
      hint: "待生成"
    },
    {
      id: "output_matrix",
      kind: "output",
      label: "风险匹配矩阵",
      status: "pending_generation",
      hint: "待生成"
    },
    {
      id: "output_actions",
      kind: "output",
      label: "整改建议",
      status: "pending_generation",
      hint: "待生成"
    }
  ];

  const workspaceViews: ResourceItemData[] = [
    ...openTabs.map((tab) => ({
      id: `workspace_${tab.id}`,
      kind: "workspace" as const,
      label: tab.label,
      status: "opened" as const,
      workspaceTabId: tab.id
    })),
    ...closedTabs.map((tab) => ({
      id: `workspace_${tab.id}`,
      kind: "workspace" as const,
      label: tab.label,
      status: "collapsed" as const,
      workspaceTabId: tab.id
    }))
  ];

  const summaryStatus = deriveSummaryStatus(inputMaterials, latestRun);
  const progress = summaryStatus === "failed" ? 25 : Math.round((workflowSteps.filter((step) => step.status === "done").length / STEP_KEY_ORDER.length) * 100);
  const blockedReason = !hasDataInventory ? "请上传数据清单附件（data_inventory）" : undefined;

  return {
    taskSummary: {
      name: taskSpace.name || "14117 行政令合规 2026-04-11",
      jurisdiction: taskSpace.jurisdiction,
      flow: taskSpace.mode.toUpperCase(),
      module: taskSpace.module.toUpperCase(),
      status: summaryStatus,
      progress,
      runBatch: toRunBatch(latestRun, taskSpace.module.toUpperCase()),
      blockedReason
    },
    sections: {
      inputMaterials: {
        id: "inputs",
        title: "输入材料",
        items: inputMaterials,
        collapsible: true,
        defaultOpen: true
      },
      taskSteps: {
        id: "steps",
        title: "任务步骤",
        items: taskSteps,
        collapsible: true,
        defaultOpen: true
      },
      runtimeResources: {
        id: "runtime",
        title: "运行中资源",
        items: runtimeResources,
        collapsible: true,
        defaultOpen: true
      },
      outputArtifacts: {
        id: "outputs",
        title: "输出成果",
        items: outputArtifacts,
        collapsible: true,
        defaultOpen: true
      },
      workspaceViews: {
        id: "workspace",
        title: "工作区视图",
        items: workspaceViews,
        collapsible: true,
        defaultOpen: true
      }
    }
  };
}

export const defaultResourceExplorerHandlers = {
  onOpenResource: (item: ResourceItemData) => {
    console.log("[resource-explorer] onOpenResource", item.id);
  },
  onGoToStep: (item: ResourceItemData) => {
    console.log("[resource-explorer] onGoToStep", item.id, item.stepKey);
  },
  onSwitchWorkspace: (item: ResourceItemData) => {
    console.log("[resource-explorer] onSwitchWorkspace", item.id, item.workspaceTabId);
  },
  onUploadMissingItem: (item: ResourceItemData) => {
    console.log("[resource-explorer] onUploadMissingItem", item.id, item.uploadKey);
  }
};
