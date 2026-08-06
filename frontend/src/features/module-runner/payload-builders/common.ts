export const splitNonEmptyLines = (input: string): string[] =>
  input
    .split(/[\n;；]+/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
