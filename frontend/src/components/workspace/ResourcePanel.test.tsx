import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAppStore } from "../../lib/app-store";
import type { ModuleRun, OutputArtifact, TaskSpace } from "../../lib/domain";
import { ResourcePanel } from "./ResourcePanel";

vi.mock("../../lib/app-store", () => ({ useAppStore: vi.fn() }));
vi.mock("../../lib/language", () => ({
  useLang: () => ({ lang: "zh", t: (key: string) => key }),
}));

const mockedUseAppStore = vi.mocked(useAppStore);

const taskSpace: TaskSpace = {
  id: "task-1",
  name: "测试任务",
  mode: "rapid",
  jurisdiction: "CN",
  taskTemplateId: "cn_assessment",
  module: "assessment",
  workspaceStyle: "cn_assessment",
  createdAt: "2026-08-08T08:00:00.000Z",
  updatedAt: "2026-08-08T08:00:00.000Z",
};

const run: ModuleRun = {
  id: "run-1",
  taskSpaceId: taskSpace.id,
  module: "assessment",
  runMode: "sync",
  startedAt: "2026-08-08T08:00:00.000Z",
  success: true,
  request: {
    uploaded_files: ["uploads/contract.docx"],
    source_registry: "resources/legal/source_registry.json",
  },
};

const artifacts: OutputArtifact[] = [
  {
    id: "report",
    taskSpaceId: taskSpace.id,
    module: "assessment",
    kind: "docx",
    path: "outputs/report.docx",
    createdAt: "2026-08-08T08:01:00.000Z",
  },
  {
    id: "facts",
    taskSpaceId: taskSpace.id,
    module: "assessment",
    kind: "facts_json",
    path: "outputs/facts.json",
    createdAt: "2026-08-08T08:01:00.000Z",
  },
];

describe("ResourcePanel", () => {
  beforeEach(() => {
    mockedUseAppStore.mockReturnValue({
      state: {
        moduleRuns: [run],
        artifacts,
      },
      dispatch: vi.fn(),
    } as unknown as ReturnType<typeof useAppStore>);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("shows only submitted files and user-facing outputs", () => {
    render(
      <ResourcePanel
        taskSpace={taskSpace}
        onToggleCollapse={vi.fn()}
        onOpenResource={vi.fn()}
      />,
    );

    expect(screen.getByText("contract.docx")).toBeInTheDocument();
    expect(screen.queryByText(/基础信息表单/)).not.toBeInTheDocument();
    expect(screen.queryByText(/facts/i)).not.toBeInTheDocument();
    expect(screen.getByText("第1次生成结果")).toBeInTheDocument();
    expect(screen.getByText("contract.docx").closest("button")).toBeNull();
  });

  it("opens a visible output from the generated result tree", () => {
    const onOpenResource = vi.fn();
    render(
      <ResourcePanel
        taskSpace={taskSpace}
        onToggleCollapse={vi.fn()}
        onOpenResource={onOpenResource}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /第1次生成结果/ }));
    fireEvent.click(screen.getByRole("button", { name: /报告 Word 版/ }));

    expect(onOpenResource).toHaveBeenCalledWith({ kind: "output", artifact: artifacts[0] });
  });
});
