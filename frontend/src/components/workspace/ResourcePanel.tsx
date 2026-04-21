import { useMemo, useState } from "react";
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

const toFolderPath = (value: string): string => {
  const normalized = value.replace(/\\/g, "/");
  const chunks = normalized.split("/");
  chunks.pop();
  return chunks.join("/");
};

type TreeNode = {
  id: string;
  type: "folder" | "file";
  name: string;
  path?: string;
  children: TreeNode[];
};

type OutputTreeEntry = {
  virtualPath: string;
  artifact: OutputArtifact;
};

type InputEntry = {
  id: string;
  name: string;
  kind: "file" | "form";
  sourcePath?: string;
  payload?: unknown;
  createdAt: string;
};

type MutableTreeNode = TreeNode & {
  childrenMap: Map<string, MutableTreeNode>;
};

const createFolderNode = (id: string, name: string): MutableTreeNode => ({
  id,
  type: "folder",
  name,
  children: [],
  childrenMap: new Map<string, MutableTreeNode>()
});

const createFileNode = (id: string, name: string, path: string): MutableTreeNode => ({
  id,
  type: "file",
  name,
  path,
  children: [],
  childrenMap: new Map<string, MutableTreeNode>()
});

const finalizeTree = (nodes: MutableTreeNode[]): TreeNode[] =>
  nodes
    .map((node) => ({
      id: node.id,
      type: node.type,
      name: node.name,
      path: node.path,
      children: finalizeTree(Array.from(node.childrenMap.values()))
    }))
    .sort((a, b) => {
      if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
      return a.name.localeCompare(b.name);
    });

const buildPathTree = (paths: string[], prefix: string): TreeNode[] => {
  const rootMap = new Map<string, MutableTreeNode>();
  paths.forEach((rawPath) => {
    const normalized = rawPath.replace(/\\/g, "/");
    const chunks = normalized.split("/").filter(Boolean);
    if (chunks.length === 0) return;

    let cursor = rootMap;
    const breadcrumb: string[] = [];
    chunks.forEach((chunk, index) => {
      breadcrumb.push(chunk);
      const isFile = index === chunks.length - 1;
      const key = `${isFile ? "file" : "folder"}:${chunk}`;
      if (!cursor.has(key)) {
        const nodeId = `${prefix}:${isFile ? "file" : "folder"}:${breadcrumb.join("/")}`;
        cursor.set(key, isFile ? createFileNode(nodeId, chunk, normalized) : createFolderNode(nodeId, chunk));
      }
      const node = cursor.get(key);
      if (node && !isFile) cursor = node.childrenMap;
    });
  });

  return finalizeTree(Array.from(rootMap.values()));
};

const hasFileExtension = (value: string): boolean => /\.(docx?|pdf|md|html|txt|csv|xlsx?|png|jpg|jpeg|json)$/i.test(value);

const looksLikeFilePath = (value: string): boolean => {
  const trimmed = value.trim();
  if (!trimmed) return false;
  if (hasFileExtension(trimmed)) return true;
  if (/^(storage\/|outputs\/|uploads\/|\/|[a-zA-Z]:\\)/.test(trimmed)) return true;
  if (/[\\/]/.test(trimmed) && !/\s\/\s/.test(trimmed)) return true;
  return false;
};

