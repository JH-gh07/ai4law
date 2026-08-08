import type { ModuleKey } from "./domain";

const stamp = () => new Date().toISOString().slice(11, 19).replace(/:/g, "");

const demoDiagnosis = () => ({
  company_name: `DemoDiag${stamp()}`,
  answers: {
    q1_is_ciio: "no",
    q2_has_important_data: "no",
    q3_pii_count: 46000,
    q4_spi_count: 2500,
    q5_no_personal_info: "no",
    q6_scenario: "contract_performance",
    q7_receiver_type: "third_party",
    q8_purpose: "境外客服与系统运维"
  }
});

const demoAssessment = () => ({
  company_name: `DemoAssess${stamp()}`,
  industry: "互联网SaaS",
  is_ciio: false,
  contains_important_data: false,
  pii_count: 1200000,
  spi_count: 15000,
  transfer_purpose: "全球客服与风控联防",
  receiver_country: "新加坡",
  force_override_path: false,
  uploaded_files: []
});

const demoReview = () => ({
  uploaded_files: []
});

const demoEuScc = () => ({
  company_name: `DemoSCC${stamp()}`,
  receiver_name: "OceanStar Technology Inc.",
  receiver_country: "新加坡",
  transfer_purpose: "境外客服与系统运维",
  pii_count: 46000,
  spi_count: 2500,
  has_scc_draft: true,
  uploaded_files: []
});

const demoPipia = () => ({
  route_type: "scc_filing",
  company_profile: {
    company_name: `DemoPIPIA${stamp()}`,
    company_uscc: "91310000XXXXXXXXXX",
    is_ciio: false,
    processing_person_count: 230000,
    outbound_pi_count: 46000,
    outbound_spi_count: 2500,
    industry: "互联网SaaS"
  },
  transfer_context: {
    purpose: "境外客服与系统运维",
    recipient_name: "OceanStar Technology Inc.",
    recipient_country_region: "美国加州",
    legal_basis: "合同履行必要"
  },
  personal_info_scope: {
    pi_categories: ["账户信息", "联系方式", "日志信息"],
    spi_categories: ["身份认证信息"],
    subject_volume: 46000
  },
  rights_protection: {
    notice_mechanism: "隐私政策+弹窗",
    consent_mechanism: "单独同意",
    dsar_channel: "privacy@example.com",
    retention_policy: "到期删除+最短必要"
  },
  emergency_plan: {
    incident_response_sla_hours: 24,
    escalation_path: "DPO -> 法务 -> 管理层"
  },
  attachments: [
    {
      file_role: "scc_contract",
      file_name: "regen_sample_scc.txt",
      file_format: "txt",
      storage_uri: "resources/legal/sources/cn/references/个人信息出境标准合同【模板】.docx"
    }
  ]
});

const demoBcr = () => ({
  company_name: `DemoBCR${stamp()}`,
  review_items: [
    {
      code: "3.2-C1",
      title: "结构完整性",
      score: "partial",
      finding: "章节覆盖不完整",
      legal_basis: "GDPR 第47条",
      recommendation: "补齐约束力与权利章节",
      evidence: "BCR-v1 第3章"
    },
    {
      code: "3.2-C2",
      title: "集团内部约束力",
      score: "compliant",
      finding: "已覆盖",
      legal_basis: "GDPR 第47条",
      recommendation: "保持",
      evidence: "BCR-v1 第4章"
    }
  ],
  attachments: []
});

