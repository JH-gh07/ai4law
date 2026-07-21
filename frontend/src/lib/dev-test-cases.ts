/**
 * 开发者模式 — 预编译测试案例 JSON payload。
 *
 * 每个案例源自 benchmarks/source-materials/ 中保留的历史测试材料。
 * 选中案例后直接 POST 到对应模块的 async endpoint，配合 SSE 事件流实时观察执行。
 *
 * 用法:
 *   import { DEV_TEST_CASES, MODULES_WITH_CASES } from "./dev-test-cases";
 *   const payload = DEV_TEST_CASES.cpra[0].payload;
 */

export type DevTestCase = {
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
  payload: Record<string, unknown>;
};

// ═══════════════════════════════════════════════════════════════════════════
// CPRA — 3 cases
// ═══════════════════════════════════════════════════════════════════════════

const cpraTrendyGoods: DevTestCase = {
  name: "CPRA-1: TrendyGoods 电商平台",
  description: "中型电商，年收入30M，缺少opt-out机制，Cookie暗模式，广告合同不合规",
  jurisdiction: "US",
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
  payload: {
    company_name: "TrendyGoods Inc.",
    business_model: "线上时尚零售商，年收入约3000万美元，通过网站和移动应用向消费者直销。使用用户行为分析进行个性化推荐，并使用第三方广告服务。DBA：TrendyGoods.com",
    data_lifecycle: "收集→分析→个性化推荐→与第三方广告网络共享。数据类别：用户浏览行为、购买历史、设备信息、联系方式",
    notice_and_consent: "隐私政策链接在网站底部。Cookie横幅仅提供'接受'按钮，同等突出的'拒绝所有'选项缺失。UI暗模式：Cookie横幅的'接受所有'按钮颜色突出，'管理偏好'链接字体极小且颜色与背景相近",
    consumer_rights_process: "提供在线表单和邮箱渠道，但缺少免费电话。身份验证：通过注册邮箱发送验证链接。SLA：承诺45天内响应",
    opt_out_and_sale_sharing: "与AdNetwork Alpha和Beta共享用户浏览行为数据和购买历史用于定向广告。页面页脚链接文字为'Privacy Settings'，未使用CPPA规定的'请勿出售或分享我的个人信息'标准化文字和三角图标，链接位于页面底部小字体区域",
    vendor_management: "与AdNetwork Alpha和Beta的合同为标准广告服务条款，未包含其必须遵守消费者opt-out指令的条款，未明确要求服务提供商/承包商遵守CPRA数据保护义务",
    attachments: [
      {
        file_role: "privacy_policy" as const,
        file_name: "privacy_policy_url",
        file_format: "url" as const,
        storage_uri: "https://trendygoods.com/privacy"
      }
    ]
  }
};

const cpraDataFlow: DevTestCase = {
  name: "CPRA-2: DataFlow SaaS 服务商",
  description: "B2B SaaS，年收入18M不达标但处理量>10万，服务提供商角色混淆，适用性边界测试",
  jurisdiction: "US",
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
  payload: {
    company_name: "DataFlow Analytics LLC",
    business_model: "B2B SaaS，为中小企业提供数据看板服务。年收入约1800万美元（未达2500万门槛）。客户将业务数据上传至DataFlow平台进行分析。适用性：公司认为自己可能不受CPRA直接管辖（年收入未达标），但作为服务提供商处理客户上传的数据",
    data_lifecycle: "客户上传数据→分析处理→生成看板→返回客户。作为服务提供商，数据由客户（控制者）决定处理目的和方式",
    notice_and_consent: "不与消费者直接交互。作为服务提供商，依赖客户（控制者）履行通知和同意义务。无独立隐私政策面向终端消费者",
    consumer_rights_process: "无面向消费者的DSR渠道。作为服务提供商，依赖控制者的DSR机制。内部流程：收到客户转交的DSR请求后，在15个工作日内协助执行（删除、访问等）",
    opt_out_and_sale_sharing: "不出售或分享数据。严格按控制者（客户）的书面指示处理数据，不将数据用于自身商业目的",
    vendor_management: "与客户签订的《数据处理协议》模板较简单，未包含CPRA §1798.100要求的全部强制性服务提供商条款（如禁止出售数据、协助DSR、允许审计等）。与AWS等云基础设施提供商签订有标准DPA",
    attachments: [
      {
        file_role: "privacy_policy" as const,
        file_name: "privacy_policy_url",
        file_format: "url" as const,
        storage_uri: "https://dataflow.io/dpa"
      }
    ]
  }
};

