import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { DocumentIR } from "../../lib/document-ir";
import { isDocumentIR } from "../../lib/document-ir";
import { ReportDocumentView } from "./ReportDocumentView";

afterEach(() => {
  cleanup();
});

function makeDocument(): DocumentIR {
  return {
    schema_version: "4.0",
    document_id: "bcr:task-1",
    report_type: "bcr",
    metadata: { title: "示例集团 — BCR 合规审查报告", company_name: "示例集团" },
    findings: [
      {
        finding_id: "BCR-C-1.1-01",
        requirement_id: "BCR-C-1.1",
        title: "约束力不足",
        risk_level: "HIGH",
        statement: "集团内部约束机制不完整。",
        legal_basis: ["GDPR Article 47(1)"],
        recommendation: "补充集团内部约束条款。",
        status: "OPEN_BLOCKING",
      },
      {
        finding_id: "BCR-C-1.9-01",
        requirement_id: "BCR-C-1.9",
        title: "TIA 不完整",
        risk_level: "MEDIUM",
        statement: "第三国法律评估不完整。",
        status: "OPEN",
      },
    ],
    sections: [
      {
        section_id: "bcr.s2",
        title: "BCR 类型与审查范围",
        level: 1,
        ordinal: "2",
        blocks: [
          { block_id: "b1", type: "key_value", items: [{ label: "BCR 类型", value: "BCR-C" }] },
          { block_id: "b2", type: "list", ordered: true, items: [{ text: "父项", children: [{ text: "子项" }] }] },
          { block_id: "b3", type: "warning", severity: "warning", text: "注意风险" },
          { block_id: "b4", type: "paragraph", text: "说明段落。" },
          { block_id: "b5", type: "claim", text: "集团规则应具有法律约束力。" },
        ],
      },
      {
        section_id: "bcr.s3",
        title: "风险与 finding 摘要",
        level: 1,
        ordinal: "3",
        blocks: [
          { block_id: "s3", type: "finding_summary", finding_refs: ["BCR-C-1.1-01", "BCR-C-1.9-01"] },
        ],
      },
      {
        section_id: "bcr.s4",
        title: "详细 finding",
        level: 1,
        ordinal: "4",
        blocks: [
          { block_id: "d1", type: "finding_detail", finding_ref: "BCR-C-1.1-01" },
          { block_id: "d2", type: "finding_detail", finding_ref: "BCR-C-1.9-01" },
        ],
      },
      {
        section_id: "bcr.s6",
        title: "建议条款",
        level: 1,
        ordinal: "6",
        blocks: [
          {
            block_id: "clauses",
            type: "clause_group",
            title: "建议条款",
            clauses: [
              {
                node_id: "clause.1",
                text: "第一条",
                children: [
                  { node_id: "clause.1.1", text: "第一项", numbering_style: "lower_alpha" },
                ],
              },
            ],
          },
        ],
      },
    ],
    compiler_version: "0.1.0",
    prompt_version: "test",
    template_version: "test",
    model: "test-model",
  };
}

describe("ReportDocumentView", () => {
  it("renders metadata title and company", () => {
    render(<ReportDocumentView document={makeDocument()} />);
    expect(screen.getByText("示例集团 — BCR 合规审查报告")).toBeInTheDocument();
    expect(screen.getByText("示例集团")).toBeInTheDocument();
  });

  it("renders all section titles with ordinal numbering", () => {
    render(<ReportDocumentView document={makeDocument()} />);
    expect(screen.getByText("2 BCR 类型与审查范围")).toBeInTheDocument();
    expect(screen.getByText("3 风险与 finding 摘要")).toBeInTheDocument();
  });

  it("renders finding detail with field blocks and text risk badge", () => {
    render(<ReportDocumentView document={makeDocument()} />);
    // risk conveyed by text, not color alone
    expect(screen.getByText("高风险")).toBeInTheDocument();
    expect(screen.getByText("中风险")).toBeInTheDocument();
    expect(screen.getAllByText("现状").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("集团内部约束机制不完整。")).toBeInTheDocument();
  });

  it("renders legal_basis shim joined when basis_entries absent", () => {
    const document = makeDocument();
    document.findings[0].legal_basis = ["GDPR Article 47(1)", "PIPL Article 38"];
    render(<ReportDocumentView document={document} />);
    expect(screen.getByText("GDPR Article 47(1)；PIPL Article 38")).toBeInTheDocument();
  });

  it("renders basis_entries one per line with attributed rationale", () => {
    const document = makeDocument();
    document.findings[0].basis_entries = [
      { citation_ref: "c1", label: "GDPR Article 47(2)(a)", rationale: "约束规则须由集团层面批准" },
      { label: "PIPL Article 38", rationale: "跨境传输需具备法定条件" },
      { label: "GDPR Article 47(1)" },
    ];
    render(<ReportDocumentView document={document} />);
    expect(screen.getByText("GDPR Article 47(2)(a)：约束规则须由集团层面批准")).toBeInTheDocument();
    expect(screen.getByText("PIPL Article 38：跨境传输需具备法定条件")).toBeInTheDocument();
    expect(screen.getByText("GDPR Article 47(1)")).toBeInTheDocument();
    // the legacy wall join must not appear when basis_entries is authoritative
    expect(screen.queryByText(/；/)).not.toBeInTheDocument();
  });

  it("renders clause tree with explicit legal numbering", () => {
    render(<ReportDocumentView document={makeDocument()} />);
    expect(screen.getByText("1. 第一条")).toBeInTheDocument();
    expect(screen.getByText("(a) 第一项")).toBeInTheDocument();
  });

  it("does not throw on an unknown block type", () => {
    const document = makeDocument();
    document.sections.push({
      section_id: "extra",
      title: "未知块",
      level: 1,
      blocks: [{ block_id: "x", type: "totally_unknown" } as never],
    });
    render(<ReportDocumentView document={document} />);
    expect(screen.getByText(/未知内容块/)).toBeInTheDocument();
  });
});

describe("isDocumentIR", () => {
  it("rejects arbitrary JSON objects", () => {
    expect(isDocumentIR({ note: "not an IR" })).toBe(false);
    expect(isDocumentIR(null)).toBe(false);
    expect(isDocumentIR([])).toBe(false);
  });

  it("accepts a valid v4 document", () => {
    expect(isDocumentIR(makeDocument())).toBe(true);
  });
});
