export function toFileName(value: string): string {
  const chunks = value.replace(/\\/g, "/").split("/");
  return chunks[chunks.length - 1] || value;
}

/** Normalize syntactic path variants without guessing filesystem roots. */
export function normalizeResourcePath(value: string): string {
  const normalizedSlashes = value.trim().replace(/\\/g, "/");
  const schemeMatch = normalizedSlashes.match(/^([a-z][a-z0-9+.-]*:\/\/)(.*)$/i);
  const scheme = schemeMatch?.[1] ?? "";
  const rawPath = schemeMatch?.[2] ?? normalizedSlashes;
  const absolute = !scheme && rawPath.startsWith("/");
  const segments: string[] = [];

  rawPath.split("/").forEach((segment) => {
    if (!segment || segment === ".") return;
    if (segment === ".." && segments.length > 0 && segments[segments.length - 1] !== "..") {
      segments.pop();
      return;
    }
    segments.push(segment);
  });

  if (!scheme) {
    const knownRootIndex = segments.findIndex((segment) =>
      ["benchmarks", "outputs", "reports", "resources", "storage", "uploads"].includes(segment.toLowerCase()),
    );
    if (knownRootIndex >= 0) return segments.slice(knownRootIndex).join("/");
  }

  return `${scheme}${absolute ? "/" : ""}${segments.join("/")}`;
}

export function getFileExtension(value: string): string {
  const fileName = toFileName(value).toLowerCase();
  const dotIndex = fileName.lastIndexOf(".");
  return dotIndex === -1 ? "" : fileName.slice(dotIndex + 1);
}

export function prettifyStem(value: string): string {
  return value
    .replace(/\.[^.]+$/, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
