import { describe, expect, it } from "vitest";

import { getModuleDevPreset } from "../../../lib/dev-presets";
import {
  createDefaultBcrValues,
  createDefaultCnFlowValues,
  createDefaultDocumentReviewValues,
  createDefaultDpiaValues,
  createDefaultEuSccValues,
  createDefaultTiaValues,
  createDefaultUs14117Values,
  type BcrFormValues,
  type CnFlowFormValues,
  type DocumentReviewFormValues,
  type DpiaFormValues,
  type EuSccFormValues,
  type TiaFormValues,
  type Us14117FormValues,
} from "../model";
import {
  buildBcrPayload,
  buildCnFlowPayload,
  buildDocumentReviewPayload,
  buildDpiaPayload,
  buildEuSccPayload,
  buildTiaPayload,
  buildUs14117Payload,
} from ".";

function withPreset<Values>(defaults: Values, module: "eu_scc" | "bcr" | "dpia" | "tia") {
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

  it("builds all BCR review items and typed attachments", () => {
    const input = withPreset<BcrFormValues>(createDefaultBcrValues(), "bcr");

    const payload = buildBcrPayload(input.values, input.paths);

    expect(payload.review_items).toHaveLength(10);
    expect(payload.review_items?.every((item) => item.finding && item.legal_basis)).toBe(true);
    expect(payload.attachments?.[0]?.file_format).toMatch(/^(docx|pdf)$/);
    expect(payload.uploaded_files).toEqual(input.paths);
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

  it("builds TIA assessment text and attachment metadata", () => {
    const input = withPreset<TiaFormValues>(createDefaultTiaValues(), "tia");

    const payload = buildTiaPayload(input.values, input.paths);

    expect(payload.third_country_assessment).toContain("已完成法律评估");
    expect(payload.final_conclusion).toContain("关键行动");
    expect(payload.attachments?.[0]?.file_role).toBe(input.values.attachment_role);
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
