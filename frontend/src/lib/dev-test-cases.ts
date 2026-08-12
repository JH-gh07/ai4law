import {
  buildAssessmentPayload,
  buildBcrPayload,
  buildCnFlowPayload,
  buildCpraPayload,
  buildDiagnosisPayload,
  buildDocumentReviewPayload,
  buildDpiaPayload,
  buildEuSccPayload,
  buildPipiaPayload,
  buildTiaPayload,
  buildUs14117Payload,
} from "../features/module-runner/payload-builders";
import type {
  AssessmentFormValues,
  BcrFormValues,
  CnFlowFormValues,
  CpraFormValues,
  DiagnosisFormValues,
  DocumentReviewFormValues,
  DpiaFormValues,
  EuSccFormValues,
  PipiaFormValues,
  TiaFormValues,
  Us14117FormValues,
} from "../features/module-runner/types";
import type { DevCaseModule, ModuleRequestMap } from "../api/api-contract";
import genomicRedScenario from "../../../benchmarks/cases/us_14117/geneguard_genomic_red/scenario.json";
import geolocationYellowScenario from "../../../benchmarks/cases/us_14117/geneguard_geolocation_yellow/scenario.json";
import telemetryGreenScenario from "../../../benchmarks/cases/us_14117/geneguard_telemetry_green/scenario.json";
import franceUkSccScenario from "../../../benchmarks/cases/eu_scc/france_c2c_uk_aws/scenario.json";
import germanyIndiaSccScenario from "../../../benchmarks/cases/eu_scc/germany_c2p_india_health/scenario.json";
import netherlandsSerbiaSccScenario from "../../../benchmarks/cases/eu_scc/netherlands_p2p_serbia_module_error/scenario.json";
import innovateUsTiaScenario from "../../../benchmarks/cases/tia/innovate_crm_us_saas/scenario.json";
import leidenIndiaTiaScenario from "../../../benchmarks/cases/tia/leiden_clinical_india/scenario.json";
import haitaoMarketingScenario from "../../../benchmarks/cases/pipia/haitao_marketing_singapore/scenario.json";
import weilanHrScenario from "../../../benchmarks/cases/pipia/weilan_hr_exemption_us/scenario.json";
import zhifutongEurocertScenario from "../../../benchmarks/cases/pipia/zhifutong_eurocert_de/scenario.json";
import kuajingYoupinScenario from "../../../benchmarks/cases/diagnosis/kuajing_youpin_ecommerce_sg/scenario.json";
import qianyanMedicalScenario from "../../../benchmarks/cases/diagnosis/qianyan_medical_research_eu/scenario.json";
import zhijiaWeilaiScenario from "../../../benchmarks/cases/diagnosis/zhijia_weilai_anonymized_de/scenario.json";
import dongfangTrustScenario from "../../../benchmarks/cases/assessment/dongfang_capital_trust_hk/scenario.json";
import youxuanShoppingScenario from "../../../benchmarks/cases/assessment/youxuan_shopping_data_export/scenario.json";
import dpiaAiRecruitmentScenario from "../../../benchmarks/cases/dpia/ai_recruitment_screening/scenario.json";
import dpiaSmartCityScenario from "../../../benchmarks/cases/dpia/smart_city_surveillance/scenario.json";
import trendyGoodsScenario from "../../../benchmarks/cases/cpra/trendy_goods_ecommerce/scenario.json";
import reviewDataSecurityScenario from "../../../benchmarks/cases/review/data_security_agreement/scenario.json";

/**
 * 开发者模式 — 由表单场景输入编译请求 payload。
 *
 * 每个案例源自 benchmarks/source-materials/ 中保留的历史测试材料。
 * formDefaults 和 backendFilePaths 是唯一场景输入；defineDevCases 通过纯 builder
 * 生成可直接 POST 的 payload，配合 SSE 事件流实时观察执行。
 *
 * 用法:
 *   import { DEV_TEST_CASES, MODULES_WITH_CASES } from "./dev-test-cases";
 *   const payload = DEV_TEST_CASES.cpra[0].payload;
 */

export type DevTestCase<Module extends DevCaseModule = DevCaseModule> = {
  /** Stable identifier shared by the frontend case catalog and CLI adapters. */
  caseId: string;
  /** 案例名称（显示在下拉菜单中） */
  name: string;
  /** 一句话描述 */
  description: string;
  /** 法域标签 */
  jurisdiction: "CN" | "EU" | "US";
  /** 可选：用于回填调试表单的默认值 */
  formDefaults?: Record<string, unknown>;
  /** 可选：开发模式下直接传给后端的测试文件路径 */
  backendFilePaths?: string[];
  /** 该案例的完整 JSON payload，可直接 POST */
  payload: ModuleRequestMap[Module];
};

type DevTestCaseSeed<Module extends DevCaseModule> =
  Omit<DevTestCase<Module>, "payload" | "caseId"> & { payload?: never };

const genomicRedRequest = genomicRedScenario.request as ModuleRequestMap["us_14117"];
const geolocationYellowRequest = geolocationYellowScenario.request as ModuleRequestMap["us_14117"];
const telemetryGreenRequest = telemetryGreenScenario.request as ModuleRequestMap["us_14117"];
const franceUkSccRequest = franceUkSccScenario.request as ModuleRequestMap["eu_scc"];
const germanyIndiaSccRequest = germanyIndiaSccScenario.request as ModuleRequestMap["eu_scc"];
const netherlandsSerbiaSccRequest = netherlandsSerbiaSccScenario.request as ModuleRequestMap["eu_scc"];
const innovateUsTiaRequest = innovateUsTiaScenario.request as ModuleRequestMap["tia"];
const leidenIndiaTiaRequest = leidenIndiaTiaScenario.request as ModuleRequestMap["tia"];
const haitaoMarketingRequest = haitaoMarketingScenario.request as ModuleRequestMap["pipia"];
const weilanHrRequest = weilanHrScenario.request as ModuleRequestMap["pipia"];
const zhifutongEurocertRequest = zhifutongEurocertScenario.request as ModuleRequestMap["pipia"];

function sharedTiaFormDefaults(
  request: ModuleRequestMap["tia"],
): TiaFormValues {
  const parts = (value: string) => value.split("；").map((item) => item.trim()).filter(Boolean);
  const labeled = (items: string[], label: string) =>
    items.find((item) => item.startsWith(label))?.slice(label.length).trim() ?? "";
  const exporter = parts(request.data_exporter_profile);
  const importer = parts(request.data_importer_profile);
  const assessment = parts(request.third_country_assessment);
  const measures = parts(request.supplementary_measures);
  const conclusion = parts(request.final_conclusion);
  const attachment = request.attachments[0];
  const frequency = labeled(exporter, "频率：");
  if (!attachment || !["one_time", "periodic", "continuous"].includes(frequency)) {
    throw new Error("TIA shared scenario requires one attachment and a supported transfer frequency");
  }
  return {
    structured_input_override: request.structured_input,
    data_exporter_name: exporter[0] ?? "",
    data_importer_name: importer[0] ?? "",
    importer_country_region: labeled(importer, "国家/地区："),
    transfer_purpose: labeled(exporter, "传输目的："),
    data_categories: labeled(exporter, "数据类别："),
    sensitive_data_description: labeled(importer, "敏感数据："),
    data_subject_categories: labeled(exporter, "数据主体："),
    transfer_frequency: frequency as TiaFormValues["transfer_frequency"],
    transfer_tool: request.transfer_tool,
    law_assessed: assessment[0] === "已完成法律评估",
    law_findings: assessment.find((item, index) => index > 0 && !item.startsWith("补充措施前判断：")) ?? "",
    pre_effectiveness: labeled(assessment, "补充措施前判断："),
    supplementary_technical: labeled(measures, "技术措施："),
    supplementary_contractual: labeled(measures, "合同措施："),
    supplementary_organizational: labeled(measures, "组织措施："),
    post_effectiveness: conclusion[0] ?? "",
    key_actions: labeled(conclusion, "关键行动："),
    dpo_opinion: labeled(conclusion, "DPO意见："),
    review_date: labeled(conclusion, "复审日期："),
    attachment_role: attachment.file_role,
  };
}

