export type ArtifactPreview = {
  path: string;
  file_name: string;
  kind: string;
  render_mode: "html" | "pdf" | "text" | "download";
  content: string;
  file_url?: string | null;
};

export async function fetchArtifactPreview(path: string): Promise<ArtifactPreview> {
  const response = await fetch(`/api/v1/artifacts/preview?path=${encodeURIComponent(path)}`);
  const data = (await response.json()) as ArtifactPreview | { detail?: string };
  if (!response.ok) {
    throw new Error(typeof (data as { detail?: string }).detail === "string" ? (data as { detail: string }).detail : "Failed to load artifact preview");
  }
  return data as ArtifactPreview;
}
