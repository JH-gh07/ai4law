import { describe, expect, it } from "vitest";

import { getModuleDevPreset } from "../../../lib/dev-presets";
import {
  createDefaultAssessmentValues,
  createDefaultBcrValues,
  createDefaultCnFlowValues,
  createDefaultCpraValues,
  createDefaultDiagnosisValues,
  createDefaultDocumentReviewValues,
  createDefaultDpiaValues,
  createDefaultEuSccValues,
  createDefaultPipiaValues,
  createDefaultTiaValues,
  createDefaultUs14117Values,
  type AssessmentFormValues,
  type BcrFormValues,
  type CnFlowFormValues,
  type CpraFormValues,
  type DiagnosisFormValues,
  type DocumentReviewFormValues,
  type DpiaFormValues,
  type EuSccFormValues,
  type PipiaFormValues,
  type TiaFormValues,
  type Us14117FormValues,
} from "../model";
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
} from ".";

function withPreset<Values>(
  defaults: Values,
  module: "assessment" | "pipia" | "eu_scc" | "bcr" | "dpia" | "tia",
) {
  const preset = getModuleDevPreset(module);
  return {
    paths: preset.backendFilePaths,
    values: { ...defaults, ...preset.formDefaults } as Values,
  };
}

describe("EU payload builders", () => {
  it("builds EU SCC role mapping without mutating inputs", () => {
    const input = withPreset<EuSccFormValues>(createDefaultEuSccValues(), "eu_scc");
    const before = structuredClone(input);

    const payload = buildEuSccPayload(input.values, input.paths);

    expect(payload.declared_module_type).toBe("Module Two");
    expect(payload.exporter_role).toBe("controller");
    expect(payload.importer_role).toBe("processor");
    expect(payload.uploaded_files).toEqual(input.paths);
    expect(input).toEqual(before);
  });

  it("uses explicit typed overrides for raw SCC cases", () => {
    const values = {
      ...createDefaultEuSccValues(),
      project_name_override: "Raw SCC case",
      scc_text_override: "MODULE THREE: preserved source text",
    };
    const payload = buildEuSccPayload(values, []);
    expect(payload.project_name).toBe("Raw SCC case");
    expect(payload.scc_text).toBe("MODULE THREE: preserved source text");
  });

  it("keeps the document module separate from the actual transfer roles", () => {
    const payload = buildEuSccPayload({
      ...createDefaultEuSccValues(),
      transfer_role: "p2p",
      declared_module_type: "Module Two",
    }, []);

    expect(payload.declared_module_type).toBe("Module Two");
    expect(payload.exporter_role).toBe("processor");
    expect(payload.importer_role).toBe("processor");
  });

  it("does not infer completed TIA or supplementary measures from review notes", () => {
    const base = createDefaultEuSccValues();
    const missing = buildEuSccPayload({
      ...base,
      government_access_response: "The review must address missing government-access safeguards.",
      supplementary_clause_review: "The review must identify missing supplementary measures.",
      has_tia: false,
      has_supplementary_measures: false,
    }, []);
    const completed = buildEuSccPayload({
      ...base,
      government_access_response: "",
      supplementary_clause_review: "",
      has_tia: true,
      has_supplementary_measures: true,
    }, []);

    expect(missing.has_tia).toBe(false);
    expect(missing.has_supplementary_measures).toBe(false);
    expect(completed.has_tia).toBe(true);
    expect(completed.has_supplementary_measures).toBe(true);
  });

  it("rejects missing SCC parties and unsupported transfer roles", () => {
    const input = withPreset<EuSccFormValues>(createDefaultEuSccValues(), "eu_scc");
    expect(() => buildEuSccPayload({ ...input.values, exporter_name: "" }, input.paths))
      .toThrow(/exporter_name/);
    expect(() => buildEuSccPayload(
      { ...input.values, transfer_role: "owner" } as unknown as EuSccFormValues,
      input.paths,
    )).toThrow(/transfer_role/);
  });

  it("builds all BCR review items and typed attachments", () => {
    const input = withPreset<BcrFormValues>(createDefaultBcrValues(), "bcr");

    const payload = buildBcrPayload(input.values, input.paths);

    expect(payload.review_items).toHaveLength(10);
    expect(payload.review_items?.every((item) => item.finding && item.legal_basis)).toBe(true);
    expect(payload.attachments?.[0]?.file_format).toMatch(/^(docx|pdf)$/);
    expect(payload.uploaded_files).toEqual(input.paths);
    expect(payload.uploaded_documents).toEqual(input.paths.map((filePath, index) => ({
      file_id: `bcr-upload-${index + 1}`,
      file_name: filePath.split("/").pop(),
      file_type: filePath.split(".").pop()?.toLowerCase(),
      file_path: filePath,
      document_role: index === 0 ? "main_bcr_document" : "other_attachment",
      auto_detected_role: false,
    })));
  });

  it("rejects missing BCR company names and unsupported attachments", () => {
    const input = withPreset<BcrFormValues>(createDefaultBcrValues(), "bcr");
    expect(() => buildBcrPayload({ ...input.values, company_name: "" }, input.paths))
      .toThrow(/company_name/);
    expect(() => buildBcrPayload(input.values, ["bcr.exe"]))
      .toThrow(/extension/);
  });

  it("builds structured DPIA risks and mitigation links", () => {
    const input = withPreset<DpiaFormValues>(createDefaultDpiaValues(), "dpia");

    const payload = buildDpiaPayload(input.values, input.paths);

    expect(payload.identified_risks?.length).toBeGreaterThan(0);
    expect(payload.mitigation_measures?.length).toBeGreaterThan(0);
    expect(payload.mitigation_measures?.[0]?.target_risk_ids).toEqual(
      payload.identified_risks?.map((risk) => risk.risk_id),
    );
    expect(payload.uploaded_files).toEqual(input.paths);
  });

  it("rejects missing DPIA project names and unsupported attachments", () => {
    const input = withPreset<DpiaFormValues>(createDefaultDpiaValues(), "dpia");
    expect(() => buildDpiaPayload({ ...input.values, project_name: "" }, input.paths))
      .toThrow(/project_name/);
    expect(() => buildDpiaPayload(input.values, ["flow.exe"]))
      .toThrow(/extension/);
  });

  it("builds TIA assessment text and attachment metadata", () => {
    const input = withPreset<TiaFormValues>(createDefaultTiaValues(), "tia");

    const payload = buildTiaPayload(input.values, input.paths);

    expect(payload.third_country_assessment).toContain("已完成法律评估");
    expect(payload.final_conclusion).toContain("关键行动");
    expect(payload.attachments?.[0]?.file_role).toBe(input.values.attachment_role);
  });

  it("rejects missing TIA exporters, unsupported tools and attachments", () => {
    const input = withPreset<TiaFormValues>(createDefaultTiaValues(), "tia");
    expect(() => buildTiaPayload({ ...input.values, data_exporter_name: "" }, input.paths))
      .toThrow(/data_exporter_name/);
    expect(() => buildTiaPayload(
      { ...input.values, transfer_tool: "contract" } as unknown as TiaFormValues,
      input.paths,
    )).toThrow(/transfer_tool/);
    expect(() => buildTiaPayload(input.values, ["assessment.exe"]))
      .toThrow(/extension/);
  });
});

