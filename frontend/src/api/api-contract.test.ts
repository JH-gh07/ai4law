import { describe, expect, expectTypeOf, it } from "vitest";

import { listModules } from "./modules";
import {
  MODULE_REQUEST_ENDPOINTS,
  type ModuleRequestMap,
  type PostJsonBody,
} from "./api-contract";

describe("generated API request contract", () => {
  it("matches every runtime module submission endpoint", () => {
    const definitions = listModules();

    expect(Object.keys(MODULE_REQUEST_ENDPOINTS).sort()).toEqual(
      definitions.map((definition) => definition.key).sort(),
    );
    for (const definition of definitions) {
      expect(MODULE_REQUEST_ENDPOINTS[definition.key]).toBe(
        definition.asyncSubmitEndpoint ?? definition.syncEndpoint,
      );
    }
  });

  it("maps module payloads to generated POST request bodies", () => {
    expectTypeOf<ModuleRequestMap["diagnosis"]>().toEqualTypeOf<
      PostJsonBody<"/api/v1/diagnosis/report">
    >();
    expectTypeOf<ModuleRequestMap["review"]>().toEqualTypeOf<
      PostJsonBody<"/api/v1/review/generate_async">
    >();
    expectTypeOf<ModuleRequestMap["us_14117"]>().toEqualTypeOf<
      PostJsonBody<"/api/v1/us_14117/generate_async">
    >();
    expectTypeOf<{}>().toMatchTypeOf<
      Pick<ModuleRequestMap["assessment"], "path_check_mode">
    >();
  });

  it("keeps known historical drift invalid at compile time", () => {
    type DiagnosisScenario = ModuleRequestMap["diagnosis"]["answers"]["q6_scenario"];
    type CnRecipient = ModuleRequestMap["cn_flow"]["recipient_entities"][number];
    type PipiaCompany = ModuleRequestMap["pipia"]["company_profile"];

    const supportedScenario: DiagnosisScenario = "contract_performance";
    // @ts-expect-error The legacy scenario is not part of the generated Pydantic enum.
    const legacyScenario: DiagnosisScenario = "business_operation";
    // @ts-expect-error country_region is required; the legacy country field cannot replace it.
    const legacyRecipient: CnRecipient = { entity_name: "Legacy", country: "CN", entity_role: "vendor" };
    // @ts-expect-error company_uscc is required by the generated PIPIA company profile.
    const missingUscc: PipiaCompany = { company_name: "Legacy Company" };

    expect(supportedScenario).toBe("contract_performance");
    expect(legacyScenario).toBe("business_operation");
    expect(legacyRecipient).toHaveProperty("country", "CN");
    expect(missingUscc).toEqual({ company_name: "Legacy Company" });
  });
});
