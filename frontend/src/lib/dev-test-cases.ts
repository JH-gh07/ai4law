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
//     resources/new/…/种子案例及测试结果/任务10（CPRA 合规）种子案例及测试结果/任务10_案例1_测试结果.docx
//     backend/tests/cpra/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const cpraTrendyGoods = {
  name: "CPRA-1: TrendyGoods 电商平台",
  description: "中型电商，年收入30M，缺少opt-out机制，Cookie暗模式，广告合同不合规",
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
//     resources/new/…/种子案例及测试结果/任务1（合规路径诊断）种子案例及测试结果/任务1_案例1_测试结果.docx
//     backend/tests/diagnosis/cases/01_scc_path.json
// ═══════════════════════════════════════════════════════════════════════════

const diagEcommerce = {
  name: "诊断-1: 跨境优品 电商（标准合同/认证路径）",
  description: "中型跨境电商，不涉及重要数据，非CIIO，出境45万一般个人信息→触发标准合同/认证路径",
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
  name: "诊断-2: 前沿生命科技 医疗研究（安全评估路径）",
  description: "研究机构出境1.5万患者医疗数据（可能涉及重要数据）→触发安全评估路径，测试'不知道'辅助判断",
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
  name: "诊断-3: 智驾未来 匿名车辆传感器数据（豁免路径）",
  description: "自动驾驶公司向德国母公司提供完全匿名化车辆传感器数据，不涉及个人信息，验证豁免路径",
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
//     resources/new/…/种子案例及测试结果/任务2（安全评估路径）种子案例及测试结果/任务2_案例1_测试结果.docx
//     backend/tests/assessment/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const assessCIO = {
  name: "评估-1: 东方信托 CIIO金融机构",
  description: "CIIO信托公司向香港母公司传输交易数据和客户信息，含重要数据风险，法律文件缺失条款",
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
  name: "评估-2: 优选购物 APP（120万用户行为数据）",
  description: "非CIIO电商平台向开曼母公司及美国下游分析商传输去标识化用户行为日志，出境人数超过100万，触发安全评估",
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
//     resources/new/…/种子案例及测试结果/任务5（SCC 审查）种子案例及测试结果/任务5_案例1_测试结果.docx
//     backend/tests/eu_scc/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const euSccBasic = {
  name: "EU-SCC-1: 法国电商 C2C→英国关联公司（补充措施缺失）",
  description: "法国电商向英国关联公司传输客户联系和订单数据，英国虽有充分性认定但下游使用美国 AWS，缺少 Schrems II 补充措施",
  jurisdiction: "EU" as const,
  formDefaults: {
    exporter_name: "EU Fashion E-commerce SAS",
    importer_name: "UK Marketing Analytics Ltd",
    importer_country: "英国",
    transfer_role: "c2c",
    scc_version: "eu_2021",
    transfer_purpose: "市场趋势分析和个性化营销",
    data_categories: "姓名、邮箱、地址、订单历史",
    data_subject_categories: "欧盟电商客户",
    transfer_frequency: "continuous",
    retention_rule: "服务协议期间加30天",
    tom_summary: "合同未针对美国 AWS 的政府访问风险配置加密、密钥控制和访问审计补充措施",
    onward_transfer_control: "英国接收方使用美国 AWS 进行处理，但 SCC 未明确约束美国下游云服务商",
    rights_and_complaint: "英国关联公司提供基本权利渠道，但未补足美国云服务商下游风险",
    has_scc_draft: true,
    has_tia: false,
    has_supplementary_measures: false,
    project_name_override: "法国电商客户数据向英国关联公司传输",
    scc_text_override: "MODULE ONE: Transfer controller to controller\n\nData exporter: EU Fashion E-commerce SAS, Paris, France (controller)\nData importer: UK Marketing Analytics Ltd, London, United Kingdom (controller)\n\nAnnex I.B - Description of transfer\nData subjects: EU e-commerce customers\nPersonal data: Name, email, address, and order history\nPurpose: Market trend analysis and personalised marketing\nFrequency: Continuous\n\nOnward transfer: The UK importer uses Amazon Web Services in the United States for processing and storage.\n\nRisk: The parties have not documented a Schrems II transfer impact assessment or effective supplementary measures for the US onward transfer, including encryption and exporter-held key controls."
  },
  backendFilePaths: ["backend/tests/fixtures/eu/scc_2021_en.md"]
};

