import type { ModuleRequestMap } from "../../../api/api-contract";
import type {
  AssessmentFormValues,
  CnFlowFormValues,
  DiagnosisFormValues,
  DocumentReviewFormValues,
  PipiaFormValues,
} from "../types";
import {
  basenameFromPath,
  inferAttachmentFormat,
  inferCnFlowAttachmentFormat,
  parseRecipientRows,
  requireAllowedValue,
  requireFileExtensions,
  requireText,
  splitCsv,
} from "./common";

const DOCUMENT_TYPES = ["privacy_policy", "scc_contract", "dpa", "other"] as const;
const REVIEW_FILE_EXTENSIONS = ["txt", "md", "json", "csv", "pdf", "docx"] as const;
const CN_FLOW_RECIPIENT_ROLES = ["processor", "controller", "subprocessor", "affiliate", "vendor"] as const;
const CN_FLOW_FILE_EXTENSIONS = ["xlsx", "csv", "docx", "pdf"] as const;
const GENERAL_FILE_EXTENSIONS = ["doc", "docx", "pdf", "txt", "md", "json", "csv"] as const;
const PIPIA_ROUTE_TYPES = ["certification", "scc_filing", "hr_exemption"] as const;

function pipiaEvidenceValue(value: "yes" | "no" | "unknown"): boolean | null {
  return value === "yes" ? true : value === "no" ? false : null;
}

function buildPipiaPathEvidence(values: PipiaFormValues): NonNullable<ModuleRequestMap["pipia"]["path_evidence"]> {
  if (values.route_type === "scc_filing") {
    return {
      recipient_notice_complete: pipiaEvidenceValue(values.recipient_notice_complete),
      sensitive_information_classification_confirmed: pipiaEvidenceValue(values.sensitive_information_classification_confirmed),
      consent_evidence_complete: pipiaEvidenceValue(values.consent_evidence_complete),
      scc_required_clauses_complete: pipiaEvidenceValue(values.scc_required_clauses_complete),
    };
  }
  if (values.route_type === "hr_exemption") {
    return {
      hr_rules_lawfully_adopted: pipiaEvidenceValue(values.hr_rules_lawfully_adopted),
      employee_handbook_has_explicit_cross_border_terms: pipiaEvidenceValue(values.employee_handbook_has_explicit_cross_border_terms),
      collective_agreement_has_explicit_cross_border_terms: pipiaEvidenceValue(values.collective_agreement_has_explicit_cross_border_terms),
      recipient_privacy_policy_provided: pipiaEvidenceValue(values.recipient_privacy_policy_provided),
    };
  }
  return {
    certification_body_china_recognized: pipiaEvidenceValue(values.certification_body_china_recognized),
    certification_legal_obligation_citation_provided: pipiaEvidenceValue(values.certification_legal_obligation_citation_provided),
    contract_governing_law: values.contract_governing_law.trim(),
    contract_exclusive_jurisdiction: values.contract_exclusive_jurisdiction.trim(),
    china_data_subject_rights_terms_present: pipiaEvidenceValue(values.china_data_subject_rights_terms_present),
  };
}

export type CnFlowResolvedFiles = {
  dataInventory: string[];
  entityInventory: string[];
  supporting: string[];
};

function trimOr(value: string, fallback: string): string {
  const trimmed = value.trim();
  return trimmed.length >= 2 ? trimmed : fallback;
}

function valueAsText(values: DiagnosisFormValues, key: string): string {
  const value = values[key];
  if (typeof value === "string") return value;
  if (typeof value === "number") return String(value);
  return "";
}

function valueAsArray(values: DiagnosisFormValues, key: string): string[] {
  const value = values[key];
  if (Array.isArray(value)) return value.map((item) => String(item));
  if (typeof value !== "string" || value.trim().length === 0) return [];
  return value.split(/[,，\n]/).map((item) => item.trim()).filter((item) => item.length > 0);
}

