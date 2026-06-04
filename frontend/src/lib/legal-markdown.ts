function isMarkdownStructured(line: string): boolean {
  return /^(?:#{1,6}\s|[-*]\s|\d+\.\s|>\s|\|)/.test(line);
}

function normalizeHeadingSpacing(value: string): string {
  return value
    .replace(/^(#{1,6})([^\s#])/gm, "$1 $2")
    .replace(/^(\d+)\)\s+/gm, "$1. ")
    .replace(/^\s*•\s+/gm, "- ");
}

function splitPipeRow(line: string): string[] {
  const normalized = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  return normalized.split("|").map((cell) => cell.trim());
}

function isMarkdownDelimiterLine(line: string): boolean {
  const cells = splitPipeRow(line);
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function looksLikePipeTableLine(line: string): boolean {
  if (!line.includes("|")) return false;
  if (isMarkdownDelimiterLine(line)) return true;
  const cells = splitPipeRow(line);
  return cells.length >= 3 && cells.every((cell) => cell.length > 0);
}

function looksLikeReviewMatrix(rows: string[][]): boolean {
  return rows.every((cells) => {
    if (cells.length < 5) return false;
    const item = cells[0] ?? "";
    const risk = cells[2] ?? "";
    return /^\d+-[A-Z]\d+$/i.test(item) && /风险\s*=/.test(risk);
  });
}

function inferPipeTableHeaders(rows: string[][]): string[] | null {
  const width = rows[0]?.length ?? 0;
  if (width < 3) return null;
  if (looksLikeReviewMatrix(rows)) {
    if (width === 6) return ["检查项", "主题", "风险", "现状", "整改建议", "本轮重点"];
    if (width === 5) return ["检查项", "主题", "风险", "现状", "整改建议"];
  }
  if (width === 3) {
    return ["来源", "定位", "备注"];
  }
  return Array.from({ length: width }, (_, index) => `列${index + 1}`);
}

function convertPipeTableBlock(lines: string[]): string[] {
  if (lines.length < 2) return lines;
  if (!lines.every(looksLikePipeTableLine)) return lines;

  const rows = lines.map(splitPipeRow);
  const width = rows[0]?.length ?? 0;
  if (width < 3 || rows.some((cells) => cells.length !== width)) return lines;

  if (isMarkdownDelimiterLine(lines[1] ?? "")) {
    return lines.map((line) => {
      const cells = splitPipeRow(line);
      return `| ${cells.join(" | ")} |`;
    });
  }

  const headers = inferPipeTableHeaders(rows);
  if (!headers || headers.length !== width) return lines;

  const delimiter = headers.map(() => "---");
  return [
    `| ${headers.join(" | ")} |`,
    `| ${delimiter.join(" | ")} |`,
    ...rows.map((cells) => `| ${cells.join(" | ")} |`),
  ];
}

function normalizePipeTables(value: string): string {
  const lines = value.split("\n");
  const output: string[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index] ?? "";
    if (!looksLikePipeTableLine(line.trim())) {
      output.push(line);
      index += 1;
      continue;
    }

    const block: string[] = [];
    let nextIndex = index;
    while (nextIndex < lines.length) {
      const current = lines[nextIndex] ?? "";
      if (!looksLikePipeTableLine(current.trim())) break;
      block.push(current.trim());
      nextIndex += 1;
    }

    output.push(...convertPipeTableBlock(block));
    index = nextIndex;
  }

  return output.join("\n");
}

// ---------------------------------------------------------------------------
// 法条引用上下文检测
//
// 目的：避免把 Article 28、Art.28、Sec. 3.2.1、第28条 等法条名称
// 错误拆成 "Article 2" + "8、..."。
//
// 覆盖的典型模式：
//   Article 28、         → 关键词紧邻数字
//   Sec. 3.2.1、         → 关键词 + 条款号链
//   Directive 95/46/EC Art.29、 → 多层引用
//   第28条、             → 中文法条
//   第 28 条、           → 中文法条（带空格）
// ---------------------------------------------------------------------------


/**
 * 检查匹配位置之前的文本是否属于法条引用上下文。
 * 匹配 "法条关键词 + 可选的条款号链条（如 3.2.1）"。
 * 例如 "Sec. 3.2." 中 3.2.1 的 1 被匹配时，before = "Sec. 3.2." 应通过检查。
 */
function isLegalNumberContext(before: string): boolean {
  return (
    // 英文法条引用：关键词 + 可选数字链 + 可选尾部 dot（如 "Sec. 3.2."）
    /(?:Article|Art\.?|Art|Section|Sec\.?|Sec|§|Regulation|Directive|GDPR|CPRA|SCC|BCR|DPIA|TIA)(?:\s*\d+(?:[.]\d+)*)*[.]?\s*$/i.test(before) ||
    // 中文法条引用："第X条"、"第 X 条"
    /第\s*\d*\s*条?\s*$/.test(before)
  );
}

/**
 * 版本号前缀检测。数字前如果是 v/V → 版本号，不拆。
 * 例如 v2.1.0 中的 2. 不拆。
 */
function isVersionPrefix(before: string): boolean {
  return /[vV]$/.test(before);
}

/**
 * 数字后是否紧跟 digit → 说明是小数或版本号的一部分，不拆。
 * 例如 28.5%、3.2.1 中的 3. 和 2.。
 */
function followedByDigit(after: string): boolean {
  return /^\d/.test(after);
}

// ---------------------------------------------------------------------------
// explodePackedLine — 将紧密排列的文本拆成独立行
//
// 安全规则（无条件拆分）：
//   1. 【依据：...】
//   2. 第X章
//   3. 纯中文数字 + 、（一、二、三...）—— 纯中文数字不会出现在法条号里
//   4. 全角括号数字 （一）（二）...
//
// 条件规则（需法条上下文检查）：
//   5. 阿拉伯数字 + 、（如 1、 28、）
//   6. (数字) / 数字.（如 (1) 或 1.）
//
// 原则：宁愿漏拆一个真标题，也不能错拆一个法条号。
// ---------------------------------------------------------------------------

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
  // 纯中文数字 + 、（不包含阿拉伯数字）
  next = next.replace(
    /(?<!\n)([一二三四五六七八九十百千万零〇两]+、)/g,
    "\n$1",
  );
  // 全角括号数字
  next = next.replace(
    /(?<!\n)(（[一二三四五六七八九十百千万零〇两0-9]+）)/g,
    "\n$1",
  );

  // --- 条件拆分：阿拉伯数字 + 、（如 1、 28、）---
  next = next.replace(/(?<!\n)(\d+、)(?=\S)/g, (match, _m, offset) => {
    const before = next.slice(0, offset);
    if (isLegalNumberContext(before)) return match;
    return `\n${match}`;
  });

  // --- 条件拆分：(数字) 或 数字. ---
  next = next.replace(
    /(?<!\n)(\(?\d+\)|\d+\.)\s*(?=\S)/g,
    (match, marker, offset) => {
      const before = next.slice(0, offset);
      const after = next.slice(offset + match.length);

      // 版本号前缀（v2.1.0）→ 不拆
      if (isVersionPrefix(before)) return match;
      // 法条引用上下文 → 不拆
      if (isLegalNumberContext(before)) return match;
      // 后跟数字 → 小数/条款号链/版本号的一部分 → 不拆
      if (followedByDigit(after)) return match;

      return `\n${marker} `;
    },
  );

  return next.split("\n").map((s) => s.trim()).filter(Boolean);
}

// ---------------------------------------------------------------------------
// classifyLine — 将拆好的行映射为 markdown 结构
//
// 关键：阿拉伯数字 + 、只做有序列表，绝不升级为标题。
// 因为 LLM 可能在行首直接输出 "28、..." 这种法条号片段。
// ---------------------------------------------------------------------------

function classifyLine(line: string): string {
  if (/^【依据：[^】]+】$/.test(line)) return line;
  if (line.startsWith("|")) return line;
  if (isMarkdownStructured(line)) return line;

  // 中文章节
  if (/^第[一二三四五六七八九十百千万零〇两0-9]+章\b/.test(line)) return `# ${line}`;

  // 纯中文数字 + 、→ h2（安全，中文数字不会是法条号的一部分）
  if (/^[一二三四五六七八九十百千万零〇两]+、/.test(line)) return `## ${line}`;

  // 全角括号数字 → h3
  if (/^（[一二三四五六七八九十百千万零〇两0-9]+）/.test(line)) return `### ${line}`;

  // 阿拉伯数字 + 、→ 只做有序列表，绝不升级为标题
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
// normalizeLegalMarkdown — 对外入口
// ---------------------------------------------------------------------------

export function normalizeLegalMarkdown(value: string): string {
  const normalized = normalizePipeTables(normalizeHeadingSpacing(
    value.replace(/\r\n?/g, "\n").replace(/ /g, " ").replace(/　/g, " "),
  ));
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