const demoDpia = () => ({
  // 1. Identify need
  project_name: `Employee Health Assessment System ${stamp()}`,
  project_goal: "通过AI算法对员工健康数据进行评估、评分和分类，生成个性化健康画像",
  dpia_trigger_reasons: [
    "处理特殊类别个人数据（健康数据）GDPR Art 9",
    "自动化决策与画像处理 GDPR Art 22",
    "大规模处理 GDPR Art 35",
  ],

  // 2. Describe processing
  processing_flow_description: "收集员工体检报告、可穿戴设备健康数据、心理评估问卷结果，通过机器学习模型进行健康风险评分和个性化健康计划推荐，数据存储在欧盟境内但可能被美国母公司访问分析。",
  data_categories: ["姓名", "工号", "部门", "体检数据", "心率", "睡眠数据", "BMI", "心理评估结果", "用药记录"],
  special_category_data: true,
  special_category_types: ["健康数据", "医疗数据"],
  data_subject_categories: ["员工", "外部专家"],
  data_subject_count: "15,000人",
  retention_period: "员工在职期间及离职后5年",
  cross_border_transfer: true,
  transfer_destination: "United States",
  automated_decision_making: true,
  systematic_monitoring: false,
  large_scale_processing: true,
  data_matching: true,
  new_technology: true,
  vulnerable_data_subjects: true,

  // 3. Consultation
  consulted_internal_departments: ["法务部", "信息安全部", "HR部门", "工会"],
  external_experts: ["数据保护律师事务所", "独立隐私顾问"],
  data_subject_consultation_plan: "计划通过匿名问卷和员工代表座谈征询意见",

  // 4. Necessity & proportionality
  lawful_basis: ["GDPR Art 6(1)(b) 合同履行", "GDPR Art 9(2)(h) 职业医学"],
  necessity_statement: "处理员工健康数据是实现职业健康管理和法定职业病防治所必需。需详细论证为何必须使用AI算法而非传统人工评估方式处理该等数据，以及为何无法以侵入性更低的方式实现同等健康管理目标。",
  proportionality_statement: "仅收集与职业健康评估直接相关的健康数据指标，限制处理频率为年度评估+季度跟踪，存储期限与劳动法规定的档案保存期限一致。需进一步论证算法评分范围与健康管理目的相称。",
  transparency_information: "将通过员工隐私通知、入职文件和HR系统公告向员工告知健康数据的处理目的、法律依据、接收方、保留期限和数据主体权利，包括对自动化决策逻辑和预期后果的说明。",

  // 5. Risk assessment
  identified_risks: [
    {
      risk_id: "RISK-001",
      risk_description: "AI健康评分偏差可能导致对特定员工的歧视性健康评估",
      likelihood: "medium",
      impact: "high",
      affected_data_subjects: "员工",
      risk_source: "technology",
    },
    {
      risk_id: "RISK-002",
      risk_description: "健康数据跨境传输至美国母公司面临充分性认定缺失风险",
      likelihood: "high",
      impact: "high",
      affected_data_subjects: "全体员工",
      risk_source: "third_party",
    },
    {
      risk_id: "RISK-003",
      risk_description: "数据匹配与重识别可能超出原始收集目的",
      likelihood: "medium",
      impact: "medium",
      affected_data_subjects: "员工",
      risk_source: "processing_activity",
    },
  ],

  // 6. Mitigation
  mitigation_measures: [
    {
      mitigation_id: "MIT-001",
      description: "实施算法公平性审计和定期偏差检测，建立人工干预和申诉渠道",
      target_risk_ids: ["RISK-001"],
      status: "planned",
      responsible_party: "数据科学团队+法务部",
    },
    {
      mitigation_id: "MIT-002",
      description: "与美国母公司签署标准合同条款（SCCs），补充传输影响评估",
      target_risk_ids: ["RISK-002"],
      status: "in_progress",
      responsible_party: "法务部+信息安全部",
    },
  ],

  // 7. Sign-off & record
  dpia_owner: "张经理（数据保护负责人）",
  dpo_name: "李律师",
  dpo_opinion: "",
  review_date: "2026-06-03",

  // Attachments
  uploaded_files: ["health-data-flow.pdf", "algorithm-description.pdf", "privacy-policy-v2.pdf"],
});

const demoTia = () => ({
  transfer_tool: "scc",
  data_exporter_profile: "EU Exporter A",
  data_importer_profile: "US Importer B",
  third_country_assessment: "存在政府访问风险",
  supplementary_measures: "端到端加密、严格密钥管理、访问透明报告",
  final_conclusion: "在补充措施生效前提下SCC可传输",
  attachments: [
    {
      file_role: "transfer_agreement",
      file_name: "agreement.pdf",
      file_format: "pdf",
      storage_uri: "storage://uploads/agreement.pdf"
    }
  ]
});

