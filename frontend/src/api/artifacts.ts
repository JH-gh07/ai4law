import { getAuthHeaders } from "./auth";
import { apiFetch } from "./client";

export type ArtifactPreview = {
  path: string;
  file_name: string;
  kind: string;
  render_mode: "html" | "pdf" | "text" | "download" | "report_ir";
  content: string;
  file_url?: string | null;
  // Structured report body; only present when render_mode === "report_ir".
  report_ir?: Record<string, unknown> | null;
};

export async function fetchArtifactPreview(path: string): Promise<ArtifactPreview> {
  const response = await apiFetch(`/api/v1/artifacts/preview?path=${encodeURIComponent(path)}`, { headers: { ...getAuthHeaders() } });
  const data = (await response.json()) as ArtifactPreview | { detail?: string };
  if (!response.ok) {
    throw new Error(typeof (data as { detail?: string }).detail === "string" ? (data as { detail: string }).detail : "Failed to load artifact preview");
  }
  return data as ArtifactPreview;
}

export type ArtifactFileAction = "file" | "download";

export async function fetchArtifactBlob(
  path: string,
  action: ArtifactFileAction,
  errorMessage: string,
): Promise<Blob> {
  const response = await apiFetch(
    `/api/v1/artifacts/${action}?path=${encodeURIComponent(path)}`,
    { headers: { ...getAuthHeaders() } },
  );
  if (!response.ok) {
    throw new Error(errorMessage.replace("{status}", String(response.status)));
  }
  return response.blob();
}