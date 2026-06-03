import { getAuthHeaders } from "./auth/auth-service";
import type { ModuleKey } from "./domain";

const ENDPOINTS: Record<ModuleKey, string> = {
  diagnosis: "/api/v1/diagnosis/report",
  assessment: "/api/v1/assessment/generate",
  review: "/api/v1/review/generate",
  scc: "/api/v1/scc/generate",
  pipia: "/api/v1/pipia/generate",
  bcr: "/api/v1/bcr/generate",
  dpia: "/api/v1/dpia/generate",
  tia: "/api/v1/tia/generate",
  cn_flow: "/api/v1/cn-flow/generate",
  cpra: "/api/v1/cpra/generate",
  us_14117: "/api/v1/us_14117/generate"
  eu_scc: "/api/v1/eu_scc/generate",

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const errorMessage = (data: unknown): string => {
  if (!isRecord(data)) {
    return "Request failed";
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => {
        if (isRecord(item) && typeof item.msg === "string") return item.msg;
        return JSON.stringify(item);
      })
      .join("; ");
  }

  return "Request failed";
};

export async function runModuleRequest(module: ModuleKey, payload: unknown): Promise<unknown> {
  const response = await fetch(ENDPOINTS[module], {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(payload)
  });

  const data: unknown = await response.json();
  if (!response.ok) {
    throw new Error(errorMessage(data));
  }

  return data;
}
