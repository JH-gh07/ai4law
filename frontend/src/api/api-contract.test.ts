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
});