const euSccHealthIndia = {
  name: "EU-SCC-2: 健康数据→印度 高风险修改",
  description: "德国健康研究公司→印度分析公司，Clause 15被修改，特殊类别数据分类错误，缺少补充措施",
  jurisdiction: "EU" as const,
  formDefaults: {
    exporter_name: "Gesundheitsforschung GmbH",
    importer_name: "Data Insights Solutions Pvt. Ltd.",
    importer_country: "印度",
    transfer_role: "c2p",
    scc_version: "eu_2021",
    transfer_purpose: "医疗研究数据统计分析",
    data_categories: "患者研究编号、年龄组、性别、诊断代码、治疗代码、实验室检测结果",
    data_subject_categories: "医疗研究参与患者",
    transfer_frequency: "periodic",
    retention_rule: "研究项目结束后按法规要求保留",
    tom_summary: "数据传输加密，但Clause 15政府请求通知条款被非法修改为\"as soon as legally permissible\"",
    onward_transfer_control: "子处理者变更通过邮件通知，15个工作日无异议即可启用",
    rights_and_complaint: "数据主体权利机制需配套完善",
    government_access_response: "Clause 15修改削弱了政府访问透明度义务",
    supplementary_clause_review: "需要重点审查Clause 15修改的有效性、SPI分类错误、以及印度法律环境下的补充措施需求",
    has_scc_draft: true,
    has_tia: false,
    has_supplementary_measures: false,
    project_name_override: "德国医疗研究数据向印度统计分析传输",
    scc_text_override: "MODULE TWO: Transfer controller to processor\n\nData exporter: Gesundheitsforschung GmbH, Berlin, Germany (controller)\nData importer: Data Insights Solutions Pvt. Ltd., Bangalore, India (processor)\n\nClause 9: Use of sub-processors\nThe data importer shall submit planned changes to its list of sub-processors by email. If the data exporter does not object in writing within fifteen (15) business days, the data importer may engage the new sub-processor.\n\nClause 14(c) - modified from standard text\nThe data importer shall provide the documented assessment and suitable safeguards only upon a specific, justified request.\n\nClause 15(a) - modified from standard text\nThe data importer shall notify the data exporter as soon as legally permissible after a legally binding public-authority request and may provide relevant information at its discretion.\n\nAnnex I.B - Description of transfer\nCategories of personal data: Patient unique study identifier (pseudonymised), age group, gender, diagnostic codes, treatment codes, and laboratory test results (anonymised).\nSensitive data transferred: Not applicable. The patient health data is anonymised for research purposes and does not constitute special categories of data."
  },
  backendFilePaths: ["backend/tests/fixtures/eu/scc_2021_en.md"]
};

