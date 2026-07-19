import { getAuthHeaders } from "./auth";
import { apiFetch } from "./client";

export type RemoteReportMetadata = {
  risk_level?: string;
  version?: string;
  summary?: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export async function fetchReportMetadata(
  taskId: string,
): Promise<RemoteReportMetadata | null> {
  try {
    const response = await apiFetch(`/api/v1/reports/${taskId}/metadata`, {
      headers: { ...getAuthHeaders() },
    });
    if (!response.ok) return null;
    const data: unknown = await response.json();
    if (!isRecord(data)) return null;
    return {
      risk_level: typeof data.risk_level === "string" ? data.risk_level : undefined,
      version: typeof data.version === "string" ? data.version : undefined,
      summary: typeof data.summary === "string" ? data.summary : undefined,
    };
  } catch {
    return null;
  }
}