function sharedPipiaFormDefaults(
  request: ModuleRequestMap["pipia"],
): PipiaFormValues {
  const parts = (value: string) => value.split("；").map((item) => item.trim()).filter(Boolean);
  const labeled = (items: string[], label: string) =>
    items.find((item) => item.startsWith(label))?.slice(label.length).trim() ?? "";
  const unlabeled = (items: string[], labels: string[]) =>
    items.filter((item) => !labels.some((label) => item.startsWith(label))).join("；");
  const evidenceState = (value: boolean | null | undefined): PipiaFormValues["recipient_notice_complete"] =>
    value === true ? "yes" : value === false ? "no" : "unknown";
  const profile = request.company_profile;
  const transfer = request.transfer_context;
  const scope = request.personal_info_scope;
  const rights = request.rights_protection;
  const emergency = request.emergency_plan;
  const evidence = request.path_evidence ?? {};
  const attachment = request.attachments[0];
  const purposeParts = parts(transfer.purpose);
  const purposeLabels = ["场景：", "频率：", "方式：", "业务概况：", "处理活动："];
  const legalParts = parts(transfer.legal_basis);
  const legalLabels = ["合法性论证：", "必要性论证："];
  const escalationParts = parts(emergency.escalation_path);
  const escalationLabels = ["链路：", "股权：", "控制人：", "境内外投资：", "组织与个保机构："];
  const frequency = labeled(purposeParts, "频率：");
  return {
    route_type: request.route_type,
    company_name: profile.company_name,
    company_uscc: profile.company_uscc,
    industry: profile.industry ?? "",
    shareholding_structure: labeled(escalationParts, "股权："),
    actual_controller: labeled(escalationParts, "控制人："),
    overseas_investment: labeled(escalationParts, "境内外投资："),
    org_structure_privacy_team: labeled(escalationParts, "组织与个保机构："),
    business_overview: labeled(purposeParts, "业务概况："),
    processing_activity_overview: labeled(purposeParts, "处理活动："),
    is_ciio: profile.is_ciio ?? false,
    processing_person_count: profile.processing_person_count ?? 0,
    outbound_pi_count: profile.outbound_pi_count ?? 0,
    outbound_spi_count: profile.outbound_spi_count ?? 0,
    outbound_scenario_name: labeled(purposeParts, "场景："),
    outbound_frequency: ["one_time", "periodic", "continuous"].includes(frequency)
      ? frequency as PipiaFormValues["outbound_frequency"]
      : "periodic",
    transfer_method: labeled(purposeParts, "方式："),
    domestic_storage: "",
    overseas_storage: "",
    transfer_link: labeled(escalationParts, "链路："),
    purpose: unlabeled(purposeParts, purposeLabels),
    recipient_name: transfer.recipient_name,
    recipient_country_region: transfer.recipient_country_region,
    legal_basis: unlabeled(legalParts, legalLabels),
    legality_justification: labeled(legalParts, "合法性论证："),
    necessity_justification: labeled(legalParts, "必要性论证："),
    pi_categories: (scope.pi_categories ?? []).join(", "),
    spi_categories: (scope.spi_categories ?? []).join(", "),
    subject_volume: scope.subject_volume ?? 0,
    notice_mechanism: rights.notice_mechanism,
    consent_mechanism: rights.consent_mechanism,
    dsar_channel: rights.dsar_channel,
    retention_policy: rights.retention_policy,
    incident_response_sla_hours: emergency.incident_response_sla_hours ?? 24,
    escalation_path: unlabeled(escalationParts, escalationLabels),
    attachment_role: attachment.file_role,
    recipient_notice_complete: evidenceState(evidence.recipient_notice_complete),
    sensitive_information_classification_confirmed: evidenceState(evidence.sensitive_information_classification_confirmed),
    consent_evidence_complete: evidenceState(evidence.consent_evidence_complete),
    scc_required_clauses_complete: evidenceState(evidence.scc_required_clauses_complete),
    hr_rules_lawfully_adopted: evidenceState(evidence.hr_rules_lawfully_adopted),
    employee_handbook_has_explicit_cross_border_terms: evidenceState(evidence.employee_handbook_has_explicit_cross_border_terms),
    collective_agreement_has_explicit_cross_border_terms: evidenceState(evidence.collective_agreement_has_explicit_cross_border_terms),
    recipient_privacy_policy_provided: evidenceState(evidence.recipient_privacy_policy_provided),
    certification_body_china_recognized: evidenceState(evidence.certification_body_china_recognized),
    certification_legal_obligation_citation_provided: evidenceState(evidence.certification_legal_obligation_citation_provided),
    contract_governing_law: evidence.contract_governing_law ?? "",
    contract_exclusive_jurisdiction: evidence.contract_exclusive_jurisdiction ?? "",
    china_data_subject_rights_terms_present: evidenceState(evidence.china_data_subject_rights_terms_present),
  };
}

function sharedEuSccFormDefaults(
  request: ModuleRequestMap["eu_scc"],
  display: Omit<
    EuSccFormValues,
    "project_name_override" | "scc_text_override" | "has_scc_draft" | "declared_module_type"
    | "has_tia" | "has_supplementary_measures"
  >,
): EuSccFormValues {
  return {
    ...display,
    project_name_override: request.project_name,
    scc_text_override: request.scc_text,
    declared_module_type: request.declared_module_type,
    has_scc_draft: true,
    has_tia: request.has_tia ?? false,
    has_supplementary_measures: request.has_supplementary_measures ?? false,
  };
}

function sharedUs14117FormDefaults(request: ModuleRequestMap["us_14117"]): Us14117FormValues {
  const dataItem = request.data_items[0];
  const entity = request.recipient_entities[0];
  if (!request.company_name || !request.transaction_type || !dataItem || !entity) {
    throw new Error("US 14117 shared scenario requires company, transaction, data and recipient facts");
  }
  return {
    company_name: request.company_name,
    project_name: request.project_name,
    transaction_description: request.transaction_description,
    transaction_type: request.transaction_type,
    data_item_name: dataItem.data_item_name,
    data_description: dataItem.data_description ?? "",
    doj_data_category: dataItem.doj_data_category ?? "",
    us_person_count: dataItem.us_person_count ?? 0,
    entity_name: entity.entity_name,
    country_of_registration: entity.country_of_registration,
    government_control: entity.government_control ?? false,
    entity_role: entity.entity_role ?? "other",
    onward_transfer: request.onward_transfer ?? false,
    onward_transfer_description: request.onward_transfer_description ?? "",
    security_measures_summary: (request.security_measures ?? []).map((item) => item.description ?? item.measure_name).join("；"),
    review_focus: "按统一场景核查数据阈值、被涵盖人员和交易类型",
    data_items_override: request.data_items,
    recipient_entities_override: request.recipient_entities,
    access_persons_override: request.access_persons ?? [],
    security_measures_override: request.security_measures ?? [],
  };
}

function buildCasePayload<Module extends DevCaseModule>(
  module: Module,
  testCase: DevTestCaseSeed<Module>,
): ModuleRequestMap[Module] {
  const values = testCase.formDefaults ?? {};
  const paths = testCase.backendFilePaths ?? [];
  let payload: ModuleRequestMap[DevCaseModule];
  switch (module) {
    case "diagnosis": payload = buildDiagnosisPayload(values as DiagnosisFormValues); break;
    case "assessment": payload = buildAssessmentPayload(values as AssessmentFormValues, paths); break;
    case "review": payload = buildDocumentReviewPayload(values as DocumentReviewFormValues, paths); break;
    case "pipia": payload = buildPipiaPayload(values as PipiaFormValues, paths); break;
    case "bcr": payload = buildBcrPayload(values as BcrFormValues, paths); break;
    case "dpia": payload = buildDpiaPayload(values as DpiaFormValues, paths); break;
    case "tia": payload = buildTiaPayload(values as TiaFormValues, paths); break;
    case "eu_scc": payload = buildEuSccPayload(values as EuSccFormValues, paths); break;
    case "us_14117": payload = buildUs14117Payload(values as Us14117FormValues, paths); break;
    case "cn_flow": payload = buildCnFlowPayload(values as CnFlowFormValues, {
      dataInventory: paths.slice(0, 1),
      entityInventory: paths.slice(1, 2),
      supporting: paths.slice(2),
    }); break;
    case "cpra": payload = buildCpraPayload(values as CpraFormValues, {
      privacyPolicy: paths,
      rightsSop: [],
      dataMap: [],
      vendorList: [],
      other: [],
    }); break;
  }
  return payload as ModuleRequestMap[Module];
}

