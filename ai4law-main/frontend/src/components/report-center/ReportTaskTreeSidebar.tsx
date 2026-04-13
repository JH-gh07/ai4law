import { useEffect, useMemo, useState } from "react";
import type { ModuleKey } from "../../lib/domain";
import { useLang } from "../../lib/language";

export type ReportTaskTreeDocument = {
  snapshotId: string;
  title: string;
  generatedAt: string;
  module: ModuleKey;
  artifactKind: string;
  riskLevel: string;
};

export type ReportTaskTreeNode = {
  taskId: string;
  taskName: string;
  taskUpdatedAt: string;
  documents: ReportTaskTreeDocument[];
};

type ReportTaskTreeSidebarProps = {
  tasks: ReportTaskTreeNode[];
  selectedTaskId: string;
  selectedSnapshotId: string;
  onSelectSnapshot: (snapshotId: string) => void;
  emptyText: string;
  emptyDocumentsText: string;
};

export function ReportTaskTreeSidebar({
  tasks,
  selectedTaskId,
  selectedSnapshotId,
  onSelectSnapshot,
  emptyText,
  emptyDocumentsText
}: ReportTaskTreeSidebarProps) {
  const { lang } = useLang();
  const [expandedTaskIds, setExpandedTaskIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setExpandedTaskIds((prev) => {
      const validTaskIds = new Set(tasks.map((item) => item.taskId));
      const next = new Set(Array.from(prev).filter((taskId) => validTaskIds.has(taskId)));
      if (selectedTaskId && validTaskIds.has(selectedTaskId)) {
        next.add(selectedTaskId);
      }
      if (next.size === 0 && tasks[0]) {
        next.add(tasks[0].taskId);
      }
      return next;
    });
  }, [selectedTaskId, tasks]);

  const toggleTask = (taskId: string) => {
    setExpandedTaskIds((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  };

  const locale = useMemo(() => (lang === "zh" ? "zh-CN" : "en-US"), [lang]);

  return (
    <div className="report-task-tree-scroll">
      {tasks.map((task) => {
        const expanded = expandedTaskIds.has(task.taskId);
        const activeTask = task.taskId === selectedTaskId;
        return (
          <section key={task.taskId} className={`report-task-node ${activeTask ? "active" : ""}`}>
            <button type="button" className="report-task-trigger" onClick={() => toggleTask(task.taskId)}>
              <span className={`report-task-caret ${expanded ? "open" : ""}`} aria-hidden>
                ▸
              </span>
              <div className="report-task-main">
                <strong>{task.taskName}</strong>
                <small>{task.taskId}</small>
              </div>
              <span className="report-task-count">{task.documents.length}</span>
            </button>

            {expanded ? (
              <div className="report-doc-tree">
                {task.documents.map((doc) => (
                  <button
                    key={doc.snapshotId}
                    type="button"
                    className={`report-doc-node ${doc.snapshotId === selectedSnapshotId ? "active" : ""}`}
                    onClick={() => onSelectSnapshot(doc.snapshotId)}
                  >
                    <div className="report-doc-main">
                      <strong>{doc.title}</strong>
                      <small>{new Date(doc.generatedAt).toLocaleString(locale)}</small>
                    </div>
                    <div className="report-doc-tags">
                      <span>{doc.artifactKind.toUpperCase()}</span>
                      <span>{doc.module.toUpperCase()}</span>
                      <span>{doc.riskLevel}</span>
                    </div>
                  </button>
                ))}
                {task.documents.length === 0 ? <p className="report-doc-empty">{emptyDocumentsText}</p> : null}
              </div>
            ) : null}
          </section>
        );
      })}
      {tasks.length === 0 ? <p className="resource-empty">{emptyText}</p> : null}
    </div>
  );
}
