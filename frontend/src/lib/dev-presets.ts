import { getDefaultTestCase } from "./dev-test-cases";

export const DEV_ACCEL_ENABLED =
  String(import.meta.env.VITE_ENABLE_DEV_ACCEL ?? "").toLowerCase() === "true";

export type DevPresetModule =
  | "assessment"
  | "pipia"
  | "dpia"
  | "tia"
  | "eu_scc"
  | "bcr"
  | "diagnosis"
  | "document_review";

export type ModuleDevPreset = {
  id: string;
  module: DevPresetModule;
  title: string;
  scenarioDescription: string;
  formDefaults: Record<string, unknown>;
  backendFilePaths: string[];
};

export type AssessmentDevPreset = ModuleDevPreset & {
  module: "assessment";
  expectedPath: "security_assessment" | "scc_or_certification" | "exemption";
};

const SHARED_CONTRACT_FIXTURE = "benchmarks/sample-inputs/sample_contract.txt";
const SHARED_EVIDENCE_FIXTURE = "benchmarks/sample-inputs/sample_evidence.txt";

function assertCase(module: string) {
  const found = getDefaultTestCase(module);
  if (!found) {
    throw new Error(`Missing default test case for module: ${module}`);
  }
  return found;
}

const DEFAULT_DIAGNOSIS_CASE = assertCase("diagnosis");
const DEFAULT_ASSESSMENT_CASE = assertCase("assessment");
const DEFAULT_REVIEW_CASE = assertCase("review");

const ASSESSMENT_SECURITY_ASSESSMENT_PRESET: AssessmentDevPreset = {
  id: "assessment_cn_security_path",
  module: "assessment",
  title: "一键体验主流程（安全评估路径）",
  scenarioDescription:
    DEFAULT_ASSESSMENT_CASE.description,
  expectedPath: "security_assessment",
  formDefaults: { ...(DEFAULT_ASSESSMENT_CASE.formDefaults ?? {}) },
  backendFilePaths: [...(DEFAULT_ASSESSMENT_CASE.backendFilePaths ?? [])]
};

const PIPIA_BASELINE_PRESET: ModuleDevPreset = {
  id: "pipia_cn_baseline",
  module: "pipia",
  title: "一键运行PIPIA（标准合同备案路径）",
  scenarioDescription: "注入典型PIPIA字段并加载预置附件，直接调用真实后端生成PIPIA报告。",
  formDefaults: {
    route_type: "scc_filing",
    company_name: "华东云链科技（测试）",
    company_uscc: "91310115MA1KTEST88",
    industry: "互联网SaaS",
    is_ciio: false,
    processing_person_count: 1200000,
    outbound_pi_count: 380000,
    outbound_spi_count: 9000,
    outbound_scenario_name: "跨境客服与数据分析",
    purpose: "为境外客服中心和风控团队提供必要数据支持",
    transfer_method: "API接口周期同步",
    outbound_frequency: "日批量+实时工单触发",
    recipient_name: "OceanStar Technology Pte. Ltd.",
    recipient_country_region: "新加坡",
    legal_basis: "履行合同+用户授权同意",
    legality_justification: "已在隐私政策与业务条款中披露必要出境场景",
    necessity_justification: "境外客服能力由集团统一调度，境内无法完全替代",
    pi_categories: "账号标识,联系方式,订单信息,设备标识",
    spi_categories: "交易风控标签",
    subject_volume: 380000,
    notice_mechanism: "隐私政策+弹窗告知",
    consent_mechanism: "单独同意勾选并留痕",
    dsar_channel: "privacy@test-example.com",
    retention_policy: "最短必要期限，超过期限自动删除或匿名化",
    domestic_storage: "境内主库按业务必要保存",
    overseas_storage: "境外缓存仅保留30天",
    incident_response_sla_hours: 24,
    escalation_path: "客服运营 -> 数据安全 -> 法务 -> 管理层",
    transfer_link: "境内业务系统 -> 脱敏网关 -> 境外客服系统",
    business_overview: "跨境电商SaaS",
    processing_activity_overview: "订单履约、客服工单、风控审查",
    shareholding_structure: "集团控股",
    actual_controller: "张某",
    overseas_investment: "新加坡子公司",
    org_structure_privacy_team: "设DPO与专项隐私治理小组",
    attachment_role: "scc_contract"
  },
  backendFilePaths: [SHARED_CONTRACT_FIXTURE, SHARED_EVIDENCE_FIXTURE]
};

