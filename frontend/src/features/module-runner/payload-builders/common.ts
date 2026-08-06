export const splitNonEmptyLines = (input: string): string[] =>
  input
    .split(/[\n;；]+/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);

export function requireText(value: string, field: string, minLength = 1): string {
  const normalized = value.trim();
  if (normalized.length < minLength) {
    throw new Error(`${field} is required`);
  }
  return normalized;
}

export function requireAllowedValue(
  value: string,
  field: string,
  allowedValues: readonly string[],
): void {
  if (!allowedValues.includes(value)) {
    throw new Error(`${field} has an unsupported value: ${value}`);
  }
}

export function requireFileExtensions(paths: readonly string[], allowedExtensions: readonly string[]): void {
  for (const path of paths) {
    const extension = path.split(".").pop()?.toLowerCase() ?? "";
    if (!allowedExtensions.includes(extension)) {
      throw new Error(`Unsupported file extension for ${path}`);
    }
  }
}
