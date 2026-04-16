import { useEffect, useMemo, useState } from "react";
import type { ModuleKey, RunMode, TaskSpace } from "../../lib/domain";
import {
  findModule,
  getDefaultPayload,
  hasAsync,
  listModules,
  runModule,
  uploadTaskFile
} from "../../lib/module-adapter";
import { useLang } from "../../lib/language";
import { findTaskTemplate, getTaskTemplateTitle } from "../../lib/task-templates";
import { extractInsight } from "../../lib/workspace";

export type RunOutput = {
  module: ModuleKey;
  runMode: RunMode;
  request: unknown;
  response?: unknown;
  success: boolean;
  error?: string;
  asyncTaskId?: string;
  asyncState?: string;
};

type ModuleRunPanelProps = {
  onRunDone: (output: RunOutput) => void;
  taskSpace: TaskSpace;
};

type UserFacingResult = {
  headline: string;
  chips: string[];
  deliverables: string[];
  highlights: string[];
  nextSteps: string[];
};

type DiagnosisSelectValue =
  | "yes"
  | "no"
  | "unknown"
  | "contract_performance"
  | "hr_management"
  | "emergency"
  | "legal_duty"
  | "other"
  | "intra_group"
  | "third_party";

type DiagnosisFieldType = "text" | "textarea" | "number" | "select";

type DiagnosisFieldConfig = {
  name: keyof DiagnosisFormValues;
  label: string;
  type: DiagnosisFieldType;
  options?: Array<{ value: DiagnosisSelectValue; label: string }>;
  min?: number;
  step?: number;
};

type DiagnosisStepConfig = {
  title: string;
  fields: DiagnosisFieldConfig[];
};

type DiagnosisFormValues = {
  company_name: string;
  q5_no_personal_info: "yes" | "no" | "unknown";
  q6_scenario: "contract_performance" | "hr_management" | "emergency" | "legal_duty" | "other";
  q7_receiver_type: "intra_group" | "third_party";
  q1_is_ciio: "yes" | "no" | "unknown";
  q2_has_important_data: "yes" | "no" | "unknown";
  q3_pii_count: number;
  q4_spi_count: number;
  q8_purpose: string;
};

type AssessmentFieldType = "text" | "textarea" | "number" | "checkbox" | "select";

type AssessmentFieldConfig = {
  name: keyof AssessmentFormValues;
  label: string;
  type: AssessmentFieldType;
  options?: string[];
  min?: number;
  step?: number;
};

type AssessmentStepConfig = {
  title: string;
  fields: AssessmentFieldConfig[];
};

type AssessmentFormValues = {
  company_name: string;
  company_uscc: string;
  legal_representative: string;
  registered_address: string;
  company_nature: string;
  industry: string;
  assessment_start_date: string;
  assessment_end_date: string;
  lead_department: string;
  participant_departments: string;
  third_party_support: boolean;
  third_party_name: string;
  third_party_scope: string;
  scenario_name: string;
  receiver_name: string;
  transfer_frequency: "one_time" | "periodic" | "continuous";
  is_long_term: boolean;
  legal_basis: string;
  necessity_basis: string;
  receiver_country: string;
  is_ciio: boolean;
  contains_important_data: boolean;
  pii_count: number;
  spi_count: number;
  transfer_purpose: string;
  data_inventory_summary: string;
  system_chain_summary: string;
  security_capability_summary: string;
  force_override_path: boolean;
};

type PipiaRouteType = "scc_filing" | "certification";
type PipiaAttachmentRole = "scc_contract" | "certification_material" | "internal_policy" | "supporting_evidence";

type PipiaFieldType = "text" | "textarea" | "number" | "checkbox" | "select";

type PipiaFieldConfig = {
  name: keyof PipiaFormValues;
  label: string;
  type: PipiaFieldType;
  options?: string[];
  min?: number;
  step?: number;
};

type PipiaStepConfig = {
  title: string;
  fields: PipiaFieldConfig[];
};

type PipiaFormValues = {
  company_name: string;
  company_uscc: string;
  industry: string;
  shareholding_structure: string;
  actual_controller: string;
  overseas_investment: string;
  org_structure_privacy_team: string;
  business_overview: string;
  processing_activity_overview: string;
  is_ciio: boolean;
  processing_person_count: number;
  outbound_pi_count: number;
  outbound_spi_count: number;
  route_type: PipiaRouteType;
  outbound_scenario_name: string;
  outbound_frequency: "one_time" | "periodic" | "continuous";
  transfer_method: string;
  domestic_storage: string;
  overseas_storage: string;
  transfer_link: string;
  purpose: string;
  recipient_name: string;
  recipient_country_region: string;
  legal_basis: string;
  legality_justification: string;
  necessity_justification: string;
  pi_categories: string;
  spi_categories: string;
  subject_volume: number;
  notice_mechanism: string;
  consent_mechanism: string;
  dsar_channel: string;
  retention_policy: string;
  incident_response_sla_hours: number;
  escalation_path: string;
  attachment_role: PipiaAttachmentRole;
};

type DocumentReviewFieldType = "text" | "textarea" | "number" | "checkbox" | "select";

type DocumentReviewFieldConfig = {
  name: keyof DocumentReviewFormValues;
  label: string;
  type: DocumentReviewFieldType;
  options?: string[];
  min?: number;
  step?: number;
};

type DocumentReviewStepConfig = {
  title: string;
  fields: DocumentReviewFieldConfig[];
};

type DocumentReviewFormValues = {
  company_name: string;
  document_title: string;
  document_version: string;
  effective_date: string;
  applicable_products: string;
  applicable_scope: string;
  publisher_entity: string;
  is_live_version: boolean;
  document_type: "privacy_policy" | "scc_contract" | "dpa" | "other";
  receiver_name: string;
  receiver_country: string;
  transfer_purpose: string;
  processor_identity_disclosed: boolean;
  scope_disclosed: boolean;
  collection_purpose_disclosed: boolean;
  processing_method_disclosed: boolean;
  category_disclosed: boolean;
  sensitive_pi_disclosed: boolean;
  crossborder_rule_disclosed: boolean;
  rights_channel_disclosed: boolean;
  contact_channel: string;
  pii_count: number;
  spi_count: number;
  has_scc_draft: boolean;
  review_focus: string;
};

type EuSccFieldType = "text" | "textarea" | "number" | "checkbox" | "select";
type EuSccFieldConfig = {
  name: keyof EuSccFormValues;
  label: string;
  type: EuSccFieldType;
  options?: string[];
  min?: number;
  step?: number;
};
type EuSccStepConfig = {
  title: string;
  fields: EuSccFieldConfig[];
};
type EuSccFormValues = {
  exporter_name: string;
  importer_name: string;
  importer_country: string;
  transfer_role: "c2c" | "c2p" | "p2p" | "p2c";
  scc_version: "eu_2021" | "other";
  transfer_purpose: string;
  data_categories: string;
  data_subject_categories: string;
  transfer_frequency: "one_time" | "periodic" | "continuous";
  retention_rule: string;
  tom_summary: string;
  onward_transfer_control: string;
  rights_and_complaint: string;
  government_access_response: string;
  supplementary_clause_review: string;
  pii_count: number;
  spi_count: number;
  has_scc_draft: boolean;
};

type BcrFieldType = "text" | "textarea" | "select";
type BcrFieldConfig = {
  name: keyof BcrFormValues;
  label: string;
  type: BcrFieldType;
  options?: string[];
};
type BcrStepConfig = {
  title: string;
  fields: BcrFieldConfig[];
};
type BcrFormValues = {
  company_name: string;
  group_structure: string;
  applicant_entity: string;
  data_flow_scope: string;
  lead_sa_rationale: string;
  binding_mechanism: string;
  third_party_beneficiary: string;
  liability_compensation: string;
  transparency_notice: string;
  training_audit: string;
  cooperation_with_sa: string;
  dp_safeguards: string;
  third_country_assessment: string;
  government_access_process: string;
  update_mechanism: string;
  definitions_quality: string;
  review_focus: string;
};

type DpiaFieldType = "text" | "textarea" | "select" | "checkbox";
type DpiaFieldConfig = {
  name: keyof DpiaFormValues;
  label: string;
  type: DpiaFieldType;
  options?: string[];
};
type DpiaStepConfig = {
  title: string;
  fields: DpiaFieldConfig[];
};
type DpiaFormValues = {
  project_name: string;
  project_goal: string;
  need_reason: string;
  controller_name: string;
  dpo_role: string;
  contact_channel: string;
  processing_description: string;
  data_types: string;
  includes_special_data: boolean;
  subject_scale: string;
  frequency: string;
  retention_period: string;
  geo_scope: string;
  has_crossborder_transfer: boolean;
  data_source: string;
  relationship_context: string;
  expectation_control: string;
  vulnerable_group: string;
  prior_concerns: string;
  novel_technology: string;
  lawful_basis: string;
  purpose_and_necessity: string;
  function_creep_control: string;
  minimization_quality: string;
  notice_plan: string;
  rights_support: string;
  processor_management: string;
  risk_assessment: string;
  mitigation_measures: string;
  residual_risk: string;
  signoff_owner: string;
  dpo_advice: string;
  review_schedule: string;
  attachment_role: "data_flow_diagram" | "security_policy" | "dpa" | "other";
};

type TiaFieldType = "text" | "textarea" | "select" | "checkbox";
type TiaFieldConfig = {
  name: keyof TiaFormValues;
  label: string;
  type: TiaFieldType;
  options?: string[];
};
type TiaStepConfig = {
  title: string;
  fields: TiaFieldConfig[];
};
type TiaFormValues = {
  data_exporter_name: string;
  data_importer_name: string;
  importer_country_region: string;
  transfer_purpose: string;
  data_categories: string;
  sensitive_data_description: string;
  data_subject_categories: string;
  transfer_frequency: "one_time" | "periodic" | "continuous";
  transfer_tool: "scc" | "bcr" | "derogation";
  law_assessed: boolean;
  law_findings: string;
  pre_effectiveness: string;
  supplementary_technical: string;
  supplementary_contractual: string;
  supplementary_organizational: string;
  post_effectiveness: string;
  key_actions: string;
  dpo_opinion: string;
  review_date: string;
  attachment_role: "transfer_agreement" | "country_law_analysis" | "technical_control_doc" | "other";
};

type CnFlowRecipientRole = "processor" | "controller" | "subprocessor" | "affiliate" | "vendor";
type CnFlowFieldType = "text" | "textarea" | "select" | "checkbox";
type CnFlowFieldConfig = {
  name: keyof CnFlowFormValues;
  label: string;
  type: CnFlowFieldType;
  options?: string[];
};
type CnFlowStepConfig = {
  title: string;
  fields: CnFlowFieldConfig[];
};
type CnFlowFormValues = {
  company_name: string;
  transfer_purpose: string;
  data_categories: string;
  sensitive_data_flags: string;
  transfer_chain: string;
  data_volume_note: string;
  necessity_justification: string;
  primary_recipient_name: string;
  primary_recipient_country: string;
  primary_recipient_role: CnFlowRecipientRole;
  primary_recipient_restricted: boolean;
  additional_recipients: string;
  internal_access_note: string;
};

type CpraFieldType = "text" | "textarea" | "checkbox";
type CpraFieldConfig = {
  name: keyof CpraFormValues;
  label: string;
  type: CpraFieldType;
};
type CpraStepConfig = {
  title: string;
  fields: CpraFieldConfig[];
};
type CpraFormValues = {
  company_name: string;
  dba_name: string;
  cpra_applicability_selfcheck: string;
  business_model: string;
  data_lifecycle: string;
  data_categories: string;
  notice_and_consent: string;
  privacy_policy_url: string;
  consumer_rights_process: string;
  identity_verification_method: string;
  rights_sla: string;
  opt_out_and_sale_sharing: string;
  spi_usage_summary: string;
  vendor_management: string;
  ui_dark_pattern_check: string;
  review_focus: string;
};

const JURISDICTIONS = ["CN", "EU", "US"] as const;

const DIAGNOSIS_STEPS: DiagnosisStepConfig[] = [
  {
    title: "基础识别",
    fields: [
      { name: "company_name", label: "企业名称", type: "text" },
      {
        name: "q5_no_personal_info",
        label: "Q1 本次出境数据是否完全不含个人信息和重要数据？",
        type: "select",
        options: [
          { value: "no", label: "否（含个人信息或重要数据）" },
          { value: "yes", label: "是（纯业务/技术数据）" },
          { value: "unknown", label: "不确定" }
        ]
      },
      {
        name: "q6_scenario",
        label: "Q2 本次数据出境的主要业务场景",
        type: "select",
        options: [
          { value: "other", label: "其他商业目的" },
          { value: "contract_performance", label: "履行合同 / 向消费者提供服务" },
          { value: "hr_management", label: "跨国公司内部人力资源管理" },
          { value: "emergency", label: "紧急情况保护自然人生命、健康或财产安全" },
          { value: "legal_duty", label: "依法履行法定职责或法定义务" }
        ]
      },
      {
        name: "q7_receiver_type",
        label: "Q3 境外数据接收方类型",
        type: "select",
        options: [
          { value: "third_party", label: "独立第三方（合作伙伴 / 服务商）" },
          { value: "intra_group", label: "集团内部关联公司" }
        ]
      }
    ]
  },
  {
    title: "强制路径触发项",
    fields: [
      {
        name: "q1_is_ciio",
        label: "Q4 是否为关键信息基础设施运营者（CIIO）？",
        type: "select",
        options: [
          { value: "no", label: "否" },
          { value: "yes", label: "是" },
          { value: "unknown", label: "不确定" }
        ]
      },
      {
        name: "q2_has_important_data",
        label: "Q5 出境数据是否包含重要数据？",
        type: "select",
        options: [
          { value: "no", label: "否" },
          { value: "yes", label: "是" },
          { value: "unknown", label: "不确定" }
        ]
      },
      { name: "q3_pii_count", label: "Q6 近12个月累计向境外提供个人信息的人数", type: "number", min: 0, step: 1000 },
      { name: "q4_spi_count", label: "Q7 近12个月累计向境外提供敏感个人信息的人数", type: "number", min: 0, step: 100 }
    ]
  },
  {
    title: "补充说明",
    fields: [
      { name: "q8_purpose", label: "Q8 出境目的简述（可选）", type: "textarea" }
    ]
  }
];

const ASSESSMENT_STEPS: AssessmentStepConfig[] = [
  {
    title: "主体基础信息",
    fields: [
      { name: "company_name", label: "企业名称", type: "text" },
      { name: "company_uscc", label: "统一社会信用代码", type: "text" },
      { name: "legal_representative", label: "法定代表人", type: "text" },
      { name: "registered_address", label: "注册地址", type: "text" },
      { name: "company_nature", label: "公司性质", type: "text" },
      { name: "industry", label: "行业", type: "text" },
      { name: "receiver_country", label: "接收方国家", type: "text" },
      { name: "receiver_name", label: "境外接收方名称", type: "text" }
    ]
  },
  {
    title: "自评估工作组织",
    fields: [
      { name: "assessment_start_date", label: "自评估开始日期", type: "text" },
      { name: "assessment_end_date", label: "自评估结束日期", type: "text" },
      { name: "lead_department", label: "牵头部门", type: "text" },
      { name: "participant_departments", label: "参与部门（逗号分隔）", type: "text" },
      { name: "third_party_support", label: "是否有第三方机构参与", type: "checkbox" },
      { name: "third_party_name", label: "第三方机构名称", type: "text" },
      { name: "third_party_scope", label: "第三方参与范围", type: "textarea" }
    ]
  },
  {
    title: "出境场景与必要性",
    fields: [
      { name: "scenario_name", label: "出境场景名称", type: "text" },
      {
        name: "transfer_frequency",
        label: "出境频率",
        type: "select",
        options: ["one_time", "periodic", "continuous"]
      },
      { name: "is_long_term", label: "是否长期持续出境", type: "checkbox" },
      { name: "transfer_purpose", label: "出境目的", type: "textarea" },
      { name: "legal_basis", label: "合法性基础", type: "textarea" },
      { name: "necessity_basis", label: "必要性说明", type: "textarea" }
    ]
  },
  {
    title: "数据清单与链路",
    fields: [
      { name: "is_ciio", label: "是否 CIIO", type: "checkbox" },
      { name: "contains_important_data", label: "是否涉及重要数据", type: "checkbox" },
      { name: "pii_count", label: "普通个人信息量", type: "number", min: 0, step: 1000 },
      { name: "spi_count", label: "敏感个人信息量", type: "number", min: 0, step: 100 },
      { name: "data_inventory_summary", label: "数据清单摘要（场景/字段/必要性）", type: "textarea" },
      { name: "system_chain_summary", label: "系统与出境链路说明", type: "textarea" },
      { name: "security_capability_summary", label: "数据安全保障能力说明", type: "textarea" }
    ]
  },
  {
    title: "执行策略与材料",
    fields: [
      { name: "force_override_path", label: "允许路径不一致时继续生成", type: "checkbox" }
    ]
  }
];

