import { describe, expect, expectTypeOf, it } from "vitest";

import type { ModuleRequestMap } from "../api/api-contract";
import { DEV_TEST_CASES } from "./dev-test-cases";
import genomicRedScenario from "../../../benchmarks/cases/us_14117/geneguard_genomic_red/scenario.json";
import geolocationYellowScenario from "../../../benchmarks/cases/us_14117/geneguard_geolocation_yellow/scenario.json";
import telemetryGreenScenario from "../../../benchmarks/cases/us_14117/geneguard_telemetry_green/scenario.json";
import franceUkSccScenario from "../../../benchmarks/cases/eu_scc/france_c2c_uk_aws/scenario.json";
import germanyIndiaSccScenario from "../../../benchmarks/cases/eu_scc/germany_c2p_india_health/scenario.json";
import netherlandsSerbiaSccScenario from "../../../benchmarks/cases/eu_scc/netherlands_p2p_serbia_module_error/scenario.json";


const asRecord = (value: unknown): Record<string, unknown> => {
  expect(value).toBeTypeOf("object");
  expect(value).not.toBeNull();
  expect(Array.isArray(value)).toBe(false);
  return value as Record<string, unknown>;
};

describe("developer test case API contracts", () => {
  it("keeps form defaults as the canonical input for every case", () => {
    const fileBackedModules = new Set([
      "assessment",
      "review",
      "pipia",
      "bcr",
      "dpia",
      "tia",
      "eu_scc",
      "cn_flow",
    ]);

    for (const [module, cases] of Object.entries(DEV_TEST_CASES)) {
      for (const testCase of cases) {
        expect(testCase.formDefaults, `${module}/${testCase.name}`).toBeTypeOf("object");
        const allowsInlineScc = module === "eu_scc" && testCase.backendFilePaths?.length === 0;
        if (fileBackedModules.has(module) && !allowsInlineScc) {
          expect(testCase.backendFilePaths?.length, `${module}/${testCase.name}`).toBeGreaterThan(0);
        }
        if (allowsInlineScc) {
          expect(String(asRecord(testCase.payload).scc_text).length).toBeGreaterThan(100);
        }
      }
    }
  });

  it("keeps the registry at 27 independently runnable cases", () => {
    expect(Object.values(DEV_TEST_CASES).flat()).toHaveLength(27);
  });

  it("binds every case payload to its generated module request", () => {
    expectTypeOf<(typeof DEV_TEST_CASES)["diagnosis"][number]["payload"]>().toMatchTypeOf<
      ModuleRequestMap["diagnosis"]
    >();
    expectTypeOf<(typeof DEV_TEST_CASES)["pipia"][number]["payload"]>().toMatchTypeOf<
      ModuleRequestMap["pipia"]
    >();
    expectTypeOf<(typeof DEV_TEST_CASES)["review"][number]["payload"]>().toMatchTypeOf<
      ModuleRequestMap["review"]
    >();
  });

  it("uses current diagnosis enum values", () => {
    const scenarios = new Set(["contract_performance", "hr_management", "emergency", "legal_duty", "other"]);
    const receiverTypes = new Set(["intra_group", "third_party"]);

    for (const testCase of DEV_TEST_CASES.diagnosis) {
      const answers = asRecord(testCase.payload.answers);
      expect(scenarios.has(String(answers.q6_scenario))).toBe(true);
      expect(receiverTypes.has(String(answers.q7_receiver_type))).toBe(true);
    }
  });

  it("uses structured assessment fields", () => {
    for (const testCase of DEV_TEST_CASES.assessment) {
      const payload = asRecord(testCase.payload);
      for (const field of ["legal_document_review", "compliance_history", "personal_info_protection"] as const) {
        const value = payload[field];
        if (value !== undefined && value !== null) asRecord(value);
      }
    }
  });

  it("includes all required BCR review item fields", () => {
    for (const testCase of DEV_TEST_CASES.bcr) {
      for (const item of testCase.payload.review_items as Array<Record<string, unknown>>) {
        expect(String(item.finding ?? "").length).toBeGreaterThan(1);
        expect(String(item.legal_basis ?? "").length).toBeGreaterThan(1);
        expect(String(item.recommendation ?? "").length).toBeGreaterThan(1);
      }
      const context = asRecord(testCase.payload.scenario_context);
      expect(String(context.company_name ?? "").length).toBeGreaterThan(1);
      expect(String(context.eu_liable_entity ?? "").length).toBeGreaterThan(1);
      expect(context.group_name).toBeUndefined();
      expect(asRecord(context.auto_extracted_facts).data_flow_scope).toBeTypeOf("string");
    }
  });

  it("uses current TIA attachment enums", () => {
    const roles = new Set(["transfer_agreement", "country_law_analysis", "technical_control_doc", "other"]);
    for (const testCase of DEV_TEST_CASES.tia) {
      for (const attachment of testCase.payload.attachments as Array<Record<string, unknown>>) {
        expect(roles.has(String(attachment.file_role))).toBe(true);
        expect(["docx", "pdf"]).toContain(attachment.file_format);
      }
    }
  });

  it("builds the official SCC requests without changing shared facts", () => {
    const canonicalRequest = (request: ModuleRequestMap["eu_scc"]) => ({
      ...request,
      scc_text: request.scc_text.trim(),
    });
    expect(DEV_TEST_CASES.eu_scc[0].payload).toEqual(canonicalRequest(franceUkSccScenario.request as ModuleRequestMap["eu_scc"]));
    expect(DEV_TEST_CASES.eu_scc[1].payload).toEqual(canonicalRequest(germanyIndiaSccScenario.request as ModuleRequestMap["eu_scc"]));
    expect(DEV_TEST_CASES.eu_scc[2].payload).toEqual(canonicalRequest(netherlandsSerbiaSccScenario.request as ModuleRequestMap["eu_scc"]));
  });

  it("keeps TIA cases aligned with the official US SaaS and India clinical scenarios", () => {
    const [usSaas, indiaClinical] = DEV_TEST_CASES.tia;

    expect(usSaas.payload.data_exporter_profile).toContain("Innovate Software GmbH");
    expect(usSaas.payload.data_importer_profile).toContain("CloudForce Inc.");
    expect(usSaas.payload.data_importer_profile).toContain("美国");
    expect(usSaas.payload.third_country_assessment).toContain("FISA 702");
    expect(usSaas.payload.third_country_assessment).toContain("CLOUD Act");
    expect(usSaas.payload.supplementary_measures).toContain("密钥");

    expect(indiaClinical.payload.data_exporter_profile).toContain("Leiden Life Sciences Institute");
    expect(indiaClinical.payload.data_importer_profile).toContain("New Delhi Clinical Research Pvt. Ltd.");
    expect(indiaClinical.payload.data_importer_profile).toContain("印度");
    expect(indiaClinical.payload.data_exporter_profile).toContain("基因组序列片段");
    expect(indiaClinical.payload.third_country_assessment).toContain("IT Act第69条");
    expect(indiaClinical.payload.supplementary_measures).toContain("安全飞地");
    expect(indiaClinical.payload.final_conclusion).toContain("荷兰 AP");
  });

  it("includes current PIPIA company profile fields", () => {
    for (const testCase of DEV_TEST_CASES.pipia) {
      const company = asRecord(testCase.payload.company_profile);
      expect(String(company.company_uscc ?? "").length).toBeGreaterThanOrEqual(8);
    }
  });

  it("keeps PIPIA cases aligned with the official SCC and certification scenarios", () => {
    const [ecommerce, certification] = DEV_TEST_CASES.pipia;

    expect(ecommerce.payload.route_type).toBe("scc_filing");
    expect(ecommerce.payload.company_profile.company_name).toBe("海淘优选（杭州）科技有限公司");
    expect(ecommerce.payload.company_profile.processing_person_count).toBe(8_000_000);
    expect(ecommerce.payload.company_profile.outbound_pi_count).toBe(500_000);
    expect(ecommerce.payload.transfer_context.recipient_name).toBe("SeaCommerce Pte. Ltd.");
    expect(ecommerce.payload.personal_info_scope.pi_categories).toContain("Hashed_Device_ID");
    expect(ecommerce.payload.personal_info_scope.pi_categories).toContain("Product_Category_Preference");

    expect(certification.payload.route_type).toBe("certification");
    expect(certification.payload.company_profile.company_name).toBe("智付通科技有限公司");
    expect(certification.payload.company_profile.outbound_pi_count).toBe(50_000);
    expect(certification.payload.transfer_context.recipient_name).toBe("EuroCert");
    expect(certification.payload.transfer_context.recipient_country_region).toBe("德国");
    expect(certification.payload.personal_info_scope.pi_categories).toContain("Contact_Email");
    expect(certification.payload.transfer_context.legal_basis).toContain("欧盟认证要求");
  });

  it("provides review files to the single-request developer endpoint", () => {
    for (const testCase of DEV_TEST_CASES.review) {
      expect(testCase.payload.uploaded_files).toEqual(testCase.backendFilePaths);
      expect(testCase.backendFilePaths?.length).toBeGreaterThan(0);
    }
  });

  it("uses current CN Flow recipient fields", () => {
    for (const testCase of DEV_TEST_CASES.cn_flow) {
      for (const entity of testCase.payload.recipient_entities as Array<Record<string, unknown>>) {
        expect(String(entity.country_region ?? "").length).toBeGreaterThan(1);
        expect(entity.country).toBeUndefined();
      }
    }
  });

  it("reuses the official EO 14117 red and yellow facts in CN Flow compatibility cases", () => {
    const [red, yellow] = DEV_TEST_CASES.cn_flow;

    expect(red.payload.company_name).toBe("GeneGuard生物科技公司");
    expect(red.payload.us_person_count).toBe(10_000);
    expect(red.payload.recipient_entities[0].entity_name).toBe("华源生命科学有限公司");
    expect(red.payload.doj_data_category_by_item).toMatchObject({
      全基因组测序原始数据: "human_genomic_data",
    });

    expect(yellow.payload.company_name).toBe("GeneGuard生物科技公司");
    expect(yellow.payload.us_person_count).toBe(150_000);
    expect(yellow.payload.recipient_entities[0].entity_name).toBe("深度洞察人工智能有限公司");
    expect(yellow.payload.doj_data_category_by_item).toMatchObject({
      精确位置轨迹数据: "precise_geolocation_data",
    });
  });

  it("uses current EO 14117 nested fields", () => {
    for (const testCase of DEV_TEST_CASES.us_14117) {
      const payload = asRecord(testCase.payload);
      for (const item of testCase.payload.data_items as Array<Record<string, unknown>>) {
        expect(String(item.data_item_name ?? "").length).toBeGreaterThan(0);
      }
      for (const entity of testCase.payload.recipient_entities as Array<Record<string, unknown>>) {
        expect(String(entity.country_of_registration ?? "").length).toBeGreaterThan(1);
      }
      for (const person of (payload.access_persons ?? []) as Array<Record<string, unknown>>) {
        expect(String(person.person_name ?? "").length).toBeGreaterThan(0);
      }
      for (const measure of testCase.payload.security_measures as Array<Record<string, unknown>>) {
        expect(String(measure.measure_name ?? "").length).toBeGreaterThan(0);
      }
    }
  });

  it("keeps EO 14117 cases aligned with the official red, yellow and green scenarios", () => {
    const [red, yellow, green] = DEV_TEST_CASES.us_14117;

    expect(red.payload.company_name).toBe("GeneGuard生物科技公司");
    expect(red.payload.recipient_entities[0].entity_name).toBe("华源生命科学有限公司");
    expect(red.payload.data_items[0].us_person_count).toBe(10_000);
    expect(red.payload.data_items[0].doj_data_category).toBe("human_genomic_data");
    expect(red.payload.data_items[0].data_description).toContain("全基因组测序");
    expect(red.payload.recipient_entities[0].country_of_registration).toContain("中国");

    expect(yellow.payload.company_name).toBe("GeneGuard生物科技公司");
    expect(yellow.payload.recipient_entities[0].entity_name).toBe("深度洞察人工智能有限公司");
    expect(yellow.payload.data_items[0].us_person_count).toBe(150_000);
    expect(yellow.payload.data_items[0].doj_data_category).toBe("precise_geolocation_data");
    expect(yellow.payload.data_items[0].data_description).toContain("位置轨迹");

    expect(green.payload.company_name).toBe("GeneGuard生物科技公司");
    expect(green.payload.recipient_entities[0].entity_name).toBe("剑桥实验室设备有限公司");
    expect(green.payload.data_items[0].us_person_count).toBe(5_000);
    expect(green.payload.data_items[1].precision_level).toBe("city_level");
    expect(green.payload.recipient_entities[0].is_covered_person).toBe(false);
  });

  it("compiles the shared EO 14117 red scenario into the exact frontend payload", () => {
    expect(DEV_TEST_CASES.us_14117[0].payload).toEqual(genomicRedScenario.request);
  });

  it("compiles the shared EO 14117 yellow scenario into the exact frontend payload", () => {
    expect(DEV_TEST_CASES.us_14117[1].payload).toEqual(geolocationYellowScenario.request);
  });

  it("compiles the shared EO 14117 green scenario into the exact frontend payload", () => {
    expect(DEV_TEST_CASES.us_14117[2].payload).toEqual(telemetryGreenScenario.request);
  });
});
