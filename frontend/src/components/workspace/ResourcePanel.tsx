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

type TreeNode = {
  id: string;
  type: "folder" | "file";
  name: string;
  path?: string;
  children: TreeNode[];
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
  const { lang, t } = useLang();
  const copy =
    lang === "zh"
      ? {
          inputLabel: "输入",
          outputLabel: "产物",
          inputEmpty: "暂无已上传输入文件",
          outputEmpty: "暂无已生成输出文件"
        }
      : {
          inputLabel: "INPUT",
          outputLabel: "OUTPUT",
          inputEmpty: "No uploaded input files yet",
          outputEmpty: "No generated output files yet"
        };
  const [expandedFolderIds, setExpandedFolderIds] = useState<Set<string>>(
    () => new Set(["tree-root-input", "tree-root-output"])
  );

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

  const outputFileMap = useMemo(
    () => new Map(outputFiles.map((file) => [file.path, file])),
    [outputFiles]
  );
  const inputTree = useMemo(
    () => buildPathTree(inputFiles.map((file) => file.path), "tree-input"),
    [inputFiles]
  );
  const outputTree = useMemo(
    () => buildPathTree(outputFiles.map((file) => file.path), "tree-output"),
    [outputFiles]
  );

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
      const isActive = allowFileSelect && !!node.path && selectedOutputPath === node.path;
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
                <small>{inputFiles.length}</small>
              </button>
              {expandedFolderIds.has("tree-root-input") ? (
                inputTree.length > 0 ? (
                  <ul className="ide-tree-list ide-tree-children">{renderTreeNodes(inputTree, 1, false)}</ul>
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
                <small>{outputFiles.length}</small>
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
      </div>
    </aside>
  );
}