const PIPIA_STEPS: PipiaStepConfig[] = [
  {
    title: "企业基本信息",
    fields: [
      { name: "company_name", label: "企业名称", type: "text" },
      { name: "company_uscc", label: "统一社会信用代码", type: "text" },
      { name: "industry", label: "行业", type: "text" },
      { name: "shareholding_structure", label: "股权结构", type: "textarea" },
      { name: "actual_controller", label: "实际控制人", type: "text" },
      { name: "overseas_investment", label: "境内外投资情况", type: "textarea" },
      { name: "org_structure_privacy_team", label: "组织架构与个保机构信息", type: "textarea" },
      { name: "business_overview", label: "整体业务概况", type: "textarea" },
      { name: "processing_activity_overview", label: "处理活动概况", type: "textarea" },
      { name: "is_ciio", label: "是否 CIIO", type: "checkbox" },
      { name: "processing_person_count", label: "处理个人信息规模", type: "number", min: 0, step: 1000 },
      { name: "outbound_pi_count", label: "出境普通个人信息规模", type: "number", min: 0, step: 1000 },
      { name: "outbound_spi_count", label: "出境敏感个人信息规模", type: "number", min: 0, step: 100 }
    ]
  },
  {
    title: "出境场景与范围",
    fields: [
      { name: "route_type", label: "路径类型", type: "select", options: ["scc_filing", "certification"] },
      { name: "outbound_scenario_name", label: "出境场景名称", type: "text" },
      {
        name: "outbound_frequency",
        label: "出境频率",
        type: "select",
        options: ["one_time", "periodic", "continuous"]
      },
      { name: "transfer_method", label: "出境方式（API/文件/同步）", type: "text" },
      { name: "domestic_storage", label: "境内存储系统/数据中心", type: "textarea" },
      { name: "overseas_storage", label: "境外存储系统/数据中心", type: "textarea" },
      { name: "transfer_link", label: "出境链路说明", type: "textarea" },
      { name: "purpose", label: "出境目的", type: "textarea" },
      { name: "recipient_name", label: "境外接收方", type: "text" },
      { name: "recipient_country_region", label: "接收方国家/地区", type: "text" },
      { name: "legal_basis", label: "处理合法性基础", type: "text" },
      { name: "legality_justification", label: "合法性论证", type: "textarea" },
      { name: "necessity_justification", label: "必要性论证", type: "textarea" },
      { name: "pi_categories", label: "普通个人信息类别（逗号分隔）", type: "text" },
      { name: "spi_categories", label: "敏感个人信息类别（逗号分隔）", type: "text" },
      { name: "subject_volume", label: "数据主体规模", type: "number", min: 0, step: 1000 }
    ]
  },
  {
    title: "权利保障与应急",
    fields: [
      { name: "notice_mechanism", label: "告知机制", type: "textarea" },
      { name: "consent_mechanism", label: "同意机制", type: "text" },
      { name: "dsar_channel", label: "权利请求渠道", type: "text" },
      { name: "retention_policy", label: "保存与删除策略", type: "textarea" },
      { name: "incident_response_sla_hours", label: "事件响应SLA（小时）", type: "number", min: 1, step: 1 },
      { name: "escalation_path", label: "升级路径", type: "text" },
      {
        name: "attachment_role",
        label: "附件角色",
        type: "select",
        options: ["scc_contract", "certification_material", "internal_policy", "supporting_evidence"]
      }
    ]
  }
];

const DOCUMENT_REVIEW_STEPS: DocumentReviewStepConfig[] = [
  {
    title: "审查对象",
    fields: [
      { name: "company_name", label: "企业名称", type: "text" },
      { name: "publisher_entity", label: "发布主体", type: "text" },
      { name: "document_title", label: "文档名称", type: "text" },
      { name: "document_version", label: "文档版本号", type: "text" },
      { name: "effective_date", label: "生效日期", type: "text" },
      { name: "applicable_products", label: "适用产品/站点", type: "text" },
      { name: "applicable_scope", label: "适用范围说明", type: "textarea" },
      { name: "is_live_version", label: "是否线上生效版本", type: "checkbox" },
      {
        name: "document_type",
        label: "文档类型",
        type: "select",
        options: ["privacy_policy", "scc_contract", "dpa", "other"]
      }
    ]
  },
  {
    title: "披露完整性检查",
    fields: [
      { name: "processor_identity_disclosed", label: "是否披露处理者身份", type: "checkbox" },
      { name: "scope_disclosed", label: "是否披露适用范围", type: "checkbox" },
      { name: "collection_purpose_disclosed", label: "是否披露收集与处理目的", type: "checkbox" },
      { name: "processing_method_disclosed", label: "是否披露处理方式", type: "checkbox" },
      { name: "category_disclosed", label: "是否披露个人信息种类", type: "checkbox" },
      { name: "sensitive_pi_disclosed", label: "是否披露敏感个人信息处理", type: "checkbox" },
      { name: "crossborder_rule_disclosed", label: "是否披露出境规则与接收方", type: "checkbox" },
      { name: "rights_channel_disclosed", label: "是否披露个人权利行使方式", type: "checkbox" },
      { name: "contact_channel", label: "投诉/联系渠道", type: "text" }
    ]
  },
  {
    title: "出境与处理背景",
    fields: [
      { name: "receiver_name", label: "境外接收方（如适用）", type: "text" },
      { name: "receiver_country", label: "接收方国家/地区", type: "text" },
      { name: "transfer_purpose", label: "处理/出境目的", type: "textarea" },
      { name: "pii_count", label: "涉及个人信息规模（估算）", type: "number", min: 0, step: 1000 },
      { name: "spi_count", label: "涉及敏感个人信息规模（估算）", type: "number", min: 0, step: 100 },
      { name: "has_scc_draft", label: "是否已有可审查合同草案", type: "checkbox" }
    ]
  },
  {
    title: "审查重点与附件",
    fields: [
      { name: "review_focus", label: "本次重点关注条款", type: "textarea" }
    ]
  }
];

const EU_SCC_STEPS: EuSccStepConfig[] = [
  {
    title: "传输主体与模块",
    fields: [
      { name: "exporter_name", label: "数据出口方（EEA）", type: "text" },
      { name: "importer_name", label: "数据进口方（第三国）", type: "text" },
      { name: "importer_country", label: "进口方国家/地区", type: "text" },
      { name: "transfer_role", label: "传输角色关系", type: "select", options: ["c2c", "c2p", "p2p", "p2c"] },
      { name: "scc_version", label: "SCC版本识别", type: "select", options: ["eu_2021", "other"] },
      { name: "has_scc_draft", label: "是否已有完整SCC文本", type: "checkbox" }
    ]
  },
  {
    title: "场景与数据范围",
    fields: [
      { name: "transfer_purpose", label: "传输目的", type: "textarea" },
      { name: "data_categories", label: "个人数据类别（逗号分隔）", type: "text" },
      { name: "data_subject_categories", label: "数据主体类别", type: "text" },
      { name: "transfer_frequency", label: "传输频率", type: "select", options: ["one_time", "periodic", "continuous"] },
      { name: "retention_rule", label: "保存期限/删除规则", type: "textarea" },
      { name: "pii_count", label: "PI 规模（估算）", type: "number", min: 0, step: 1000 },
      { name: "spi_count", label: "SPI 规模（估算）", type: "number", min: 0, step: 100 }
    ]
  },
  {
    title: "条款与保障机制",
    fields: [
      { name: "tom_summary", label: "技术与组织措施（TOM）摘要", type: "textarea" },
      { name: "onward_transfer_control", label: "子处理者/再传输控制", type: "textarea" },
      { name: "rights_and_complaint", label: "数据主体权利与投诉机制", type: "textarea" },
      { name: "government_access_response", label: "政府访问请求应对机制", type: "textarea" },
      { name: "supplementary_clause_review", label: "补充条款冲突检查关注点", type: "textarea" }
    ]
  },
  {
    title: "审查文件",
    fields: []
  }
];

const BCR_STEPS: BcrStepConfig[] = [
  {
    title: "主体与范围",
    fields: [
      { name: "company_name", label: "集团名称", type: "text" },
      { name: "group_structure", label: "集团结构与申请主体", type: "textarea" },
      { name: "applicant_entity", label: "申请实体与职责", type: "textarea" },
      { name: "lead_sa_rationale", label: "BCR Lead 选择理由", type: "textarea" },
      { name: "data_flow_scope", label: "数据流与处理活动范围", type: "textarea" }
    ]
  },
  {
    title: "约束力与权利机制",
    fields: [
      { name: "binding_mechanism", label: "集团内部/员工约束机制", type: "textarea" },
      { name: "third_party_beneficiary", label: "第三方受益人权利条款", type: "textarea" },
      { name: "liability_compensation", label: "责任承担与赔偿能力说明", type: "textarea" },
      { name: "transparency_notice", label: "对外公开与告知安排", type: "textarea" }
    ]
  },
  {
    title: "治理与监管协作",
    fields: [
      { name: "training_audit", label: "培训与审计制度", type: "textarea" },
      { name: "cooperation_with_sa", label: "与监管协作义务", type: "textarea" },
      { name: "dp_safeguards", label: "数据保护原则与保障", type: "textarea" },
      { name: "third_country_assessment", label: "第三国法律评估机制", type: "textarea" },
      { name: "government_access_process", label: "政府访问请求处理机制", type: "textarea" }
    ]
  },
  {
    title: "更新与文档材料",
    fields: [
      { name: "update_mechanism", label: "更新机制与成员清单维护", type: "textarea" },
      { name: "definitions_quality", label: "定义表与术语清晰度", type: "textarea" },
      { name: "review_focus", label: "本次重点关注项", type: "textarea" }
    ]
  }
];

const DPIA_STEPS: DpiaStepConfig[] = [
  {
    title: "项目与触发理由",
    fields: [
      { name: "project_name", label: "项目名称", type: "text" },
      { name: "project_goal", label: "项目目标/摘要", type: "textarea" },
      { name: "need_reason", label: "需要 DPIA 的主要理由", type: "textarea" },
      { name: "controller_name", label: "控制者名称", type: "text" },
      { name: "dpo_role", label: "DPO 职位", type: "text" },
      { name: "contact_channel", label: "控制者/DPO 联系方式", type: "text" }
    ]
  },
  {
    title: "处理活动描述",
    fields: [
      { name: "processing_description", label: "处理流程与活动描述", type: "textarea" },
      { name: "data_types", label: "数据类型", type: "text" },
      { name: "includes_special_data", label: "是否涉及特殊类别数据", type: "checkbox" },
      { name: "subject_scale", label: "数据主体规模", type: "text" },
      { name: "frequency", label: "处理频率", type: "text" },
      { name: "retention_period", label: "保存期限", type: "text" },
      { name: "geo_scope", label: "地理覆盖范围", type: "text" },
      { name: "has_crossborder_transfer", label: "是否涉及跨境传输", type: "checkbox" },
      { name: "data_source", label: "数据来源", type: "text" },
      { name: "relationship_context", label: "与数据主体关系", type: "text" }
    ]
  },
  {
    title: "必要性与相称性",
    fields: [
      { name: "lawful_basis", label: "合法性基础", type: "text" },
      { name: "purpose_and_necessity", label: "目的与必要性论证", type: "textarea" },
      { name: "expectation_control", label: "合理预期与控制程度", type: "textarea" },
      { name: "vulnerable_group", label: "脆弱群体说明", type: "text" },
      { name: "prior_concerns", label: "既有争议/历史缺陷", type: "textarea" },
      { name: "novel_technology", label: "新技术/创新技术情况", type: "textarea" },
      { name: "function_creep_control", label: "防止功能漂移措施", type: "textarea" },
      { name: "minimization_quality", label: "最小化与数据质量措施", type: "textarea" },
      { name: "notice_plan", label: "告知安排", type: "textarea" },
      { name: "rights_support", label: "数据主体权利支持机制", type: "textarea" },
      { name: "processor_management", label: "处理者/供应商管理机制", type: "textarea" }
    ]
  },
  {
    title: "风险与缓解",
    fields: [
      { name: "risk_assessment", label: "风险识别与影响评估", type: "textarea" },
      { name: "mitigation_measures", label: "缓解措施", type: "textarea" },
      { name: "residual_risk", label: "剩余风险", type: "textarea" },
      { name: "signoff_owner", label: "签署/批准责任人", type: "text" },
      { name: "dpo_advice", label: "DPO 意见摘要", type: "textarea" },
      { name: "review_schedule", label: "持续复审安排", type: "text" },
      {
        name: "attachment_role",
        label: "附件角色",
        type: "select",
        options: ["data_flow_diagram", "security_policy", "dpa", "other"]
      }
    ]
  },
  {
    title: "附件材料",
    fields: []
  }
];

const TIA_STEPS: TiaStepConfig[] = [
  {
    title: "传输事实识别",
    fields: [
      { name: "data_exporter_name", label: "数据出口方（EU）", type: "text" },
      { name: "data_importer_name", label: "数据进口方（第三国）", type: "text" },
      { name: "importer_country_region", label: "进口方国家/地区", type: "text" },
      { name: "transfer_purpose", label: "传输目的", type: "textarea" },
      { name: "data_categories", label: "数据类别", type: "text" },
      { name: "sensitive_data_description", label: "敏感/特殊类别数据说明", type: "text" },
      { name: "data_subject_categories", label: "数据主体类别", type: "text" },
      { name: "transfer_frequency", label: "传输频率", type: "select", options: ["one_time", "periodic", "continuous"] },
      { name: "transfer_tool", label: "传输工具", type: "select", options: ["scc", "bcr", "derogation"] }
    ]
  },
  {
    title: "第三国法律评估",
    fields: [
      { name: "law_assessed", label: "是否已完成目的地法律评估", type: "checkbox" },
      { name: "law_findings", label: "法律与实践评估发现", type: "textarea" },
      { name: "pre_effectiveness", label: "补充措施前的有效性判断", type: "textarea" }
    ]
  },
  {
    title: "补充措施与结论",
    fields: [
      { name: "supplementary_technical", label: "技术性补充措施", type: "textarea" },
      { name: "supplementary_contractual", label: "合同性补充措施", type: "textarea" },
      { name: "supplementary_organizational", label: "组织性补充措施", type: "textarea" },
      { name: "post_effectiveness", label: "补充措施后的有效性判断", type: "textarea" },
      { name: "key_actions", label: "关键行动项", type: "textarea" },
      { name: "dpo_opinion", label: "DPO 意见", type: "textarea" },
      { name: "review_date", label: "下次复审日期", type: "text" },
      {
        name: "attachment_role",
        label: "附件角色",
        type: "select",
        options: ["transfer_agreement", "country_law_analysis", "technical_control_doc", "other"]
      }
    ]
  },
  {
    title: "附件材料",
    fields: []
  }
];

const BCR_REVIEW_ITEMS: Array<{ code: string; title: string; legal_basis: string; recommendation: string }> = [
  { code: "3.2-C1", title: "Binding nature and scope", legal_basis: "GDPR Art.47 + EDPB 1/2022", recommendation: "补齐内部约束力、申请主体与范围映射。" },
  { code: "3.2-C2", title: "Material scope and data flow", legal_basis: "EDPB 1/2022 Scope", recommendation: "明确数据类别、主体类别、处理目的和传输范围。" },
  { code: "3.2-C3", title: "Third-party beneficiary rights", legal_basis: "EDPB 1.3.1", recommendation: "明确数据主体可直接主张权利与救济路径。" },
  { code: "3.2-C4", title: "Liability and compensation", legal_basis: "EDPB 1.5/1.6", recommendation: "明确EEA责任主体、赔偿机制与举证责任。" },
  { code: "3.2-C5", title: "Transparency and notice", legal_basis: "EDPB 1.7", recommendation: "补齐公开版本、联系方式与可读性要求。" },
  { code: "3.2-C6", title: "Training and audit effectiveness", legal_basis: "EDPB 3.1/3.3", recommendation: "明确培训与审计频率、职责和整改闭环。" },
  { code: "3.2-C7", title: "Cooperation duty with SA", legal_basis: "EDPB 4.1", recommendation: "补齐监管协作、检查与信息提供义务。" },
  { code: "3.2-C8", title: "Data protection safeguards", legal_basis: "EDPB 5.x", recommendation: "补齐原则、权利、Article 28、记录和DPIA联动。" },
  { code: "3.2-C9", title: "Third-country law and government access", legal_basis: "EDPB 5.4", recommendation: "补齐第三国法律评估与政府访问应对机制。" },
  { code: "3.2-C10", title: "Update and definitions", legal_basis: "EDPB 8.1/9.1", recommendation: "明确更新报送机制与定义表。" }
];

