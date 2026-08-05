import { describe, expect, it } from "vitest";

import { DEV_TEST_CASES } from "./dev-test-cases";

const asRecord = (value: unknown): Record<string, unknown> => {
  expect(value).toBeTypeOf("object");
  expect(value).not.toBeNull();
  expect(Array.isArray(value)).toBe(false);
  return value as Record<string, unknown>;
};

describe("developer test case API contracts", () => {
  it("keeps the registry at 26 independently runnable cases", () => {
    expect(Object.values(DEV_TEST_CASES).flat()).toHaveLength(26);
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
      for (const field of ["legal_document_review", "compliance_history", "personal_info_protection"] as const) {
        const value = testCase.payload[field];
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
      for (const item of testCase.payload.data_items as Array<Record<string, unknown>>) {
        expect(String(item.data_item_name ?? "").length).toBeGreaterThan(0);
      }
      for (const entity of testCase.payload.recipient_entities as Array<Record<string, unknown>>) {
        expect(String(entity.country_of_registration ?? "").length).toBeGreaterThan(1);
      }
      for (const person of (testCase.payload.access_persons ?? []) as Array<Record<string, unknown>>) {
        expect(String(person.person_name ?? "").length).toBeGreaterThan(0);
      }
      for (const measure of testCase.payload.security_measures as Array<Record<string, unknown>>) {
        expect(String(measure.measure_name ?? "").length).toBeGreaterThan(0);
      }
    }
  });
});