describe("document review payload builder", () => {
  const paths = ["resources/legal/sources/cn/sample.md"];

  it("emits only fields accepted by ReviewGenerateRequest", () => {
    const values = createDefaultDocumentReviewValues();

    const payload = buildDocumentReviewPayload(values, paths);

    expect(payload.uploaded_files).toEqual(paths);
    expect(payload.scenario_context?.document_title).toBe(values.document_title);
    expect(payload.scenario_context?.has_scc_draft).toBe(values.has_scc_draft);
    expect(payload).not.toHaveProperty("company_name");
    expect(payload).not.toHaveProperty("receiver_name");
  });

  it("rejects a missing document title", () => {
    const values = { ...createDefaultDocumentReviewValues(), document_title: "" };
    expect(() => buildDocumentReviewPayload(values, paths)).toThrow(/document_title/);
  });

  it("rejects an unsupported document type", () => {
    const values = {
      ...createDefaultDocumentReviewValues(),
      document_type: "vendor_contract",
    } as unknown as DocumentReviewFormValues;
    expect(() => buildDocumentReviewPayload(values, paths)).toThrow(/document_type/);
  });

  it("rejects an unsupported review file extension", () => {
    expect(() => buildDocumentReviewPayload(createDefaultDocumentReviewValues(), ["sample.exe"]))
      .toThrow(/extension/);
  });
});