export function defineDevCases<Module extends DevCaseModule>(
  module: Module,
  cases: DevTestCaseSeed<Module>[],
): DevTestCase<Module>[] {
  return cases.map((testCase, index) => ({
    ...testCase,
    caseId: `${module}-${String(index + 1).padStart(2, "0")}`,
    payload: buildCasePayload(module, testCase),
  }));
}

// ═══════════════════════════════════════════════════════════════════════════
// CPRA — 3 cases
//   来源测试文档:
//     benchmarks/source-materials/us/legacy-docx/“CPRA合规”测试案例及预期输出.docx
//     resources/new/…/美国/任务2：“CPRA合规”路径描述及测试案例/“CPRA合规”测试案例及预期输出.docx
//     benchmarks/datasets/seed-cases-v1/_source/task10/task10_case1.docx
//     backend/tests/cpra/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const cpraTrendyGoods = {
  name: trendyGoodsScenario.display.name,
  description: trendyGoodsScenario.display.description,
  jurisdiction: "US" as const,
  formDefaults: {
    company_name: "TrendyGoods Inc.",
    dba_name: "TrendyGoods.com",
    cpra_applicability_selfcheck: "年收入约3000万美元，超过2500万美元门槛，受CPRA管辖",
    business_model: "线上时尚零售商，通过网站和移动应用向消费者直销。使用用户行为分析进行个性化推荐，并使用第三方广告服务",
    data_lifecycle: "收集→分析→个性化推荐→与第三方广告网络共享",
    data_categories: "用户浏览行为、购买历史、设备信息、联系方式",
    notice_and_consent: "隐私政策链接在网站底部。Cookie横幅仅提供\"接受\"按钮，同等突出的\"拒绝所有\"选项缺失",
    privacy_policy_url: "https://trendygoods.com/privacy",
    consumer_rights_process: "提供在线表单和邮箱渠道，但缺少免费电话",
    identity_verification_method: "通过注册邮箱发送验证链接",
    rights_sla: "承诺45天内响应",
    opt_out_and_sale_sharing: "与AdNetwork Alpha和Beta共享用户浏览行为数据和购买历史用于定向广告。页脚链接文字为\"Privacy Settings\"，未使用CPPA规定的标准化文字和三角图标",
    spi_usage_summary: "无特殊敏感信息处理",
    vendor_management: "与AdNetwork的合同为标准广告服务条款，未包含其必须遵守消费者opt-out指令的条款",
    ui_dark_pattern_check: "Cookie横幅\"接受所有\"按钮颜色突出，\"管理偏好\"链接字体极小且颜色与背景相近",
    review_focus: "重点检查opt-out机制、Cookie同意横幅和广告合作伙伴合同"
  },

};

const cpraDataFlow = {
  name: "CPRA-2: DataFlow SaaS 服务商",
  description: "B2B SaaS，年收入18M不达标但处理量>10万，服务提供商角色混淆，适用性边界测试",
  jurisdiction: "US" as const,
  formDefaults: {
    company_name: "DataFlow Analytics LLC",
    dba_name: "",
    cpra_applicability_selfcheck: "年收入约1800万美元（未达2500万门槛），但年处理消费者个人信息可能超过10万条，需评估是否仍受管辖",
    business_model: "B2B SaaS，为中小企业提供数据看板服务。客户将业务数据上传至DataFlow平台进行分析",
    data_lifecycle: "客户上传数据→分析处理→生成看板→返回客户。作为服务提供商，数据由客户（控制者）决定处理目的",
    data_categories: "客户业务数据（含可能涉及的消费者个人信息）",
    notice_and_consent: "不与消费者直接交互，依赖客户（控制者）履行通知义务",
    privacy_policy_url: "https://dataflow.io/dpa",
    consumer_rights_process: "无面向消费者的DSR渠道。内部流程：收到客户转交的DSR请求后15个工作日内协助执行",
    identity_verification_method: "由控制者（客户）负责验证",
    rights_sla: "协助客户在15个工作日内响应",
    opt_out_and_sale_sharing: "不出售或分享数据，严格按控制者的书面指示处理数据",
    spi_usage_summary: "不主动识别或分类客户数据中的敏感信息",
    vendor_management: "与客户签订的《数据处理协议》模板需审查是否包含CPRA §1798.100要求的全部强制性条款。与AWS等云基础设施提供商签订有标准DPA",
    ui_dark_pattern_check: "不适用（无面向消费者的UI）",
    review_focus: "重点审查适用性边界和服务提供商合同合规性"
  },

};

const cpraFitLife = {
  name: "CPRA-3: FitLife AI 健康科技",
  description: "健康APP收集SPI，暗模式获取同意，向第三方营销出售健康衍生数据，缺失Limit SPI权利",
  jurisdiction: "US" as const,
  formDefaults: {
    company_name: "FitLife AI Inc.",
    dba_name: "FitLife",
    cpra_applicability_selfcheck: "年收入超过2500万美元，处理大量消费者健康数据，明确受CPRA管辖",
    business_model: "智能健身APP开发商，通过手机传感器和可穿戴设备收集用户的健康、生物特征和精确位置数据，提供个性化健身指导和健康风险预测",
    data_lifecycle: "传感器采集→健康分析→个性化指导+产品推荐→与保健品/保险公司共享健康衍生数据",
    data_categories: "心率、步数、睡眠、位置、健康评估数据",
    notice_and_consent: "注册界面使用捆绑同意设计。SPI处理的单独同意选项默认勾选且隐藏在多层菜单后。UI暗模式：\"同意并继续\"为大号绿色按钮，\"仅浏览\"为灰色小字",
    privacy_policy_url: "https://fitlife.ai/privacy",
    consumer_rights_process: "DSR渠道隐藏在五层菜单中（设置→隐私→更多选项→行使权利→提交请求），不符合\"易于找到和使用\"要求。完全缺失Limit SPI权利入口",
    identity_verification_method: "仅邮箱验证",
    rights_sla: "未明确承诺处理时限",
    opt_out_and_sale_sharing: "向保健品公司HealthSupps和保险公司QuickInsure共享用户健康衍生数据。未提供选择退出链接",
    spi_usage_summary: "健康数据用于个性化健身（合理），但同时用于第三方营销（超出合理范围，需要Limit SPI机制）",
    vendor_management: "与HealthSupps和QuickInsure的合同为简单数据共享协议，完全未提及CPRA合规义务",
    ui_dark_pattern_check: "注册界面\"同意并继续\"为大号绿色按钮，\"仅浏览\"为灰色小字。健康SPI单独同意默认勾选且隐藏。存在明确暗模式",
    review_focus: "重点审查SPI同意有效性、暗模式、Limit SPI权利缺失和第三方数据共享"
  },

};

// ═══════════════════════════════════════════════════════════════════════════
// Diagnosis — 3 cases
//   来源测试文档:
//     benchmarks/source-materials/cn/legacy-docx/“合规路径诊断”测试案例及预期输出.docx
//     benchmarks/source-materials/shared/测试案例系统输入内容与提示词(3).docx (L2-L31)
//     resources/new/…/中国/任务1：“合规路径诊断”路径描述及测试案例/“合规路径诊断”测试案例及预期输出.docx
//     benchmarks/datasets/seed-cases-v1/_source/task1/task1_case1.docx
//     backend/tests/diagnosis/cases/01_scc_path.json
// ═══════════════════════════════════════════════════════════════════════════

