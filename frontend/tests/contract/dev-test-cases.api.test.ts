// @vitest-environment node

import { describe, expect, it } from "vitest";

import { findModule } from "../../src/api/modules";
import type { ModuleKey } from "../../src/lib/domain";
import { DEV_TEST_CASES } from "../../src/lib/dev-test-cases";
import {
  fetchContractState,
  registerContractUser,
  submitDevTestCase,
  submitRawContractPayload,
} from "./dev-case-api-runner";

const baseUrl = (process.env.AI4LAW_CONTRACT_BASE_URL ?? "").replace(/\/$/, "");
const contractDescribe = baseUrl ? describe : describe.skip;

contractDescribe("developer cases against the FastAPI contract app", () => {
  it("accepts all 26 cases without executing background runners", async () => {
    const token = await registerContractUser(baseUrl);
    const entries = Object.entries(DEV_TEST_CASES);
    const initialState = await fetchContractState(baseUrl);
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
    expect(state.manager_count).toBe(9);
    expect(state.submission_count - initialState.submission_count).toBe(23);
    expect(state.external_network_blocked).toBe(true);
  }, 30_000);

  it("rejects representative stale or incomplete payloads", async () => {
    const token = await registerContractUser(baseUrl);
    const cnFlowDefinition = findModule("cn_flow");
    const pipiaDefinition = findModule("pipia");
    const reviewDefinition = findModule("review");

    const cnFlowPayload = structuredClone(DEV_TEST_CASES.cn_flow[0].payload);
    const cnFlowRecipient = cnFlowPayload.recipient_entities[0] as Record<string, unknown>;
    cnFlowRecipient.country = cnFlowRecipient.country_region;
    delete cnFlowRecipient.country_region;

    const pipiaPayload = structuredClone(DEV_TEST_CASES.pipia[0].payload);
    delete (pipiaPayload.company_profile as Record<string, unknown>).company_uscc;

    const reviewPayload = structuredClone(DEV_TEST_CASES.review[0].payload);
    delete reviewPayload.uploaded_files;

    const [cnFlowResult, pipiaResult, reviewResult] = await Promise.all([
      submitRawContractPayload({
        baseUrl,
        endpoint: cnFlowDefinition.asyncSubmitEndpoint!,
        payload: cnFlowPayload,
        token,
      }),
      submitRawContractPayload({
        baseUrl,
        endpoint: pipiaDefinition.asyncSubmitEndpoint!,
        payload: pipiaPayload,
        token,
      }),
      submitRawContractPayload({
        baseUrl,
        endpoint: reviewDefinition.asyncSubmitEndpoint!,
        payload: reviewPayload,
        token,
      }),
    ]);

    expect(cnFlowResult.status).toBe(422);
    expect(pipiaResult.status).toBe(422);
    expect(reviewResult.status).toBe(400);
  });
});
