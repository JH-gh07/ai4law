import { describe, expect, it } from "vitest";

import { mergeModuleRuns, reconcileRecoveredTaskSpaces, remapRecoveredArtifacts } from "./app-store";

describe("mergeModuleRuns", () => {
  it("keeps one task-space run and lets a terminal server state replace local running", () => {
    const merged = mergeModuleRuns([
      {
        id: "local-run",
        taskSpaceId: "workspace-1",
        module: "review",
        runMode: "async",
        startedAt: "2026-08-10T19:07:25.841Z",
        request: {},
        success: false,
        asyncTaskId: "task-1",
        asyncState: "running",
      },
      {
        id: "recovered-run",
        taskSpaceId: "task-1",
        module: "review",
        runMode: "async",
        startedAt: "2026-08-10T19:07:25.623Z",
        request: {},
        finishedAt: "2026-08-11T03:17:05.574Z",
        success: false,
        error: "Review generation failed",
        asyncTaskId: "task-1",
        asyncState: "failed",
      },
    ]);

    expect(merged).toHaveLength(1);
    expect(merged[0]?.taskSpaceId).toBe("workspace-1");
    expect(merged[0]?.asyncState).toBe("failed");
    expect(merged[0]?.finishedAt).toBe("2026-08-11T03:17:05.574Z");
  });
});

describe("recovery task-space reconciliation", () => {
  it("removes a duplicate async-task workspace when the run belongs to an existing workspace", () => {
    const tasks = [
      { id: "workspace-1", name: "Review", mode: "rapid", jurisdiction: "CN", taskTemplateId: "review", module: "review", workspaceStyle: "cn_document_review", createdAt: "2026-08-10", updatedAt: "2026-08-11" },
      { id: "task-1", name: "Recovered Review", mode: "rapid", jurisdiction: "CN", taskTemplateId: "review", module: "review", workspaceStyle: "cn_document_review", createdAt: "2026-08-10", updatedAt: "2026-08-11" },
    ] as any;
    const runs = [{ id: "run-1", taskSpaceId: "workspace-1", module: "review", runMode: "async", startedAt: "2026-08-10", success: true, request: {}, asyncTaskId: "task-1", asyncState: "completed" }] as any;
    expect(reconcileRecoveredTaskSpaces(tasks, runs).map((item) => item.id)).toEqual(["workspace-1"]);
    expect(remapRecoveredArtifacts([{ id: "a", taskSpaceId: "task-1", module: "review", kind: "pdf", path: "x", createdAt: "2026-08-11" }] as any, runs)[0].taskSpaceId).toBe("workspace-1");
  });
});
