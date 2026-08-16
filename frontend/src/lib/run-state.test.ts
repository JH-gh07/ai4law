import { describe, expect, it } from "vitest";

import { selectRunningModuleRuns } from "./run-state";

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