describe("CN Flow payload builder", () => {
  const values: CnFlowFormValues = {
    ...createDefaultCnFlowValues(),
    company_name: "GlobalShop Inc.",
    transfer_purpose: "向中国供应商传输订单信息用于履约",
    data_categories: "客户姓名,收货地址",
    transfer_chain: "美国总部 -> 中国供应商ERP",
    primary_recipient_name: "深圳供应商有限公司",
    primary_recipient_country: "中国",
    primary_recipient_role: "vendor",
  };
  const files = {
    dataInventory: ["data_inventory.csv"],
    entityInventory: ["entity_inventory.xlsx"],
    supporting: ["transfer_map.pdf"],
  };

  it("builds categorized attachments and recipient rows", () => {
    const payload = buildCnFlowPayload(
      { ...values, additional_recipients: "北京研究所,中国,affiliate,yes" },
      files,
    );

    expect(payload.attachments).toHaveLength(3);
    expect(payload.recipient_entities).toHaveLength(2);
    expect(payload.recipient_entities[1]?.is_restricted_party).toBe(true);
  });

  it("rejects a missing transfer purpose", () => {
    expect(() => buildCnFlowPayload({ ...values, transfer_purpose: "" }, files))
      .toThrow(/transfer_purpose/);
  });

  it("rejects an unsupported recipient role", () => {
    const invalid = { ...values, primary_recipient_role: "owner" } as unknown as CnFlowFormValues;
    expect(() => buildCnFlowPayload(invalid, files)).toThrow(/primary_recipient_role/);
  });

  it("rejects an unsupported attachment extension", () => {
    expect(() => buildCnFlowPayload(values, { ...files, dataInventory: ["inventory.exe"] }))
      .toThrow(/extension/);
  });
});

describe("US 14117 payload builder", () => {
  const values: Us14117FormValues = {
    ...createDefaultUs14117Values(),
    company_name: "VisionAI Corp.",
    project_name: "AI模型训练数据共享",
    transaction_description: "向境外供应商提供用于模型训练的数据集",
    data_item_name: "人脸图像",
    data_description: "包含可识别个人的面部信息",
    doj_data_category: "biometric_identifiers",
    us_person_count: 1000,
    entity_name: "受限AI科技有限公司",
    country_of_registration: "中国",
    entity_role: "vendor",
    security_measures_summary: "基于角色的访问控制和审计日志",
  };

  it("builds nested data, recipient and security measure arrays", () => {
    const payload = buildUs14117Payload(values, ["evidence.docx"]);

    expect(payload.data_items[0]?.data_item_name).toBe(values.data_item_name);
    expect(payload.recipient_entities[0]?.entity_name).toBe(values.entity_name);
    expect(payload.security_measures).toHaveLength(1);
    expect(payload.attachments).toEqual(["evidence.docx"]);
  });

  it("preserves typed nested overrides for complex cases", () => {
    const payload = buildUs14117Payload({
      ...values,
      data_items_override: [
        { data_item_name: "基因组", doj_data_category: "human_genomic_data", us_person_count: 50000 },
        { data_item_name: "表型数据", doj_data_category: "human_omic_data", us_person_count: 50000 },
      ],
      recipient_entities_override: [
        { entity_name: "研究院", country_of_registration: "中国", entity_role: "research_institution" },
      ],
    }, []);
    expect(payload.data_items).toHaveLength(2);
    expect(payload.recipient_entities[0]?.entity_role).toBe("research_institution");
  });

  it("rejects a missing project name", () => {
    expect(() => buildUs14117Payload({ ...values, project_name: "" }, []))
      .toThrow(/project_name/);
  });

  it("rejects an unsupported transaction type", () => {
    expect(() => buildUs14117Payload({ ...values, transaction_type: "sale" }, []))
      .toThrow(/transaction_type/);
  });

  it("rejects an unsupported attachment extension", () => {
    expect(() => buildUs14117Payload(values, ["evidence.exe"]))
      .toThrow(/extension/);
  });
});

