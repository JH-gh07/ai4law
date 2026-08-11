import { describe, expect, expectTypeOf, it } from "vitest";

import type { ModuleRequestMap } from "../api/api-contract";
import { DEV_TEST_CASES } from "./dev-test-cases";


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
        if (fileBackedModules.has(module)) {
          expect(testCase.backendFilePaths?.length, `${module}/${testCase.name}`).toBeGreaterThan(0);
        }
      }
    }
  });

  it("keeps the registry at 26 independently runnable cases", () => {
    expect(Object.values(DEV_TEST_CASES).flat()).toHaveLength(26);
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

  it("keeps the first SCC case aligned with the official France-UK C2C scenario", () => {
    const testCase = DEV_TEST_CASES.eu_scc[0];

    expect(testCase.payload.declared_module_type).toBe("Module One");
    expect(testCase.payload.company_name).toBe("EU Fashion E-commerce SAS");
    expect(testCase.payload.scc_text).toContain("UK Marketing Analytics Ltd");
    expect(testCase.payload.scc_text).toContain("MODULE ONE");
    expect(testCase.payload.scc_text).toContain("Amazon Web Services");
    expect(testCase.payload.scc_text).not.toContain("E-Commerce GmbH");
    expect(testCase.payload.scc_text).not.toContain("MODULE TWO");
  });

  it("includes current PIPIA company profile fields", () => {
    for (const testCase of DEV_TEST_CASES.pipia) {
      const company = asRecord(testCase.payload.company_profile);
      expect(String(company.company_uscc ?? "").length).toBeGreaterThanOrEqual(8);
    }
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
});
