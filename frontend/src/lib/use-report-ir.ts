import { useEffect, useMemo, useState } from "react";
import { fetchArtifactPreview } from "../api/artifacts";
import { useAppStore } from "./app-store";
import { isDocumentIR, type DocumentIR } from "./document-ir";

export type ReportIrState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; document: DocumentIR }
  | { status: "error"; message: string }
  | { status: "unavailable" };

/**
 * Resolve the structured report body for a task from its registered
 * `document_ir_json` artifact. The IR is fetched on demand and held in
 * component memory only — it is never written to AppState or localStorage
 * (task067 T04 requirement #7).
 */
export function useReportIr(taskSpaceId: string, module: string): ReportIrState {
  const { state } = useAppStore();
  const irArtifact = useMemo(
    () =>
      state.artifacts.find(
        (artifact) =>
          artifact.taskSpaceId === taskSpaceId &&
          artifact.module === module &&
          artifact.kind.toLowerCase() === "document_ir_json"
      ),
    [state.artifacts, taskSpaceId, module]
  );

  const [irState, setIrState] = useState<ReportIrState>({ status: "idle" });

  useEffect(() => {
    if (!irArtifact) {
      setIrState({ status: "unavailable" });
      return;
    }
    let cancelled = false;
    setIrState({ status: "loading" });
    fetchArtifactPreview(irArtifact.path)
      .then((preview) => {
        if (cancelled) return;
        if (preview.render_mode !== "report_ir" || !isDocumentIR(preview.report_ir)) {
          setIrState({ status: "unavailable" });
          return;
        }
        setIrState({ status: "ready", document: preview.report_ir });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setIrState({
          status: "error",
          message: error instanceof Error ? error.message : "报告结构加载失败",
        });
      });
    return () => {
      cancelled = true;
    };
  }, [irArtifact]);

  return irState;
}
