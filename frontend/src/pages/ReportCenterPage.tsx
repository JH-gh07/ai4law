import { useEffect, useMemo, useState } from "react";
import { useAppStore } from "../lib/app-store";
import type { ModuleRun, ReportReviewSnapshot } from "../lib/domain";
import { useLang } from "../lib/language";
import { buildReportSnapshots, buildTraceLinks, fetchReportMetadata } from "../lib/report-adapter";

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
  const [taskId, setTaskId] = useState<string>("ALL");
  const [selectedId, setSelectedId] = useState<string>("");
  const [remoteSummary, setRemoteSummary] = useState<Record<string, { summary?: string; version?: string; risk_level?: string }>>({});
  const [copiedPath, setCopiedPath] = useState("");

  const snapshots = useMemo(() => {
    const list = state.taskSpaces.flatMap((task) =>
      buildReportSnapshots(task, state.artifacts, state.moduleRuns, state.issues, state.evidenceHits)
    );
    const token = keyword.trim().toLowerCase();
    return list
      .filter((item) => (taskId === "ALL" ? true : item.taskSpaceId === taskId))
      .filter((item) => (token ? `${item.module} ${item.artifactPath}`.toLowerCase().includes(token) : true));
  }, [keyword, state.artifacts, state.evidenceHits, state.issues, state.moduleRuns, state.taskSpaces, taskId]);

  useEffect(() => {
    if (!selectedId && snapshots.length > 0) {
      setSelectedId(snapshots[0].id);
    }
    if (selectedId && snapshots.every((item) => item.id !== selectedId)) {
      setSelectedId(snapshots[0]?.id ?? "");
    }
  }, [selectedId, snapshots]);

  const selectedSnapshot = snapshots.find((item) => item.id === selectedId) ?? snapshots[0] ?? null;

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
        <select className="runner-select report-task-select" value={taskId} onChange={(event) => setTaskId(event.target.value)}>
          <option value="ALL">{t("taskSpacesTitle")}</option>
          {state.taskSpaces.map((task) => (
            <option key={task.id} value={task.id}>{task.name}</option>
          ))}
        </select>
      </header>

      <div className="report-review-layout">
        <aside className="report-pane report-pane-list">
          <div className="pane-title">{t("reportReviewList")}</div>
          <div className="report-list-scroll">
            {snapshots.map((snapshot) => (
              <article
                key={snapshot.id}
                className={`report-list-item ${snapshot.id === selectedSnapshot?.id ? "active" : ""}`}
                onClick={() => setSelectedId(snapshot.id)}
              >
                <div className="report-list-head">
                  <strong>{snapshot.module.toUpperCase()}</strong>
                  <span>{t("reportDraftLabel")}</span>
                </div>
                <p>{snapshot.artifactKind.toUpperCase()} · {snapshot.artifactPath.split("/").slice(-1)[0]}</p>
                <div className="report-list-meta">
                  <span>{t("reportRiskLabel")}: {snapshot.riskLevel}</span>
                  <span>{t("reportIssueCount")}: {snapshot.issueCount}</span>
                </div>
              </article>
            ))}
            {snapshots.length === 0 ? <p className="resource-empty">{t("reportNoData")}</p> : null}
          </div>
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
                {chapters.map((chapter, index) => (
                  <section key={`${chapter.title}-${index}`} className="report-preview-chapter">
                    <h4>{chapter.title}</h4>
                    <p>{chapter.content.slice(0, 520) || "..."}</p>
                  </section>
                ))}
                {chapters.length === 0 ? <p className="resource-empty">{t("previewEmpty")}</p> : null}
              </article>
            </section>
          ) : (
            <p className="resource-empty">{t("reportNoData")}</p>
          )}
        </main>

        <aside className="report-pane report-pane-trace">
          <div className="pane-title">{t("reportReviewTrace")}</div>
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
                <code>{selectedSnapshot.artifactPath}</code>
                <button className="pill-btn" onClick={() => copyPath(selectedSnapshot)}>
                  {copiedPath === selectedSnapshot.id ? t("reportPathCopied") : t("reportCopyPath")}
                </button>
              </div>

              <div className="report-trace-list">
                {traceLinks.map((link) => (
                  <article key={link.id} className="report-trace-item">
                    <small>{link.targetType.toUpperCase()}</small>
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