const cpraFitLife: DevTestCase = {
  name: "CPRA-3: FitLife AI 健康科技",
  description: "健康APP收集SPI，暗模式获取同意，向第三方营销出售健康衍生数据，缺失Limit SPI权利",
  jurisdiction: "US",
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
  payload: {
    company_name: "FitLife AI Inc.",
    business_model: "智能健身APP开发商，通过手机传感器和可穿戴设备收集用户的健康、生物特征和精确位置数据，提供个性化健身指导和健康风险预测，并向用户推荐保健品和保险产品。",
    data_lifecycle: "传感器采集（心率、步数、睡眠、位置）→健康分析→个性化指导+产品推荐→与保健品/保险公司共享健康衍生数据。SPI使用：健康数据用于个性化健身（合理），但同时用于第三方营销（超出合理范围）",
    notice_and_consent: "注册界面使用捆绑同意设计（'点击注册即表示您同意我们的隐私政策和服务条款'，无单独同意选项）。对SPI处理的同意通过不平等设计获取。UI暗模式：注册时'同意并继续'按钮为大号绿色，'仅浏览'链接为灰色小字。健康数据SPI处理的单独同意选项默认勾选且隐藏在三层菜单后",
    consumer_rights_process: "DSR渠道隐藏在'设置→隐私→更多选项→行使您的权利→提交请求'的五层菜单中，不符合CPRA要求消费者权利行使渠道'易于找到和使用'的规定。身份验证：仅邮箱验证。SLA：未明确承诺处理时限。完全缺失'限制敏感信息使用'(Limit SPI)的权利行使入口",
    opt_out_and_sale_sharing: "向保健品公司HealthSupps和保险公司QuickInsure共享用户健康衍生数据（如'运动活跃度评分''健康风险等级'）。未提供选择退出链接，也未在共享前获得有效的选择同意",
    vendor_management: "与HealthSupps和QuickInsure的合同为简单的数据共享协议，完全未提及CPRA合规义务。未约定服务提供商/承包商必须遵守消费者的opt-out指令",
    attachments: [
      {
        file_role: "privacy_policy" as const,
        file_name: "privacy_policy_url",
        file_format: "url" as const,
        storage_uri: "https://fitlife.ai/privacy"
      }
    ]
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// Diagnosis — 3 cases
// ═══════════════════════════════════════════════════════════════════════════

const diagEcommerce: DevTestCase = {
  name: "诊断-1: 跨境优品 电商（标准合同/认证路径）",
  description: "中型跨境电商，不涉及重要数据，非CIIO，出境45万一般个人信息→触发标准合同/认证路径",
  jurisdiction: "CN",
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
  payload: {
    company_name: "跨境优品",
    answers: {
      q1_is_ciio: "no",
      q2_has_important_data: "no",
      q3_pii_count: 450000,
      q4_spi_count: 0,
      q5_no_personal_info: "no",
      q6_scenario: "business_operation",
      q7_receiver_type: "affiliated_company",
      q8_purpose: "将订单数据同步至新加坡亚太数据中心，用于优化区域物流算法和精准营销",
      m1_enterprise_name: "跨境优品",
      m1_industry: "电商零售",
      m1_business_channels: ["线上平台（APP / 小程序 / 官网）", "跨境服务（面向国外用户 / 业务涉及国外）"],
      m1_service_targets: "个人用户",
      m1_company_size: "中型（51-200人）"
    }
  }
};

const diagMedical: DevTestCase = {
  name: "诊断-2: 前沿生命科技 医疗研究（安全评估路径）",
  description: "研究机构出境1.5万患者医疗数据（可能涉及重要数据）→触发安全评估路径，测试'不知道'辅助判断",
  jurisdiction: "CN",
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
  payload: {
    company_name: "前沿生命科技研究院",
    answers: {
      q1_is_ciio: "no",
      q2_has_important_data: "yes",
      q3_pii_count: 15000,
      q4_spi_count: 15000,
      q5_no_personal_info: "no",
      q6_scenario: "scientific_research",
      q7_receiver_type: "academic_partner",
      q8_purpose: "与欧盟大学合作罕见病研究，传输脱敏医疗记录（含诊断结果、用药史、基因测序数据摘要）至欧盟合作方服务器进行分析",
      m1_enterprise_name: "前沿生命科技研究院",
      m1_industry: "医疗健康",
      m1_business_channels: ["数据合作（与其他公司共享 / 交换数据）"],
      m1_service_targets: "个人用户",
      m1_company_size: "中型（51-200人）"
    }
  }
};

const diagAnonymous: DevTestCase = {
  name: "诊断-3: 智造未来科技有限公司（路径判断）",
  description: "工业物联网企业向德国研发中心共享设备数据，涉及个人信息与企业数据跨境传输，测试路径判断输入链路",
  jurisdiction: "CN",
  formDefaults: {
    company_name: "智造未来科技有限公司",
    m1_industry: "智能制造",
    m1_business_channels: [
      "线上平台（APP / 小程序 / 官网）",
      "数据合作（与其他公司共享 / 交换数据）",
      "跨境服务（面向国外用户 / 业务涉及国外）"
    ],
    m1_service_targets: "企业用户",
    m1_company_size: "中型（51-200人）",
    m2_core_needs: ["不确定业务是否需要数据跨境", "识别业务合规风险点"],
    m2_had_compliance_issue: "no",
    m2_deadline: "一般需求（1-3个月）",
    m3_processes_personal_info: "yes",
    m3_personal_info_types: ["姓名", "手机号", "邮箱地址", "账号信息"],
    m3_processes_enterprise_public_data: "yes",
    m3_enterprise_public_data_desc: "处理客户工厂的设备传感器数据、生产日志、性能报告等企业运营数据",
    m3_data_sources: ["用户主动提交", "设备自动采集"],
    m3_processing_activities: ["收集", "存储", "传输", "跨境传输"],
    m3_data_volume_range: "10万条以下",
    m3_retention_period: "业务必要期限内留存",
    m3_retention_desc: "客户合同期内持续存储，合同终止后180天内匿名化处理",
    m4_share_to_third_party: "yes",
    m4_third_party_types: "德国研发中心",
    m4_cross_border_transfer: "yes",
    m4_cross_border_regions: "德国",
    m4_commercialization: "yes",
    m4_commercialization_mode: "作为核心产品“预测性维护”功能的改进依据，用于持续优化AI模型",
    m4_entrusted_processing: "yes",
    m4_entrusted_party_type: "使用国际云服务商的德国法兰克福区域服务器进行存储和计算",
    m4_authorization_method: '单独点击"同意"按钮',
    m5_systems: ["自有 APP", "官方网站", "定制化业务系统"],
    m5_security_measures: ["数据加密", "访问权限控制", "操作日志审计"],
    m5_compliance_docs: ["隐私政策", "用户协议"],
    m5_penalty_or_complaint: "无相关记录"
  },
  payload: {
    company_name: "智造未来科技有限公司",
    answers: {
      q1_is_ciio: "no",
      q2_has_important_data: "unknown",
      q3_pii_count: 2000,
      q4_spi_count: 0,
      q5_no_personal_info: "no",
      q6_scenario: "technology_development",
      q7_receiver_type: "affiliated_company",
      q8_purpose: "向德国慕尼黑研发中心持续共享设备运行状态、故障日志等数据以优化算法模型，并结合企业规模、数据性质等因素判断适用的数据出境合规路径",
      m1_enterprise_name: "智造未来科技有限公司",
      m1_industry: "智能制造",
      m1_business_channels: [
        "线上平台（APP / 小程序 / 官网）",
        "数据合作（与其他公司共享 / 交换数据）",
        "跨境服务（面向国外用户 / 业务涉及国外）"
      ],
      m1_service_targets: "企业用户",
      m1_company_size: "中型（51-200人）"
    }
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// Assessment — 2 cases
// ═══════════════════════════════════════════════════════════════════════════

const assessCIO: DevTestCase = {
  name: "评估-1: 东方信托 CIIO金融机构",
  description: "CIIO信托公司向香港母公司传输交易数据和客户信息，含重要数据风险，法律文件缺失条款",
  jurisdiction: "CN",
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
  payload: {
    company_name: "东方信托有限责任公司",
    industry: "金融科技",
    is_ciio: true,
    contains_important_data: true,
    pii_count: 80000,
    spi_count: 80000,
    transfer_purpose: "跨境集团财务报告与风险管理，满足集团合并报表监管要求，进行集中风险分析",
    receiver_country: "香港",
    force_override_path: true,
    transfer_frequency: "continuous",
    receiver_name: "东方金融控股集团",
    security_capability_summary: "管理：有《数据分类分级管理规范》。技术：传输采用AES-256加密，存储采用令牌化。认证：通过网络安全等级保护（三级）测评。",
    data_inventory_summary: "每日交易结算数据、高净值客户资产配置信息（含金融账户信息）。频率：每日T+1。合法性依据：履行集团内部管理与监管报告义务",
    system_chain_summary: "境内存储：公司本地数据中心。传输链路：通过IPSec-VPN专线加密传输至香港母公司私有云。境外存储：香港数据中心",
    legal_document_review: "与母公司签订有《集团数据共享与处理协议》，但缺少'数据出境安全评估办法'第九条要求的全部6项核心条款（接受方所在法律环境变化的处理措施、再转移约束不明确）",
    compliance_history: "2024年曾因'客户信息保护不力'受到当地银保监局警告，已整改完毕",
    personal_info_protection: "已通过线上协议更新获取约8万名高净值客户关于向关联集团共享资产信息用于风险管理的单独同意，但同意记录未系统化归档"
  }
};

const assessEcommerce: DevTestCase = {
  name: "评估-2: 智慧云联科技（上海）有限公司（安全评估路径）",
  description: "中外合资云计算服务商向新加坡子公司实时传输客户服务与交易行为数据，含重要数据与百万级PI，测试安全评估完整输入链路",
  jurisdiction: "CN",
  formDefaults: {
    company_name: "智慧云联科技（上海）有限公司",
    company_uscc: "91310000MA7F123456",
    legal_representative: "张伟",
    registered_address: "中国（上海）自由贸易试验区张江高科技园区亮秀路112号Y1座1001室",
    company_nature: "有限责任公司（中外合资）",
    industry: "云计算与数据服务",
    receiver_country: "新加坡",
    receiver_name: "Wisdom Cloud Connect Pte. Ltd.",
    assessment_start_date: "2025-08-01",
    assessment_end_date: "2025-09-15",
    lead_department: "集团法律合规与公共事务部",
    participant_departments: "信息技术部，网络安全部，亚太区业务运营部，数据中心管理部",
    third_party_support: true,
    third_party_name: "德勤企业风险管理咨询（上海）有限公司",
    third_party_scope:
      "对数据出境活动的风险评估方法、已采取的安全措施有效性进行审阅与验证，并出具第三方核查报告；协助对新加坡子公司的数据保护环境进行合规性差距分析",
    scenario_name: "亚太区客户支持与实时风险控制数据同步",
    transfer_frequency: "continuous",
    is_long_term: true,
    transfer_purpose:
      "全球统一客户服务、集中化风险分析与建模、履行与境外关联方的《全球运营支持与数据处理协议》",
    legal_basis:
      "根据《个人信息保护法》第十三条第一款第二项、第一款第七项以及《数据安全法》《网络安全法》相关规定，在完成安全评估后开展跨境传输",
    necessity_basis:
      "保障全球服务连续性与质量；满足跨国欺诈侦测与集中风控建模需求；基于网络延迟、基础设施稳定性和运营成本综合评估后，新加坡数据中心为最优技术架构",
    is_ciio: false,
    contains_important_data: true,
    pii_count: 1200000,
    spi_count: 15000,
    data_inventory_summary:
      "场景一：客户服务支持，字段包括客户唯一标识符、姓名、联系方式、服务请求内容、沟通记录、问题解决状态；场景二：交易风险控制，字段包括Device ID、IP地址、交易时间、金额、类型、收款方信息、行为序列、风险评分标签、加密后的证件号码及验证结果；场景三：系统运维与安全，字段包括系统日志、匿名化性能监控数据、安全事件告警信息",
    system_chain_summary:
      "数据来源于中国境内应用服务器和数据库；先在上海数据中心进行清洗、脱敏和格式化；随后通过IPSec VPN专线与TLS 1.3加密实时传输至新加坡数据中心；境外供客户服务系统、风控引擎和运维平台调用；风控结果与客户服务归档信息再回流境内",
    security_capability_summary:
      "技术措施：传输全程加密、敏感个人信息AES-256加密存储、密钥由境内总部HSM管理、RBAC+MFA访问控制、日志留存不少于6年、非生产环境仅用合成/深度脱敏数据；管理措施：签署集团内数据跨境传输协议、每年两次内部审计和一次渗透测试、建立中新两地数据泄露应急响应预案并定期演练",
    force_override_path: true
  },
  payload: {
    company_name: "智慧云联科技（上海）有限公司",
    company_uscc: "91310000MA7F123456",
    legal_representative: "张伟",
    registered_address: "中国（上海）自由贸易试验区张江高科技园区亮秀路112号Y1座1001室",
    company_nature: "有限责任公司（中外合资）",
    industry: "云计算与数据服务",
    receiver_country: "新加坡",
    receiver_name: "Wisdom Cloud Connect Pte. Ltd.",
    assessment_start_date: "2025-08-01",
    assessment_end_date: "2025-09-15",
    lead_department: "集团法律合规与公共事务部",
    participant_departments: "信息技术部，网络安全部，亚太区业务运营部，数据中心管理部",
    third_party_support: true,
    third_party_name: "德勤企业风险管理咨询（上海）有限公司",
    third_party_scope:
      "对本数据出境活动的风险评估方法、已采取的安全措施有效性进行审阅与验证，并出具《第三方核查报告》；协助对新加坡子公司的数据保护环境进行合规性差距分析",
    scenario_name: "亚太区客户支持与实时风险控制数据同步",
    transfer_frequency: "continuous",
    is_long_term: true,
    transfer_purpose:
      "全球统一客户服务；集中化风险分析与建模；履行与境外关联方的服务合同",
    legal_basis:
      "根据《个人信息保护法》第十三条第一款第二项、第一款第七项，以及《数据安全法》《网络安全法》及相关监管规定，在完成安全评估后进行数据出境",
    necessity_basis:
      "业务连续性与服务质量、风险防控有效性以及技术架构与成本最优共同决定需向新加坡数据中心持续实时传输相关数据",
    is_ciio: false,
    contains_important_data: true,
    pii_count: 1200000,
    spi_count: 15000,
    force_override_path: true,
    data_inventory_summary:
      "客户服务支持：客户唯一标识符、姓名、联系方式、服务请求内容、沟通记录、问题解决状态；交易风险控制：Device ID、IP地址、交易时间、金额、类型、收款方信息、行为序列、风险评分标签、加密后的证件号码及验证结果；系统运维与安全：系统日志、匿名化性能监控数据、安全事件告警信息",
    system_chain_summary:
      "中国境内应用服务器与数据库产生日志和业务数据；在上海数据中心进行初步清洗、脱敏和格式化；通过IPSec VPN专线和TLS 1.3加密实时传输至新加坡；境外处理后风控结果与工单归档信息再回传境内",
    security_capability_summary:
      "传输全程加密；敏感个人信息AES-256加密存储，密钥由境内总部HSM管理；最小权限+MFA；全链路日志留存不少于6年并实时监控；非生产环境仅使用合成数据或深度脱敏数据；每年两次内部审计和一次渗透测试；中、新两地数据泄露应急响应预案并定期演练"
  },
  backendFilePaths: [
    "resources/legal/sources/cn/references/数据出境风险自评估报告（模板）.docx",
    "resources/legal/sources/cn/references/数据出境安全评估申报指南（第三版）.docx",
    "resources/legal/sources/cn/references/个人信息出境标准合同备案指南（第二版）.docx"
  ]
};

// ═══════════════════════════════════════════════════════════════════════════
// EU SCC — 3 cases (from EU data export path)
// ═══════════════════════════════════════════════════════════════════════════

const euSccBasic: DevTestCase = {
  name: "EU-SCC-1: 基本合规的C2P模块",
  description: "德国电商→美国云服务商，C2P模块基本合规但有2个中风险问题",
  jurisdiction: "EU",
  formDefaults: {
    exporter_name: "E-Commerce GmbH",
    importer_name: "CloudServe Inc.",
    importer_country: "美国",
    transfer_role: "c2p",
    scc_version: "eu_2021",
    transfer_purpose: "云托管和基础设施服务，处理电商平台客户的订单和支付数据",
    data_categories: "姓名、邮箱、收货地址、订单历史、支付信息",
    data_subject_categories: "电商平台客户",
    transfer_frequency: "continuous",
    retention_rule: "服务协议期间加30天",
    tom_summary: "静态加密AES-256、传输加密TLS 1.3、访问控制、定期安全审计",
    onward_transfer_control: "子处理者列表公开并可提前30天通知变更",
    rights_and_complaint: "通过隐私政策和DSR渠道支持数据主体权利",
    has_scc_draft: true,
    has_tia: false,
    has_supplementary_measures: false
  },
  payload: {
    project_name: "电商平台云服务数据处理",
    scc_text: "MODULE TWO: Transfer controller to processor\n\nClause 1: Purpose and scope...\n\nThe data exporter is: E-Commerce GmbH, Berlin, Germany\nThe data importer is: CloudServe Inc., Delaware, USA\n\nAnnex I\nA. LIST OF PARTIES\nData exporter: E-Commerce GmbH, Friedrichstrasse 123, 10117 Berlin, Germany, Contact: dpo@ecommerce.de, Role: Controller\nData importer: CloudServe Inc., 123 Main St, Wilmington DE, USA, Contact: privacy@cloudserve.com, Role: Processor\n\nB. DESCRIPTION OF TRANSFER\nCategories of data subjects: Customers of the data exporter's online platform\nCategories of personal data: Name, email, shipping address, order history, payment information\nSensitive data transferred: No\nFrequency of transfer: Continuous\nNature of processing: Hosting, storage, and technical support\nPurpose of transfer: Cloud hosting and infrastructure services\nRetention period: Duration of service agreement plus 30 days\n\nC. COMPETENT SUPERVISORY AUTHORITY\nBerlin Data Protection Authority (Berliner Beauftragte fur Datenschutz und Informationsfreiheit)\n\nClause 9: Use of sub-processors\nThe data importer maintains a list of approved sub-processors available at https://cloudserve.com/subprocessors. The data importer shall inform the data exporter of any intended changes to sub-processors at least 30 days in advance.\n\nTechnical and organisational measures: Encryption at rest (AES-256), encryption in transit (TLS 1.3), access controls, regular security audits",
    declared_module_type: "C2P",
    exporter_role: "controller",
    importer_role: "processor",
    has_tia: false,
    has_supplementary_measures: false,
    company_name: "E-Commerce GmbH"
  }
};

const euSccHealthIndia: DevTestCase = {
  name: "EU-SCC-2: 健康数据→印度 高风险修改",
  description: "荷兰研究机构→印度分析公司，Clause 15被修改，SPI分类错误，缺少补充措施",
  jurisdiction: "EU",
  formDefaults: {
    exporter_name: "Health Research Institute",
    importer_name: "DataAnalytica India Pvt Ltd",
    importer_country: "印度",
    transfer_role: "c2p",
    scc_version: "eu_2021",
    transfer_purpose: "罕见病研究数据分析，处理患者健康记录和基因测序数据",
    data_categories: "患者健康记录、基因测序数据、治疗历史",
    data_subject_categories: "罕见病研究参与者",
    transfer_frequency: "periodic",
    retention_rule: "研究项目结束后按法规要求保留",
    tom_summary: "数据传输加密，但Clause 15政府请求通知条款被非法修改为\"as soon as legally permissible\"",
    onward_transfer_control: "子处理者变更通过邮件通知，15个工作日无异议即可启用",
    rights_and_complaint: "数据主体权利机制需配套完善",
    government_access_response: "Clause 15修改削弱了政府访问透明度义务",
    supplementary_clause_review: "需要重点审查Clause 15修改的有效性、SPI分类错误、以及印度法律环境下的补充措施需求",
    has_scc_draft: true,
    has_tia: false,
    has_supplementary_measures: false
  },
  payload: {
    project_name: "罕见病研究数据分析",
    scc_text: "MODULE TWO: Transfer controller to processor\n\nData exporter: Health Research Institute, Amsterdam, Netherlands\nData importer: DataAnalytica India Pvt Ltd, Bangalore, India\n\nClause 15(a) - modified from standard text: The data importer shall, as soon as legally permissible, provide the data exporter with information about any legally binding request from a public authority. The data importer shall use reasonable discretion in determining what information to provide.\n\nAnnex I.B:\nCategories of data subjects: Patients participating in rare disease studies\nCategories of personal data: Patient health records, genetic sequencing data, treatment history\nSensitive data transferred: The parties confirm that no special categories of data are transferred\n\nClause 9: Use of sub-processors\nThe data importer shall submit any planned changes to its list of sub-processors to the data exporter via email. If the data exporter does not object in writing within fifteen (15) business days, the data importer may engage the new sub-processor.",
    declared_module_type: "C2P",
    exporter_role: "controller",
    importer_role: "processor",
    has_tia: false,
    has_supplementary_measures: false,
    company_name: "Health Research Institute"
  }
};

const euSccModuleError: DevTestCase = {
  name: "EU-SCC-3: 多方加入 模块选择错误",
  description: "C→P→Sub-P三层关系误选Module Two(C2P)，应为Module Three(P2P)，加入方信息缺失",
  jurisdiction: "EU",
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
    has_supplementary_measures: false
  },
  payload: {
    project_name: "客户支持工单子处理",
    scc_text: "MODULE TWO: Transfer controller to processor (ERROR - should be Module Three)\n\nData exporter: Orange Cloud BV (processor acting on behalf of Nordic Retail Group, the controller)\nData importer: Orange Cloud BV (incorrect - double role assignment)\nSub-processor: Balkan IT Support DOO, Belgrade, Serbia\n\nClause 7: Docking clause\nAn entity that is not a Party to these Clauses may, with the agreement of the Parties, accede to these Clauses at any time, either as a data exporter or as a data importer, by completing the Annexes and signing Annex I.A.\n\nAnnex I.A: Nordic Retail Group (controller) details marked as 'See Master Service Agreement' with no address or contact information filled in.\n\nClause 9: Data importer may engage sub-processors after notification. No requirement for specific written authorization from controller.",
    declared_module_type: "C2P",
    exporter_role: "processor",
    importer_role: "processor",
    has_tia: false,
    has_supplementary_measures: false,
    company_name: "Orange Cloud BV"
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// BCR — 3 cases
// ═══════════════════════════════════════════════════════════════════════════

const bcrMediumRisk: DevTestCase = {
  name: "BCR-1: GlobalTech 中风险BCR-C",
  description: "跨国科技集团BCR-C，TIA描述笼统，投诉流程不具体，向集团外传输限制不明确(3个中风险)",
  jurisdiction: "EU",
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
  payload: {
    company_name: "GlobalTech Inc.",
    review_items: [
      {
        code: "3.2-C5",
        title: "向集团外传输 (Onward Transfer) — Clause 3.5",
        evidence: "条款允许向第三方传输数据的前提是第三方承诺遵守'实质相似'的义务，但未明确要求必须确保第三方提供与GDPR'实质等同'的保护水平，也未规定必须使用SCC等经批准的传输工具",
        score: "partial"
      },
      {
        code: "3.2-C7",
        title: "投诉与救济 — Clause 4.7",
        evidence: "投诉处理机制描述过于笼统，未规定具体的响应时限、调查步骤、书面回复要求，未明确告知数据主体有权向监管机构投诉或寻求司法救济",
        score: "partial"
      },
      {
        code: "3.2-C9",
        title: "第三国法律评估 — Chapter 6",
        evidence: "仅泛泛要求评估，未提及必须遵循EDPB建议01/2020的六步法进行结构化评估，也未要求记录评估结果。通知义务被弱化为'在法律允许的范围内'",
        score: "partial"
      }
    ],
    scenario_context: {
      group_name: "GlobalTech Inc.",
      applicant_entity: "GlobalTech Ireland Ltd, Dublin",
      group_structure_summary: "跨国科技公司，业务遍及欧盟、美国、印度和新加坡，总部位于爱尔兰都柏林",
      data_flow_scope: "内部从欧盟实体向非充分性认定国家（美国、印度）的数据传输"
    }
  }
};

const bcrHighRisk: DevTestCase = {
  name: "BCR-2: HealthData 高风险BCR-C",
  description: "医疗联盟BCR-C，缺失第三方受益人权利条款、未指定欧盟责任主体、法律约束力不清晰(3个高风险)",
  jurisdiction: "EU",
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
  payload: {
    company_name: "HealthData Alliance",
    review_items: [
      {
        code: "3.2-C3",
        title: "第三方受益人权利 — 全文缺失",
        evidence: "全文未包含任何条款赋予数据主体作为第三方受益人强制执行BCR的权利，直接违反GDPR第47(1)(b)条",
        score: "non_compliant"
      },
      {
        code: "3.2-C4",
        title: "欧盟责任主体与赔偿 — Chapter 8",
        evidence: "仅泛泛提及成员根据适用法律承担责任，完全没有指定一个位于欧盟的实体作为责任主体，也未承诺该实体将为非欧盟成员的违规行为向数据主体承担赔偿责任",
        score: "non_compliant"
      },
      {
        code: "3.2-C1",
        title: "法律约束力机制 — 全文",
        evidence: "文档称BCR通过'联盟章程'对成员有约束力，但未提供该章程作为附件，也未解释其如何对成员产生法律约束力",
        score: "non_compliant"
      }
    ],
    scenario_context: {
      group_name: "HealthData Alliance",
      applicant_entity: "（未指定）",
      group_structure_summary: "多家欧洲医疗机构组成的联盟，共享匿名医疗研究数据",
      data_flow_scope: "成员间共享匿名的医疗研究数据，涉及多国数据传输"
    }
  }
};

const bcrStructuralFailure: DevTestCase = {
  name: "BCR-3: CloudProcessors 结构缺失与模块错误",
  description: "提交内容极度简略(仅3页)，BCR-C vs BCR-P模块混淆，缺失所有核心章节",
  jurisdiction: "EU",
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
  payload: {
    company_name: "CloudProcessors Consortium",
    review_items: [
      {
        code: "3.2-C1",
        title: "模块选择与文档类型 — 全文",
        evidence: "文档标题声称是BCR for Controllers，但内容反复提及'代表客户''根据客户指示'处理数据，明确描述了数据处理者的角色。应适用BCR-P而非BCR-C",
        score: "non_compliant"
      },
      {
        code: "3.2-C2",
        title: "结构完整性 — 全文",
        evidence: "文档仅3页，缺失EDPB建议表格中要求的所有核心章节：具有法律约束力的内部机制、第三方受益人权利、欧盟责任主体与赔偿条款、数据保护原则、数据主体权利、第三国法律评估、投诉处理流程、培训审计机制、更新程序等",
        score: "non_compliant"
      }
    ],
    scenario_context: {
      group_name: "CloudProcessors Consortium",
      applicant_entity: "（未指定）",
      group_structure_summary: "声称是一个处理者联盟，为外部控制者提供云处理服务",
      data_flow_scope: "代表客户处理数据，在全球范围内传输"
    }
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// DPIA — 2 cases
// ═══════════════════════════════════════════════════════════════════════════

const dpiaAIRecruitment: DevTestCase = {
  name: "DPIA-1: AI招聘筛选系统",
  description: "跨国科技公司AI招聘系统，大规模处理+自动决策+特殊数据推断风险+跨境传输",
  jurisdiction: "EU",
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
  payload: {
    project_name: "AI招聘筛选与候选人评估系统",
    project_goal: "通过自动化分析求职者的多维度数据（简历、视频面试、测试结果），提高招聘效率，减少人工偏见，并识别最适合岗位的候选人。系统将为每位候选人生成综合评分和排名",
    dpia_trigger_reasons: [
      "自动化决策与画像：系统对候选人进行自动化评估和排名，可能产生具有法律效力的决定",
      "大规模处理：预计每年处理超过10万份欧盟求职者申请",
      "特殊类别数据风险：通过视频面试分析可能间接推断出种族、健康状况等特殊类别数据",
      "系统监控：对求职者进行系统性评估"
    ],
    processing_flow_description: "数据从求职者→公司招聘网站/第三方平台→AWS欧盟服务器（存储）→AI模型（美国研发，部署在欧盟）→结果返回HR系统。AI模型分析简历、在线档案、视频面试记录（面部表情和语言分析）、在线测试结果，自动筛选并生成评分排名",
    data_categories: ["身份信息", "联系方式", "教育背景", "工作经历", "技能证书", "视频/音频记录", "在线测试答案", "面部特征数据", "打字/点击行为数据"],
    special_category_data: true,
    special_category_types: ["种族（可能通过视频面试推断）", "健康状况（可能通过视频面试推断疲劳/压力）", "工会成员身份（可能通过简历推断）"],
    data_subject_categories: ["求职者"],
    data_subject_count: "超过10万人/年",
    retention_period: "未成功候选人数据保留6个月，成功候选人数据转为员工档案",
    cross_border_transfer: true,
    transfer_destination: "美国（AI模型由美国团队开发，部分训练数据可能传至美国进行模型优化）",
    automated_decision_making: true,
    systematic_monitoring: true,
    large_scale_processing: true,
    data_matching: false,
    new_technology: true
  }
};

const dpiaSmartCity: DevTestCase = {
  name: "DPIA-2: 智能城市人群分析系统",
  description: "城市管理局公共场所人群监控系统，大规模监控+数据关联重识别风险+寒蝉效应",
  jurisdiction: "EU",
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
  payload: {
    project_name: "市中心商业区人群动态智能分析系统",
    project_goal: "通过多源数据融合分析，实时掌握公共空间人群动态，优化城市规划、提升公共安全应急响应能力，并为商家提供客流洞察以促进经济发展",
    dpia_trigger_reasons: [
      "大规模系统监控：在公共空间对大量个人进行持续、系统性跟踪",
      "大规模处理：覆盖日均数十万人流量",
      "数据匹配与关联：将匿名设备标识符与商业消费等数据进行关联分析，可能重识别个人",
      "可能妨碍权利行使：大规模监控可能对集会自由、匿名权产生寒蝉效应"
    ],
    processing_flow_description: "摄像头→视频流（本地边缘服务器实时分析，生成匿名化人数/流向数据）→中心平台；Wi-Fi/信令数据→匿名设备ID→中心平台与商业数据（去标识化）关联分析",
    data_categories: ["视频元数据（人数、运动矢量）", "匿名设备标识符（MAC地址哈希、IMSI哈希）", "时间戳", "位置坐标", "与商业POS系统关联的匿名消费记录"],
    special_category_data: false,
    special_category_types: [],
    data_subject_categories: ["市民", "游客", "消费者"],
    data_subject_count: "日均30-50万人",
    retention_period: "原始视频流保留72小时，匿名统计数据永久保留",
    cross_border_transfer: false,
    transfer_destination: "",
    automated_decision_making: false,
    systematic_monitoring: true,
    large_scale_processing: true,
    data_matching: true,
    new_technology: true
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// TIA — 2 cases (from docx extraction)
// ═══════════════════════════════════════════════════════════════════════════

const tiaBasicSCC: DevTestCase = {
  name: "TIA-1: 基本SCC传输影响评估",
  description: "爱尔兰科技公司→印度处理者，SCC作为传输工具，目的地法律评估+补充措施",
  jurisdiction: "EU",
  formDefaults: {
    data_exporter_name: "TechInnovate Ireland Ltd，注册于爱尔兰都柏林，为欧盟客户提供SaaS数据分析平台，角色：数据控制者",
    data_importer_name: "AnalyticsPro India Pvt Ltd，位于印度班加罗尔，角色：数据处理者",
    importer_country_region: "印度",
    transfer_purpose: "委托印度处理者进行数据分析和处理支持",
    data_categories: "客户数据分析结果、使用统计、账户信息",
    sensitive_data_description: "不含特殊类别数据",
    data_subject_categories: "平台用户",
    transfer_frequency: "periodic",
    transfer_tool: "scc",
    law_assessed: true,
    law_findings: "印度未获欧盟充分性认定。DPDP Act 2023提供基本框架但政府访问权限仍宽（IT法第69条）。根据Schrems II标准存在风险",
    pre_effectiveness: "仅SCC条款不足以完全覆盖印度政府访问数据的残余风险",
    supplementary_technical: "端到端加密（密钥由出口方管理）、数据最小化、假名化处理",
    supplementary_contractual: "增加透明度义务（进口方收到政府数据请求24小时内通知出口方）、定期审计权",
    supplementary_organizational: "进口方员工定期DP培训、访问控制日志、事件响应SLA",
    post_effectiveness: "实施补充措施后，第三国法律不会损害SCC提供的实质等同保护水平。传输可继续，每年复审",
    key_actions: "完善审计日志、季度复盘、监控印度数据保护法律变化",
    dpo_opinion: "同意在附加措施落实后继续传输，建议每年复审",
    review_date: "2026-07-01",
    attachment_role: "country_law_analysis"
  },
  payload: {
    transfer_tool: "scc",
    data_exporter_profile: "TechInnovate Ireland Ltd，注册于爱尔兰都柏林，为欧盟客户提供SaaS数据分析平台。作为数据控制者处理客户数据",
    data_importer_profile: "AnalyticsPro India Pvt Ltd，位于印度班加罗尔，为TechInnovate提供数据处理和技术支持服务。角色：数据处理者",
    third_country_assessment: "印度目前没有获得欧盟充分性认定。印度的数据保护法律（DPDP Act 2023）提供了基本保护框架，但政府机构的数据访问权限仍然较宽。根据Schrems II判决标准，印度法律在政府访问数据的必要性和相称性方面存在一定风险。印度《信息技术法》第69条赋予政府广泛的监控权力",
    supplementary_measures: "技术措施：端到端加密（数据在传输前加密，密钥由出口方管理，进口方无法解密）；数据最小化（仅传输分析所必需的数据字段）；假名化处理。合同措施：在SCC基础上增加透明度义务（进口方须在收到政府数据请求24小时内通知出口方）；定期审计权。组织措施：进口方员工定期数据保护培训；访问控制日志；事件响应SLA",
    final_conclusion: "经评估，在实施上述技术、合同和组织补充措施后，第三国法律不会损害SCC提供的实质等同保护水平。传输可继续进行，但需每年复审目的地法律变化",
    attachments: [{ file_role: "tia_main_report", file_name: "sample_contract.txt", file_format: "txt", storage_uri: "benchmarks/sample-inputs/sample_contract.txt" }]
  }
};

const tiaChinaBCR: DevTestCase = {
  name: "TIA-2: BCR传输至中国 有效性存疑",
  description: "德国制造集团→中国子公司，BCR工具，中国数据法律环境评估为高风险",
  jurisdiction: "EU",
  formDefaults: {
    data_exporter_name: "Precision Manufacturing Group GmbH，德国斯图加特，全球精密制造集团母公司，持有已获批的BCR-C",
    data_importer_name: "Precision Manufacturing (Shanghai) Co. Ltd，位于中国上海，集团全资子公司，角色：共同控制者",
    importer_country_region: "中国",
    transfer_purpose: "集团内部数据传输，支持亚太区生产和销售运营",
    data_categories: "生产运营数据、销售报表、员工信息、供应链数据",
    sensitive_data_description: "不含特殊类别数据",
    data_subject_categories: "员工、客户联系人",
    transfer_frequency: "continuous",
    transfer_tool: "bcr",
    law_assessed: true,
    law_findings: "中国法律环境：网安法第37条、数安法第21条赋予监管机构广泛数据访问权限；《国家情报法》第7条允许情报机构依法收集信息；缺乏独立司法审查机制挑战政府数据请求。中国未获欧盟充分性认定",
    pre_effectiveness: "仅依赖BCR-C本身不足以完全覆盖中国法律环境带来的风险",
    supplementary_technical: "强加密（256-bit，密钥完全由德国方管理）、数据拆分存储（关键数据保留德国，仅匿名化运营指标传中国）、安全远程访问环境（数据不落地中国本地存储）",
    supplementary_contractual: "员工合同中增加数据保护条款、强化集团内部数据保护协议",
    supplementary_organizational: "BCR框架下年度审计（德国母公司DPO主导）、中国子公司员工每季度DP培训",
    post_effectiveness: "有条件通过：BCR-C已获批提供全面保护框架；技术措施（加密+密钥分离+数据不落地）极大限制政府实际访问可能性；定期审计确保合规持续性。前提：所有补充措施持续有效并每年复审",
    key_actions: "年度复审中国法律变化、升级加密标准、完善审计日志",
    dpo_opinion: "有条件同意，建议每半年复核中国数据法律环境变化",
    review_date: "2026-07-01",
    attachment_role: "country_law_analysis"
  },
  payload: {
    transfer_tool: "bcr",
    data_exporter_profile: "Precision Manufacturing Group GmbH，德国斯图加特，全球精密制造集团母公司。持有已获批的BCR-C（控制者BCR）",
    data_importer_profile: "Precision Manufacturing (Shanghai) Co. Ltd，位于中国上海，集团全资子公司，负责亚太区生产和销售。角色：共同控制者",
    third_country_assessment: "中国法律环境评估：中国的《网络安全法》《数据安全法》《个人信息保护法》建立了全面的数据保护框架，但根据Schrems II标准，中国法律中存在若干可能影响传输保护水平的因素：（1）《网络安全法》第37条和《数据安全法》第21条赋予监管机构广泛的数据访问权限；（2）《国家情报法》第7条允许情报机构依法收集信息；（3）缺乏独立的司法审查机制来挑战政府数据请求。此外，中国尚未获得欧盟充分性认定",
    supplementary_measures: "技术措施：数据在传输前进行强加密（256-bit），密钥完全由德国出口方管理；实施了数据拆分存储策略（关键业务数据保留在德国，仅匿名化的运营指标传输至中国）；部署了安全的远程访问环境（数据不落地中国本地存储）。合同措施：在中国子公司员工合同中加入数据保护条款；与子公司签订强化的集团内部数据保护协议。组织措施：BCR框架下的年度审计（由德国母公司DPO主导）；中国子公司员工每季度数据保护培训",
    final_conclusion: "经评估，尽管中国法律环境存在风险，但通过以下因素组合，可以认为传输能提供GDPR要求的实质等同保护水平：（1）BCR-C已获批准，提供了全面的集团内部保护框架；（2）技术措施（加密+密钥分离+数据不落地）极大限制了政府实际访问数据的可能性；（3）定期审计机制确保了合规持续性。结论：有条件通过——前提是所有补充措施持续有效并每年复审",
    attachments: [{ file_role: "tia_main_report", file_name: "sample_contract.txt", file_format: "txt", storage_uri: "benchmarks/sample-inputs/sample_contract.txt" }]
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// PIPIA — 2 cases (from docx extraction)
// ═══════════════════════════════════════════════════════════════════════════

const pipiaSCCFiling: DevTestCase = {
  name: "PIPIA-1: 标准合同备案路径",
  description: "跨境电商向新加坡传输50万用户订单数据，非CIIO，不涉及敏感信息，走标准合同路径",
  jurisdiction: "CN",
  formDefaults: {
    company_name: "跨境优品（深圳）电子商务有限公司",
    company_uscc: "91440300MA1TEST003",
    industry: "电商零售",
    shareholding_structure: "境内自然人持股80%，境外VC持股20%",
    actual_controller: "张三（中国籍）",
    overseas_investment: "已在香港设立全资子公司用于海外仓储",
    org_structure_privacy_team: "设有数据合规部（3人），直接向CRO汇报",
    business_overview: "面向东南亚市场的跨境电商平台，主营中国制造消费品，年GMV约5亿元人民币",
    processing_activity_overview: "收集用户注册信息、浏览行为、订单信息、支付信息。使用数据分析进行个性化推荐",
    is_ciio: false,
    processing_person_count: 500000,
    outbound_pi_count: 500000,
    outbound_spi_count: 0,
    route_type: "scc_filing",
    outbound_scenario_name: "订单数据同步至亚太数据中心",
    outbound_frequency: "periodic",
    transfer_method: "API实时同步+每日批量导出",
    domestic_storage: "阿里云深圳Region",
    overseas_storage: "AWS新加坡Region（亚太数据中心）",
    transfer_link: "通过阿里云→AWS专线，经香港中转至新加坡",
    purpose: "将用户在平台上的订单数据同步至新加坡亚太数据中心，用于区域物流优化和精准营销",
    recipient_name: "跨境优品（香港）国际有限公司",
    recipient_country_region: "新加坡",
    legal_basis: "履行合同所必需+用户同意",
    legality_justification: "用户在下单时已通过弹窗方式获得单独同意，明确告知数据将传输至新加坡用于订单处理和物流优化",
    necessity_justification: "数据传输是完成跨境订单交付和提供物流跟踪服务所必需的。区域物流算法的优化分析不涉及个人精准画像",
    pi_categories: "姓名,手机号,收货地址,商品订单号,购买时间,商品金额,支付方式（去标识化）",
    spi_categories: "",
    subject_volume: 450000,
    notice_mechanism: "APP注册时弹窗告知数据出境情况；隐私政策中专设数据跨境传输章节",
    consent_mechanism: "用户下单时弹窗单独同意数据跨境传输，同意记录归档保存",
    dsar_channel: "privacy@kuajingyoupin.com",
    retention_policy: "订单数据保留至交易完成后3年（税法要求），营销分析数据保留2年",
    incident_response_sla_hours: 24,
    escalation_path: "安全事件→数据安全专员→CRO（2h内）→CEO（4h内）→网信办（24h内）",
    attachment_role: "scc_contract"
  },
  payload: {
    route_type: "scc_filing",
    company_profile: {
      company_name: "跨境优品（深圳）电子商务有限公司",
      industry: "电商零售",
      shareholding_structure: "境内自然人持股80%，境外VC持股20%",
      actual_controller: "张三（中国籍）",
      overseas_investment: "已在香港设立全资子公司用于海外仓储",
      org_structure_privacy_team: "设有数据合规部（3人），直接向CRO汇报",
      business_overview: "面向东南亚市场的跨境电商平台，主营中国制造消费品。年GMV约5亿元人民币",
      processing_activity_overview: "收集用户注册信息、浏览行为、订单信息、支付信息。使用数据分析进行个性化推荐",
      is_ciio: false,
      processing_person_count: 500000,
      outbound_pi_count: 500000,
      outbound_spi_count: 0
    },
    transfer_context: {
      transfer_scenario_name: "订单数据同步至亚太数据中心",
      transfer_frequency: "daily",
      transfer_method: "API实时同步+每日批量导出",
      domestic_storage: "阿里云深圳Region",
      overseas_storage: "AWS新加坡Region（亚太数据中心）",
      transfer_link: "通过阿里云→AWS专线，经香港中转至新加坡",
      purpose: "将用户在平台上的订单数据同步至新加坡亚太数据中心，用于区域物流优化和精准营销",
      recipient_name: "跨境优品（香港）国际有限公司",
      recipient_country_region: "新加坡",
      legal_basis: "履行合同所必需+用户同意",
      legality_justification: "用户在下单时已通过弹窗方式获得单独同意，明确告知数据将传输至新加坡用于订单处理和物流优化",
      necessity_justification: "数据传输是完成跨境订单交付和提供物流跟踪服务所必需的。区域物流算法的优化分析不涉及个人精准画像"
    },
    personal_info_scope: {
      pi_categories: ["姓名", "手机号", "收货地址", "商品订单号", "购买时间", "商品金额", "支付方式（去标识化处理为支付渠道编号）"],
      spi_categories: [],
      subject_volume: 450000
    },
    rights_protection: {
      notice_mechanism: "APP注册时弹窗告知数据出境情况；隐私政策中专设'数据跨境传输'章节。2024年度进行了隐私政策更新并征得用户重新确认",
      consent_mechanism: "用户下单时弹窗单独同意数据跨境传输，同意记录归档保存",
      dsar_channel: "APP内'我的→隐私中心→数据权利'提供在线表单、邮箱privacy@example.com",
      retention_policy: "订单数据保留至交易完成后3年（根据税法要求），营销分析数据保留2年"
    },
    emergency_plan: {
      incident_response_sla_hours: 24,
      escalation_path: "安全事件→数据安全专员→CRO（2小时内）→CEO（4小时内）→网信办（24小时内）",
      data_breach_notification_plan: "24小时内通知受影响的用户，48小时内向网信办报告"
    },
    attachments: [
      { file_role: "scc_contract", file_name: "sample_contract.txt", file_format: "txt", storage_uri: "benchmarks/sample-inputs/sample_contract.txt" }
    ]
  }
};

const pipiaCertification: DevTestCase = {
  name: "PIPIA-2: 个人信息保护认证路径",
  description: "金融科技公司向美国传输50万用户支付数据，含敏感金融信息，走认证路径",
  jurisdiction: "CN",
  formDefaults: {
    company_name: "快捷支付科技（北京）有限公司",
    company_uscc: "91110000MA1TEST004",
    industry: "金融科技",
    shareholding_structure: "境内自然人持股60%，母公司FastPay Global Inc.（美国）持股40%",
    actual_controller: "李四（中国籍）",
    overseas_investment: "母公司在美国纳斯达克上市",
    org_structure_privacy_team: "设有信息安全与数据合规部（8人），直接向CISO汇报",
    business_overview: "第三方支付平台，年处理交易额超500亿元人民币",
    processing_activity_overview: "收单、支付清结算、风控反欺诈、跨境支付",
    is_ciio: false,
    processing_person_count: 500000,
    outbound_pi_count: 500000,
    outbound_spi_count: 120000,
    route_type: "certification",
    outbound_scenario_name: "跨境支付清算数据处理",
    outbound_frequency: "continuous",
    transfer_method: "API实时传输+加密通道",
    domestic_storage: "自建数据中心（北京）",
    overseas_storage: "母公司美国AWS美西区",
    transfer_link: "通过企业VPN专线从北京→美西AWS",
    purpose: "向美国母公司提供支付交易数据用于全球风控模型训练和反欺诈分析",
    recipient_name: "FastPay Global Inc.",
    recipient_country_region: "美国",
    legal_basis: "用户单独同意",
    legality_justification: "用户开通跨境支付功能时通过人脸识别+短信验证码双因素确认后单独同意数据出境",
    necessity_justification: "全球反欺诈模型依赖多地区交易数据，单独使用中国数据无法有效识别跨境支付欺诈模式",
    pi_categories: "姓名,身份证号,手机号,银行卡号,交易时间,交易金额,交易对手方,设备指纹",
    spi_categories: "银行卡号,身份证号,金融交易记录",
    subject_volume: 500000,
    notice_mechanism: "开通跨境支付功能时弹窗告知；APP支付安全中心持续展示数据处理说明",
    consent_mechanism: "双因素认证后单独同意（人脸识别+短信验证码）",
    dsar_channel: "dpo@fastpay.cn",
    retention_policy: "交易数据保留5年（反洗钱法规要求），风控模型训练数据保留至模型迭代完成后删除",
    incident_response_sla_hours: 4,
    escalation_path: "安全事件→安全团队（30min内）→CISO→CEO（1h内）→监管部门（按法规时限）",
    attachment_role: "certification_material"
  },
  payload: {
    route_type: "certification",
    company_profile: {
      company_name: "快捷支付科技（北京）有限公司",
      industry: "金融科技",
      is_ciio: false,
      processing_person_count: 500000,
      outbound_pi_count: 500000,
      outbound_spi_count: 120000
    },
    transfer_context: {
      transfer_scenario_name: "跨境支付清算数据处理",
      transfer_frequency: "continuous",
      transfer_method: "API实时传输+加密通道",
      domestic_storage: "自建数据中心（北京）",
      overseas_storage: "母公司美国AWS美西区",
      transfer_link: "通过企业VPN专线从北京→美西AWS",
      purpose: "向美国母公司提供支付交易数据用于全球风控模型训练和反欺诈分析",
      recipient_name: "FastPay Global Inc.",
      recipient_country_region: "美国",
      legal_basis: "用户单独同意",
      legality_justification: "用户开通跨境支付功能时通过人脸识别+短信验证码双因素确认后单独同意数据出境",
      necessity_justification: "全球反欺诈模型依赖多地区交易数据，单独使用中国数据无法有效识别跨境支付欺诈模式"
    },
    personal_info_scope: {
      pi_categories: ["姓名", "身份证号", "手机号", "银行卡号", "交易时间", "交易金额", "交易对手方", "设备指纹"],
      spi_categories: ["银行卡号", "身份证号", "金融交易记录"],
      subject_volume: 500000
    },
    rights_protection: {
      notice_mechanism: "开通跨境支付功能时弹窗告知；APP'支付安全中心'持续展示数据处理说明",
      consent_mechanism: "双因素认证后单独同意（人脸识别+短信验证码）",
      dsar_channel: "APP内在线客服、邮箱dpo@fastpay.cn、400热线",
      retention_policy: "交易数据保留5年（反洗钱法规要求），风控模型训练数据保留至模型迭代完成后删除"
    },
    emergency_plan: {
      incident_response_sla_hours: 4,
      escalation_path: "安全事件→安全团队（30分钟内）→CISO→CEO（1小时内）→监管部门（按法规时限）",
      data_breach_notification_plan: "4小时内通知受影响用户和网信办"
    },
    attachments: [
      { file_role: "certification_material", file_name: "sample_evidence.txt", file_format: "txt", storage_uri: "benchmarks/sample-inputs/sample_evidence.txt" }
    ]
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// US 14117 — 2 cases (from docx extraction)
// ═══════════════════════════════════════════════════════════════════════════

const us14117Basic: DevTestCase = {
  name: "14117-1: 基本数据交易评估",
  description: "美国公司向中国受限主体传输基因组数据，触发14117行政令风险评估",
  jurisdiction: "US",
  formDefaults: {
    company_name: "American Genomics Research Institute",
    project_name: "国际合作基因组研究",
    transaction_description: "与深圳华大基因研究院合作进行大规模人群基因组研究，美方向中方传输约5万份去标识化基因组测序数据（BAM/FASTQ格式），中方负责生物信息学分析和变异注释",
    transaction_type: "cooperative_research"
  },
  payload: {
    project_name: "国际合作基因组研究",
    transaction_description: "与深圳华大基因研究院合作进行大规模人群基因组研究，美方向中方传输约5万份去标识化基因组测序数据（BAM/FASTQ格式），中方负责生物信息学分析和变异注释",
    transaction_type: "cooperative_research",
    data_items: [
      { data_category: "human_genomic_data", description: "5万份人类全基因组测序数据（BAM格式）", contains_human_genomic: true, volume: "50000", sensitivity: "high" },
      { data_category: "human_omic_data", description: "表型数据：年龄、性别、BMI、疾病诊断", contains_human_omic: true, volume: "50000", sensitivity: "high" },
      { data_category: "personal_identifier", description: "去标识化的受试者编号（可关联至原始样本）", contains_personal_identifier: true, volume: "50000", sensitivity: "medium" }
    ],
    recipient_entities: [
      { entity_name: "深圳华大基因研究院", country: "中国", entity_type: "research_institution", is_covered_person: false, is_restricted_party: false },
      { entity_name: "中国国家基因库", country: "中国", entity_type: "government_affiliated", is_covered_person: false, is_restricted_party: false }
    ],
    security_measures: [
      { measure_type: "data_minimization", description: "仅传输分析所必需的基因组区间，非全基因组" },
      { measure_type: "de_identification", description: "移除直接标识符，使用研究编号替代" },
      { measure_type: "contractual_controls", description: "研究合作协议包含数据安全条款" }
    ],
    company_name: "American Genomics Research Institute"
  }
};

const us14117RestrictedParty: DevTestCase = {
  name: "14117-2: 受限主体传输",
  description: "美国AI公司向被列入实体清单的中国公司传输训练数据，高风险合规案例",
  jurisdiction: "US",
  formDefaults: {
    company_name: "VisionAI Corp.",
    project_name: "AI模型训练数据共享",
    transaction_description: "与列入BIS实体清单的中国AI公司签订数据许可协议，向其提供用于计算机视觉模型训练的图像数据集（约100万张标注图片，含人脸和GPS坐标）",
    transaction_type: "vendor_agreement"
  },
  payload: {
    project_name: "AI模型训练数据共享",
    transaction_description: "与列入BIS实体清单的中国AI公司签订数据许可协议，向其提供用于计算机视觉模型训练的图像数据集（约100万张标注图片）",
    transaction_type: "vendor_agreement",
    data_items: [
      { data_category: "personal_identifier", description: "图像中包含可识别个人的面部信息", contains_personal_identifier: true, volume: "1000000", sensitivity: "high" },
      { data_category: "geolocation_data", description: "图像EXIF数据包含精确GPS坐标", contains_geolocation: true, volume: "1000000", sensitivity: "medium" },
      { data_category: "biometric_data", description: "人脸图像可用于面部识别模型训练", contains_biometric: true, volume: "1000000", sensitivity: "high" }
    ],
    recipient_entities: [
      { entity_name: "受限AI科技有限公司", country: "中国", entity_type: "commercial_entity", is_covered_person: false, is_restricted_party: true, restriction_reason: "列入BIS实体清单" },
      { entity_name: "受限AI科技的美国子公司", country: "美国", entity_type: "subsidiary", is_covered_person: false, is_restricted_party: false }
    ],
    access_persons: [
      { person_role: "data_scientist", nationality: "中国", access_level: "full", is_restricted_national: false, background_check: "standard" }
    ],
    security_measures: [
      { measure_type: "access_control", description: "基于角色的访问控制，仅授权研究人员可访问" },
      { measure_type: "audit_logging", description: "所有数据访问操作记录审计日志" }
    ],
    onward_transfer: true,
    onward_transfer_description: "数据可能被中国母公司再转移至其位于阿联酋的研发中心",
    company_name: "VisionAI Corp."
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// CN Flow (中国对华流动评估) — 2 cases
// ═══════════════════════════════════════════════════════════════════════════

const cnFlowBasic: DevTestCase = {
  name: "CN-FLOW-1: 基础对华数据流动评估",
  description: "美国电商平台向中国供应商传输订单数据，审查受限主体和敏感数据类别",
  jurisdiction: "US",
  formDefaults: {
    company_name: "GlobalShop Inc.",
    transfer_purpose: "向中国供应商传输订单信息用于商品生产和物流配送",
    data_categories: "客户姓名,收货地址,联系电话,商品订单号,SKU信息",
    sensitive_data_flags: "无敏感信息",
    transfer_chain: "美国总部→AWS美东区→通过加密API→中国供应商ERP系统。传输频率：每日实时",
    primary_recipient_name: "深圳智能制造有限公司",
    primary_recipient_country: "中国",
    primary_recipient_role: "vendor",
    primary_recipient_restricted: false
  },
  payload: {
    company_name: "GlobalShop Inc.",
    transfer_purpose: "向中国供应商传输订单信息用于商品生产和物流配送",
    data_categories: ["客户姓名", "收货地址", "联系电话", "商品订单号", "SKU信息"],
    sensitive_data_flags: ["无敏感信息"],
    recipient_entities: [
      { entity_name: "深圳智能制造有限公司", country: "中国", entity_role: "vendor", is_restricted_party: false, entity_type: "manufacturer" },
      { entity_name: "广州物流供应链有限公司", country: "中国", entity_role: "processor", is_restricted_party: false, entity_type: "logistics" }
    ],
    transfer_chain: "美国总部→AWS美东区→通过加密API→中国供应商ERP系统。传输频率：每日实时",
    attachments: [
      { file_role: "data_inventory", file_name: "data_inventory.csv", file_format: "csv", storage_uri: "benchmarks/sample-inputs/data_inventory.csv" },
      { file_role: "entity_inventory", file_name: "entity_inventory.csv", file_format: "csv", storage_uri: "benchmarks/sample-inputs/entity_inventory.csv" }
    ]
  }
};

const cnFlowRestricted: DevTestCase = {
  name: "CN-FLOW-2: 受限主体+敏感数据",
  description: "美国半导体公司向中国受限实体传输技术数据，涉及出口管制和高风险数据类别",
  jurisdiction: "US",
  formDefaults: {
    company_name: "Advanced Semiconductor Corp.",
    transfer_purpose: "向中国合作方提供芯片设计文件用于封装测试，技术数据可能涉及出口管制分类（ECCN 3E001）",
    data_categories: "芯片设计文件（GDSII格式）,测试规范文档,良率数据报告,工程师联系信息",
    sensitive_data_flags: "出口管制技术数据,可能涉及ECCN 3E001分类",
    transfer_chain: "美国总部安全服务器→通过加密VPN→上海公司内部服务器→（可能）再传输至北京研究所",
    primary_recipient_name: "上海先进半导体制造有限公司",
    primary_recipient_country: "中国",
    primary_recipient_role: "vendor",
    primary_recipient_restricted: false,
    additional_recipients: "北京微电子研究所,中国,affiliate,yes",
    internal_access_note: "内部员工访问需要双重认证和项目负责人批准。所有数据访问记录审计日志。中国籍员工可能接触技术数据"
  },
  payload: {
    company_name: "Advanced Semiconductor Corp.",
    transfer_purpose: "向中国合作方提供芯片设计文件用于封装测试，技术数据可能涉及出口管制分类",
    data_categories: ["芯片设计文件（GDSII格式）", "测试规范文档", "良率数据报告", "工程师联系信息"],
    sensitive_data_flags: ["出口管制技术数据", "可能涉及ECCN 3E001分类"],
    recipient_entities: [
      { entity_name: "上海先进半导体制造有限公司", country: "中国", entity_role: "vendor", is_restricted_party: false, entity_type: "semiconductor_manufacturer" },
      { entity_name: "北京微电子研究所", country: "中国", entity_role: "affiliate", is_restricted_party: true, entity_type: "government_affiliated", restriction_source: "Entity List" }
    ],
    transfer_chain: "美国总部安全服务器→通过加密VPN→上海公司内部服务器→（可能）再传输至北京研究所",
    internal_access_note: "内部员工访问需要双重认证和项目负责人批准。所有数据访问记录审计日志。中国籍员工可能接触技术数据",
    attachments: [
      { file_role: "data_inventory", file_name: "data_inventory.csv", file_format: "csv", storage_uri: "benchmarks/sample-inputs/data_inventory.csv" },
      { file_role: "entity_inventory", file_name: "entity_inventory.csv", file_format: "csv", storage_uri: "benchmarks/sample-inputs/entity_inventory.csv" }
    ]
  }
};


// ═══════════════════════════════════════════════════════════════════════════
// Document Review — 2 cases
// ═══════════════════════════════════════════════════════════════════════════

const reviewPrivacyPolicy: DevTestCase = {
  name: "审查-1: 隐私政策合规审查",
  description: "审查跨境电商平台隐私政策，检查跨境传输告知、敏感信息处理、用户权利行使路径与联系方式披露的完整性",
  jurisdiction: "CN",
  formDefaults: {
    company_name: "华东云链科技（测试）",
    publisher_entity: "华东云链科技（测试）",
    document_title: "跨境业务隐私政策（测试版）",
    document_version: "v2.3",
    effective_date: "2025-06-01",
    applicable_products: "华东云链SaaS平台、华东云链APP",
    applicable_scope: "面向全球用户的云服务平台的个人信息处理活动",
    is_live_version: true,
    document_type: "privacy_policy",
    receiver_name: "OceanStar Technology Pte. Ltd.",
    receiver_country: "新加坡",
    transfer_purpose: "跨境客服工单处理和统一运维支持",
    processor_identity_disclosed: true,
    scope_disclosed: true,
    collection_purpose_disclosed: true,
    processing_method_disclosed: true,
    category_disclosed: true,
    sensitive_pi_disclosed: false,
    crossborder_rule_disclosed: false,
    rights_channel_disclosed: true,
    contact_channel: "privacy@huadongcloud.com",
    pii_count: 280000,
    spi_count: 5000,
    has_scc_draft: false,
    review_focus: "重点核查跨境传输告知的完整性、敏感信息处理的合法性基础、用户权利行使路径与联系方式的披露"
  },
  payload: {
    company_name: "华东云链科技（测试）",
    document_type: "privacy_policy",
    receiver_name: "OceanStar Technology Pte. Ltd.",
    receiver_country: "新加坡",
    transfer_purpose: "跨境客服工单处理和统一运维支持",
    review_focus: "重点核查跨境传输告知、敏感信息处理、用户权利行使路径与联系方式披露",
    pii_count: 280000,
    spi_count: 5000
  }
};

const reviewSccContract: DevTestCase = {
  name: "审查-2: 智付通科技有限公司（个人信息出境标准合同）",
  description: "审查与新加坡支付网关服务商签订的个人信息出境标准合同草案，核查条款完整性、再委托、通知时限和数据主体权利保障",
  jurisdiction: "CN",
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
  payload: {
    company_name: "智付通科技有限公司",
    document_type: "scc_contract",
    receiver_name: "星洲支付处理有限公司 (Starstate Payment Processing Pte. Ltd.)",
    receiver_country: "新加坡",
    transfer_purpose: "跨境支付交易的风险筛查、欺诈监测、合规审计及资金结算处理",
    review_focus:
      "审查标准合同条款完整性、数据接收方义务、再委托限制、安全事件通知时限、删除规则与个人信息主体权利保障",
    pii_count: 500000,
    spi_count: 500000,
    has_scc_draft: true
  },
  backendFilePaths: [
    "resources/legal/sources/cn/references/个人信息出境标准合同【模板】.docx"
  ]
};

// ═══════════════════════════════════════════════════════════════════════════
// Exported registry
// ═══════════════════════════════════════════════════════════════════════════

export const DEV_TEST_CASES: Record<string, DevTestCase[]> = {
  cpra: [cpraTrendyGoods, cpraDataFlow, cpraFitLife],
  diagnosis: [diagEcommerce, diagMedical, diagAnonymous],
  assessment: [assessCIO, assessEcommerce],
  eu_scc: [euSccBasic, euSccHealthIndia, euSccModuleError],
  bcr: [bcrMediumRisk, bcrHighRisk, bcrStructuralFailure],
  dpia: [dpiaAIRecruitment, dpiaSmartCity],
  tia: [tiaBasicSCC, tiaChinaBCR],
  pipia: [pipiaSCCFiling, pipiaCertification],
  review: [reviewPrivacyPolicy, reviewSccContract],
  cn_flow: [cnFlowBasic, cnFlowRestricted],
  us_14117: [us14117Basic, us14117RestrictedParty],
};

export const MODULES_WITH_CASES = Object.keys(DEV_TEST_CASES) as string[];

export function getTestCases(module: string): DevTestCase[] {
  return DEV_TEST_CASES[module] ?? [];
}

const DEFAULT_CASE_INDEX: Record<string, number> = {
  diagnosis: 2,
  assessment: 1,
  review: 1,
};

export function getDefaultTestCase(module: string): DevTestCase | null {
  const cases = getTestCases(module);
  if (cases.length === 0) return null;
  const preferredIndex = DEFAULT_CASE_INDEX[module] ?? 0;
  return cases[preferredIndex] ?? cases[0] ?? null;
}