describe("diagnosis payload builder", () => {
  it("maps questionnaire values to typed answers", () => {
    const values = createDefaultDiagnosisValues();
    const payload = buildDiagnosisPayload(values);

    expect(payload.company_name.length).toBeGreaterThanOrEqual(2);
    expect(payload.answers).toHaveProperty("q6_scenario", "other");
  });

  it("preserves the existing fallback for a missing company name", () => {
    const payload = buildDiagnosisPayload({ ...createDefaultDiagnosisValues(), company_name: "" });
    expect(payload.company_name).toBe("未命名企业");
  });

  it("rejects an unsupported yes/no questionnaire value", () => {
    const values: DiagnosisFormValues = {
      ...createDefaultDiagnosisValues(),
      m3_processes_personal_info: "maybe",
    };
    expect(() => buildDiagnosisPayload(values)).toThrow(/m3_processes_personal_info/);
  });
});

describe("assessment payload builder", () => {
  const input = withPreset<AssessmentFormValues>(createDefaultAssessmentValues(), "assessment");

  it("builds a request with normalized counts and uploaded files", () => {
    const payload = buildAssessmentPayload(input.values, input.paths);
    expect(payload.uploaded_files).toEqual(input.paths);
    expect(payload.pii_count).toBeGreaterThanOrEqual(0);
  });

  it("rejects a missing company USCC", () => {
    expect(() => buildAssessmentPayload({ ...input.values, company_uscc: "" }, input.paths))
      .toThrow(/company_uscc/);
  });

  it("rejects an unsupported attachment extension", () => {
    expect(() => buildAssessmentPayload(input.values, ["inventory.exe"]))
      .toThrow(/extension/);
  });
});

describe("PIPIA payload builder", () => {
  const input = withPreset<PipiaFormValues>(createDefaultPipiaValues(), "pipia");

  it("builds nested PIPIA request sections", () => {
    const payload = buildPipiaPayload(input.values, input.paths);
    expect(payload.company_profile.company_uscc).toBe(input.values.company_uscc);
    expect(payload.attachments).toHaveLength(input.paths.length);
  });

  it("rejects an unsupported route type", () => {
    const invalid = { ...input.values, route_type: "assessment" } as unknown as PipiaFormValues;
    expect(() => buildPipiaPayload(invalid, input.paths)).toThrow(/route_type/);
  });

  it("preserves supporting evidence without pretending it is an SCC contract", () => {
    const values = { ...input.values, route_type: "scc_filing", attachment_role: "supporting_evidence" } as const;
    const payload = buildPipiaPayload(values, input.paths);

    expect(payload.attachments[0]?.file_role).toBe("supporting_evidence");
  });

  it("rejects an unsupported attachment extension", () => {
    expect(() => buildPipiaPayload(input.values, ["evidence.exe"]))
      .toThrow(/extension/);
  });
});

describe("CPRA payload builder", () => {
  const values: CpraFormValues = {
    ...createDefaultCpraValues(),
    company_name: "TrendyGoods Inc.",
    business_model: "加州电商零售平台",
    data_lifecycle: "收集订单并用于履约",
    notice_and_consent: "收集时告知",
    privacy_policy_url: "https://example.com/privacy",
    consumer_rights_process: "在线受理访问和删除请求",
    opt_out_and_sale_sharing: "提供 Do Not Sell or Share 入口",
  };
  const files = { privacyPolicy: [], rightsSop: [], dataMap: [], vendorList: [], other: [] };

  it("builds a URL attachment without uploaded files", () => {
    const payload = buildCpraPayload(values, files);
    expect(payload.attachments[0]?.file_format).toBe("url");
  });

  it("rejects a missing business model", () => {
    expect(() => buildCpraPayload({ ...values, business_model: "" }, files))
      .toThrow(/business_model/);
  });

  it("rejects an invalid privacy policy URL", () => {
    expect(() => buildCpraPayload({ ...values, privacy_policy_url: "example.com" }, files))
      .toThrow(/privacy_policy_url/);
  });

  it("rejects an unsupported attachment extension", () => {
    expect(() => buildCpraPayload({ ...values, privacy_policy_url: "" }, { ...files, privacyPolicy: ["policy.exe"] }))
      .toThrow(/extension/);
  });
});
