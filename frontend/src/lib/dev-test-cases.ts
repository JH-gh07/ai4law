/**
 * 开发者模式 — 预编译测试案例 JSON payload。
 *
 * 每个案例对应 doc/数规通功能路径描述/ 中的一个测试案例 docx。
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
  name: "诊断-3: 智驾未来 匿名地图数据（豁免路径）",
  description: "自动驾驶公司出境匿名化传感器数据，不含个人信息也不涉重要数据→豁免路径",
  jurisdiction: "CN",
  payload: {
    company_name: "智驾未来",
    answers: {
      q1_is_ciio: "no",
      q2_has_important_data: "no",
      q3_pii_count: 0,
      q4_spi_count: 0,
      q5_no_personal_info: "yes",
      q6_scenario: "technology_development",
      q7_receiver_type: "parent_company",
      q8_purpose: "向德国母公司提供匿名化传感器数据包用于改进全球自动驾驶算法",
      m1_enterprise_name: "智驾未来",
      m1_industry: "智能制造",
      m1_business_channels: ["数据合作（与其他公司共享 / 交换数据）", "跨境服务（面向国外用户 / 业务涉及国外）"],
      m1_service_targets: "企业用户",
      m1_company_size: "大型（201-500人）"
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
  name: "评估-2: 优选购物 大型电商用户行为数据",
  description: "非CIIO电商平台，出境120万用户行为日志至开曼母公司，链路复杂涉及多次跨境",
  jurisdiction: "CN",
  payload: {
    company_name: "优选购物",
    industry: "电商零售",
    is_ciio: false,
    contains_important_data: false,
    pii_count: 1200000,
    spi_count: 0,
    transfer_purpose: "将用户浏览、点击、购买行为日志传输至母公司数据湖用于训练全球推荐算法模型",
    receiver_country: "开曼群岛",
    force_override_path: true,
    transfer_frequency: "continuous",
    receiver_name: "Global E-commerce Inc.",
    data_inventory_summary: "用户浏览记录、点击流、搜索关键词、购买历史、设备信息（已去标识化处理）。年出境用户数预计达120万人。数据类别：行为日志、交易记录",
    system_chain_summary: "通过阿里云国际站从杭州区域同步至新加坡区域，再转至母公司AWS美西区数据湖。链路长，涉及多次跨境和云服务商转换",
    security_capability_summary: "传输加密：TLS 1.3 + AES-256。访问控制：基于角色。去标识化：哈希+盐值处理用户ID。审计：操作日志留存180天",
    legal_document_review: "与母公司签订了《数据处理与共享协议》，但关于'再转移至AWS美西区的控制措施'描述不充分",
    personal_info_protection: "在APP隐私政策中披露了数据出境情况，但未对120万用户单独取得数据出境的'单独同意'（依赖隐私政策的概括同意）"
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// CN SCC (标准合同审查) — 3 cases
// ═══════════════════════════════════════════════════════════════════════════

const sccFinancial: DevTestCase = {
  name: "SCC-1: 金融数据处理者出境",
  description: "金融科技公司作为数据处理者向新加坡传输数据，标准合同条款审查发现高风险修改",
  jurisdiction: "CN",
  payload: {
    company_name: "数字支付科技（深圳）有限公司",
    receiver_name: "PayTech Singapore Pte Ltd",
    receiver_country: "新加坡",
    transfer_purpose: "为新加坡客户提供支付处理服务的境外技术支持",
    pii_count: 500000,
    spi_count: 120000,
    has_scc_draft: true,
    is_ciio: false,
    has_important_data: false,
    contract_summary: "标准合同第3.4条被修改为'数据接收方应在法律允许的范围内尽力通知数据提供方'而不是范本的'应当立即通知'。第8条关于数据安全事件的通知时限从72小时被改为'合理时间内'。附件中个人信息类别描述过于笼统（仅写'支付相关信息'）",
    data_fields: [
      { field_name: "姓名", category: "标识信息", is_sensitive: false },
      { field_name: "身份证号", category: "身份信息", is_sensitive: true },
      { field_name: "银行卡号", category: "金融账户信息", is_sensitive: true },
      { field_name: "手机号", category: "联系方式", is_sensitive: false },
      { field_name: "交易记录", category: "交易信息", is_sensitive: false }
    ]
  }
};

const sccMedicalResearch: DevTestCase = {
  name: "SCC-2: 医疗研究数据出境",
  description: "跨国药企向印度CRO传输临床试验数据，SCC条款修改评估，SPI分类错误",
  jurisdiction: "CN",
  payload: {
    company_name: "辉达制药（上海）有限公司",
    receiver_name: "MedResearch India Pvt Ltd",
    receiver_country: "印度",
    transfer_purpose: "委托印度CRO进行III期临床试验数据的统计分析和医学撰写",
    pii_count: 8500,
    spi_count: 8500,
    has_scc_draft: true,
    is_ciio: false,
    has_important_data: false,
    contract_summary: "标准合同中关于'数据删除'的条款约定为'合同终止后6个月内删除'，缺少'在数据处理目的完成后立即删除'的前置条件。附件将患者健康数据标记为'非敏感'。Clause 15(a)被修改为在政府请求通知义务中增加了'as soon as legally permissible'的限制条件",
    data_fields: [
      { field_name: "受试者编号", category: "标识信息", is_sensitive: false },
      { field_name: "年龄/性别", category: "人口统计", is_sensitive: false },
      { field_name: "诊断结果", category: "健康数据", is_sensitive: true },
      { field_name: "用药记录", category: "健康数据", is_sensitive: true },
      { field_name: "实验室检测结果", category: "健康数据", is_sensitive: true },
      { field_name: "不良事件记录", category: "健康数据", is_sensitive: true }
    ]
  }
};

const sccCloudProcessor: DevTestCase = {
  name: "SCC-3: 云服务商多方加入模块选择错误",
  description: "三层关系C→P→Sub-P应选用Module Three但误用Module Two，加入方信息缺失",
  jurisdiction: "CN",
  payload: {
    company_name: "橙子云科技（北京）有限公司",
    receiver_name: "Balkan IT Support DOO",
    receiver_country: "塞尔维亚",
    transfer_purpose: "将客户支持工单数据转委托给塞尔维亚子处理者处理",
    pii_count: 15000,
    spi_count: 0,
    has_scc_draft: true,
    is_ciio: false,
    has_important_data: false,
    contract_summary: "实际关系为：北欧零售集团（C）→橙子云（P）→巴尔干IT（Sub-P），应使用Module Three (P2P)但错误选择了Module Two (C2P)。Annex I.A中'加入方'信息仅写'见主服务协议'未完整填写。Clause 9子处理者授权机制中未明确书面授权方式"
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// EU SCC — 3 cases (from EU data export path)
// ═══════════════════════════════════════════════════════════════════════════

const euSccBasic: DevTestCase = {
  name: "EU-SCC-1: 基本合规的C2P模块",
  description: "德国电商→美国云服务商，C2P模块基本合规但有2个中风险问题（安全措施描述不足/数据类别笼统）",
  jurisdiction: "EU",
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
  payload: {
    transfer_tool: "scc",
    data_exporter_profile: "TechInnovate Ireland Ltd，注册于爱尔兰都柏林，为欧盟客户提供SaaS数据分析平台。作为数据控制者处理客户数据",
    data_importer_profile: "AnalyticsPro India Pvt Ltd，位于印度班加罗尔，为TechInnovate提供数据处理和技术支持服务。角色：数据处理者",
    third_country_assessment: "印度目前没有获得欧盟充分性认定。印度的数据保护法律（DPDP Act 2023）提供了基本保护框架，但政府机构的数据访问权限仍然较宽。根据Schrems II判决标准，印度法律在政府访问数据的必要性和相称性方面存在一定风险。印度《信息技术法》第69条赋予政府广泛的监控权力",
    supplementary_measures: "技术措施：端到端加密（数据在传输前加密，密钥由出口方管理，进口方无法解密）；数据最小化（仅传输分析所必需的数据字段）；假名化处理。合同措施：在SCC基础上增加透明度义务（进口方须在收到政府数据请求24小时内通知出口方）；定期审计权。组织措施：进口方员工定期数据保护培训；访问控制日志；事件响应SLA",
    final_conclusion: "经评估，在实施上述技术、合同和组织补充措施后，第三国法律不会损害SCC提供的实质等同保护水平。传输可继续进行，但需每年复审目的地法律变化",
    attachments: [{ file_role: "tia_main_report", file_name: "tia_report.docx", file_format: "docx", storage_uri: "storage/uploads/tia_report.docx" }]
  }
};

const tiaChinaBCR: DevTestCase = {
  name: "TIA-2: BCR传输至中国 有效性存疑",
  description: "德国制造集团→中国子公司，BCR工具，中国数据法律环境评估为高风险",
  jurisdiction: "EU",
  payload: {
    transfer_tool: "bcr",
    data_exporter_profile: "Precision Manufacturing Group GmbH，德国斯图加特，全球精密制造集团母公司。持有已获批的BCR-C（控制者BCR）",
    data_importer_profile: "Precision Manufacturing (Shanghai) Co. Ltd，位于中国上海，集团全资子公司，负责亚太区生产和销售。角色：共同控制者",
    third_country_assessment: "中国法律环境评估：中国的《网络安全法》《数据安全法》《个人信息保护法》建立了全面的数据保护框架，但根据Schrems II标准，中国法律中存在若干可能影响传输保护水平的因素：（1）《网络安全法》第37条和《数据安全法》第21条赋予监管机构广泛的数据访问权限；（2）《国家情报法》第7条允许情报机构依法收集信息；（3）缺乏独立的司法审查机制来挑战政府数据请求。此外，中国尚未获得欧盟充分性认定",
    supplementary_measures: "技术措施：数据在传输前进行强加密（256-bit），密钥完全由德国出口方管理；实施了数据拆分存储策略（关键业务数据保留在德国，仅匿名化的运营指标传输至中国）；部署了安全的远程访问环境（数据不落地中国本地存储）。合同措施：在中国子公司员工合同中加入数据保护条款；与子公司签订强化的集团内部数据保护协议。组织措施：BCR框架下的年度审计（由德国母公司DPO主导）；中国子公司员工每季度数据保护培训",
    final_conclusion: "经评估，尽管中国法律环境存在风险，但通过以下因素组合，可以认为传输能提供GDPR要求的实质等同保护水平：（1）BCR-C已获批准，提供了全面的集团内部保护框架；（2）技术措施（加密+密钥分离+数据不落地）极大限制了政府实际访问数据的可能性；（3）定期审计机制确保了合规持续性。结论：有条件通过——前提是所有补充措施持续有效并每年复审",
    attachments: [{ file_role: "tia_main_report", file_name: "tia_report_bcr.docx", file_format: "docx", storage_uri: "storage/uploads/tia_report_bcr.docx" }]
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// PIPIA — 2 cases (from docx extraction)
// ═══════════════════════════════════════════════════════════════════════════

const pipiaSCCFiling: DevTestCase = {
  name: "PIPIA-1: 标准合同备案路径",
  description: "跨境电商向新加坡传输50万用户订单数据，非CIIO，不涉及敏感信息，走标准合同路径",
  jurisdiction: "CN",
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
      { file_role: "scc_contract", file_name: "个人信息出境标准合同（草案）.docx", file_format: "docx", storage_uri: "storage/uploads/scc_draft.docx" }
    ]
  }
};

const pipiaCertification: DevTestCase = {
  name: "PIPIA-2: 个人信息保护认证路径",
  description: "金融科技公司向美国传输50万用户支付数据，含敏感金融信息，走认证路径",
  jurisdiction: "CN",
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
      { file_role: "certification_material", file_name: "个人信息保护认证申请材料.docx", file_format: "docx", storage_uri: "storage/uploads/cert_material.docx" }
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
      { file_role: "data_inventory", file_name: "data_inventory.xlsx", file_format: "xlsx", storage_uri: "storage/uploads/data_inventory.xlsx" },
      { file_role: "entity_inventory", file_name: "entity_inventory.xlsx", file_format: "xlsx", storage_uri: "storage/uploads/entity_inventory.xlsx" }
    ]
  }
};

const cnFlowRestricted: DevTestCase = {
  name: "CN-FLOW-2: 受限主体+敏感数据",
  description: "美国半导体公司向中国受限实体传输技术数据，涉及出口管制和高风险数据类别",
  jurisdiction: "US",
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
      { file_role: "data_inventory", file_name: "tech_data_inventory.xlsx", file_format: "xlsx", storage_uri: "storage/uploads/tech_data.xlsx" },
      { file_role: "entity_inventory", file_name: "entity_check.xlsx", file_format: "xlsx", storage_uri: "storage/uploads/entity_check.xlsx" }
    ]
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// Exported registry
// ═══════════════════════════════════════════════════════════════════════════

export const DEV_TEST_CASES: Record<string, DevTestCase[]> = {
  cpra: [cpraTrendyGoods, cpraDataFlow, cpraFitLife],
  diagnosis: [diagEcommerce, diagMedical, diagAnonymous],
  assessment: [assessCIO, assessEcommerce],
  scc: [sccFinancial, sccMedicalResearch, sccCloudProcessor],
  eu_scc: [euSccBasic, euSccHealthIndia, euSccModuleError],
  bcr: [bcrMediumRisk, bcrHighRisk, bcrStructuralFailure],
  dpia: [dpiaAIRecruitment, dpiaSmartCity],
  tia: [tiaBasicSCC, tiaChinaBCR],
  pipia: [pipiaSCCFiling, pipiaCertification],
  cn_flow: [cnFlowBasic, cnFlowRestricted],
  us_14117: [us14117Basic, us14117RestrictedParty],
};

export const MODULES_WITH_CASES = Object.keys(DEV_TEST_CASES) as string[];

export function getTestCases(module: string): DevTestCase[] {
  return DEV_TEST_CASES[module] ?? [];
}
