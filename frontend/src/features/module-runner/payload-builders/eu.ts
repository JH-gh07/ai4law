import type { ModuleRequestMap } from "../../../api/api-contract";
import type { BcrFormValues, DpiaFormValues, EuSccFormValues, TiaFormValues } from "../types";
import {
  basenameFromPath,
  composeBcrFinding,
  hasText,
  inferDocxPdfFormat,
  splitNonEmptyLines,
  toBcrScore,
} from "./common";

const BCR_REVIEW_ITEMS = [
  { code: "3.2-C1", title: "Binding nature and scope", legal_basis: "GDPR Art.47 + EDPB 1/2022", recommendation: "补齐内部约束力、申请主体与范围映射。" },
  { code: "3.2-C2", title: "Material scope and data flow", legal_basis: "EDPB 1/2022 Scope", recommendation: "明确数据类别、主体类别、处理目的和传输范围。" },
  { code: "3.2-C3", title: "Third-party beneficiary rights", legal_basis: "EDPB 1.3.1", recommendation: "明确数据主体可直接主张权利与救济路径。" },
  { code: "3.2-C4", title: "Liability and compensation", legal_basis: "EDPB 1.3.2", recommendation: "明确责任分配、赔偿与内部追偿机制。" },
  { code: "3.2-C5", title: "Transparency", legal_basis: "EDPB 1.4", recommendation: "补齐BCR公开、告知与变更通知机制。" },
  { code: "3.2-C6", title: "Training and audit", legal_basis: "EDPB 2.1/2.3", recommendation: "建立培训、审计、纠偏与证据留存机制。" },
  { code: "3.2-C7", title: "Cooperation with supervisory authorities", legal_basis: "EDPB 3.1", recommendation: "明确监管协作、检查和整改承诺。" },
  { code: "3.2-C8", title: "Data protection safeguards", legal_basis: "EDPB 5.x", recommendation: "补齐原则、权利、Article 28、记录和DPIA联动。" },
  { code: "3.2-C9", title: "Third-country law and government access", legal_basis: "EDPB 5.4", recommendation: "补齐第三国法律评估与政府访问应对机制。" },
  { code: "3.2-C10", title: "Update and definitions", legal_basis: "EDPB 8.1/9.1", recommendation: "明确更新报送机制与定义表。" },
] as const;

type EuSccPayload = ModuleRequestMap["eu_scc"];

const SCC_ROLE_MAP: Record<
  EuSccFormValues["transfer_role"],
  {
    declared: EuSccPayload["declared_module_type"];
    exporter: EuSccPayload["exporter_role"];
    importer: EuSccPayload["importer_role"];
  }
> = {
  c2c: { declared: "Module One", exporter: "controller", importer: "controller" },
  c2p: { declared: "Module Two", exporter: "controller", importer: "processor" },
  p2p: { declared: "Module Three", exporter: "processor", importer: "processor" },
  p2c: { declared: "Module Four", exporter: "processor", importer: "controller" },
};

export function buildEuSccPayload(
  values: EuSccFormValues,
  resolvedFilePaths: string[],
): EuSccPayload {
  const purposeContext = [
    values.transfer_purpose.trim(),
    `角色关系：${values.transfer_role}`,
    `SCC版本：${values.scc_version}`,
    `数据类别：${values.data_categories}`,
    values.data_subject_categories ? `主体类别：${values.data_subject_categories}` : "",
    `传输频率：${values.transfer_frequency}`,
    values.retention_rule ? `保存规则：${values.retention_rule}` : "",
    values.tom_summary ? `TOM：${values.tom_summary}` : "",
    values.onward_transfer_control ? `再传输：${values.onward_transfer_control}` : "",
    values.government_access_response ? `政府访问：${values.government_access_response}` : "",
    values.supplementary_clause_review ? `补充条款：${values.supplementary_clause_review}` : "",
    values.rights_and_complaint ? `权利救济：${values.rights_and_complaint}` : "",
  ]
    .filter((item) => item.length > 0)
    .join("；");
  const roles = SCC_ROLE_MAP[values.transfer_role];

  return {
    project_name: values.project_name_override?.trim()
      || `${values.exporter_name.trim()} - ${values.importer_name.trim()} SCC审查`,
    scc_text: values.scc_text_override?.trim() || [
        `SCC ${roles.declared} (${values.scc_version})`,
        `Data exporter: ${values.exporter_name.trim()} (${roles.exporter})`,
        `Data importer: ${values.importer_name.trim()}, ${values.importer_country.trim()} (${roles.importer})`,
        purposeContext,
      ].join("\n"),
    declared_module_type: roles.declared,
    exporter_role: roles.exporter,
    importer_role: roles.importer,
    has_tia: hasText(values.government_access_response ?? ""),
    has_supplementary_measures: hasText(values.supplementary_clause_review ?? ""),
    uploaded_files: [...resolvedFilePaths],
    company_name: values.exporter_name.trim(),
  };
}