const EU_SCC_BASELINE_PRESET: ModuleDevPreset = {
  id: "scc_eu_baseline",
  module: "eu_scc",
  title: "一键运行SCC审查",
  scenarioDescription: "自动填充SCC关键字段并引用预置合同文本，直接触发真实SCC后端流程。",
  formDefaults: {
    exporter_name: "DataComply Europe GmbH",
    importer_name: "OceanStar Technology Pte. Ltd.",
    importer_country: "Singapore",
    transfer_role: "c2p",
    scc_version: "eu_2021",
    transfer_purpose: "跨境客服与统一运维支持",
    data_categories: "账号数据、订单信息、日志数据",
    data_subject_categories: "电商用户、平台商家员工",
    transfer_frequency: "periodic",
    retention_rule: "运营数据保留180天",
    tom_summary: "TLS传输加密、最小权限、操作审计、访问告警",
    onward_transfer_control: "再传输需合同审批并纳入供应商清单",
    rights_and_complaint: "支持数据主体访问、更正、删除与投诉渠道",
    government_access_response: "建立政府访问请求审查与升级机制",
    supplementary_clause_review: "重点复核第三方受益人权利、责任承担与管辖条款",
    pii_count: 280000,
    spi_count: 5000,
    has_scc_draft: true
  },
  backendFilePaths: [SHARED_CONTRACT_FIXTURE]
};

const BCR_BASELINE_PRESET: ModuleDevPreset = {
  id: "bcr_eu_baseline",
  module: "bcr",
  title: "一键运行BCR审查",
  scenarioDescription: "注入集团治理与跨境机制字段，并加载BCR主文档进行真实后端审查。",
  formDefaults: {
    company_name: "DataComply Global Group",
    group_structure: "母公司+欧盟控制实体+新加坡处理中心",
    applicant_entity: "DataComply Europe GmbH",
    data_flow_scope: "欧盟业务数据流向集团内部处理中心",
    lead_sa_rationale: "主营业地位于德国，选择德国监管机构作为lead SA",
    binding_mechanism: "集团内部强制政策+员工承诺+内控稽核",
    third_party_beneficiary: "数据主体可直接主张第三方受益人权利",
    liability_compensation: "母公司承担连带责任并设置赔付流程",
    transparency_notice: "通过隐私政策与员工通知持续更新",
    training_audit: "年度培训+季度审计",
    cooperation_with_sa: "设专职联络窗口配合监管问询",
    dp_safeguards: "最小化、加密、访问控制与日志留痕",
    third_country_assessment: "建立目的国法律变化跟踪与再评估机制",
    government_access_process: "政府访问请求需法律审查与逐级审批",
    update_mechanism: "重大变化触发版本更新与备案",
    definitions_quality: "术语体系与GDPR保持一致",
    review_focus: "重点审查责任承担、补充措施和第三方受益人条款"
  },
  backendFilePaths: ["resources/templates/eu/3.2_bcr_review_template_v0.docx"]
};

const DPIA_BASELINE_PRESET: ModuleDevPreset = {
  id: "dpia_eu_baseline",
  module: "dpia",
  title: "一键运行DPIA",
  scenarioDescription: "填充DPIA四步关键字段并附带流程文档，直接产出真实DPIA结果。",
  formDefaults: {
    project_name: "Global Support Analytics",
    project_goal: "提升跨境客服质量与响应效率",
    need_reason: "统一工单处理与风控识别",
    controller_name: "DataComply Europe GmbH",
    dpo_role: "集团DPO办公室",
    contact_channel: "dpo@test-example.com",
    processing_description: "汇总用户咨询、订单和行为数据用于工单分发与异常识别",
    data_types: "账号信息、订单信息、行为日志",
    includes_special_data: true,
    subject_scale: "约35万欧盟用户",
    frequency: "持续处理",
    retention_period: "180天",
    geo_scope: "德国/法国/西班牙",
    has_crossborder_transfer: true,
    data_source: "用户提交+系统日志",
    relationship_context: "用户与平台服务关系",
    expectation_control: "通过隐私政策与产品内提示满足合理预期",
    vulnerable_group: "未成年人占比低",
    prior_concerns: "曾发生过权限配置不当风险",
    novel_technology: "使用规则引擎进行风险打分",
    lawful_basis: "合同履行 + 合法利益",
    purpose_and_necessity: "跨境协作与统一运营所需",
    function_creep_control: "用途变更需二次评估与审批",
    minimization_quality: "仅保留必要字段并定期清理",
    notice_plan: "多层告知并记录版本",
    rights_support: "工单系统支持DSR闭环",
    processor_management: "DPA + 年度审计",
    risk_assessment: "中高风险，主要集中在跨境与敏感信息处理",
    mitigation_measures: "加密、脱敏、访问控制、审批与审计",
    residual_risk: "可控，需持续复核",
    signoff_owner: "法务负责人",
    dpo_advice: "建议季度复盘",
    review_schedule: "每季度复核",
    attachment_role: "data_flow_diagram"
  },
  backendFilePaths: ["resources/legal/sources/eu/references/2.2 ICO_DPIA_Temple.docx"]
};