const euSccModuleError = {
  name: "EU-SCC-3: 多方加入 模块选择错误",
  description: "C→P→Sub-P三层关系误选Module Two(C2P)，应为Module Three(P2P)，加入方信息缺失",
  jurisdiction: "EU" as const,
  formDefaults: {
    exporter_name: "Orange Cloud BV",
    importer_name: "Balkan IT Support DOO",
    importer_country: "塞尔维亚",
    transfer_role: "c2p",
    scc_version: "eu_2021",
    transfer_purpose: "客户支持工单数据转委托给塞尔维亚子处理者。实际链：控制者(北欧零售集团)→处理者(Orange Cloud)→子处理者(Balkan IT) — 应为Module Three",
    data_categories: "客户姓名、问题描述、联系信息",
    data_subject_categories: "北欧零售集团客户",
    transfer_frequency: "continuous",
    retention_rule: "工单解决后按主服务协议保留",
    tom_summary: "标准安全措施，但缺少针对子处理者授权的完整合规框架",
    onward_transfer_control: "子处理者授权链不完整，加入方信息仅引用外部文件",
    supplementary_clause_review: "核心缺陷：模块选择根本性错误（应为Module Three而非Module Two）、加入方信息缺失、授权链不完整",
    has_scc_draft: true,
    has_tia: false,
    has_supplementary_measures: false,
    project_name_override: "客户支持工单子处理",
    scc_text_override: "MODULE TWO: Transfer controller to processor (ERROR - should be Module Three)\n\nData exporter: Orange Cloud BV (processor acting on behalf of Nordic Retail Group, the controller)\nData importer: Orange Cloud BV (incorrect - double role assignment)\nSub-processor: Balkan IT Support DOO, Belgrade, Serbia\n\nClause 7: Docking clause\nAn entity that is not a Party to these Clauses may, with the agreement of the Parties, accede to these Clauses at any time, either as a data exporter or as a data importer, by completing the Annexes and signing Annex I.A.\n\nAnnex I.A: Nordic Retail Group (controller) details marked as 'See Master Service Agreement' with no address or contact information filled in.\n\nClause 9: Data importer may engage sub-processors after notification. No requirement for specific written authorization from controller."},
  backendFilePaths: ["backend/tests/fixtures/eu/scc_2021_en.md"]
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
  name: "DPIA-1: AI招聘筛选系统",
  description: "跨国科技公司AI招聘系统，大规模处理+自动决策+特殊数据推断风险+跨境传输",
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
  name: "DPIA-2: 智能城市人群分析系统",
  description: "城市管理局公共场所人群监控系统，大规模监控+数据关联重识别风险+寒蝉效应",
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
//     resources/new/…/种子案例及测试结果/任务6（TIA 审查）种子案例及测试结果/任务6_案例1_测试结果.docx
//     backend/tests/tia/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const tiaBasicSCC = {
  name: "TIA-1: 德国公司→美国 SaaS 高风险评估",
  description: "德国创新软件公司将 CRM 迁移至美国 SaaS，评估 FISA 702/CLOUD Act 与补充措施",
  jurisdiction: "EU" as const,
  formDefaults: {
    data_exporter_name: "Innovate Software GmbH，注册于德国柏林，角色：数据控制者",
    data_importer_name: "CloudForce Inc.，位于美国，提供 CRM SaaS 平台，角色：数据处理者",
    importer_country_region: "美国",
    transfer_purpose: "将全部客户关系管理（CRM）系统迁移至美国 SaaS 平台",
    data_categories: "欧盟客户联系信息、交易记录",
    sensitive_data_description: "不含特殊类别数据",
    data_subject_categories: "欧盟客户",
    transfer_frequency: "continuous",
    transfer_tool: "scc" as const,
    law_assessed: true,
    law_findings: "美国 FISA 702 和 CLOUD Act 可能允许政府访问 SaaS 数据，依据 Schrems II 需要评估其对 SCC 有效性的影响",
    pre_effectiveness: "仅依赖 SCC 不能消除美国政府访问风险，初步结论为可能无效",
    supplementary_technical: "传输前端到端加密，密钥仅由德国出口方本地管理",
    supplementary_contractual: "CloudForce 作出政府请求透明度和抵抗非法访问的合同承诺",
    supplementary_organizational: "独立安全审计、访问控制、密钥管理验证和事件响应流程",
    post_effectiveness: "在加密、出口方密钥管理和合同承诺持续有效并通过审计的前提下，传输可进行",
    key_actions: "完成第三方安全审计、签署补充合同、验证密钥控制",
    dpo_opinion: "有条件同意，前提是完成安全审计并签署补充合同",
    review_date: "2026-07-01",
    attachment_role: "country_law_analysis"
  },
  backendFilePaths: ["resources/legal/sources/eu/references/TIA - Template.docx"]
};

