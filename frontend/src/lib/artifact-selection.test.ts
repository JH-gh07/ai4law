import { describe, expect, it } from "vitest";
import { findPdfCompanion } from "./artifact-selection";

const artifact = (kind: string, path: string) => ({ kind, path });

describe("findPdfCompanion", () => {
  it("returns only the PDF with the same report basename", () => {
    const selected = artifact("markdown", "outputs/report-a.md");
    const exact = artifact("pdf", "outputs/report-a.pdf");
    const unrelated = artifact("pdf", "outputs/report-b.pdf");

    expect(findPdfCompanion(selected, [unrelated, exact])).toBe(exact);
    expect(findPdfCompanion(selected, [unrelated])).toBeNull();
  });

  it("accepts a selected PDF as its own companion", () => {
    const selected = artifact("pdf", "outputs/report.pdf");
    expect(findPdfCompanion(selected, [selected])).toBe(selected);
  });
});