const diagEcommerce = {
  name: kuajingYoupinScenario.display.name,
  description: kuajingYoupinScenario.display.description,
  jurisdiction: "CN" as const,
  formDefaults: {
    company_name: "跨境优品",
    m1_industry: "电商零售",
    m1_business_channels: ["线上平台（APP / 小程序 / 官网）", "跨境服务（面向国外用户 / 业务涉及国外）"],
    m1_service_targets: "个人用户",
    m1_company_size: "中型（51-200人）",
    m2_core_needs: ["识别业务合规风险点"],
    m2_had_compliance_issue: "no",
    m2_deadline: "一般需求（1-3个月）",
    m3_processes_personal_info: "yes",
    m3_personal_info_types: ["姓名", "手机号", "收货地址"],
    m3_processes_important_data: "no",
    m3_data_sources: ["用户主动提交"],
    m3_processing_activities: ["收集", "存储", "传输", "跨境传输"],
    m3_data_volume_range: "10-100万条",
    m3_retention_period: "按法律规定期限留存",
    m4_share_to_third_party: "no",
    m4_cross_border_transfer: "yes",
    m4_cross_border_regions: "新加坡",
    m4_commercialization: "no",
    m4_entrusted_processing: "no",
    m4_authorization_method: "弹窗勾选同意",
    m5_systems: ["自有 APP", "官方网站"],
    m5_security_measures: ["数据加密", "访问权限控制"],
    m5_compliance_docs: ["隐私政策", "用户协议"],
    m5_penalty_or_complaint: "无相关记录"
  },
};

const diagMedical = {
  name: qianyanMedicalScenario.display.name,
  description: qianyanMedicalScenario.display.description,
  jurisdiction: "CN" as const,
  formDefaults: {
    company_name: "前沿生命科技研究院",
    m1_industry: "医疗健康",
    m1_business_channels: ["数据合作（与其他公司共享 / 交换数据）"],
    m1_service_targets: "个人用户",
    m1_company_size: "中型（51-200人）",
    m2_core_needs: ["识别业务合规风险点"],
    m2_had_compliance_issue: "no",
    m2_deadline: "紧急需求（1个月内）",
    m3_processes_personal_info: "yes",
    m3_personal_info_types: ["健康信息"],
    m3_processes_important_data: "yes",
    m3_important_data_types: ["医疗健康数据"],
    m3_data_sources: ["用户主动提交"],
    m3_processing_activities: ["收集", "存储", "传输", "跨境传输"],
    m3_data_volume_range: "10万条以下",
    m3_retention_period: "按法律规定期限留存",
    m4_share_to_third_party: "yes",
    m4_third_party_types: "学术合作方",
    m4_cross_border_transfer: "yes",
    m4_cross_border_regions: "欧盟",
    m4_commercialization: "no",
    m4_entrusted_processing: "no",
    m4_authorization_method: '单独点击"同意"按钮',
    m5_systems: ["定制化业务系统"],
    m5_security_measures: ["数据加密", "数据脱敏", "访问权限控制", "操作日志审计"],
    m5_compliance_docs: ["数据安全管理制度", "应急响应预案"],
    m5_penalty_or_complaint: "无相关记录"
  },
};

const diagAnonymous = {
  name: zhijiaWeilaiScenario.display.name,
  description: zhijiaWeilaiScenario.display.description,
  jurisdiction: "CN" as const,
  formDefaults: {
    company_name: "智驾未来",
    m1_industry: "汽车与自动驾驶技术",
    m1_business_channels: [
      "数据合作（与其他公司共享 / 交换数据）",
      "跨境服务（面向国外用户 / 业务涉及国外）"
    ],
    m1_service_targets: "企业用户",
    m1_company_size: "中型（51-200人）",
    m2_core_needs: ["确认匿名化数据是否需要跨境合规路径", "识别业务合规风险点"],
    m2_had_compliance_issue: "no",
    m2_deadline: "一般需求（1-3个月）",
    m3_processes_personal_info: "no",
    m3_personal_info_types: [],
    m3_processes_enterprise_public_data: "no",
    m3_enterprise_public_data_desc: "已完全匿名化的车辆传感器数据包，无法关联到特定车辆或个人",
    m3_data_sources: ["设备自动采集"],
    m3_processing_activities: ["收集", "存储", "传输", "跨境传输"],
    m3_data_volume_range: "10万条以上",
    m3_retention_period: "业务必要期限内留存",
    m3_retention_desc: "按全球算法研发项目需要保存，数据始终维持不可识别状态",
    m4_share_to_third_party: "yes",
    m4_third_party_types: "德国母公司研发中心",
    m4_cross_border_transfer: "yes",
    m4_cross_border_regions: "德国",
    m4_commercialization: "no",
    m4_commercialization_mode: "",
    m4_entrusted_processing: "no",
    m4_entrusted_party_type: "",
    m4_authorization_method: "不适用（不包含个人信息）",
    m5_systems: ["定制化业务系统"],
    m5_security_measures: ["数据加密", "访问权限控制", "操作日志审计"],
    m5_compliance_docs: ["匿名化处理技术文档", "数据出境管理制度"],
    m5_penalty_or_complaint: "无相关记录"
  },
};

// ═══════════════════════════════════════════════════════════════════════════
// Assessment — 2 cases
//   来源测试文档:
//     benchmarks/source-materials/cn/legacy-docx/“安全评估路径”测试案例及预期输出.docx
//     benchmarks/source-materials/shared/测试案例系统输入内容与提示词(3).docx (L33-L50)
//     resources/new/…/中国/任务2：“安全评估路径”路径描述及测试案例/“安全评估路径”测试案例及预期输出.docx
//     benchmarks/datasets/seed-cases-v1/_source/task2/task2_case1.docx
//     backend/tests/assessment/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const assessCIO = {
  name: dongfangTrustScenario.display.name,
  description: dongfangTrustScenario.display.description,
  jurisdiction: "CN" as const,
  formDefaults: {
    company_name: "东方信托有限责任公司",
    company_uscc: "91110000MA1TEST001",
    industry: "金融科技",
    is_ciio: true,
    contains_important_data: true,
    pii_count: 80000,
    spi_count: 80000,
    transfer_purpose: "跨境集团财务报告与风险管理，满足集团合并报表监管要求",
    receiver_country: "香港",
    force_override_path: true,
    transfer_frequency: "continuous",
    receiver_name: "东方金融控股集团",
    security_capability_summary: "管理：有《数据分类分级管理规范》。技术：传输采用AES-256加密，存储采用令牌化。认证：通过网络安全等级保护（三级）测评",
    data_inventory_summary: "每日交易结算数据、高净值客户资产配置信息（含金融账户信息）",
    system_chain_summary: "境内存储：公司本地数据中心；传输链路：通过IPSec-VPN专线加密传输至香港母公司私有云；境外存储：香港数据中心",
    legal_basis: "履行集团内部管理与监管报告义务",
    necessity_basis: "集团合并报表监管要求，境内无法完全替代",
    scenario_name: "跨境集团财务报告与风险管理",
    assessment_start_date: "2025-04-01",
    assessment_end_date: "2025-04-20",
    lead_department: "合规部",
    participant_departments: "信息技术部、业务部门",
    legal_representative: "（略）",
    registered_address: "北京市",
    company_nature: "持牌金融机构"
  },
  backendFilePaths: [
    "resources/legal/sources/cn/references/数据出境风险自评估报告（模板）.docx",
  ],
};

