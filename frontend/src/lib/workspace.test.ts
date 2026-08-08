import { describe, expect, it } from "vitest";

import { extractInsight, extractReportMetrics, extractRunResponseState } from "./workspace";

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

describe("workspace run response state", () => {
  it("derives async completion artifacts, evidence, and issues from one response", () => {
    const response = {
      report_path: "outputs/tia/report.md",
      output_files: {
        markdown: "outputs/tia/report.md",
        pdf: "outputs/tia/report.pdf",
        zip: "outputs/tia/report.zip",
      },
      chapters: [
        {
          title: "传输工具适用性判断",
          citations: ["GDPR Article 46"],
        },
      ],
      consistency_issues: ["high: supplementary measures require revision"],
    };

    const derived = extractRunResponseState("task-tia", "tia", response);

    expect(derived.artifacts.map((item) => item.path)).toEqual([
      "outputs/tia/report.md",
      "outputs/tia/report.pdf",
      "outputs/tia/report.zip",
    ]);
    expect(derived.evidenceHits).toHaveLength(1);
    expect(derived.evidenceHits[0]?.title).toBe("GDPR Article 46");
    expect(derived.issues).toHaveLength(1);
    expect(derived.issues[0]?.severity).toBe("high");
  });
});
