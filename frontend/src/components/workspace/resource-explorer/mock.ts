import type { ModuleRun, TaskSpace, WorkflowStepState } from "../../../lib/domain";
import { isRunFailed, isRunInProgress } from "../../../lib/run-state";
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
const LANG_KEY = "ai4law_ui_lang";
const isZh = () => globalThis.localStorage?.getItem(LANG_KEY) === "zh";
const L = (zh: string, en: string) => (isZh() ? zh : en);

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

const deriveSummaryStatus = (inputMaterials: ResourceItemData[], latestRun: ModuleRun | null): "blocked" | "in_progress" | "completed" => {
  const hasMissingCritical = inputMaterials.some((item) => item.kind === "input" && item.status === "missing" && item.id === "data_inventory");
  if (hasMissingCritical) return "blocked";
  if (isRunFailed(latestRun)) return "blocked";
  if (isRunInProgress(latestRun) || latestRun) return "in_progress";
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
      label: L("数据清单（data_inventory）", "Data Inventory (data_inventory)"),
      status: hasDataInventory ? "uploaded" : "missing",
      hint: hasDataInventory ? L("已检测到上传文件。", "Upload detected.") : L("请上传数据清单附件（data_inventory）", "Please upload data inventory attachments (data_inventory)."),
      highlight: !hasDataInventory,
      blocked: !hasDataInventory,
      uploadKey: "data_inventory"
    },
    {
      id: "external_entities",
      kind: "input",
      label: L("外部实体清单", "External Entity Inventory"),
      status: hasExternalEntities ? "uploaded" : "pending",
      hint: hasExternalEntities ? L("已上传，可继续下一步。", "Uploaded. You can continue.") : L("建议上传以完成实体核验。", "Recommended for entity verification."),
      uploadKey: "external_entities"
    },
    {
      id: "internal_access",
      kind: "input",
      label: L("内部访问与材料", "Internal Access & Materials"),
      status: hasInternalMaterials ? "uploaded" : "pending",
      hint: hasInternalMaterials ? L("已上传，可用于访问边界审查。", "Uploaded for access-boundary checks.") : L("尚未上传，后续一致性检查可能受影响。", "Not uploaded yet. Consistency checks may be affected."),
      uploadKey: "internal_access"
    },
    {
      id: "attachments",
      kind: "input",
      label: L("附件上传", "Attachments"),
      status: "optional",
      hint: L("可选补充合同台账、组织架构、股权结构等材料。", "Optional: contract ledgers, org structure, shareholding documents."),
      uploadKey: "attachments"
    }
  ];

  const stepByKey = new Map(workflowSteps.map((step) => [step.key, step]));
  const taskSteps: ResourceItemData[] = [
    {
      id: "step_1",
      kind: "step",
      label: L("1. 出境数据清单", "1. Export Data Inventory"),
      status: !hasDataInventory ? "in_progress" : stepStatusToExplorerStatus(stepByKey.get("input_validation")?.status ?? "pending"),
      hint: !hasDataInventory ? L("当前步骤缺少关键材料。", "Critical materials missing for this step.") : L("可继续到外部实体清单。", "Proceed to external entity inventory."),
      stepKey: "input_validation",
      highlight: !hasDataInventory
    },
    {
      id: "step_2",
      kind: "step",
      label: L("2. 外部实体清单", "2. External Entity Inventory"),
      status: "pending",
      hint: L("待处理", "Pending"),
      stepKey: "execution"
    },
    {
      id: "step_3",
      kind: "step",
      label: L("3. 内部访问与材料", "3. Internal Access & Materials"),
      status: "pending",
      hint: L("待处理", "Pending"),
      stepKey: "evidence_binding"
    },
    {
      id: "step_4",
      kind: "step",
      label: L("4. 附件上传", "4. Attachments"),
      status: "pending",
      hint: L("待处理", "Pending"),
      stepKey: "consistency_check"
    }
  ];

  const runtimeResources: ResourceItemData[] = [
    {
      id: "runtime_draft",
      kind: "runtime",
      label: L("当前表单草稿", "Current Form Draft"),
      status: "editing",
      hint: L("编辑中", "Editing"),
      meta: L("点击可回到运行表单。", "Click to return to the run form.")
    },
    {
      id: "runtime_evidence",
      kind: "runtime",
      label: L("证据绑定", "Evidence Binding"),
      status: evidenceCount > 0 ? "completed" : "pending",
      hint: evidenceCount > 0 ? (isZh() ? `已绑定 ${evidenceCount} 条` : `${evidenceCount} linked`) : L("0，待处理", "0, pending")
    },
    {
      id: "runtime_consistency",
      kind: "runtime",
      label: L("一致性检查", "Consistency Check"),
      status: issueCount > 0 ? "failed" : "pending",
      hint: issueCount > 0 ? (isZh() ? `存在 ${issueCount} 条告警` : `${issueCount} alerts`) : L("待处理", "Pending")
    },
    {
      id: "runtime_logs",
      kind: "runtime",
      label: L("运行日志", "Run Logs"),
      status: "opened",
      hint: L("可查看", "Viewable")
    }
  ];

  const outputArtifacts: ResourceItemData[] = [
    {
      id: "output_report",
      kind: "output",
      label: L("14117 风险评估结论报告", "14117 Risk Assessment Report"),
      status: artifactCount > 0 ? "completed" : "pending_generation",
      hint: artifactCount > 0 ? L("已生成，可进入报告审阅。", "Generated. Ready for review.") : L("待生成", "Pending generation")
    },
    {
      id: "output_checklist",
      kind: "output",
      label: L("核验清单", "Verification Checklist"),
      status: "pending_generation",
      hint: L("待生成", "Pending generation")
    },
    {
      id: "output_matrix",
      kind: "output",
      label: L("风险匹配矩阵", "Risk Mapping Matrix"),
      status: "pending_generation",
      hint: L("待生成", "Pending generation")
    },
    {
      id: "output_actions",
      kind: "output",
      label: L("整改建议", "Remediation Suggestions"),
      status: "pending_generation",
      hint: L("待生成", "Pending generation")
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
  const progress = summaryStatus === "blocked" ? 25 : Math.round((workflowSteps.filter((step) => step.status === "done").length / STEP_KEY_ORDER.length) * 100);
  const blockedReason = !hasDataInventory ? L("请上传数据清单附件（data_inventory）", "Please upload data inventory attachments (data_inventory).") : undefined;

  return {
    taskSummary: {
      name: taskSpace.name || L("14117 行政令合规 2026-04-11", "14117 Executive Order Compliance 2026-04-11"),
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
        title: L("输入材料", "Input Materials"),
        items: inputMaterials,
        collapsible: true,
        defaultOpen: true
      },
      taskSteps: {
        id: "steps",
        title: L("任务步骤", "Task Steps"),
        items: taskSteps,
        collapsible: true,
        defaultOpen: true
      },
      runtimeResources: {
        id: "runtime",
        title: L("运行中资源", "Runtime Resources"),
        items: runtimeResources,
        collapsible: true,
        defaultOpen: true
      },
      outputArtifacts: {
        id: "outputs",
        title: L("输出成果", "Output Artifacts"),
        items: outputArtifacts,
        collapsible: true,
        defaultOpen: true
      },
      workspaceViews: {
        id: "workspace",
        title: L("工作区视图", "Workspace Views"),
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
