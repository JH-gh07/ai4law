// @vitest-environment node

import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { getSeedDevCases, SEED_DEV_TEST_CASES } from "../../src/lib/dev-seed-cases";

const REPOSITORY_ROOT = fileURLToPath(new URL("../../../", import.meta.url));

describe("seed developer cases", () => {
  it("exposes 38 unsigned cases across the ten seeded modules", () => {
    const cases = Object.values(SEED_DEV_TEST_CASES).flat();
    expect(cases).toHaveLength(38);
    expect(cases.filter((item) => item.sourceKind === "synthetic_fixture")).toHaveLength(29);
    expect(cases.filter((item) => item.sourceKind === "source_faithful")).toHaveLength(9);
    expect(cases.every((item) => item.goldStatus === "unsigned")).toBe(true);
    expect(SEED_DEV_TEST_CASES.cn_flow).toBeUndefined();
  });

  it("keeps the frozen per-module distribution", () => {
    expect(Object.fromEntries(
      Object.keys(SEED_DEV_TEST_CASES).sort().map((module) => [
        module,
        getSeedDevCases(module as Parameters<typeof getSeedDevCases>[0]).length,
      ]),
    )).toEqual({
      assessment: 5, bcr: 2, cpra: 5, diagnosis: 5, dpia: 2,
      eu_scc: 5, pipia: 5, review: 2, tia: 2, us_14117: 5,
    });
  });

  it("keeps every source request and backend attachment resolvable", () => {
    for (const testCase of Object.values(SEED_DEV_TEST_CASES).flat()) {
      expect(existsSync(`${REPOSITORY_ROOT}/${testCase.sourceRequestPath}`), testCase.caseId).toBe(true);
      for (const path of testCase.backendFilePaths) {
        expect(existsSync(`${REPOSITORY_ROOT}/${path}`), `${testCase.caseId}: ${path}`).toBe(true);
      }
      expect(testCase.name).toContain("未签署");
    }
  });
});