const tiaChinaBCR = {
  name: "TIA-2: 荷兰→印度临床试验数据高风险评估",
  description: "荷兰生命科学研究所向印度临床研究公司传输可重新识别的健康和基因数据",
  jurisdiction: "EU" as const,
  formDefaults: {
    data_exporter_name: "Leiden Life Sciences Institute，位于荷兰，角色：数据控制者",
    data_importer_name: "New Delhi Clinical Research Pvt. Ltd.，位于印度，角色：数据处理者",
    importer_country_region: "印度",
    transfer_purpose: "药物临床试验数据分析",
    data_categories: "匿名化但可重新识别的健康数据、基因组序列片段",
    sensitive_data_description: "健康数据和基因数据属于极敏感数据，需要额外保护",
    data_subject_categories: "荷兰临床试验受试者",
    transfer_frequency: "periodic",
    transfer_tool: "scc" as const,
    law_assessed: true,
    law_findings: "印度 IT Act第69条体现政府访问风险，印度属于高风险目的地，初步结论为 SCC 可能无效",
    pre_effectiveness: "SCC 本身不足以覆盖印度政府访问健康和基因数据的风险",
    supplementary_technical: "安全飞地、密钥分离、出口方控制密钥和严格访问控制",
    supplementary_contractual: "加强政府请求通知、用途限制和监管配合义务",
    supplementary_organizational: "临床研究访问审批、独立安全验证、DPO 风险复核",
    post_effectiveness: "在安全飞地、密钥分离和严格前提持续有效的条件下可进行，但属于高度条件化结论",
    key_actions: "取得荷兰 AP 的非正式指导或正式批准，完成安全飞地验证并设置近期复审",
    dpo_opinion: "极高风险警告，建议在实施前寻求荷兰 AP 指导或批准",
    review_date: "2026-06-01",
    attachment_role: "country_law_analysis"
  },
  backendFilePaths: ["resources/legal/sources/eu/references/TIA - Template.docx"]
};

// ═══════════════════════════════════════════════════════════════════════════
// PIPIA — 2 cases (from docx extraction)
//   来源测试文档:
//     benchmarks/source-materials/cn/legacy-docx/“认证_标准合同路径”测试案例及预期输出.docx
//     resources/new/…/中国/任务3：“认证标准合同路径”路径描述及测试案例/“认证_标准合同路径”测试案例及预期输出.docx
//     resources/new/…/种子案例及测试结果/任务3（标准合同路径）种子案例及测试结果/任务3_案例1_测试结果.docx
//     backend/tests/pipia/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const pipiaSCCFiling = {
  name: "PIPIA-1: 海淘优选会员营销数据标准合同路径",
  description: "海淘优选向新加坡子公司传输50万高价值会员营销数据，存在敏感属性识别和告知同意缺口",
  jurisdiction: "CN" as const,
  formDefaults: {
    company_name: "海淘优选（杭州）科技有限公司",
    company_uscc: "待补充统一社会信用代码",
    industry: "电商零售",
    shareholding_structure: "资料未提供",
    actual_controller: "资料未提供",
    overseas_investment: "新加坡全资子公司 SeaCommerce Pte. Ltd.",
    org_structure_privacy_team: "资料未提供",
    business_overview: "面向中国消费者的跨境电商平台，注册会员800万",
    processing_activity_overview: "筛选约50万年消费超万元的高价值会员，用于个性化推荐、精准营销和区域市场分析",
    is_ciio: false,
    processing_person_count: 8000000,
    outbound_pi_count: 500000,
    outbound_spi_count: 0,
    route_type: "scc_filing" as const,
    outbound_scenario_name: "高价值会员营销数据同步至新加坡亚太运营中心",
    outbound_frequency: "periodic",
    transfer_method: "加密 API 同步",
    domestic_storage: "杭州阿里云 RDS 数据库",
    overseas_storage: "新加坡 AWS Redshift 数据仓库",
    transfer_link: "杭州阿里云 RDS→加密 API→新加坡 AWS Redshift",
    purpose: "为高价值会员提供个性化商品推荐和营销活动，并开展区域市场分析",
    recipient_name: "SeaCommerce Pte. Ltd.",
    recipient_country_region: "新加坡",
    legal_basis: "用户单独同意+履行个性化服务合同所必需",
    legality_justification: "隐私政策仅写向关联公司共享用于营销，未明确 SeaCommerce 名称和所在地；批量同意记录不完整",
    necessity_justification: "个性化服务作为合同必要性的论证较宽泛，字段范围仍需精简",
    pi_categories: "Hashed_Device_ID,Product_Category_Preference,Browsing_History,Order_Summary",
    spi_categories: "",
    subject_volume: 500000,
    notice_mechanism: "隐私政策仅笼统写明关联公司，未明确新加坡接收方名称和所在地",
    consent_mechanism: "仅有单条同意记录截图，未提供覆盖50万目标用户的批量记录或统计报告",
    dsar_channel: "待补充个人信息主体权利请求渠道",
    retention_policy: "资料未提供，需补充最短必要保存期限",
    incident_response_sla_hours: 24,
    escalation_path: "资料未提供，需补充安全事件处置和上报流程",
    attachment_role: "scc_contract"
  },
  backendFilePaths: [
    "resources/legal/sources/cn/references/个人信息出境标准合同【模板】.docx",
  ]
};

