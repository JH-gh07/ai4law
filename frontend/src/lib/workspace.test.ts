import { describe, expect, it } from "vitest";

import { extractInsight, extractReportMetrics } from "./workspace";

describe("workspace report metrics", () => {
  it("uses BCR findings, bound footnotes, and rating for the report summary", () => {
    const response = {
      rating: "高风险",
      findings: [
        { legal_basis: ["GDPR Article 47(1)(a) [1]", "EDPB 1/2022"] },
        { legal_basis: ["GDPR Article 47(1)(b) [1]", "EDPB 01/2020 [2]"] },
      ],
      missing_requirements: ["BCR-C-1.2"],
    };

    expect(extractInsight(response).riskLevel).toBe("高风险");
    expect(extractReportMetrics(response)).toEqual({
      issueCount: 2,
      evidenceCount: 2,
    });
  });

  it("leaves absent metrics undefined so the workspace can use stored fallbacks", () => {
    expect(extractReportMetrics({ report_path: "report.md" })).toEqual({
      issueCount: undefined,
      evidenceCount: undefined,
    });
  });
});
