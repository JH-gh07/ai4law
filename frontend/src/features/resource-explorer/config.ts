import type { ResourceLanguage } from "./contracts";

export const USER_INPUT_EXTENSIONS = new Set([
  "csv",
  "doc",
  "docx",
  "jpeg",
  "jpg",
  "json",
  "md",
  "pdf",
  "png",
  "txt",
  "xls",
  "xlsx",
]);

export const USER_FACING_OUTPUT_EXTENSIONS = new Set([
  "csv",
  "doc",
  "docx",
  "html",
  "md",
  "pdf",
  "xls",
  "xlsx",
  "zip",
]);

/** Unknown kinds stay hidden even when their extension looks downloadable. */
export const USER_FACING_ARTIFACT_KINDS = new Set([
  "annotated_docx",
  "docx",
  "html",
  "markdown",
  "md",
  "mitigation_plan_xlsx",
  "pdf",
  "report",
  "risk_matrix_xlsx",
  "xlsx",
  "zip",
]);

/** Request fields that are allowed to contribute entries to the input file list. */
export const INPUT_CONTAINER_KEYS = new Set(["attachments", "uploaded_files"]);

export const INTERNAL_ARTIFACT_PATTERNS = [
  "citation_map",
  "compliance_reasoning",
  "document_ir",
  "dpia_need_assessment",
  "evidence_chain",
  "facts.json",
  "findings.json",
  "generation_basis_pack",
  "internal_ai_review",
  "issue_list",
  "legal_grounding",
  "material_checklist",
  "path_judgment",
  "rule_engine_result",
  "trace_manifest",
  "writing_strategy",
] as const;

export const INPUT_SOURCE_KIND_LABELS: Record<string, Record<ResourceLanguage, string>> = {
  uploaded: { zh: "用户上传", en: "User Upload" },
  dev_preset: { zh: "预置案例", en: "Preset" },
  shared_scenario: { zh: "共享场景", en: "Shared Scenario" },
  inline: { zh: "内联输入", en: "Inline Input" },
};

export const INPUT_ROLE_LABELS: Record<string, Record<ResourceLanguage, string>> = {
  bcr: { zh: "BCR 材料", en: "BCR Material" },
  certification_material: { zh: "认证申请材料", en: "Certification Material" },
  country_law_analysis: { zh: "目的国法律分析", en: "Country Law Analysis" },
  data_flow_diagram: { zh: "数据流转图", en: "Data Flow Diagram" },
  data_inventory: { zh: "数据清单", en: "Data Inventory" },
  data_map: { zh: "数据映射材料", en: "Data Mapping Material" },
  dpia: { zh: "DPIA 材料", en: "DPIA Material" },
  entity_inventory: { zh: "实体清单", en: "Entity Inventory" },
  internal_policy: { zh: "内部制度文件", en: "Internal Policy" },
  privacy_policy: { zh: "隐私政策", en: "Privacy Policy" },
  rights_sop: { zh: "消费者权利 SOP", en: "Consumer Rights SOP" },
  scc_contract: { zh: "标准合同文本", en: "SCC Contract" },
  security_policy: { zh: "安全制度文件", en: "Security Policy" },
  supporting_evidence: { zh: "支撑证据材料", en: "Supporting Evidence" },
  supporting_material: { zh: "补充证明材料", en: "Supporting Material" },
  technical_control_doc: { zh: "技术控制说明", en: "Technical Control Note" },
  tia: { zh: "TIA 材料", en: "TIA Material" },
  transfer_agreement: { zh: "传输协议文本", en: "Transfer Agreement" },
  vendor_list: { zh: "供应商清单", en: "Vendor List" },
};

export const OUTPUT_STEM_LABELS: Record<string, Record<ResourceLanguage, string>> = {
  mitigation_plan: { zh: "风险缓解计划", en: "Mitigation Plan" },
  risk_matrix: { zh: "风险矩阵", en: "Risk Matrix" },
};
