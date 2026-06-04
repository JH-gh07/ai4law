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

function isLegalNumberContext(before: string): boolean {
  return (
    /(?:Article|Art\.?|Art|Section|Sec\.?|Sec|§|Regulation|Directive|GDPR|CPRA|SCC|BCR|DPIA|TIA)(?:\s*\d+(?:[.]\d+)*)*[.]?\s*$/i.test(before) ||
    /第\s*\d*\s*条?\s*$/.test(before)
  );
}

function isVersionPrefix(before: string): boolean {
  return /[vV]$/.test(before);
}

function followedByDigit(after: string): boolean {
  return /^\d/.test(after);
}

function explodePackedLine(line: string): string[] {
  let next = line.replace(/\s*(【依据：[^】]+】)/g, "\n$1");

  if (isMarkdownStructured(next)) {
    return next.split("\n").map((s) => s.trim()).filter(Boolean);
  }

  next = next.replace(/(?<!\n)(第[一二三四五六七八九十百千万零〇两0-9]+章)/g, "\n$1");
  next = next.replace(/(?<!\n)([一二三四五六七八九十百千万零〇两]+、)/g, "\n$1");
  next = next.replace(/(?<!\n)(（[一二三四五六七八九十百千万零〇两0-9]+）)/g, "\n$1");

  next = next.replace(/(?<!\n)(\d+、)(?=\S)/g, (match, _m, offset) => {
    const before = next.slice(0, offset);
    if (isLegalNumberContext(before)) return match;
    return `\n${match}`;
  });

  next = next.replace(/(?<!\n)(\(?\d+\)|\d+\.)\s*(?=\S)/g, (match, marker, offset) => {
    const before = next.slice(0, offset);
    const after = next.slice(offset + match.length);
    if (isVersionPrefix(before)) return match;
    if (isLegalNumberContext(before)) return match;
    if (followedByDigit(after)) return match;
    return `\n${marker} `;
  });

  return next.split("\n").map((s) => s.trim()).filter(Boolean);
}

function classifyLine(line: string): string {
  if (/^【依据：[^】]+】$/.test(line)) return line;
  if (line.startsWith("|")) return line;
  if (isMarkdownStructured(line)) return line;
  if (/^第[一二三四五六七八九十百千万零〇两0-9]+章\b/.test(line)) return `# ${line}`;
  if (/^[一二三四五六七八九十百千万零〇两]+、/.test(line)) return `## ${line}`;
  if (/^（[一二三四五六七八九十百千万零〇两0-9]+）/.test(line)) return `### ${line}`;

  const chineseDotOrder = line.match(/^(\d+)、\s*(.*)$/);
  if (chineseDotOrder) {
    return `${chineseDotOrder[1]}. ${chineseDotOrder[2] || ""}`.trim();
  }

  const ordered = line.match(/^(?:\(?(\d+)\)|(\d+)\.)\s*(.*)$/);
  if (ordered) {
    const no = ordered[1] || ordered[2] || "1";
    const content = ordered[3] || "";
    return `${no}. ${content}`.trim();
  }

  return line;
}

function lineKind(line: string): "heading" | "list" | "basis" | "table" | "paragraph" {
  if (/^【依据：[^】]+】$/.test(line)) return "basis";
  if (line.startsWith("|")) return "table";
  if (/^#{1,6}\s/.test(line)) return "heading";
  if (/^(?:[-*]\s|\d+\.\s)/.test(line)) return "list";
  return "paragraph";
}

export function normalizeFallbackMarkdown(value: string): string {
  const normalized = normalizePipeTables(
    normalizeHeadingSpacing(value.replace(/\r\n?/g, "\n").replace(/ /g, " ").replace(/　/g, " ")),
  );
  const lines = normalized.split("\n").flatMap((line) => {
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
