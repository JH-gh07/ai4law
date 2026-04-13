import { useMemo } from "react";
import { useAppStore } from "../../lib/app-store";
import type { TaskSpace } from "../../lib/domain";
import { deriveWorkflowSteps } from "../../lib/workflow";
import { ResourceExplorer } from "./resource-explorer/ResourceExplorer";
import { buildResourceExplorerData, defaultResourceExplorerHandlers } from "./resource-explorer/mock";
import type { ResourceItemData } from "./resource-explorer/types";

type ResourcePanelProps = {
  taskSpace: TaskSpace;
  tabs: Array<{ id: string; label: string; closable: boolean }>;
  openTabs: string[];
  activeTab: string;
  onActivateTab: (tabId: string) => void;
  onOpenTab: (tabId: string) => void;
  onOpenResource?: (item: ResourceItemData) => void;
  onGoToStep?: (item: ResourceItemData) => void;
  onSwitchWorkspace?: (item: ResourceItemData) => void;
  onUploadMissingItem?: (item: ResourceItemData) => void;
};

export function ResourcePanel({
  taskSpace,
  tabs,
  openTabs,
  activeTab,
  onActivateTab,
  onOpenTab,
  onOpenResource,
  onGoToStep,
  onSwitchWorkspace,
  onUploadMissingItem
}: ResourcePanelProps) {
  const { state } = useAppStore();

  const runs = useMemo(
    () => state.moduleRuns.filter((item) => item.taskSpaceId === taskSpace.id).sort((a, b) => (a.startedAt < b.startedAt ? 1 : -1)),
    [state.moduleRuns, taskSpace.id]
  );

  const artifacts = useMemo(
    () => state.artifacts.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.artifacts, taskSpace.id]
  );

  const latestRunByModule = useMemo(() => {
    return runs[0] ?? null;
  }, [runs]);

  const evidence = useMemo(
    () => state.evidenceHits.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.evidenceHits, taskSpace.id]
  );

  const issues = useMemo(
    () => state.issues.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.issues, taskSpace.id]
  );

  const workflowSteps = useMemo(
    () => deriveWorkflowSteps(taskSpace, latestRunByModule, state.artifacts, state.evidenceHits, state.issues),
    [latestRunByModule, state.artifacts, state.evidenceHits, state.issues, taskSpace]
  );

  const closedTabs = useMemo(
    () => tabs.filter((tab) => !openTabs.includes(tab.id)),
    [tabs, openTabs]
  );

  const explorerData = useMemo(
    () =>
      buildResourceExplorerData({
        taskSpace,
        latestRun: latestRunByModule,
        workflowSteps,
        openTabs: tabs.filter((tab) => openTabs.includes(tab.id)).map((tab) => ({ id: tab.id, label: tab.label })),
        closedTabs: closedTabs.map((tab) => ({ id: tab.id, label: tab.label })),
        evidenceCount: evidence.length,
        issueCount: issues.length,
        artifactCount: artifacts.length
      }),
    [artifacts.length, closedTabs, evidence.length, issues.length, latestRunByModule, openTabs, tabs, taskSpace, workflowSteps]
  );

  const handlers = useMemo(
    () => ({
      onOpenResource: onOpenResource ?? defaultResourceExplorerHandlers.onOpenResource,
      onGoToStep: onGoToStep ?? defaultResourceExplorerHandlers.onGoToStep,
      onSwitchWorkspace: (item: ResourceItemData) => {
        if (item.workspaceTabId) {
          if (openTabs.includes(item.workspaceTabId)) {
            onActivateTab(item.workspaceTabId);
          } else {
            onOpenTab(item.workspaceTabId);
          }
        }
        if (onSwitchWorkspace) onSwitchWorkspace(item);
        else defaultResourceExplorerHandlers.onSwitchWorkspace(item);
      },
      onUploadMissingItem: onUploadMissingItem ?? defaultResourceExplorerHandlers.onUploadMissingItem
    }),
    [onActivateTab, onGoToStep, onOpenResource, onOpenTab, onSwitchWorkspace, onUploadMissingItem, openTabs]
  );

  return (
    <aside className="pane resource-pane" data-guide="workspace-left">
      <div className="pane-title">Resource Explorer</div>
      <div className="resource-pane-body">
        <ResourceExplorer data={explorerData} handlers={handlers} />
        <p className="resource-explorer-meta">
          当前标签页：{tabs.find((tab) => tab.id === activeTab)?.label ?? activeTab} · 打开 {openTabs.length}/{tabs.length}
        </p>
      </div>
    </aside>
  );
}