const assessEcommerce = {
  name: youxuanShoppingScenario.display.name,
  description: youxuanShoppingScenario.display.description,
  jurisdiction: "CN" as const,
  formDefaults: {
    company_name: "优选购物",
    company_uscc: "91440300MA5TEST002",
    legal_representative: "待补充",
    registered_address: "中国大陆",
    company_nature: "有限责任公司",
    industry: "电子商务",
    receiver_country: "开曼群岛",
    receiver_name: "Global E-commerce Inc.",
    assessment_start_date: "2025-08-01",
    assessment_end_date: "2025-09-15",
    lead_department: "法务合规部",
    participant_departments: "信息技术部、网络安全部、业务运营部",
    third_party_support: false,
    third_party_name: "",
    third_party_scope: "",
    scenario_name: "全球推荐算法训练的用户行为数据同步",
    transfer_frequency: "continuous",
    is_long_term: true,
    transfer_purpose:
      "将中国大陆用户浏览、点击和购买行为日志传输至境外数据湖，用于训练全球推荐算法模型",
    legal_basis:
      "隐私政策仅概括说明可能向关联方共享数据，尚未针对该出境场景完成充分告知和单独同意",
    necessity_basis:
      "全球推荐算法需要跨区域行为数据，但应先证明去标识化有效性并完成境外接收方及下游处理者约束",
    is_ciio: false,
    contains_important_data: false,
    pii_count: 1200000,
    spi_count: 0,
    data_inventory_summary:
      "中国大陆用户浏览、点击、购买行为日志（去标识化后），年出境用户数预计约120万人；需核验K-匿名和差分隐私技术的有效性",
    system_chain_summary:
      "中国境内应用和数据库→杭州区域清洗、去标识化→阿里云国际站新加坡区域→Global E-commerce Inc. 数据湖→美国 DataMind LLC 分析处理",
    security_capability_summary:
      "使用K-匿名和差分隐私进行去标识化，但未提供第三方审计或技术验证；与母公司有协议，但未明确约束美国下游处理者 DataMind LLC",
    force_override_path: true
  },
  backendFilePaths: [
    "resources/legal/sources/cn/references/数据出境风险自评估报告（模板）.docx",
  ]
};

// ═══════════════════════════════════════════════════════════════════════════
// EU SCC — 3 cases (from EU data export path)
//   来源测试文档:
//     benchmarks/source-materials/eu/legacy-docx/“SCC审查”测试案例及预期输出.docx（含3个case：C2C缺失补充措施、C2P Clause15修改、Module选择错误）
//     resources/new/…/欧盟/任务1：“SCC审查”路径描述及测试案例/“SCC审查”测试案例及预期输出.docx
//     benchmarks/datasets/seed-cases-v1/_source/task5/task5_case1.docx
//     backend/tests/eu_scc/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const euSccBasic = {
  name: franceUkSccScenario.display.name,
  description: franceUkSccScenario.display.description,
  jurisdiction: "EU" as const,
  formDefaults: sharedEuSccFormDefaults(franceUkSccRequest, {
      exporter_name: "EU Fashion E-commerce SAS", importer_name: "UK Marketing Analytics Ltd", importer_country: "英国",
      transfer_role: "c2c", scc_version: "eu_2021", transfer_purpose: "市场趋势分析和个性化营销",
      data_categories: "姓名、邮箱、地址、订单历史", data_subject_categories: "欧盟电商客户",
      transfer_frequency: "continuous", retention_rule: "最后一次客户互动后3年",
      tom_summary: "TLS、AES-256、最小权限和安全培训；未覆盖美国下游政府访问风险",
      onward_transfer_control: "英国接收方使用美国 AWS 进行处理和存储",
      rights_and_complaint: "由英国接收方提供查询与投诉渠道", government_access_response: "",
      supplementary_clause_review: "", pii_count: 0, spi_count: 0,
  }),
  backendFilePaths: franceUkSccRequest.uploaded_files
};

const euSccHealthIndia = {
  name: germanyIndiaSccScenario.display.name,
  description: germanyIndiaSccScenario.display.description,
  jurisdiction: "EU" as const,
  formDefaults: sharedEuSccFormDefaults(germanyIndiaSccRequest, {
      exporter_name: "Gesundheitsforschung GmbH", importer_name: "Data Insights Solutions Pvt. Ltd.", importer_country: "印度",
      transfer_role: "c2p", scc_version: "eu_2021", transfer_purpose: "医疗研究数据统计分析",
      data_categories: "患者研究编号、年龄组、性别、诊断代码、治疗代码、实验室检测结果",
      data_subject_categories: "医疗研究参与患者", transfer_frequency: "periodic",
      retention_rule: "研究项目结束后按法规要求保留", tom_summary: "TLS、AES-256和最小权限控制",
      onward_transfer_control: "子处理者变更采用15个工作日无异议机制", rights_and_complaint: "需补充数据主体权利机制",
      government_access_response: "Clause 15通知义务被削弱", supplementary_clause_review: "需核查条款修改和特殊类别数据误分类",
      pii_count: 0, spi_count: 0,
  }),
  backendFilePaths: germanyIndiaSccRequest.uploaded_files
};

const euSccModuleError = {
  name: netherlandsSerbiaSccScenario.display.name,
  description: netherlandsSerbiaSccScenario.display.description,
  jurisdiction: "EU" as const,
  formDefaults: sharedEuSccFormDefaults(netherlandsSerbiaSccRequest, {
    exporter_name: "Orange Cloud BV",
    importer_name: "Balkan IT Support DOO",
    importer_country: "塞尔维亚",
    transfer_role: "p2p",
    scc_version: "eu_2021",
    transfer_purpose: "客户支持工单数据转委托给塞尔维亚子处理者。实际链：控制者(北欧零售集团)→处理者(Orange Cloud)→子处理者(Balkan IT) — 应为Module Three",
    data_categories: "客户姓名、问题描述、联系信息",
    data_subject_categories: "北欧零售集团客户",
    transfer_frequency: "continuous",
    retention_rule: "工单解决后按主服务协议保留",
    tom_summary: "标准安全措施，但缺少针对子处理者授权的完整合规框架",
    onward_transfer_control: "子处理者授权链不完整，加入方信息仅引用外部文件",
    supplementary_clause_review: "核心缺陷：模块选择根本性错误（应为Module Three而非Module Two）、加入方信息缺失、授权链不完整",
    rights_and_complaint: "上游控制者信息不完整，影响权利行使和责任识别",
    government_access_response: "未提供塞尔维亚第三国法律评估",
    pii_count: 0,
    spi_count: 0,
  }),
  backendFilePaths: netherlandsSerbiaSccRequest.uploaded_files
};

// ═══════════════════════════════════════════════════════════════════════════
// BCR — 3 cases
//   来源测试文档:
//     benchmarks/source-materials/eu/legacy-docx/“BCR审核”测试案例及预期输出.docx
//     resources/new/…/欧盟/任务2：“BCR审核”路径描述及测试案例/“BCR审核”测试案例及预期输出.docx
//     backend/tests/bcr/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const bcrMediumRisk = {
  name: "BCR-1: GlobalTech 中风险BCR-C",
  description: "跨国科技集团BCR-C，TIA描述笼统，投诉流程不具体，向集团外传输限制不明确(3个中风险)",
  jurisdiction: "EU" as const,
  formDefaults: {
    company_name: "GlobalTech Inc.",
    group_structure: "跨国科技公司，总部爱尔兰都柏林，业务遍及欧盟、美国、印度和新加坡",
    applicant_entity: "GlobalTech Ireland Ltd, Dublin",
    data_flow_scope: "内部从欧盟实体向非充分性认定国家（美国、印度）的数据传输",
    lead_sa_rationale: "主营业地位于爱尔兰，选择DPC作为lead SA",
    binding_mechanism: "集团内部强制政策+董事会决议",
    third_party_beneficiary: "已包含第三方受益人权利条款，但执行流程不够具体",
    liability_compensation: "母公司GlobalTech Inc.承担连带责任",
    transparency_notice: "通过隐私政策对外公开BCR摘要",
    training_audit: "年度培训+内部审计",
    cooperation_with_sa: "承诺配合DPC监管",
    dp_safeguards: "最小化、加密、访问控制、日志留痕",
    third_country_assessment: "仅泛泛承诺评估，未提及EDPB建议01/2020的六步法，未要求记录评估结果",
    government_access_process: "通知义务被弱化为\"在法律允许的范围内\"",
    update_mechanism: "重大变化触发版本更新",
    definitions_quality: "术语与GDPR一致",
    review_focus: "重点审查第三国法律评估(TIA)的具体性、投诉流程的可执行性、向集团外传输的限制条件"
  },
  backendFilePaths: ["backend/tests/fixtures/eu/bcr_c_globaltech.docx"]
};

