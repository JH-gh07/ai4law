import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchArtifactBlob } from "../../api/artifacts";
import { PdfViewer } from "./PdfViewer";

vi.mock("../../api/artifacts", () => ({
  fetchArtifactBlob: vi.fn(),
}));

const fetchPdf = vi.mocked(fetchArtifactBlob);

describe("PdfViewer", () => {
  beforeEach(() => {
    fetchPdf.mockReset();
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi
        .fn()
        .mockReturnValueOnce("blob:first")
        .mockReturnValueOnce("blob:second"),
      revokeObjectURL: vi.fn(),
    });
  });

  it("fetches once per path and revokes URLs on path changes and unmount", async () => {
    fetchPdf.mockResolvedValue(new Blob(["%PDF"], { type: "application/pdf" }));
    const { rerender, unmount } = render(
      <PdfViewer artifactPath="outputs/first.pdf" title="First report" />,
    );

    expect(await screen.findByTitle("First report")).toHaveAttribute("src", "blob:first");
    expect(fetchPdf).toHaveBeenCalledTimes(1);

    rerender(<PdfViewer artifactPath="outputs/first.pdf" title="First report" />);
    expect(fetchPdf).toHaveBeenCalledTimes(1);

    rerender(<PdfViewer artifactPath="outputs/second.pdf" title="Second report" />);
    expect(await screen.findByTitle("Second report")).toHaveAttribute("src", "blob:second");
    expect(fetchPdf).toHaveBeenCalledTimes(2);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:first");

    unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:second");
  });

  it("shows an accessible error and retries the same path", async () => {
    fetchPdf
      .mockRejectedValueOnce(new Error("PDF unavailable"))
      .mockResolvedValueOnce(new Blob(["%PDF"], { type: "application/pdf" }));
    render(<PdfViewer artifactPath="outputs/report.pdf" title="Report" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("PDF unavailable");
    fireEvent.click(screen.getByRole("button", { name: "重试 PDF 预览" }));

    expect(await screen.findByTitle("Report")).toBeInTheDocument();
    await waitFor(() => expect(fetchPdf).toHaveBeenCalledTimes(2));
  });
});
