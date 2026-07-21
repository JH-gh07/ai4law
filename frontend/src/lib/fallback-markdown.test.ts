import { describe, expect, it } from "vitest";
import goldenCasesJson from "../../../backend/common/render/normalization_test_cases.json";
import { normalizeFallbackMarkdown } from "./fallback-markdown";

type GoldenCases = {
  test_cases: Array<{ id: string; input: string; expected: string }>;
};

const goldenCases = goldenCasesJson as GoldenCases;

describe("normalizeFallbackMarkdown", () => {
  for (const testCase of goldenCases.test_cases) {
    it(testCase.id, () => {
      expect(normalizeFallbackMarkdown(testCase.input)).toBe(testCase.expected);
    });
  }
});
