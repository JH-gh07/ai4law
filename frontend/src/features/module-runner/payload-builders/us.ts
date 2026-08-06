import type { ModuleRequestMap } from "../../../api/api-contract";
import type {
  CpraFormValues,
  Us14117FormValues,
} from "../types";
import {
  basenameFromPath,
  inferCpraAttachmentFormat,
  isValidUrl,
  requireAllowedValue,
  requireFileExtensions,
  requireText,
} from "./common";

const US_14117_TRANSACTION_TYPES = [
  "vendor_agreement",
  "employment_agreement",
  "investment_agreement",
  "data_brokerage",
  "cooperative_research",
  "cloud_remote_access",
  "onward_transfer",
  "other",
] as const;
const US_14117_FILE_EXTENSIONS = ["txt", "md", "json", "csv", "pdf", "docx"] as const;
const CPRA_FILE_EXTENSIONS = ["docx", "pdf", "xlsx", "csv"] as const;

export type CpraResolvedFiles = {
  privacyPolicy: string[];
  rightsSop: string[];
  dataMap: string[];
  vendorList: string[];
  other: string[];
};

export function buildUs14117Payload(
  values: Us14117FormValues,
  resolvedFilePaths: string[],
): ModuleRequestMap["us_14117"] {
  requireText(values.company_name, "company_name");
  requireText(values.project_name, "project_name");
  requireText(values.transaction_description, "transaction_description");
  requireText(values.data_item_name, "data_item_name");
  requireText(values.entity_name, "entity_name");
  requireText(values.country_of_registration, "country_of_registration");
  requireAllowedValue(values.transaction_type, "transaction_type", US_14117_TRANSACTION_TYPES);
  requireFileExtensions(resolvedFilePaths, US_14117_FILE_EXTENSIONS);

  return {
    company_name: values.company_name.trim(),
    project_name: values.project_name.trim(),
    transaction_description: values.transaction_description.trim(),
    transaction_type: values.transaction_type,
    attachments: [...resolvedFilePaths],
    data_items: [{
      data_item_name: values.data_item_name.trim(),
      data_description: values.data_description.trim(),
      doj_data_category: values.doj_data_category,
      us_person_count: Math.max(0, values.us_person_count),
    }],
    recipient_entities: [{
      entity_name: values.entity_name.trim(),
      country_of_registration: values.country_of_registration.trim(),
      government_control: values.government_control,
      entity_role: values.entity_role,
    }],
    security_measures: values.security_measures_summary.trim()
      ? [{
        measure_name: values.security_measures_summary.trim().slice(0, 80),
        category: "access_control",
        status: "implemented",
        description: values.security_measures_summary.trim(),
      }]
      : [],
    onward_transfer: values.onward_transfer,
    onward_transfer_description: values.onward_transfer_description.trim(),
  };
}

export function buildCpraPayload(
  values: CpraFormValues,
  resolvedFiles: CpraResolvedFiles,
): ModuleRequestMap["cpra"] {
  requireText(values.company_name, "company_name");
  requireText(values.business_model, "business_model");
  requireText(values.data_lifecycle, "data_lifecycle");
  requireText(values.notice_and_consent, "notice_and_consent");
  requireText(values.consumer_rights_process, "consumer_rights_process");
  requireText(values.opt_out_and_sale_sharing, "opt_out_and_sale_sharing");
  if (values.privacy_policy_url.trim() && !isValidUrl(values.privacy_policy_url)) {
    throw new Error("privacy_policy_url must be an http(s) URL");
  }

  const uploadedAttachments = [
    ...resolvedFiles.privacyPolicy.map((path) => ({ path, role: "privacy_policy" as const })),
    ...resolvedFiles.rightsSop.map((path) => ({ path, role: "rights_sop" as const })),
    ...resolvedFiles.dataMap.map((path) => ({ path, role: "data_map" as const })),
    ...resolvedFiles.vendorList.map((path) => ({ path, role: "vendor_list" as const })),
    ...resolvedFiles.other.map((path) => ({ path, role: "other" as const })),
  ].map(({ path, role }) => {
    requireFileExtensions([path], CPRA_FILE_EXTENSIONS);
    return {
      file_role: role,
      file_name: basenameFromPath(path),
      file_format: inferCpraAttachmentFormat(path)!,
      storage_uri: path,
    };
  });
  const urlAttachments = values.privacy_policy_url.trim()
    ? [{
      file_role: "privacy_policy" as const,
      file_name: "privacy_policy_url",
      file_format: "url" as const,
      storage_uri: values.privacy_policy_url.trim(),
    }]
    : [];
  const attachments = [...urlAttachments, ...uploadedAttachments];
  if (attachments.length === 0) throw new Error("attachments is required");

  return {
    company_name: values.company_name.trim(),
    business_model: [values.business_model.trim(), values.dba_name ? `DBA：${values.dba_name}` : "", values.cpra_applicability_selfcheck ? `适用性：${values.cpra_applicability_selfcheck}` : "", values.review_focus ? `重点：${values.review_focus}` : ""].filter((item) => item.length > 0).join("；"),
    data_lifecycle: [values.data_lifecycle, values.data_categories ? `数据类别：${values.data_categories}` : "", values.spi_usage_summary ? `SPI使用：${values.spi_usage_summary}` : ""].filter((item) => item.trim()).join("；"),
    notice_and_consent: [values.notice_and_consent, values.privacy_policy_url.trim() ? `隐私政策：${values.privacy_policy_url.trim()}` : "", values.ui_dark_pattern_check ? `UI暗模式：${values.ui_dark_pattern_check}` : ""].filter((item) => item.trim()).join("；"),
    consumer_rights_process: [values.consumer_rights_process, values.identity_verification_method ? `身份验证：${values.identity_verification_method}` : "", values.rights_sla ? `SLA：${values.rights_sla}` : ""].filter((item) => item.trim()).join("；"),
    opt_out_and_sale_sharing: values.opt_out_and_sale_sharing.trim(),
    vendor_management: [values.vendor_management, values.spi_usage_summary ? `SPI限制：${values.spi_usage_summary}` : ""].filter((item) => item.trim()).join("；"),
    attachments,
  };
}
