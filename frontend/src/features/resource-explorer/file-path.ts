export function toFileName(value: string): string {
  const chunks = value.replace(/\\/g, "/").split("/");
  return chunks[chunks.length - 1] || value;
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
