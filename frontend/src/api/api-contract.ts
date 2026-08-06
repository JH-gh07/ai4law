import type { ModuleKey } from "../lib/domain";
import type { paths } from "./generated/openapi";

export type PostJsonBody<Path extends keyof paths> =
  paths[Path] extends {
    post: {
      requestBody: {
        content: { "application/json": infer Body };
      };
    };
  }
    ? Body
    : never;

export const MODULE_REQUEST_ENDPOINTS = {
  diagnosis: "/api/v1/diagnosis/report",
  assessment: "/api/v1/assessment/generate_async",
  review: "/api/v1/review/generate_async",
  pipia: "/api/v1/pipia/generate_async",
  bcr: "/api/v1/bcr/generate_async",
  dpia: "/api/v1/dpia/generate_async",
  tia: "/api/v1/tia/generate_async",
  cn_flow: "/api/v1/cn-flow/generate_async",
  cpra: "/api/v1/cpra/generate_async",
  us_14117: "/api/v1/us_14117/generate_async",
  eu_scc: "/api/v1/eu_scc/generate_async",
} as const satisfies Record<ModuleKey, keyof paths>;

export type DevCaseModule = keyof typeof MODULE_REQUEST_ENDPOINTS;

export type ModuleRequestMap = {
  [Module in DevCaseModule]: PostJsonBody<(typeof MODULE_REQUEST_ENDPOINTS)[Module]>;
};