export function buildBcrPayload(
  values: BcrFormValues,
  resolvedFilePaths: string[],
): ModuleRequestMap["bcr"] {
  const attachments = resolvedFilePaths.map((path) => ({
    file_name: basenameFromPath(path),
    file_format: inferDocxPdfFormat(path)!,
    storage_uri: path,
  }));
  const evidenceTexts = [
    `${values.binding_mechanism} ${values.lead_sa_rationale}`,
    values.data_flow_scope,
    values.third_party_beneficiary,
    values.liability_compensation,
    values.transparency_notice,
    values.training_audit,
    values.cooperation_with_sa,
    values.dp_safeguards,
    `${values.third_country_assessment} ${values.government_access_process}`,
    `${values.update_mechanism} ${values.definitions_quality}`,
  ];
  const reviewItems = BCR_REVIEW_ITEMS.map((item, index) => {
    const evidence = evidenceTexts[index]?.trim() || "未提供";
    const score = toBcrScore(evidence);
    return {
      code: item.code,
      title: item.title,
      score,
      finding: composeBcrFinding(score, evidence.slice(0, 180)),
      legal_basis: item.legal_basis,
      recommendation: values.review_focus
        ? `${item.recommendation} 本轮重点：${values.review_focus}`
        : item.recommendation,
      evidence,
    };
  });

  return {
    company_name: values.company_name.trim(),
    review_items: reviewItems,
    attachments,
    uploaded_files: [...resolvedFilePaths],
    scenario_context: {
      company_name: values.company_name.trim(),
      eu_liable_entity: values.applicant_entity.trim(),
      auto_extracted_facts: {
        group_structure_summary: values.group_structure.trim(),
        data_flow_scope: values.data_flow_scope.trim(),
      },
    },
  };
}

export function buildDpiaPayload(
  values: DpiaFormValues,
  resolvedFilePaths: string[],
): ModuleRequestMap["dpia"] {
  const dataCategories = splitNonEmptyLines(values.data_types);
  const lawfulBasis = splitNonEmptyLines(values.lawful_basis);
  const triggerReasons = splitNonEmptyLines(values.need_reason);
  const specialCategoryTypes = values.includes_special_data
    ? (dataCategories.length > 0 ? dataCategories.slice(0, 5) : ["special_category_data"])
    : [];
  const identifiedRisks = splitNonEmptyLines(values.risk_assessment).map((risk, index) => ({
    risk_id: `RISK-${String(index + 1).padStart(3, "0")}`,
    risk_description: risk,
    likelihood: /高|重大|high/i.test(risk) ? "high" as const : /低|low/i.test(risk) ? "low" as const : "medium" as const,
    impact: /高|重大|high/i.test(risk) ? "high" as const : /低|low/i.test(risk) ? "low" as const : "medium" as const,
    affected_data_subjects: values.subject_scale.trim(),
    risk_source: values.has_crossborder_transfer
      ? "third_party" as const
      : values.novel_technology.trim()
        ? "technology" as const
        : values.includes_special_data
          ? "data_type" as const
          : "processing_activity" as const,
  }));
  const mitigationMeasures = splitNonEmptyLines(values.mitigation_measures).map((measure, index) => ({
    mitigation_id: `MIT-${String(index + 1).padStart(3, "0")}`,
    description: measure,
    target_risk_ids: identifiedRisks.map((risk) => risk.risk_id),
    status: "planned" as const,
    responsible_party: values.signoff_owner.trim() || values.controller_name.trim() || values.dpo_role.trim(),
  }));

  return {
    project_name: values.project_name.trim(),
    project_goal: values.project_goal.trim(),
    dpia_trigger_reasons: triggerReasons,
    processing_flow_description: [
      values.processing_description,
      values.data_types ? `数据类型：${values.data_types}` : "",
      values.subject_scale ? `主体规模：${values.subject_scale}` : "",
      values.frequency ? `频率：${values.frequency}` : "",
      values.retention_period ? `保存期限：${values.retention_period}` : "",
      values.geo_scope ? `地理范围：${values.geo_scope}` : "",
      values.data_source ? `数据来源：${values.data_source}` : "",
      values.relationship_context ? `关系背景：${values.relationship_context}` : "",
      values.includes_special_data ? "包含特殊类别数据" : "",
      values.has_crossborder_transfer ? "涉及跨境传输" : "",
      values.vulnerable_group ? `脆弱群体：${values.vulnerable_group}` : "",
      values.novel_technology ? `新技术：${values.novel_technology}` : "",
    ].filter((item) => item.trim().length > 0).join("；"),
    data_categories: dataCategories,
    special_category_data: values.includes_special_data,
    special_category_types: specialCategoryTypes,
    data_subject_categories: splitNonEmptyLines(values.relationship_context),
    data_subject_count: values.subject_scale.trim(),
    retention_period: values.retention_period.trim(),
    cross_border_transfer: values.has_crossborder_transfer,
    transfer_destination: values.geo_scope.trim(),
    automated_decision_making: values.novel_technology.trim().length > 0,
    systematic_monitoring: /持续|监控|monitor/i.test(`${values.frequency} ${values.processing_description}`),
    large_scale_processing: /万|large|大量|规模/i.test(values.subject_scale),
    data_matching: /匹配|关联|融合|match/i.test(`${values.processing_description} ${values.project_goal}`),
    new_technology: values.novel_technology.trim().length > 0,
    vulnerable_data_subjects: values.vulnerable_group.trim().length > 0,
    consulted_internal_departments: splitNonEmptyLines(values.processor_management),
    external_experts: splitNonEmptyLines(values.contact_channel),
    data_subject_consultation_plan: [values.notice_plan, values.rights_support, values.expectation_control]
      .filter((item) => item.trim().length > 0)
      .join("；"),
    lawful_basis: lawfulBasis,
    necessity_statement: [
      values.purpose_and_necessity,
      values.need_reason ? `触发理由：${values.need_reason}` : "",
      values.minimization_quality ? `最小化与质量：${values.minimization_quality}` : "",
    ].filter((item) => item.trim().length > 0).join("；"),
    proportionality_statement: [
      values.function_creep_control,
      values.processor_management,
      values.relationship_context ? `关系背景：${values.relationship_context}` : "",
    ].filter((item) => item.trim().length > 0).join("；"),
    transparency_information: [
      values.notice_plan,
      values.contact_channel ? `联系渠道：${values.contact_channel}` : "",
      values.controller_name ? `控制者：${values.controller_name}` : "",
    ].filter((item) => item.trim().length > 0).join("；"),
    identified_risks: identifiedRisks,
    mitigation_measures: mitigationMeasures,
    dpia_owner: values.signoff_owner.trim() || values.controller_name.trim(),
    dpo_name: values.dpo_role.trim(),
    dpo_opinion: [
      values.dpo_advice,
      values.residual_risk ? `剩余风险：${values.residual_risk}` : "",
    ].filter((item) => item.trim().length > 0).join("；"),
    review_date: values.review_schedule.trim(),
    uploaded_files: [...resolvedFilePaths],
  };
}

