import { describe, expect, it } from "vitest";

import { getModuleDevPreset } from "../../../lib/dev-presets";
import {
  createDefaultBcrValues,
  createDefaultDpiaValues,
  createDefaultEuSccValues,
  createDefaultTiaValues,
  type BcrFormValues,
  type DpiaFormValues,
  type EuSccFormValues,
  type TiaFormValues,
} from "../model";
import {
  buildBcrPayload,
  buildDpiaPayload,
  buildEuSccPayload,
  buildTiaPayload,
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
