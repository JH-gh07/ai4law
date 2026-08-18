import { describe, expect, it } from "vitest";

import { selectPreferredRun, selectRunningModuleRuns } from "./run-state";

describe("selectRunningModuleRuns", () => {
  it("reconciles a generic Review failure once when the backend may still be running", () => {
    const runs = [
      {
        id: "review-run",
        taskSpaceId: "workspace-1",
        module: "review",
        runMode: "async",
        startedAt: "2026-08-16T06:26:33.000Z",
        finishedAt: "2026-08-16T06:26:33.000Z",
        success: false,
        request: {},
        error: "Review generation failed",
        asyncTaskId: "review-task",
        asyncState: "failed",
      },
      {
        id: "old-run",
        taskSpaceId: "workspace-1",
        module: "review",
        runMode: "async",
        startedAt: "2026-08-10T06:26:33.000Z",
        finishedAt: "2026-08-10T06:26:33.000Z",
        success: false,
        request: {},
        error: "Review generation failed",
        asyncTaskId: "old-task",
        asyncState: "failed",
        statusCheckedAt: "2026-08-10T06:27:00.000Z",
      },
    ] as any;

    expect(selectRunningModuleRuns(runs).map((run) => run.asyncTaskId)).toEqual(["review-task"]);
  });
});

describe("selectPreferredRun", () => {
  it("keeps a newer successful retry preferred when an older failure is reconciled later", () => {
    const preferred = selectPreferredRun([
      {
        id: "old-failure",
        taskSpaceId: "workspace-1",
        module: "review",
        runMode: "async",
        startedAt: "2026-08-15T21:25:25.809Z",
        finishedAt: "2026-08-16T12:42:21.903Z",
        success: false,
        request: {},
        error: "Review generation failed",
        asyncTaskId: "old-task",
        asyncState: "failed",
        statusCheckedAt: "2026-08-16T12:42:15.948Z",
      },
      {
        id: "new-success",
        taskSpaceId: "workspace-1",
        module: "review",
        runMode: "async",
        startedAt: "2026-08-15T22:26:33.269Z",
        finishedAt: "2026-08-15T22:32:08.956Z",
        success: true,
        request: {},
        asyncTaskId: "new-task",
        asyncState: "completed",
      },
    ]);

    expect(preferred?.id).toBe("new-success");
    expect(preferred?.success).toBe(true);
  });
});