const CN_FLOW_STEPS: CnFlowStepConfig[] = [
  {
    title: "出境数据清单",
    fields: [
      { name: "company_name", label: "企业名称", type: "text" },
      { name: "transfer_purpose", label: "出境目的", type: "textarea" },
      { name: "data_categories", label: "出境数据类别（逗号分隔）", type: "text" },
      { name: "sensitive_data_flags", label: "敏感/重点数据标签（逗号分隔）", type: "text" },
      { name: "data_volume_note", label: "数据规模与体量说明", type: "textarea" },
      { name: "necessity_justification", label: "出境必要性与替代性说明", type: "textarea" }
    ]
  },
  {
    title: "外部实体清单",
    fields: [
      { name: "primary_recipient_name", label: "主要接收方名称", type: "text" },
      { name: "primary_recipient_country", label: "主要接收方国家/地区", type: "text" },
      {
        name: "primary_recipient_role",
        label: "主要接收方角色",
        type: "select",
        options: ["processor", "controller", "subprocessor", "affiliate", "vendor"]
      },
      { name: "primary_recipient_restricted", label: "主要接收方是否受限主体", type: "checkbox" },
      {
        name: "additional_recipients",
        label: "其他接收方（每行：名称,国家,角色,是否受限[yes/no]）",
        type: "textarea"
      },
      { name: "transfer_chain", label: "传输链路说明", type: "textarea" }
    ]
  },
  {
    title: "内部访问与材料",
    fields: [
      { name: "internal_access_note", label: "内部员工访问风险说明（可选）", type: "textarea" }
    ]
  },
  {
    title: "附件上传",
    fields: []
  }
];

const CPRA_STEPS: CpraStepConfig[] = [
  {
    title: "企业信息与适用性",
    fields: [
      { name: "company_name", label: "企业名称", type: "text" },
      { name: "dba_name", label: "DBA/品牌名（可选）", type: "text" },
      { name: "cpra_applicability_selfcheck", label: "CPRA适用性自检结论", type: "textarea" },
      { name: "business_model", label: "业务模型", type: "text" }
    ]
  },
  {
    title: "数据处理活动",
    fields: [
      { name: "data_lifecycle", label: "数据生命周期描述", type: "textarea" },
      { name: "data_categories", label: "处理数据类别", type: "text" },
      { name: "notice_and_consent", label: "告知与同意机制", type: "textarea" },
      { name: "privacy_policy_url", label: "隐私政策URL（可选）", type: "text" }
    ]
  },
  {
    title: "消费者权利机制",
    fields: [
      { name: "consumer_rights_process", label: "DSR受理渠道与流程", type: "textarea" },
      { name: "identity_verification_method", label: "身份验证方法", type: "textarea" },
      { name: "rights_sla", label: "处理时限/SLA说明", type: "textarea" }
    ]
  },
  {
    title: "敏感信息与第三方管理",
    fields: [
      { name: "opt_out_and_sale_sharing", label: "出售/共享与Opt-out机制", type: "textarea" },
      { name: "spi_usage_summary", label: "敏感个人信息（SPI）使用说明", type: "textarea" },
      { name: "vendor_management", label: "供应商/第三方管理机制", type: "textarea" },
      { name: "ui_dark_pattern_check", label: "UI/UX暗模式风险检查", type: "textarea" },
      { name: "review_focus", label: "本次重点整改关注项", type: "textarea" }
    ]
  },
  {
    title: "附件上传",
    fields: []
  }
];

const asRecord = (value: unknown): Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {};

const toString = (value: unknown, fallback = ""): string => (typeof value === "string" ? value : fallback);
const toNumber = (value: unknown, fallback = 0): number =>
  typeof value === "number" && Number.isFinite(value) ? value : fallback;
const toBoolean = (value: unknown, fallback = false): boolean => (typeof value === "boolean" ? value : fallback);

const toRouteType = (value: unknown): PipiaRouteType =>
  value === "certification" ? "certification" : "scc_filing";

const toAttachmentRole = (value: unknown): PipiaAttachmentRole => {
  if (value === "certification_material") return "certification_material";
  if (value === "internal_policy") return "internal_policy";
  if (value === "supporting_evidence") return "supporting_evidence";
  return "scc_contract";
};

const splitCsv = (value: string): string[] =>
  value
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);

const hasText = (value: string, minLength = 2): boolean => value.trim().length >= minLength;

const assertInput = (condition: boolean, message: string): void => {
  if (!condition) {
    throw new Error(message);
  }
};

const basenameFromPath = (path: string): string => {
  const normalized = path.replace(/\\/g, "/");
  const chunks = normalized.split("/");
  return chunks[chunks.length - 1] || "attachment.txt";
};

const inferAttachmentFormat = (value: string): "doc" | "docx" | "pdf" | "txt" | "md" | "json" | "csv" => {
  const suffix = value.split(".").pop()?.toLowerCase();
  if (suffix === "doc") return "doc";
  if (suffix === "docx") return "docx";
  if (suffix === "pdf") return "pdf";
  if (suffix === "md") return "md";
  if (suffix === "json") return "json";
  if (suffix === "csv") return "csv";
  return "txt";
};

const inferDocxPdfFormat = (value: string): "docx" | "pdf" | null => {
  const suffix = value.split(".").pop()?.toLowerCase();
  if (suffix === "docx") return "docx";
  if (suffix === "pdf") return "pdf";
  return null;
};

const inferDpiaAttachmentFormat = (value: string): "docx" | "pdf" | "png" | "jpg" | null => {
  const suffix = value.split(".").pop()?.toLowerCase();
  if (suffix === "docx") return "docx";
  if (suffix === "pdf") return "pdf";
  if (suffix === "png") return "png";
  if (suffix === "jpg" || suffix === "jpeg") return "jpg";
  return null;
};

const inferCnFlowAttachmentFormat = (value: string): "xlsx" | "csv" | "docx" | "pdf" | null => {
  const suffix = value.split(".").pop()?.toLowerCase();
  if (suffix === "xlsx") return "xlsx";
  if (suffix === "csv") return "csv";
  if (suffix === "docx") return "docx";
  if (suffix === "pdf") return "pdf";
  return null;
};

const inferCpraAttachmentFormat = (value: string): "docx" | "pdf" | "xlsx" | "csv" | null => {
  const suffix = value.split(".").pop()?.toLowerCase();
  if (suffix === "docx") return "docx";
  if (suffix === "pdf") return "pdf";
  if (suffix === "xlsx") return "xlsx";
  if (suffix === "csv") return "csv";
  return null;
};

const isValidUrl = (value: string): boolean => /^https?:\/\/\S+$/i.test(value.trim());

const parseRecipientRows = (raw: string): Array<{
  entity_name: string;
  country_region: string;
  entity_role: CnFlowRecipientRole;
  is_restricted_party: boolean;
}> => {
  const rows = raw
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  return rows.flatMap((line) => {
    const [name = "", country = "", role = "", restricted = ""] = line.split(/[,\|]/).map((part) => part.trim());
    if (!hasText(name) || !hasText(country)) return [];
    const entityRole: CnFlowRecipientRole =
      role === "controller" || role === "subprocessor" || role === "affiliate" || role === "vendor"
        ? role
        : "processor";
    const restrictedNormalized = restricted.toLowerCase();
    const isRestricted = ["yes", "true", "1", "是", "受限", "high"].includes(restrictedNormalized);
    return [
      {
        entity_name: name,
        country_region: country,
        entity_role: entityRole,
        is_restricted_party: isRestricted
      }
    ];
  });
};

const toBcrScore = (value: string): "compliant" | "partial" | "non_compliant" => {
  const len = value.trim().length;
  if (len >= 48) return "compliant";
  if (len >= 16) return "partial";
  return "non_compliant";
};

const composeBcrFinding = (score: "compliant" | "partial" | "non_compliant", evidence: string): string => {
  if (score === "compliant") return `已覆盖核心要求：${evidence}`;
  if (score === "partial") return `条款已涉及但表述不充分：${evidence}`;
  return `尚未形成可执行机制：${evidence}`;
};

const createDefaultAssessmentValues = (): AssessmentFormValues => {
  const demo = asRecord(getDefaultPayload("assessment"));
  return {
    company_name: toString(demo.company_name, ""),
    company_uscc: "91310000XXXXXXXXXX",
    legal_representative: "",
    registered_address: "",
    company_nature: "",
    industry: toString(demo.industry, ""),
    assessment_start_date: "",
    assessment_end_date: "",
    lead_department: "",
    participant_departments: "",
    third_party_support: false,
    third_party_name: "",
    third_party_scope: "",
    scenario_name: "",
    receiver_name: "",
    transfer_frequency: "periodic",
    is_long_term: true,
    legal_basis: "",
    necessity_basis: "",
    receiver_country: toString(demo.receiver_country, ""),
    is_ciio: toBoolean(demo.is_ciio, false),
    contains_important_data: toBoolean(demo.contains_important_data, false),
    pii_count: toNumber(demo.pii_count, 0),
    spi_count: toNumber(demo.spi_count, 0),
    transfer_purpose: toString(demo.transfer_purpose, ""),
    data_inventory_summary: "",
    system_chain_summary: "",
    security_capability_summary: "",
    force_override_path: toBoolean(demo.force_override_path, true)
  };
};

const createDefaultDiagnosisValues = (): DiagnosisFormValues => {
  const demo = asRecord(getDefaultPayload("diagnosis"));
  const answers = asRecord(demo.answers);
  return {
    company_name: toString(demo.company_name, ""),
    q5_no_personal_info:
      answers.q5_no_personal_info === "yes" || answers.q5_no_personal_info === "unknown"
        ? answers.q5_no_personal_info
        : "no",
    q6_scenario:
      answers.q6_scenario === "contract_performance" ||
      answers.q6_scenario === "hr_management" ||
      answers.q6_scenario === "emergency" ||
      answers.q6_scenario === "legal_duty"
        ? answers.q6_scenario
        : "other",
    q7_receiver_type: answers.q7_receiver_type === "intra_group" ? "intra_group" : "third_party",
    q1_is_ciio: answers.q1_is_ciio === "yes" || answers.q1_is_ciio === "unknown" ? answers.q1_is_ciio : "no",
    q2_has_important_data:
      answers.q2_has_important_data === "yes" || answers.q2_has_important_data === "unknown"
        ? answers.q2_has_important_data
        : "no",
    q3_pii_count: toNumber(answers.q3_pii_count, 0),
    q4_spi_count: toNumber(answers.q4_spi_count, 0),
    q8_purpose: toString(answers.q8_purpose, "")
  };
};

const createDefaultPipiaValues = (): PipiaFormValues => {
  const demo = asRecord(getDefaultPayload("pipia"));
  const companyProfile = asRecord(demo.company_profile);
  const transferContext = asRecord(demo.transfer_context);
  const personalInfoScope = asRecord(demo.personal_info_scope);
  const rightsProtection = asRecord(demo.rights_protection);
  const emergencyPlan = asRecord(demo.emergency_plan);
  const firstAttachment =
    Array.isArray(demo.attachments) && demo.attachments.length > 0
      ? asRecord(demo.attachments[0])
      : {};

  return {
    company_name: toString(companyProfile.company_name, ""),
    company_uscc: toString(companyProfile.company_uscc, ""),
    industry: toString(companyProfile.industry, ""),
    shareholding_structure: "",
    actual_controller: "",
    overseas_investment: "",
    org_structure_privacy_team: "",
    business_overview: "",
    processing_activity_overview: "",
    is_ciio: toBoolean(companyProfile.is_ciio, false),
    processing_person_count: toNumber(companyProfile.processing_person_count, 0),
    outbound_pi_count: toNumber(companyProfile.outbound_pi_count, 0),
    outbound_spi_count: toNumber(companyProfile.outbound_spi_count, 0),
    route_type: toRouteType(demo.route_type),
    outbound_scenario_name: "",
    outbound_frequency: "periodic",
    transfer_method: "",
    domestic_storage: "",
    overseas_storage: "",
    transfer_link: "",
    purpose: toString(transferContext.purpose, ""),
    recipient_name: toString(transferContext.recipient_name, ""),
    recipient_country_region: toString(transferContext.recipient_country_region, ""),
    legal_basis: toString(transferContext.legal_basis, ""),
    legality_justification: "",
    necessity_justification: "",
    pi_categories: Array.isArray(personalInfoScope.pi_categories)
      ? personalInfoScope.pi_categories.filter((item): item is string => typeof item === "string").join(",")
      : "",
    spi_categories: Array.isArray(personalInfoScope.spi_categories)
      ? personalInfoScope.spi_categories.filter((item): item is string => typeof item === "string").join(",")
      : "",
    subject_volume: toNumber(personalInfoScope.subject_volume, 0),
    notice_mechanism: toString(rightsProtection.notice_mechanism, ""),
    consent_mechanism: toString(rightsProtection.consent_mechanism, ""),
    dsar_channel: toString(rightsProtection.dsar_channel, ""),
    retention_policy: toString(rightsProtection.retention_policy, ""),
    incident_response_sla_hours: toNumber(emergencyPlan.incident_response_sla_hours, 24),
    escalation_path: toString(emergencyPlan.escalation_path, ""),
    attachment_role: toAttachmentRole(firstAttachment.file_role)
  };
};

const createDefaultDocumentReviewValues = (): DocumentReviewFormValues => {
  const demo = asRecord(getDefaultPayload("scc"));
  return {
    company_name: toString(demo.company_name, ""),
    document_title: "隐私政策",
    document_version: "v1.0",
    effective_date: "",
    applicable_products: "",
    applicable_scope: "",
    publisher_entity: "",
    is_live_version: true,
    document_type: "privacy_policy",
    receiver_name: toString(demo.receiver_name, ""),
    receiver_country: toString(demo.receiver_country, ""),
    transfer_purpose: toString(demo.transfer_purpose, ""),
    processor_identity_disclosed: false,
    scope_disclosed: false,
    collection_purpose_disclosed: false,
    processing_method_disclosed: false,
    category_disclosed: false,
    sensitive_pi_disclosed: false,
    crossborder_rule_disclosed: false,
    rights_channel_disclosed: false,
    contact_channel: "",
    pii_count: toNumber(demo.pii_count, 0),
    spi_count: toNumber(demo.spi_count, 0),
    has_scc_draft: toBoolean(demo.has_scc_draft, false),
    review_focus: "重点审查出境告知、敏感信息处理、个人权利与救济条款。"
  };
};

const createDefaultEuSccValues = (): EuSccFormValues => {
  const demo = asRecord(getDefaultPayload("scc"));
  return {
    exporter_name: toString(demo.company_name, ""),
    importer_name: toString(demo.receiver_name, ""),
    importer_country: toString(demo.receiver_country, ""),
    transfer_role: "c2p",
    scc_version: "eu_2021",
    transfer_purpose: toString(demo.transfer_purpose, ""),
    data_categories: "",
    data_subject_categories: "",
    transfer_frequency: "periodic",
    retention_rule: "",
    tom_summary: "",
    onward_transfer_control: "",
    rights_and_complaint: "",
    government_access_response: "",
    supplementary_clause_review: "",
    pii_count: toNumber(demo.pii_count, 0),
    spi_count: toNumber(demo.spi_count, 0),
    has_scc_draft: toBoolean(demo.has_scc_draft, true)
  };
};

const createDefaultBcrValues = (): BcrFormValues => {
  const demo = asRecord(getDefaultPayload("bcr"));
  return {
    company_name: toString(demo.company_name, ""),
    group_structure: "",
    applicant_entity: "",
    data_flow_scope: "",
    lead_sa_rationale: "",
    binding_mechanism: "",
    third_party_beneficiary: "",
    liability_compensation: "",
    transparency_notice: "",
    training_audit: "",
    cooperation_with_sa: "",
    dp_safeguards: "",
    third_country_assessment: "",
    government_access_process: "",
    update_mechanism: "",
    definitions_quality: "",
    review_focus: "优先检查第三国法律评估机制、第三方受益人权利和责任承担条款。"
  };
};