const bcrHighRisk = {
  name: "BCR-2: HealthData 高风险BCR-C",
  description: "医疗联盟BCR-C，缺失第三方受益人权利条款、未指定欧盟责任主体、法律约束力不清晰(3个高风险)",
  jurisdiction: "EU" as const,
  formDefaults: {
    company_name: "HealthData Alliance",
    group_structure: "多家欧洲医疗机构组成的联盟，共享匿名医疗研究数据",
    applicant_entity: "（未指定）",
    data_flow_scope: "成员间共享匿名的医疗研究数据，涉及多国传输",
    lead_sa_rationale: "未明确说明",
    binding_mechanism: "声称通过\"联盟章程\"约束，但未提供附件也未解释法律效力",
    third_party_beneficiary: "全文未包含任何第三方受益人权利条款 — 直接违反GDPR第47(1)(b)条",
    liability_compensation: "仅泛泛提及成员根据适用法律承担责任，未指定欧盟责任主体，未承诺连带赔偿责任 — 违反GDPR第47(2)(f)条",
    transparency_notice: "未明确对外公开方式",
    training_audit: "未提及",
    cooperation_with_sa: "未明确",
    dp_safeguards: "原则性提及但无具体措施",
    third_country_assessment: "未提及",
    government_access_process: "未提及",
    update_mechanism: "未提及",
    definitions_quality: "术语体系不完整",
    review_focus: "重点审查缺失的强制性核心要素：第三方受益人权利、欧盟责任主体、法律约束力机制"
  },
  backendFilePaths: ["backend/tests/fixtures/eu/bcr_c_globaltech.docx"]
};

const bcrStructuralFailure = {
  name: "BCR-3: CloudProcessors 结构缺失与模块错误",
  description: "提交内容极度简略(仅3页)，BCR-C vs BCR-P模块混淆，缺失所有核心章节",
  jurisdiction: "EU" as const,
  formDefaults: {
    company_name: "CloudProcessors Consortium",
    group_structure: "声称是处理者联盟，为外部控制者提供云处理服务",
    applicant_entity: "（未指定）",
    data_flow_scope: "代表客户处理数据，在全球范围内传输",
    lead_sa_rationale: "未说明",
    binding_mechanism: "无",
    third_party_beneficiary: "无",
    liability_compensation: "无",
    transparency_notice: "无",
    training_audit: "无",
    cooperation_with_sa: "无",
    dp_safeguards: "仅原则性声明\"我们将保护数据\"，无具体措施",
    third_country_assessment: "无",
    government_access_process: "无",
    update_mechanism: "无",
    definitions_quality: "无定义表",
    review_focus: "结构性审查：文档类型错误（应为BCR-P非BCR-C）、缺失EDPB要求的所有核心章节、内容极度简略缺乏可执行性"
  },
  backendFilePaths: ["backend/tests/fixtures/eu/bcr_c_globaltech.docx"]
};

// ═══════════════════════════════════════════════════════════════════════════
// DPIA — 2 cases
//   来源测试文档:
//     benchmarks/source-materials/eu/legacy-docx/“DPIA草案生成”测试案例及预期输出.docx
//     resources/new/…/欧盟/任务3：“DPIA草案生成”路径描述及测试案例/“DPIA草案生成”测试案例及预期输出.docx
//     backend/tests/dpia/cases/01_health_ai.json
// ═══════════════════════════════════════════════════════════════════════════

const dpiaAIRecruitment = {
  name: dpiaAiRecruitmentScenario.display.name,
  description: dpiaAiRecruitmentScenario.display.description,
  jurisdiction: "EU" as const,
  formDefaults: {
    project_name: "AI招聘筛选与候选人评估系统",
    project_goal: "通过自动化分析求职者多维度数据（简历、视频面试、测试结果），提高招聘效率，减少人工偏见，识别最佳候选人",
    need_reason: "自动化决策与画像（可能产生法律效力）、大规模处理（>10万份/年）、特殊类别数据风险（视频面试推断种族/健康）、系统性监控",
    controller_name: "TechGiant EU Ltd",
    dpo_role: "集团DPO办公室",
    contact_channel: "dpo@techgiant.eu",
    processing_description: "数据从求职者→公司招聘网站/第三方平台→AWS欧盟服务器→AI模型分析简历、在线档案、视频面试（面部表情和语言分析）、在线测试→自动生成评分排名→返回HR系统",
    data_types: "身份信息、联系方式、教育背景、工作经历、技能证书、视频/音频记录、在线测试答案、面部特征数据、打字/点击行为数据",
    includes_special_data: true,
    subject_scale: "超过10万人/年",
    frequency: "持续处理",
    retention_period: "未成功候选人数据保留6个月，成功候选人转为员工档案",
    geo_scope: "欧盟全境",
    has_crossborder_transfer: true,
    data_source: "求职者主动提交+第三方平台同步+在线测试采集",
    relationship_context: "求职者与雇主关系",
    expectation_control: "在求职申请开始时通过弹窗明确告知AI系统使用、逻辑、后果及权利",
    vulnerable_group: "求职者（部分属于弱势群体）",
    prior_concerns: "AI招聘领域的歧视性决策已引发社会关注",
    novel_technology: "使用AI进行面部表情分析和自动评分排名属于新技术",
    lawful_basis: "同意（明确同意）+合同履行（招聘流程）+合法利益（提高效率）",
    purpose_and_necessity: "自动化筛选对海量申请是必要的，但面部表情分析的必要性存疑",
    function_creep_control: "用途变更需二次DPIA评估",
    minimization_quality: "取消微表情分析，仅分析语言内容和语调；提供非视频申请渠道",
    notice_plan: "隐私政策专项说明+实时告知AI使用、数据类型、决策逻辑、后果和权利",
    rights_support: "支持人工复核决策、数据访问、更正、删除",
    processor_management: "AI模型供应商为处理者，已签订DPA",
    risk_assessment: "高风险：歧视性决策（高可能性/高影响）、数据泄露（中/高）、决策不透明（高/高）、跨境传输风险（中/高）、过度监控（高/高）",
    mitigation_measures: "每季度公平性审计、开发决策解释功能、取消实时面部表情分析、实施第三方公平性审计",
    residual_risk: "需在实施前通过第三方公平性审计和决策解释功能上线后才能接受",
    signoff_owner: "Dr. Emma Schmidt，首席数据保护官",
    dpo_advice: "有条件同意：必须通过公平性审计、决策解释功能上线、获得DPA肯定意见",
    review_schedule: "实施6个月后全面复审",
    attachment_role: "data_flow_diagram"
  },
  backendFilePaths: ["resources/legal/sources/eu/references/2.2 ICO_DPIA_Temple.docx"]
};