export function buildDiagnosisPayload(values: DiagnosisFormValues): ModuleRequestMap["diagnosis"] {
  for (const field of ["m3_processes_personal_info", "m3_processes_important_data"]) {
    const value = valueAsText(values, field);
    if (value && value !== "yes" && value !== "no") {
      throw new Error(`${field} has an unsupported value: ${value}`);
    }
  }
  const personalInfoTypes = valueAsArray(values, "m3_personal_info_types");
  const sensitiveKeywords = ["身份证", "人脸", "指纹", "声纹", "健康", "金融", "未成年人", "精准位置"];
  const hasSensitivePi = personalInfoTypes.some((item) => sensitiveKeywords.some((key) => item.includes(key)));
  const volume = valueAsText(values, "m3_data_volume_range");
  const estimatedPiiCount =
    volume === "1000万条以上" ? 10000000 :
    volume === "100-1000万条" ? 2000000 :
    volume === "10-100万条" ? 300000 :
    volume === "10万条以下" ? 50000 : 0;
  const estimatedSpiCount = !hasSensitivePi ? 0 :
    volume === "1000万条以上" ? 20000 :
    volume === "100-1000万条" ? 12000 :
    volume === "10-100万条" ? 6000 : 1000;
  const personalInfoFlag = valueAsText(values, "m3_processes_personal_info");
  const importantDataFlag = valueAsText(values, "m3_processes_important_data");
  const companyNameRaw = valueAsText(values, "company_name").trim();
  const companyName = companyNameRaw.length >= 2 ? companyNameRaw : "未命名企业";

  return {
    company_name: companyName,
    control: true,
    answers: {
      q1_is_ciio: "unknown",
      q2_has_important_data: importantDataFlag === "yes" ? "yes" : importantDataFlag === "no" ? "no" : "unknown",
      q3_pii_count: personalInfoFlag === "yes" ? estimatedPiiCount : 0,
      q4_spi_count: personalInfoFlag === "yes" ? estimatedSpiCount : 0,
      q5_no_personal_info: personalInfoFlag === "no" && importantDataFlag === "no" ? "yes" : "no",
      q6_scenario: "other",
      q7_receiver_type: valueAsText(values, "m4_share_to_third_party") === "yes" ? "third_party" : "intra_group",
      q8_purpose: valueAsText(values, "m2_core_needs_other"),
      m1_enterprise_name: companyName,
      m1_industry: valueAsText(values, "m1_industry"),
      m1_business_channels: valueAsArray(values, "m1_business_channels"),
      m1_service_targets: valueAsText(values, "m1_service_targets"),
      m1_company_size: valueAsText(values, "m1_company_size"),
      m2_core_needs: valueAsArray(values, "m2_core_needs"),
      m2_had_compliance_issue: valueAsText(values, "m2_had_compliance_issue"),
      m2_issue_description: valueAsText(values, "m2_issue_description"),
      m2_deadline: valueAsText(values, "m2_deadline"),
      m3_processes_personal_info: personalInfoFlag,
      m3_personal_info_types: personalInfoTypes,
      m3_sensitive_info_types: personalInfoTypes.filter((item) => sensitiveKeywords.some((key) => item.includes(key))),
      m3_processes_important_data: importantDataFlag,
      m3_important_data_types: valueAsArray(values, "m3_important_data_types"),
      m3_data_sources: valueAsArray(values, "m3_data_sources"),
      m3_processing_activities: valueAsArray(values, "m3_processing_activities"),
      m3_data_volume_range: volume,
      m3_processes_enterprise_public_data: valueAsText(values, "m3_processes_enterprise_public_data"),
      m3_enterprise_public_data_desc: valueAsText(values, "m3_enterprise_public_data_desc"),
      m3_retention_period: valueAsText(values, "m3_retention_period"),
      m3_retention_desc: valueAsText(values, "m3_retention_desc"),
      m4_share_to_third_party: valueAsText(values, "m4_share_to_third_party"),
      m4_third_party_types: valueAsText(values, "m4_third_party_types"),
      m4_cross_border_transfer: valueAsText(values, "m4_cross_border_transfer"),
      m4_cross_border_regions: valueAsText(values, "m4_cross_border_regions"),
      m4_commercialization: valueAsText(values, "m4_commercialization"),
      m4_commercialization_mode: valueAsText(values, "m4_commercialization_mode"),
      m4_entrusted_processing: valueAsText(values, "m4_entrusted_processing"),
      m4_entrusted_party_type: valueAsText(values, "m4_entrusted_party_type"),
      m4_authorization_method: valueAsText(values, "m4_authorization_method"),
      m5_systems: valueAsArray(values, "m5_systems"),
      m5_security_measures: valueAsArray(values, "m5_security_measures"),
      m5_compliance_docs: valueAsArray(values, "m5_compliance_docs"),
      m5_penalty_or_complaint: valueAsText(values, "m5_penalty_or_complaint"),
      m5_penalty_time: valueAsText(values, "m5_penalty_time"),
      m5_penalty_reason: valueAsText(values, "m5_penalty_reason"),
      m5_penalty_result: valueAsText(values, "m5_penalty_result"),
    },
  };
}

