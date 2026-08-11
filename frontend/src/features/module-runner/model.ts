import { getDefaultPayload } from "../../api/modules";
import { DEV_ACCEL_ENABLED, getAssessmentDevPreset, getModuleDevPreset } from "../../lib/dev-presets";
import { extractInsight } from "../../lib/workspace";
import type {
  AssessmentFormValues,
  AssessmentStepConfig,
  AutoExtractResult,
  BcrFormValues,
  BcrStepConfig,
  CnFlowFormValues,
  CnFlowRecipientRole,
  CnFlowStepConfig,
  CpraFormValues,
  CpraStepConfig,
  DiagnosisFormValues,
  DiagnosisStepConfig,
  DocumentReviewExtractState,
  DocumentReviewFormValues,
  DpiaFormValues,
  DpiaStepConfig,
  EuSccFormValues,
  EuSccStepConfig,
  PipiaAttachmentRole,
  PipiaFormValues,
  PipiaRouteType,
  PipiaStepConfig,
  TiaFormValues,
  TiaStepConfig,
  Us14117FormValues,
  Us14117StepConfig,
  UserFacingResult,
} from "./types";

export type {
  AssessmentFormValues,
  AsyncRunProgressState,
  BcrFormValues,
  CnFlowFormValues,
  CpraFormValues,
  DiagnosisFieldConfig,
  DiagnosisFormValues,
  DocumentReviewExtractState,
  DocumentReviewFormValues,
  DpiaFormValues,
  EuSccFormValues,
  PipiaFormValues,
  TiaFormValues,
  Us14117FieldConfig,
  Us14117FormValues,
} from "./types";

export const US14117_STEPS: Us14117StepConfig[] = [
  {
    title: "交易基本信息",
    fields: [
      { name: "company_name", label: "企业名称", type: "text" },
      { name: "project_name", label: "项目名称", type: "text" },
      { name: "transaction_description", label: "交易描述（业务场景、数据传输内容、目的）", type: "textarea" },
      {
        name: "transaction_type",
        label: "交易类型",
        type: "select",
        options: ["vendor_agreement", "employment_agreement", "investment_agreement", "data_brokerage", "cooperative_research", "cloud_remote_access", "onward_transfer", "other"]
      }
    ]
  },
  {
    title: "数据分类与实体",
    fields: [
      { name: "data_item_name", label: "主要数据项名称", type: "text" },
      { name: "data_description", label: "数据描述（内容、格式、来源）", type: "textarea" },
      {
        name: "doj_data_category",
        label: "DOJ 数据类别",
        type: "select",
        options: ["human_genomic_data", "biometric_identifiers", "precise_geolocation_data", "personal_health_data", "personal_financial_data", "covered_personal_identifiers", "government_related_data", "not_14117_data"]
      },
      { name: "us_person_count", label: "涉及美国人数量（估算）", type: "number", min: 0, step: 1000 },
      { name: "entity_name", label: "接收方实体名称", type: "text" },
      { name: "country_of_registration", label: "接收方注册国家/地区", type: "text" },
      { name: "government_control", label: "接收方是否受政府控制", type: "checkbox" },
      {
        name: "entity_role",
        label: "接收方角色",
        type: "select",
        options: ["processor", "controller", "subprocessor", "affiliate", "vendor"]
      }
    ]
  },
  {
    title: "安全与再传输",
    fields: [
      { name: "onward_transfer", label: "是否涉及再传输", type: "checkbox" },
      { name: "onward_transfer_description", label: "再传输说明（如涉及）", type: "textarea" },
      { name: "security_measures_summary", label: "安全措施摘要（加密、访问控制、审计等）", type: "textarea" },
      { name: "review_focus", label: "本次重点审查关注项", type: "textarea" }
    ]
  },
  {
    title: "附件上传",
    fields: []
  }
];

export const JURISDICTIONS = ["CN", "EU", "US"] as const;

const diagnosisIsYes = (answers: DiagnosisFormValues, key: string): boolean => answers[key] === "yes";
export const DIAGNOSIS_STEP_SHORT_TITLES = ["业务基础", "合规需求", "数据处理", "数据流转", "系统架构"] as const;

