import { useEffect, useRef, useState } from "react";
import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";

import { fetchArtifactBlob } from "../../api/artifacts";
import { ChevronToggleIcon } from "./AppIcons";
import { openPdfDocument } from "./pdf-document";

type PdfViewerProps = {
  artifactPath: string;
  title: string;
  lang?: "zh" | "en";
};

type PdfViewerState =
  | { status: "loading"; document: null; error: null }
  | { status: "ready"; document: PDFDocumentProxy; error: null }
  | { status: "error"; document: null; error: string };

const loadingState: PdfViewerState = {
  status: "loading",
  document: null,
  error: null,
};

const pendingPdfLoads = new Map<string, Promise<Blob>>();

function loadPdfBlob(artifactPath: string): Promise<Blob> {
  const pending = pendingPdfLoads.get(artifactPath);
  if (pending) return pending;

  const request = fetchArtifactBlob(artifactPath, "file", "Failed to load PDF ({status})")
    .finally(() => {
      if (pendingPdfLoads.get(artifactPath) === request) {
        pendingPdfLoads.delete(artifactPath);
      }
    });
  pendingPdfLoads.set(artifactPath, request);
  return request;
}

export function PdfViewer({ artifactPath, title, lang = "zh" }: PdfViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [attempt, setAttempt] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [pageRendering, setPageRendering] = useState(false);
  const [state, setState] = useState<PdfViewerState>(loadingState);

  useEffect(() => {
    let active = true;
    let loadedDocument: PDFDocumentProxy | null = null;
    setState(loadingState);
    setPageNumber(1);

    loadPdfBlob(artifactPath)
      .then((blob) => blob.arrayBuffer())
      .then((data) => openPdfDocument(data))
      .then((document) => {
        loadedDocument = document;
        if (!active) {
          void document.destroy();
          return;
        }
        setState({ status: "ready", document, error: null });
      })
      .catch((error: unknown) => {
        if (!active) return;
        setState({
          status: "error",
          document: null,
          error: error instanceof Error ? error.message : "PDF preview failed",
        });
      });

    return () => {
      active = false;
      if (loadedDocument) void loadedDocument.destroy();
    };
  }, [artifactPath, attempt]);

  useEffect(() => {
    if (state.status !== "ready") return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    let active = true;
    let renderTask: RenderTask | null = null;
    setPageRendering(true);

    state.document.getPage(pageNumber)
      .then((page) => {
        if (!active) return;
        const viewport = page.getViewport({ scale: 1.5 });
        const outputScale = Math.max(1, window.devicePixelRatio || 1);
        const context = canvas.getContext("2d", { alpha: false });
        if (!context) throw new Error("Canvas 2D context is unavailable");

        canvas.width = Math.floor(viewport.width * outputScale);
        canvas.height = Math.floor(viewport.height * outputScale);
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;
        renderTask = page.render({
          canvas,
          canvasContext: context,
          viewport,
          transform: outputScale === 1 ? undefined : [outputScale, 0, 0, outputScale, 0, 0],
          background: "rgb(255,255,255)",
        });
        return renderTask.promise;
      })
      .then(() => {
        if (active) setPageRendering(false);
      })
      .catch((error: unknown) => {
        if (!active || (error instanceof Error && error.name === "RenderingCancelledException")) return;
        setState({
          status: "error",
          document: null,
          error: error instanceof Error ? error.message : "PDF page rendering failed",
        });
      });

    return () => {
      active = false;
      renderTask?.cancel();
    };
  }, [pageNumber, state]);

  if (state.status === "loading") {
    return (
      <div className="pdf-viewer-state" role="status" aria-live="polite" aria-busy="true">
        {lang === "zh" ? "正在加载 PDF 预览..." : "Loading PDF preview..."}
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="pdf-viewer-state pdf-viewer-error" role="alert">
        <span>{state.error}</span>
        <button
          type="button"
          className="workspace-report-link-button"
          onClick={() => setAttempt((current) => current + 1)}
          aria-label={lang === "zh" ? "重试 PDF 预览" : "Retry PDF preview"}
        >
          {lang === "zh" ? "重试" : "Retry"}
        </button>
      </div>
    );
  }

  const pageCount = state.document.numPages;
  return (
    <section className="pdf-viewer" aria-label={`${title} PDF`} aria-busy={pageRendering}>
      <div className="pdf-viewer-toolbar">
        <button
          type="button"
          className="pdf-viewer-page-button"
          onClick={() => setPageNumber((current) => Math.max(1, current - 1))}
          disabled={pageNumber <= 1 || pageRendering}
          aria-label={lang === "zh" ? "上一页" : "Previous page"}
          title={lang === "zh" ? "上一页" : "Previous page"}
        >
          <ChevronToggleIcon direction="left" width="16" height="16" />
        </button>
        <span>{lang === "zh" ? `第 ${pageNumber} / ${pageCount} 页` : `Page ${pageNumber} of ${pageCount}`}</span>
        <button
          type="button"
          className="pdf-viewer-page-button"
          onClick={() => setPageNumber((current) => Math.min(pageCount, current + 1))}
          disabled={pageNumber >= pageCount || pageRendering}
          aria-label={lang === "zh" ? "下一页" : "Next page"}
          title={lang === "zh" ? "下一页" : "Next page"}
        >
          <ChevronToggleIcon direction="right" width="16" height="16" />
        </button>
      </div>
      <div className="pdf-viewer-page-shell">
        <canvas ref={canvasRef} className="pdf-viewer-canvas" aria-label={`${title} ${pageNumber}`} />
      </div>
    </section>
  );
}
