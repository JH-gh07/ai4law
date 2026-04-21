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

const demoScc = () => ({
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
      storage_uri: "storage/uploads/regen_sample_scc.txt"
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
  project_name: `DemoDPIA${stamp()}`,
  processing_description: "收集用户行为日志并用于推荐优化",
  purpose_and_necessity: "保障服务可用性并优化推荐准确率",
  lawful_basis: "合法利益+合同履行",
  risk_assessment: "存在画像偏差与过度处理风险",
  mitigation_measures: "去标识化、最小化、访问控制、审计",
  residual_risk: "中风险，可接受并持续监控",
  attachments: [
    {
      file_role: "data_flow_diagram",
      file_name: "flow.pdf",
      file_format: "pdf",
      storage_uri: "storage://uploads/flow.pdf"
    }
  ]
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
      storage_uri: "storage/uploads/cn_regen_data_inventory_20260408_134644.csv"
    },
    {
      file_role: "entity_inventory",
      file_name: "entity_inventory.csv",
      file_format: "csv",
      storage_uri: "storage/uploads/cn_regen_entity_inventory_20260408_134644.csv"
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

export function buildDemoPayload(module: ModuleKey): unknown {
  switch (module) {
    case "diagnosis":
      return demoDiagnosis();
    case "assessment":
      return demoAssessment();
    case "review":
      return demoReview();
    case "scc":
      return demoScc();
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
    case "cpra":
      return demoCpra();
    default:
      return {};
  }
}