export function buildAssessmentPayload(
  values: AssessmentFormValues,
  resolvedFilePaths: string[],
): ModuleRequestMap["assessment"] {
  requireText(values.company_name, "company_name");
  requireText(values.company_uscc, "company_uscc", 8);
  requireText(values.receiver_country, "receiver_country");
  requireText(values.transfer_purpose, "transfer_purpose");
  requireText(values.legal_basis, "legal_basis");
  requireText(values.necessity_basis, "necessity_basis");
  requireText(values.data_inventory_summary, "data_inventory_summary");
  requireText(values.system_chain_summary, "system_chain_summary");
  if (resolvedFilePaths.length === 0) throw new Error("uploaded_files is required");
  requireFileExtensions(resolvedFilePaths, GENERAL_FILE_EXTENSIONS);
  const purposeContext = [
    values.transfer_purpose.trim(),
    values.scenario_name ? `场景：${values.scenario_name}` : "",
    values.legal_basis ? `合法性：${values.legal_basis}` : "",
    values.necessity_basis ? `必要性：${values.necessity_basis}` : "",
    values.data_inventory_summary ? `数据清单：${values.data_inventory_summary}` : "",
    values.system_chain_summary ? `链路：${values.system_chain_summary}` : "",
    values.security_capability_summary ? `保障能力：${values.security_capability_summary}` : "",
    values.assessment_start_date || values.assessment_end_date
      ? `自评估周期：${values.assessment_start_date || "未填"} 至 ${values.assessment_end_date || "未填"}` : "",
    values.lead_department ? `牵头部门：${values.lead_department}` : "",
    values.participant_departments ? `参与部门：${values.participant_departments}` : "",
    values.third_party_support
      ? `第三方支持：${values.third_party_name || "已参与"}；${values.third_party_scope || "范围未填"}` : "",
  ].filter((item) => item.length > 0).join("；");
  return {
    company_name: trimOr(values.company_name, "待确认企业"),
    control: true,
    industry: trimOr([values.industry, values.company_nature].filter((item) => item.trim()).join(" / "), "未说明行业"),
    is_ciio: values.is_ciio,
    contains_important_data: values.contains_important_data,
    pii_count: Math.max(0, values.pii_count),
    spi_count: Math.max(0, values.spi_count),
    transfer_purpose: trimOr(purposeContext, "数据出境场景评估与风险自评估"),
    receiver_country: trimOr(values.receiver_country, "待确认国家"),
    force_override_path: values.force_override_path,
    uploaded_files: [...resolvedFilePaths],
  };
}

