import { describe, expect, it } from "vitest";

import { mergeModuleRuns } from "./app-store";

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