const demoCnFlow = () => ({
  company_name: `DemoFlow${stamp()}`,
  transfer_purpose: "云服务监控与客服协同",
  data_categories: ["账户信息", "设备日志"],
  sensitive_data_flags: ["biometric"],
  recipient_entities: [
    {
      entity_name: "US ServiceCo",
      country_region: "美国",
      entity_role: "processor",
      is_restricted_party: false
    }
  ],
  transfer_chain: "CN Controller -> US ServiceCo (processor)",
  attachments: [
    {
      file_role: "data_inventory",
      file_name: "data_inventory.csv",
      file_format: "csv",
      storage_uri: "backend/tests/fixtures/cn/cn_flow_data_inventory.csv"
    },
    {
      file_role: "entity_inventory",
      file_name: "entity_inventory.csv",
      file_format: "csv",
      storage_uri: "backend/tests/fixtures/cn/cn_flow_entity_inventory.csv"
    }
  ]
});

const demoCpra = () => ({
  company_name: `DemoCPRA${stamp()}`,
  business_model: "SaaS",
  data_lifecycle: "收集-处理-存储-删除",
  notice_and_consent: "隐私告知缺失",
  consumer_rights_process: "目前仅邮箱接收",
  opt_out_and_sale_sharing: "存在共享但无opt-out",
  vendor_management: "供应商管理未体现DPA",
  attachments: [
    {
      file_role: "privacy_policy",
      file_name: "policy.url",
      file_format: "url",
      storage_uri: "https://example.com/privacy"
    }
  ]
});

const demoUs14117 = () => ({
  project_name: `EO14117评估${stamp()}`,
  transaction_description: "通过供应商协议向中国AI公司提供150,000名美国人的精确地理位置数据用于算法训练",
  transaction_type: "vendor_agreement",
  data_items: [
    {
      data_item_name: "精确GPS轨迹数据",
      data_description: "150,000名美国人的实时GPS轨迹数据（精度<10米）",
      business_context: "AI模型训练——位置预测算法",
      is_personal_info: true,
      is_sensitive_personal_info: true,
      us_person_count: 150000,
      data_subject_type: "consumer",
      doj_data_category: "precise_geolocation_data",
      precision_level: "raw",
      is_government_related: false,
      export_necessity: "算法训练所需训练数据"
    },
    {
      data_item_name: "用户邮箱地址",
      data_description: "150,000个用户的电子邮箱地址",
      business_context: "账号关联与通知",
      is_personal_info: true,
      is_sensitive_personal_info: false,
      us_person_count: 150000,
      data_subject_type: "consumer",
      doj_data_category: "",
      precision_level: "",
      is_government_related: false,
      export_necessity: "账号体系必须"
    }
  ],
  recipient_entities: [
    {
      entity_name: "深度洞察人工智能有限公司",
      country_of_registration: "China",
      tax_id: "",
      ownership_structure: "创始人持股60%，中国风投资本40%",
      governing_law: "中华人民共和国法律",
      government_control: false,
      government_investment: "",
      parent_company: "",
      entity_role: "processor"
    }
  ],
  access_persons: [
    {
      person_name: "王芳",
      nationality: "中国",
      country_of_residence: "中国",
      department: "AI研发部",
      position: "机器学习工程师",
      employer: "深度洞察人工智能有限公司",
      has_actual_access: true,
      access_type: "remote"
    }
  ],
  security_measures: [
    {
      measure_name: "logical_isolation_of_covered_data",
      category: "access_control",
      status: "missing",
      description: "尚未建立隔离工作区"
    },
    {
      measure_name: "encryption_at_rest",
      category: "encryption",
      status: "planned",
      description: "计划部署AES-256静态加密"
    }
  ],
  onward_transfer: false,
  onward_transfer_description: "",
  attachments: [],
  company_name: `DemoFlow${stamp()}`
});

export function buildDemoPayload(module: ModuleKey): unknown {
  switch (module) {
    case "diagnosis":
      return demoDiagnosis();
    case "assessment":
      return demoAssessment();
    case "review":
      return demoReview();
    case "eu_scc":
      return demoEuScc();
    case "pipia":
      return demoPipia();
    case "bcr":
      return demoBcr();
    case "dpia":
      return demoDpia();
    case "tia":
      return demoTia();
    case "cn_flow":
      return demoCnFlow();
    case "us_14117":
      return demoUs14117();
    case "cpra":
      return demoCpra();
    default:
      return {};
  }
}