export function buildPipiaPayload(
  values: PipiaFormValues,
  resolvedFilePaths: string[],
): ModuleRequestMap["pipia"] {
  requireAllowedValue(values.route_type, "route_type", PIPIA_ROUTE_TYPES);
  requireText(values.company_name, "company_name");
  requireText(values.company_uscc, "company_uscc", 8);
  requireText(values.purpose, "purpose");
  requireText(values.recipient_name, "recipient_name");
  requireText(values.recipient_country_region, "recipient_country_region");
  requireText(values.legal_basis, "legal_basis");
  requireText(values.notice_mechanism, "notice_mechanism");
  requireText(values.consent_mechanism, "consent_mechanism");
  requireText(values.dsar_channel, "dsar_channel");
  requireText(values.retention_policy, "retention_policy");
  if (splitCsv(values.pi_categories).length === 0) throw new Error("pi_categories is required");
  if (resolvedFilePaths.length === 0) throw new Error("attachments is required");
  requireFileExtensions(resolvedFilePaths, GENERAL_FILE_EXTENSIONS);
  return {
    route_type: values.route_type,
    company_profile: {
      company_name: trimOr(values.company_name, "待确认企业"),
      company_uscc: values.company_uscc.trim(),
      is_ciio: values.is_ciio,
      processing_person_count: Math.max(0, values.processing_person_count),
      outbound_pi_count: Math.max(0, values.outbound_pi_count),
      outbound_spi_count: Math.max(0, values.outbound_spi_count),
      industry: trimOr(values.industry, "未说明行业"),
    },
    transfer_context: {
      purpose: trimOr([values.purpose, values.outbound_scenario_name ? `场景：${values.outbound_scenario_name}` : "", values.outbound_frequency ? `频率：${values.outbound_frequency}` : "", values.transfer_method ? `方式：${values.transfer_method}` : "", values.business_overview ? `业务概况：${values.business_overview}` : "", values.processing_activity_overview ? `处理活动：${values.processing_activity_overview}` : ""].filter((item) => item.trim()).join("；"), "个人信息出境处理活动评估"),
      recipient_name: trimOr(values.recipient_name, "待确认接收方"),
      recipient_country_region: trimOr(values.recipient_country_region, "待确认国家/地区"),
      legal_basis: trimOr([values.legal_basis, values.legality_justification ? `合法性论证：${values.legality_justification}` : "", values.necessity_justification ? `必要性论证：${values.necessity_justification}` : ""].filter((item) => item.trim()).join("；"), "合同履行必要"),
    },
    personal_info_scope: {
      pi_categories: splitCsv(values.pi_categories),
      spi_categories: splitCsv(values.spi_categories),
      subject_volume: Math.max(0, values.subject_volume),
    },
    rights_protection: {
      notice_mechanism: trimOr(values.notice_mechanism, "隐私政策告知"),
      consent_mechanism: trimOr(values.consent_mechanism, "单独同意"),
      dsar_channel: trimOr(values.dsar_channel, "privacy@example.com"),
      retention_policy: trimOr([values.retention_policy, values.domestic_storage ? `境内存储：${values.domestic_storage}` : "", values.overseas_storage ? `境外存储：${values.overseas_storage}` : ""].filter((item) => item.trim()).join("；"), "到期删除+最短必要"),
    },
    emergency_plan: {
      incident_response_sla_hours: Math.max(0, values.incident_response_sla_hours),
      escalation_path: trimOr([values.escalation_path, values.transfer_link ? `链路：${values.transfer_link}` : "", values.shareholding_structure ? `股权：${values.shareholding_structure}` : "", values.actual_controller ? `控制人：${values.actual_controller}` : "", values.overseas_investment ? `境内外投资：${values.overseas_investment}` : "", values.org_structure_privacy_team ? `组织与个保机构：${values.org_structure_privacy_team}` : ""].filter((item) => item.trim()).join("；"), "DPO -> 法务 -> 管理层"),
    },
    path_evidence: buildPipiaPathEvidence(values),
    attachments: resolvedFilePaths.map((path) => ({
      file_role: values.attachment_role,
      file_name: basenameFromPath(path),
      file_format: inferAttachmentFormat(path),
      storage_uri: path,
    })),
  };
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
    us_person_count: Math.max(0, Number(values.us_person_count)),
    transaction_type: values.transaction_type,
    doj_data_category_by_item: Object.fromEntries(
      [...dataCategories, ...splitCsv(values.sensitive_data_flags)].map((item) => [
        item,
        values.doj_data_category,
      ]),
    ),
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