const dpiaSmartCity = {
  name: dpiaSmartCityScenario.display.name,
  description: dpiaSmartCityScenario.display.description,
  jurisdiction: "EU" as const,
  formDefaults: {
    project_name: "市中心商业区人群动态智能分析系统",
    project_goal: "通过多源数据融合分析实时掌握公共空间人群动态，优化城市规划、提升公共安全应急响应、为商家提供客流洞察",
    need_reason: "大规模系统监控（公共空间持续跟踪）、大规模处理（日均30-50万人）、数据匹配与关联（可能重识别个人）、可能妨碍权利行使（集会自由、匿名权的寒蝉效应）",
    controller_name: "智慧城市管理局",
    dpo_role: "市DPO办公室",
    contact_channel: "dpo@smartcity.eu",
    processing_description: "摄像头→视频流（本地边缘服务器实时分析生成匿名化人数/流向数据）→中心平台；Wi-Fi/信令数据→匿名设备ID→中心平台与商业数据（去标识化）关联分析",
    data_types: "视频元数据（人数、运动矢量）、匿名设备标识符（MAC地址哈希、IMSI哈希）、时间戳、位置坐标、与POS系统关联的匿名消费记录",
    includes_special_data: false,
    subject_scale: "日均30-50万人",
    frequency: "持续处理",
    retention_period: "原始视频流保留72小时，匿名统计数据永久保留",
    geo_scope: "市中心商业区",
    has_crossborder_transfer: false,
    data_source: "公共空间自动采集（摄像头、Wi-Fi探针、移动网络信令）",
    relationship_context: "无直接关系（在公共空间被动采集）",
    expectation_control: "在公共区域设置告知标志，但个体可能无法合理预期被如此广泛地分析",
    vulnerable_group: "所有市民和游客",
    prior_concerns: "类似系统已在其他城市引发隐私争议",
    novel_technology: "多源数据融合分析和设备指纹重识别属于新技术",
    lawful_basis: "公共利益（城市规划与公共安全）+合法利益（经济发展）",
    purpose_and_necessity: "人群管理对公共安全是必要的，但商业推广用途的必要性需额外论证",
    function_creep_control: "商业推广用途需单独评估和审批",
    minimization_quality: "边缘计算匿名化处理、数据最小化提取",
    notice_plan: "在监控区域设置告知标志+市政府网站专项说明",
    rights_support: "由于数据匿名化处理，个体权利行使受限（需建立配套机制）",
    processor_management: "系统集成商和设备供应商均为处理者",
    risk_assessment: "中高风险：大规模监控（高可能性/高影响）、数据重识别（中/高）、寒蝉效应（中/高）、商业用途目的漂移（中/中）",
    mitigation_measures: "边缘计算匿名化、数据最小化、严格的用途限制和访问控制、定期隐私影响复审",
    residual_risk: "需持续复核，特别是在技术能力提升导致重识别风险增加时",
    signoff_owner: "市长或市政委员会",
    dpo_advice: "建议：有条件同意。需确保：1)商业用途需单独法律基础 2)建立独立监督机制 3)定期公开发布透明度报告",
    review_schedule: "每年复审",
    attachment_role: "data_flow_diagram"
  },
  backendFilePaths: ["resources/legal/sources/eu/references/2.2 ICO_DPIA_Temple.docx"]
};

// ═══════════════════════════════════════════════════════════════════════════
// TIA — 2 cases (from docx extraction)
//   来源测试文档:
//     benchmarks/source-materials/eu/legacy-docx/“TIA草案生成”测试案例及预期输出.docx
//     resources/new/…/欧盟/任务4：“TIA草案生成”路径描述及测试案例/“TIA草案生成”测试案例及预期输出.docx
//     benchmarks/datasets/seed-cases-v1/_source/task6/task6_case1.docx
//     backend/tests/tia/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const tiaBasicSCC = {
  name: innovateUsTiaScenario.display.name,
  description: innovateUsTiaScenario.display.description,
  jurisdiction: "EU" as const,
  formDefaults: sharedTiaFormDefaults(innovateUsTiaRequest),
  backendFilePaths: ["resources/legal/sources/eu/references/TIA - Template.docx"]
};

const tiaChinaBCR = {
  name: leidenIndiaTiaScenario.display.name,
  description: leidenIndiaTiaScenario.display.description,
  jurisdiction: "EU" as const,
  formDefaults: sharedTiaFormDefaults(leidenIndiaTiaRequest),
  backendFilePaths: ["resources/legal/sources/eu/references/TIA - Template.docx"]
};

// ═══════════════════════════════════════════════════════════════════════════
// PIPIA — 3 cases (from shared scenarios, source_exact)
//   来源测试文档:
//     benchmarks/source-materials/cn/legacy-docx/“认证_标准合同路径”测试案例及预期输出.docx
//     resources/new/…/中国/任务3：“认证标准合同路径”路径描述及测试案例/“认证_标准合同路径”测试案例及预期输出.docx
//     benchmarks/cases/pipia/weilan_hr_exemption_us/scenario.json
//     benchmarks/cases/pipia/zhifutong_eurocert_de/scenario.json
// ═══════════════════════════════════════════════════════════════════════════

const pipiaHaitaoMarketing = {
  name: haitaoMarketingScenario.display.name,
  description: haitaoMarketingScenario.display.description,
  jurisdiction: "CN" as const,
  formDefaults: sharedPipiaFormDefaults(haitaoMarketingRequest),
  backendFilePaths: haitaoMarketingRequest.attachments?.map((a: any) => a.storage_uri) ?? [],
};

const pipiaWeilanHr = {
  name: weilanHrScenario.display.name,
  description: weilanHrScenario.display.description,
  jurisdiction: "CN" as const,
  formDefaults: sharedPipiaFormDefaults(weilanHrRequest),
  backendFilePaths: weilanHrRequest.attachments?.map((a: any) => a.storage_uri) ?? [],
};

const pipiaZhifutongEurocert = {
  name: zhifutongEurocertScenario.display.name,
  description: zhifutongEurocertScenario.display.description,
  jurisdiction: "CN" as const,
  formDefaults: sharedPipiaFormDefaults(zhifutongEurocertRequest),
  backendFilePaths: zhifutongEurocertRequest.attachments?.map((a: any) => a.storage_uri) ?? [],
};

// ═══════════════════════════════════════════════════════════════════════════
// US 14117 — 2 cases (from docx extraction)
//   来源测试文档:
//     benchmarks/source-materials/us/legacy-docx/“14117行政令合规”测试案例及预期输出.docx
//     resources/new/…/美国/任务1：“14117行政令合规”路径描述及测试案例/“14117行政令合规”测试案例及预期输出.docx
//     benchmarks/datasets/seed-cases-v1/_source/task9/task9_case1.docx
//     backend/tests/us_14117/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const us14117Basic = {
  name: genomicRedScenario.display.name,
  description: genomicRedScenario.display.description,
  jurisdiction: "US" as const,
  formDefaults: sharedUs14117FormDefaults(genomicRedRequest),
  backendFilePaths: genomicRedRequest.attachments ?? [],
};

const us14117RestrictedParty = {
  name: geolocationYellowScenario.display.name,
  description: geolocationYellowScenario.display.description,
  jurisdiction: "US" as const,
  formDefaults: sharedUs14117FormDefaults(geolocationYellowRequest),
  backendFilePaths: geolocationYellowRequest.attachments ?? [],
};

const us14117TelemetryGreen = {
  name: telemetryGreenScenario.display.name,
  description: telemetryGreenScenario.display.description,
  jurisdiction: "US" as const,
  formDefaults: sharedUs14117FormDefaults(telemetryGreenRequest),
  backendFilePaths: telemetryGreenRequest.attachments ?? [],
};

// ═══════════════════════════════════════════════════════════════════════════
// CN Flow (中国对华流动评估) — 2 cases
//   来源测试文档:
//     resources/templates/us/4.1_cn_flow_compliance_template_v0.docx（预置输入模板）
//     backend/tests/cn_flow/cases/01_minimal.json
//   注：benchmarks/source-materials 中无独立 CN Flow 测试案例，场景来自 EO 14117 行政令相关材料
// ═══════════════════════════════════════════════════════════════════════════

const cnFlowBasic = {
  name: "CN-FLOW-1: GeneGuard 基因组数据红灯兼容请求",
  description: "复用 EO 14117 正式红灯案例，验证旧 CN Flow 请求到统一服务的兼容转换",
  jurisdiction: "US" as const,
  formDefaults: {
    company_name: "GeneGuard生物科技公司",
    transfer_purpose: "向中国上海华源生命科学有限公司提供美国志愿者全基因组测序原始数据，用于基因标记与疾病关联联合研究",
    data_categories: "全基因组测序原始数据",
    sensitive_data_flags: "",
    us_person_count: 10000,
    transaction_type: "cooperative_research",
    doj_data_category: "human_genomic_data",
    transfer_chain: "GeneGuard加州精准医疗事业部→华源生命科学有限公司（中国上海）",
    data_volume_note: "10,000名美国志愿者，超过人类基因组数据批量阈值",
    necessity_justification: "联合研究用于分析基因标记与疾病关联性",
    primary_recipient_name: "华源生命科学有限公司",
    primary_recipient_country: "中国",
    primary_recipient_role: "affiliate",
    primary_recipient_restricted: true,
    additional_recipients: ""
  },
  backendFilePaths: [
    "backend/tests/fixtures/cn/cn_flow_data_inventory.csv",
    "backend/tests/fixtures/cn/cn_flow_entity_inventory.csv",
  ]
};

