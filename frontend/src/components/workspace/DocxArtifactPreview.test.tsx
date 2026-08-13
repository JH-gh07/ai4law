import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ArtifactPreview } from "../../api/artifacts";
import { DocxArtifactPreview } from "./DocxArtifactPreview";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const preview: ArtifactPreview = {
  path: "outputs/review/report.docx",
  file_name: "review_report.docx",
  kind: "docx",
  render_mode: "text",
  content: "# 报告\n**bold** 段\n| a | b |",
};

function renderDocx(overrides: Partial<ArtifactPreview> = {}, downloadBusy = false) {
  const onOpen = vi.fn();
  const onDownload = vi.fn();
  render(
    <DocxArtifactPreview
      preview={{ ...preview, ...overrides }}
      lang="zh"
      downloadBusy={downloadBusy}
      onOpen={onOpen}
      onDownload={onDownload}
    />,
  );
  return { onOpen, onDownload };
}

describe("DocxArtifactPreview", () => {
  it("shows artifact metadata and download/open actions without markdown rendering", () => {
    renderDocx();

    expect(screen.getByText("review_report.docx")).toBeInTheDocument();
    expect(screen.getByText("DOCX")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "打开原文件" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "下载" })).toBeInTheDocument();

    // Markdown source is never fed through a Markdown renderer: the extracted
    // text stays as a literal <pre>, so heading/emphasis/table syntax survives.
    const pre = screen.getByText(/# 报告/).closest("pre");
    expect(pre).not.toBeNull();
    expect(pre?.className).toContain("workspace-plain-preview");
    expect(screen.queryByRole("heading")).toBeNull();
    expect(document.querySelector(".workspace-report-richtext")).toBeNull();
  });

  it("keeps the extracted text collapsed and labelled auxiliary", () => {
    renderDocx();
    const details = screen.getByText(/辅助抽取文本/).closest("details");
    expect(details).not.toBeNull();
    expect(screen.getByText(/\*\*bold\*\* 段/)).toBeInTheDocument();
  });

  it("omits the extracted text when content is empty", () => {
    renderDocx({ content: "" });
    expect(screen.queryByText(/辅助抽取文本/)).not.toBeInTheDocument();
  });

  it("fires open and download with the artifact path", () => {
    const { onOpen, onDownload } = renderDocx();
    fireEvent.click(screen.getByRole("button", { name: "打开原文件" }));
    fireEvent.click(screen.getByRole("button", { name: "下载" }));
    expect(onOpen).toHaveBeenCalledWith("outputs/review/report.docx");
    expect(onDownload).toHaveBeenCalledWith("outputs/review/report.docx");
  });

  it("disables download while a download is busy", () => {
    renderDocx({}, true);
    expect(screen.getByRole("button", { name: "下载" })).toBeDisabled();
  });
});
