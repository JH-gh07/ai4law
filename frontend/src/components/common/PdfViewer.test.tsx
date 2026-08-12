import { StrictMode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchArtifactBlob } from "../../api/artifacts";
import { PdfViewer } from "./PdfViewer";
import { openPdfDocument } from "./pdf-document";

vi.mock("../../api/artifacts", () => ({
  fetchArtifactBlob: vi.fn(),
}));

vi.mock("./pdf-document", () => ({
  openPdfDocument: vi.fn(),
}));

const fetchPdf = vi.mocked(fetchArtifactBlob);
const openPdf = vi.mocked(openPdfDocument);

function createPdfDocument() {
  const render = vi.fn(() => ({ promise: Promise.resolve(), cancel: vi.fn() }));
  const getPage = vi.fn().mockResolvedValue({
    getViewport: () => ({ width: 600, height: 840 }),
    render,
  });
  return {
    numPages: 2,
    getPage,
    destroy: vi.fn().mockResolvedValue(undefined),
    render,
  };
}

describe("PdfViewer", () => {
  const documents: ReturnType<typeof createPdfDocument>[] = [];

  beforeEach(() => {
    fetchPdf.mockReset();
    openPdf.mockReset();
    documents.length = 0;
    openPdf.mockImplementation(async () => {
      const document = createPdfDocument();
      documents.push(document);
      return document as never;
    });
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D);
  });

  it("fetches once per path and destroys parsed documents on path changes and unmount", async () => {
    fetchPdf.mockResolvedValue(new Blob(["%PDF"], { type: "application/pdf" }));
    const { rerender, unmount } = render(
      <PdfViewer artifactPath="outputs/first.pdf" title="First report" />,
    );

    expect(await screen.findByLabelText("First report 1")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText("First report PDF")).toHaveAttribute("aria-busy", "false"));
    expect(fetchPdf).toHaveBeenCalledTimes(1);

    rerender(<PdfViewer artifactPath="outputs/first.pdf" title="First report" />);
    expect(fetchPdf).toHaveBeenCalledTimes(1);

    rerender(<PdfViewer artifactPath="outputs/second.pdf" title="Second report" />);
    expect(await screen.findByLabelText("Second report 1")).toBeInTheDocument();
    await waitFor(() => expect(documents[0]?.destroy).toHaveBeenCalledTimes(1));
    expect(fetchPdf).toHaveBeenCalledTimes(2);

    unmount();
    expect(documents[1]?.destroy).toHaveBeenCalledTimes(1);
  });

  it("fetches only once when React StrictMode replays the mount effect", async () => {
    fetchPdf.mockResolvedValue(new Blob(["%PDF"], { type: "application/pdf" }));

    render(
      <StrictMode>
        <PdfViewer artifactPath="outputs/strict.pdf" title="Strict report" />
      </StrictMode>,
    );

    expect(await screen.findByLabelText("Strict report 1")).toBeInTheDocument();
    expect(fetchPdf).toHaveBeenCalledTimes(1);
  });

  it("shows an accessible error and retries the same path", async () => {
    fetchPdf
      .mockRejectedValueOnce(new Error("PDF unavailable"))
      .mockResolvedValueOnce(new Blob(["%PDF"], { type: "application/pdf" }));
    render(<PdfViewer artifactPath="outputs/report.pdf" title="Report" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("PDF unavailable");
    fireEvent.click(screen.getByRole("button", { name: "重试 PDF 预览" }));

    expect(await screen.findByLabelText("Report 1")).toBeInTheDocument();
    await waitFor(() => expect(fetchPdf).toHaveBeenCalledTimes(2));
  });
});
