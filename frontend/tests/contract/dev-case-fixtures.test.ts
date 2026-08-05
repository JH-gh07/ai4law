// @vitest-environment node

import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { DEV_TEST_CASES } from "../../src/lib/dev-test-cases";

const REPOSITORY_ROOT = fileURLToPath(new URL("../../../", import.meta.url));

describe("developer case fixture hygiene", () => {
  it("keeps every backend fixture present and tracked by Git", () => {
    const fixturePaths = Object.values(DEV_TEST_CASES)
      .flat()
      .flatMap((testCase) => testCase.backendFilePaths ?? []);

    expect(fixturePaths.length).toBeGreaterThan(0);
    for (const relativePath of fixturePaths) {
      expect(existsSync(resolve(REPOSITORY_ROOT, relativePath)), relativePath).toBe(true);
      expect(() => {
        execFileSync("git", ["-C", REPOSITORY_ROOT, "ls-files", "--error-unmatch", "--", relativePath], {
          stdio: "ignore",
        });
      }, `${relativePath} must be tracked by Git`).not.toThrow();
    }
  });
});
