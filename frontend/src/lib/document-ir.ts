/**
 * TypeScript mirror of the v4 DocumentIR layout contract.
 *
 * These types correspond 1:1 to the Pydantic models in
 * `backend/common/reporting/schema/`. The frontend never persists IR; it only
 * receives it from the artifact preview API and holds it in component memory
 * (task067 T04).
 */

export type RiskLevel = "HIGH" | "MEDIUM" | "LOW";
export type FindingStatus = "OPEN_BLOCKING" | "OPEN" | "RESOLVED" | "WONT_FIX";
export type NumberingStyle = "decimal" | "lower_alpha" | "lower_roman" | "none";

export type BlockType =
  | "paragraph"
  | "claim"
  | "list"
  | "table"
  | "warning"
  | "key_value"
  | "finding_summary"
  | "finding_detail"
  | "finding_reference"
  | "clause_group"
  | "page_break"
  | "citation_note";

interface BlockBase {
  block_id: string;
}

export interface ParagraphBlock extends BlockBase {
  type: "paragraph";
  text: string;
  fact_refs?: string[];
  issue_refs?: string[];
}

export interface ClaimBlock extends BlockBase {
  type: "claim";
  text: string;
  citation_refs?: string[];
  fact_refs?: string[];
  issue_refs?: string[];
  finding_ref?: string | null;
  verification?: string;
  verification_reason?: string;
}

export interface ListItemNode {
  text: string;
  children?: ListItemNode[];
}

export interface ListBlock extends BlockBase {
  type: "list";
  ordered?: boolean;
  items: ListItemNode[];
}

export interface TableBlock extends BlockBase {
  type: "table";
  headers: string[];
  rows: string[][];
}

export interface WarningBlock extends BlockBase {
  type: "warning";
  text: string;
  severity?: "info" | "warning" | "error" | "fatal";
}

export interface KeyValueItem {
  label: string;
  value: string;
}

export interface KeyValueBlock extends BlockBase {
  type: "key_value";
  items: KeyValueItem[];
  columns?: number;
}

export interface FindingSummaryBlock extends BlockBase {
  type: "finding_summary";
  finding_refs: string[];
  columns?: string[];
}

export interface FindingDetailBlock extends BlockBase {
  type: "finding_detail";
  finding_ref: string;
  field_order?: string[];
}

export interface FindingReferenceBlock extends BlockBase {
  type: "finding_reference";
  finding_ref: string;
  note?: string;
}

export interface ClauseNode {
  node_id: string;
  label?: string | null;
  text: string;
  numbering_style?: NumberingStyle;
  citation_refs?: string[];
  children?: ClauseNode[];
}

export interface ClauseGroupBlock extends BlockBase {
  type: "clause_group";
  title: string;
  clauses: ClauseNode[];
}

export interface PageBreakBlock extends BlockBase {
  type: "page_break";
  reason: string;
}

export interface CitationNoteBlock extends BlockBase {
  type: "citation_note";
  citation_refs: string[];
}

export type Block =
  | ParagraphBlock
  | ClaimBlock
  | ListBlock
  | TableBlock
  | WarningBlock
  | KeyValueBlock
  | FindingSummaryBlock
  | FindingDetailBlock
  | FindingReferenceBlock
  | ClauseGroupBlock
  | PageBreakBlock
  | CitationNoteBlock;

export interface FindingBasis {
  citation_ref?: string | null;
  label: string;
  rationale?: string;
  is_primary?: boolean;
}

export interface FindingRecord {
  finding_id: string;
  requirement_id: string;
  title: string;
  risk_level?: RiskLevel;
  risk_score?: number;
  statement: string;
  legal_basis?: string[];
  recommendation?: string;
  suggested_revision?: string | null;
  facts_uncertain?: boolean;
  review_confidence?: number;
  citation_refs?: string[];
  status?: FindingStatus;
  primary_display_count?: number;
  basis_entries?: FindingBasis[];
}

export interface ActionRecord {
  action_id: string;
  finding_refs: string[];
  title: string;
  description?: string;
  priority?: "P0" | "P1" | "P2" | "P3";
  status?: "OPEN" | "DONE";
}

export interface CitationRecord {
  citation_id: string;
  source_id: string;
  source_type: string;
  title: string;
  locator?: { article?: string | null; paragraph?: string | null; item?: string | null } | null;
  authority_level?: string;
  binding_force?: string;
  can_enter_external_report?: boolean;
}

export interface ReportMetadata {
  title: string;
  short_title?: string;
  company_name?: string;
  jurisdiction?: string;
  locale?: string;
  report_date?: string;
  report_id?: string;
}

export interface SectionIR {
  section_id: string;
  title: string;
  level: number;
  ordinal?: string | null;
  purpose?: string | null;
  blocks: Block[];
}

export interface DocumentIR {
  schema_version: string;
  document_id: string;
  report_type: string;
  identity?: unknown;
  lifecycle?: unknown;
  findings: FindingRecord[];
  actions?: ActionRecord[];
  citations?: CitationRecord[];
  render_contract?: unknown;
  metadata: ReportMetadata;
  sections: SectionIR[];
  diagnostics?: unknown[];
  provenance?: { generated_at?: string };
  compiler_version: string;
  prompt_version: string;
  template_version: string;
  model: string;
  migrated_from_schema?: string | null;
}

/** Coarse runtime check: an arbitrary JSON object must not pass as IR. */
export function isDocumentIR(value: unknown): value is DocumentIR {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
  const record = value as Record<string, unknown>;
  return (
    typeof record.schema_version === "string" &&
    (record.schema_version === "4.0" || record.schema_version === "3.0") &&
    typeof record.document_id === "string" &&
    Array.isArray(record.sections) &&
    Array.isArray(record.findings)
  );
}