const TIA_BASELINE_PRESET: ModuleDevPreset = {
  id: "tia_eu_baseline",
  module: "tia",
  title: "一键运行TIA",
  scenarioDescription: "填充TIA核心法律评估与补充措施字段，一键触发真实TIA后端执行。",
  formDefaults: {
    data_exporter_name: "DataComply Europe GmbH",
    data_importer_name: "OceanStar Technology Pte. Ltd.",
    importer_country_region: "Singapore",
    transfer_purpose: "客服协同、统一运维、风险识别",
    data_categories: "账号数据、订单数据、日志数据",
    sensitive_data_description: "风险标签",
    data_subject_categories: "平台用户",
    transfer_frequency: "periodic",
    transfer_tool: "scc",
    law_assessed: true,
    law_findings: "目的地法律整体可接受，但政府访问请求透明度有限",
    pre_effectiveness: "仅SCC条款不足以完全覆盖残余风险",
    supplementary_technical: "端到端加密、密钥分离、最小权限",
    supplementary_contractual: "增加政府访问通知与挑战义务",
    supplementary_organizational: "建立请求审查委员会与应急流程",
    post_effectiveness: "补充措施后风险可降至可接受水平",
    key_actions: "完善审计日志与季度复盘",
    dpo_opinion: "同意在附加措施落实后继续传输",
    review_date: "2026-07-01",
    attachment_role: "country_law_analysis"
  },
  backendFilePaths: ["resources/legal/sources/eu/references/TIA - Template.docx"]
};

const DIAGNOSIS_BASELINE_PRESET: ModuleDevPreset = {
  id: "diagnosis_cn_baseline",
  module: "diagnosis",
  title: "一键体验合规路径诊断",
  scenarioDescription: DEFAULT_DIAGNOSIS_CASE.description,
  formDefaults: { ...(DEFAULT_DIAGNOSIS_CASE.formDefaults ?? {}) },
  backendFilePaths: []
};

const DOCUMENT_REVIEW_BASELINE_PRESET: ModuleDevPreset = {
  id: "document_review_cn_baseline",
  module: "document_review",
  title: "一键运行文档专项智能审查",
  scenarioDescription: DEFAULT_REVIEW_CASE.description,
  formDefaults: { ...(DEFAULT_REVIEW_CASE.formDefaults ?? {}) },
  backendFilePaths: [...(DEFAULT_REVIEW_CASE.backendFilePaths ?? [])]
};

const PRESET_MAP = new Map<string, ModuleDevPreset>([
  [ASSESSMENT_SECURITY_ASSESSMENT_PRESET.id, ASSESSMENT_SECURITY_ASSESSMENT_PRESET],
  [PIPIA_BASELINE_PRESET.id, PIPIA_BASELINE_PRESET],
  [EU_SCC_BASELINE_PRESET.id, EU_SCC_BASELINE_PRESET],
  [BCR_BASELINE_PRESET.id, BCR_BASELINE_PRESET],
  [DPIA_BASELINE_PRESET.id, DPIA_BASELINE_PRESET],
  [TIA_BASELINE_PRESET.id, TIA_BASELINE_PRESET],
  [DIAGNOSIS_BASELINE_PRESET.id, DIAGNOSIS_BASELINE_PRESET],
  [DOCUMENT_REVIEW_BASELINE_PRESET.id, DOCUMENT_REVIEW_BASELINE_PRESET],
]);

const DEFAULT_PRESET_IDS: Record<DevPresetModule, string> = {
  assessment: ASSESSMENT_SECURITY_ASSESSMENT_PRESET.id,
  pipia: PIPIA_BASELINE_PRESET.id,
  eu_scc: EU_SCC_BASELINE_PRESET.id,
  bcr: BCR_BASELINE_PRESET.id,
  dpia: DPIA_BASELINE_PRESET.id,
  tia: TIA_BASELINE_PRESET.id,
  diagnosis: DIAGNOSIS_BASELINE_PRESET.id,
  document_review: DOCUMENT_REVIEW_BASELINE_PRESET.id,
};

export function getModuleDevPreset(module: DevPresetModule, id?: string): ModuleDevPreset {
  const preferredId = id ?? DEFAULT_PRESET_IDS[module];
  const preferred = PRESET_MAP.get(preferredId);
  if (preferred && preferred.module === module) {
    return preferred;
  }
  const fallback = Array.from(PRESET_MAP.values()).find((item) => item.module === module);
  if (!fallback) {
    throw new Error(`Missing dev preset for module: ${module}`);
  }
  return fallback;
}

export const DEFAULT_ASSESSMENT_PRESET_ID = ASSESSMENT_SECURITY_ASSESSMENT_PRESET.id;

export function getAssessmentDevPreset(id: string = DEFAULT_ASSESSMENT_PRESET_ID): AssessmentDevPreset {
  return getModuleDevPreset("assessment", id) as AssessmentDevPreset;
}