export const DIAGNOSIS_STEPS: DiagnosisStepConfig[] = [
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

export const ASSESSMENT_STEPS: AssessmentStepConfig[] = [
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

export const PIPIA_STEPS: PipiaStepConfig[] = [
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

export const EU_SCC_STEPS: EuSccStepConfig[] = [
  {
    title: "传输主体与模块",
    fields: [
      { name: "exporter_name", label: "数据出口方（EEA）", type: "text" },
      { name: "importer_name", label: "数据进口方（第三国）", type: "text" },
      { name: "importer_country", label: "进口方国家/地区", type: "text" },
      { name: "transfer_role", label: "传输角色关系", type: "select", options: ["c2c", "c2p", "p2p", "p2c"] },
      { name: "declared_module_type", label: "文档声明的SCC模块", type: "select", options: ["Module One", "Module Two", "Module Three", "Module Four"] },
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
      { name: "has_tia", label: "已完成传输影响评估（TIA）", type: "checkbox" },
      { name: "has_supplementary_measures", label: "已落实有效补充措施", type: "checkbox" },
      { name: "government_access_response", label: "政府访问请求应对机制", type: "textarea" },
      { name: "supplementary_clause_review", label: "补充条款冲突检查关注点", type: "textarea" }
    ]
  },
  {
    title: "审查文件",
    fields: []
  }
];

export const BCR_STEPS: BcrStepConfig[] = [
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

export const DPIA_STEPS: DpiaStepConfig[] = [
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

export const TIA_STEPS: TiaStepConfig[] = [
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

export const BCR_REVIEW_ITEMS = [
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
] as const;

export const CN_FLOW_STEPS: CnFlowStepConfig[] = [
  {
    title: "出境数据清单",
    fields: [
      { name: "company_name", label: "企业名称", type: "text" },
      { name: "transfer_purpose", label: "出境目的", type: "textarea" },
      { name: "data_categories", label: "出境数据类别（逗号分隔）", type: "text" },
      { name: "sensitive_data_flags", label: "敏感/重点数据标签（逗号分隔）", type: "text" },
      { name: "us_person_count", label: "涉及美国个人数量", type: "text" },
      {
        name: "transaction_type",
        label: "交易类型",
        type: "select",
        options: ["vendor_agreement", "employment_agreement", "investment_agreement", "data_brokerage", "cooperative_research", "cloud_remote_access", "onward_transfer", "other"]
      },
      {
        name: "doj_data_category",
        label: "DOJ 数据分类（当前所有数据项）",
        type: "select",
        options: ["human_genomic_data", "biometric_identifiers", "precise_geolocation_data", "personal_health_data", "personal_financial_data", "covered_personal_identifiers", "government_related_data", "not_14117_data"]
      },
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

export const CPRA_STEPS: CpraStepConfig[] = [
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

export const splitCsv = (value: string): string[] =>
  value
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);

export const hasText = (value: string, minLength = 2): boolean => value.trim().length >= minLength;

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

export const assertInput = (condition: boolean, message: string): void => {
  if (!condition) {
    throw new Error(currentUiLang() === "zh" ? message : toEnglishValidation(message));
  }
};

export const basenameFromPath = (path: string): string => {
  const normalized = path.replace(/\\/g, "/");
  const chunks = normalized.split("/");
  return chunks[chunks.length - 1] || "attachment.txt";
};

export const inferAttachmentFormat = (value: string): "doc" | "docx" | "pdf" | "txt" | "md" | "json" | "csv" => {
  const suffix = value.split(".").pop()?.toLowerCase();
  if (suffix === "doc") return "doc";
  if (suffix === "docx") return "docx";
  if (suffix === "pdf") return "pdf";
  if (suffix === "md") return "md";
  if (suffix === "json") return "json";
  if (suffix === "csv") return "csv";
  return "txt";
};

export const getDocumentReviewFileKey = (file: File): string => `${file.name}-${file.size}-${file.lastModified}`;

export const getDocumentReviewFileExt = (name: string): string => {
  const normalized = name.toLowerCase();
  return normalized.includes(".") ? normalized.slice(normalized.lastIndexOf(".") + 1) : "";
};

export const isDocumentReviewTextPreviewExt = (ext: string): boolean => ["txt", "md", "json", "csv"].includes(ext);

export const isDocumentReviewImagePreviewExt = (ext: string): boolean =>
  ["png", "jpg", "jpeg", "gif", "webp", "bmp"].includes(ext);

export const canInlinePreviewDocumentReviewExt = (ext: string): boolean =>
  ext === "pdf" || isDocumentReviewTextPreviewExt(ext) || isDocumentReviewImagePreviewExt(ext);

export const getDocumentReviewTypeLabel = (ext: string): string => {
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

export const formatDocumentReviewFileSize = (size: number): string => {
  if (size >= 1024 * 1024) {
    const value = size / (1024 * 1024);
    return `${value >= 10 ? value.toFixed(0) : value.toFixed(1)} MB`;
  }
  return `${Math.max(1, Math.round(size / 1024))} KB`;
};

export const formatDocumentReviewFileDate = (value: number, lang: "zh" | "en"): string =>
  new Intl.DateTimeFormat(lang === "zh" ? "zh-CN" : "en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));

export const getDocumentReviewDocTypeLabel = (value: DocumentReviewFormValues["document_type"]): string => {
  if (value === "privacy_policy") return "隐私政策";
  if (value === "scc_contract") return "标准合同";
  if (value === "dpa") return "数据处理协议";
  return "其他文档";
};

export const getDocumentReviewExtractStatusMeta = (
  state?: DocumentReviewExtractState
): { label: string; tone: "neutral" | "loading" | "success" | "error" } => {
  if (!state) return { label: "待解析", tone: "neutral" };
  if (state.status === "loading") return { label: "解析中", tone: "loading" };
  if (state.status === "done") return { label: "已回填", tone: "success" };
  return { label: "需人工确认", tone: "error" };
};

export const inferDocxPdfFormat = (value: string): "docx" | "pdf" | null => {
  const suffix = value.split(".").pop()?.toLowerCase();
  if (suffix === "docx") return "docx";
  if (suffix === "pdf") return "pdf";
  return null;
};

export const inferDpiaAttachmentFormat = (value: string): "docx" | "pdf" | "png" | "jpg" | null => {
  const suffix = value.split(".").pop()?.toLowerCase();
  if (suffix === "docx") return "docx";
  if (suffix === "pdf") return "pdf";
  if (suffix === "png") return "png";
  if (suffix === "jpg" || suffix === "jpeg") return "jpg";
  return null;
};

export const inferCnFlowAttachmentFormat = (value: string): "xlsx" | "csv" | "docx" | "pdf" | null => {
  const suffix = value.split(".").pop()?.toLowerCase();
  if (suffix === "xlsx") return "xlsx";
  if (suffix === "csv") return "csv";
  if (suffix === "docx") return "docx";
  if (suffix === "pdf") return "pdf";
  return null;
};

export const inferCpraAttachmentFormat = (value: string): "docx" | "pdf" | "xlsx" | "csv" | null => {
  const suffix = value.split(".").pop()?.toLowerCase();
  if (suffix === "docx") return "docx";
  if (suffix === "pdf") return "pdf";
  if (suffix === "xlsx") return "xlsx";
  if (suffix === "csv") return "csv";
  return null;
};

export const isValidUrl = (value: string): boolean => /^https?:\/\/\S+$/i.test(value.trim());

export const parseRecipientRows = (raw: string): Array<{
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

export const toBcrScore = (value: string): "compliant" | "partial" | "non_compliant" => {
  const len = value.trim().length;
  if (len >= 48) return "compliant";
  if (len >= 16) return "partial";
  return "non_compliant";
};

export const composeBcrFinding = (score: "compliant" | "partial" | "non_compliant", evidence: string): string => {
  if (score === "compliant") return `已覆盖核心要求：${evidence}`;
  if (score === "partial") return `条款已涉及但表述不充分：${evidence}`;
  return `尚未形成可执行机制：${evidence}`;
};

export const createDefaultAssessmentValues = (): AssessmentFormValues => {
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

export const createDefaultDiagnosisValues = (): DiagnosisFormValues => {
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

export const createDefaultPipiaValues = (): PipiaFormValues => {
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

export const createDefaultDocumentReviewValues = (): DocumentReviewFormValues => {
  const demo = asRecord(getDefaultPayload("eu_scc"));
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

export const buildAutoExtractResult = async (file: File): Promise<AutoExtractResult> => {
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

export const seedDocumentReviewValuesForFile = (base: DocumentReviewFormValues, file: File): DocumentReviewFormValues => ({
  ...base,
  document_title: file.name.replace(/\.[^.]+$/, "") || base.document_title,
  document_type: inferDocTypeFromFileName(file.name),
  review_focus: inferReviewFocusFromText(file.name)
});

export const createDefaultEuSccValues = (): EuSccFormValues => {
  const demo = asRecord(getDefaultPayload("eu_scc"));
  const base: EuSccFormValues = {
    exporter_name: toString(demo.company_name, ""),
    importer_name: toString(demo.receiver_name, ""),
    importer_country: toString(demo.receiver_country, ""),
    transfer_role: "c2p",
    declared_module_type: "Module Two",
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
    has_tia: false,
    has_supplementary_measures: false,
    pii_count: toNumber(demo.pii_count, 0),
    spi_count: toNumber(demo.spi_count, 0),
    has_scc_draft: toBoolean(demo.has_scc_draft, true)
  };
  if (!DEV_ACCEL_ENABLED) return base;
  const preset = getModuleDevPreset("eu_scc");
  return { ...base, ...(preset.formDefaults as Partial<EuSccFormValues>) };
};

export const createDefaultBcrValues = (): BcrFormValues => {
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

export const createDefaultDpiaValues = (): DpiaFormValues => {
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

export const createDefaultTiaValues = (): TiaFormValues => {
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

export const createDefaultCnFlowValues = (): CnFlowFormValues => {
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
    us_person_count: toNumber(demo.us_person_count, 0),
    transaction_type: toString(demo.transaction_type, "vendor_agreement"),
    doj_data_category: "not_14117_data",
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

export const createDefaultUs14117Values = (): Us14117FormValues => ({
  company_name: "",
  project_name: "",
  transaction_description: "",
  transaction_type: "vendor_agreement",
  data_item_name: "",
  data_description: "",
  doj_data_category: "not_14117_data",
  us_person_count: 0,
  entity_name: "",
  country_of_registration: "",
  government_control: false,
  entity_role: "processor",
  onward_transfer: false,
  onward_transfer_description: "",
  security_measures_summary: "",
  review_focus: ""
});

export const createDefaultCpraValues = (): CpraFormValues => {
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

export const DOCUMENT_TYPE_LABEL: Record<DocumentReviewFormValues["document_type"], string> = {
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

export const localizeStepTitle = (lang: "zh" | "en", title: string): string =>
  lang === "en" ? (STEP_TITLE_EN[title] ?? title) : title;

export const localizeFieldLabel = (lang: "zh" | "en", fieldName: string, label: string): string =>
  lang === "en" ? (FIELD_LABEL_EN[fieldName] ?? humanizeKey(fieldName)) : label;

export const localizeOptionLabel = (lang: "zh" | "en", key: string, fallback: string): string =>
  lang === "en" ? (TEXT_EN_BY_ZH[fallback] ?? TEXT_EN_BY_ZH[key] ?? humanizeKey(key)) : fallback;

export const toFileName = (value: string): string => {
  const name = basenameFromPath(value);
  return name || value;
};

export const buildUserFacingResult = (response: unknown, lang: "zh" | "en"): UserFacingResult => {
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
    deliverablePaths: Array.from(
      new Set(
        [insight.reportPath, ...Object.values(insight.outputFiles)]
          .filter((item): item is string => typeof item === "string" && item.length > 0)
      )
    ),
    highlights,
    nextSteps
  };
};

void buildUserFacingResult;

export const REVIEW_ASYNC_STATE_LABEL: Record<string, string> = {
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
