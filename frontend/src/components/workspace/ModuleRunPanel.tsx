import { useEffect, useMemo, useRef, useState } from "react";
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
import { DEV_ACCEL_ENABLED, getAssessmentDevPreset, getModuleDevPreset } from "../../lib/dev-presets";

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

type AutoExtractResult = {
  documentTitle: string;
  documentType: DocumentReviewFormValues["document_type"];
  reviewFocus: string;
  transferPurpose: string;
  sensitivePiDisclosed: boolean;
  rightsChannelDisclosed: boolean;
  crossborderRuleDisclosed: boolean;
  contactChannel: string;
  note: string;
};

type DocumentReviewExtractState = {
  status: "loading" | "done" | "error";
  note: string;
};

type AsyncRunProgressState = {
  state: string;
  progress?: number;
};

type DiagnosisOption = {
  value: string;
  label: string;
  extraFieldId?: string;
  extraPlaceholder?: string;
};

type DiagnosisFieldType = "text" | "textarea" | "single" | "multi";

type DiagnosisFieldConfig = {
  name: string;
  label: string;
  type: DiagnosisFieldType;
  group?: string;
  options?: DiagnosisOption[];
  visibleWhen?: (answers: DiagnosisFormValues) => boolean;
};

type DiagnosisStepConfig = {
  title: string;
  fields: DiagnosisFieldConfig[];
};

type DiagnosisFormValues = Record<string, unknown>;

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

const diagnosisIsYes = (answers: DiagnosisFormValues, key: string): boolean => answers[key] === "yes";
const DIAGNOSIS_STEP_SHORT_TITLES = ["业务基础", "合规需求", "数据处理", "数据流转", "系统架构"] as const;

