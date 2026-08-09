/** Frontend fallback equivalent of backend normalize_legal_markdown_structure. */
/**
 * fallback-markdown.ts
 *
 * 这个文件定义了一个用于规范化 Markdown 文本的函数 `normalizeFallbackMarkdown`，以及一些辅助函数和类型。
 *
 * 函数：
 * - normalizeFallbackMarkdown: 接收一个字符串输入，返回规范化后的 Markdown 字符串。它会处理换行符、空格、章节标题、列表项等，并确保输出符合 Markdown 语法。
 *
 * 辅助函数：
 * - explodePackedLine: 将一行文本拆分为多个块，处理章节标题、列表项等。
 * - classifyBlock: 根据文本内容分类块的类型，如标题、列表项、表格行等。
 *
 * 类型：
 * - BlockKind: 定义了可能的块类型，包括 "basis"、"heading"、"list_item"、"table_row"、"table_rule" 和 "paragraph"。
 */
type BlockKind = "basis" | "heading" | "list_item" | "table_row" | "table_rule" | "paragraph";

const markdownPrefix = /^\s*(?:#{1,6}\s|[*_]{2,3}[^*_\s]|[-*]\s|\d+\.\s|>\s|\|)/;
const chapterLabel = /^第[一二三四五六七八九十百千万零〇两0-9]+章(?:\s|$)/;
const sectionLabel = /^[一二三四五六七八九十百千万零〇两0-9]+、/;
const subsectionLabel = /^（[一二三四五六七八九十百千万零〇两0-9]+）/;
const orderedItem = /^(?:\(?(\d+)\)|(\d+)[、.])\s*/;
const basisBlock = /^【依据：[^】]+】$/;

function explodePackedLine(line: string): string[] {
  let next = line.replace(/\s*(【依据：[^】]+】)/g, "\n$1");
  if (!markdownPrefix.test(next)) {
    next = next
      .replace(/(?<!\n)(第[一二三四五六七八九十百千万零〇两0-9]+章)/g, "\n$1")
      // “统一、”“唯一、”“逐一、”“之一、” are prose, not section labels.
      .replace(/(?<!\n)(?<![统唯逐之])([一二三四五六七八九十百千万零〇两0-9]+、)/g, "\n$1")
      .replace(/(?<!\n)(（[一二三四五六七八九十百千万零〇两0-9]+）)/g, "\n$1")
      .replace(/(?<!\n)(\(?\d+\)|\d+[、.])\s*(?=\S)/g, "\n$1 ");
  }
  return next.split("\n").map((part) => part.trim()).filter(Boolean);
}

function classifyBlock(line: string): [BlockKind, string] {
  if (basisBlock.test(line)) return ["basis", line];
  if (line.startsWith("|")) {
    return [/^\|?[\s:|-]+\|?$/.test(line) ? "table_rule" : "table_row", line];
  }
  if (markdownPrefix.test(line)) {
    const stripped = line.trimStart();
    if (stripped.startsWith("#")) return ["heading", line];
    if (stripped.startsWith("|")) {
      return [/^\|?[\s:|-]+\|?$/.test(stripped) ? "table_rule" : "table_row", line];
    }
    if (/^(?:\d+\.\s|[-*]\s)/.test(stripped)) return ["list_item", line];
    return ["paragraph", line];
  }
  if (chapterLabel.test(line)) return ["heading", `# ${line}`];
  if (sectionLabel.test(line)) return ["heading", `## ${line}`];
  if (subsectionLabel.test(line)) return ["heading", `### ${line}`];

  const ordered = orderedItem.exec(line);
  if (ordered) {
    const number = ordered[1] ?? ordered[2] ?? "1";
    return ["list_item", `${number}. ${line.slice(ordered[0].length).trim()}`.trimEnd()];
  }
  return ["paragraph", line];
}

export function normalizeFallbackMarkdown(value: string): string {
  if (!value) return value;
  const normalized = value
    .replace(/\r\n?/g, "\n")
    .replace(/ /g, " ")
    .replace(/　/g, " ")
    .replace(/[ \t]+\n/g, "\n");
  const blocks = normalized
    .split("\n")
    .flatMap((line) => {
      const stripped = line.trim();
      return stripped ? explodePackedLine(stripped).map(classifyBlock) : [];
    });
  if (blocks.length === 0) return "";

  const output: string[] = [];
  let previous: BlockKind | null = null;
  for (const [kind, rendered] of blocks) {
    if (output.length > 0) {
      const compact =
        (kind === "list_item" && previous === "list_item") ||
        (kind === "table_row" && previous === "table_row") ||
        (kind === "table_row" && previous === "table_rule") ||
        (kind === "table_rule" && previous === "table_row") ||
        (kind === "table_rule" && previous === "table_rule");
      output.push(compact ? "\n" : "\n\n");
    }
    output.push(rendered);
    previous = kind;
  }
  return output.join("").replace(/\n{3,}/g, "\n\n").trim();
}
