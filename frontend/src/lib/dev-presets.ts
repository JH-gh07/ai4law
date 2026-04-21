export const DEV_ACCEL_ENABLED =
  import.meta.env.DEV && String(import.meta.env.VITE_ENABLE_DEV_ACCEL ?? "").toLowerCase() === "true";

export type AssessmentDevPreset = {
  id: string;
  title: string;
  scenarioDescription: string;
  expectedPath: "security_assessment" | "scc_or_certification" | "exemption";
  formDefaults: Record<string, unknown>;
  backendFilePaths: string[];
};

const ASSESSMENT_SECURITY_ASSESSMENT_PRESET: AssessmentDevPreset = {
  id: "assessment_cn_security_path",
  title: "一键体验主流程（安全评估路径）",
  scenarioDescription:
    "互联网平台向新加坡服务商持续传输用户账户与订单数据，规模触发安全评估阈值，含制度与数据清单附件。",
  expectedPath: "security_assessment",
  formDefaults: {
    company_name: "华东云链科技（测试）",
    company_uscc: "91310115MA1KTEST88",
    legal_representative: "李某",
    registered_address: "上海市浦东新区XX路88号",
    company_nature: "互联网平台企业",
    industry: "互联网SaaS",
    assessment_start_date: "2026-04-01",
    assessment_end_date: "2026-04-20",
    lead_department: "法务与数据合规部",
    participant_departments: "技术安全部、数据平台部、客服运营部",
    third_party_support: true,
    third_party_name: "合规顾问机构A",
    third_party_scope: "协助梳理出境链路与风险自评估材料",
    scenario_name: "跨境客服与运维支持",
    receiver_name: "OceanStar Technology Pte. Ltd.",
    transfer_frequency: "periodic",
    is_long_term: true,
    legal_basis: "履行跨境服务合同及履行法定义务",
    necessity_basis: "需由境外客服与运维团队处理工单和故障，无法完全在境内替代",
    receiver_country: "新加坡",
    is_ciio: false,
    contains_important_data: true,
    pii_count: 1600000,
    spi_count: 18000,
    transfer_purpose: "跨境客服、反欺诈风控与统一运维保障",
    data_inventory_summary: "账号标识、联系方式、交易记录、设备日志，覆盖近12个月跨境同步数据集",
    system_chain_summary: "境内业务库 -> 脱敏网关 -> 境外客服系统（新加坡）-> 运维审计平台",
    security_capability_summary: "跨境专线、传输加密、最小权限、审计留痕、异常告警与应急预案",
    force_override_path: false
  },
  backendFilePaths: [
    "storage/uploads/cn_regen_data_inventory_20260408_134644.csv",
    "storage/uploads/cn_regen_entity_inventory_20260408_134644.csv",
    "storage/uploads/regen_sample_scc.txt"
  ]
};

const ASSESSMENT_PRESET_MAP = new Map<string, AssessmentDevPreset>([
  [ASSESSMENT_SECURITY_ASSESSMENT_PRESET.id, ASSESSMENT_SECURITY_ASSESSMENT_PRESET]
]);

export const DEFAULT_ASSESSMENT_PRESET_ID = ASSESSMENT_SECURITY_ASSESSMENT_PRESET.id;

export function getAssessmentDevPreset(id: string = DEFAULT_ASSESSMENT_PRESET_ID): AssessmentDevPreset {
  return ASSESSMENT_PRESET_MAP.get(id) ?? ASSESSMENT_SECURITY_ASSESSMENT_PRESET;
}

