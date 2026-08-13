import { useMemo, useState } from "react";
import type { InputEntry, ResourceOpenTarget, TreeNode } from "../../features/resource-explorer/contracts";
import { INPUT_SOURCE_KIND_LABELS } from "../../features/resource-explorer/config";
import { buildInputEntries } from "../../features/resource-explorer/input-resources";
import { buildOutputEntries } from "../../features/resource-explorer/output-artifacts";
import { buildPathTree } from "../../features/resource-explorer/path-tree";
import { useAppStore } from "../../lib/app-store";
import type { TaskSpace } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { ChevronToggleIcon, FileNodeIcon, FolderInputIcon, FolderOutputIcon } from "../common/AppIcons";

export type { ResourceOpenTarget } from "../../features/resource-explorer/contracts";

type ResourcePanelProps = {
  taskSpace: TaskSpace;
  onToggleCollapse: () => void;
  onOpenResource: (target: ResourceOpenTarget) => void;
  selectedOutputPath?: string | null;
};

export function ResourcePanel({ taskSpace, onToggleCollapse, onOpenResource, selectedOutputPath }: ResourcePanelProps) {
  const { state } = useAppStore();
  const { lang } = useLang();
  const copy = lang === "zh"
    ? {
        panelTitle: "任务材料",
        inputLabel: "已提交材料",
        outputLabel: "生成结果",
        inputEmpty: "暂无已提交材料",
        outputEmpty: "暂无生成结果"
      }
    : {
        panelTitle: "Task Materials",
        inputLabel: "Submitted Materials",
        outputLabel: "Generated Results",
        inputEmpty: "No submitted materials yet",
        outputEmpty: "No generated results yet"
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

  const outputEntries = useMemo(
    () => buildOutputEntries(outputFiles, relatedRuns, lang),
    [lang, outputFiles, relatedRuns]
  );

  const inputEntries = useMemo(
    () => buildInputEntries(relatedRuns, outputFiles, lang),
    [lang, outputFiles, relatedRuns]
  );

  const inputGroups = useMemo(() => {
    const byKind = new Map<string, InputEntry[]>();
    const unlabeled: InputEntry[] = [];
    for (const entry of inputEntries) {
      if (entry.sourceKind) {
        const list = byKind.get(entry.sourceKind) ?? [];
        list.push(entry);
        byKind.set(entry.sourceKind, list);
      } else {
        unlabeled.push(entry);
      }
    }
    const groups: { key: string; label: string; entries: InputEntry[] }[] = [];
    for (const [kind, list] of byKind) {
      groups.push({
        key: kind,
        label: INPUT_SOURCE_KIND_LABELS[kind]?.[lang] ?? kind,
        entries: list,
      });
    }
    if (unlabeled.length) groups.push({ key: "other", label: "", entries: unlabeled });
    return groups;
  }, [inputEntries, lang]);

  const outputFileMap = useMemo(
    () => new Map(outputEntries.map((entry) => [entry.virtualPath, entry.artifact])),
    [outputEntries]
  );
  const outputTree = useMemo(
    () => buildPathTree(outputEntries.map((entry) => entry.virtualPath), "tree-output"),
    [outputEntries]
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
        return [
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
                <FolderOutputIcon width="14" height="14" />
              </span>
              <span className="ide-tree-label">{node.name}</span>
            </button>
            {expanded && node.children.length > 0 ? (
              <ul className="ide-tree-list ide-tree-children">{renderTreeNodes(node.children, depth + 1, allowFileSelect)}</ul>
            ) : null}
          </li>
        ];
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
              onClick={() => onOpenResource({ kind: "output", artifact })}
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
      <div className="pane-title resource-pane-headline">{copy.panelTitle}</div>
      <button
        className="workspace-side-toggle workspace-side-toggle-left"
        onClick={onToggleCollapse}
        aria-label="collapse-left-sidebar"
      >
        <ChevronToggleIcon direction="left" width="16" height="16" />
      </button>
      <div className="resource-pane-body resource-pane-body-ide">
        <section className="ide-tree-shell" aria-label={copy.panelTitle}>
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
                    {inputGroups.map((group) => (
                      <li key={group.key}>
                        {group.label ? (
                          <div className="ide-tree-row ide-tree-row-group" style={{ ["--tree-depth" as string]: 1 }}>
                            <span className="ide-tree-label ide-tree-group-label">{group.label}</span>
                          </div>
                        ) : null}
                        <ul className="ide-tree-list">
                          {group.entries.map((entry) => (
                            <li key={entry.id}>
                              <div
                                className="ide-tree-row ide-tree-row-file"
                                style={{ ["--tree-depth" as string]: group.label ? 2 : 1 }}
                                title={lang === "zh" ? "已记录输入文件；安全预览接口尚未统一，当前仅展示" : "Input recorded; preview is display-only until access control is unified"}
                              >
                                <span className="ide-tree-caret ide-tree-caret-empty" aria-hidden="true" />
                                <span className="ide-tree-icon">
                                  <FileNodeIcon width="14" height="14" />
                                </span>
                                <span className="ide-tree-label">{entry.name}</span>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
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
      </div>
    </aside>
  );
}
