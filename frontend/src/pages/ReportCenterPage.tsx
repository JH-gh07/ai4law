/**
 * 本文档用于展示报告中心页面的组件
 *
 * 该页面会根据用户的任务空间和报告快照信息，展示报告列表、报告预览和追踪信息。
 * 用户可以通过搜索关键字筛选报告，查看报告的详细内容和相关追踪信息。
 *
 * @returns {JSX.Element} - 报告中心页面的组件  
 */
import { useEffect, useMemo, useState } from "react";
import { ReportTaskTreeSidebar, type ReportTaskTreeNode } from "../components/report-center/ReportTaskTreeSidebar";
import { ReportDocumentView } from "../components/report/ReportDocumentView";
import { useAppStore } from "../lib/app-store";
import type { ModuleRun, ReportReviewSnapshot } from "../lib/domain";
import { useLang } from "../lib/language";
import { fetchMyReports, type MyReportItem } from "../api/me";
import { fetchReportMetadata } from "../api/reports";
import { buildReportSnapshots, buildTraceLinks } from "../lib/report-adapter";
import { useReportIr } from "../lib/use-report-ir";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

function readChapters(run: ModuleRun | undefined): Array<{ title: string; content: string }> {
  if (!run || !isRecord(run.response) || !Array.isArray(run.response.chapters)) return [];
  return run.response.chapters
    .filter((item): item is Record<string, unknown> => isRecord(item))
    .map((item) => ({
      title: typeof item.title === "string" ? item.title : "Untitled",
      content: typeof item.content === "string" ? item.content : ""
    }))
    .slice(0, 8);
}

