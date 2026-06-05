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
// Pipe table normalization
// ---------------------------------------------------------------------------

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
// explodePackedLine — 仅保留安全组的拆行规则
//
// 已删除的规则（原因：假阳性太高，永远补不完）：
//   · 阿拉伯数字 + 、（会把 Article 28、中的 28、拆出来）
//   · (数字) / 数字.（会把 §1798.100(b) 中的 100. 拆出来）
//
// 保留的规则（中文法律文本专用，零假阳性）：
//   1. 【依据：...】 → 独立行（后端经常内嵌在段中）
//   2. 第X章          → 独立行
//   3. 纯中文数字 + 、 → 独立行（不含 0-9，不与法条号冲突）
//   4. （全角数字）     → 独立行
//
// 策略：LLM 的输出已经高度结构化（# h1、## h2、空行分段），
// 前端不应替 LLM 做段落拆分。分段质量由 LLM prompt 控制。
// ---------------------------------------------------------------------------

function explodePackedLine(line: string): string[] {
  // 1. 拆【依据：...】— 后端经常把依据块内嵌在段中
  let next = line.replace(/\s*(【依据：[^】]+】)/g, "\n$1");

  // 已结构化 → 不拆
  if (isMarkdownStructured(next)) {
    return next.split("\n").map((s) => s.trim()).filter(Boolean);
  }

  // 2. 第X章
  next = next.replace(
    /(?<!\n)(第[一二三四五六七八九十百千万零〇两0-9]+章)/g,
    "\n$1",
  );
  // 3. 纯中文数字 + 、
  next = next.replace(
    /(?<!\n)([一二三四五六七八九十百千万零〇两]+、)/g,
    "\n$1",
  );
  // 4. 全角括号数字
  next = next.replace(
    /(?<!\n)(（[一二三四五六七八九十百千万零〇两0-9]+）)/g,
    "\n$1",
  );

  return next.split("\n").map((s) => s.trim()).filter(Boolean);
}

// ---------------------------------------------------------------------------
// classifyLine — 将拆好的行映射为 markdown 角色
//
// 只处理 LLM 输出中自然出现在行首的模式（# / - / 第X章 / 一、/ （一））。
// 不再对行中出现的阿拉伯数字做任何角色分配。
// ---------------------------------------------------------------------------

function classifyLine(line: string): string {
  if (/^【依据：[^】]+】$/.test(line)) return line;
  if (line.startsWith("|")) return line;
  if (isMarkdownStructured(line)) return line;

  // 中文章节 → h1
  if (/^第[一二三四五六七八九十百千万零〇两0-9]+章\b/.test(line)) return `# ${line}`;

  // 纯中文数字 + 、→ h2
  if (/^[一二三四五六七八九十百千万零〇两]+、/.test(line)) return `## ${line}`;

  // 全角括号数字 → h3
  if (/^（[一二三四五六七八九十百千万零〇两0-9]+）/.test(line)) return `### ${line}`;

  return line;
}

// ---------------------------------------------------------------------------
// lineKind — 行角色分类（用于段间距拼装）
// ---------------------------------------------------------------------------

function lineKind(line: string): "heading" | "list" | "basis" | "table" | "paragraph" {
  if (/^【依据：[^】]+】$/.test(line)) return "basis";
  if (line.startsWith("|")) return "table";
  if (/^#{1,6}\s/.test(line)) return "heading";
  if (/^(?:[-*]\s|\d+\.\s)/.test(line)) return "list";
  return "paragraph";
}

// ---------------------------------------------------------------------------
// normalizeFallbackMarkdown — 对外入口
// ---------------------------------------------------------------------------

export function normalizeFallbackMarkdown(value: string): string {
  const normalized = normalizePipeTables(
    normalizeHeadingSpacing(
      value.replace(/\r\n?/g, "\n").replace(/ /g, " ").replace(/　/g, " "),
    ),
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
