export type LegalLocatorLanguage = "zh" | "en";

const NUMERIC_ARTICLE_RE = /^\d+[A-Za-z]?(?:[-–]\d+[A-Za-z]?)?$/;

export function formatLegalLocator(
  rawValue: string | null | undefined,
  language: LegalLocatorLanguage = "zh",
): string {
  const value = String(rawValue ?? "").trim();
  if (!value) return "";
  if (!NUMERIC_ARTICLE_RE.test(value)) return value;
  return language === "zh" ? `第${value}条` : `Article ${value}`;
}
