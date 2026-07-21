type ArtifactReference = {
  kind: string;
  path: string;
};

const extension = (value: string): string => {
  const fileName = value.replace(/\\/g, "/").split("/").pop()?.toLowerCase() ?? "";
  const dot = fileName.lastIndexOf(".");
  return dot === -1 ? "" : fileName.slice(dot + 1);
};

const basename = (value: string): string => {
  const fileName = value.replace(/\\/g, "/").split("/").pop()?.toLowerCase() ?? "";
  const dot = fileName.lastIndexOf(".");
  return dot === -1 ? fileName : fileName.slice(0, dot);
};

const isPdf = (artifact: ArtifactReference): boolean =>
  artifact.kind.toLowerCase() === "pdf" || extension(artifact.path) === "pdf";

export function findPdfCompanion<T extends ArtifactReference>(
  selected: T | null,
  artifacts: T[],
): T | null {
  if (!selected) return null;
  if (isPdf(selected)) return selected;
  const selectedBasename = basename(selected.path);
  return (
    artifacts.find(
      (artifact) => isPdf(artifact) && basename(artifact.path) === selectedBasename,
    ) ?? null
  );
}