function collectPaths(value: unknown, bag: Set<string>) {
  if (typeof value === "string") {
    if (looksLikeFilePath(value)) {
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

const parseTime = (value: string | undefined): number | null => {
  if (!value) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export function ResourcePanel({ taskSpace, onToggleCollapse, onSelectOutput, selectedOutputPath }: ResourcePanelProps) {
  const { state } = useAppStore();
  const { lang, t } = useLang();
  const copy =
    lang === "zh"
      ? {
          inputLabel: "输入",
          outputLabel: "产物",
          inputEmpty: "暂无输入记录",
          outputEmpty: "暂无已生成输出文件"
        }
      : {
          inputLabel: "INPUT",
          outputLabel: "OUTPUT",
          inputEmpty: "No input records yet",
          outputEmpty: "No generated output files yet"
        };
  const [expandedFolderIds, setExpandedFolderIds] = useState<Set<string>>(
    () => new Set(["tree-root-input", "tree-root-output"])
  );
  const [selectedInputId, setSelectedInputId] = useState<string | null>(null);

  const relatedRuns = useMemo(
    () => state.moduleRuns.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.moduleRuns, taskSpace.id]
  );

  const outputFiles = useMemo(
    () => state.artifacts.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.artifacts, taskSpace.id]
  );

  const outputEntries = useMemo<OutputTreeEntry[]>(() => {
    if (outputFiles.length === 0) return [];

    const uniqueOutputFiles: OutputArtifact[] = [];
    const seenArtifactPaths = new Set<string>();
    for (const artifact of outputFiles) {
      if (seenArtifactPaths.has(artifact.path)) continue;
      seenArtifactPaths.add(artifact.path);
      uniqueOutputFiles.push(artifact);
    }

    const runsWithTime = relatedRuns
      .map((run) => {
        const startedAt = parseTime(run.startedAt);
        const finishedAt = parseTime(run.finishedAt);
        const anchorTime = startedAt ?? finishedAt;
        return anchorTime === null ? null : { runId: run.id, time: anchorTime };
      })
      .filter((item): item is { runId: string; time: number } => !!item)
      .sort((a, b) => b.time - a.time);

    const runFolderById = new Map<string, string>();
    runsWithTime.forEach((item, index) => {
      runFolderById.set(item.runId, `run-${String(index + 1).padStart(3, "0")}`);
    });

    const assignRunFolder = (artifact: OutputArtifact): string => {
      const artifactTime = parseTime(artifact.createdAt);
      if (artifactTime === null || runsWithTime.length === 0) return "run-unknown";
      for (let index = 0; index < runsWithTime.length; index += 1) {
        const lowerBound = runsWithTime[index].time;
        const upperBound = index === 0 ? Number.POSITIVE_INFINITY : runsWithTime[index - 1].time;
        if (artifactTime >= lowerBound && artifactTime < upperBound) {
          return runFolderById.get(runsWithTime[index].runId) ?? "run-unknown";
        }
      }
      return "run-unknown";
    };

    return uniqueOutputFiles.map((artifact) => {
      const folder = toFolderPath(artifact.path);
      const fileName = toFileName(artifact.path);
      const runFolder = assignRunFolder(artifact);
      const virtualPath = folder ? `${folder}/${runFolder}/${fileName}` : `${runFolder}/${fileName}`;
      return { virtualPath, artifact };
    });
  }, [outputFiles, relatedRuns]);

  const inputEntries = useMemo<InputEntry[]>(() => {
    const sortedRuns = [...relatedRuns].sort((a, b) => (a.startedAt < b.startedAt ? 1 : -1));
    const entries: InputEntry[] = [];
    const usedNames = new Map<string, number>();
    const seenPaths = new Set<string>();

    const pickUniqueName = (baseName: string): string => {
      const count = (usedNames.get(baseName) ?? 0) + 1;
      usedNames.set(baseName, count);
      return count === 1 ? baseName : `${baseName} (${count})`;
    };

    sortedRuns.forEach((run, index) => {
      entries.push({
        id: `input-form-${run.id}`,
        name: pickUniqueName(`form_submission_${String(index + 1).padStart(3, "0")}.json`),
        kind: "form",
        payload: run.request,
        createdAt: run.startedAt
      });

      const bag = new Set<string>();
      collectPaths(run.request, bag);
      Array.from(bag)
        .filter((path) => !outputFiles.some((file) => file.path === path))
        .forEach((path) => {
          if (seenPaths.has(path)) return;
          seenPaths.add(path);
          entries.push({
            id: `input-file-${path}`,
            name: pickUniqueName(toFileName(path)),
            kind: "file",
            sourcePath: path,
            createdAt: run.startedAt
          });
        });
    });

    return entries;
  }, [outputFiles, relatedRuns]);

  const outputFileMap = useMemo(
    () => new Map(outputEntries.map((entry) => [entry.virtualPath, entry.artifact])),
    [outputEntries]
  );
  const inputEntryById = useMemo(
    () => new Map(inputEntries.map((entry) => [entry.id, entry])),
    [inputEntries]
  );
  const outputTree = useMemo(
    () => buildPathTree(outputEntries.map((entry) => entry.virtualPath), "tree-output"),
    [outputEntries]
  );
  const selectedInputEntry = selectedInputId ? inputEntryById.get(selectedInputId) ?? null : null;

  const toggleFolder = (folderId: string) => {
    setExpandedFolderIds((prev) => {
      const next = new Set(prev);
      if (next.has(folderId)) next.delete(folderId);
      else next.add(folderId);
      return next;
    });
  };

  const renderTreeNodes = (nodes: TreeNode[], depth: number, allowFileSelect: boolean): JSX.Element[] =>
    nodes.flatMap((node) => {
      if (node.type === "folder") {
        const expanded = expandedFolderIds.has(node.id);
        const row = (
          <li key={node.id}>
            <button
              type="button"
              className="ide-tree-row ide-tree-row-folder"
              style={{ ["--tree-depth" as string]: depth }}
              onClick={() => toggleFolder(node.id)}
            >
              <span className={`ide-tree-caret ${expanded ? "expanded" : ""}`} aria-hidden="true">
                ▸
              </span>
              <span className="ide-tree-icon">
                <FolderInputIcon width="14" height="14" />
              </span>
              <span className="ide-tree-label">{node.name}</span>
            </button>
            {expanded && node.children.length > 0 ? (
              <ul className="ide-tree-list ide-tree-children">{renderTreeNodes(node.children, depth + 1, allowFileSelect)}</ul>
            ) : null}
          </li>
        );
        return [row];
      }

      const artifact = node.path ? outputFileMap.get(node.path) : undefined;
      const isActive = allowFileSelect && !!artifact && selectedOutputPath === artifact.path;
      const rowClass = `ide-tree-row ide-tree-row-file ${isActive ? "active" : ""}`;
      const rowContent = (
        <>
          <span className="ide-tree-caret ide-tree-caret-empty" aria-hidden="true" />
          <span className="ide-tree-icon">
            <FileNodeIcon width="14" height="14" />
          </span>
          <span className="ide-tree-label">{node.name}</span>
        </>
      );

      return [
        <li key={node.id}>
          {allowFileSelect && artifact ? (
            <button
              type="button"
              className={rowClass}
              style={{ ["--tree-depth" as string]: depth }}
              onClick={() => onSelectOutput(artifact)}
            >
              {rowContent}
            </button>
          ) : (
            <div className={rowClass} style={{ ["--tree-depth" as string]: depth }}>
              {rowContent}
            </div>
          )}
        </li>
      ];
    });

  return (
    <aside className="pane resource-pane resource-pane-ide" data-guide="workspace-left">
      <div className="pane-title resource-pane-headline">{t("leftTitle")}</div>
      <button
        className="workspace-side-toggle workspace-side-toggle-left"
        onClick={onToggleCollapse}
        aria-label="collapse-left-sidebar"
      >
        <ChevronToggleIcon direction="left" width="16" height="16" />
      </button>
      <div className="resource-pane-body resource-pane-body-ide">
        <section className="ide-tree-shell" aria-label={t("leftTitle")}>
          <ul className="ide-tree-list">
            <li>
              <button
                type="button"
                className="ide-tree-row ide-tree-row-root"
                onClick={() => toggleFolder("tree-root-input")}
              >
                <span className={`ide-tree-caret ${expandedFolderIds.has("tree-root-input") ? "expanded" : ""}`} aria-hidden="true">
                  ▸
                </span>
                <span className="ide-tree-icon">
                  <FolderInputIcon width="14" height="14" />
                </span>
                <span className="ide-tree-label">{copy.inputLabel}</span>
                <small>{inputEntries.length}</small>
              </button>
              {expandedFolderIds.has("tree-root-input") ? (
                inputEntries.length > 0 ? (
                  <ul className="ide-tree-list ide-tree-children">
                    {inputEntries.map((entry) => {
                      const isActive = selectedInputId === entry.id;
                      return (
                        <li key={entry.id}>
                          <button
                            type="button"
                            className={`ide-tree-row ide-tree-row-file ${isActive ? "active" : ""}`}
                            style={{ ["--tree-depth" as string]: 1 }}
                            onClick={() => setSelectedInputId(entry.id)}
                          >
                            <span className="ide-tree-caret ide-tree-caret-empty" aria-hidden="true" />
                            <span className="ide-tree-icon">
                              <FileNodeIcon width="14" height="14" />
                            </span>
                            <span className="ide-tree-label">{entry.name}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <p className="ide-folder-empty">{copy.inputEmpty}</p>
                )
              ) : null}
            </li>

            <li>
              <button
                type="button"
                className="ide-tree-row ide-tree-row-root"
                onClick={() => toggleFolder("tree-root-output")}
              >
                <span className={`ide-tree-caret ${expandedFolderIds.has("tree-root-output") ? "expanded" : ""}`} aria-hidden="true">
                  ▸
                </span>
                <span className="ide-tree-icon">
                  <FolderOutputIcon width="14" height="14" />
                </span>
                <span className="ide-tree-label">{copy.outputLabel}</span>
                <small>{outputEntries.length}</small>
              </button>
              {expandedFolderIds.has("tree-root-output") ? (
                outputTree.length > 0 ? (
                  <ul className="ide-tree-list ide-tree-children">{renderTreeNodes(outputTree, 1, true)}</ul>
                ) : (
                  <p className="ide-folder-empty">{copy.outputEmpty}</p>
                )
              ) : null}
            </li>
          </ul>
        </section>
        {selectedInputEntry ? (
          <section className="schema-upload-card">
            <div className="runner-title">
              {selectedInputEntry.kind === "form"
                ? (lang === "zh" ? "表单提交详情" : "Form Submission Detail")
                : (lang === "zh" ? "输入文件详情" : "Input File Detail")}
            </div>
            {selectedInputEntry.kind === "form" ? (
              <textarea
                className="runner-textarea schema-textarea"
                readOnly
                value={JSON.stringify(selectedInputEntry.payload ?? {}, null, 2)}
              />
            ) : (
              <div className="runner-empty-card">{selectedInputEntry.sourcePath}</div>
            )}
          </section>
        ) : null}
      </div>
    </aside>
  );
}