const pipiaCertification = {
  name: "PIPIA-2: 智付通向 EuroCert 提交商户资料",
  description: "智付通为欧盟支付业务认证向德国 EuroCert 提供约5万商户资料，认证机构资格和法律基础存疑",
  jurisdiction: "CN" as const,
  formDefaults: {
    company_name: "智付通科技有限公司",
    company_uscc: "待补充统一社会信用代码",
    industry: "金融科技",
    shareholding_structure: "资料未提供",
    actual_controller: "资料未提供",
    overseas_investment: "资料未提供",
    org_structure_privacy_team: "资料未提供",
    business_overview: "提供跨境支付技术，计划拓展欧盟业务",
    processing_activity_overview: "向欧盟认证机构提供商户基本信息和交易概况以申请支付服务认证",
    is_ciio: false,
    processing_person_count: 50000,
    outbound_pi_count: 50000,
    outbound_spi_count: 0,
    route_type: "certification" as const,
    outbound_scenario_name: "向 EuroCert 提交欧盟支付服务认证资料",
    outbound_frequency: "one_time",
    transfer_method: "安全邮件和加密链接手动传输",
    domestic_storage: "资料未提供",
    overseas_storage: "EuroCert 认证业务系统，具体位置待补充",
    transfer_link: "中国境内→安全邮件/加密链接→德国 EuroCert",
    purpose: "满足欧盟监管机构对支付服务商的尽职调查和合规认证要求",
    recipient_name: "EuroCert",
    recipient_country_region: "德国",
    legal_basis: "履行法定义务（欧盟认证要求）+商户合同授权",
    legality_justification: "未提供欧盟认证要求的具体条款，将其等同于中国法下法定义务存在争议",
    necessity_justification: "需区分欧盟业务准入认证与中国个人信息出境认证，当前 EuroCert 的中国认可资质未证明",
    pi_categories: "Merchant_Name,Business_Registration_Number,Contact_Email,Contact_Name,Monthly_Txn_Volume_Band",
    spi_categories: "",
    subject_volume: 50000,
    notice_mechanism: "资料未提供，需补充对商户联系人个人信息出境的明确告知",
    consent_mechanism: "声称商户合同已授权，但未提供可核验授权条款",
    dsar_channel: "待补充中国个人信息主体权利请求渠道",
    retention_policy: "认证服务合同未明确中国个人信息主体保护和必要保存期限",
    incident_response_sla_hours: 24,
    escalation_path: "资料未提供，需补充跨境事件处置和监管上报流程",
    attachment_role: "certification_material"
  },
  backendFilePaths: [
    "resources/legal/sources/cn/references/个人信息出境标准合同【模板】.docx",
  ]
};

// ═══════════════════════════════════════════════════════════════════════════
// US 14117 — 2 cases (from docx extraction)
//   来源测试文档:
//     benchmarks/source-materials/us/legacy-docx/“14117行政令合规”测试案例及预期输出.docx
//     resources/new/…/美国/任务1：“14117行政令合规”路径描述及测试案例/“14117行政令合规”测试案例及预期输出.docx
//     resources/new/…/种子案例及测试结果/任务9（14117 行政令合规）种子案例及测试结果/任务9_案例1_测试结果.docx
//     backend/tests/us_14117/cases/01_minimal.json
// ═══════════════════════════════════════════════════════════════════════════