const cnFlowRestricted = {
  name: "CN-FLOW-2: GeneGuard 位置数据黄灯兼容请求",
  description: "复用 EO 14117 正式黄灯案例，验证旧 CN Flow 请求到统一服务的兼容转换",
  jurisdiction: "US" as const,
  formDefaults: {
    company_name: "GeneGuard生物科技公司",
    transfer_purpose: "通过供应商协议向北京深度洞察人工智能有限公司提供匿名化精确位置轨迹，用于健康预测模型训练",
    data_categories: "精确位置轨迹数据",
    sensitive_data_flags: "",
    us_person_count: 150000,
    transaction_type: "vendor_agreement",
    doj_data_category: "precise_geolocation_data",
    transfer_chain: "GeneGuard健康地理分析部测试环境→深度洞察人工智能有限公司（中国北京）",
    data_volume_note: "150,000名美国人，超过精确地理位置数据批量阈值",
    necessity_justification: "用于优化环境因素与健康影响的 AI 预测模型",
    primary_recipient_name: "深度洞察人工智能有限公司",
    primary_recipient_country: "中国",
    primary_recipient_role: "vendor",
    primary_recipient_restricted: true,
    additional_recipients: "",
    internal_access_note: "中国籍数据科学家张伟、王芳可访问 GeneGuard 测试环境；隔离和全量日志措施尚待落实"
  },
  backendFilePaths: [
    "backend/tests/fixtures/cn/cn_flow_data_inventory.csv",
    "backend/tests/fixtures/cn/cn_flow_entity_inventory.csv",
  ]
};


// ═══════════════════════════════════════════════════════════════════════════
// Document Review — 2 cases
//   来源测试文档:
//     benchmarks/source-materials/cn/legacy-docx/“文档专项智能审查”功能说明与路径描述.docx
//     resources/new/…/中国/任务4：“文档专项智能审查”路径描述及测试案例/“文档专项智能审查”测试案例及预期输出/“文档专项智能审查”测试案例及预期输出.docx
//     backend/tests/review/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const reviewPrivacyPolicy = {
  name: reviewDataSecurityScenario.display.name,
  description: reviewDataSecurityScenario.display.description,
  jurisdiction: "CN" as const,
  formDefaults: {
    company_name: "金陵科技学院信息化建设与管理处",
    publisher_entity: "金陵科技学院信息化建设与管理处",
    document_title: "数据安全及保密协议",
    document_version: "2025-10-15模板",
    effective_date: "2025-10-15",
    applicable_products: "校园一卡通系统数据分析和运维",
    applicable_scope: "甲方委托云途信息技术有限公司进行校园一卡通数据分析和运维，乙方平台服务器位于海外",
    is_live_version: true,
    document_type: "dpa",
    receiver_name: "云途信息技术有限公司",
    receiver_country: "新加坡",
    transfer_purpose: "校园一卡通系统数据分析、运维及可能的境外平台处理",
    processor_identity_disclosed: true,
    scope_disclosed: true,
    collection_purpose_disclosed: true,
    processing_method_disclosed: true,
    category_disclosed: true,
    sensitive_pi_disclosed: false,
    crossborder_rule_disclosed: false,
    rights_channel_disclosed: false,
    contact_channel: "待补充",
    pii_count: 0,
    spi_count: 0,
    has_scc_draft: false,
    review_focus: "重点核查跨境传输告知的完整性、敏感信息处理的合法性基础、用户权利行使路径与联系方式的披露"
  },
  backendFilePaths: [
    "backend/tests/fixtures/cn/data_security_agreement.docx",
  ]
};

const reviewSccContract = {
  name: "审查-2: 智付通科技有限公司（个人信息出境标准合同）",
  description: "审查与新加坡支付网关服务商签订的个人信息出境标准合同草案，核查条款完整性、再委托、通知时限和数据主体权利保障",
  jurisdiction: "CN" as const,
  formDefaults: {
    company_name: "智付通科技有限公司",
    publisher_entity: "智付通科技有限公司",
    document_title: "个人信息出境标准合同",
    document_version: "标准化补充整合草案",
    effective_date: "",
    applicable_products: "跨境支付与结算解决方案",
    applicable_scope: "向新加坡支付网关服务商传输中国用户支付交易信息用于风险筛查和结算处理",
    is_live_version: false,
    document_type: "scc_contract",
    receiver_name: "星洲支付处理有限公司 (Starstate Payment Processing Pte. Ltd.)",
    receiver_country: "新加坡",
    transfer_purpose: "跨境支付交易的风险筛查、欺诈监测、合规审计及资金结算所必需的数据处理服务",
    processor_identity_disclosed: true,
    scope_disclosed: true,
    collection_purpose_disclosed: true,
    processing_method_disclosed: true,
    category_disclosed: true,
    sensitive_pi_disclosed: true,
    crossborder_rule_disclosed: true,
    rights_channel_disclosed: true,
    contact_channel: "法务合规与数据保护负责人（待合同定稿后确认）",
    pii_count: 500000,
    spi_count: 500000,
    has_scc_draft: true,
    review_focus:
      "重点审查个人信息出境标准合同条款完整性、双方义务、再委托限制、删除与留存规则、安全事件通知时限、监管报告表述、以及个人信息主体权利保障机制"
  },
  backendFilePaths: [
    "resources/legal/sources/cn/references/个人信息出境标准合同【模板】.docx",
  ]
};

// ═══════════════════════════════════════════════════════════════════════════
// Exported registry
// ═══════════════════════════════════════════════════════════════════════════

export const DEV_TEST_CASES = {
  cpra: defineDevCases("cpra", [cpraTrendyGoods, cpraDataFlow, cpraFitLife]),
  diagnosis: defineDevCases("diagnosis", [diagEcommerce, diagMedical, diagAnonymous]),
  assessment: defineDevCases("assessment", [assessCIO, assessEcommerce]),
  eu_scc: defineDevCases("eu_scc", [euSccBasic, euSccHealthIndia, euSccModuleError]),
  bcr: defineDevCases("bcr", [bcrMediumRisk, bcrHighRisk, bcrStructuralFailure]),
  dpia: defineDevCases("dpia", [dpiaAIRecruitment, dpiaSmartCity]),
  tia: defineDevCases("tia", [tiaBasicSCC, tiaChinaBCR]),
  pipia: defineDevCases("pipia", [pipiaHaitaoMarketing, pipiaWeilanHr, pipiaZhifutongEurocert]),
  review: defineDevCases("review", [reviewPrivacyPolicy, reviewSccContract]),
  cn_flow: defineDevCases("cn_flow", [cnFlowBasic, cnFlowRestricted]),
  us_14117: defineDevCases("us_14117", [us14117Basic, us14117RestrictedParty, us14117TelemetryGreen]),
} satisfies { [Module in DevCaseModule]: DevTestCase<Module>[] };

export const MODULES_WITH_CASES = Object.keys(DEV_TEST_CASES) as DevCaseModule[];

export function getTestCases<Module extends DevCaseModule>(
  module: Module,
): (typeof DEV_TEST_CASES)[Module] {
  return DEV_TEST_CASES[module];
}

const DEFAULT_CASE_INDEX: Partial<Record<DevCaseModule, number>> = {
  diagnosis: 2,
  assessment: 1,
  review: 1,
};

export function getDefaultTestCase<Module extends DevCaseModule>(
  module: Module,
): (typeof DEV_TEST_CASES)[Module][number] | null {
  const cases = getTestCases(module);
  if (cases.length === 0) return null;
  const preferredIndex = DEFAULT_CASE_INDEX[module] ?? 0;
  return cases[preferredIndex] ?? cases[0] ?? null;
}