export function buildTiaPayload(
  values: TiaFormValues,
  resolvedFilePaths: string[],
): ModuleRequestMap["tia"] {
  const attachments = resolvedFilePaths.map((path) => ({
    file_role: values.attachment_role,
    file_name: basenameFromPath(path),
    file_format: inferDocxPdfFormat(path)!,
    storage_uri: path,
  }));

  return {
    transfer_tool: values.transfer_tool,
    data_exporter_profile: [
      values.data_exporter_name,
      `传输目的：${values.transfer_purpose}`,
      values.data_categories ? `数据类别：${values.data_categories}` : "",
      values.data_subject_categories ? `数据主体：${values.data_subject_categories}` : "",
      `频率：${values.transfer_frequency}`,
    ].filter((item) => item.trim().length > 0).join("；"),
    data_importer_profile: [
      values.data_importer_name,
      `国家/地区：${values.importer_country_region}`,
      values.sensitive_data_description ? `敏感数据：${values.sensitive_data_description}` : "",
    ].filter((item) => item.trim().length > 0).join("；"),
    third_country_assessment: [
      values.law_assessed ? "已完成法律评估" : "法律评估待完成",
      values.law_findings,
      values.pre_effectiveness ? `补充措施前判断：${values.pre_effectiveness}` : "",
    ].filter((item) => item.trim().length > 0).join("；"),
    supplementary_measures: [
      `技术措施：${values.supplementary_technical}`,
      values.supplementary_contractual ? `合同措施：${values.supplementary_contractual}` : "",
      values.supplementary_organizational ? `组织措施：${values.supplementary_organizational}` : "",
    ].filter((item) => item.trim().length > 0).join("；"),
    final_conclusion: [
      values.post_effectiveness,
      `关键行动：${values.key_actions}`,
      values.dpo_opinion ? `DPO意见：${values.dpo_opinion}` : "",
      values.review_date ? `复审日期：${values.review_date}` : "",
    ].filter((item) => item.trim().length > 0).join("；"),
    attachments,
  };
}
