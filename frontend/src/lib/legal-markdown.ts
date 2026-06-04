function isMarkdownStructured(line: string): boolean {
  return /^(?:#{1,6}\s|[-*]\s|\d+\.\s|>\s|\|)/.test(line);
}

function normalizeHeadingSpacing(value: string): string {
  return value
    .replace(/^(#{1,6})([^\s#])/gm, "$1 $2")
    .replace(/^(\d+)\)\s+/gm, "$1. ")
    .replace(/^\s*•\s+/gm, "- ");
}

function explodePackedLine(line: string): string[] {
  let next = line.replace(/\s*(【依据：[^】]+】)/g, "\n$1");
  if (!isMarkdownStructured(next)) {
    next = next
      .replace(/(?<!\n)(第[一二三四五六七八九十百千万零〇两0-9]+章)/g, "\n$1")
      .replace(/(?<!\n)([一二三四五六七八九十百千万零〇两0-9]+、)/g, "\n$1")
      .replace(/(?<!\n)(（[一二三四五六七八九十百千万零〇两0-9]+）)/g, "\n$1")
      .replace(/(?<!\n)(\(?\d+\)|\d+[、.])\s*(?=\S)/g, (_, marker: string) => `\n${marker} `);
  }
  return next.split("\n").map((item) => item.trim()).filter(Boolean);
}

function classifyLine(line: string): string {
  if (/^【依据：[^】]+】$/.test(line)) return line;
  if (line.startsWith("|")) return line;
  if (isMarkdownStructured(line)) return line;
  if (/^第[一二三四五六七八九十百千万零〇两0-9]+章\b/.test(line)) return `# ${line}`;
  if (/^[一二三四五六七八九十百千万零〇两0-9]+、/.test(line)) return `## ${line}`;
  if (/^（[一二三四五六七八九十百千万零〇两0-9]+）/.test(line)) return `### ${line}`;
  const ordered = line.match(/^(?:\(?(\d+)\)|(\d+)[、.])\s*(.*)$/);
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

export function normalizeLegalMarkdown(value: string): string {
  const normalized = normalizeHeadingSpacing(
    value.replace(/\r\n?/g, "\n").replace(/\u00a0/g, " ").replace(/\u3000/g, " "),
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
