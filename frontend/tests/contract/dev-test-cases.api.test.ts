// @vitest-environment node

import { describe, expect, it } from "vitest";

import { findModule } from "../../src/api/modules";
import type { ModuleKey } from "../../src/lib/domain";
import { DEV_TEST_CASES } from "../../src/lib/dev-test-cases";
import {
  fetchContractState,
  registerContractUser,
  submitDevTestCase,
} from "./dev-case-api-runner";

const baseUrl = (process.env.AI4LAW_CONTRACT_BASE_URL ?? "").replace(/\/$/, "");
const contractDescribe = baseUrl ? describe : describe.skip;

contractDescribe("developer cases against the FastAPI contract app", () => {
  it("accepts all 26 cases without executing background runners", async () => {
    const token = await registerContractUser(baseUrl);
    const entries = Object.entries(DEV_TEST_CASES);
    let submittedCases = 0;

    for (const [moduleKey, testCases] of entries) {
      const definition = findModule(moduleKey as ModuleKey);
      for (const testCase of testCases) {
        const result = await submitDevTestCase({
          baseUrl,
          definition,
          testCase,
          token,
        });
        expect(
          result.status,
          `${moduleKey}/${testCase.name}: HTTP ${result.status} ${JSON.stringify(result.body)}`,
        ).toBeGreaterThanOrEqual(200);
        expect(result.status).toBeLessThan(300);
        submittedCases += 1;
      }
    }

    const state = await fetchContractState(baseUrl);
    expect(submittedCases).toBe(26);
    expect(state).toEqual({
      manager_count: 9,
      submission_count: 23,
      external_network_blocked: true,
    });
  }, 30_000);
});
