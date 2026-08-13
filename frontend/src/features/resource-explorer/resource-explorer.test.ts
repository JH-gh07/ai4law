import { describe, expect, it } from "vitest";
import type { ModuleRun, OutputArtifact } from "../../lib/domain";
import { buildInputEntries, collectUserInputFiles } from "./input-resources";
import {
  buildOutputEntries,
  filterUserFacingArtifacts,
  resolveArtifactDisplayName,
} from "./output-artifacts";
import { buildPathTree } from "./path-tree";

const makeRun = (overrides: Partial<ModuleRun> = {}): ModuleRun => ({
  id: "run-1",
  taskSpaceId: "task-1",
  module: "assessment",
  runMode: "sync",
  startedAt: "2026-08-08T08:00:00.000Z",
  success: true,
  request: {},
  ...overrides,
});

const makeArtifact = (path: string, kind = "report", createdAt = "2026-08-08T08:01:00.000Z"): OutputArtifact => ({
  id: `artifact-${path}`,
  taskSpaceId: "task-1",
  module: "assessment",
  kind,
  path,
  createdAt,
});

describe("resource explorer input files", () => {
  it("collects supported user files, preserves role labels, and ignores internal data files", () => {
    const result = collectUserInputFiles({
      uploaded_files: ["uploads/contract.docx", "uploads/inventory.xlsx", "uploads/review-notes.md"],
      attachments: [
        {
          file_role: "privacy_policy",
          storage_uri: "storage/uploads/privacy-policy.pdf",
        },
        {
          file_role: "data_flow_diagram",
          storage_uri: "storage/uploads/data-flow.png",
        },
      ],
      source_registry: "resources/legal/source_registry.json",
      generated_context: "outputs/facts.json",
      output_files: { markdown: "outputs/report.md" },
      debug_files: ["outputs/debug.json"],
      description: "report.pdf",
      source_url: "https://example.com/law.pdf",
    });

    expect(result).toEqual([
      { path: "uploads/contract.docx" },
      { path: "uploads/inventory.xlsx" },
      { path: "uploads/review-notes.md" },
      { path: "storage/uploads/privacy-policy.pdf", labelKey: "privacy_policy" },
      { path: "storage/uploads/data-flow.png", labelKey: "data_flow_diagram" },
    ]);
  });

  it("does not infer short role names from unrelated filename substrings", () => {
    expect(collectUserInputFiles({
      uploaded_files: ["uploads/negotiation.pdf", "uploads/tia.pdf"],
    })).toEqual([
      { path: "uploads/negotiation.pdf" },
      { path: "uploads/tia.pdf", labelKey: "tia" },
    ]);
  });

  it("builds only real file entries, deduplicates paths, and excludes generated outputs", () => {
    const runs = [
      makeRun({
        id: "newer",
        startedAt: "2026-08-08T09:00:00.000Z",
        request: { uploaded_files: ["uploads/a.docx", "outputs/report.pdf"] },
      }),
      makeRun({
        id: "older",
        request: { uploaded_files: ["uploads\\a.docx", "uploads/b.pdf"] },
      }),
    ];

    const entries = buildInputEntries(runs, [makeArtifact("/workspace/outputs/report.pdf", "pdf")], "zh");

    expect(entries.map((entry) => ({ name: entry.name, sourcePath: entry.sourcePath }))).toEqual([
      { name: "a.docx", sourcePath: "uploads/a.docx" },
      { name: "b.pdf", sourcePath: "uploads/b.pdf" },
    ]);
    expect(entries.every((entry) => entry.kind === "file")).toBe(true);
  });
});

describe("resource explorer output artifacts", () => {
  it("hides internal compiler artifacts and unsupported files while retaining user deliverables", () => {
    const artifacts = [
      makeArtifact("outputs/report.docx", "docx"),
      makeArtifact("outputs/report.pdf", "pdf"),
      makeArtifact("outputs/report.md", "markdown"),
      makeArtifact("outputs/bundle.zip", "zip"),
      makeArtifact("outputs/risk_matrix.xlsx", "xlsx"),
      makeArtifact("outputs/citation_map.json", "citation_map_json"),
      makeArtifact("outputs/document_ir.json", "document_ir_json"),
      makeArtifact("outputs/facts.json", "facts_json"),
      makeArtifact("outputs/issue_list.xlsx", "issue_list_xlsx"),
      makeArtifact("outputs/debug.log", "trace"),
      makeArtifact("outputs/secret.xlsx", "compiler_snapshot"),
      makeArtifact("/workspace/outputs/report.docx", "docx"),
    ];

    expect(filterUserFacingArtifacts(artifacts).map((item) => item.path)).toEqual([
      "outputs/report.docx",
      "outputs/report.pdf",
      "outputs/report.md",
      "outputs/bundle.zip",
      "outputs/risk_matrix.xlsx",
    ]);
  });

  it("uses stable user-facing names instead of internal artifact kinds", () => {
    expect(resolveArtifactDisplayName(makeArtifact("outputs/report.docx", "docx"), "zh")).toBe("报告 Word 版");
    expect(resolveArtifactDisplayName(makeArtifact("outputs/report.pdf", "pdf"), "en")).toBe("Report PDF");
    expect(resolveArtifactDisplayName(makeArtifact("outputs/risk_matrix.xlsx", "xlsx"), "zh")).toBe("风险矩阵（XLSX）");
  });

  it("groups visible outputs by run and disambiguates duplicate display names", () => {
    const runs = [makeRun()];
    const entries = buildOutputEntries(
      [
        makeArtifact("outputs/report-a.docx", "docx"),
        makeArtifact("outputs/report-b.docx", "docx"),
        makeArtifact("outputs/facts.json", "facts_json"),
      ],
      runs,
      "zh",
    );

    expect(entries.map((entry) => entry.virtualPath)).toEqual([
      "第1次生成结果/报告 Word 版",
      "第1次生成结果/报告 Word 版 (2)",
    ]);
  });
});

describe("resource explorer path tree", () => {
  it("builds a deterministic folder-first tree from virtual paths", () => {
    const tree = buildPathTree([
      "第2次生成结果/报告 PDF 版",
      "第1次生成结果/报告 Word 版",
      "根文件.zip",
    ], "output");

    expect(tree.map((node) => `${node.type}:${node.name}`)).toEqual([
      "folder:第1次生成结果",
      "folder:第2次生成结果",
      "file:根文件.zip",
    ]);
    expect(tree[0]?.children[0]).toMatchObject({
      type: "file",
      name: "报告 Word 版",
      path: "第1次生成结果/报告 Word 版",
    });
  });
});

describe("resource explorer input manifest (task068 T03)", () => {
  it("recovers inputs from a persisted manifest when request is empty", () => {
    const runs = [
      makeRun({
        id: "recovered",
        module: "review",
        request: {},
        response: {
          input_manifest: {
            entries: [
              { input_id: "f-1", display_name: "合同.docx", source_kind: "uploaded", public_locator: "合同.docx", consumed_by_service: true },
              { input_id: "inline-1", display_name: "审查场景（内联）", source_kind: "inline", public_locator: "", consumed_by_service: true },
              { input_id: "f-2", display_name: "预设案例.pdf", source_kind: "dev_preset", public_locator: "预设案例.pdf", consumed_by_service: false },
            ],
          },
        },
      }),
    ];

    const entries = buildInputEntries(runs, [], "zh");
    expect(entries.map((entry) => ({ name: entry.name, sourceKind: entry.sourceKind }))).toEqual([
      { name: "合同.docx", sourceKind: "uploaded" },
      { name: "审查场景（内联）", sourceKind: "inline" },
    ]);
  });
});
