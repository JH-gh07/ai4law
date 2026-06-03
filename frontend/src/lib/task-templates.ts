import type { Jurisdiction, ModuleKey, WorkspaceStyleKey } from "./domain";

export type LocalizedText = {
  zh: string;
  en: string;
};

export type TaskTemplate = {
  id: string;
  jurisdiction: Jurisdiction;
  module: ModuleKey;
  workspaceStyle: WorkspaceStyleKey;
  title: LocalizedText;
  subtitle: LocalizedText;
  inputHint: LocalizedText;
  outputHint: LocalizedText;
};

export const TASK_TEMPLATES: TaskTemplate[] = [
  {
    id: "cn_diagnosis",
    jurisdiction: "CN",
    module: "diagnosis",
    workspaceStyle: "cn_diagnosis",
    title: { zh: "合规路径诊断", en: "Compliance Route Diagnosis" },
    subtitle: {
      zh: "通过智能问答快速识别安全评估/标准合同/认证路径",
      en: "Identify assessment/SCC/certification routes through guided Q&A"
    },
    inputHint: { zh: "一键诊断，明确合规路径", en: "Input: dynamic Q&A" },
    outputHint: { zh: "", en: "Output: diagnosis report" }
  },
  {
    id: "cn_assessment",
    jurisdiction: "CN",
    module: "assessment",
    workspaceStyle: "cn_assessment",
    title: { zh: "安全评估路径", en: "Security Assessment Path" },
    subtitle: {
      zh: "收集申报要件并生成《数据出境风险自评估报告》草案",
      en: "Collect filing inputs and draft security self-assessment report"
    },
    inputHint: { zh: "一键生成风险评估报告草案", en: "Input: forms + supporting files" },
    outputHint: { zh: "", en: "Output: risk self-assessment draft" }
  },
  {
    id: "cn_pipia",
    jurisdiction: "CN",
    module: "pipia",
    workspaceStyle: "cn_pipia",
    title: { zh: "认证/标准合同路径", en: "Certification / SCC Filing Path" },
    subtitle: {
      zh: "生成《个人信息保护影响评估（PIPIA）》草案",
      en: "Draft personal information protection impact assessment (PIPIA)"
    },
    inputHint: { zh: "一键生成个人信息保护评估报告", en: "Input: processing and transfer context" },
    outputHint: { zh: "", en: "Output: PIPIA draft report" }
  },
  {
    id: "cn_document_review",
    jurisdiction: "CN",
    module: "review",
    workspaceStyle: "cn_document_review",
    title: { zh: "文档专项智能审查", en: "Document Compliance Review" },
    subtitle: {
      zh: "审查隐私政策、标准合同、DPA 等并给出条款建议",
      en: "Review privacy policy, SCC, DPA and produce clause-level advice"
    },
    inputHint: { zh: "智能审阅合同、隐私政策等文件", en: "Input: contracts/policy text" },
    outputHint: { zh: "", en: "Output: document compliance report" }
  },
  {
    id: "eu_scc",
    jurisdiction: "EU",
    module: "eu_scc",
    workspaceStyle: "eu_scc",
    title: { zh: "SCC 审查", en: "SCC Review" },
    subtitle: { zh: "按 GDPR SCC 模块进行条款审查", en: "Clause review aligned with GDPR SCC modules" },
    inputHint: { zh: "审查跨境数据传输合同", en: "Input: SCC text/attachments" },
    outputHint: { zh: "", en: "Output: SCC compliance report" }
  },
  {
    id: "eu_bcr",
    jurisdiction: "EU",
    module: "bcr",
    workspaceStyle: "eu_bcr",
    title: { zh: "BCR 审核", en: "BCR Review" },
    subtitle: { zh: "按 EDPB 要求识别高风险缺口并分级", en: "Identify and rank BCR gaps against EDPB guidance" },
    inputHint: { zh: "审查集团内部规则", en: "Input: BCR text + group context" },
    outputHint: { zh: "", en: "Output: BCR review report" }
  },
  {
    id: "eu_dpia",
    jurisdiction: "EU",
    module: "dpia",
    workspaceStyle: "eu_dpia",
    title: { zh: "DPIA 草案生成", en: "DPIA Draft" },
    subtitle: { zh: "依据 GDPR 第35条生成 DPIA 草案", en: "Generate DPIA draft under GDPR Article 35" },
    inputHint: { zh: "一键生成数据保护影响评估草案", en: "Input: processing risk questionnaire" },
    outputHint: { zh: "", en: "Output: DPIA draft" }
  },
  {
    id: "eu_tia",
    jurisdiction: "EU",
    module: "tia",
    workspaceStyle: "eu_tia",
    title: { zh: "TIA 草案生成", en: "TIA Draft" },
    subtitle: {
      zh: "评估第三国保护水平与补充措施",
      en: "Assess third-country protection level and supplemental measures"
    },
    inputHint: { zh: "一键生成跨境传输影响评估草案", en: "Input: country + recipient + safeguards" },
    outputHint: { zh: "", en: "Output: TIA draft" }
  },
  {
    id: "us_14117",
    jurisdiction: "US",
    module: "us_14117",
    workspaceStyle: "us_14117",
    title: { zh: "14117 行政令合规", en: "EO 14117 Compliance" },
    subtitle: { zh: "识别涵盖人员/受关注国家 输出红黄绿结论", en: "Identify covered persons and output RED/YELLOW/GREEN" },
    inputHint: { zh: "输入数据清单、实体清单、交易信息", en: "Input: data inventory + entity inventory + transaction details" },
    outputHint: { zh: "", en: "Output: EO 14117 risk conclusion report" }
  },
  {
    id: "us_cpra",
    jurisdiction: "US",
    module: "cpra",
    workspaceStyle: "us_cpra",
    title: { zh: "CPRA 合规", en: "CPRA Compliance" },
    subtitle: { zh: "完成数据映射、告知与合同机制检查", en: "Check mapping, notices, and contractual controls" },
    inputHint: { zh: "一键生成加州隐私法合规报告", en: "Input: data mapping and governance materials" },
    outputHint: { zh: "", en: "Output: CPRA panorama report" }
  }
];

