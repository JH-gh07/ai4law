import type { CnFlowRecipientRole } from "../types";

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

export const splitCsv = (value: string): string[] =>
  value.split(/[,，\n]/).map((item) => item.trim()).filter((item) => item.length > 0);

export const hasText = (value: string, minLength = 2): boolean => value.trim().length >= minLength;

export const basenameFromPath = (path: string): string => {
  const normalized = path.replace(/\\/g, "/");
  const chunks = normalized.split("/");
  return chunks[chunks.length - 1] || "attachment.txt";
};

export const inferAttachmentFormat = (value: string): "doc" | "docx" | "pdf" | "txt" | "md" | "json" | "csv" => {
  const suffix = value.split(".").pop()?.toLowerCase();
  if (suffix === "doc") return "doc";
  if (suffix === "docx") return "docx";
  if (suffix === "pdf") return "pdf";
  if (suffix === "md") return "md";
  if (suffix === "json") return "json";
  if (suffix === "csv") return "csv";
  return "txt";
};

export const inferDocxPdfFormat = (value: string): "docx" | "pdf" | null => {
  const suffix = value.split(".").pop()?.toLowerCase();
  return suffix === "docx" || suffix === "pdf" ? suffix : null;
};

export const inferCnFlowAttachmentFormat = (value: string): "xlsx" | "csv" | "docx" | "pdf" | null => {
  const suffix = value.split(".").pop()?.toLowerCase();
  return suffix === "xlsx" || suffix === "csv" || suffix === "docx" || suffix === "pdf" ? suffix : null;
};

export const inferCpraAttachmentFormat = (value: string): "docx" | "pdf" | "xlsx" | "csv" | null => {
  const suffix = value.split(".").pop()?.toLowerCase();
  return suffix === "docx" || suffix === "pdf" || suffix === "xlsx" || suffix === "csv" ? suffix : null;
};

export const isValidUrl = (value: string): boolean => /^https?:\/\/\S+$/i.test(value.trim());

export const parseRecipientRows = (raw: string): Array<{
  entity_name: string;
  country_region: string;
  entity_role: CnFlowRecipientRole;
  is_restricted_party: boolean;
}> => raw.split("\n").map((line) => line.trim()).filter(Boolean).flatMap((line) => {
  const [name = "", country = "", role = "", restricted = ""] = line.split(/[,\|]/).map((part) => part.trim());
  if (!hasText(name) || !hasText(country)) return [];
  const entityRole: CnFlowRecipientRole =
    role === "controller" || role === "subprocessor" || role === "affiliate" || role === "vendor"
      ? role
      : "processor";
  return [{
    entity_name: name,
    country_region: country,
    entity_role: entityRole,
    is_restricted_party: ["yes", "true", "1", "是", "受限", "high"].includes(restricted.toLowerCase()),
  }];
});

export const toBcrScore = (value: string): "compliant" | "partial" | "non_compliant" => {
  const length = value.trim().length;
  if (length >= 48) return "compliant";
  if (length >= 16) return "partial";
  return "non_compliant";
};

export const composeBcrFinding = (
  score: "compliant" | "partial" | "non_compliant",
  evidence: string,
): string => {
  if (score === "compliant") return `已覆盖核心要求：${evidence}`;
  if (score === "partial") return `条款已涉及但表述不充分：${evidence}`;
  return `尚未形成可执行机制：${evidence}`;
};