const us14117Basic = {
  name: "14117-1: GeneGuard→华源生命科学基因组数据（红灯）",
  description: "GeneGuard 向中国国资控股的华源生命科学传输1万名美国人的全基因组数据，禁止传输",
  jurisdiction: "US" as const,
  formDefaults: {
    company_name: "GeneGuard生物科技公司",
    project_name: "与华源生命科学联合研究",
    transaction_description: "加州精准医疗事业部向中国上海华源生命科学有限公司传输10,000名美国志愿者的全基因组测序数据，用于基因标记与疾病关联研究",
    transaction_type: "cooperative_research",
    data_item_name: "人类全基因组测序数据",
    data_description: "10,000名美国志愿者的全基因组测序原始数据",
    doj_data_category: "human_genomic_data",
    us_person_count: 10000,
    entity_name: "华源生命科学有限公司",
    country_of_registration: "中国",
    government_control: true,
    entity_role: "research_institution" as const,
    onward_transfer: false,
    onward_transfer_description: "",
    security_measures_summary: "拟传输原始全基因组数据，现有措施不能消除其不可逆敏感性",
    review_focus: "重点核查基因组数据阈值、被覆盖人员和研究合作豁免",
    data_items_override: [
      { data_item_name: "全基因组测序原始数据", data_description: "10,000名美国志愿者的全基因组测序数据", is_personal_info: true, is_sensitive_personal_info: true, us_person_count: 10000, doj_data_category: "human_genomic_data", precision_level: "raw" }
    ],
    recipient_entities_override: [
      { entity_name: "华源生命科学有限公司", country_of_registration: "中国（上海）", entity_role: "research_institution" as const, government_control: true, is_covered_person: true }
    ],
    security_measures_override: [
      { measure_name: "改为聚合分析结果", category: "data_minimization", status: "missing", description: "当前仍计划传输原始全基因组测序数据" }
    ]
  },
  backendFilePaths: [
    "backend/tests/fixtures/us/us14117_data_inventory.csv",
    "backend/tests/fixtures/us/us14117_entity_inventory.csv",
  ],
};

const us14117RestrictedParty = {
  name: "14117-2: GeneGuard→深度洞察位置数据（黄灯）",
  description: "GeneGuard 向中国深度洞察人工智能有限公司提供15万名美国人的精确位置数据，需采取安全措施",
  jurisdiction: "US" as const,
  formDefaults: {
    company_name: "GeneGuard生物科技公司",
    project_name: "健康地理分析 AI 模型训练",
    transaction_description: "健康地理分析部通过供应商协议向北京深度洞察人工智能有限公司提供150,000名美国人的匿名化精确位置轨迹，用于健康预测模型训练",
    transaction_type: "vendor_agreement",
    data_item_name: "匿名化精确位置轨迹数据",
    data_description: "150,000名美国人的精确 GPS 位置轨迹数据，用于 AI 预测模型训练",
    doj_data_category: "precise_geolocation_data",
    us_person_count: 150000,
    entity_name: "深度洞察人工智能有限公司",
    country_of_registration: "中国",
    government_control: false,
    entity_role: "vendor" as const,
    onward_transfer: false,
    onward_transfer_description: "",
    security_measures_summary: "隔离工作区、访问控制、日志审计和季度审计尚待落实",
    review_focus: "重点核查被覆盖人员、限制性供应商协议和两名中国员工的实际访问",
    data_items_override: [
      { data_item_name: "精确位置轨迹", data_description: "150,000名美国人的实时精确位置轨迹（GPS）数据", is_personal_info: true, is_sensitive_personal_info: true, us_person_count: 150000, doj_data_category: "precise_geolocation_data", precision_level: "raw" }
    ],
    recipient_entities_override: [
      { entity_name: "深度洞察人工智能有限公司", country_of_registration: "中国（北京）", entity_role: "vendor" as const, is_covered_person: true }
    ],
    access_persons_override: [
      { person_name: "张伟", nationality: "中国", country_of_residence: "中国", department: "算法研发部", position: "高级数据科学家", has_actual_access: true, access_type: "remote" },
      { person_name: "王芳", nationality: "中国", country_of_residence: "中国", department: "算法研发部", position: "数据科学家", has_actual_access: true, access_type: "remote" }
    ],
    security_measures_override: [
      { measure_name: "数据隔离工作区", category: "access_control", status: "missing", description: "尚未建立满足限制性交易要求的隔离环境" },
      { measure_name: "访问审计日志", category: "audit_logging", status: "missing", description: "尚未完成全量日志记录和季度审计机制" }
    ]
  },
  backendFilePaths: [
    "backend/tests/fixtures/us/us14117_data_inventory.csv",
    "backend/tests/fixtures/us/us14117_entity_inventory.csv",
  ],
};

