import { useEffect, useState } from "react";
import { fetchArtifactBlob } from "../../api/artifacts";

type PdfViewerProps = {
  artifactPath: string;
  title: string;
  lang?: "zh" | "en";
};

type PdfViewerState =
  | { status: "loading"; objectUrl: null; error: null }
  | { status: "ready"; objectUrl: string; error: null }
  | { status: "error"; objectUrl: null; error: string };

const loadingState: PdfViewerState = {
  status: "loading",
  objectUrl: null,
  error: null,
};

export function PdfViewer({ artifactPath, title, lang = "zh" }: PdfViewerProps) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<PdfViewerState>(loadingState);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    setState(loadingState);

    fetchArtifactBlob(artifactPath, "file", "Failed to load PDF ({status})")
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (!active) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        setState({ status: "ready", objectUrl, error: null });
      })
      .catch((error: unknown) => {
        if (!active) return;
        setState({
          status: "error",
          objectUrl: null,
          error: error instanceof Error ? error.message : "PDF preview failed",
        });
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [artifactPath, attempt]);

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

  return (
    <div className="workspace-report-pdf-frame">
      <iframe title={title} src={state.objectUrl} />
    </div>
  );
}