const createDefaultDpiaValues = (): DpiaFormValues => {
  const demo = asRecord(getDefaultPayload("dpia"));
  return {
    project_name: toString(demo.project_name, ""),
    project_goal: "",
    need_reason: "",
    controller_name: "",
    dpo_role: "",
    contact_channel: "",
    processing_description: toString(demo.processing_description, ""),
    data_types: "",
    includes_special_data: false,
    subject_scale: "",
    frequency: "",
    retention_period: "",
    geo_scope: "",
    has_crossborder_transfer: false,
    data_source: "",
    relationship_context: "",
    expectation_control: "",
    vulnerable_group: "",
    prior_concerns: "",
    novel_technology: "",
    lawful_basis: toString(demo.lawful_basis, ""),
    purpose_and_necessity: toString(demo.purpose_and_necessity, ""),
    function_creep_control: "",
    minimization_quality: "",
    notice_plan: "",
    rights_support: "",
    processor_management: "",
    risk_assessment: toString(demo.risk_assessment, ""),
    mitigation_measures: toString(demo.mitigation_measures, ""),
    residual_risk: toString(demo.residual_risk, ""),
    signoff_owner: "",
    dpo_advice: "",
    review_schedule: "",
    attachment_role: "data_flow_diagram"
  };
};

const createDefaultTiaValues = (): TiaFormValues => {
  const demo = asRecord(getDefaultPayload("tia"));
  const transferToolRaw = toString(demo.transfer_tool, "scc");
  const transferTool: TiaFormValues["transfer_tool"] =
    transferToolRaw === "bcr" || transferToolRaw === "derogation" ? transferToolRaw : "scc";
  return {
    data_exporter_name: "",
    data_importer_name: "",
    importer_country_region: "",
    transfer_purpose: "",
    data_categories: "",
    sensitive_data_description: "",
    data_subject_categories: "",
    transfer_frequency: "periodic",
    transfer_tool: transferTool,
    law_assessed: true,
    law_findings: toString(demo.third_country_assessment, ""),
    pre_effectiveness: "",
    supplementary_technical: "",
    supplementary_contractual: "",
    supplementary_organizational: "",
    post_effectiveness: "",
    key_actions: "",
    dpo_opinion: "",
    review_date: "",
    attachment_role: "country_law_analysis"
  };
};

const createDefaultCnFlowValues = (): CnFlowFormValues => {
  const demo = asRecord(getDefaultPayload("cn_flow"));
  const recipient = Array.isArray(demo.recipient_entities) && demo.recipient_entities.length > 0
    ? asRecord(demo.recipient_entities[0])
    : {};
  const roleRaw = toString(recipient.entity_role, "processor");
  const primaryRole: CnFlowRecipientRole =
    roleRaw === "controller" || roleRaw === "subprocessor" || roleRaw === "affiliate" || roleRaw === "vendor"
      ? roleRaw
      : "processor";
  return {
    company_name: toString(demo.company_name, ""),
    transfer_purpose: toString(demo.transfer_purpose, ""),
    data_categories: Array.isArray(demo.data_categories)
      ? demo.data_categories.filter((item): item is string => typeof item === "string").join(",")
      : "",
    sensitive_data_flags: Array.isArray(demo.sensitive_data_flags)
      ? demo.sensitive_data_flags.filter((item): item is string => typeof item === "string").join(",")
      : "",
    transfer_chain: toString(demo.transfer_chain, ""),
    data_volume_note: "",
    necessity_justification: "",
    primary_recipient_name: toString(recipient.entity_name, ""),
    primary_recipient_country: toString(recipient.country_region, ""),
    primary_recipient_role: primaryRole,
    primary_recipient_restricted: toBoolean(recipient.is_restricted_party, false),
    additional_recipients: "",
    internal_access_note: ""
  };
};

const createDefaultCpraValues = (): CpraFormValues => {
  const demo = asRecord(getDefaultPayload("cpra"));
  return {
    company_name: toString(demo.company_name, ""),
    dba_name: "",
    cpra_applicability_selfcheck: "",
    business_model: toString(demo.business_model, ""),
    data_lifecycle: toString(demo.data_lifecycle, ""),
    data_categories: "",
    notice_and_consent: toString(demo.notice_and_consent, ""),
    privacy_policy_url: "",
    consumer_rights_process: toString(demo.consumer_rights_process, ""),
    identity_verification_method: "",
    rights_sla: "",
    opt_out_and_sale_sharing: toString(demo.opt_out_and_sale_sharing, ""),
    spi_usage_summary: "",
    vendor_management: toString(demo.vendor_management, ""),
    ui_dark_pattern_check: "",
    review_focus: "优先检查消费者权利响应时限、SPI限制与Do Not Sell/Share入口。"
  };
};

const readStringArray = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];

const RECOMMENDED_PATH_LABEL: Record<string, { zh: string; en: string }> = {
  security_assessment: { zh: "安全评估路径", en: "Security Assessment Path" },
  scc_or_certification: { zh: "标准合同备案/认证路径", en: "SCC Filing / Certification Path" },
  exemption: { zh: "豁免路径", en: "Exemption Path" }
};

const ROUTE_TYPE_LABEL: Record<string, { zh: string; en: string }> = {
  scc_filing: { zh: "标准合同备案", en: "SCC Filing" },
  certification: { zh: "认证路径", en: "Certification Path" }
};

const DOCUMENT_TYPE_LABEL: Record<DocumentReviewFormValues["document_type"], string> = {
  privacy_policy: "隐私政策",
  scc_contract: "标准合同",
  dpa: "数据处理协议",
  other: "其他文档"
};

const toFileName = (value: string): string => {
  const name = basenameFromPath(value);
  return name || value;
};

const buildUserFacingResult = (response: unknown, lang: "zh" | "en"): UserFacingResult => {
  const copy = lang === "zh"
    ? {
      noHeadline: "已完成运行并生成可用结果",
      pathPrefix: "建议路径",
      routePrefix: "建议流程",
      reportDone: "文档草案已生成",
      riskPrefix: "风险等级",
      issuePrefix: "一致性提醒",
      chapterPrefix: "章节生成",
      regPrefix: "法规命中",
      filesPrefix: "交付文件",
      defaultStep1: "先查看本页“关键结果”，确认路径和风险等级是否符合预期。",
      defaultStep2: "再进入结果面板和报告中心进行内容复核与交付。"
    }
    : {
      noHeadline: "Run completed with user-ready results",
      pathPrefix: "Suggested Path",
      routePrefix: "Suggested Workflow",
      reportDone: "Draft documents generated",
      riskPrefix: "Risk Level",
      issuePrefix: "Consistency Alerts",
      chapterPrefix: "Chapters",
      regPrefix: "Regulation Hits",
      filesPrefix: "Deliverables",
      defaultStep1: "Review key outcomes on this panel and confirm path/risk alignment.",
      defaultStep2: "Then continue to result panel and report center for final review."
    };

  const insight = extractInsight(response);
  const responseRecord = asRecord(response);
  const resultRecord = asRecord(responseRecord.result);

  const recommendedPathRaw = toString(responseRecord.recommended_path) || toString(resultRecord.recommended_path);
  const recommendedPathLabel = recommendedPathRaw
    ? (RECOMMENDED_PATH_LABEL[recommendedPathRaw]?.[lang] ?? recommendedPathRaw)
    : "";

  const routeTypeRaw = toString(responseRecord.route_type);
  const routeTypeLabel = routeTypeRaw ? (ROUTE_TYPE_LABEL[routeTypeRaw]?.[lang] ?? routeTypeRaw) : "";

  const riskLevel = insight.riskLevel || toString(responseRecord.risk_level) || toString(resultRecord.risk_level);
  const rationale = toString(resultRecord.rationale);
  const legalBasis = readStringArray(resultRecord.legal_basis);
  const actionItems = readStringArray(resultRecord.action_items);

  const chapters = Array.isArray(responseRecord.chapters) ? responseRecord.chapters.filter(asRecord) : [];
  const regulations = Array.isArray(responseRecord.regulations) ? responseRecord.regulations.filter(asRecord) : [];

  const deliverableNames = Array.from(
    new Set(
      [insight.reportPath, ...Object.values(insight.outputFiles)]
        .filter((item): item is string => typeof item === "string" && item.length > 0)
        .map((item) => toFileName(item))
    )
  );

  let headline = copy.noHeadline;
  if (recommendedPathLabel) {
    headline = `${copy.pathPrefix}：${recommendedPathLabel}`;
  } else if (routeTypeLabel) {
    headline = `${copy.routePrefix}：${routeTypeLabel}`;
  } else if (deliverableNames.length > 0) {
    headline = copy.reportDone;
  }

  const chips: string[] = [];
  if (riskLevel) chips.push(`${copy.riskPrefix}：${riskLevel}`);
  if (insight.consistencyIssues.length > 0) chips.push(`${copy.issuePrefix}：${insight.consistencyIssues.length}`);
  if (chapters.length > 0) chips.push(`${copy.chapterPrefix}：${chapters.length}`);
  if (regulations.length > 0) chips.push(`${copy.regPrefix}：${regulations.length}`);
  if (deliverableNames.length > 0) chips.push(`${copy.filesPrefix}：${deliverableNames.length}`);

  const highlights: string[] = [];
  if (rationale) highlights.push(rationale);
  if (legalBasis.length > 0) highlights.push(legalBasis.slice(0, 3).join("；"));
  if (insight.consistencyIssues.length > 0) highlights.push(...insight.consistencyIssues.slice(0, 3));
  if (highlights.length === 0 && regulations.length > 0) {
    const topTitles = regulations
      .map((item) => toString(item.title))
      .filter((item): item is string => typeof item === "string" && item.length > 0)
      .slice(0, 3);
    if (topTitles.length > 0) highlights.push(topTitles.join("；"));
  }

  const nextSteps = actionItems.length > 0 ? actionItems.slice(0, 4) : [copy.defaultStep1, copy.defaultStep2];

  return {
    headline,
    chips,
    deliverables: deliverableNames,
    highlights,
    nextSteps
  };
};

void buildUserFacingResult;