// ═══════════════════════════════════════════════════════════════════════════
// CN Flow (中国对华流动评估) — 2 cases
//   来源测试文档:
//     resources/templates/us/4.1_cn_flow_compliance_template_v0.docx（预置输入模板）
//     backend/tests/cn_flow/cases/01_minimal.json
//   注：benchmarks/source-materials 中无独立 CN Flow 测试案例，场景来自 EO 14117 行政令相关材料
// ═══════════════════════════════════════════════════════════════════════════

const cnFlowBasic = {
  name: "CN-FLOW-1: 基础对华数据流动评估",
  description: "美国电商平台向中国供应商传输订单数据，审查受限主体和敏感数据类别",
  jurisdiction: "US" as const,
  formDefaults: {
    company_name: "GlobalShop Inc.",
    transfer_purpose: "向中国供应商传输订单信息用于商品生产和物流配送",
    data_categories: "客户姓名,收货地址,联系电话,商品订单号,SKU信息",
    sensitive_data_flags: "无敏感信息",
    us_person_count: 100000,
    transaction_type: "vendor_agreement",
    doj_data_category: "covered_personal_identifiers",
    transfer_chain: "美国总部→AWS美东区→通过加密API→中国供应商ERP系统。传输频率：每日实时",
    primary_recipient_name: "深圳智能制造有限公司",
    primary_recipient_country: "中国",
    primary_recipient_role: "vendor",
    primary_recipient_restricted: false,
    additional_recipients: "广州物流供应链有限公司,中国,processor,no"
  },
  backendFilePaths: [
    "backend/tests/fixtures/cn/cn_flow_data_inventory.csv",
    "backend/tests/fixtures/cn/cn_flow_entity_inventory.csv",
  ]
};

const cnFlowRestricted = {
  name: "CN-FLOW-2: 受限主体+敏感数据",
  description: "美国半导体公司向中国受限实体传输技术数据，涉及出口管制和高风险数据类别",
  jurisdiction: "US" as const,
  formDefaults: {
    company_name: "Advanced Semiconductor Corp.",
    transfer_purpose: "向中国合作方提供芯片设计文件用于封装测试，技术数据可能涉及出口管制分类（ECCN 3E001）",
    data_categories: "芯片设计文件（GDSII格式）,测试规范文档,良率数据报告,工程师联系信息",
    sensitive_data_flags: "出口管制技术数据,可能涉及ECCN 3E001分类",
    us_person_count: 1000,
    transaction_type: "vendor_agreement",
    doj_data_category: "not_14117_data",
    transfer_chain: "美国总部安全服务器→通过加密VPN→上海公司内部服务器→（可能）再传输至北京研究所",
    primary_recipient_name: "上海先进半导体制造有限公司",
    primary_recipient_country: "中国",
    primary_recipient_role: "vendor",
    primary_recipient_restricted: false,
    additional_recipients: "北京微电子研究所,中国,affiliate,yes",
    internal_access_note: "内部员工访问需要双重认证和项目负责人批准。所有数据访问记录审计日志。中国籍员工可能接触技术数据"
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
  name: "审查-1: 数据安全及保密协议（隐含出境风险）",
  description: "审查金陵科技学院与云途信息技术有限公司的数据安全及保密协议，检查隐含出境、敏感数据、事件时限和审计权",
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
  pipia: defineDevCases("pipia", [pipiaSCCFiling, pipiaCertification]),
  review: defineDevCases("review", [reviewPrivacyPolicy, reviewSccContract]),
  cn_flow: defineDevCases("cn_flow", [cnFlowBasic, cnFlowRestricted]),
  us_14117: defineDevCases("us_14117", [us14117Basic, us14117RestrictedParty]),
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
