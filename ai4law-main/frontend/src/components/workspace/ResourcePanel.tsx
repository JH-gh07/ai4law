import { useMemo } from "react";
import { useAppStore } from "../../lib/app-store";
import type { OutputArtifact, TaskSpace } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { ChevronToggleIcon, FileNodeIcon, FolderInputIcon, FolderOutputIcon } from "../common/AppIcons";

type ResourcePanelProps = {
  taskSpace: TaskSpace;
  onToggleCollapse: () => void;
  onSelectOutput: (artifact: OutputArtifact) => void;
  selectedOutputPath?: string | null;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const toFileName = (value: string): string => {
  const normalized = value.replace(/\\/g, "/");
  const chunks = normalized.split("/");
  return chunks[chunks.length - 1] || value;
};

function collectPaths(value: unknown, bag: Set<string>) {
  if (typeof value === "string") {
    if (/[\\/]/.test(value) || /\.(docx?|pdf|md|html|txt|csv|xlsx?|png|jpg|jpeg)$/i.test(value)) {
      bag.add(value);
    }
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item) => collectPaths(item, bag));
    return;
  }
  if (isRecord(value)) {
    Object.values(value).forEach((item) => collectPaths(item, bag));
  }
}

export function ResourcePanel({ taskSpace, onToggleCollapse, onSelectOutput, selectedOutputPath }: ResourcePanelProps) {
  const { state } = useAppStore();
  const { lang } = useLang();

  const relatedRuns = useMemo(
    () => state.moduleRuns.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.moduleRuns, taskSpace.id]
  );

  const outputFiles = useMemo(
    () => state.artifacts.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.artifacts, taskSpace.id]
  );

  const inputFiles = useMemo(() => {
    const bag = new Set<string>();
    relatedRuns.forEach((run) => collectPaths(run.request, bag));
    return Array.from(bag)
      .filter((path) => !outputFiles.some((file) => file.path === path))
      .map((path) => ({ id: path, name: toFileName(path), path }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [outputFiles, relatedRuns]);

  return (
    <aside className="pane resource-pane resource-pane-ide" data-guide="workspace-left">
      <div className="pane-title resource-pane-headline">Project Files</div>
      <button className="workspace-side-toggle workspace-side-toggle-left" onClick={onToggleCollapse} aria-label="collapse-left-sidebar">
        <ChevronToggleIcon direction="left" width="16" height="16" />
      </button>
      <div className="resource-pane-body resource-pane-body-ide">
        <section className="ide-tree-section">
          <div className="ide-folder-head">
            <div className="ide-folder-title">
              <FolderInputIcon width="16" height="16" />
              <span>{lang === "zh" ? "input" : "input"}</span>
            </div>
            <small>{inputFiles.length}</small>
          </div>
          <div className="ide-file-list">
            {inputFiles.length > 0 ? (
              inputFiles.map((file) => (
                <article key={file.id} className="ide-file-row">
                  <span className="ide-file-icon"><FileNodeIcon width="14" height="14" /></span>
                  <div className="ide-file-copy">
                    <strong>{file.name}</strong>
                    <span>{file.path}</span>
                  </div>
                </article>
              ))
            ) : (
              <p className="ide-folder-empty">{lang === "zh" ? "暂无已上传输入文件" : "No uploaded input files yet"}</p>
            )}
          </div>
        </section>

        <section className="ide-tree-section">
          <div className="ide-folder-head">
            <div className="ide-folder-title">
              <FolderOutputIcon width="16" height="16" />
              <span>{lang === "zh" ? "output" : "output"}</span>
            </div>
            <small>{outputFiles.length}</small>
          </div>
          <div className="ide-file-list">
            {outputFiles.length > 0 ? (
              outputFiles.map((file) => (
                <button
                  type="button"
                  key={file.id}
                  className={`ide-file-row ide-file-row-button ${selectedOutputPath === file.path ? "active" : ""}`}
                  onClick={() => onSelectOutput(file)}
                >
                  <span className="ide-file-icon"><FileNodeIcon width="14" height="14" /></span>
                  <div className="ide-file-copy">
                    <strong>{toFileName(file.path)}</strong>
                    <span>{file.kind.toUpperCase()}</span>
                  </div>
                </button>
              ))
            ) : (
              <p className="ide-folder-empty">{lang === "zh" ? "暂无生成报告或产物文件" : "No generated output files yet"}</p>
            )}
          </div>
        </section>
      </div>
    </aside>
  );
}