export function ModuleRunPanel({ onRunDone, taskSpace }: ModuleRunPanelProps) {
  const { t, lang } = useLang();
  const [jurisdiction, setJurisdiction] = useState<(typeof JURISDICTIONS)[number]>(taskSpace.jurisdiction);
  const [moduleKey, setModuleKey] = useState<ModuleKey>(taskSpace.module);
  const [runMode, setRunMode] = useState<RunMode>("sync");
  const [payloadText, setPayloadText] = useState("");
  const [responseData, setResponseData] = useState<unknown>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [diagnosisStepIndex, setDiagnosisStepIndex] = useState(0);
  const [diagnosisValues, setDiagnosisValues] = useState<DiagnosisFormValues>(createDefaultDiagnosisValues);
  const [assessmentStepIndex, setAssessmentStepIndex] = useState(0);
  const [assessmentValues, setAssessmentValues] = useState<AssessmentFormValues>(createDefaultAssessmentValues);
  const [assessmentFiles, setAssessmentFiles] = useState<File[]>([]);
  const [pipiaStepIndex, setPipiaStepIndex] = useState(0);
  const [pipiaValues, setPipiaValues] = useState<PipiaFormValues>(createDefaultPipiaValues);
  const [pipiaFiles, setPipiaFiles] = useState<File[]>([]);
  const [documentReviewStepIndex, setDocumentReviewStepIndex] = useState(0);
  const [documentReviewValues, setDocumentReviewValues] = useState<DocumentReviewFormValues>(createDefaultDocumentReviewValues);
  const [documentReviewFiles, setDocumentReviewFiles] = useState<File[]>([]);
  const [euSccStepIndex, setEuSccStepIndex] = useState(0);
  const [euSccValues, setEuSccValues] = useState<EuSccFormValues>(createDefaultEuSccValues);
  const [euSccFiles, setEuSccFiles] = useState<File[]>([]);
  const [bcrStepIndex, setBcrStepIndex] = useState(0);
  const [bcrValues, setBcrValues] = useState<BcrFormValues>(createDefaultBcrValues);
  const [bcrFiles, setBcrFiles] = useState<File[]>([]);
  const [dpiaStepIndex, setDpiaStepIndex] = useState(0);
  const [dpiaValues, setDpiaValues] = useState<DpiaFormValues>(createDefaultDpiaValues);
  const [dpiaFiles, setDpiaFiles] = useState<File[]>([]);
  const [tiaStepIndex, setTiaStepIndex] = useState(0);
  const [tiaValues, setTiaValues] = useState<TiaFormValues>(createDefaultTiaValues);
  const [tiaFiles, setTiaFiles] = useState<File[]>([]);
  const [cnFlowStepIndex, setCnFlowStepIndex] = useState(0);
  const [cnFlowValues, setCnFlowValues] = useState<CnFlowFormValues>(createDefaultCnFlowValues);
  const [cnFlowDataInventoryFiles, setCnFlowDataInventoryFiles] = useState<File[]>([]);
  const [cnFlowEntityInventoryFiles, setCnFlowEntityInventoryFiles] = useState<File[]>([]);
  const [cnFlowSupportingFiles, setCnFlowSupportingFiles] = useState<File[]>([]);
  const [cpraStepIndex, setCpraStepIndex] = useState(0);
  const [cpraValues, setCpraValues] = useState<CpraFormValues>(createDefaultCpraValues);
  const [cpraPrivacyPolicyFiles, setCpraPrivacyPolicyFiles] = useState<File[]>([]);
  const [cpraRightsSopFiles, setCpraRightsSopFiles] = useState<File[]>([]);
  const [cpraDataMapFiles, setCpraDataMapFiles] = useState<File[]>([]);
  const [cpraVendorListFiles, setCpraVendorListFiles] = useState<File[]>([]);
  const [cpraOtherFiles, setCpraOtherFiles] = useState<File[]>([]);

  const taskTemplate = findTaskTemplate(taskSpace.taskTemplateId);
  const templateModule = useMemo(
    () => listModules().find((item) => item.key === taskSpace.module),
    [taskSpace.module]
  );
  const lockedModule = !!taskTemplate && !!templateModule;

  const modules = useMemo(() => {
    if (lockedModule && templateModule) {
      return [templateModule];
    }
    return listModules().filter((item) => item.jurisdiction === jurisdiction);
  }, [jurisdiction, lockedModule, templateModule]);

  const userFacingResult = useMemo(() => buildUserFacingResult(responseData, lang), [responseData, lang]);

  useEffect(() => {
    setJurisdiction(taskSpace.jurisdiction);
    setModuleKey(taskSpace.module);
  }, [taskSpace.jurisdiction, taskSpace.module]);

  useEffect(() => {
    if (!modules.find((item) => item.key === moduleKey)) {
      setModuleKey(modules[0]?.key ?? "diagnosis");
    }
  }, [moduleKey, modules]);

  useEffect(() => {
    setPayloadText(JSON.stringify(getDefaultPayload(moduleKey), null, 2));
    setResponseData(undefined);
    setError(null);
    if (moduleKey === "diagnosis") {
      setDiagnosisStepIndex(0);
      setDiagnosisValues(createDefaultDiagnosisValues());
    }
    if (moduleKey === "assessment") {
      setAssessmentStepIndex(0);
      setAssessmentValues(createDefaultAssessmentValues());
      setAssessmentFiles([]);
    }
    if (moduleKey === "pipia") {
      setPipiaStepIndex(0);
      setPipiaValues(createDefaultPipiaValues());
      setPipiaFiles([]);
    }
    if (taskTemplate?.id === "cn_document_review") {
      setDocumentReviewStepIndex(0);
      setDocumentReviewValues(createDefaultDocumentReviewValues());
      setDocumentReviewFiles([]);
    }
    if (taskTemplate?.id === "eu_scc") {
      setEuSccStepIndex(0);
      setEuSccValues(createDefaultEuSccValues());
      setEuSccFiles([]);
    }
    if (moduleKey === "bcr") {
      setBcrStepIndex(0);
      setBcrValues(createDefaultBcrValues());
      setBcrFiles([]);
    }
    if (moduleKey === "dpia") {
      setDpiaStepIndex(0);
      setDpiaValues(createDefaultDpiaValues());
      setDpiaFiles([]);
    }
    if (moduleKey === "tia") {
      setTiaStepIndex(0);
      setTiaValues(createDefaultTiaValues());
      setTiaFiles([]);
    }
    if (moduleKey === "cn_flow") {
      setCnFlowStepIndex(0);
      setCnFlowValues(createDefaultCnFlowValues());
      setCnFlowDataInventoryFiles([]);
      setCnFlowEntityInventoryFiles([]);
      setCnFlowSupportingFiles([]);
    }
    if (moduleKey === "cpra") {
      setCpraStepIndex(0);
      setCpraValues(createDefaultCpraValues());
      setCpraPrivacyPolicyFiles([]);
      setCpraRightsSopFiles([]);
      setCpraDataMapFiles([]);
      setCpraVendorListFiles([]);
      setCpraOtherFiles([]);
    }
  }, [moduleKey, taskTemplate?.id]);

  const definition = findModule(moduleKey);
  const allowAsync = hasAsync(definition);
  const isDocumentReviewTask = taskTemplate?.id === "cn_document_review";
  const isEuSccTask = taskTemplate?.id === "eu_scc";
  const isDiagnosisModule = moduleKey === "diagnosis";
  const isAssessmentModule = moduleKey === "assessment";
  const isPipiaModule = moduleKey === "pipia";
  const isBcrModule = moduleKey === "bcr";
  const isDpiaModule = moduleKey === "dpia";
  const isTiaModule = moduleKey === "tia";
  const isCnFlowModule = moduleKey === "cn_flow";
  const isCpraModule = moduleKey === "cpra";

  const updateDiagnosisValue = <K extends keyof DiagnosisFormValues>(name: K, value: DiagnosisFormValues[K]) => {
    setDiagnosisValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateAssessmentValue = <K extends keyof AssessmentFormValues>(name: K, value: AssessmentFormValues[K]) => {
    setAssessmentValues((prev) => ({ ...prev, [name]: value }));
  };

  const updatePipiaValue = <K extends keyof PipiaFormValues>(name: K, value: PipiaFormValues[K]) => {
    setPipiaValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateDocumentReviewValue = <K extends keyof DocumentReviewFormValues>(
    name: K,
    value: DocumentReviewFormValues[K]
  ) => {
    setDocumentReviewValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateEuSccValue = <K extends keyof EuSccFormValues>(name: K, value: EuSccFormValues[K]) => {
    setEuSccValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateBcrValue = <K extends keyof BcrFormValues>(name: K, value: BcrFormValues[K]) => {
    setBcrValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateDpiaValue = <K extends keyof DpiaFormValues>(name: K, value: DpiaFormValues[K]) => {
    setDpiaValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateTiaValue = <K extends keyof TiaFormValues>(name: K, value: TiaFormValues[K]) => {
    setTiaValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateCnFlowValue = <K extends keyof CnFlowFormValues>(name: K, value: CnFlowFormValues[K]) => {
    setCnFlowValues((prev) => ({ ...prev, [name]: value }));
  };

  const updateCpraValue = <K extends keyof CpraFormValues>(name: K, value: CpraFormValues[K]) => {
    setCpraValues((prev) => ({ ...prev, [name]: value }));
  };

  const uploadFiles = async (files: File[]): Promise<string[]> => {
    if (files.length === 0) return [];
    const uploadedPaths: string[] = [];
    for (const file of files) {
      const uploaded = await uploadTaskFile(file);
      uploadedPaths.push(uploaded.path);
    }
    return uploadedPaths;
  };

  const buildAssessmentPayload = async (): Promise<unknown> => {
    assertInput(hasText(assessmentValues.company_name), "请填写企业名称。");
    assertInput(hasText(assessmentValues.company_uscc, 8), "请填写统一社会信用代码（至少8位）。");
    assertInput(hasText(assessmentValues.receiver_country), "请填写接收方国家/地区。");
    assertInput(hasText(assessmentValues.transfer_purpose), "请填写出境目的。");
    assertInput(hasText(assessmentValues.legal_basis), "请填写合法性基础。");
    assertInput(hasText(assessmentValues.necessity_basis), "请填写必要性说明。");
    assertInput(hasText(assessmentValues.data_inventory_summary), "请填写数据清单摘要。");
    assertInput(hasText(assessmentValues.system_chain_summary), "请填写系统与出境链路说明。");
    assertInput(
      assessmentFiles.length > 0,
      "请上传至少1份安全评估附件材料（如数据清单、系统链路图、制度文件）。"
    );

    const uploadedFiles = await uploadFiles(assessmentFiles);
    const trimOr = (value: string, fallback: string): string => {
      const trimmed = value.trim();
      return trimmed.length >= 2 ? trimmed : fallback;
    };
    const purposeContext = [
      assessmentValues.transfer_purpose.trim(),
      assessmentValues.scenario_name ? `场景：${assessmentValues.scenario_name}` : "",
      assessmentValues.legal_basis ? `合法性：${assessmentValues.legal_basis}` : "",
      assessmentValues.necessity_basis ? `必要性：${assessmentValues.necessity_basis}` : "",
      assessmentValues.data_inventory_summary ? `数据清单：${assessmentValues.data_inventory_summary}` : "",
      assessmentValues.system_chain_summary ? `链路：${assessmentValues.system_chain_summary}` : "",
      assessmentValues.security_capability_summary ? `保障能力：${assessmentValues.security_capability_summary}` : "",
      assessmentValues.assessment_start_date || assessmentValues.assessment_end_date
        ? `自评估周期：${assessmentValues.assessment_start_date || "未填"} 至 ${assessmentValues.assessment_end_date || "未填"}`
        : "",
      assessmentValues.lead_department ? `牵头部门：${assessmentValues.lead_department}` : "",
      assessmentValues.participant_departments ? `参与部门：${assessmentValues.participant_departments}` : "",
      assessmentValues.third_party_support
        ? `第三方支持：${assessmentValues.third_party_name || "已参与"}；${assessmentValues.third_party_scope || "范围未填"}`
        : ""
    ]
      .filter((item) => item.length > 0)
      .join("；");

    return {
      company_name: trimOr(assessmentValues.company_name, "待确认企业"),
      industry: trimOr(
        [assessmentValues.industry, assessmentValues.company_nature].filter((item) => item.trim().length > 0).join(" / "),
        "未说明行业"
      ),
      is_ciio: assessmentValues.is_ciio,
      contains_important_data: assessmentValues.contains_important_data,
      pii_count: Math.max(0, assessmentValues.pii_count),
      spi_count: Math.max(0, assessmentValues.spi_count),
      transfer_purpose: trimOr(purposeContext, "数据出境场景评估与风险自评估"),
      receiver_country: trimOr(assessmentValues.receiver_country, "待确认国家"),
      force_override_path: assessmentValues.force_override_path,
      uploaded_files: uploadedFiles
    };
  };

  const buildPipiaPayload = async (): Promise<unknown> => {
    assertInput(hasText(pipiaValues.company_name), "请填写处理者名称。");
    assertInput(hasText(pipiaValues.company_uscc, 8), "请填写统一社会信用代码（至少8位）。");
    assertInput(hasText(pipiaValues.purpose), "请填写拟出境活动目的。");
    assertInput(hasText(pipiaValues.recipient_name), "请填写境外接收方名称。");
    assertInput(hasText(pipiaValues.recipient_country_region), "请填写接收方国家/地区。");
    assertInput(hasText(pipiaValues.legal_basis), "请填写处理合法性基础。");
    assertInput(splitCsv(pipiaValues.pi_categories).length > 0, "请至少填写一类拟出境个人信息。");
    assertInput(hasText(pipiaValues.notice_mechanism), "请填写告知机制。");
    assertInput(hasText(pipiaValues.consent_mechanism), "请填写单独同意机制。");
    assertInput(hasText(pipiaValues.dsar_channel), "请填写个人权利请求渠道。");
    assertInput(hasText(pipiaValues.retention_policy), "请填写保存与删除策略。");
    assertInput(pipiaFiles.length > 0, "请上传至少1份PIPIA相关附件。");
    if (pipiaValues.route_type === "scc_filing") {
      assertInput(
        pipiaValues.attachment_role === "scc_contract",
        "标准合同备案路径下，附件角色需选择为 scc_contract。"
      );
    }

    const uploadedFiles = await uploadFiles(pipiaFiles);
    const trimOr = (value: string, fallback: string): string => {
      const trimmed = value.trim();
      return trimmed.length >= 2 ? trimmed : fallback;
    };
    const attachments = uploadedFiles.map((path) => ({
      file_role: pipiaValues.attachment_role,
      file_name: basenameFromPath(path),
      file_format: inferAttachmentFormat(path),
      storage_uri: path
    }));

    return {
      route_type: pipiaValues.route_type,
      company_profile: {
        company_name: trimOr(pipiaValues.company_name, "待确认企业"),
        company_uscc: pipiaValues.company_uscc.trim().length >= 8 ? pipiaValues.company_uscc.trim() : "91310000XXXXXXXXXX",
        is_ciio: pipiaValues.is_ciio,
        processing_person_count: pipiaValues.processing_person_count,
        outbound_pi_count: pipiaValues.outbound_pi_count,
        outbound_spi_count: pipiaValues.outbound_spi_count,
        industry: trimOr(pipiaValues.industry, "未说明行业")
      },
      transfer_context: {
        purpose: trimOr(
          [
            pipiaValues.purpose,
            pipiaValues.outbound_scenario_name ? `场景：${pipiaValues.outbound_scenario_name}` : "",
            pipiaValues.outbound_frequency ? `频率：${pipiaValues.outbound_frequency}` : "",
            pipiaValues.transfer_method ? `方式：${pipiaValues.transfer_method}` : "",
            pipiaValues.business_overview ? `业务概况：${pipiaValues.business_overview}` : "",
            pipiaValues.processing_activity_overview ? `处理活动：${pipiaValues.processing_activity_overview}` : ""
          ].filter((item) => item.trim().length > 0).join("；"),
          "个人信息出境处理活动评估"
        ),
        recipient_name: trimOr(pipiaValues.recipient_name, "待确认接收方"),
        recipient_country_region: trimOr(pipiaValues.recipient_country_region, "待确认国家/地区"),
        legal_basis: trimOr(
          [
            pipiaValues.legal_basis,
            pipiaValues.legality_justification ? `合法性论证：${pipiaValues.legality_justification}` : "",
            pipiaValues.necessity_justification ? `必要性论证：${pipiaValues.necessity_justification}` : ""
          ].filter((item) => item.trim().length > 0).join("；"),
          "合同履行必要"
        )
      },
      personal_info_scope: {
        pi_categories: splitCsv(pipiaValues.pi_categories).length > 0 ? splitCsv(pipiaValues.pi_categories) : ["账户信息"],
        spi_categories: splitCsv(pipiaValues.spi_categories),
        subject_volume: pipiaValues.subject_volume
      },
      rights_protection: {
        notice_mechanism: trimOr(pipiaValues.notice_mechanism, "隐私政策告知"),
        consent_mechanism: trimOr(pipiaValues.consent_mechanism, "单独同意"),
        dsar_channel: trimOr(pipiaValues.dsar_channel, "privacy@example.com"),
        retention_policy: trimOr(
          [
            pipiaValues.retention_policy,
            pipiaValues.domestic_storage ? `境内存储：${pipiaValues.domestic_storage}` : "",
            pipiaValues.overseas_storage ? `境外存储：${pipiaValues.overseas_storage}` : ""
          ].filter((item) => item.trim().length > 0).join("；"),
          "到期删除+最短必要"
        )
      },
      emergency_plan: {
        incident_response_sla_hours: pipiaValues.incident_response_sla_hours,
        escalation_path: trimOr(
          [
            pipiaValues.escalation_path,
            pipiaValues.transfer_link ? `链路：${pipiaValues.transfer_link}` : "",
            pipiaValues.shareholding_structure ? `股权：${pipiaValues.shareholding_structure}` : "",
            pipiaValues.actual_controller ? `控制人：${pipiaValues.actual_controller}` : "",
            pipiaValues.overseas_investment ? `境内外投资：${pipiaValues.overseas_investment}` : "",
            pipiaValues.org_structure_privacy_team ? `组织与个保机构：${pipiaValues.org_structure_privacy_team}` : ""
          ].filter((item) => item.trim().length > 0).join("；"),
          "DPO -> 法务 -> 管理层"
        )
      },
      attachments
    };
  };

  const buildDocumentReviewPayload = async (): Promise<unknown> => {
    assertInput(
      hasText(documentReviewValues.publisher_entity) || hasText(documentReviewValues.company_name),
      "请填写企业名称或发布主体。"
    );
    assertInput(hasText(documentReviewValues.document_title), "请填写文档名称。");
    assertInput(hasText(documentReviewValues.review_focus), "请填写本次审查重点。");
    assertInput(documentReviewFiles.length > 0, "请至少上传1份合同或政策文本后再执行审查。");

    const uploadedFiles = await uploadFiles(documentReviewFiles);
    const trimOr = (value: string, fallback: string): string => {
      const trimmed = value.trim();
      return trimmed.length >= 2 ? trimmed : fallback;
    };
    const reviewContext = [
      documentReviewValues.document_title ? `文档：${documentReviewValues.document_title}` : "",
      documentReviewValues.document_version ? `版本：${documentReviewValues.document_version}` : "",
      documentReviewValues.effective_date ? `生效日期：${documentReviewValues.effective_date}` : "",
      documentReviewValues.applicable_products ? `适用产品：${documentReviewValues.applicable_products}` : "",
      documentReviewValues.applicable_scope ? `适用范围：${documentReviewValues.applicable_scope}` : "",
      documentReviewValues.is_live_version ? "当前线上生效版本" : "非线上生效版本",
      documentReviewValues.transfer_purpose.trim(),
      `${DOCUMENT_TYPE_LABEL[documentReviewValues.document_type]}审查`,
      documentReviewValues.processor_identity_disclosed ? "已披露处理者身份" : "未明确披露处理者身份",
      documentReviewValues.scope_disclosed ? "已披露适用范围" : "未明确披露适用范围",
      documentReviewValues.collection_purpose_disclosed ? "已披露收集与处理目的" : "未充分披露收集与处理目的",
      documentReviewValues.processing_method_disclosed ? "已披露处理方式" : "未充分披露处理方式",
      documentReviewValues.category_disclosed ? "已披露个人信息种类" : "未充分披露个人信息种类",
      documentReviewValues.sensitive_pi_disclosed ? "已披露敏感信息处理" : "未充分披露敏感信息处理",
      documentReviewValues.crossborder_rule_disclosed ? "已披露出境规则" : "未充分披露出境规则",
      documentReviewValues.rights_channel_disclosed ? "已披露权利行使渠道" : "未充分披露权利行使渠道",
      documentReviewValues.contact_channel ? `联系渠道：${documentReviewValues.contact_channel}` : "",
      documentReviewValues.review_focus.trim()
    ]
      .filter((item) => item.length > 0)
      .join("；");

    return {
      company_name: trimOr(documentReviewValues.publisher_entity || documentReviewValues.company_name, "待确认企业"),
      receiver_name: trimOr(documentReviewValues.receiver_name, "待确认接收方"),
      receiver_country: trimOr(documentReviewValues.receiver_country, "待确认国家"),
      transfer_purpose: trimOr(
        reviewContext || documentReviewValues.transfer_purpose,
        "文档合规审查与跨境条款核验"
      ),
      pii_count: Math.max(0, documentReviewValues.pii_count),
      spi_count: Math.max(0, documentReviewValues.spi_count),
      has_scc_draft: documentReviewValues.has_scc_draft || uploadedFiles.length > 0,
      uploaded_files: uploadedFiles
    };
  };

  const buildEuSccPayload = async (): Promise<unknown> => {
    assertInput(hasText(euSccValues.exporter_name), "请填写数据出口方名称。");
    assertInput(hasText(euSccValues.importer_name), "请填写数据进口方名称。");
    assertInput(hasText(euSccValues.importer_country), "请填写进口方国家/地区。");
    assertInput(hasText(euSccValues.transfer_purpose), "请填写传输目的。");
    assertInput(hasText(euSccValues.data_categories), "请填写数据类别。");
    assertInput(hasText(euSccValues.tom_summary), "请填写技术与组织措施（TOM）摘要。");
    assertInput(hasText(euSccValues.rights_and_complaint), "请填写数据主体权利与投诉机制。");
    assertInput(euSccFiles.length > 0, "请上传至少1份SCC文本或配套附件。");

    const uploadedFiles = await uploadFiles(euSccFiles);
    const purposeContext = [
      euSccValues.transfer_purpose.trim(),
      `角色关系：${euSccValues.transfer_role}`,
      `SCC版本：${euSccValues.scc_version}`,
      `数据类别：${euSccValues.data_categories}`,
      euSccValues.data_subject_categories ? `主体类别：${euSccValues.data_subject_categories}` : "",
      `传输频率：${euSccValues.transfer_frequency}`,
      euSccValues.retention_rule ? `保存规则：${euSccValues.retention_rule}` : "",
      euSccValues.tom_summary ? `TOM：${euSccValues.tom_summary}` : "",
      euSccValues.onward_transfer_control ? `再传输：${euSccValues.onward_transfer_control}` : "",
      euSccValues.government_access_response ? `政府访问：${euSccValues.government_access_response}` : "",
      euSccValues.supplementary_clause_review ? `补充条款：${euSccValues.supplementary_clause_review}` : "",
      euSccValues.rights_and_complaint ? `权利救济：${euSccValues.rights_and_complaint}` : ""
    ]
      .filter((item) => item.length > 0)
      .join("；");

    return {
      company_name: euSccValues.exporter_name.trim(),
      receiver_name: euSccValues.importer_name.trim(),
      receiver_country: euSccValues.importer_country.trim(),
      transfer_purpose: purposeContext,
      pii_count: Math.max(0, euSccValues.pii_count),
      spi_count: Math.max(0, euSccValues.spi_count),
      has_scc_draft: euSccValues.has_scc_draft || uploadedFiles.length > 0,
      uploaded_files: uploadedFiles
    };
  };

  const buildBcrPayload = async (): Promise<unknown> => {
    assertInput(hasText(bcrValues.company_name), "请填写集团名称。");
    assertInput(hasText(bcrValues.group_structure), "请填写集团结构与申请主体信息。");
    assertInput(hasText(bcrValues.data_flow_scope), "请填写数据流与处理活动范围。");
    assertInput(hasText(bcrValues.binding_mechanism), "请填写内部约束机制。");
    assertInput(hasText(bcrValues.third_country_assessment), "请填写第三国法律评估机制。");
    assertInput(hasText(bcrValues.government_access_process), "请填写政府访问请求处理机制。");
    assertInput(bcrFiles.length > 0, "请上传至少1份BCR主文本或配套申请材料。");

    const uploadedFiles = await uploadFiles(bcrFiles);
    const attachments = uploadedFiles.map((path) => {
      const format = inferDocxPdfFormat(path);
      assertInput(!!format, `BCR附件仅支持 .docx 或 .pdf：${basenameFromPath(path)}`);
      return {
        file_name: basenameFromPath(path),
        file_format: format,
        storage_uri: path
      };
    });

    const evidenceTexts = [
      `${bcrValues.binding_mechanism} ${bcrValues.lead_sa_rationale}`,
      bcrValues.data_flow_scope,
      bcrValues.third_party_beneficiary,
      bcrValues.liability_compensation,
      bcrValues.transparency_notice,
      bcrValues.training_audit,
      bcrValues.cooperation_with_sa,
      bcrValues.dp_safeguards,
      `${bcrValues.third_country_assessment} ${bcrValues.government_access_process}`,
      `${bcrValues.update_mechanism} ${bcrValues.definitions_quality}`
    ];

    const review_items = BCR_REVIEW_ITEMS.map((item, index) => {
      const evidence = evidenceTexts[index]?.trim() || "未提供";
      const score = toBcrScore(evidence);
      return {
        code: item.code,
        title: item.title,
        score,
        finding: composeBcrFinding(score, evidence.slice(0, 180)),
        legal_basis: item.legal_basis,
        recommendation: bcrValues.review_focus
          ? `${item.recommendation} 本轮重点：${bcrValues.review_focus}`
          : item.recommendation,
        evidence
      };
    });

    return {
      company_name: bcrValues.company_name.trim(),
      review_items,
      attachments,
      uploaded_files: uploadedFiles
    };
  };

  const buildDpiaPayload = async (): Promise<unknown> => {
    assertInput(hasText(dpiaValues.project_name), "请填写项目名称。");
    assertInput(hasText(dpiaValues.processing_description), "请填写处理活动描述。");
    assertInput(hasText(dpiaValues.purpose_and_necessity), "请填写目的与必要性说明。");
    assertInput(hasText(dpiaValues.lawful_basis), "请填写合法性基础。");
    assertInput(hasText(dpiaValues.risk_assessment), "请填写风险评估。");
    assertInput(hasText(dpiaValues.mitigation_measures), "请填写缓解措施。");
    assertInput(hasText(dpiaValues.residual_risk), "请填写剩余风险结论。");
    assertInput(dpiaFiles.length > 0, "请上传至少1份DPIA附件（流程图/制度/合同等）。");

    const uploadedFiles = await uploadFiles(dpiaFiles);
    const attachments = uploadedFiles.map((path) => {
      const format = inferDpiaAttachmentFormat(path);
      assertInput(!!format, `DPIA附件仅支持 .docx/.pdf/.png/.jpg：${basenameFromPath(path)}`);
      return {
        file_role: dpiaValues.attachment_role,
        file_name: basenameFromPath(path),
        file_format: format,
        storage_uri: path
      };
    });

    return {
      project_name: dpiaValues.project_name.trim(),
      processing_description: [
        dpiaValues.processing_description,
        dpiaValues.project_goal ? `项目目标：${dpiaValues.project_goal}` : "",
        dpiaValues.data_types ? `数据类型：${dpiaValues.data_types}` : "",
        dpiaValues.subject_scale ? `主体规模：${dpiaValues.subject_scale}` : "",
        dpiaValues.frequency ? `频率：${dpiaValues.frequency}` : "",
        dpiaValues.retention_period ? `保存期限：${dpiaValues.retention_period}` : "",
        dpiaValues.geo_scope ? `地理范围：${dpiaValues.geo_scope}` : "",
        dpiaValues.data_source ? `数据来源：${dpiaValues.data_source}` : "",
        dpiaValues.relationship_context ? `关系背景：${dpiaValues.relationship_context}` : "",
        dpiaValues.includes_special_data ? "包含特殊类别数据" : "",
        dpiaValues.has_crossborder_transfer ? "涉及跨境传输" : "",
        dpiaValues.vulnerable_group ? `脆弱群体：${dpiaValues.vulnerable_group}` : "",
        dpiaValues.novel_technology ? `新技术：${dpiaValues.novel_technology}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      purpose_and_necessity: [
        dpiaValues.purpose_and_necessity,
        dpiaValues.need_reason ? `触发理由：${dpiaValues.need_reason}` : "",
        dpiaValues.expectation_control ? `合理预期：${dpiaValues.expectation_control}` : "",
        dpiaValues.function_creep_control ? `防功能漂移：${dpiaValues.function_creep_control}` : "",
        dpiaValues.minimization_quality ? `最小化与质量：${dpiaValues.minimization_quality}` : "",
        dpiaValues.notice_plan ? `告知安排：${dpiaValues.notice_plan}` : "",
        dpiaValues.rights_support ? `权利支持：${dpiaValues.rights_support}` : "",
        dpiaValues.processor_management ? `处理者管理：${dpiaValues.processor_management}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      lawful_basis: dpiaValues.lawful_basis.trim(),
      risk_assessment: [
        dpiaValues.risk_assessment,
        dpiaValues.prior_concerns ? `历史风险：${dpiaValues.prior_concerns}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      mitigation_measures: [
        dpiaValues.mitigation_measures,
        dpiaValues.signoff_owner ? `签署责任人：${dpiaValues.signoff_owner}` : "",
        dpiaValues.controller_name ? `控制者：${dpiaValues.controller_name}` : "",
        dpiaValues.dpo_role ? `DPO：${dpiaValues.dpo_role}` : "",
        dpiaValues.contact_channel ? `联系渠道：${dpiaValues.contact_channel}` : "",
        dpiaValues.dpo_advice ? `DPO意见：${dpiaValues.dpo_advice}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      residual_risk: [
        dpiaValues.residual_risk,
        dpiaValues.review_schedule ? `复审安排：${dpiaValues.review_schedule}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      attachments
    };
  };

  const buildTiaPayload = async (): Promise<unknown> => {
    assertInput(hasText(tiaValues.data_exporter_name), "请填写数据出口方名称。");
    assertInput(hasText(tiaValues.data_importer_name), "请填写数据进口方名称。");
    assertInput(hasText(tiaValues.importer_country_region), "请填写进口方国家/地区。");
    assertInput(hasText(tiaValues.transfer_purpose), "请填写传输目的。");
    assertInput(hasText(tiaValues.law_findings), "请填写第三国法律评估发现。");
    assertInput(hasText(tiaValues.supplementary_technical), "请填写技术性补充措施。");
    assertInput(hasText(tiaValues.post_effectiveness), "请填写补充措施后的有效性判断。");
    assertInput(hasText(tiaValues.key_actions), "请填写关键行动项。");
    assertInput(tiaFiles.length > 0, "请上传至少1份TIA附件。");

    const uploadedFiles = await uploadFiles(tiaFiles);
    const attachments = uploadedFiles.map((path) => {
      const format = inferDocxPdfFormat(path);
      assertInput(!!format, `TIA附件仅支持 .docx 或 .pdf：${basenameFromPath(path)}`);
      return {
        file_role: tiaValues.attachment_role,
        file_name: basenameFromPath(path),
        file_format: format,
        storage_uri: path
      };
    });

    return {
      transfer_tool: tiaValues.transfer_tool,
      data_exporter_profile: [
        tiaValues.data_exporter_name,
        `传输目的：${tiaValues.transfer_purpose}`,
        tiaValues.data_categories ? `数据类别：${tiaValues.data_categories}` : "",
        tiaValues.data_subject_categories ? `数据主体：${tiaValues.data_subject_categories}` : "",
        `频率：${tiaValues.transfer_frequency}`
      ].filter((item) => item.trim().length > 0).join("；"),
      data_importer_profile: [
        tiaValues.data_importer_name,
        `国家/地区：${tiaValues.importer_country_region}`,
        tiaValues.sensitive_data_description ? `敏感数据：${tiaValues.sensitive_data_description}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      third_country_assessment: [
        tiaValues.law_assessed ? "已完成法律评估" : "法律评估待完成",
        tiaValues.law_findings,
        tiaValues.pre_effectiveness ? `补充措施前判断：${tiaValues.pre_effectiveness}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      supplementary_measures: [
        `技术措施：${tiaValues.supplementary_technical}`,
        tiaValues.supplementary_contractual ? `合同措施：${tiaValues.supplementary_contractual}` : "",
        tiaValues.supplementary_organizational ? `组织措施：${tiaValues.supplementary_organizational}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      final_conclusion: [
        tiaValues.post_effectiveness,
        `关键行动：${tiaValues.key_actions}`,
        tiaValues.dpo_opinion ? `DPO意见：${tiaValues.dpo_opinion}` : "",
        tiaValues.review_date ? `复审日期：${tiaValues.review_date}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      attachments
    };
  };

  const buildCnFlowPayload = async (): Promise<unknown> => {
    assertInput(hasText(cnFlowValues.company_name), "请填写企业名称。");
    assertInput(hasText(cnFlowValues.transfer_purpose), "请填写出境目的。");
    assertInput(splitCsv(cnFlowValues.data_categories).length > 0, "请至少填写一类拟出境数据。");
    assertInput(hasText(cnFlowValues.transfer_chain), "请填写传输链路说明。");
    assertInput(hasText(cnFlowValues.primary_recipient_name), "请填写主要接收方名称。");
    assertInput(hasText(cnFlowValues.primary_recipient_country), "请填写主要接收方国家/地区。");
    assertInput(cnFlowDataInventoryFiles.length > 0, "请上传数据清单附件（data_inventory）。");
    assertInput(cnFlowEntityInventoryFiles.length > 0, "请上传实体清单附件（entity_inventory）。");

    const [dataInventoryPaths, entityInventoryPaths, supportingPaths] = await Promise.all([
      uploadFiles(cnFlowDataInventoryFiles),
      uploadFiles(cnFlowEntityInventoryFiles),
      uploadFiles(cnFlowSupportingFiles)
    ]);

    const attachments = [
      ...dataInventoryPaths.map((path) => {
        const format = inferCnFlowAttachmentFormat(path);
        assertInput(!!format, `数据清单附件格式仅支持 .xlsx/.csv/.docx/.pdf：${basenameFromPath(path)}`);
        return {
          file_role: "data_inventory" as const,
          file_name: basenameFromPath(path),
          file_format: format,
          storage_uri: path
        };
      }),
      ...entityInventoryPaths.map((path) => {
        const format = inferCnFlowAttachmentFormat(path);
        assertInput(!!format, `实体清单附件格式仅支持 .xlsx/.csv/.docx/.pdf：${basenameFromPath(path)}`);
        return {
          file_role: "entity_inventory" as const,
          file_name: basenameFromPath(path),
          file_format: format,
          storage_uri: path
        };
      }),
      ...supportingPaths.map((path) => {
        const format = inferCnFlowAttachmentFormat(path);
        assertInput(!!format, `补充材料格式仅支持 .xlsx/.csv/.docx/.pdf：${basenameFromPath(path)}`);
        return {
          file_role: "supporting_material" as const,
          file_name: basenameFromPath(path),
          file_format: format,
          storage_uri: path
        };
      })
    ];

    const recipient_entities = [
      {
        entity_name: cnFlowValues.primary_recipient_name.trim(),
        country_region: cnFlowValues.primary_recipient_country.trim(),
        entity_role: cnFlowValues.primary_recipient_role,
        is_restricted_party: cnFlowValues.primary_recipient_restricted
      },
      ...parseRecipientRows(cnFlowValues.additional_recipients)
    ];

    return {
      company_name: cnFlowValues.company_name.trim(),
      transfer_purpose: [
        cnFlowValues.transfer_purpose.trim(),
        cnFlowValues.necessity_justification ? `必要性：${cnFlowValues.necessity_justification}` : "",
        cnFlowValues.data_volume_note ? `规模说明：${cnFlowValues.data_volume_note}` : "",
        cnFlowValues.internal_access_note ? `内部访问风险：${cnFlowValues.internal_access_note}` : ""
      ].filter((item) => item.length > 0).join("；"),
      data_categories: splitCsv(cnFlowValues.data_categories),
      sensitive_data_flags: splitCsv(cnFlowValues.sensitive_data_flags),
      recipient_entities,
      transfer_chain: cnFlowValues.transfer_chain.trim(),
      attachments
    };
  };

  const buildCpraPayload = async (): Promise<unknown> => {
    assertInput(hasText(cpraValues.company_name), "请填写企业名称。");
    assertInput(hasText(cpraValues.business_model), "请填写业务模型。");
    assertInput(hasText(cpraValues.data_lifecycle), "请填写数据生命周期说明。");
    assertInput(hasText(cpraValues.notice_and_consent), "请填写告知与同意机制。");
    assertInput(hasText(cpraValues.consumer_rights_process), "请填写消费者权利响应机制。");
    assertInput(hasText(cpraValues.opt_out_and_sale_sharing), "请填写出售/共享与Opt-out机制。");
    assertInput(
      hasText(cpraValues.privacy_policy_url) || cpraPrivacyPolicyFiles.length > 0,
      "请提供隐私政策URL或上传隐私政策文件。"
    );

    const [
      privacyPaths,
      rightsPaths,
      dataMapPaths,
      vendorPaths,
      otherPaths
    ] = await Promise.all([
      uploadFiles(cpraPrivacyPolicyFiles),
      uploadFiles(cpraRightsSopFiles),
      uploadFiles(cpraDataMapFiles),
      uploadFiles(cpraVendorListFiles),
      uploadFiles(cpraOtherFiles)
    ]);

    const uploadedAttachments = [
      ...privacyPaths.map((path) => {
        const format = inferCpraAttachmentFormat(path);
        assertInput(!!format, `隐私政策附件格式仅支持 .docx/.pdf/.xlsx/.csv：${basenameFromPath(path)}`);
        return {
          file_role: "privacy_policy" as const,
          file_name: basenameFromPath(path),
          file_format: format,
          storage_uri: path
        };
      }),
      ...rightsPaths.map((path) => {
        const format = inferCpraAttachmentFormat(path);
        assertInput(!!format, `权利流程附件格式仅支持 .docx/.pdf/.xlsx/.csv：${basenameFromPath(path)}`);
        return {
          file_role: "rights_sop" as const,
          file_name: basenameFromPath(path),
          file_format: format,
          storage_uri: path
        };
      }),
      ...dataMapPaths.map((path) => {
        const format = inferCpraAttachmentFormat(path);
        assertInput(!!format, `数据映射附件格式仅支持 .docx/.pdf/.xlsx/.csv：${basenameFromPath(path)}`);
        return {
          file_role: "data_map" as const,
          file_name: basenameFromPath(path),
          file_format: format,
          storage_uri: path
        };
      }),
      ...vendorPaths.map((path) => {
        const format = inferCpraAttachmentFormat(path);
        assertInput(!!format, `供应商附件格式仅支持 .docx/.pdf/.xlsx/.csv：${basenameFromPath(path)}`);
        return {
          file_role: "vendor_list" as const,
          file_name: basenameFromPath(path),
          file_format: format,
          storage_uri: path
        };
      }),
      ...otherPaths.map((path) => {
        const format = inferCpraAttachmentFormat(path);
        assertInput(!!format, `补充附件格式仅支持 .docx/.pdf/.xlsx/.csv：${basenameFromPath(path)}`);
        return {
          file_role: "other" as const,
          file_name: basenameFromPath(path),
          file_format: format,
          storage_uri: path
        };
      })
    ];

    const urlAttachment = hasText(cpraValues.privacy_policy_url)
      ? (() => {
        assertInput(isValidUrl(cpraValues.privacy_policy_url), "隐私政策URL格式不正确，请使用 http(s) 链接。");
        return [
          {
            file_role: "privacy_policy" as const,
            file_name: "privacy_policy_url",
            file_format: "url" as const,
            storage_uri: cpraValues.privacy_policy_url.trim()
          }
        ];
      })()
      : [];

    const attachments = [...urlAttachment, ...uploadedAttachments];
    assertInput(attachments.length > 0, "请至少提供1份CPRA附件或隐私政策URL。");

    return {
      company_name: cpraValues.company_name.trim(),
      business_model: [
        cpraValues.business_model.trim(),
        cpraValues.dba_name ? `DBA：${cpraValues.dba_name}` : "",
        cpraValues.cpra_applicability_selfcheck ? `适用性：${cpraValues.cpra_applicability_selfcheck}` : "",
        cpraValues.review_focus ? `重点：${cpraValues.review_focus}` : ""
      ].filter((item) => item.length > 0).join("；"),
      data_lifecycle: [
        cpraValues.data_lifecycle,
        cpraValues.data_categories ? `数据类别：${cpraValues.data_categories}` : "",
        cpraValues.spi_usage_summary ? `SPI使用：${cpraValues.spi_usage_summary}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      notice_and_consent: [
        cpraValues.notice_and_consent,
        hasText(cpraValues.privacy_policy_url) ? `隐私政策：${cpraValues.privacy_policy_url.trim()}` : "",
        cpraValues.ui_dark_pattern_check ? `UI暗模式：${cpraValues.ui_dark_pattern_check}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      consumer_rights_process: [
        cpraValues.consumer_rights_process,
        cpraValues.identity_verification_method ? `身份验证：${cpraValues.identity_verification_method}` : "",
        cpraValues.rights_sla ? `SLA：${cpraValues.rights_sla}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      opt_out_and_sale_sharing: cpraValues.opt_out_and_sale_sharing.trim(),
      vendor_management: [
        cpraValues.vendor_management,
        cpraValues.spi_usage_summary ? `SPI限制：${cpraValues.spi_usage_summary}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      attachments
    };
  };

  const buildDiagnosisPayload = (): unknown => ({
    company_name: diagnosisValues.company_name,
    answers: {
      q1_is_ciio: diagnosisValues.q1_is_ciio,
      q2_has_important_data: diagnosisValues.q2_has_important_data,
      q3_pii_count: diagnosisValues.q3_pii_count,
      q4_spi_count: diagnosisValues.q4_spi_count,
      q5_no_personal_info: diagnosisValues.q5_no_personal_info,
      q6_scenario: diagnosisValues.q6_scenario,
      q7_receiver_type: diagnosisValues.q7_receiver_type,
      q8_purpose: diagnosisValues.q8_purpose
    }
  });

  const execute = async () => {
    let requestPayload: unknown;
    try {
      if (isDocumentReviewTask) {
        requestPayload = await buildDocumentReviewPayload();
      } else if (isEuSccTask) {
        requestPayload = await buildEuSccPayload();
      } else if (isDiagnosisModule) {
        requestPayload = buildDiagnosisPayload();
      } else if (isAssessmentModule) {
        requestPayload = await buildAssessmentPayload();
      } else if (isPipiaModule) {
        requestPayload = await buildPipiaPayload();
      } else if (isBcrModule) {
        requestPayload = await buildBcrPayload();
      } else if (isDpiaModule) {
        requestPayload = await buildDpiaPayload();
      } else if (isTiaModule) {
        requestPayload = await buildTiaPayload();
      } else if (isCnFlowModule) {
        requestPayload = await buildCnFlowPayload();
      } else if (isCpraModule) {
        requestPayload = await buildCpraPayload();
      } else {
        requestPayload = JSON.parse(payloadText);
      }
    } catch (parseErr) {
      const message = parseErr instanceof Error ? parseErr.message : "Payload parse error";
      setError(message);
      onRunDone({
        module: moduleKey,
        runMode,
        request: isDocumentReviewTask
          ? documentReviewValues
          : isEuSccTask
          ? euSccValues
          : isDiagnosisModule
          ? diagnosisValues
          : isAssessmentModule
            ? assessmentValues
            : isPipiaModule
              ? pipiaValues
              : isBcrModule
                ? bcrValues
                : isDpiaModule
                  ? dpiaValues
                  : isTiaModule
                    ? tiaValues
                    : isCnFlowModule
                      ? cnFlowValues
                      : isCpraModule
                        ? cpraValues
              : payloadText,
        success: false,
        error: message
      });
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await runModule(definition, requestPayload, allowAsync ? runMode : "sync");
      setResponseData(result.response);
      onRunDone({
        module: moduleKey,
        runMode: result.runMode,
        request: requestPayload,
        response: result.response,
        success: true,
        asyncTaskId: result.asyncTaskId,
        asyncState: result.asyncState
      });
    } catch (runErr) {
      const message = runErr instanceof Error ? runErr.message : "Request failed";
      setResponseData(undefined);
      setError(message);
      onRunDone({ module: moduleKey, runMode, request: requestPayload, success: false, error: message });
    } finally {
      setLoading(false);
    }
  };

  const currentAssessmentStep = ASSESSMENT_STEPS[assessmentStepIndex];
  const assessmentProgress = Math.round(((assessmentStepIndex + 1) / ASSESSMENT_STEPS.length) * 100);
  const currentDiagnosisStep = DIAGNOSIS_STEPS[diagnosisStepIndex];
  const diagnosisProgress = Math.round(((diagnosisStepIndex + 1) / DIAGNOSIS_STEPS.length) * 100);
  const currentPipiaStep = PIPIA_STEPS[pipiaStepIndex];
  const pipiaProgress = Math.round(((pipiaStepIndex + 1) / PIPIA_STEPS.length) * 100);
  const currentDocumentReviewStep = DOCUMENT_REVIEW_STEPS[documentReviewStepIndex];
  const documentReviewProgress = Math.round(((documentReviewStepIndex + 1) / DOCUMENT_REVIEW_STEPS.length) * 100);
  const currentEuSccStep = EU_SCC_STEPS[euSccStepIndex];
  const euSccProgress = Math.round(((euSccStepIndex + 1) / EU_SCC_STEPS.length) * 100);
  const currentBcrStep = BCR_STEPS[bcrStepIndex];
  const bcrProgress = Math.round(((bcrStepIndex + 1) / BCR_STEPS.length) * 100);
  const currentDpiaStep = DPIA_STEPS[dpiaStepIndex];
  const dpiaProgress = Math.round(((dpiaStepIndex + 1) / DPIA_STEPS.length) * 100);
  const currentTiaStep = TIA_STEPS[tiaStepIndex];
  const tiaProgress = Math.round(((tiaStepIndex + 1) / TIA_STEPS.length) * 100);
  const currentCnFlowStep = CN_FLOW_STEPS[cnFlowStepIndex];
  const cnFlowProgress = Math.round(((cnFlowStepIndex + 1) / CN_FLOW_STEPS.length) * 100);
  const currentCpraStep = CPRA_STEPS[cpraStepIndex];
  const cpraProgress = Math.round(((cpraStepIndex + 1) / CPRA_STEPS.length) * 100);
  const panelModuleLabel =
    isDocumentReviewTask && taskTemplate
      ? getTaskTemplateTitle(taskTemplate, lang)
      : definition.label;

  return (
    <section className="run-panel" data-guide="stage-run">
      <header className="run-panel-head">
        <div>
          <div className="runner-title">{t("runPanel")}</div>
          <h3 className="font-display text-xl text-ink">{panelModuleLabel}</h3>
          {taskTemplate ? (
            <p className="run-panel-template-hint">
              {getTaskTemplateTitle(taskTemplate, lang)}
            </p>
          ) : null}
        </div>
        <div className="run-mode-group">
          <button
            className={`pill-btn ${runMode === "sync" ? "active-mode" : ""}`}
            onClick={() => setRunMode("sync")}
          >
            {t("runSync")}
          </button>
          <button
            className={`pill-btn ${runMode === "async" ? "active-mode" : ""}`}
            onClick={() => setRunMode("async")}
            disabled={!allowAsync}
          >
            {t("runAsync")}
          </button>
        </div>
      </header>

      {!lockedModule ? (
        <div className="jurisdiction-tabs">
          {JURISDICTIONS.map((item) => (
            <button
              key={item}
              className={`tab-btn ${item === jurisdiction ? "active" : ""}`}
              onClick={() => setJurisdiction(item)}
            >
              {item}
            </button>
          ))}
        </div>
      ) : null}

      {!lockedModule ? (
        <div className="module-tabs">
          {modules.map((item) => (
            <button
              key={item.key}
              className={`tab-btn ${item.key === moduleKey ? "active" : ""}`}
              onClick={() => setModuleKey(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : (
        <div className="module-lock-line">
          {t("runLockedModule")}
          {" "}
          <strong>{panelModuleLabel}</strong>
        </div>
      )}

      {isDocumentReviewTask ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">Document Review Wizard</div>
            <span>{documentReviewProgress}%</span>
          </div>
          <div className="schema-stepper">
            {DOCUMENT_REVIEW_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === documentReviewStepIndex ? "active" : ""}`}
                onClick={() => setDocumentReviewStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentDocumentReviewStep.title}</div>
          <div className="schema-field-grid">
            {currentDocumentReviewStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      value={String(documentReviewValues[field.name])}
                      onChange={(event) => updateDocumentReviewValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{field.label}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(documentReviewValues[field.name])}
                      onChange={(event) => updateDocumentReviewValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "number") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      type="number"
                      min={field.min}
                      step={field.step}
                      value={Number(documentReviewValues[field.name])}
                      onChange={(event) => {
                        const parsed = Number(event.target.value);
                        updateDocumentReviewValue(field.name, (Number.isFinite(parsed) ? parsed : 0) as never);
                      }}
                    />
                  </label>
                );
              }

              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <select
                      value={String(documentReviewValues[field.name])}
                      onChange={(event) => updateDocumentReviewValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </label>
                );
              }

              return (
                <label key={String(field.name)} className="schema-checkbox-field">
                  <input
                    type="checkbox"
                    checked={Boolean(documentReviewValues[field.name])}
                    onChange={(event) => updateDocumentReviewValue(field.name, event.target.checked as never)}
                  />
                  <span>{field.label}</span>
                </label>
              );
            })}
          </div>

          {documentReviewStepIndex === DOCUMENT_REVIEW_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">上传待审文本</div>
              <input
                type="file"
                multiple
                onChange={(event) => setDocumentReviewFiles(Array.from(event.target.files ?? []))}
              />
              <div className="schema-upload-list">
                {documentReviewFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {documentReviewFiles.length === 0 ? <p className="resource-empty">请上传至少1份合同或政策文本后再执行。</p> : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setDocumentReviewStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={documentReviewStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setDocumentReviewStepIndex((prev) => Math.min(DOCUMENT_REVIEW_STEPS.length - 1, prev + 1))}
              disabled={documentReviewStepIndex === DOCUMENT_REVIEW_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成文档合规审查报告"}
            </button>
          </div>
        </section>
      ) : isEuSccTask ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">SCC Review Wizard</div>
            <span>{euSccProgress}%</span>
          </div>
          <div className="schema-stepper">
            {EU_SCC_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === euSccStepIndex ? "active" : ""}`}
                onClick={() => setEuSccStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentEuSccStep.title}</div>
          <div className="schema-field-grid">
            {currentEuSccStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      value={String(euSccValues[field.name])}
                      onChange={(event) => updateEuSccValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{field.label}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(euSccValues[field.name])}
                      onChange={(event) => updateEuSccValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "number") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      type="number"
                      min={field.min}
                      step={field.step}
                      value={Number(euSccValues[field.name])}
                      onChange={(event) => {
                        const parsed = Number(event.target.value);
                        updateEuSccValue(field.name, (Number.isFinite(parsed) ? parsed : 0) as never);
                      }}
                    />
                  </label>
                );
              }
              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <select
                      value={String(euSccValues[field.name])}
                      onChange={(event) => updateEuSccValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </label>
                );
              }
              return (
                <label key={String(field.name)} className="schema-checkbox-field">
                  <input
                    type="checkbox"
                    checked={Boolean(euSccValues[field.name])}
                    onChange={(event) => updateEuSccValue(field.name, event.target.checked as never)}
                  />
                  <span>{field.label}</span>
                </label>
              );
            })}
          </div>

          {euSccStepIndex === EU_SCC_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">SCC文本与配套材料上传</div>
              <input type="file" multiple onChange={(event) => setEuSccFiles(Array.from(event.target.files ?? []))} />
              <div className="schema-upload-list">
                {euSccFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {euSccFiles.length === 0 ? <p className="resource-empty">请上传至少1份SCC文本或附件后再提交。</p> : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setEuSccStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={euSccStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setEuSccStepIndex((prev) => Math.min(EU_SCC_STEPS.length - 1, prev + 1))}
              disabled={euSccStepIndex === EU_SCC_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成SCC合规审查报告"}
            </button>
          </div>
        </section>
      ) : isDiagnosisModule ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">Diagnosis Wizard</div>
            <span>{diagnosisProgress}%</span>
          </div>
          <div className="schema-stepper">
            {DIAGNOSIS_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === diagnosisStepIndex ? "active" : ""}`}
                onClick={() => setDiagnosisStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentDiagnosisStep.title}</div>
          <div className="schema-field-grid">
            {currentDiagnosisStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      value={String(diagnosisValues[field.name])}
                      onChange={(event) => updateDiagnosisValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{field.label}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(diagnosisValues[field.name])}
                      onChange={(event) => updateDiagnosisValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "number") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      type="number"
                      min={field.min}
                      step={field.step}
                      value={Number(diagnosisValues[field.name])}
                      onChange={(event) => {
                        const parsed = Number(event.target.value);
                        updateDiagnosisValue(field.name, (Number.isFinite(parsed) ? parsed : 0) as never);
                      }}
                    />
                  </label>
                );
              }

              return (
                <label key={String(field.name)} className="field-wrap">
                  <span>{field.label}</span>
                  <select
                    value={String(diagnosisValues[field.name])}
                    onChange={(event) => updateDiagnosisValue(field.name, event.target.value as never)}
                  >
                    {(field.options ?? []).map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
              );
            })}
          </div>

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setDiagnosisStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={diagnosisStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setDiagnosisStepIndex((prev) => Math.min(DIAGNOSIS_STEPS.length - 1, prev + 1))}
              disabled={diagnosisStepIndex === DIAGNOSIS_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : `${t("runNow")} ${definition.label}`}
            </button>
          </div>
        </section>
      ) : isAssessmentModule ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">Assessment Wizard</div>
            <span>{assessmentProgress}%</span>
          </div>
          <div className="schema-stepper">
            {ASSESSMENT_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === assessmentStepIndex ? "active" : ""}`}
                onClick={() => setAssessmentStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentAssessmentStep.title}</div>
          <div className="schema-field-grid">
            {currentAssessmentStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      value={String(assessmentValues[field.name])}
                      onChange={(event) => updateAssessmentValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{field.label}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(assessmentValues[field.name])}
                      onChange={(event) => updateAssessmentValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "number") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      type="number"
                      min={field.min}
                      step={field.step}
                      value={Number(assessmentValues[field.name])}
                      onChange={(event) => {
                        const parsed = Number(event.target.value);
                        updateAssessmentValue(field.name, (Number.isFinite(parsed) ? parsed : 0) as never);
                      }}
                    />
                  </label>
                );
              }

              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <select
                      value={String(assessmentValues[field.name])}
                      onChange={(event) => updateAssessmentValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </label>
                );
              }

              return (
                <label key={String(field.name)} className="schema-checkbox-field">
                  <input
                    type="checkbox"
                    checked={Boolean(assessmentValues[field.name])}
                    onChange={(event) => updateAssessmentValue(field.name, event.target.checked as never)}
                  />
                  <span>{field.label}</span>
                </label>
              );
            })}
          </div>

          {assessmentStepIndex === ASSESSMENT_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">附件上传</div>
              <input
                type="file"
                multiple
                onChange={(event) => setAssessmentFiles(Array.from(event.target.files ?? []))}
              />
              <div className="schema-upload-list">
                {assessmentFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {assessmentFiles.length === 0 ? <p className="resource-empty">请上传附件材料后再提交。</p> : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setAssessmentStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={assessmentStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setAssessmentStepIndex((prev) => Math.min(ASSESSMENT_STEPS.length - 1, prev + 1))}
              disabled={assessmentStepIndex === ASSESSMENT_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : `${t("runNow")} ${definition.label}`}
            </button>
          </div>
        </section>
      ) : isPipiaModule ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">PIPIA Wizard</div>
            <span>{pipiaProgress}%</span>
          </div>
          <div className="schema-stepper">
            {PIPIA_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === pipiaStepIndex ? "active" : ""}`}
                onClick={() => setPipiaStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentPipiaStep.title}</div>
          <div className="schema-field-grid">
            {currentPipiaStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      value={String(pipiaValues[field.name])}
                      onChange={(event) => updatePipiaValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{field.label}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(pipiaValues[field.name])}
                      onChange={(event) => updatePipiaValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }

              if (field.type === "number") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      type="number"
                      min={field.min}
                      step={field.step}
                      value={Number(pipiaValues[field.name])}
                      onChange={(event) => {
                        const parsed = Number(event.target.value);
                        updatePipiaValue(field.name, (Number.isFinite(parsed) ? parsed : 0) as never);
                      }}
                    />
                  </label>
                );
              }

              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <select
                      value={String(pipiaValues[field.name])}
                      onChange={(event) => updatePipiaValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </label>
                );
              }

              return (
                <label key={String(field.name)} className="schema-checkbox-field">
                  <input
                    type="checkbox"
                    checked={Boolean(pipiaValues[field.name])}
                    onChange={(event) => updatePipiaValue(field.name, event.target.checked as never)}
                  />
                  <span>{field.label}</span>
                </label>
              );
            })}
          </div>

          {pipiaStepIndex === PIPIA_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">附件上传</div>
              <input
                type="file"
                multiple
                onChange={(event) => setPipiaFiles(Array.from(event.target.files ?? []))}
              />
              <div className="schema-upload-list">
                {pipiaFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {pipiaFiles.length === 0 ? <p className="resource-empty">请上传至少1份PIPIA附件后再提交。</p> : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setPipiaStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={pipiaStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setPipiaStepIndex((prev) => Math.min(PIPIA_STEPS.length - 1, prev + 1))}
              disabled={pipiaStepIndex === PIPIA_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : `${t("runNow")} ${definition.label}`}
            </button>
          </div>
        </section>
      ) : isBcrModule ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">BCR Review Wizard</div>
            <span>{bcrProgress}%</span>
          </div>
          <div className="schema-stepper">
            {BCR_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === bcrStepIndex ? "active" : ""}`}
                onClick={() => setBcrStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentBcrStep.title}</div>
          <div className="schema-field-grid">
            {currentBcrStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      value={String(bcrValues[field.name])}
                      onChange={(event) => updateBcrValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <select
                      value={String(bcrValues[field.name])}
                      onChange={(event) => updateBcrValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </label>
                );
              }
              return (
                <label key={String(field.name)} className="field-wrap schema-field-wide">
                  <span>{field.label}</span>
                  <textarea
                    className="runner-textarea schema-textarea"
                    value={String(bcrValues[field.name])}
                    onChange={(event) => updateBcrValue(field.name, event.target.value as never)}
                  />
                </label>
              );
            })}
          </div>

          {bcrStepIndex === BCR_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">BCR主文本与配套材料上传（仅docx/pdf）</div>
              <input type="file" multiple onChange={(event) => setBcrFiles(Array.from(event.target.files ?? []))} />
              <div className="schema-upload-list">
                {bcrFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {bcrFiles.length === 0 ? <p className="resource-empty">请上传至少1份BCR材料后再提交。</p> : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setBcrStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={bcrStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setBcrStepIndex((prev) => Math.min(BCR_STEPS.length - 1, prev + 1))}
              disabled={bcrStepIndex === BCR_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成BCR审查报告"}
            </button>
          </div>
        </section>
      ) : isDpiaModule ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">DPIA Wizard</div>
            <span>{dpiaProgress}%</span>
          </div>
          <div className="schema-stepper">
            {DPIA_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === dpiaStepIndex ? "active" : ""}`}
                onClick={() => setDpiaStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentDpiaStep.title}</div>
          <div className="schema-field-grid">
            {currentDpiaStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      value={String(dpiaValues[field.name])}
                      onChange={(event) => updateDpiaValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{field.label}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(dpiaValues[field.name])}
                      onChange={(event) => updateDpiaValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <select
                      value={String(dpiaValues[field.name])}
                      onChange={(event) => updateDpiaValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </label>
                );
              }
              return (
                <label key={String(field.name)} className="schema-checkbox-field">
                  <input
                    type="checkbox"
                    checked={Boolean(dpiaValues[field.name])}
                    onChange={(event) => updateDpiaValue(field.name, event.target.checked as never)}
                  />
                  <span>{field.label}</span>
                </label>
              );
            })}
          </div>

          {dpiaStepIndex === DPIA_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">DPIA附件上传（docx/pdf/png/jpg）</div>
              <input type="file" multiple onChange={(event) => setDpiaFiles(Array.from(event.target.files ?? []))} />
              <div className="schema-upload-list">
                {dpiaFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {dpiaFiles.length === 0 ? <p className="resource-empty">请上传至少1份DPIA附件后再提交。</p> : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setDpiaStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={dpiaStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setDpiaStepIndex((prev) => Math.min(DPIA_STEPS.length - 1, prev + 1))}
              disabled={dpiaStepIndex === DPIA_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成DPIA草案"}
            </button>
          </div>
        </section>
      ) : isTiaModule ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">TIA Wizard</div>
            <span>{tiaProgress}%</span>
          </div>
          <div className="schema-stepper">
            {TIA_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === tiaStepIndex ? "active" : ""}`}
                onClick={() => setTiaStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentTiaStep.title}</div>
          <div className="schema-field-grid">
            {currentTiaStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <input
                      value={String(tiaValues[field.name])}
                      onChange={(event) => updateTiaValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{field.label}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={String(tiaValues[field.name])}
                      onChange={(event) => updateTiaValue(field.name, event.target.value as never)}
                    />
                  </label>
                );
              }
              if (field.type === "select") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{field.label}</span>
                    <select
                      value={String(tiaValues[field.name])}
                      onChange={(event) => updateTiaValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </label>
                );
              }
              return (
                <label key={String(field.name)} className="schema-checkbox-field">
                  <input
                    type="checkbox"
                    checked={Boolean(tiaValues[field.name])}
                    onChange={(event) => updateTiaValue(field.name, event.target.checked as never)}
                  />
                  <span>{field.label}</span>
                </label>
              );
            })}
          </div>

          {tiaStepIndex === TIA_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">TIA附件上传（docx/pdf）</div>
              <input type="file" multiple onChange={(event) => setTiaFiles(Array.from(event.target.files ?? []))} />
              <div className="schema-upload-list">
                {tiaFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {tiaFiles.length === 0 ? <p className="resource-empty">请上传至少1份TIA附件后再提交。</p> : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setTiaStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={tiaStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setTiaStepIndex((prev) => Math.min(TIA_STEPS.length - 1, prev + 1))}
              disabled={tiaStepIndex === TIA_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成TIA草案"}
            </button>
          </div>
        </section>
      ) : isCnFlowModule ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">EO 14117 Wizard</div>
            <span>{cnFlowProgress}%</span>
          </div>
          <div className="schema-stepper">
            {CN_FLOW_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === cnFlowStepIndex ? "active" : ""}`}
                onClick={() => setCnFlowStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentCnFlowStep.title}</div>
          {currentCnFlowStep.fields.length > 0 ? (
            <div className="schema-field-grid">
              {currentCnFlowStep.fields.map((field) => {
                if (field.type === "text") {
                  return (
                    <label key={String(field.name)} className="field-wrap">
                      <span>{field.label}</span>
                      <input
                        value={String(cnFlowValues[field.name])}
                        onChange={(event) => updateCnFlowValue(field.name, event.target.value as never)}
                      />
                    </label>
                  );
                }
                if (field.type === "textarea") {
                  return (
                    <label key={String(field.name)} className="field-wrap schema-field-wide">
                      <span>{field.label}</span>
                      <textarea
                        className="runner-textarea schema-textarea"
                        value={String(cnFlowValues[field.name])}
                        onChange={(event) => updateCnFlowValue(field.name, event.target.value as never)}
                      />
                    </label>
                  );
                }
                if (field.type === "select") {
                  return (
                    <label key={String(field.name)} className="field-wrap">
                      <span>{field.label}</span>
                      <select
                        value={String(cnFlowValues[field.name])}
                        onChange={(event) => updateCnFlowValue(field.name, event.target.value as never)}
                      >
                        {(field.options ?? []).map((option) => (
                          <option key={option} value={option}>{option}</option>
                        ))}
                      </select>
                    </label>
                  );
                }
                return (
                  <label key={String(field.name)} className="schema-checkbox-field">
                    <input
                      type="checkbox"
                      checked={Boolean(cnFlowValues[field.name])}
                      onChange={(event) => updateCnFlowValue(field.name, event.target.checked as never)}
                    />
                    <span>{field.label}</span>
                  </label>
                );
              })}
            </div>
          ) : null}

          {cnFlowStepIndex === CN_FLOW_STEPS.length - 1 ? (
            <>
              <section className="schema-upload-card">
                <div className="runner-title">数据清单附件（必传，data_inventory）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCnFlowDataInventoryFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cnFlowDataInventoryFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cnFlowDataInventoryFiles.length === 0 ? (
                    <p className="resource-empty">请上传至少1份数据清单（xlsx/csv/docx/pdf）。</p>
                  ) : null}
                </div>
              </section>

              <section className="schema-upload-card">
                <div className="runner-title">实体清单附件（必传，entity_inventory）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCnFlowEntityInventoryFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cnFlowEntityInventoryFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cnFlowEntityInventoryFiles.length === 0 ? (
                    <p className="resource-empty">请上传至少1份实体清单（xlsx/csv/docx/pdf）。</p>
                  ) : null}
                </div>
              </section>

              <section className="schema-upload-card">
                <div className="runner-title">补充材料（可选，supporting_material）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCnFlowSupportingFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cnFlowSupportingFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cnFlowSupportingFiles.length === 0 ? (
                    <p className="resource-empty">可上传股权结构、组织架构、合同台账等辅助材料。</p>
                  ) : null}
                </div>
              </section>
            </>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setCnFlowStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={cnFlowStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setCnFlowStepIndex((prev) => Math.min(CN_FLOW_STEPS.length - 1, prev + 1))}
              disabled={cnFlowStepIndex === CN_FLOW_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成14117风险评估结论报告"}
            </button>
          </div>
        </section>
      ) : isCpraModule ? (
        <section className="schema-wizard">
          <div className="schema-wizard-head">
            <div className="runner-title">CPRA Wizard</div>
            <span>{cpraProgress}%</span>
          </div>
          <div className="schema-stepper">
            {CPRA_STEPS.map((step, index) => (
              <button
                key={step.title}
                className={`schema-step-dot ${index === cpraStepIndex ? "active" : ""}`}
                onClick={() => setCpraStepIndex(index)}
                type="button"
              >
                {index + 1}. {step.title}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{currentCpraStep.title}</div>
          {currentCpraStep.fields.length > 0 ? (
            <div className="schema-field-grid">
              {currentCpraStep.fields.map((field) => {
                if (field.type === "text") {
                  return (
                    <label key={String(field.name)} className="field-wrap">
                      <span>{field.label}</span>
                      <input
                        value={String(cpraValues[field.name])}
                        onChange={(event) => updateCpraValue(field.name, event.target.value as never)}
                      />
                    </label>
                  );
                }
                if (field.type === "textarea") {
                  return (
                    <label key={String(field.name)} className="field-wrap schema-field-wide">
                      <span>{field.label}</span>
                      <textarea
                        className="runner-textarea schema-textarea"
                        value={String(cpraValues[field.name])}
                        onChange={(event) => updateCpraValue(field.name, event.target.value as never)}
                      />
                    </label>
                  );
                }
                return (
                  <label key={String(field.name)} className="schema-checkbox-field">
                    <input
                      type="checkbox"
                      checked={Boolean(cpraValues[field.name])}
                      onChange={(event) => updateCpraValue(field.name, event.target.checked as never)}
                    />
                    <span>{field.label}</span>
                  </label>
                );
              })}
            </div>
          ) : null}

          {cpraStepIndex === CPRA_STEPS.length - 1 ? (
            <>
              <section className="schema-upload-card">
                <div className="runner-title">隐私政策（privacy_policy）</div>
                <p className="resource-empty">可填写URL，也可上传文档。两者满足其一即可。</p>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCpraPrivacyPolicyFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cpraPrivacyPolicyFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cpraPrivacyPolicyFiles.length === 0 ? (
                    <p className="resource-empty">若未提供URL，请至少上传1份隐私政策文件。</p>
                  ) : null}
                </div>
              </section>

              <section className="schema-upload-card">
                <div className="runner-title">消费者权利SOP（rights_sop，可选）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCpraRightsSopFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cpraRightsSopFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cpraRightsSopFiles.length === 0 ? <p className="resource-empty">可选上传。</p> : null}
                </div>
              </section>

              <section className="schema-upload-card">
                <div className="runner-title">数据映射材料（data_map，可选）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCpraDataMapFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cpraDataMapFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cpraDataMapFiles.length === 0 ? <p className="resource-empty">可选上传。</p> : null}
                </div>
              </section>

              <section className="schema-upload-card">
                <div className="runner-title">供应商清单（vendor_list，可选）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCpraVendorListFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cpraVendorListFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cpraVendorListFiles.length === 0 ? <p className="resource-empty">可选上传。</p> : null}
                </div>
              </section>

              <section className="schema-upload-card">
                <div className="runner-title">其他补充材料（other，可选）</div>
                <input
                  type="file"
                  multiple
                  onChange={(event) => setCpraOtherFiles(Array.from(event.target.files ?? []))}
                />
                <div className="schema-upload-list">
                  {cpraOtherFiles.map((file) => (
                    <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                      <strong>{file.name}</strong>
                      <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                    </article>
                  ))}
                  {cpraOtherFiles.length === 0 ? <p className="resource-empty">可选上传。</p> : null}
                </div>
              </section>
            </>
          ) : null}

          <div className="schema-actions-row">
            <button
              className="pill-btn"
              type="button"
              onClick={() => setCpraStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={cpraStepIndex === 0}
            >
              上一步
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setCpraStepIndex((prev) => Math.min(CPRA_STEPS.length - 1, prev + 1))}
              disabled={cpraStepIndex === CPRA_STEPS.length - 1}
            >
              下一步
            </button>
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : "生成CPRA合规全景报告"}
            </button>
          </div>
        </section>
      ) : (
        <>
          <div className="runner-title">{t("payloadLabel")}</div>
          <textarea className="runner-textarea" value={payloadText} onChange={(event) => setPayloadText(event.target.value)} />
          <div className="mt-2 flex justify-end">
            <button className="pill-btn-primary" onClick={execute} disabled={loading}>
              {loading ? t("runningNow") : `${t("runNow")} ${definition.label}`}
            </button>
          </div>
        </>
      )}

      <div className="runner-title mt-3">{t("responseLabel")}</div>
      {responseData ? (
        <section className="runner-user-result">
          <article className="runner-user-headline">
            <strong>{userFacingResult.headline}</strong>
            {userFacingResult.chips.length > 0 ? (
              <div className="runner-user-chip-row">
                {userFacingResult.chips.map((chip) => (
                  <span key={chip} className="runner-user-chip">{chip}</span>
                ))}
              </div>
            ) : null}
          </article>

          {userFacingResult.deliverables.length > 0 ? (
            <article className="runner-user-block">
              <h4>{lang === "zh" ? "已生成文件" : "Generated Files"}</h4>
              <ul>
                {userFacingResult.deliverables.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ) : null}

          {userFacingResult.highlights.length > 0 ? (
            <article className="runner-user-block">
              <h4>{lang === "zh" ? "关键结果" : "Key Findings"}</h4>
              <ul>
                {userFacingResult.highlights.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            </article>
          ) : null}

          <article className="runner-user-block">
            <h4>{lang === "zh" ? "建议下一步" : "Recommended Next Steps"}</h4>
            <ul>
              {userFacingResult.nextSteps.map((item, index) => (
                <li key={`${item}-${index}`}>{item}</li>
              ))}
            </ul>
          </article>
        </section>
      ) : (
        <div className="runner-empty-card">{t("runResultPlaceholder")}</div>
      )}

      <div className="runner-preview-hint">
        {responseData
          ? (lang === "zh" ? "结果已生成，系统会自动切换到“报告”页签进行前端预览。" : "Result generated. The workspace switches to the report tab for preview.")
          : (lang === "zh" ? "运行完成后，报告内容将在“报告”页签中预览。" : "Generated reports will be previewed in the report tab.")}
      </div>
      {error ? <div className="runner-error">{error}</div> : null}
    </section>
  );
}