const TEMPLATE_MAP = new Map(TASK_TEMPLATES.map((item) => [item.id, item]));

export function listTaskTemplates(): TaskTemplate[] {
  return TASK_TEMPLATES;
}

export function listTaskTemplatesByJurisdiction(jurisdiction: Jurisdiction): TaskTemplate[] {
  return TASK_TEMPLATES.filter((item) => item.jurisdiction === jurisdiction);
}

export function findTaskTemplate(taskTemplateId: string): TaskTemplate | undefined {
  return TEMPLATE_MAP.get(taskTemplateId);
}

export function getDefaultTaskTemplate(jurisdiction: Jurisdiction): TaskTemplate {
  return (
    TASK_TEMPLATES.find((item) => item.jurisdiction === jurisdiction) ??
    TASK_TEMPLATES[0]
  );
}

export function getTaskTemplateTitle(taskTemplate: TaskTemplate, lang: "zh" | "en"): string {
  return taskTemplate.title[lang];
}

export function getTaskTemplateSubtitle(taskTemplate: TaskTemplate, lang: "zh" | "en"): string {
  return taskTemplate.subtitle[lang];
}

export function getTaskTemplateInputHint(taskTemplate: TaskTemplate, lang: "zh" | "en"): string {
  return taskTemplate.inputHint[lang];
}

export function getTaskTemplateOutputHint(taskTemplate: TaskTemplate, lang: "zh" | "en"): string {
  return taskTemplate.outputHint[lang];
}

export function buildSuggestedTaskName(taskTemplate: TaskTemplate, lang: "zh" | "en"): string {
  const today = new Date().toISOString().slice(0, 10);
  return lang === "zh" ? `${taskTemplate.title.zh} ${today}` : `${taskTemplate.title.en} ${today}`;
}
