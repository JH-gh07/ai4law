import type { ModuleRequestMap } from "../../../api/api-contract";
import {
  basenameFromPath,
  inferCnFlowAttachmentFormat,
  parseRecipientRows,
  splitCsv,
  type CnFlowFormValues,
  type DocumentReviewFormValues,
} from "../model";
import { requireAllowedValue, requireFileExtensions, requireText } from "./common";

const DOCUMENT_TYPES = ["privacy_policy", "scc_contract", "dpa", "other"] as const;
const REVIEW_FILE_EXTENSIONS = ["txt", "md", "json", "csv", "pdf", "docx"] as const;
const CN_FLOW_RECIPIENT_ROLES = ["processor", "controller", "subprocessor", "affiliate", "vendor"] as const;
const CN_FLOW_FILE_EXTENSIONS = ["xlsx", "csv", "docx", "pdf"] as const;

export type CnFlowResolvedFiles = {
  dataInventory: string[];
  entityInventory: string[];
  supporting: string[];
};

function trimOr(value: string, fallback: string): string {
  const trimmed = value.trim();
  return trimmed.length >= 2 ? trimmed : fallback;
}

export function buildDocumentReviewPayload(
  values: DocumentReviewFormValues,
  resolvedFilePaths: string[],
): ModuleRequestMap["review"] {
  requireText(values.publisher_entity || values.company_name, "publisher_entity or company_name");
  requireText(values.document_title, "document_title");
  requireText(values.review_focus, "review_focus");
  requireAllowedValue(values.document_type, "document_type", DOCUMENT_TYPES);
  if (resolvedFilePaths.length === 0) {
    throw new Error("uploaded_files is required");
  }
  requireFileExtensions(resolvedFilePaths, REVIEW_FILE_EXTENSIONS);

  return {
    uploaded_files: [...resolvedFilePaths],
    document_type: values.document_type,
    review_focus: values.review_focus.trim(),
    scenario_context: {
      company_name: trimOr(values.publisher_entity || values.company_name, ""),
      document_title: values.document_title.trim(),
      document_version: values.document_version.trim(),
      publisher_entity: trimOr(values.publisher_entity, ""),
      receiver_name: trimOr(values.receiver_name, ""),
      receiver_country: trimOr(values.receiver_country, ""),
      transfer_purpose: values.transfer_purpose.trim(),
      pii_count: Math.max(0, values.pii_count),
      spi_count: Math.max(0, values.spi_count),
      has_scc_draft: values.has_scc_draft,
      review_focus: values.review_focus.trim(),
    },
    review_config: {
      review_depth: "standard",
      max_llm_clauses: 20,
      enable_cross_document_check: false,
    },
  };
}

export function buildCnFlowPayload(
  values: CnFlowFormValues,
  resolvedFiles: CnFlowResolvedFiles,
): ModuleRequestMap["cn_flow"] {
  requireText(values.company_name, "company_name");
  requireText(values.transfer_purpose, "transfer_purpose");
  requireText(values.transfer_chain, "transfer_chain");
  requireText(values.primary_recipient_name, "primary_recipient_name");
  requireText(values.primary_recipient_country, "primary_recipient_country");
  requireAllowedValue(values.primary_recipient_role, "primary_recipient_role", CN_FLOW_RECIPIENT_ROLES);
  const dataCategories = splitCsv(values.data_categories);
  if (dataCategories.length === 0) {
    throw new Error("data_categories is required");
  }
  if (resolvedFiles.dataInventory.length === 0 || resolvedFiles.entityInventory.length === 0) {
    throw new Error("data_inventory and entity_inventory attachments are required");
  }

  const attachments = [
    ...resolvedFiles.dataInventory.map((path) => ({ path, role: "data_inventory" as const })),
    ...resolvedFiles.entityInventory.map((path) => ({ path, role: "entity_inventory" as const })),
    ...resolvedFiles.supporting.map((path) => ({ path, role: "supporting_material" as const })),
  ].map(({ path, role }) => {
    requireFileExtensions([path], CN_FLOW_FILE_EXTENSIONS);
    return {
      file_role: role,
      file_name: basenameFromPath(path),
      file_format: inferCnFlowAttachmentFormat(path)!,
      storage_uri: path,
    };
  });

  return {
    company_name: values.company_name.trim(),
    transfer_purpose: [
      values.transfer_purpose.trim(),
      values.necessity_justification ? `必要性：${values.necessity_justification}` : "",
      values.data_volume_note ? `规模说明：${values.data_volume_note}` : "",
      values.internal_access_note ? `内部访问风险：${values.internal_access_note}` : "",
    ].filter((item) => item.length > 0).join("；"),
    data_categories: dataCategories,
    sensitive_data_flags: splitCsv(values.sensitive_data_flags),
    recipient_entities: [
      {
        entity_name: values.primary_recipient_name.trim(),
        country_region: values.primary_recipient_country.trim(),
        entity_role: values.primary_recipient_role,
        is_restricted_party: values.primary_recipient_restricted,
      },
      ...parseRecipientRows(values.additional_recipients),
    ],
    transfer_chain: values.transfer_chain.trim(),
    attachments,
  };
}