export function ReportCenterPage() {
  const { t } = useLang();
  const { state } = useAppStore();
  const [keyword, setKeyword] = useState("");
  const [selectedId, setSelectedId] = useState<string>("");
  const [remoteSummary, setRemoteSummary] = useState<Record<string, { summary?: string; version?: string; risk_level?: string }>>({});
  const [copiedPath, setCopiedPath] = useState("");
  const [remoteReports, setRemoteReports] = useState<MyReportItem[]>([]);

  const taskMap = useMemo(
    () => new Map(state.taskSpaces.map((task) => [task.id, task])),
    [state.taskSpaces]
  );

  const snapshots = useMemo(() => {
    return state.taskSpaces.flatMap((task) =>
      buildReportSnapshots(task, state.artifacts, state.moduleRuns, state.issues, state.evidenceHits)
    );
  }, [state.artifacts, state.evidenceHits, state.issues, state.moduleRuns, state.taskSpaces]);

  const filteredSnapshots = useMemo(() => {
    const token = keyword.trim().toLowerCase();
    return snapshots
      .filter((item) => {
        if (!token) return true;
        const task = taskMap.get(item.taskSpaceId);
        const searchable = `${item.module} ${item.artifactPath} ${item.artifactKind} ${item.taskSpaceId} ${task?.name ?? ""}`.toLowerCase();
        return searchable.includes(token);
      });
  }, [keyword, snapshots, taskMap]);

  const treeNodes = useMemo<ReportTaskTreeNode[]>(() => {
    const token = keyword.trim().toLowerCase();
    const allNodes = state.taskSpaces.map<ReportTaskTreeNode>((task) => {
      const docs = filteredSnapshots
        .filter((snapshot) => snapshot.taskSpaceId === task.id)
        .map((snapshot) => {
          const filename = snapshot.artifactPath.split("/").slice(-1)[0] ?? "";
          const title = filename ? filename.replace(/\.[^/.]+$/, "") : `${snapshot.module.toUpperCase()} · ${snapshot.artifactKind.toUpperCase()}`;
          return {
            snapshotId: snapshot.id,
            title,
            generatedAt: snapshot.generatedAt,
            module: snapshot.module,
            artifactKind: snapshot.artifactKind,
            riskLevel: snapshot.riskLevel || t("reportNoEvidenceLabel")
          };
        })
        .sort((a, b) => (a.generatedAt < b.generatedAt ? 1 : -1));

      return {
        taskId: task.id,
        taskName: task.name,
        taskUpdatedAt: task.updatedAt,
        documents: docs
      };
    });

    return allNodes
      .filter((task) => {
        if (!token) return true;
        const byTaskName = `${task.taskName} ${task.taskId}`.toLowerCase().includes(token);
        return byTaskName || task.documents.length > 0;
      })
      .sort((a, b) => {
        const latestA = a.documents[0]?.generatedAt ?? a.taskUpdatedAt;
        const latestB = b.documents[0]?.generatedAt ?? b.taskUpdatedAt;
        return latestA < latestB ? 1 : -1;
      });
  }, [filteredSnapshots, keyword, state.taskSpaces, t]);

  useEffect(() => {
    if (!selectedId && filteredSnapshots.length > 0) {
      setSelectedId(filteredSnapshots[0].id);
    }
    if (selectedId && filteredSnapshots.every((item) => item.id !== selectedId)) {
      setSelectedId(filteredSnapshots[0]?.id ?? "");
    }
  }, [filteredSnapshots, selectedId]);

  const selectedSnapshot = filteredSnapshots.find((item) => item.id === selectedId) ?? filteredSnapshots[0] ?? null;

  useEffect(() => {
    let cancelled = false;
    fetchMyReports().then((items) => {
      if (cancelled) return;
      setRemoteReports(items);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedSnapshot) return;
    let cancelled = false;
    fetchReportMetadata(selectedSnapshot.taskSpaceId).then((metadata) => {
      if (cancelled || !metadata) return;
      setRemoteSummary((prev) => ({ ...prev, [selectedSnapshot.id]: metadata }));
    });
    return () => {
      cancelled = true;
    };
  }, [selectedSnapshot]);

  const selectedRun = useMemo(
    () => state.moduleRuns.find((run) => run.id === selectedSnapshot?.runId),
    [selectedSnapshot?.runId, state.moduleRuns]
  );

  const chapters = useMemo(() => readChapters(selectedRun), [selectedRun]);

  // Structured IR is the primary body source; it is fetched on demand and held
  // in memory only (never persisted). Response-compat chapters remain the
  // fallback, and DOCX never enters the body path.
  const reportIr = useReportIr(selectedSnapshot?.taskSpaceId ?? "", selectedSnapshot?.module ?? "");
  const traceLinks = useMemo(
    () => (selectedSnapshot ? buildTraceLinks(selectedSnapshot, state.moduleRuns, state.issues, state.evidenceHits) : []),
    [selectedSnapshot, state.evidenceHits, state.issues, state.moduleRuns]
  );

  const summary = selectedSnapshot ? remoteSummary[selectedSnapshot.id]?.summary : undefined;
  const version = selectedSnapshot ? remoteSummary[selectedSnapshot.id]?.version ?? selectedSnapshot.version : "";
  const risk = selectedSnapshot ? remoteSummary[selectedSnapshot.id]?.risk_level ?? selectedSnapshot.riskLevel : "";

  const copyPath = async (snapshot: ReportReviewSnapshot) => {
    try {
      await navigator.clipboard.writeText(snapshot.artifactPath);
      setCopiedPath(snapshot.id);
      window.setTimeout(() => setCopiedPath(""), 1200);
    } catch {
      setCopiedPath("");
    }
  };

  return (
    <section className="page-shell report-review-page">
      <header className="page-header">
        <h2>{t("reportCenterTitle")}</h2>
        <input
          className="resource-search"
          placeholder={t("searchPlaceholder")}
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <div className="report-task-count-pill">{t("taskSpacesTitle")} · {treeNodes.length}</div>
      </header>

      <div className="report-review-layout">
        <aside className="report-pane report-pane-list">
          <div className="pane-title">{t("reportReviewList")}</div>
          <ReportTaskTreeSidebar
            tasks={treeNodes}
            selectedTaskId={selectedSnapshot?.taskSpaceId ?? ""}
            selectedSnapshotId={selectedSnapshot?.id ?? ""}
            onSelectSnapshot={setSelectedId}
            emptyText={t("reportNoData")}
            emptyDocumentsText={t("reportTaskEmpty")}
          />
        </aside>

        <main className="report-pane report-pane-preview">
          <div className="pane-title">{t("reportReviewPreview")}</div>
          {selectedSnapshot ? (
            <section className="report-preview-paper">
              <header className="report-preview-head">
                <h3>{selectedSnapshot.module.toUpperCase()} · {t("reportDraftLabel")}</h3>
                <p>{summary ?? t("reportOpenHint")}</p>
              </header>
              <div className="report-preview-summary">
                <span>{t("reportVersionLabel")}: {version}</span>
                <span>{t("reportGeneratedAt")}: {new Date(selectedSnapshot.generatedAt).toLocaleString()}</span>
                <span>{t("reportRiskLabel")}: {risk || t("reportNoEvidenceLabel")}</span>
                <span>{t("reportRunSource")}: {selectedSnapshot.module.toUpperCase()}</span>
              </div>
              <article className="report-preview-body">
                {reportIr.status === "ready" ? (
                  <ReportDocumentView document={reportIr.document} />
                ) : (
                  <>
                    {reportIr.status === "error" ? (
                      <p className="ir-report-error" role="alert">
                        {t("reportIrError")}：{reportIr.message}
                      </p>
                    ) : null}
                    {chapters.map((chapter, index) => (
                      <section key={`${chapter.title}-${index}`} className="report-preview-chapter">
                        <h4>{chapter.title}</h4>
                        <p>{chapter.content.slice(0, 520) || "..."}</p>
                      </section>
                    ))}
                    {chapters.length === 0 && reportIr.status !== "loading" ? (
                      <p className="resource-empty">{t("previewEmpty")}</p>
                    ) : null}
                  </>
                )}
              </article>
            </section>
          ) : (
            <p className="resource-empty">{t("reportNoData")}</p>
          )}
        </main>

        <aside className="report-pane report-pane-trace">
          <div className="pane-title">{t("reportReviewTrace")}</div>
          {remoteReports.length > 0 ? (
            <section className="report-trace-stack">
              <div className="report-download-box">
                <small>{t("navReports")} · {remoteReports.length}</small>
                <code>{t("reportDownloadHint")}</code>
              </div>
            </section>
          ) : null}
          {selectedSnapshot ? (
            <section className="report-trace-stack">
              <div className="report-trace-kpis">
                <article>
                  <small>{t("reportIssueCount")}</small>
                  <strong>{selectedSnapshot.issueCount}</strong>
                </article>
                <article>
                  <small>{t("reportEvidenceCount")}</small>
                  <strong>{selectedSnapshot.evidenceCount}</strong>
                </article>
              </div>
              <div className="report-download-box">
                <small>{t("reportDownloadHint")}</small>
                <button className="pill-btn" onClick={() => copyPath(selectedSnapshot)}>
                  {copiedPath === selectedSnapshot.id ? t("reportPathCopied") : t("reportCopyPath")}
                </button>
              </div>

              <div className="report-trace-list">
                {traceLinks.map((link) => (
                  <article key={link.id} className="report-trace-item">
                    <strong>{link.title}</strong>
                    {link.excerpt ? <p>{link.excerpt}</p> : null}
                  </article>
                ))}
                {traceLinks.length === 0 ? <p className="resource-empty">{t("reportTraceEmpty")}</p> : null}
              </div>
            </section>
          ) : (
            <p className="resource-empty">{t("reportNoData")}</p>
          )}
        </aside>
      </div>
    </section>
  );
}
