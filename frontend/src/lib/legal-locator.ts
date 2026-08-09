/**
 * legal-locator.ts
 *
 * 这个文件定义了一个用于格式化法律条款定位符的函数 `formatLegalLocator`，以及一个类型 `LegalLocatorLanguage`。
 *
 * 函数：
 * - formatLegalLocator: 接收一个原始值和语言参数，返回格式化后的法律条款定位符字符串。
 *
 * 类型：
 * - LegalLocatorLanguage: 定义了支持的语言类型，可以是 "zh"（中文）或 "en"（英文）。
 */
export type LegalLocatorLanguage = "zh" | "en";

const NUMERIC_ARTICLE_RE = /^\d+[A-Za-z]?(?:[-–]\d+[A-Za-z]?)?$/;
//这个正则表达式用于识别法律条款的编号格式，例如 "123"、"123A"、"123-456"、"123A-456B" 等。

export function formatLegalLocator(
  rawValue: string | null | undefined,
  language: LegalLocatorLanguage = "zh",
): string {
  const value = String(rawValue ?? "").trim();
  if (!value) return "";
  if (!NUMERIC_ARTICLE_RE.test(value)) return value;
  return language === "zh" ? `第${value}条` : `Article ${value}`;
}
