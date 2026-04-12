import { ResourceSection } from "./ResourceSection";
import { TaskSummaryCard } from "./TaskSummaryCard";
import { WorkspaceSection } from "./WorkspaceSection";
import type { ResourceExplorerData, ResourceExplorerHandlers } from "./types";

type ResourceExplorerProps = {
  data: ResourceExplorerData;
  handlers: ResourceExplorerHandlers;
};

export function ResourceExplorer({ data, handlers }: ResourceExplorerProps) {
  return (
    <div className="resource-explorer">
      <TaskSummaryCard summary={data.taskSummary} />

      <ResourceSection
        section={data.sections.inputMaterials}
        onItemClick={handlers.onOpenResource}
        onUploadMissing={handlers.onUploadMissingItem}
      />

      <ResourceSection section={data.sections.taskSteps} onItemClick={handlers.onGoToStep} />

      <ResourceSection section={data.sections.runtimeResources} onItemClick={handlers.onOpenResource} />

      <ResourceSection section={data.sections.outputArtifacts} onItemClick={handlers.onOpenResource} />

      <WorkspaceSection section={data.sections.workspaceViews} onSwitchWorkspace={handlers.onSwitchWorkspace} />
    </div>
  );
}