const DIAGNOSIS_STEPS: DiagnosisStepConfig[] = [
  {
    title: "一、业务基础信息",
    fields: [
      { name: "company_name", label: "企业名称（选填）", type: "text", group: "企业基础" },
      {
        name: "m1_industry",
        label: "业务所属行业",
        type: "single",
        group: "行业与服务对象",
        options: [
          { value: "电商零售", label: "电商零售" },
          { value: "社交娱乐", label: "社交娱乐" },
          { value: "工具类应用", label: "工具类应用" },
          { value: "金融科技", label: "金融科技" },
          { value: "教育培训", label: "教育培训" },
          { value: "医疗健康", label: "医疗健康" },
          { value: "智能制造", label: "智能制造" },
          { value: "政务服务", label: "政务服务" },
          { value: "其他", label: "其他（需补充文本）", extraFieldId: "m1_industry_other", extraPlaceholder: "请补充行业" }
        ]
      },
      {
        name: "m1_business_channels",
        label: "业务主要开展方式（多选）",
        type: "multi",
        group: "业务开展方式",
        options: [
          { value: "线上平台（APP / 小程序 / 官网）", label: "线上平台（APP / 小程序 / 官网）" },
          { value: "线下实体（门店 / 上门服务）", label: "线下实体（门店 / 上门服务）" },
          { value: "数据合作（与其他公司共享 / 交换数据）", label: "数据合作（与其他公司共享 / 交换数据）" },
          { value: "跨境服务（面向国外用户 / 业务涉及国外）", label: "跨境服务（面向国外用户 / 业务涉及国外）" },
          { value: "纯内部使用（仅员工用，不对外）", label: "纯内部使用（仅员工用，不对外）" },
          {
            value: "其他",
            label: "其他（需补充文本）",
            extraFieldId: "m1_business_channels_other",
            extraPlaceholder: "请补充开展方式"
          }
        ]
      },
      {
        name: "m1_service_targets",
        label: "服务对象",
        type: "single",
        group: "行业与服务对象",
        options: [
          { value: "个人用户", label: "个人用户" },
          { value: "企业用户", label: "企业用户" },
          { value: "个人用户和企业用户两者都有", label: "个人用户和企业用户两者都有" },
          { value: "政府机构", label: "政府机构" }
        ]
      },
      {
        name: "m1_company_size",
        label: "企业规模",
        type: "single",
        group: "企业规模",
        options: [
          { value: "微型（员工≤10人）", label: "微型（员工≤10人）" },
          { value: "小型（11-50人）", label: "小型（11-50人）" },
          { value: "中型（51-200人）", label: "中型（51-200人）" },
          { value: "大型（201-500人）", label: "大型（201-500人）" },
          { value: "特大型（501-1000人）", label: "特大型（501-1000人）" },
          { value: "超大型（>1000人）", label: "超大型（>1000人）" }
        ]
      }
    ]
  },
  {
    title: "二、合规需求与现状",
    fields: [
      {
        name: "m2_core_needs",
        label: "当前最想解决的合规问题（多选）",
        type: "multi",
        options: [
          { value: "不确定业务是否需要做数据合规", label: "不确定业务是否需要做数据合规" },
          { value: "识别业务合规风险点", label: "识别业务合规风险点" },
          { value: "制定合规文件（隐私政策 / 用户协议等）", label: "制定合规文件（隐私政策 / 用户协议等）" },
          { value: "数据安全技术落地指导", label: "数据安全技术落地指导" },
          { value: "合规审计 / 备案", label: "合规审计 / 备案" },
          { value: "应对合规紧急情况（投诉 / 整改）", label: "应对合规紧急情况（投诉 / 整改）" },
          { value: "其他", label: "其他（需补充文本）", extraFieldId: "m2_core_needs_other", extraPlaceholder: "请补充需求" }
        ]
      },
      {
        name: "m2_had_compliance_issue",
        label: "是否遇到过数据合规相关问题",
        type: "single",
        options: [
          { value: "yes", label: "是（需补充描述）", extraFieldId: "m2_issue_description", extraPlaceholder: "请补充问题描述" },
          { value: "no", label: "否" },
          { value: "unknown", label: "不清楚" }
        ]
      },
      {
        name: "m2_deadline",
        label: "完成合规的时间节点",
        type: "single",
        options: [
          { value: "无紧急需求（3个月以上）", label: "无紧急需求（3个月以上）" },
          { value: "一般需求（1-3个月）", label: "一般需求（1-3个月）" },
          { value: "紧急需求（1个月内）", label: "紧急需求（1个月内）" },
          { value: "已被要求整改", label: "已被要求整改（需填写期限）", extraFieldId: "m2_deadline_detail", extraPlaceholder: "请填写整改期限" }
        ]
      }
    ]
  },
  {
    title: "三、数据处理核心信息",
    fields: [
      {
        name: "m3_processes_personal_info",
        label: "是否会收集、存储或使用个人信息",
        type: "single",
        options: [
          { value: "yes", label: "是" },
          { value: "no", label: "否" }
        ]
      },
      {
        name: "m3_personal_info_types",
        label: "收集的个人信息类型（多选）",
        type: "multi",
        visibleWhen: (answers) => diagnosisIsYes(answers, "m3_processes_personal_info"),
        options: [
          { value: "姓名", label: "姓名" },
          { value: "手机号", label: "手机号" },
          { value: "邮箱", label: "邮箱" },
          { value: "收货地址", label: "收货地址" },
          { value: "设备信息", label: "设备信息" },
          { value: "浏览 / 行为记录", label: "浏览 / 行为记录" },
          { value: "交易信息", label: "交易信息" },
          { value: "身份证号", label: "身份证号" },
          { value: "人脸 / 指纹 / 声纹", label: "人脸 / 指纹 / 声纹" },
          { value: "健康信息", label: "健康信息" },
          { value: "金融账户信息", label: "金融账户信息" },
          { value: "未成年人信息", label: "未成年人信息" },
          { value: "精准位置信息", label: "精准位置信息" }
        ]
      },
      {
        name: "m3_processes_important_data",
        label: "是否处理重要数据",
        type: "single",
        visibleWhen: (answers) => diagnosisIsYes(answers, "m3_processes_personal_info"),
        options: [
          { value: "yes", label: "是" },
          { value: "no", label: "否" }
        ]
      },
      {
        name: "m3_important_data_types",
        label: "重要数据类型（多选）",
        type: "multi",
        visibleWhen: (answers) =>
          diagnosisIsYes(answers, "m3_processes_personal_info") && diagnosisIsYes(answers, "m3_processes_important_data"),
        options: [
          { value: "工业生产数据", label: "工业生产数据" },
          { value: "金融交易数据", label: "金融交易数据" },
          { value: "医疗健康数据", label: "医疗健康数据" },
          { value: "教育数据", label: "教育数据" },
          { value: "交通数据", label: "交通数据" },
          { value: "能源数据", label: "能源数据" },
          { value: "政务数据", label: "政务数据" },
          { value: "其他", label: "其他（需补充文本）", extraFieldId: "m3_important_data_types_other", extraPlaceholder: "请补充重要数据类型" }
        ]
      },
      {
        name: "m3_data_sources",
        label: "数据来源（多选）",
        type: "multi",
        visibleWhen: (answers) => diagnosisIsYes(answers, "m3_processes_personal_info"),
        options: [
          { value: "用户主动提交", label: "用户主动提交" },
          { value: "第三方合作获取", label: "第三方合作获取" },
          { value: "公开渠道采集", label: "公开渠道采集" },
          { value: "设备自动采集", label: "设备自动采集" },
          { value: "其他", label: "其他（需补充文本）", extraFieldId: "m3_data_sources_other", extraPlaceholder: "请补充数据来源" }
        ]
      },
      {
        name: "m3_processing_activities",
        label: "数据处理方式（多选）",
        type: "multi",
        visibleWhen: (answers) => diagnosisIsYes(answers, "m3_processes_personal_info"),
        options: [
          { value: "收集", label: "收集" },
          { value: "存储", label: "存储" },
          { value: "加工", label: "加工" },
          { value: "传输", label: "传输" },
          { value: "提供给他人", label: "提供给他人" },
          { value: "公开", label: "公开" },
          { value: "删除", label: "删除" },
          { value: "跨境传输", label: "跨境传输" }
        ]
      },
      {
        name: "m3_data_volume_range",
        label: "数据处理规模",
        type: "single",
        visibleWhen: (answers) => diagnosisIsYes(answers, "m3_processes_personal_info"),
        options: [
          { value: "10万条以下", label: "10万条以下" },
          { value: "10-100万条", label: "10-100万条" },
          { value: "100-1000万条", label: "100-1000万条" },
          { value: "1000万条以上", label: "1000万条以上" }
        ]
      },
      {
        name: "m3_processes_enterprise_public_data",
        label: "是否处理企业数据或公共数据",
        type: "single",
        options: [
          { value: "yes", label: "是（补充说明）", extraFieldId: "m3_enterprise_public_data_desc", extraPlaceholder: "请补充说明" },
          { value: "no", label: "否" }
        ]
      },
      {
        name: "m3_retention_period",
        label: "数据留存周期",
        type: "single",
        options: [
          { value: "永久留存", label: "永久留存" },
          { value: "业务必要期限内留存", label: "业务必要期限内留存（补充说明）", extraFieldId: "m3_retention_desc", extraPlaceholder: "请补充留存说明" },
          { value: "按法律规定期限留存", label: "按法律规定期限留存" },
          { value: "无明确规则", label: "无明确规则" }
        ]
      }
    ]
  },
  {
    title: "四、数据流转与共享情况",
    fields: [
      {
        name: "m4_share_to_third_party",
        label: "是否共享给第三方",
        type: "single",
        options: [
          { value: "yes", label: "是（补充第三方类型）", extraFieldId: "m4_third_party_types", extraPlaceholder: "请补充第三方类型" },
          { value: "no", label: "否" }
        ]
      },
      {
        name: "m4_cross_border_transfer",
        label: "是否涉及跨境传输",
        type: "single",
        options: [
          { value: "yes", label: "是（补充出境国家/地区）", extraFieldId: "m4_cross_border_regions", extraPlaceholder: "请补充出境国家/地区" },
          { value: "no", label: "否" }
        ]
      },
      {
        name: "m4_commercialization",
        label: "数据是否用于商业化变现",
        type: "single",
        options: [
          { value: "yes", label: "是（补充变现方式）", extraFieldId: "m4_commercialization_mode", extraPlaceholder: "请补充变现方式" },
          { value: "no", label: "否" }
        ]
      },
      {
        name: "m4_entrusted_processing",
        label: "是否委托其他公司处理数据",
        type: "single",
        options: [
          { value: "yes", label: "是（补充委托方类型）", extraFieldId: "m4_entrusted_party_type", extraPlaceholder: "请补充委托方类型" },
          { value: "no", label: "否" }
        ]
      },
      {
        name: "m4_authorization_method",
        label: "用户授权方式",
        type: "single",
        options: [
          { value: "弹窗勾选同意", label: "弹窗勾选同意" },
          { value: "单独点击“同意”按钮", label: "单独点击“同意”按钮" },
          { value: "继续使用即视为同意", label: "继续使用即视为同意" },
          { value: "分级授权", label: "分级授权" },
          { value: "无授权机制", label: "无授权机制" }
        ]
      }
    ]
  },
  {
    title: "五、业务系统与技术架构",
    fields: [
      {
        name: "m5_systems",
        label: "当前业务系统（多选）",
        type: "multi",
        options: [
          { value: "自有 APP", label: "自有 APP" },
          { value: "微信 / 支付宝小程序", label: "微信 / 支付宝小程序" },
          { value: "官方网站", label: "官方网站" },
          { value: "企业微信 / 飞书 / 钉钉等协作工具", label: "企业微信 / 飞书 / 钉钉等协作工具" },
          { value: "定制化业务系统", label: "定制化业务系统" },
          { value: "其他", label: "其他（补充文本）", extraFieldId: "m5_systems_other", extraPlaceholder: "请补充系统类型" }
        ]
      },
      {
        name: "m5_security_measures",
        label: "当前数据安全技术措施（多选）",
        type: "multi",
        options: [
          { value: "数据加密", label: "数据加密" },
          { value: "数据脱敏", label: "数据脱敏" },
          { value: "访问权限控制", label: "访问权限控制" },
          { value: "操作日志审计", label: "操作日志审计" },
          { value: "安全防护设备", label: "安全防护设备" },
          { value: "无", label: "无" },
          { value: "其他", label: "其他（补充文本）", extraFieldId: "m5_security_measures_other", extraPlaceholder: "请补充安全措施" }
        ]
      },
      {
        name: "m5_compliance_docs",
        label: "当前合规相关制度文件（多选）",
        type: "multi",
        options: [
          { value: "隐私政策", label: "隐私政策" },
          { value: "用户协议", label: "用户协议" },
          { value: "数据安全管理制度", label: "数据安全管理制度" },
          { value: "应急响应预案", label: "应急响应预案" },
          { value: "无", label: "无" },
          { value: "其他", label: "其他（补充文本）", extraFieldId: "m5_compliance_docs_other", extraPlaceholder: "请补充制度文件" }
        ]
      },
      {
        name: "m5_penalty_or_complaint",
        label: "是否有过合规相关处罚或投诉记录",
        type: "single",
        options: [
          { value: "曾被监管部门处罚", label: "曾被监管部门处罚", extraFieldId: "m5_penalty_time", extraPlaceholder: "请填写处罚时间" },
          { value: "收到过用户合规投诉", label: "收到过用户合规投诉" },
          { value: "无相关记录", label: "无相关记录" }
        ]
      },
      {
        name: "m5_penalty_reason",
        label: "处罚事由",
        type: "text",
        visibleWhen: (answers) => answers.m5_penalty_or_complaint === "曾被监管部门处罚"
      },
      {
        name: "m5_penalty_result",
        label: "处罚结果",
        type: "text",
        visibleWhen: (answers) => answers.m5_penalty_or_complaint === "曾被监管部门处罚"
      }
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

const UI_LANG_KEY = "ai4law_ui_lang";
const currentUiLang = (): "zh" | "en" => (globalThis.localStorage?.getItem(UI_LANG_KEY) === "zh" ? "zh" : "en");
const replaceAllText = (source: string, from: string, to: string): string => source.split(from).join(to);

const toEnglishValidation = (message: string): string => {
  let text = message;
  const replacements: Array<[string, string]> = [
    ["请填写", "Please provide "],
    ["请至少填写一类", "Please provide at least one "],
    ["请上传至少1份", "Please upload at least one "],
    ["请上传", "Please upload "],
    ["仅支持", "only supports"],
    ["格式不正确，请使用 http(s) 链接。", "format is invalid. Please use an http(s) URL."],
    ["企业名称", "company name"],
    ["统一社会信用代码（至少8位）", "Unified Social Credit Code (at least 8 characters)"],
    ["接收方国家/地区", "recipient country/region"],
    ["出境目的", "cross-border transfer purpose"],
    ["合法性基础", "legal basis"],
    ["必要性说明", "necessity rationale"],
    ["数据清单摘要", "data inventory summary"],
    ["系统与出境链路说明", "system and transfer-chain description"],
    ["安全评估附件材料", "security assessment attachments"],
    ["处理者名称", "data processor name"],
    ["拟出境活动目的", "intended transfer activity purpose"],
    ["境外接收方名称", "overseas recipient name"],
    ["处理合法性基础", "processing legal basis"],
    ["拟出境个人信息", "personal information to be transferred"],
    ["告知机制", "notice mechanism"],
    ["单独同意机制", "separate consent mechanism"],
    ["个人权利请求渠道", "data-subject rights request channel"],
    ["保存与删除策略", "retention and deletion policy"],
    ["文档名称", "document title"],
    ["本次审查重点", "review focus"],
    ["合同或政策文本后再执行审查", "contract/policy text before running review"],
    ["数据出口方名称", "data exporter name"],
    ["数据进口方名称", "data importer name"],
    ["进口方国家/地区", "importer country/region"],
    ["传输目的", "transfer purpose"],
    ["数据类别", "data categories"],
    ["技术与组织措施（TOM）摘要", "technical and organizational measures (TOM) summary"],
    ["数据主体权利与投诉机制", "data-subject rights and complaint mechanism"],
    ["集团名称", "group name"],
    ["集团结构与申请主体信息", "group structure and applicant-entity information"],
    ["数据流与处理活动范围", "data flow and processing scope"],
    ["内部约束机制", "internal binding mechanism"],
    ["第三国法律评估机制", "third-country legal assessment mechanism"],
    ["政府访问请求处理机制", "government access request handling mechanism"],
    ["项目名称", "project name"],
    ["处理活动描述", "processing activity description"],
    ["目的与必要性说明", "purpose and necessity statement"],
    ["风险评估", "risk assessment"],
    ["缓解措施", "mitigation measures"],
    ["剩余风险结论", "residual risk conclusion"],
    ["第三国法律评估发现", "third-country law assessment findings"],
    ["技术性补充措施", "technical supplementary measures"],
    ["补充措施后的有效性判断", "post-supplementary effectiveness assessment"],
    ["关键行动项", "key action items"],
    ["数据清单附件（data_inventory）", "data inventory attachment (data_inventory)"],
    ["实体清单附件（entity_inventory）", "entity inventory attachment (entity_inventory)"],
    ["隐私政策URL", "privacy policy URL"],
    ["。", "."]
  ];
  for (const [from, to] of replacements) {
    text = replaceAllText(text, from, to);
  }

  if (/[\u4e00-\u9fff]/.test(text)) {
    text = "Invalid or missing required input. Please check required fields and attachments.";
  }
  return text;
};

const assertInput = (condition: boolean, message: string): void => {
  if (!condition) {
    throw new Error(currentUiLang() === "zh" ? message : toEnglishValidation(message));
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

const getDocumentReviewFileKey = (file: File): string => `${file.name}-${file.size}-${file.lastModified}`;

const getDocumentReviewFileExt = (name: string): string => {
  const normalized = name.toLowerCase();
  return normalized.includes(".") ? normalized.slice(normalized.lastIndexOf(".") + 1) : "";
};

const isDocumentReviewTextPreviewExt = (ext: string): boolean => ["txt", "md", "json", "csv"].includes(ext);

const isDocumentReviewImagePreviewExt = (ext: string): boolean =>
  ["png", "jpg", "jpeg", "gif", "webp", "bmp"].includes(ext);

const canInlinePreviewDocumentReviewExt = (ext: string): boolean =>
  ext === "pdf" || isDocumentReviewTextPreviewExt(ext) || isDocumentReviewImagePreviewExt(ext);

const getDocumentReviewTypeLabel = (ext: string): string => {
  if (ext === "pdf") return "PDF";
  if (ext === "docx") return "DOCX";
  if (ext === "doc") return "DOC";
  if (ext === "md") return "Markdown";
  if (ext === "txt") return "Text";
  if (ext === "csv") return "CSV";
  if (ext === "json") return "JSON";
  if (["jpg", "jpeg"].includes(ext)) return "JPG";
  if (ext === "png") return "PNG";
  if (ext === "gif") return "GIF";
  if (ext === "webp") return "WEBP";
  if (ext === "bmp") return "BMP";
  return ext ? ext.toUpperCase() : "FILE";
};

const formatDocumentReviewFileSize = (size: number): string => {
  if (size >= 1024 * 1024) {
    const value = size / (1024 * 1024);
    return `${value >= 10 ? value.toFixed(0) : value.toFixed(1)} MB`;
  }
  return `${Math.max(1, Math.round(size / 1024))} KB`;
};

const formatDocumentReviewFileDate = (value: number, lang: "zh" | "en"): string =>
  new Intl.DateTimeFormat(lang === "zh" ? "zh-CN" : "en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));

const getDocumentReviewDocTypeLabel = (value: DocumentReviewFormValues["document_type"]): string => {
  if (value === "privacy_policy") return "隐私政策";
  if (value === "scc_contract") return "标准合同";
  if (value === "dpa") return "数据处理协议";
  return "其他文档";
};

const getDocumentReviewExtractStatusMeta = (
  state?: DocumentReviewExtractState
): { label: string; tone: "neutral" | "loading" | "success" | "error" } => {
  if (!state) return { label: "待解析", tone: "neutral" };
  if (state.status === "loading") return { label: "解析中", tone: "loading" };
  if (state.status === "done") return { label: "已回填", tone: "success" };
  return { label: "需人工确认", tone: "error" };
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
  const base: AssessmentFormValues = {
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
  if (!DEV_ACCEL_ENABLED) return base;
  const preset = getAssessmentDevPreset();
  return {
    ...base,
    ...(preset.formDefaults as Partial<AssessmentFormValues>)
  };
};

const createDefaultDiagnosisValues = (): DiagnosisFormValues => {
  const demo = asRecord(getDefaultPayload("diagnosis"));
  const answers = asRecord(demo.answers);
  const toStrArray = (value: unknown): string[] => {
    if (Array.isArray(value)) return value.map((item) => String(item));
    if (typeof value === "string") {
      return value
        .split(/[,，\n]/)
        .map((item) => item.trim())
        .filter((item) => item.length > 0);
    }
    return [];
  };

  const base: DiagnosisFormValues = {
    company_name: toString(demo.company_name, ""),
    m1_industry: toString(answers.m1_industry, ""),
    m1_industry_other: toString(answers.m1_industry_other, ""),
    m1_business_channels: toStrArray(answers.m1_business_channels),
    m1_business_channels_other: toString(answers.m1_business_channels_other, ""),
    m1_service_targets: toString(answers.m1_service_targets, ""),
    m1_company_size: toString(answers.m1_company_size, ""),

    m2_core_needs: toStrArray(answers.m2_core_needs),
    m2_core_needs_other: toString(answers.m2_core_needs_other, ""),
    m2_had_compliance_issue: toString(answers.m2_had_compliance_issue, ""),
    m2_issue_description: toString(answers.m2_issue_description, ""),
    m2_deadline: toString(answers.m2_deadline, ""),
    m2_deadline_detail: toString(answers.m2_deadline_detail, ""),

    m3_processes_personal_info: toString(answers.m3_processes_personal_info, ""),
    m3_personal_info_types: toStrArray(answers.m3_personal_info_types),
    m3_processes_important_data: toString(answers.m3_processes_important_data, ""),
    m3_important_data_types: toStrArray(answers.m3_important_data_types),
    m3_important_data_types_other: toString(answers.m3_important_data_types_other, ""),
    m3_data_sources: toStrArray(answers.m3_data_sources),
    m3_data_sources_other: toString(answers.m3_data_sources_other, ""),
    m3_processing_activities: toStrArray(answers.m3_processing_activities),
    m3_data_volume_range: toString(answers.m3_data_volume_range, ""),
    m3_processes_enterprise_public_data: toString(answers.m3_processes_enterprise_public_data, ""),
    m3_enterprise_public_data_desc: toString(answers.m3_enterprise_public_data_desc, ""),
    m3_retention_period: toString(answers.m3_retention_period, ""),
    m3_retention_desc: toString(answers.m3_retention_desc, ""),

    m4_share_to_third_party: toString(answers.m4_share_to_third_party, ""),
    m4_third_party_types: toString(answers.m4_third_party_types, ""),
    m4_cross_border_transfer: toString(answers.m4_cross_border_transfer, ""),
    m4_cross_border_regions: toString(answers.m4_cross_border_regions, ""),
    m4_commercialization: toString(answers.m4_commercialization, ""),
    m4_commercialization_mode: toString(answers.m4_commercialization_mode, ""),
    m4_entrusted_processing: toString(answers.m4_entrusted_processing, ""),
    m4_entrusted_party_type: toString(answers.m4_entrusted_party_type, ""),
    m4_authorization_method: toString(answers.m4_authorization_method, ""),

    m5_systems: toStrArray(answers.m5_systems),
    m5_systems_other: toString(answers.m5_systems_other, ""),
    m5_security_measures: toStrArray(answers.m5_security_measures),
    m5_security_measures_other: toString(answers.m5_security_measures_other, ""),
    m5_compliance_docs: toStrArray(answers.m5_compliance_docs),
    m5_compliance_docs_other: toString(answers.m5_compliance_docs_other, ""),
    m5_penalty_or_complaint: toString(answers.m5_penalty_or_complaint, ""),
    m5_penalty_time: toString(answers.m5_penalty_time, ""),
    m5_penalty_reason: toString(answers.m5_penalty_reason, ""),
    m5_penalty_result: toString(answers.m5_penalty_result, "")
  };
  if (!DEV_ACCEL_ENABLED) return base;
  const preset = getModuleDevPreset("diagnosis");
  return { ...base, ...(preset.formDefaults as Partial<DiagnosisFormValues>) };
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

  const base: PipiaFormValues = {
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
  if (!DEV_ACCEL_ENABLED) return base;
  const preset = getModuleDevPreset("pipia");
  return { ...base, ...(preset.formDefaults as Partial<PipiaFormValues>) };
};

const createDefaultDocumentReviewValues = (): DocumentReviewFormValues => {
  const demo = asRecord(getDefaultPayload("scc"));
  const base: DocumentReviewFormValues = {
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
  if (!DEV_ACCEL_ENABLED) return base;
  const preset = getModuleDevPreset("document_review");
  return { ...base, ...(preset.formDefaults as Partial<DocumentReviewFormValues>) };
};

const inferDocTypeFromFileName = (name: string): DocumentReviewFormValues["document_type"] => {
  const normalized = name.toLowerCase();
  if (normalized.includes("scc") || normalized.includes("标准合同")) return "scc_contract";
  if (normalized.includes("dpa") || normalized.includes("数据处理协议")) return "dpa";
  return "privacy_policy";
};

const inferReviewFocusFromText = (text: string): string => {
  const normalized = text.toLowerCase();
  const points: string[] = [];
  if (normalized.includes("敏感") || normalized.includes("sensitive")) points.push("敏感个人信息处理边界");
  if (normalized.includes("跨境") || normalized.includes("cross-border")) points.push("跨境传输告知与规则");
  if (normalized.includes("同意") || normalized.includes("consent")) points.push("告知同意机制与撤回路径");
  if (normalized.includes("删除") || normalized.includes("更正") || normalized.includes("访问")) points.push("用户权利响应机制");
  if (normalized.includes("第三方") || normalized.includes("vendor")) points.push("第三方共享与委托处理条款");
  if (points.length === 0) {
    return "优先核查处理者身份披露、数据处理目的、权利救济与联系方式。";
  }
  return `优先核查：${points.slice(0, 4).join("、")}。`;
};

const buildAutoExtractResult = async (file: File): Promise<AutoExtractResult> => {
  const fileName = file.name;
  const extension = fileName.toLowerCase().includes(".")
    ? fileName.toLowerCase().slice(fileName.toLowerCase().lastIndexOf(".") + 1)
    : "";
  const typeFromName = inferDocTypeFromFileName(fileName);
  const titleFromName = fileName.replace(/\.[^.]+$/, "");

  let text = "";
  if (["txt", "md", "csv", "json"].includes(extension)) {
    try {
      text = await file.text();
    } catch {
      text = "";
    }
  }

  const normalized = text.toLowerCase();
  const extracted: AutoExtractResult = {
    documentTitle: titleFromName || "待确认文档",
    documentType: typeFromName,
    reviewFocus: inferReviewFocusFromText(text || fileName),
    transferPurpose:
      normalized.includes("跨境") || normalized.includes("cross-border")
        ? "根据文档内容，存在跨境传输相关描述，需重点核查出境规则。"
        : "待确认跨境传输目的与业务必要性。",
    sensitivePiDisclosed: normalized.includes("敏感") || normalized.includes("sensitive"),
    rightsChannelDisclosed:
      normalized.includes("联系") ||
      normalized.includes("邮箱") ||
      normalized.includes("email") ||
      normalized.includes("电话"),
    crossborderRuleDisclosed: normalized.includes("跨境") || normalized.includes("cross-border"),
    contactChannel:
      normalized.includes("邮箱") || normalized.includes("email")
        ? "文档中可能已披露邮箱渠道，请复核。"
        : "",
    note:
      text.length > 0
        ? "已基于可读文本自动提取并回填，建议逐项复核。"
        : "当前基于文件名进行初步回填（该格式暂不支持浏览器内全文解析）。",
  };

  return extracted;
};

const seedDocumentReviewValuesForFile = (base: DocumentReviewFormValues, file: File): DocumentReviewFormValues => ({
  ...base,
  document_title: file.name.replace(/\.[^.]+$/, "") || base.document_title,
  document_type: inferDocTypeFromFileName(file.name),
  review_focus: inferReviewFocusFromText(file.name)
});

const createDefaultEuSccValues = (): EuSccFormValues => {
  const demo = asRecord(getDefaultPayload("scc"));
  const base: EuSccFormValues = {
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
  if (!DEV_ACCEL_ENABLED) return base;
  const preset = getModuleDevPreset("scc");
  return { ...base, ...(preset.formDefaults as Partial<EuSccFormValues>) };
};

const createDefaultBcrValues = (): BcrFormValues => {
  const demo = asRecord(getDefaultPayload("bcr"));
  const base: BcrFormValues = {
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
  if (!DEV_ACCEL_ENABLED) return base;
  const preset = getModuleDevPreset("bcr");
  return { ...base, ...(preset.formDefaults as Partial<BcrFormValues>) };
};

const createDefaultDpiaValues = (): DpiaFormValues => {
  const demo = asRecord(getDefaultPayload("dpia"));
  const base: DpiaFormValues = {
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
  if (!DEV_ACCEL_ENABLED) return base;
  const preset = getModuleDevPreset("dpia");
  return { ...base, ...(preset.formDefaults as Partial<DpiaFormValues>) };
};

const createDefaultTiaValues = (): TiaFormValues => {
  const demo = asRecord(getDefaultPayload("tia"));
  const transferToolRaw = toString(demo.transfer_tool, "scc");
  const transferTool: TiaFormValues["transfer_tool"] =
    transferToolRaw === "bcr" || transferToolRaw === "derogation" ? transferToolRaw : "scc";
  const base: TiaFormValues = {
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
  if (!DEV_ACCEL_ENABLED) return base;
  const preset = getModuleDevPreset("tia");
  return { ...base, ...(preset.formDefaults as Partial<TiaFormValues>) };
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

const STEP_TITLE_EN: Record<string, string> = {
  "基础识别": "Basic Identification",
  "强制路径触发项": "Mandatory Path Triggers",
  "补充说明": "Supplementary Notes",
  "主体基础信息": "Entity Basics",
  "自评估工作组织": "Assessment Team Setup",
  "出境场景与必要性": "Transfer Scenario and Necessity",
  "数据清单与链路": "Data Inventory and Transfer Chain",
  "执行策略与材料": "Execution Strategy and Materials",
  "企业基本信息": "Enterprise Profile",
  "出境场景与范围": "Transfer Scenario and Scope",
  "权利保障与响应": "Rights Protection and Response",
  "审查对象": "Review Subject",
  "披露完整性检查": "Disclosure Completeness Check",
  "出境与处理背景": "Transfer and Processing Context",
  "审查重点与附件": "Review Focus and Attachments",
  "传输主体与模块": "Transfer Parties and Modules",
  "场景与数据范围": "Scenario and Data Scope",
  "条款与保障机制": "Clauses and Safeguards",
  "审查文件": "Review Files",
  "主体与范围": "Entity and Scope",
  "约束力与权利机制": "Binding Force and Rights",
  "治理与监管协作": "Governance and Regulatory Cooperation",
  "更新与文档材料": "Updates and Documentation",
  "项目与触发理由": "Project and Trigger",
  "必要性与相称性": "Necessity and Proportionality",
  "风险与缓解措施": "Risks and Mitigations",
  "出境数据清单": "Outbound Data Inventory",
  "外部实体清单": "External Entity Inventory",
  "内部访问与材料": "Internal Access and Materials",
  "企业信息与适用性": "Business Profile and Applicability",
  "消费者权利机制": "Consumer Rights Process",
  "敏感信息与第三方管理": "Sensitive Data and Vendor Governance",
  "附件上传": "File Uploads"
};

const FIELD_LABEL_EN: Record<string, string> = {
  company_name: "Company Name",
  company_uscc: "Unified Social Credit Code",
  legal_representative: "Legal Representative",
  registered_address: "Registered Address",
  company_nature: "Company Nature",
  industry: "Industry",
  receiver_country: "Recipient Country / Region",
  receiver_name: "Overseas Recipient Name",
  q5_no_personal_info: "Q1 Is the outbound dataset completely free of personal information and important data?",
  q6_scenario: "Q2 What is the main business scenario for this outbound transfer?",
  q7_receiver_type: "Q3 What type of overseas recipient is involved?",
  q1_is_ciio: "Q4 Is the company a Critical Information Infrastructure Operator (CIIO)?",
  q2_has_important_data: "Q5 Does the outbound dataset include important data?",
  q3_pii_count: "Q6 Within the past 2 months, how many individuals' personal information has been provided overseas?",
  q4_spi_count: "Q7 Within the past 2 months, how many individuals' sensitive personal information has been provided overseas?",
  q8_purpose: "Q8 Additional context and purpose notes",
  assessment_start_date: "Assessment Start Date",
  assessment_end_date: "Assessment End Date",
  lead_department: "Lead Department",
  participant_departments: "Participating Departments (comma-separated)",
  third_party_support: "Third-Party Support Involved",
  third_party_name: "Third-Party Organization Name",
  third_party_scope: "Third-Party Scope",
  scenario_name: "Scenario Name",
  transfer_frequency: "Transfer Frequency",
  is_long_term: "Long-term / Ongoing Transfer",
  transfer_purpose: "Transfer Purpose",
  legal_basis: "Legal Basis",
  necessity_basis: "Necessity Explanation",
  is_ciio: "Is CIIO",
  contains_important_data: "Contains Important Data",
  pii_count: "PI Volume",
  spi_count: "SPI Volume",
  data_inventory_summary: "Data Inventory Summary",
  system_chain_summary: "System and Transfer Chain Description",
  security_capability_summary: "Security Capability Summary",
  force_override_path: "Allow Output Even if Path Differs",
  shareholding_structure: "Shareholding Structure",
  actual_controller: "Actual Controller",
  overseas_investment: "Domestic and Overseas Investments",
  org_structure_privacy_team: "Org Structure and Privacy Team",
  business_overview: "Business Overview",
  processing_activity_overview: "Processing Activity Overview",
  processing_person_count: "PI Processing Scale",
  outbound_pi_count: "Outbound PI Volume",
  outbound_spi_count: "Outbound SPI Volume",
  route_type: "Route Type",
  outbound_scenario_name: "Outbound Scenario Name",
  outbound_frequency: "Outbound Frequency",
  transfer_method: "Transfer Method (API / file / sync)",
  domestic_storage: "Domestic Storage System / DC",
  overseas_storage: "Overseas Storage System / DC",
  transfer_link: "Transfer Chain Description",
  purpose: "Purpose",
  recipient_name: "Recipient Name",
  recipient_country_region: "Recipient Country / Region",
  legality_justification: "Legality Analysis",
  necessity_justification: "Necessity Analysis",
  pi_categories: "PI Categories (comma-separated)",
  spi_categories: "SPI Categories (comma-separated)",
  subject_volume: "Data Subject Volume",
  notice_mechanism: "Notice Mechanism",
  consent_mechanism: "Consent Mechanism",
  dsar_channel: "DSAR Channel",
  retention_policy: "Retention / Deletion Policy",
  incident_response_sla_hours: "Incident Response SLA (hours)",
  escalation_path: "Escalation Path",
  attachment_role: "Attachment Role",
  publisher_entity: "Publishing Entity",
  document_title: "Document Title",
  document_version: "Document Version",
  effective_date: "Effective Date",
  applicable_products: "Applicable Products / Sites",
  applicable_scope: "Applicable Scope",
  is_live_version: "Live Version",
  document_type: "Document Type",
  processor_identity_disclosed: "Discloses Processor Identity",
  scope_disclosed: "Discloses Scope",
  collection_purpose_disclosed: "Discloses Collection and Processing Purpose",
  processing_method_disclosed: "Discloses Processing Method",
  category_disclosed: "Discloses PI Categories",
  sensitive_pi_disclosed: "Discloses Sensitive PI Processing",
  crossborder_rule_disclosed: "Discloses Cross-Border Rules",
  rights_channel_disclosed: "Discloses Rights Exercise Channel",
  contact_channel: "Contact / Complaint Channel",
  has_scc_draft: "Has Existing Draft",
  review_focus: "Review Focus",
  exporter_name: "Data Exporter (EEA)",
  importer_name: "Data Importer (Third Country)",
  importer_country: "Importer Country / Region",
  transfer_role: "Transfer Role",
  scc_version: "SCC Version",
  data_categories: "Data Categories",
  data_subject_categories: "Data Subject Categories",
  retention_rule: "Retention Rule",
  tom_summary: "Technical and Organizational Measures (TOM) Summary",
  onward_transfer_control: "Onward Transfer / Subprocessor Control",
  rights_and_complaint: "Rights and Complaint Mechanism",
  government_access_response: "Government Access Response",
  supplementary_clause_review: "Supplementary Clause Review Focus",
  group_structure: "Group Structure",
  applicant_entity: "Applicant Entity and Responsibilities",
  lead_sa_rationale: "Lead SA Rationale",
  data_flow_scope: "Data Flow and Processing Scope",
  binding_mechanism: "Binding Mechanism",
  third_party_beneficiary: "Third-Party Beneficiary Rights",
  liability_compensation: "Liability and Compensation",
  transparency_notice: "Transparency and Notice",
  training_audit: "Training and Audit Mechanism",
  cooperation_with_sa: "Cooperation with Supervisory Authority",
  dp_safeguards: "Data Protection Safeguards",
  third_country_assessment: "Third-Country Law Assessment",
  government_access_process: "Government Access Handling Process",
  update_mechanism: "Update Mechanism",
  definitions_quality: "Definitions and Terminology Quality",
  project_name: "Project Name",
  project_goal: "Project Goal",
  need_reason: "Main Trigger for DPIA",
  controller_name: "Controller Name",
  dpo_role: "DPO / Privacy Role",
  processing_description: "Processing Description",
  data_types: "Data Types",
  subject_scale: "Data Subject Scale",
  frequency: "Frequency",
  retention_period: "Retention Period",
  geo_scope: "Geographic Scope",
  data_source: "Data Source",
  includes_special_data: "Includes Special Category Data",
  has_crossborder_transfer: "Includes Cross-Border Transfer",
  vulnerable_group: "Vulnerable Group",
  relationship_context: "Relationship Context",
  purpose_and_necessity: "Purpose and Necessity",
  expectation_control: "Reasonable Expectations and Control",
  lawful_basis: "Lawful Basis",
  prior_concerns: "Prior Concerns / Incidents",
  novel_technology: "Novel Technology",
  function_creep_control: "Function Creep Control",
  minimization_quality: "Minimization and Data Quality",
  notice_plan: "Notice Plan",
  rights_support: "Rights Support",
  processor_management: "Processor / Vendor Management",
  risk_assessment: "Risk Assessment",
  mitigation_measures: "Mitigation Measures",
  residual_risk: "Residual Risk",
  signoff_owner: "Sign-off Owner",
  dpo_advice: "DPO Advice",
  review_schedule: "Review Schedule",
  data_exporter_name: "Data Exporter (EU)",
  data_importer_name: "Data Importer",
  importer_country_region: "Importer Country / Region",
  law_assessed: "Law Assessment Completed",
  law_findings: "Law and Practice Findings",
  pre_effectiveness: "Effectiveness Before Supplementary Measures",
  supplementary_technical: "Technical Supplementary Measures",
  supplementary_contractual: "Contractual Supplementary Measures",
  supplementary_organizational: "Organizational Supplementary Measures",
  post_effectiveness: "Effectiveness After Supplementary Measures",
  key_actions: "Key Action Items",
  transfer_chain: "Transfer Chain Description",
  sensitive_data_flags: "Sensitive / Important Data Flags",
  data_volume_note: "Data Volume Notes",
  primary_recipient_name: "Primary Recipient Name",
  primary_recipient_country: "Primary Recipient Country / Region",
  primary_recipient_role: "Primary Recipient Role",
  primary_recipient_restricted: "Primary Recipient Is Restricted",
  additional_recipients: "Additional Recipients (one per line: name, country, role, restricted[yes/no])",
  internal_access_note: "Internal Access Notes",
  dba_name: "DBA / Brand Name",
  cpra_applicability_selfcheck: "CPRA Applicability Self-Check",
  business_model: "Business Model",
  data_lifecycle: "Data Lifecycle",
  privacy_policy_url: "Privacy Policy URL",
  consumer_rights_process: "Consumer Rights Process",
  identity_verification_method: "Identity Verification Method",
  rights_sla: "Rights SLA",
  opt_out_and_sale_sharing: "Sale / Sharing and Opt-Out",
  spi_usage_summary: "SPI Usage Summary",
  vendor_management: "Vendor Management",
  ui_dark_pattern_check: "UI / UX Dark Pattern Check"
};

const TEXT_EN_BY_ZH: Record<string, string> = {
  "否（含个人信息或重要数据）": "No (contains personal information or important data)",
  "是（纯匿名技术数据）": "Yes (purely anonymous technical data)",
  "不确定": "Unknown",
  "其他商业目的": "Other Business Purpose",
  "履行合同 / 向消费者提供服务": "Contract Performance / Consumer Services",
  "跨国公司内部人力资源管理": "Intra-group HR Management",
  "紧急情况下保护自然人生命、健康或财产安全": "Emergency Protection of Life, Health or Property",
  "依法履行法定职责或法定义务": "Compliance with Legal Duties or Obligations",
  "独立第三方（合作伙伴 / 服务商）": "Independent Third Party (partner / vendor)",
  "集团内部关联公司": "Intra-group Affiliate",
  "上一步": "Previous",
  "下一步": "Next",
  "上传待审文本": "Upload Documents for Review",
  "SCC文本与配套材料上传": "Upload SCC Text and Supporting Materials",
  "BCR主文本与配套材料上传（仅docx/pdf）": "Upload BCR Main Text and Supporting Materials (docx/pdf)",
  "DPIA附件上传（docx/pdf/png/jpg）": "Upload DPIA Attachments (docx/pdf/png/jpg)",
  "TIA附件上传（docx/pdf）": "Upload TIA Attachments (docx/pdf)",
  "数据清单附件（必传，data_inventory）": "Data Inventory Attachment (required, data_inventory)",
  "实体清单附件（必传，entity_inventory）": "Entity Inventory Attachment (required, entity_inventory)",
  "补充材料（可选，supporting_material）": "Supporting Materials (optional, supporting_material)",
  "隐私政策（privacy_policy）": "Privacy Policy (privacy_policy)",
  "请至少上传1份合同或政策文本后再执行。": "Upload at least one contract or policy document before running.",
  "请至少上传1份SCC文本或附件后再提交。": "Upload at least one SCC text or supporting file before submitting.",
  "请上传附件材料后再提交。": "Upload supporting materials before submitting.",
  "请至少上传1份PIPIA附件后再提交。": "Upload at least one PIPIA attachment before submitting.",
  "请至少上传1份BCR材料后再提交。": "Upload at least one BCR document before submitting.",
  "请至少上传1份DPIA附件后再提交。": "Upload at least one DPIA attachment before submitting.",
  "请至少上传1份TIA附件后再提交。": "Upload at least one TIA attachment before submitting.",
  "请至少上传1份数据清单（xlsx/csv/docx/pdf）。": "Upload at least one data inventory file (xlsx/csv/docx/pdf).",
  "请至少上传1份实体清单（xlsx/csv/docx/pdf）。": "Upload at least one entity inventory file (xlsx/csv/docx/pdf).",
  "可上传股权结构组织架构合同台账等辅助材料。": "You may upload supporting materials such as shareholding charts, org charts, and contract ledgers.",
  "可填写URL，也可上传文档，两者满足其一即可。": "You may provide a URL or upload a file. Either one is sufficient.",
  "若未提供URL，请至少上传1份隐私政策文件。": "If no URL is provided, upload at least one privacy policy file.",
  "可上传。": "Optional upload.",
  "privacy_policy": "Privacy Policy",
  "scc_contract": "Standard Contract",
  "dpa": "Data Processing Agreement",
  "other": "Other",
  one_time: "One-time",
  periodic: "Periodic",
  continuous: "Continuous",
  scc_filing: "SCC Filing",
  certification: "Certification",
  processor: "Processor",
  controller: "Controller",
  subprocessor: "Subprocessor",
  affiliate: "Affiliate",
  vendor: "Vendor",
  c2c: "Controller to Controller",
  c2p: "Controller to Processor",
  p2p: "Processor to Processor",
  p2c: "Processor to Controller",
  eu_2021: "EU 2021 SCC",
  other_business: "Other"
};

const humanizeKey = (value: string): string =>
  value
    .split(/[_-]/)
    .filter(Boolean)
    .map((part) => {
      const upperMap: Record<string, string> = {
        uscc: "USCC",
        cpra: "CPRA",
        dpia: "DPIA",
        tia: "TIA",
        dpo: "DPO",
        sla: "SLA",
        url: "URL",
        ui: "UI",
        ux: "UX",
        spi: "SPI",
        pii: "PII",
        pi: "PI",
        ciio: "CIIO",
        scc: "SCC",
        bcr: "BCR",
        dsar: "DSAR",
        dsr: "DSR",
        tom: "TOM",
        eea: "EEA",
        eu: "EU",
        cpra_applicability_selfcheck: "CPRA Applicability Self-Check"
      };
      if (upperMap[part]) return upperMap[part];
      return part.charAt(0).toUpperCase() + part.slice(1);
    })
    .join(" ");

const localizeStepTitle = (lang: "zh" | "en", title: string): string =>
  lang === "en" ? (STEP_TITLE_EN[title] ?? title) : title;

const localizeFieldLabel = (lang: "zh" | "en", fieldName: string, label: string): string =>
  lang === "en" ? (FIELD_LABEL_EN[fieldName] ?? humanizeKey(fieldName)) : label;

const localizeOptionLabel = (lang: "zh" | "en", key: string, fallback: string): string =>
  lang === "en" ? (TEXT_EN_BY_ZH[fallback] ?? TEXT_EN_BY_ZH[key] ?? humanizeKey(key)) : fallback;

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
  // Citation highlights (for review module structured_citations)
  if (insight.citations.length > 0) {
    const topCitations = insight.citations.slice(0, 5).map(
      (c) => `《${c.source_title}》${c.article}`.trim()
    );
    if (topCitations.length > 0) {
      highlights.push(`${lang === "zh" ? "审查引用法规" : "Cited Regulations"}：${topCitations.join("、")}`);
    }
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

const REVIEW_ASYNC_STATE_LABEL: Record<string, string> = {
  created: "已创建任务",
  uploaded: "文件已接收",
  segmenting: "正在切分条款",
  classifying: "正在识别条款类型",
  reviewing: "正在专项审查",
  aggregating: "正在汇总问题",
  rendering: "正在生成报告",
  completed: "已完成",
  failed: "执行失败",
};

export function ModuleRunPanel({ onRunDone, taskSpace }: ModuleRunPanelProps) {
  const { t, lang } = useLang();
  const diagnosisStepTopRef = useRef<HTMLDivElement | null>(null);
  const [jurisdiction, setJurisdiction] = useState<(typeof JURISDICTIONS)[number]>(taskSpace.jurisdiction);
  const [moduleKey, setModuleKey] = useState<ModuleKey>(taskSpace.module);
  const [payloadText, setPayloadText] = useState("");
  const [responseData, setResponseData] = useState<unknown>(undefined);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [asyncRunProgress, setAsyncRunProgress] = useState<AsyncRunProgressState | null>(null);
  const [diagnosisStepIndex, setDiagnosisStepIndex] = useState(0);
  const [diagnosisValues, setDiagnosisValues] = useState<DiagnosisFormValues>(createDefaultDiagnosisValues);
  const [assessmentStepIndex, setAssessmentStepIndex] = useState(0);
  const [assessmentValues, setAssessmentValues] = useState<AssessmentFormValues>(createDefaultAssessmentValues);
  const [assessmentFiles, setAssessmentFiles] = useState<File[]>([]);
  const [assessmentDevFilePaths, setAssessmentDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getAssessmentDevPreset().backendFilePaths : []
  );
  const [pipiaStepIndex, setPipiaStepIndex] = useState(0);
  const [pipiaValues, setPipiaValues] = useState<PipiaFormValues>(createDefaultPipiaValues);
  const [pipiaFiles, setPipiaFiles] = useState<File[]>([]);
  const [pipiaDevFilePaths, setPipiaDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getModuleDevPreset("pipia").backendFilePaths : []
  );
  const [documentReviewValues, setDocumentReviewValues] = useState<DocumentReviewFormValues>(createDefaultDocumentReviewValues);
  const [documentReviewFiles, setDocumentReviewFiles] = useState<File[]>([]);
  const [documentReviewDevFilePaths, setDocumentReviewDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getModuleDevPreset("document_review").backendFilePaths : []
  );
  const [documentReviewSelectedFileIndex, setDocumentReviewSelectedFileIndex] = useState(0);
  const [documentReviewPreviewUrl, setDocumentReviewPreviewUrl] = useState<string | null>(null);
  const [documentReviewTextPreview, setDocumentReviewTextPreview] = useState("");
  const [documentReviewFileFormValues, setDocumentReviewFileFormValues] = useState<Record<string, DocumentReviewFormValues>>(
    {}
  );
  const [documentReviewExtractStates, setDocumentReviewExtractStates] = useState<Record<string, DocumentReviewExtractState>>(
    {}
  );
  const documentReviewParsedKeysRef = useRef<Set<string>>(new Set());
  const [euSccStepIndex, setEuSccStepIndex] = useState(0);
  const [euSccValues, setEuSccValues] = useState<EuSccFormValues>(createDefaultEuSccValues);
  const [euSccFiles, setEuSccFiles] = useState<File[]>([]);
  const [euSccDevFilePaths, setEuSccDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getModuleDevPreset("scc").backendFilePaths : []
  );
  const [bcrStepIndex, setBcrStepIndex] = useState(0);
  const [bcrValues, setBcrValues] = useState<BcrFormValues>(createDefaultBcrValues);
  const [bcrFiles, setBcrFiles] = useState<File[]>([]);
  const [bcrDevFilePaths, setBcrDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getModuleDevPreset("bcr").backendFilePaths : []
  );
  const [dpiaStepIndex, setDpiaStepIndex] = useState(0);
  const [dpiaValues, setDpiaValues] = useState<DpiaFormValues>(createDefaultDpiaValues);
  const [dpiaFiles, setDpiaFiles] = useState<File[]>([]);
  const [dpiaDevFilePaths, setDpiaDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getModuleDevPreset("dpia").backendFilePaths : []
  );
  const [tiaStepIndex, setTiaStepIndex] = useState(0);
  const [tiaValues, setTiaValues] = useState<TiaFormValues>(createDefaultTiaValues);
  const [tiaFiles, setTiaFiles] = useState<File[]>([]);
  const [tiaDevFilePaths, setTiaDevFilePaths] = useState<string[]>(() =>
    DEV_ACCEL_ENABLED ? getModuleDevPreset("tia").backendFilePaths : []
  );
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
      setAssessmentDevFilePaths(DEV_ACCEL_ENABLED ? getAssessmentDevPreset().backendFilePaths : []);
    }
    if (moduleKey === "pipia") {
      setPipiaStepIndex(0);
      setPipiaValues(createDefaultPipiaValues());
      setPipiaFiles([]);
      setPipiaDevFilePaths(DEV_ACCEL_ENABLED ? getModuleDevPreset("pipia").backendFilePaths : []);
    }
    if (taskTemplate?.id === "cn_document_review") {
      setDocumentReviewValues(createDefaultDocumentReviewValues());
      setDocumentReviewFiles([]);
      setDocumentReviewDevFilePaths(DEV_ACCEL_ENABLED ? getModuleDevPreset("document_review").backendFilePaths : []);
      setDocumentReviewSelectedFileIndex(0);
      setDocumentReviewPreviewUrl(null);
      setDocumentReviewTextPreview("");
      setDocumentReviewFileFormValues({});
      setDocumentReviewExtractStates({});
      documentReviewParsedKeysRef.current = new Set();
    }
    if (taskTemplate?.id === "eu_scc") {
      setEuSccStepIndex(0);
      setEuSccValues(createDefaultEuSccValues());
      setEuSccFiles([]);
      setEuSccDevFilePaths(DEV_ACCEL_ENABLED ? getModuleDevPreset("scc").backendFilePaths : []);
    }
    if (moduleKey === "bcr") {
      setBcrStepIndex(0);
      setBcrValues(createDefaultBcrValues());
      setBcrFiles([]);
      setBcrDevFilePaths(DEV_ACCEL_ENABLED ? getModuleDevPreset("bcr").backendFilePaths : []);
    }
    if (moduleKey === "dpia") {
      setDpiaStepIndex(0);
      setDpiaValues(createDefaultDpiaValues());
      setDpiaFiles([]);
      setDpiaDevFilePaths(DEV_ACCEL_ENABLED ? getModuleDevPreset("dpia").backendFilePaths : []);
    }
    if (moduleKey === "tia") {
      setTiaStepIndex(0);
      setTiaValues(createDefaultTiaValues());
      setTiaFiles([]);
      setTiaDevFilePaths(DEV_ACCEL_ENABLED ? getModuleDevPreset("tia").backendFilePaths : []);
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

  useEffect(() => {
    if (!isDiagnosisModule) return;
    const anchor = diagnosisStepTopRef.current;
    if (!anchor) return;
    const frame = requestAnimationFrame(() => {
      anchor.scrollIntoView({ block: "start", behavior: "auto" });
    });
    return () => cancelAnimationFrame(frame);
  }, [isDiagnosisModule, diagnosisStepIndex]);

  const updateDiagnosisValue = (name: string, value: unknown) => {
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
    const nextValues = { ...documentReviewValues, [name]: value };
    setDocumentReviewValues(nextValues);
    const activeFile = documentReviewFiles[documentReviewSelectedFileIndex] ?? null;
    if (activeFile) {
      const fileKey = getDocumentReviewFileKey(activeFile);
      setDocumentReviewFileFormValues((prev) => ({ ...prev, [fileKey]: nextValues }));
    }
  };

  const syncDocumentReviewValuesForFile = (file: File) => {
    const fileKey = getDocumentReviewFileKey(file);
    const savedValues = documentReviewFileFormValues[fileKey];
    if (savedValues) {
      setDocumentReviewValues(savedValues);
      return;
    }

    const defaultValues = createDefaultDocumentReviewValues();
    const seededValues = seedDocumentReviewValuesForFile(
      {
        ...defaultValues,
        company_name: documentReviewValues.company_name || defaultValues.company_name,
        publisher_entity: documentReviewValues.publisher_entity || defaultValues.publisher_entity,
        receiver_name: documentReviewValues.receiver_name || defaultValues.receiver_name,
        receiver_country: documentReviewValues.receiver_country || defaultValues.receiver_country,
        transfer_purpose: documentReviewValues.transfer_purpose || defaultValues.transfer_purpose,
        pii_count: documentReviewValues.pii_count,
        spi_count: documentReviewValues.spi_count,
        has_scc_draft: documentReviewValues.has_scc_draft,
        review_focus: documentReviewValues.review_focus || defaultValues.review_focus,
        contact_channel: documentReviewValues.contact_channel || defaultValues.contact_channel,
        sensitive_pi_disclosed: documentReviewValues.sensitive_pi_disclosed,
        rights_channel_disclosed: documentReviewValues.rights_channel_disclosed,
        crossborder_rule_disclosed: documentReviewValues.crossborder_rule_disclosed
      },
      file
    );

    setDocumentReviewValues(seededValues);
    setDocumentReviewFileFormValues((prev) => ({ ...prev, [fileKey]: seededValues }));
  };

  const onSelectDocumentReviewFiles = (incomingFiles: FileList | null) => {
    const next = Array.from(incomingFiles ?? []);
    if (next.length === 0) return;
    const hadNoUploadedFiles = documentReviewFiles.length === 0;
    setDocumentReviewFiles((prev) => {
      const merged = [...prev];
      for (const file of next) {
        const duplicate = merged.some(
          (item) =>
            item.name === file.name &&
            item.size === file.size &&
            item.lastModified === file.lastModified
        );
        if (!duplicate) {
          merged.push(file);
        }
      }
      return merged;
    });
    if (hadNoUploadedFiles) {
      setDocumentReviewSelectedFileIndex(0);
      syncDocumentReviewValuesForFile(next[0]);
    }
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

  const buildAssessmentPayloadFrom = async (
    values: AssessmentFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(hasText(values.company_name), "请填写企业名称。");
    assertInput(hasText(values.company_uscc, 8), "请填写统一社会信用代码（至少8位）。");
    assertInput(hasText(values.receiver_country), "请填写接收方国家/地区。");
    assertInput(hasText(values.transfer_purpose), "请填写出境目的。");
    assertInput(hasText(values.legal_basis), "请填写合法性基础。");
    assertInput(hasText(values.necessity_basis), "请填写必要性说明。");
    assertInput(hasText(values.data_inventory_summary), "请填写数据清单摘要。");
    assertInput(hasText(values.system_chain_summary), "请填写系统与出境链路说明。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(
      files.length > 0 || presetFilePaths.length > 0,
      "请上传至少1份安全评估附件材料（如数据清单、系统链路图、制度文件）。"
    );

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
    const trimOr = (value: string, fallback: string): string => {
      const trimmed = value.trim();
      return trimmed.length >= 2 ? trimmed : fallback;
    };
    const purposeContext = [
      values.transfer_purpose.trim(),
      values.scenario_name ? `场景：${values.scenario_name}` : "",
      values.legal_basis ? `合法性：${values.legal_basis}` : "",
      values.necessity_basis ? `必要性：${values.necessity_basis}` : "",
      values.data_inventory_summary ? `数据清单：${values.data_inventory_summary}` : "",
      values.system_chain_summary ? `链路：${values.system_chain_summary}` : "",
      values.security_capability_summary ? `保障能力：${values.security_capability_summary}` : "",
      values.assessment_start_date || values.assessment_end_date
        ? `自评估周期：${values.assessment_start_date || "未填"} 至 ${values.assessment_end_date || "未填"}`
        : "",
      values.lead_department ? `牵头部门：${values.lead_department}` : "",
      values.participant_departments ? `参与部门：${values.participant_departments}` : "",
      values.third_party_support
        ? `第三方支持：${values.third_party_name || "已参与"}；${values.third_party_scope || "范围未填"}`
        : ""
    ]
      .filter((item) => item.length > 0)
      .join("；");

    return {
      company_name: trimOr(values.company_name, "待确认企业"),
      industry: trimOr(
        [values.industry, values.company_nature].filter((item) => item.trim().length > 0).join(" / "),
        "未说明行业"
      ),
      is_ciio: values.is_ciio,
      contains_important_data: values.contains_important_data,
      pii_count: Math.max(0, values.pii_count),
      spi_count: Math.max(0, values.spi_count),
      transfer_purpose: trimOr(purposeContext, "数据出境场景评估与风险自评估"),
      receiver_country: trimOr(values.receiver_country, "待确认国家"),
      force_override_path: values.force_override_path,
      uploaded_files: uploadedFiles
    };
  };

  const buildAssessmentPayload = async (): Promise<unknown> =>
    buildAssessmentPayloadFrom(assessmentValues, assessmentFiles, assessmentDevFilePaths);

  const buildPipiaPayloadFrom = async (
    values: PipiaFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(hasText(values.company_name), "请填写处理者名称。");
    assertInput(hasText(values.company_uscc, 8), "请填写统一社会信用代码（至少8位）。");
    assertInput(hasText(values.purpose), "请填写拟出境活动目的。");
    assertInput(hasText(values.recipient_name), "请填写境外接收方名称。");
    assertInput(hasText(values.recipient_country_region), "请填写接收方国家/地区。");
    assertInput(hasText(values.legal_basis), "请填写处理合法性基础。");
    assertInput(splitCsv(values.pi_categories).length > 0, "请至少填写一类拟出境个人信息。");
    assertInput(hasText(values.notice_mechanism), "请填写告知机制。");
    assertInput(hasText(values.consent_mechanism), "请填写单独同意机制。");
    assertInput(hasText(values.dsar_channel), "请填写个人权利请求渠道。");
    assertInput(hasText(values.retention_policy), "请填写保存与删除策略。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(files.length > 0 || presetFilePaths.length > 0, "请上传至少1份PIPIA相关附件。");
    if (values.route_type === "scc_filing") {
      assertInput(
        values.attachment_role === "scc_contract",
        "标准合同备案路径下，附件角色需选择为 scc_contract。"
      );
    }

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
    const trimOr = (value: string, fallback: string): string => {
      const trimmed = value.trim();
      return trimmed.length >= 2 ? trimmed : fallback;
    };
    const attachments = uploadedFiles.map((path) => ({
      file_role: values.attachment_role,
      file_name: basenameFromPath(path),
      file_format: inferAttachmentFormat(path),
      storage_uri: path
    }));

    return {
      route_type: values.route_type,
      company_profile: {
        company_name: trimOr(values.company_name, "待确认企业"),
        company_uscc: values.company_uscc.trim().length >= 8 ? values.company_uscc.trim() : "91310000XXXXXXXXXX",
        is_ciio: values.is_ciio,
        processing_person_count: values.processing_person_count,
        outbound_pi_count: values.outbound_pi_count,
        outbound_spi_count: values.outbound_spi_count,
        industry: trimOr(values.industry, "未说明行业")
      },
      transfer_context: {
        purpose: trimOr(
          [
            values.purpose,
            values.outbound_scenario_name ? `场景：${values.outbound_scenario_name}` : "",
            values.outbound_frequency ? `频率：${values.outbound_frequency}` : "",
            values.transfer_method ? `方式：${values.transfer_method}` : "",
            values.business_overview ? `业务概况：${values.business_overview}` : "",
            values.processing_activity_overview ? `处理活动：${values.processing_activity_overview}` : ""
          ].filter((item) => item.trim().length > 0).join("；"),
          "个人信息出境处理活动评估"
        ),
        recipient_name: trimOr(values.recipient_name, "待确认接收方"),
        recipient_country_region: trimOr(values.recipient_country_region, "待确认国家/地区"),
        legal_basis: trimOr(
          [
            values.legal_basis,
            values.legality_justification ? `合法性论证：${values.legality_justification}` : "",
            values.necessity_justification ? `必要性论证：${values.necessity_justification}` : ""
          ].filter((item) => item.trim().length > 0).join("；"),
          "合同履行必要"
        )
      },
      personal_info_scope: {
        pi_categories: splitCsv(values.pi_categories).length > 0 ? splitCsv(values.pi_categories) : ["账户信息"],
        spi_categories: splitCsv(values.spi_categories),
        subject_volume: values.subject_volume
      },
      rights_protection: {
        notice_mechanism: trimOr(values.notice_mechanism, "隐私政策告知"),
        consent_mechanism: trimOr(values.consent_mechanism, "单独同意"),
        dsar_channel: trimOr(values.dsar_channel, "privacy@example.com"),
        retention_policy: trimOr(
          [
            values.retention_policy,
            values.domestic_storage ? `境内存储：${values.domestic_storage}` : "",
            values.overseas_storage ? `境外存储：${values.overseas_storage}` : ""
          ].filter((item) => item.trim().length > 0).join("；"),
          "到期删除+最短必要"
        )
      },
      emergency_plan: {
        incident_response_sla_hours: values.incident_response_sla_hours,
        escalation_path: trimOr(
          [
            values.escalation_path,
            values.transfer_link ? `链路：${values.transfer_link}` : "",
            values.shareholding_structure ? `股权：${values.shareholding_structure}` : "",
            values.actual_controller ? `控制人：${values.actual_controller}` : "",
            values.overseas_investment ? `境内外投资：${values.overseas_investment}` : "",
            values.org_structure_privacy_team ? `组织与个保机构：${values.org_structure_privacy_team}` : ""
          ].filter((item) => item.trim().length > 0).join("；"),
          "DPO -> 法务 -> 管理层"
        )
      },
      attachments
    };
  };

  const buildPipiaPayload = async (): Promise<unknown> =>
    buildPipiaPayloadFrom(pipiaValues, pipiaFiles, pipiaDevFilePaths);

  const buildDocumentReviewPayloadFrom = async (
    values: DocumentReviewFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(
      hasText(values.publisher_entity) || hasText(values.company_name),
      "请填写企业名称或发布主体。"
    );
    assertInput(hasText(values.document_title), "请填写文档名称。");
    assertInput(hasText(values.review_focus), "请填写本次审查重点。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(files.length > 0 || presetFilePaths.length > 0, "请至少上传1份合同或政策文本后再执行审查。");

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
    const trimOr = (value: string, fallback: string): string => {
      const trimmed = value.trim();
      return trimmed.length >= 2 ? trimmed : fallback;
    };
    const reviewContext = [
      values.document_title ? `文档：${values.document_title}` : "",
      values.document_version ? `版本：${values.document_version}` : "",
      values.effective_date ? `生效日期：${values.effective_date}` : "",
      values.applicable_products ? `适用产品：${values.applicable_products}` : "",
      values.applicable_scope ? `适用范围：${values.applicable_scope}` : "",
      values.is_live_version ? "当前线上生效版本" : "非线上生效版本",
      values.transfer_purpose.trim(),
      `${DOCUMENT_TYPE_LABEL[values.document_type]}审查`,
      values.processor_identity_disclosed ? "已披露处理者身份" : "未明确披露处理者身份",
      values.scope_disclosed ? "已披露适用范围" : "未明确披露适用范围",
      values.collection_purpose_disclosed ? "已披露收集与处理目的" : "未充分披露收集与处理目的",
      values.processing_method_disclosed ? "已披露处理方式" : "未充分披露处理方式",
      values.category_disclosed ? "已披露个人信息种类" : "未充分披露个人信息种类",
      values.sensitive_pi_disclosed ? "已披露敏感信息处理" : "未充分披露敏感信息处理",
      values.crossborder_rule_disclosed ? "已披露出境规则" : "未充分披露出境规则",
      values.rights_channel_disclosed ? "已披露权利行使渠道" : "未充分披露权利行使渠道",
      values.contact_channel ? `联系渠道：${values.contact_channel}` : "",
      values.review_focus.trim()
    ]
      .filter((item) => item.length > 0)
      .join("；");

    return {
      company_name: trimOr(values.publisher_entity || values.company_name, "待确认企业"),
      receiver_name: trimOr(values.receiver_name, "待确认接收方"),
      receiver_country: trimOr(values.receiver_country, "待确认国家"),
      transfer_purpose: trimOr(
        reviewContext || values.transfer_purpose,
        "文档合规审查与跨境条款核验"
      ),
      pii_count: Math.max(0, values.pii_count),
      spi_count: Math.max(0, values.spi_count),
      has_scc_draft: values.has_scc_draft || uploadedFiles.length > 0,
      uploaded_files: uploadedFiles,
      // NEW: Enhanced review context fields for backend pipeline
      document_type: values.document_type || "other",
      review_focus: values.review_focus?.trim() || "",
      scenario_context: {
        company_name: trimOr(values.publisher_entity || values.company_name, ""),
        document_title: values.document_title?.trim() || "",
        document_version: values.document_version?.trim() || "",
        publisher_entity: trimOr(values.publisher_entity, ""),
        receiver_name: trimOr(values.receiver_name, ""),
        receiver_country: trimOr(values.receiver_country, ""),
        transfer_purpose: values.transfer_purpose?.trim() || "",
        pii_count: Math.max(0, values.pii_count),
        spi_count: Math.max(0, values.spi_count),
        has_scc_draft: values.has_scc_draft || false,
        review_focus: values.review_focus?.trim() || "",
      },
      review_config: {
        review_depth: "standard",
        max_llm_clauses: 20,
        enable_cross_document_check: false,
      },
    };
  };

  const VALID_DOC_TYPES = ["privacy_policy", "scc_contract", "dpa", "other"];
  const buildDocumentReviewPayload = async (): Promise<unknown> => {
    const payload = await buildDocumentReviewPayloadFrom(documentReviewValues, documentReviewFiles, documentReviewDevFilePaths) as Record<string, unknown>;
    const docType = String(payload.document_type || "");
    if (!VALID_DOC_TYPES.includes(docType)) {
      console.warn(`[documentReview] unexpected document_type: "${docType}", defaulting to "other"`);
      payload.document_type = "other";
    }
    return payload;
  };

  const buildEuSccPayloadFrom = async (
    values: EuSccFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(hasText(values.exporter_name), "请填写数据出口方名称。");
    assertInput(hasText(values.importer_name), "请填写数据进口方名称。");
    assertInput(hasText(values.importer_country), "请填写进口方国家/地区。");
    assertInput(hasText(values.transfer_purpose), "请填写传输目的。");
    assertInput(hasText(values.data_categories), "请填写数据类别。");
    assertInput(hasText(values.tom_summary), "请填写技术与组织措施（TOM）摘要。");
    assertInput(hasText(values.rights_and_complaint), "请填写数据主体权利与投诉机制。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(files.length > 0 || presetFilePaths.length > 0, "请上传至少1份SCC文本或配套附件。");

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
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
      values.rights_and_complaint ? `权利救济：${values.rights_and_complaint}` : ""
    ]
      .filter((item) => item.length > 0)
      .join("；");

    return {
      company_name: values.exporter_name.trim(),
      receiver_name: values.importer_name.trim(),
      receiver_country: values.importer_country.trim(),
      transfer_purpose: purposeContext,
      pii_count: Math.max(0, values.pii_count),
      spi_count: Math.max(0, values.spi_count),
      has_scc_draft: values.has_scc_draft || uploadedFiles.length > 0,
      uploaded_files: uploadedFiles
    };
  };

  const buildEuSccPayload = async (): Promise<unknown> =>
    buildEuSccPayloadFrom(euSccValues, euSccFiles, euSccDevFilePaths);

  const buildBcrPayloadFrom = async (
    values: BcrFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(hasText(values.company_name), "请填写集团名称。");
    assertInput(hasText(values.group_structure), "请填写集团结构与申请主体信息。");
    assertInput(hasText(values.data_flow_scope), "请填写数据流与处理活动范围。");
    assertInput(hasText(values.binding_mechanism), "请填写内部约束机制。");
    assertInput(hasText(values.third_country_assessment), "请填写第三国法律评估机制。");
    assertInput(hasText(values.government_access_process), "请填写政府访问请求处理机制。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(files.length > 0 || presetFilePaths.length > 0, "请上传至少1份BCR主文本或配套申请材料。");

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
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
      `${values.binding_mechanism} ${values.lead_sa_rationale}`,
      values.data_flow_scope,
      values.third_party_beneficiary,
      values.liability_compensation,
      values.transparency_notice,
      values.training_audit,
      values.cooperation_with_sa,
      values.dp_safeguards,
      `${values.third_country_assessment} ${values.government_access_process}`,
      `${values.update_mechanism} ${values.definitions_quality}`
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
        recommendation: values.review_focus
          ? `${item.recommendation} 本轮重点：${values.review_focus}`
          : item.recommendation,
        evidence
      };
    });

    return {
      company_name: values.company_name.trim(),
      review_items,
      attachments,
      uploaded_files: uploadedFiles
    };
  };

  const buildBcrPayload = async (): Promise<unknown> =>
    buildBcrPayloadFrom(bcrValues, bcrFiles, bcrDevFilePaths);

  const buildDpiaPayloadFrom = async (
    values: DpiaFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(hasText(values.project_name), "请填写项目名称。");
    assertInput(hasText(values.processing_description), "请填写处理活动描述。");
    assertInput(hasText(values.purpose_and_necessity), "请填写目的与必要性说明。");
    assertInput(hasText(values.lawful_basis), "请填写合法性基础。");
    assertInput(hasText(values.risk_assessment), "请填写风险评估。");
    assertInput(hasText(values.mitigation_measures), "请填写缓解措施。");
    assertInput(hasText(values.residual_risk), "请填写剩余风险结论。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(files.length > 0 || presetFilePaths.length > 0, "请上传至少1份DPIA附件（流程图/制度/合同等）。");

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
    const attachments = uploadedFiles.map((path) => {
      const format = inferDpiaAttachmentFormat(path);
      assertInput(!!format, `DPIA附件仅支持 .docx/.pdf/.png/.jpg：${basenameFromPath(path)}`);
      return {
        file_role: values.attachment_role,
        file_name: basenameFromPath(path),
        file_format: format,
        storage_uri: path
      };
    });

    return {
      project_name: values.project_name.trim(),
      processing_description: [
        values.processing_description,
        values.project_goal ? `项目目标：${values.project_goal}` : "",
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
        values.novel_technology ? `新技术：${values.novel_technology}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      purpose_and_necessity: [
        values.purpose_and_necessity,
        values.need_reason ? `触发理由：${values.need_reason}` : "",
        values.expectation_control ? `合理预期：${values.expectation_control}` : "",
        values.function_creep_control ? `防功能漂移：${values.function_creep_control}` : "",
        values.minimization_quality ? `最小化与质量：${values.minimization_quality}` : "",
        values.notice_plan ? `告知安排：${values.notice_plan}` : "",
        values.rights_support ? `权利支持：${values.rights_support}` : "",
        values.processor_management ? `处理者管理：${values.processor_management}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      lawful_basis: values.lawful_basis.trim(),
      risk_assessment: [
        values.risk_assessment,
        values.prior_concerns ? `历史风险：${values.prior_concerns}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      mitigation_measures: [
        values.mitigation_measures,
        values.signoff_owner ? `签署责任人：${values.signoff_owner}` : "",
        values.controller_name ? `控制者：${values.controller_name}` : "",
        values.dpo_role ? `DPO：${values.dpo_role}` : "",
        values.contact_channel ? `联系渠道：${values.contact_channel}` : "",
        values.dpo_advice ? `DPO意见：${values.dpo_advice}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      residual_risk: [
        values.residual_risk,
        values.review_schedule ? `复审安排：${values.review_schedule}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      attachments
    };
  };

  const buildDpiaPayload = async (): Promise<unknown> =>
    buildDpiaPayloadFrom(dpiaValues, dpiaFiles, dpiaDevFilePaths);

  const buildTiaPayloadFrom = async (
    values: TiaFormValues,
    files: File[],
    devPresetPaths: string[]
  ): Promise<unknown> => {
    assertInput(hasText(values.data_exporter_name), "请填写数据出口方名称。");
    assertInput(hasText(values.data_importer_name), "请填写数据进口方名称。");
    assertInput(hasText(values.importer_country_region), "请填写进口方国家/地区。");
    assertInput(hasText(values.transfer_purpose), "请填写传输目的。");
    assertInput(hasText(values.law_findings), "请填写第三国法律评估发现。");
    assertInput(hasText(values.supplementary_technical), "请填写技术性补充措施。");
    assertInput(hasText(values.post_effectiveness), "请填写补充措施后的有效性判断。");
    assertInput(hasText(values.key_actions), "请填写关键行动项。");
    const presetFilePaths = DEV_ACCEL_ENABLED ? devPresetPaths.filter((item) => item.trim().length > 0) : [];
    assertInput(files.length > 0 || presetFilePaths.length > 0, "请上传至少1份TIA附件。");

    const uploadedFiles = presetFilePaths.length > 0 ? presetFilePaths : await uploadFiles(files);
    const attachments = uploadedFiles.map((path) => {
      const format = inferDocxPdfFormat(path);
      assertInput(!!format, `TIA附件仅支持 .docx 或 .pdf：${basenameFromPath(path)}`);
      return {
        file_role: values.attachment_role,
        file_name: basenameFromPath(path),
        file_format: format,
        storage_uri: path
      };
    });

    return {
      transfer_tool: values.transfer_tool,
      data_exporter_profile: [
        values.data_exporter_name,
        `传输目的：${values.transfer_purpose}`,
        values.data_categories ? `数据类别：${values.data_categories}` : "",
        values.data_subject_categories ? `数据主体：${values.data_subject_categories}` : "",
        `频率：${values.transfer_frequency}`
      ].filter((item) => item.trim().length > 0).join("；"),
      data_importer_profile: [
        values.data_importer_name,
        `国家/地区：${values.importer_country_region}`,
        values.sensitive_data_description ? `敏感数据：${values.sensitive_data_description}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      third_country_assessment: [
        values.law_assessed ? "已完成法律评估" : "法律评估待完成",
        values.law_findings,
        values.pre_effectiveness ? `补充措施前判断：${values.pre_effectiveness}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      supplementary_measures: [
        `技术措施：${values.supplementary_technical}`,
        values.supplementary_contractual ? `合同措施：${values.supplementary_contractual}` : "",
        values.supplementary_organizational ? `组织措施：${values.supplementary_organizational}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      final_conclusion: [
        values.post_effectiveness,
        `关键行动：${values.key_actions}`,
        values.dpo_opinion ? `DPO意见：${values.dpo_opinion}` : "",
        values.review_date ? `复审日期：${values.review_date}` : ""
      ].filter((item) => item.trim().length > 0).join("；"),
      attachments
    };
  };

  const buildTiaPayload = async (): Promise<unknown> =>
    buildTiaPayloadFrom(tiaValues, tiaFiles, tiaDevFilePaths);

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

  const buildDiagnosisPayloadFrom = (values: DiagnosisFormValues): unknown => {
    const asText = (key: string): string => {
      const value = values[key];
      if (typeof value === "string") return value;
      if (typeof value === "number") return String(value);
      return "";
    };
    const asArray = (key: string): string[] => {
      const value = values[key];
      if (Array.isArray(value)) return value.map((item) => String(item));
      if (typeof value === "string" && value.trim().length > 0) {
        return value.split(/[,，\n]/).map((item) => item.trim()).filter((item) => item.length > 0);
      }
      return [];
    };
    const hasSensitivePi = asArray("m3_personal_info_types").some((item) =>
      ["身份证", "人脸", "指纹", "声纹", "健康", "金融", "未成年人", "精准位置"].some((key) => item.includes(key))
    );

    const volume = asText("m3_data_volume_range");
    const estimatedPiiCount =
      volume === "1000万条以上" ? 10000000 :
      volume === "100-1000万条" ? 2000000 :
      volume === "10-100万条" ? 300000 :
      volume === "10万条以下" ? 50000 : 0;
    const estimatedSpiCount =
      !hasSensitivePi ? 0 :
      volume === "1000万条以上" ? 20000 :
      volume === "100-1000万条" ? 12000 :
      volume === "10-100万条" ? 6000 : 1000;

    const personalInfoFlag = asText("m3_processes_personal_info");
    const importantDataFlag = asText("m3_processes_important_data");
    const noPersonalAndNoImportant = personalInfoFlag === "no" && importantDataFlag === "no";

    const receiverType = asText("m4_share_to_third_party") === "yes" ? "third_party" : "intra_group";
    const companyNameRaw = asText("company_name").trim();
    const companyName = companyNameRaw.length >= 2 ? companyNameRaw : "未命名企业";

    return {
      company_name: companyName,
      answers: {
        q1_is_ciio: "unknown",
        q2_has_important_data: importantDataFlag === "yes" ? "yes" : importantDataFlag === "no" ? "no" : "unknown",
        q3_pii_count: personalInfoFlag === "yes" ? estimatedPiiCount : 0,
        q4_spi_count: personalInfoFlag === "yes" ? estimatedSpiCount : 0,
        q5_no_personal_info: noPersonalAndNoImportant ? "yes" : "no",
        q6_scenario: "other",
        q7_receiver_type: receiverType,
        q8_purpose: asText("m2_core_needs_other"),

        m1_enterprise_name: companyName,
        m1_industry: asText("m1_industry"),
        m1_business_channels: asArray("m1_business_channels"),
        m1_service_targets: asText("m1_service_targets"),
        m1_company_size: asText("m1_company_size"),

        m2_core_needs: asArray("m2_core_needs"),
        m2_had_compliance_issue: asText("m2_had_compliance_issue"),
        m2_issue_description: asText("m2_issue_description"),
        m2_deadline: asText("m2_deadline"),

        m3_processes_personal_info: personalInfoFlag,
        m3_personal_info_types: asArray("m3_personal_info_types"),
        m3_sensitive_info_types: asArray("m3_personal_info_types").filter((item) =>
          ["身份证", "人脸", "指纹", "声纹", "健康", "金融", "未成年人", "精准位置"].some((key) => item.includes(key))
        ),
        m3_processes_important_data: importantDataFlag,
        m3_important_data_types: asArray("m3_important_data_types"),
        m3_data_sources: asArray("m3_data_sources"),
        m3_processing_activities: asArray("m3_processing_activities"),
        m3_data_volume_range: volume,
        m3_processes_enterprise_public_data: asText("m3_processes_enterprise_public_data"),
        m3_enterprise_public_data_desc: asText("m3_enterprise_public_data_desc"),
        m3_retention_period: asText("m3_retention_period"),
        m3_retention_desc: asText("m3_retention_desc"),

        m4_share_to_third_party: asText("m4_share_to_third_party"),
        m4_third_party_types: asText("m4_third_party_types"),
        m4_cross_border_transfer: asText("m4_cross_border_transfer"),
        m4_cross_border_regions: asText("m4_cross_border_regions"),
        m4_commercialization: asText("m4_commercialization"),
        m4_commercialization_mode: asText("m4_commercialization_mode"),
        m4_entrusted_processing: asText("m4_entrusted_processing"),
        m4_entrusted_party_type: asText("m4_entrusted_party_type"),
        m4_authorization_method: asText("m4_authorization_method"),

        m5_systems: asArray("m5_systems"),
        m5_security_measures: asArray("m5_security_measures"),
        m5_compliance_docs: asArray("m5_compliance_docs"),
        m5_penalty_or_complaint: asText("m5_penalty_or_complaint"),
        m5_penalty_time: asText("m5_penalty_time"),
        m5_penalty_reason: asText("m5_penalty_reason"),
        m5_penalty_result: asText("m5_penalty_result"),

        m1_industry_other: asText("m1_industry_other"),
        m1_business_channels_other: asText("m1_business_channels_other"),
        m2_core_needs_other: asText("m2_core_needs_other"),
        m2_deadline_detail: asText("m2_deadline_detail"),
        m3_important_data_types_other: asText("m3_important_data_types_other"),
        m3_data_sources_other: asText("m3_data_sources_other"),
        m5_systems_other: asText("m5_systems_other"),
        m5_security_measures_other: asText("m5_security_measures_other"),
        m5_compliance_docs_other: asText("m5_compliance_docs_other")
      }
    };
  };

  const buildDiagnosisPayload = (): unknown => buildDiagnosisPayloadFrom(diagnosisValues);

  const runWithPayload = async (requestPayload: unknown) => {
    setLoading(true);
    setError(null);
    setAsyncRunProgress(null);
    try {
      const preferredRunMode: RunMode = hasAsync(definition) ? "async" : "sync";
      const timeoutMs = moduleKey === "review" ? 900000 : 180000;
      const result = await runModule(
        definition,
        requestPayload,
        preferredRunMode,
        timeoutMs,
        (progress) => setAsyncRunProgress(progress),
      );
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
      onRunDone({ module: moduleKey, runMode: hasAsync(definition) ? "async" : "sync", request: requestPayload, success: false, error: message });
    } finally {
      setLoading(false);
    }
  };

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
        runMode: "sync",
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

    await runWithPayload(requestPayload);
  };

  const runAssessmentDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isAssessmentModule || loading) return;
    const preset = getAssessmentDevPreset();
    const nextValues: AssessmentFormValues = {
      ...assessmentValues,
      ...(preset.formDefaults as Partial<AssessmentFormValues>)
    };
    setAssessmentValues(nextValues);
    setAssessmentFiles([]);
    setAssessmentDevFilePaths(preset.backendFilePaths);
    setAssessmentStepIndex(ASSESSMENT_STEPS.length - 1);
    const payload = await buildAssessmentPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const runPipiaDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isPipiaModule || loading) return;
    const preset = getModuleDevPreset("pipia");
    const nextValues: PipiaFormValues = { ...pipiaValues, ...(preset.formDefaults as Partial<PipiaFormValues>) };
    setPipiaValues(nextValues);
    setPipiaFiles([]);
    setPipiaDevFilePaths(preset.backendFilePaths);
    setPipiaStepIndex(PIPIA_STEPS.length - 1);
    const payload = await buildPipiaPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const runEuSccDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isEuSccTask || loading) return;
    const preset = getModuleDevPreset("scc");
    const nextValues: EuSccFormValues = { ...euSccValues, ...(preset.formDefaults as Partial<EuSccFormValues>) };
    setEuSccValues(nextValues);
    setEuSccFiles([]);
    setEuSccDevFilePaths(preset.backendFilePaths);
    setEuSccStepIndex(EU_SCC_STEPS.length - 1);
    const payload = await buildEuSccPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const runBcrDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isBcrModule || loading) return;
    const preset = getModuleDevPreset("bcr");
    const nextValues: BcrFormValues = { ...bcrValues, ...(preset.formDefaults as Partial<BcrFormValues>) };
    setBcrValues(nextValues);
    setBcrFiles([]);
    setBcrDevFilePaths(preset.backendFilePaths);
    setBcrStepIndex(BCR_STEPS.length - 1);
    const payload = await buildBcrPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const runDpiaDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isDpiaModule || loading) return;
    const preset = getModuleDevPreset("dpia");
    const nextValues: DpiaFormValues = { ...dpiaValues, ...(preset.formDefaults as Partial<DpiaFormValues>) };
    setDpiaValues(nextValues);
    setDpiaFiles([]);
    setDpiaDevFilePaths(preset.backendFilePaths);
    setDpiaStepIndex(DPIA_STEPS.length - 1);
    const payload = await buildDpiaPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const runTiaDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isTiaModule || loading) return;
    const preset = getModuleDevPreset("tia");
    const nextValues: TiaFormValues = { ...tiaValues, ...(preset.formDefaults as Partial<TiaFormValues>) };
    setTiaValues(nextValues);
    setTiaFiles([]);
    setTiaDevFilePaths(preset.backendFilePaths);
    setTiaStepIndex(TIA_STEPS.length - 1);
    const payload = await buildTiaPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const runDiagnosisDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isDiagnosisModule || loading) return;
    const preset = getModuleDevPreset("diagnosis");
    const nextValues: DiagnosisFormValues = {
      ...diagnosisValues,
      ...(preset.formDefaults as Partial<DiagnosisFormValues>)
    };
    setDiagnosisValues(nextValues);
    setDiagnosisStepIndex(DIAGNOSIS_STEPS.length - 1);
    const payload = buildDiagnosisPayloadFrom(nextValues);
    await runWithPayload(payload);
  };

  const runDocumentReviewDevPreset = async () => {
    if (!DEV_ACCEL_ENABLED || !isDocumentReviewTask || loading) return;
    const preset = getModuleDevPreset("document_review");
    const nextValues: DocumentReviewFormValues = {
      ...documentReviewValues,
      ...(preset.formDefaults as Partial<DocumentReviewFormValues>)
    };
    setDocumentReviewValues(nextValues);
    setDocumentReviewFiles([]);
    setDocumentReviewDevFilePaths(preset.backendFilePaths);
    const payload = await buildDocumentReviewPayloadFrom(nextValues, [], preset.backendFilePaths);
    await runWithPayload(payload);
  };

  const currentAssessmentStep = ASSESSMENT_STEPS[assessmentStepIndex];
  const assessmentProgress = Math.round(((assessmentStepIndex + 1) / ASSESSMENT_STEPS.length) * 100);
  const currentDiagnosisStep = DIAGNOSIS_STEPS[diagnosisStepIndex];
  const diagnosisProgress = Math.round(((diagnosisStepIndex + 1) / DIAGNOSIS_STEPS.length) * 100);
  const visibleDiagnosisFields = useMemo(() => {
    const seen = new Set<string>();
    const fields: DiagnosisFieldConfig[] = [];
    for (const field of currentDiagnosisStep.fields) {
      const visible = field.visibleWhen ? field.visibleWhen(diagnosisValues) : true;
      if (!visible) continue;
      if (seen.has(field.name)) continue;
      seen.add(field.name);
      fields.push(field);
    }
    return fields;
  }, [currentDiagnosisStep.fields, diagnosisValues]);

  const diagnosisFieldGroups = useMemo(() => {
    const order: string[] = [];
    const map = new Map<string, DiagnosisFieldConfig[]>();

    for (const field of visibleDiagnosisFields) {
      const groupName = field.group ?? "";
      if (!map.has(groupName)) {
        map.set(groupName, []);
        order.push(groupName);
      }
      map.get(groupName)?.push(field);
    }

    return order.map((groupName) => ({ groupName, fields: map.get(groupName) ?? [] }));
  }, [visibleDiagnosisFields]);
  const currentPipiaStep = PIPIA_STEPS[pipiaStepIndex];
  const pipiaProgress = Math.round(((pipiaStepIndex + 1) / PIPIA_STEPS.length) * 100);
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

  const selectedDocumentReviewFile = documentReviewFiles[documentReviewSelectedFileIndex] ?? null;
  const selectedDocumentReviewFileExt = selectedDocumentReviewFile
    ? getDocumentReviewFileExt(selectedDocumentReviewFile.name)
    : "";
  const selectedDocumentReviewFileKey = selectedDocumentReviewFile
    ? getDocumentReviewFileKey(selectedDocumentReviewFile)
    : "";
  const selectedDocumentReviewExtractState = selectedDocumentReviewFileKey
    ? documentReviewExtractStates[selectedDocumentReviewFileKey]
    : undefined;
  const documentReviewSourceCount = documentReviewFiles.length + documentReviewDevFilePaths.length;
  const documentReviewPreviewableCount = documentReviewFiles.filter((file) =>
    canInlinePreviewDocumentReviewExt(getDocumentReviewFileExt(file.name))
  ).length;
  const documentReviewParsedCount = documentReviewFiles.filter((file) =>
    documentReviewParsedKeysRef.current.has(getDocumentReviewFileKey(file))
  ).length;
  const selectedDocumentReviewCanPreview = canInlinePreviewDocumentReviewExt(selectedDocumentReviewFileExt);
  const selectedDocumentReviewTypeLabel = getDocumentReviewTypeLabel(selectedDocumentReviewFileExt);
  const selectedDocumentReviewSummaryDate = selectedDocumentReviewFile
    ? formatDocumentReviewFileDate(selectedDocumentReviewFile.lastModified, lang)
    : "";
  const selectedDocumentReviewExtractMeta = getDocumentReviewExtractStatusMeta(selectedDocumentReviewExtractState);

  useEffect(() => {
    if (documentReviewFiles.length === 0) {
      setDocumentReviewSelectedFileIndex(0);
      return;
    }
    setDocumentReviewSelectedFileIndex((prev) => Math.min(prev, documentReviewFiles.length - 1));
  }, [documentReviewFiles]);

  useEffect(() => {
    if (!selectedDocumentReviewFile) {
      setDocumentReviewPreviewUrl((current) => {
        if (current) URL.revokeObjectURL(current);
        return null;
      });
      setDocumentReviewTextPreview("");
      return;
    }

    const objectUrl = URL.createObjectURL(selectedDocumentReviewFile);
    setDocumentReviewPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return objectUrl;
    });

    if (isDocumentReviewTextPreviewExt(selectedDocumentReviewFileExt)) {
      selectedDocumentReviewFile
        .text()
        .then((content) => setDocumentReviewTextPreview(content.slice(0, 8000)))
        .catch(() => setDocumentReviewTextPreview(""));
    } else {
      setDocumentReviewTextPreview("");
    }

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [selectedDocumentReviewFile, selectedDocumentReviewFileExt]);

  useEffect(() => {
    if (!selectedDocumentReviewFile) return;
    const fileKey = getDocumentReviewFileKey(selectedDocumentReviewFile);
    if (documentReviewParsedKeysRef.current.has(fileKey)) return;

    let cancelled = false;
    setDocumentReviewExtractStates((prev) => ({
      ...prev,
      [fileKey]: {
        status: "loading",
        note: "正在解析文档并自动回填字段..."
      }
    }));
    buildAutoExtractResult(selectedDocumentReviewFile)
      .then((extracted) => {
        if (cancelled) return;
        setDocumentReviewValues((prev) => {
          const nextValues = {
            ...prev,
            document_title: extracted.documentTitle || prev.document_title,
            document_type: extracted.documentType || prev.document_type,
            review_focus: extracted.reviewFocus || prev.review_focus,
            transfer_purpose: extracted.transferPurpose || prev.transfer_purpose,
            sensitive_pi_disclosed: extracted.sensitivePiDisclosed,
            rights_channel_disclosed: extracted.rightsChannelDisclosed,
            crossborder_rule_disclosed: extracted.crossborderRuleDisclosed,
            contact_channel: extracted.contactChannel || prev.contact_channel,
          };
          setDocumentReviewFileFormValues((saved) => ({ ...saved, [fileKey]: nextValues }));
          return nextValues;
        });
        setDocumentReviewExtractStates((prev) => ({
          ...prev,
          [fileKey]: {
            status: "done",
            note: extracted.note
          }
        }));
        documentReviewParsedKeysRef.current.add(fileKey);
      })
      .catch(() => {
        if (cancelled) return;
        setDocumentReviewExtractStates((prev) => ({
          ...prev,
          [fileKey]: {
            status: "error",
            note: "自动提取失败，请手动确认与填写。"
          }
        }));
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDocumentReviewFile]);

  return (
    <section className="run-panel" data-guide="stage-run">
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
        <section className="doc-review-workbench">
          <aside className="doc-review-input-pane">
            <header className="doc-review-panel-head">
              <div className="doc-review-panel-copy">
                <span className="doc-review-kicker">Input Workspace</span>
                <div className="schema-wizard-head">
                  <div className="runner-title">文档输入管理</div>
                  <span className="doc-review-count-badge">{documentReviewSourceCount} 份材料</span>
                </div>
                <p>集中管理上传材料、预置文件与解析进度。点击文件后，右侧立即切换到对应预览与确认状态。</p>
              </div>
              <div className="doc-review-panel-stats">
                <article>
                  <strong>{documentReviewFiles.length}</strong>
                  <span>已上传</span>
                </article>
                <article>
                  <strong>{documentReviewPreviewableCount}</strong>
                  <span>可预览</span>
                </article>
                <article>
                  <strong>{documentReviewParsedCount}</strong>
                  <span>已回填</span>
                </article>
              </div>
            </header>

            <label className="doc-review-upload-drop">
              <div className="doc-review-upload-copy">
                <span>上传待审查文档</span>
                <p>建议上传隐私政策、用户协议、标准合同、DPA 或辅助证明材料，支持批量导入并自动去重。</p>
              </div>
              <div className="doc-review-upload-tags">
                <span>PDF</span>
                <span>DOCX</span>
                <span>Markdown</span>
                <span>CSV / JSON</span>
                <span>图片</span>
              </div>
              <input
                type="file"
                multiple
                onChange={(event) => onSelectDocumentReviewFiles(event.target.files)}
              />
            </label>

            <section className="doc-review-source-section">
              <div className="doc-review-source-head">
                <strong>上传队列</strong>
                <small>点击任一文件，可切换预览舞台与自动回填状态。</small>
              </div>
              {documentReviewFiles.length === 0 ? (
                <article className="doc-review-queue-empty">
                  <strong>上传后这里会形成统一文件队列</strong>
                  <p>每个文件会显示格式、体积、可预览性与解析状态，方便你逐份核对并进入专项审查。</p>
                </article>
              ) : (
                <div className="doc-review-file-list">
                  {documentReviewFiles.map((file, index) => {
                    const fileKey = getDocumentReviewFileKey(file);
                    const fileExt = getDocumentReviewFileExt(file.name);
                    const fileStatus = getDocumentReviewExtractStatusMeta(documentReviewExtractStates[fileKey]);
                    const canPreview = canInlinePreviewDocumentReviewExt(fileExt);
                    return (
                      <button
                        type="button"
                        key={fileKey}
                        className={`doc-review-file-item ${index === documentReviewSelectedFileIndex ? "active" : ""}`}
                        onClick={() => {
                          setDocumentReviewSelectedFileIndex(index);
                          syncDocumentReviewValuesForFile(file);
                        }}
                      >
                        <div className="doc-review-file-item-main">
                          <div className="doc-review-file-item-title-row">
                            <strong>{file.name}</strong>
                            {index === documentReviewSelectedFileIndex ? (
                              <span className="doc-review-inline-flag">当前查看</span>
                            ) : null}
                          </div>
                          <div className="doc-review-file-item-meta">
                            <span className="doc-review-meta-pill">{getDocumentReviewTypeLabel(fileExt)}</span>
                            <span className="doc-review-meta-pill">{formatDocumentReviewFileSize(file.size)}</span>
                            <span className={`doc-review-meta-pill ${canPreview ? "is-success" : "is-neutral"}`}>
                              {canPreview ? "可预览" : "不可内嵌预览"}
                            </span>
                          </div>
                        </div>
                        <div className="doc-review-file-item-side">
                          <span className={`doc-review-status-pill is-${fileStatus.tone}`}>{fileStatus.label}</span>
                          <small>{formatDocumentReviewFileDate(file.lastModified, lang)}</small>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </section>

            {DEV_ACCEL_ENABLED && documentReviewDevFilePaths.length > 0 ? (
              <section className="doc-review-source-section doc-review-source-section-muted">
                <div className="doc-review-source-head">
                  <strong>开发预置材料</strong>
                  <small>用于快速体验真实审查链路，不占用本地上传队列。</small>
                </div>
                <div className="doc-review-preset-list">
                  {documentReviewDevFilePaths.map((path) => {
                    const fileName = path.split("/").pop() || path;
                    return (
                      <article key={`dev-document-review-file-${path}`} className="doc-review-preset-item">
                        <div>
                          <strong>{fileName}</strong>
                          <div className="doc-review-file-item-meta">
                            <span className="doc-review-meta-pill">{getDocumentReviewTypeLabel(getDocumentReviewFileExt(fileName))}</span>
                            <span className="doc-review-meta-pill is-neutral">预置导入</span>
                          </div>
                        </div>
                        <span className="doc-review-status-pill is-neutral">Dev preset</span>
                      </article>
                    );
                  })}
                </div>
              </section>
            ) : null}
          </aside>

          <div className="doc-review-main-pane">
            {!selectedDocumentReviewFile ? (
              <article className="doc-review-empty-state">
                <div className="doc-review-empty-state-hero">
                  <span className="doc-review-kicker">Preview Workspace</span>
                  <h3>右侧会在选中文件后切换为完整的预览与状态面板</h3>
                  <p>PDF、图片、文本可直接预览；DOC / DOCX 等格式也不会只停留在占位态，而会进入更明确的解析说明与下一步引导。</p>
                </div>
                <div className="doc-review-empty-state-grid">
                  <article>
                    <strong>1. 上传或使用预置材料</strong>
                    <p>将审查对象纳入统一文件队列，建立本次工作台的输入集合。</p>
                  </article>
                  <article>
                    <strong>2. 切换预览对象</strong>
                    <p>点击任一文件，右侧立即显示预览、解析状态、格式能力与人工确认入口。</p>
                  </article>
                  <article>
                    <strong>3. 确认字段并执行审查</strong>
                    <p>核对自动回填结果后直接运行专项审查，输出条款级建议和审查报告。</p>
                  </article>
                </div>
                <div className="doc-review-empty-state-footer">
                  {documentReviewSourceCount > 0
                    ? `当前已纳入 ${documentReviewSourceCount} 份材料，请从左侧选择一个文件开始。`
                    : "当前还没有材料，先从左侧上传文档即可进入工作状态。"}
                </div>
              </article>
            ) : (
              <article className="doc-review-preview-card">
                <header className="doc-review-preview-head">
                  <div className="doc-review-preview-title-block">
                    <span className="doc-review-kicker">Preview Stage</span>
                    <strong>{selectedDocumentReviewFile.name}</strong>
                    <p>
                      {selectedDocumentReviewCanPreview
                        ? "当前格式支持内嵌预览，你可以边看正文边核对自动回填字段。"
                        : "当前格式暂不支持内嵌预览，但仍可参与自动解析与专项审查，不会中断流程。"}
                    </p>
                  </div>
                  <div className="doc-review-preview-meta">
                    <span className="doc-review-meta-pill">{selectedDocumentReviewTypeLabel}</span>
                    <span className="doc-review-meta-pill">{formatDocumentReviewFileSize(selectedDocumentReviewFile.size)}</span>
                    <span className="doc-review-meta-pill">{selectedDocumentReviewSummaryDate}</span>
                    <span className={`doc-review-status-pill is-${selectedDocumentReviewCanPreview ? "success" : "neutral"}`}>
                      {selectedDocumentReviewCanPreview ? "可预览" : "审查模式"}
                    </span>
                    <span className={`doc-review-status-pill is-${selectedDocumentReviewExtractMeta.tone}`}>
                      {selectedDocumentReviewExtractMeta.label}
                    </span>
                  </div>
                </header>
                <div className={`doc-review-preview-body ${selectedDocumentReviewCanPreview ? "" : "is-fallback"}`}>
                  {documentReviewPreviewUrl && selectedDocumentReviewFileExt === "pdf" ? (
                    <div className="doc-review-pdf-surface">
                      <iframe title={selectedDocumentReviewFile.name} src={documentReviewPreviewUrl} />
                    </div>
                  ) : documentReviewPreviewUrl && isDocumentReviewImagePreviewExt(selectedDocumentReviewFileExt) ? (
                    <div className="doc-review-image-surface">
                      <img src={documentReviewPreviewUrl} alt={selectedDocumentReviewFile.name} />
                    </div>
                  ) : isDocumentReviewTextPreviewExt(selectedDocumentReviewFileExt) ? (
                    <div className="doc-review-text-surface">
                      <pre>{documentReviewTextPreview || "正在读取文本..."}</pre>
                    </div>
                  ) : (
                    <div className="doc-review-preview-fallback">
                      <div className="doc-review-preview-fallback-emblem">{selectedDocumentReviewTypeLabel}</div>
                      <div className="doc-review-preview-fallback-copy">
                        <strong>当前格式暂不支持内嵌预览</strong>
                        <p>这不是失败态。文件仍会参与自动解析、字段回填与专项审查，你可以继续完成整套工作流。</p>
                      </div>
                      <div className="doc-review-preview-fallback-actions">
                        <span className={`doc-review-status-pill is-${selectedDocumentReviewExtractMeta.tone}`}>
                          {selectedDocumentReviewExtractMeta.label}
                        </span>
                        <span className="doc-review-meta-pill">{selectedDocumentReviewSummaryDate}</span>
                      </div>
                      <div className="doc-review-preview-next">
                        <span>建议下一步</span>
                        <ul>
                          <li>先核对下方结构化字段与自动回填结果</li>
                          <li>如需直观预览正文，可补充 PDF、图片或文本版本</li>
                          <li>确认无误后，直接执行专项审查生成报告</li>
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              </article>
            )}

            <article className="doc-review-confirm-card">
              <header className="doc-review-confirm-head">
                <div>
                  <span className="doc-review-kicker">Review Controls</span>
                  <h4>结构化确认与审查准备</h4>
                  <p>系统会基于当前文档自动回填关键字段；你只需确认或修正，再执行专项审查生成报告。</p>
                </div>
                <div className="doc-review-confirm-head-side">
                  <span className={`doc-review-status-pill is-${selectedDocumentReviewFile ? selectedDocumentReviewExtractMeta.tone : "neutral"}`}>
                    {selectedDocumentReviewFile ? selectedDocumentReviewExtractMeta.label : "等待选择文件"}
                  </span>
                </div>
              </header>
              <div className="doc-review-confirm-summary">
                <article>
                  <span>当前文档</span>
                  <strong>{selectedDocumentReviewFile ? selectedDocumentReviewFile.name : "尚未选择"}</strong>
                  <small>
                    {selectedDocumentReviewFile
                      ? `${selectedDocumentReviewTypeLabel} · ${getDocumentReviewDocTypeLabel(documentReviewValues.document_type)}`
                      : "先从左侧文件队列选择一个对象"}
                  </small>
                </article>
                <article>
                  <span>回填状态</span>
                  <strong>{selectedDocumentReviewFile ? selectedDocumentReviewExtractMeta.label : "等待解析"}</strong>
                  <small>{selectedDocumentReviewFile ? "系统会自动尝试提取标题、类型与审查重点。" : "选择文件后自动启动解析。"}</small>
                </article>
                <article>
                  <span>执行前动作</span>
                  <strong>{selectedDocumentReviewFile ? "确认字段后执行专项审查" : "先完成文件选择"}</strong>
                  <small>预置确认分组：{DOCUMENT_REVIEW_STEPS.length} 组。</small>
                </article>
              </div>
              <p className={`doc-review-autofill-note is-${selectedDocumentReviewFile ? selectedDocumentReviewExtractMeta.tone : "neutral"}`}>
                {selectedDocumentReviewFile
                  ? selectedDocumentReviewExtractState?.note || "已选中文件，准备进入自动提取与人工确认。"
                  : "选择文件后，这里会显示自动提取结果、风险提醒和下一步建议。"}
              </p>
              <div className="schema-field-grid">
                <label className="field-wrap">
                  <span>{localizeFieldLabel(lang, "document_title", "文档名称")}</span>
                  <input
                    value={String(documentReviewValues.document_title)}
                    onChange={(event) => updateDocumentReviewValue("document_title", event.target.value)}
                  />
                </label>
                <label className="field-wrap">
                  <span>{localizeFieldLabel(lang, "document_type", "文档类型")}</span>
                  <select
                    value={String(documentReviewValues.document_type)}
                    onChange={(event) =>
                      updateDocumentReviewValue("document_type", event.target.value as DocumentReviewFormValues["document_type"])
                    }
                  >
                    <option value="privacy_policy">隐私政策</option>
                    <option value="scc_contract">标准合同</option>
                    <option value="dpa">数据处理协议</option>
                    <option value="other">其他</option>
                  </select>
                </label>
                <label className="field-wrap schema-field-wide">
                  <span>{localizeFieldLabel(lang, "review_focus", "本次重点关注条款")}</span>
                  <textarea
                    className="runner-textarea schema-textarea"
                    value={String(documentReviewValues.review_focus)}
                    onChange={(event) => updateDocumentReviewValue("review_focus", event.target.value)}
                  />
                </label>
              </div>
              <div className="schema-actions-row">
                {DEV_ACCEL_ENABLED ? (
                  <button
                    className="pill-btn"
                    type="button"
                    onClick={runDocumentReviewDevPreset}
                    disabled={loading}
                    title="开发期一键注入文档审查预设并运行真实后端流程"
                  >
                    一键体验文档审查
                  </button>
                ) : null}
                <button className="pill-btn-primary" onClick={execute} disabled={loading}>
                  {loading ? t("runningNow") : "执行专项审查并生成报告"}
                </button>
              </div>
              {loading && asyncRunProgress ? (
                <p className="doc-review-autofill-note is-loading">
                  {REVIEW_ASYNC_STATE_LABEL[asyncRunProgress.state] ?? asyncRunProgress.state}
                  {typeof asyncRunProgress.progress === "number" ? `（${asyncRunProgress.progress}%）` : ""}
                </p>
              ) : null}
            </article>
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
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === euSccStepIndex ? "active" : ""}`}
                onClick={() => setEuSccStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentEuSccStep.title)}</div>
          <div className="schema-field-grid">
            {currentEuSccStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <select
                      value={String(euSccValues[field.name])}
                      onChange={(event) => updateEuSccValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
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
                  <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                </label>
              );
            })}
          </div>

          {euSccStepIndex === EU_SCC_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">SCC文本与配套材料上传</div>
              <input type="file" multiple onChange={(event) => setEuSccFiles(Array.from(event.target.files ?? []))} />
              <div className="schema-upload-list">
                {DEV_ACCEL_ENABLED && euSccDevFilePaths.length > 0 ? (
                  <>
                    {euSccDevFilePaths.map((path) => (
                      <article key={`dev-scc-file-${path}`} className="schema-upload-item">
                        <strong>{path.split("/").pop() || path}</strong>
                        <small>Dev preset</small>
                      </article>
                    ))}
                  </>
                ) : null}
                {euSccFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {euSccFiles.length === 0 && (!DEV_ACCEL_ENABLED || euSccDevFilePaths.length === 0) ? (
                  <p className="resource-empty">请上传至少1份SCC文本或附件后再提交。</p>
                ) : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runEuSccDevPreset}
                disabled={loading}
                title="开发期一键注入SCC预设并运行真实后端流程"
              >
                一键体验SCC
              </button>
            ) : null}
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
        <section className="schema-wizard schema-wizard--diagnosis">
          <div ref={diagnosisStepTopRef} />
          <div className="schema-wizard-head">
            <div className="runner-title">业务数据合规需求诊断</div>
            <span>{diagnosisProgress}%</span>
          </div>
          <div className="schema-stepper">
            {DIAGNOSIS_STEPS.map((step, index) => (
              <button
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === diagnosisStepIndex ? "active" : ""}`}
                onClick={() => setDiagnosisStepIndex(index)}
                type="button"
              >
                {index + 1} {DIAGNOSIS_STEP_SHORT_TITLES[index] ?? localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentDiagnosisStep.title)}</div>
          <div className="diagnosis-sections" key={`diagnosis-step-${diagnosisStepIndex}`}>
            {diagnosisFieldGroups.map(({ groupName, fields }) => (
              <section key={`diagnosis-group-${diagnosisStepIndex}-${groupName}`} className="diagnosis-section">
                {groupName ? <h4 className="diagnosis-section-title">{groupName}</h4> : null}
                <div className="schema-field-grid diagnosis-field-grid">
                  {fields.map((field) => {
              const selectedSingle = typeof diagnosisValues[field.name] === "string" ? String(diagnosisValues[field.name]) : "";
              const selectedMulti = Array.isArray(diagnosisValues[field.name])
                ? (diagnosisValues[field.name] as unknown[]).map((item) => String(item))
                : [];

              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <input
                      value={typeof diagnosisValues[field.name] === "string" ? String(diagnosisValues[field.name]) : ""}
                      onChange={(event) => updateDiagnosisValue(field.name, event.target.value)}
                    />
                  </label>
                );
              }

              if (field.type === "textarea") {
                return (
                  <label key={String(field.name)} className="field-wrap schema-field-wide">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <textarea
                      className="runner-textarea schema-textarea"
                      value={typeof diagnosisValues[field.name] === "string" ? String(diagnosisValues[field.name]) : ""}
                      onChange={(event) => updateDiagnosisValue(field.name, event.target.value)}
                    />
                  </label>
                );
              }

              if (field.type === "single") {
                return (
                  <label key={String(field.name)} className="field-wrap diagnosis-field">
                    <span className="diagnosis-field-label">{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <div className={`diagnosis-option-grid ${field.name === "m1_business_channels" ? "diagnosis-option-grid--multiwide" : "diagnosis-option-grid--single"}`}>
                      {(field.options ?? []).map((option) => (
                        <label key={`${field.name}-${option.value}`} className="diagnosis-option-card">
                          <input
                            type="radio"
                            name={field.name}
                            checked={selectedSingle === option.value}
                            onChange={() => updateDiagnosisValue(field.name, option.value)}
                          />
                          <span>{localizeOptionLabel(lang, option.value, option.label)}</span>
                        </label>
                      ))}
                    </div>
                    {(field.options ?? [])
                      .filter((option) => option.extraFieldId && selectedSingle === option.value)
                      .map((option) => (
                        <input
                          key={`${field.name}-${option.extraFieldId}`}
                          className="diagnosis-extra-input"
                          value={typeof diagnosisValues[option.extraFieldId as string] === "string"
                            ? String(diagnosisValues[option.extraFieldId as string])
                            : ""}
                          onChange={(event) => updateDiagnosisValue(option.extraFieldId as string, event.target.value)}
                          placeholder={option.extraPlaceholder ?? "请补充说明"}
                        />
                      ))}
                  </label>
                );
              }

              if (field.type === "multi") {
                return (
                  <label key={String(field.name)} className="field-wrap diagnosis-field">
                    <span className="diagnosis-field-label">{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <div className={`diagnosis-option-grid ${field.name === "m1_business_channels" ? "diagnosis-option-grid--multiwide" : "diagnosis-option-grid--multi"}`}>
                      {(field.options ?? []).map((option) => {
                        const checked = selectedMulti.includes(option.value);
                        return (
                          <label key={`${field.name}-${option.value}`} className="diagnosis-option-card">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={(event) => {
                                const next = event.target.checked
                                  ? [...selectedMulti, option.value]
                                  : selectedMulti.filter((item) => item !== option.value);
                                updateDiagnosisValue(field.name, next);
                                if (!event.target.checked && option.extraFieldId) {
                                  updateDiagnosisValue(option.extraFieldId, "");
                                }
                              }}
                            />
                            <span>{localizeOptionLabel(lang, option.value, option.label)}</span>
                          </label>
                        );
                      })}
                    </div>
                    {(field.options ?? [])
                      .filter((option) => option.extraFieldId && selectedMulti.includes(option.value))
                      .map((option) => (
                        <input
                          key={`${field.name}-${option.extraFieldId}`}
                          className="diagnosis-extra-input"
                          value={typeof diagnosisValues[option.extraFieldId as string] === "string"
                            ? String(diagnosisValues[option.extraFieldId as string])
                            : ""}
                          onChange={(event) => updateDiagnosisValue(option.extraFieldId as string, event.target.value)}
                          placeholder={option.extraPlaceholder ?? "请补充说明"}
                        />
                      ))}
                  </label>
                );
              }

              return (
                <label key={String(field.name)} className="field-wrap diagnosis-field">
                  <span className="diagnosis-field-label">{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                  <input
                    className="diagnosis-extra-input"
                    value={typeof diagnosisValues[field.name] === "string" ? String(diagnosisValues[field.name]) : ""}
                    onChange={(event) => updateDiagnosisValue(field.name, event.target.value)}
                  />
                </label>
              );
            })}
                </div>
              </section>
            ))}
          </div>

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runDiagnosisDevPreset}
                disabled={loading}
                title="开发期一键注入诊断问卷预设并运行真实后端流程"
              >
                一键体验诊断
              </button>
            ) : null}
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
          {DEV_ACCEL_ENABLED ? (
            <div className="schema-dev-banner">
              <strong>开发测试模式</strong>
              <span>
                当前为测试模式数据，仅用于开发联调与功能演示，不用于正式提交或合规判断。
              </span>
            </div>
          ) : null}
          <div className="schema-wizard-head">
            <div className="runner-title">Assessment Wizard</div>
            <span>{assessmentProgress}%</span>
          </div>
          <div className="schema-stepper">
            {ASSESSMENT_STEPS.map((step, index) => (
              <button
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === assessmentStepIndex ? "active" : ""}`}
                onClick={() => setAssessmentStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentAssessmentStep.title)}</div>
          <div className="schema-field-grid">
            {currentAssessmentStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <select
                      value={String(assessmentValues[field.name])}
                      onChange={(event) => updateAssessmentValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
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
                  <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                {DEV_ACCEL_ENABLED && assessmentDevFilePaths.length > 0 ? (
                  <>
                    {assessmentDevFilePaths.map((path) => (
                      <article key={`dev-assessment-file-${path}`} className="schema-upload-item">
                        <strong>{path.split("/").pop() || path}</strong>
                        <small>Dev preset</small>
                      </article>
                    ))}
                  </>
                ) : null}
                {assessmentFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {assessmentFiles.length === 0 && (!DEV_ACCEL_ENABLED || assessmentDevFilePaths.length === 0) ? (
                  <p className="resource-empty">请上传附件材料后再提交。</p>
                ) : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runAssessmentDevPreset}
                disabled={loading}
                title="开发期一键注入预设数据并运行真实Assessment流程"
              >
                一键体验主流程
              </button>
            ) : null}
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
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === pipiaStepIndex ? "active" : ""}`}
                onClick={() => setPipiaStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentPipiaStep.title)}</div>
          <div className="schema-field-grid">
            {currentPipiaStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <select
                      value={String(pipiaValues[field.name])}
                      onChange={(event) => updatePipiaValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
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
                  <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                {DEV_ACCEL_ENABLED && pipiaDevFilePaths.length > 0 ? (
                  <>
                    {pipiaDevFilePaths.map((path) => (
                      <article key={`dev-pipia-file-${path}`} className="schema-upload-item">
                        <strong>{path.split("/").pop() || path}</strong>
                        <small>Dev preset</small>
                      </article>
                    ))}
                  </>
                ) : null}
                {pipiaFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {pipiaFiles.length === 0 && (!DEV_ACCEL_ENABLED || pipiaDevFilePaths.length === 0) ? (
                  <p className="resource-empty">请上传至少1份PIPIA附件后再提交。</p>
                ) : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runPipiaDevPreset}
                disabled={loading}
                title="开发期一键注入PIPIA预设并运行真实后端流程"
              >
                一键体验PIPIA
              </button>
            ) : null}
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
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === bcrStepIndex ? "active" : ""}`}
                onClick={() => setBcrStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentBcrStep.title)}</div>
          <div className="schema-field-grid">
            {currentBcrStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <select
                      value={String(bcrValues[field.name])}
                      onChange={(event) => updateBcrValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
                      ))}
                    </select>
                  </label>
                );
              }
              return (
                <label key={String(field.name)} className="field-wrap schema-field-wide">
                  <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                {DEV_ACCEL_ENABLED && bcrDevFilePaths.length > 0 ? (
                  <>
                    {bcrDevFilePaths.map((path) => (
                      <article key={`dev-bcr-file-${path}`} className="schema-upload-item">
                        <strong>{path.split("/").pop() || path}</strong>
                        <small>Dev preset</small>
                      </article>
                    ))}
                  </>
                ) : null}
                {bcrFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {bcrFiles.length === 0 && (!DEV_ACCEL_ENABLED || bcrDevFilePaths.length === 0) ? (
                  <p className="resource-empty">请上传至少1份BCR材料后再提交。</p>
                ) : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runBcrDevPreset}
                disabled={loading}
                title="开发期一键注入BCR预设并运行真实后端流程"
              >
                一键体验BCR
              </button>
            ) : null}
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
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === dpiaStepIndex ? "active" : ""}`}
                onClick={() => setDpiaStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentDpiaStep.title)}</div>
          <div className="schema-field-grid">
            {currentDpiaStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <select
                      value={String(dpiaValues[field.name])}
                      onChange={(event) => updateDpiaValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
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
                  <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                </label>
              );
            })}
          </div>

          {dpiaStepIndex === DPIA_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">DPIA附件上传（docx/pdf/png/jpg）</div>
              <input type="file" multiple onChange={(event) => setDpiaFiles(Array.from(event.target.files ?? []))} />
              <div className="schema-upload-list">
                {DEV_ACCEL_ENABLED && dpiaDevFilePaths.length > 0 ? (
                  <>
                    {dpiaDevFilePaths.map((path) => (
                      <article key={`dev-dpia-file-${path}`} className="schema-upload-item">
                        <strong>{path.split("/").pop() || path}</strong>
                        <small>Dev preset</small>
                      </article>
                    ))}
                  </>
                ) : null}
                {dpiaFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {dpiaFiles.length === 0 && (!DEV_ACCEL_ENABLED || dpiaDevFilePaths.length === 0) ? (
                  <p className="resource-empty">请上传至少1份DPIA附件后再提交。</p>
                ) : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runDpiaDevPreset}
                disabled={loading}
                title="开发期一键注入DPIA预设并运行真实后端流程"
              >
                一键体验DPIA
              </button>
            ) : null}
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
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === tiaStepIndex ? "active" : ""}`}
                onClick={() => setTiaStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentTiaStep.title)}</div>
          <div className="schema-field-grid">
            {currentTiaStep.fields.map((field) => {
              if (field.type === "text") {
                return (
                  <label key={String(field.name)} className="field-wrap">
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                    <select
                      value={String(tiaValues[field.name])}
                      onChange={(event) => updateTiaValue(field.name, event.target.value as never)}
                    >
                      {(field.options ?? []).map((option) => (
                        <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
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
                  <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                </label>
              );
            })}
          </div>

          {tiaStepIndex === TIA_STEPS.length - 1 ? (
            <section className="schema-upload-card">
              <div className="runner-title">TIA附件上传（docx/pdf）</div>
              <input type="file" multiple onChange={(event) => setTiaFiles(Array.from(event.target.files ?? []))} />
              <div className="schema-upload-list">
                {DEV_ACCEL_ENABLED && tiaDevFilePaths.length > 0 ? (
                  <>
                    {tiaDevFilePaths.map((path) => (
                      <article key={`dev-tia-file-${path}`} className="schema-upload-item">
                        <strong>{path.split("/").pop() || path}</strong>
                        <small>Dev preset</small>
                      </article>
                    ))}
                  </>
                ) : null}
                {tiaFiles.map((file) => (
                  <article key={`${file.name}-${file.size}-${file.lastModified}`} className="schema-upload-item">
                    <strong>{file.name}</strong>
                    <small>{Math.max(1, Math.round(file.size / 1024))} KB</small>
                  </article>
                ))}
                {tiaFiles.length === 0 && (!DEV_ACCEL_ENABLED || tiaDevFilePaths.length === 0) ? (
                  <p className="resource-empty">请上传至少1份TIA附件后再提交。</p>
                ) : null}
              </div>
            </section>
          ) : null}

          <div className="schema-actions-row">
            {DEV_ACCEL_ENABLED ? (
              <button
                className="pill-btn"
                type="button"
                onClick={runTiaDevPreset}
                disabled={loading}
                title="开发期一键注入TIA预设并运行真实后端流程"
              >
                一键体验TIA
              </button>
            ) : null}
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
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === cnFlowStepIndex ? "active" : ""}`}
                onClick={() => setCnFlowStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentCnFlowStep.title)}</div>
          {currentCnFlowStep.fields.length > 0 ? (
            <div className="schema-field-grid">
              {currentCnFlowStep.fields.map((field) => {
                if (field.type === "text") {
                  return (
                    <label key={String(field.name)} className="field-wrap">
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
                      <select
                        value={String(cnFlowValues[field.name])}
                        onChange={(event) => updateCnFlowValue(field.name, event.target.value as never)}
                      >
                        {(field.options ?? []).map((option) => (
                          <option key={option} value={option}>{localizeOptionLabel(lang, String(option), option)}</option>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                key={localizeStepTitle(lang, step.title)}
                className={`schema-step-dot ${index === cpraStepIndex ? "active" : ""}`}
                onClick={() => setCpraStepIndex(index)}
                type="button"
              >
                {index + 1}. {localizeStepTitle(lang, step.title)}
              </button>
            ))}
          </div>

          <div className="schema-current-title">{localizeStepTitle(lang, currentCpraStep.title)}</div>
          {currentCpraStep.fields.length > 0 ? (
            <div className="schema-field-grid">
              {currentCpraStep.fields.map((field) => {
                if (field.type === "text") {
                  return (
                    <label key={String(field.name)} className="field-wrap">
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                      <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
                    <span>{localizeFieldLabel(lang, String(field.name), field.label)}</span>
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
