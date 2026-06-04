function isMarkdownStructured(line: string): boolean {
  return /^(?:#{1,6}\s|[-*]\s|\d+\.\s|>\s|\|)/.test(line);
}

function normalizeHeadingSpacing(value: string): string {
  return value
    .replace(/^(#{1,6})([^\s#])/gm, "$1 $2")
    .replace(/^(\d+)\)\s+/gm, "$1. ")
    .replace(/^\s*•\s+/gm, "- ");
}

// ---------------------------------------------------------------------------
// 法条引用上下文检测
// 目的：避免把 Article 28、Art.28、GDPR Art.28、第28条 等法条名称
// 错误拆成 "Article 2" 和 "8、..."。
// ---------------------------------------------------------------------------

const LEGAL_REF_PATTERN =
  /(?:Article|Art\.?|Art|Section|Sec\.?|Sec|§|Regulation|Directive|GDPR|CPRA|SCC|BCR|DPIA|TIA)\s*$/i;

/** 数字前是否紧邻法条引用关键词 */
function isLegalArticlePrefix(textBefore: string): boolean {
  return LEGAL_REF_PATTERN.test(textBefore);
}

/** 数字后是否跟着版本号/小数模式（如 28.5、2.1.0）—— 拒绝拆分 */
function isDecimalOrVersion(digit: string, textAfter: string): boolean {
  // digit 后紧跟 .\d → 小数或版本号的一部分，不拆
  return /^\.[\d]/.test(textAfter);
}

/** 数字是否属于 "第X条"、"第 X 条" 等中文法条前缀 —— 拒绝拆分 */
function isChineseArticleNumber(line: string, matchIndex: number): boolean {
  const before = line.slice(0, matchIndex);
  return /第\s*$/.test(before);
}

// ---------------------------------------------------------------------------
// explodePackedLine — 将紧密排列的文本拆成独立行
//
// 安全规则（无条件拆分，因为这些模式在中文法律文本中几乎永远是编号）：
//   1. 【依据：...】
//   2. 第X章
//   3. 纯中文数字 + 、（一、二、三...）
//   4. 全角括号中文数字 （一）（二）...
//
// 条件规则（需要法条上下文检查，宁愿漏拆也不能错拆法条号）：
//   5. 阿拉伯数字 + 、（如 1、 28、）—— 需检查前面不是法条引用
//   6. (数字) / 数字.  —— 需检查前面不是法条引用 + 排除小数
// ---------------------------------------------------------------------------

const PURE_CHINESE_NUM = /[一二三四五六七八九十百千万零〇两]+/;

function explodePackedLine(line: string): string[] {
  // 1. 先拆【依据：...】
  let next = line.replace(/\s*(【依据：[^】]+】)/g, "\n$1");

  // 已结构化 → 不拆
  if (isMarkdownStructured(next)) {
    return next.split("\n").map((s) => s.trim()).filter(Boolean);
  }

  // --- 安全拆分（无条件）---
  // 第X章
  next = next.replace(
    /(?<!\n)(第[一二三四五六七八九十百千万零〇两0-9]+章)/g,
    "\n$1",
  );
  // 纯中文数字 + 、（不包含阿拉伯数字，避免与法条号冲突）
  next = next.replace(
    /(?<!\n)([一二三四五六七八九十百千万零〇两]+、)/g,
    "\n$1",
  );
  // 全角括号中文数字
  next = next.replace(
    /(?<!\n)(（[一二三四五六七八九十百千万零〇两0-9]+）)/g,
    "\n$1",
  );

  // --- 条件拆分（需上下文检查）---
  // 阿拉伯数字 + 、（如 1、 28、）
  next = next.replace(
    /(?<!\n)(\d+、)(?=\S)/g,
    (match, _m, offset) => {
      const before = next.slice(0, offset);
      // 法条上下文 → 不拆（如 Article 28、）
      if (isLegalArticlePrefix(before)) return match;
      // "第 X 条" 模式 → 不拆
      if (isChineseArticleNumber(next, offset)) return match;
      return `\n${match}`;
    },
  );

  // (数字) 或 数字.  —— 需排除小数和法条上下文
  next = next.replace(
    /(?<!\n)(\(?\d+\)|\d+\.)\s*(?=\S)/g,
    (match, marker, offset) => {
      const before = next.slice(0, offset);
      const after = next.slice(offset + match.length);
      // 法条上下文 → 不拆
      if (isLegalArticlePrefix(before)) return match;
      // "第 X 条" 模式 → 不拆
      if (isChineseArticleNumber(next, offset)) return match;
      // 小数/版本号 → 不拆
      if (isDecimalOrVersion(match.replace(/[().]/g, ""), after)) return match;
      return `\n${marker} `;
    },
  );

  return next.split("\n").map((s) => s.trim()).filter(Boolean);
}

// ---------------------------------------------------------------------------
// classifyLine
// ---------------------------------------------------------------------------

function classifyLine(line: string): string {
  if (/^【依据：[^】]+】$/.test(line)) return line;
  if (line.startsWith("|")) return line;
  if (isMarkdownStructured(line)) return line;

  // 中文章节
  if (/^第[一二三四五六七八九十百千万零〇两0-9]+章\b/.test(line)) return `# ${line}`;

  // 纯中文数字 + 、→ 二级标题（安全，因为中文数字不会出现在法条号里）
  if (/^[一二三四五六七八九十百千万零〇两]+、/.test(line)) return `## ${line}`;

  // 全角括号中文数字 → 三级标题
  if (/^（[一二三四五六七八九十百千万零〇两0-9]+）/.test(line)) return `### ${line}`;

  // 阿拉伯数字 + 、→ 只做有序列表，不升级为标题
  // （因为可能是法条号 "28、" 被 LLM 原生放在行首的情况）
  const chineseDotOrder = line.match(/^(\d+)、\s*(.*)$/);
  if (chineseDotOrder) {
    return `${chineseDotOrder[1]}. ${chineseDotOrder[2] || ""}`.trim();
  }

  // (数字) 或 数字. → 有序列表
  const ordered = line.match(/^(?:\(?(\d+)\)|(\d+)\.)\s*(.*)$/);
  if (ordered) {
    const no = ordered[1] || ordered[2] || "1";
    const content = ordered[3] || "";
    return `${no}. ${content}`.trim();
  }

  return line;
}

// ---------------------------------------------------------------------------
// lineKind
// ---------------------------------------------------------------------------

function lineKind(line: string): "heading" | "list" | "basis" | "table" | "paragraph" {
  if (/^【依据：[^】]+】$/.test(line)) return "basis";
  if (line.startsWith("|")) return "table";
  if (/^#{1,6}\s/.test(line)) return "heading";
  if (/^(?:[-*]\s|\d+\.\s)/.test(line)) return "list";
  return "paragraph";
}

// ---------------------------------------------------------------------------
// normalizeLegalMarkdown
// ---------------------------------------------------------------------------

export function normalizeLegalMarkdown(value: string): string {
  const normalized = normalizeHeadingSpacing(
    value.replace(/\r\n?/g, "\n").replace(/ /g, " ").replace(/　/g, " "),
  );
  const lines = normalized
    .split("\n")
    .flatMap((line) => {
      const trimmed = line.trim();
      if (!trimmed) return [""];
      return explodePackedLine(trimmed).map(classifyLine);
    });

  const parts: string[] = [];
  let prevKind: ReturnType<typeof lineKind> | null = null;
  let sawBlankLine = false;

  for (const line of lines) {
    if (!line) {
      sawBlankLine = true;
      continue;
    }

    const kind = lineKind(line);
    if (parts.length > 0) {
      let separator = "\n\n";
      if (!sawBlankLine && kind === "paragraph" && prevKind === "paragraph") separator = "\n";
      if (!sawBlankLine && kind === "list" && prevKind === "list") separator = "\n";
      if (!sawBlankLine && kind === "table" && prevKind === "table") separator = "\n";
      parts.push(separator);
    }
    parts.push(line);
    prevKind = kind;
    sawBlankLine = false;
  }

  return parts.join("").replace(/\n{3,}/g, "\n\n").trim();
}
