import { useMemo, useState } from "react";
import { useAppStore } from "../../lib/app-store";
import type { OutputArtifact, TaskSpace } from "../../lib/domain";
import { useLang } from "../../lib/language";
import { ChevronToggleIcon, FileNodeIcon, FolderInputIcon, FolderOutputIcon } from "../common/AppIcons";

type ResourcePanelProps = {
  taskSpace: TaskSpace;
  onToggleCollapse: () => void;
  onOpenResource: (target: ResourceOpenTarget) => void;
  selectedOutputPath?: string | null;
};

export type ResourceOpenTarget =
  | { kind: "output"; artifact: OutputArtifact }
  | {
      kind: "input-form";
      entry: {
        id: string;
        name: string;
        payload?: unknown;
        createdAt: string;
      };
    }
  | {
      kind: "input-file";
      entry: {
        id: string;
        name: string;
        sourcePath: string;
        createdAt: string;
      };
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

type InputResourceCandidate = {
  path: string;
  labelHint?: string;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const toFileName = (value: string): string => {
  const normalized = value.replace(/\\/g, "/");
  const chunks = normalized.split("/");
  return chunks[chunks.length - 1] || value;
};

const getFileExtension = (value: string): string => {
  const fileName = toFileName(value).toLowerCase();
  const dotIndex = fileName.lastIndexOf(".");
  return dotIndex === -1 ? "" : fileName.slice(dotIndex + 1);
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

const prettifyStem = (value: string): string =>
  value
    .replace(/\.[^.]+$/, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const inferLabelHint = (path: string, hint: string | undefined, lang: "zh" | "en"): string | undefined => {
  const source = `${path} ${hint ?? ""}`.toLowerCase();
  const mappings: Array<[string, string]> = lang === "zh"
    ? [
        ["data_inventory", "数据清单"],
        ["entity_inventory", "实体清单"],
        ["supporting_material", "补充证明材料"],
        ["privacy_policy", "隐私政策"],
        ["rights_sop", "消费者权利SOP"],
        ["data_map", "数据映射材料"],
        ["vendor_list", "供应商清单"],
        ["scc_contract", "标准合同文本"],
        ["certification_material", "认证申请材料"],
        ["internal_policy", "内部制度文件"],
        ["supporting_evidence", "支撑证据材料"],
        ["data_flow_diagram", "数据流转图"],
        ["security_policy", "安全制度文件"],
        ["transfer_agreement", "传输协议文本"],
        ["country_law_analysis", "目的国法律分析"],
        ["technical_control_doc", "技术控制说明"],
        ["bcr", "BCR材料"],
        ["dpia", "DPIA材料"],
        ["tia", "TIA材料"],
        ["uploaded_files", "上传附件"],
      ]
    : [
        ["data_inventory", "Data Inventory"],
        ["entity_inventory", "Entity Inventory"],
        ["supporting_material", "Supporting Material"],
        ["privacy_policy", "Privacy Policy"],
        ["rights_sop", "Consumer Rights SOP"],
        ["data_map", "Data Mapping Material"],
        ["vendor_list", "Vendor List"],
        ["scc_contract", "SCC Contract"],
        ["certification_material", "Certification Material"],
        ["internal_policy", "Internal Policy"],
        ["supporting_evidence", "Supporting Evidence"],
        ["data_flow_diagram", "Data Flow Diagram"],
        ["security_policy", "Security Policy"],
        ["transfer_agreement", "Transfer Agreement"],
        ["country_law_analysis", "Country Law Analysis"],
        ["technical_control_doc", "Technical Control Note"],
        ["bcr", "BCR Material"],
        ["dpia", "DPIA Material"],
        ["tia", "TIA Material"],
        ["uploaded_files", "Uploaded Attachment"],
      ];

  const matched = mappings.find(([keyword]) => source.includes(keyword));
  return matched?.[1];
};

const buildDisplayNameFromPath = (path: string, labelHint: string | undefined, lang: "zh" | "en"): string => {
  const extension = getFileExtension(path);
  const fileName = toFileName(path);
  const fallback = prettifyStem(fileName) || fileName;
  const semantic = labelHint ?? inferLabelHint(path, undefined, lang) ?? fallback;
  return extension ? `${semantic}.${extension}` : semantic;
};

const parseTime = (value: string | undefined): number | null => {
  if (!value) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const buildFormEntryName = (index: number, lang: "zh" | "en"): string =>
  lang === "zh" ? `基础信息表单（第${index + 1}次）` : `Intake Form (${index + 1})`;

const buildOutputDisplayName = (artifact: OutputArtifact, lang: "zh" | "en"): string => {
  const lower = toFileName(artifact.path).toLowerCase();
  const ext = getFileExtension(artifact.path).toUpperCase();
  const suffix = ext ? (lang === "zh" ? `（${ext}）` : ` (${ext})`) : "";

  if (lower.includes("citation_map")) return lang === "zh" ? "引用映射" : "Citation Map";
  if (lower.includes("final_brief")) return lang === "zh" ? "执行简报" : "Execution Brief";
  if (artifact.kind.toLowerCase() === "html") return lang === "zh" ? "报告预览页" : "Report Preview";
  if (artifact.kind.toLowerCase() === "pdf") return lang === "zh" ? "报告 PDF 版" : "Report PDF";
  if (artifact.kind.toLowerCase() === "docx" || artifact.kind.toLowerCase() === "annotated_docx") {
    return lang === "zh" ? "报告 Word 版" : "Report Word";
  }
  if (artifact.kind.toLowerCase() === "markdown" || artifact.kind.toLowerCase() === "md") {
    return lang === "zh" ? "报告 Markdown 版" : "Report Markdown";
  }
  if (artifact.kind.toLowerCase() === "report") {
    return lang === "zh" ? `审查报告${suffix}` : `Review Report${suffix}`;
  }
  return buildDisplayNameFromPath(artifact.path, undefined, lang);
};

function collectInputResources(
  value: unknown,
  bag: Map<string, InputResourceCandidate>,
  lang: "zh" | "en",
  keyHint?: string,
) {
  if (typeof value === "string") {
    if (looksLikeFilePath(value)) {
      const existing = bag.get(value);
      bag.set(value, {
        path: value,
        labelHint: existing?.labelHint ?? inferLabelHint(value, keyHint, lang),
      });
    }
    return;
  }

  if (Array.isArray(value)) {
    value.forEach((item) => collectInputResources(item, bag, lang, keyHint));
    return;
  }

  if (!isRecord(value)) return;

  const maybePath =
    typeof value.storage_uri === "string"
      ? value.storage_uri
      : typeof value.path === "string"
        ? value.path
        : typeof value.file_path === "string"
          ? value.file_path
          : null;

  if (maybePath && looksLikeFilePath(maybePath)) {
    const roleHint =
      typeof value.file_role === "string"
        ? value.file_role
        : typeof value.file_name === "string"
          ? value.file_name
          : keyHint;
    const existing = bag.get(maybePath);
    bag.set(maybePath, {
      path: maybePath,
      labelHint: existing?.labelHint ?? inferLabelHint(maybePath, roleHint, lang),
    });
  }

  Object.entries(value).forEach(([key, nested]) => {
    collectInputResources(nested, bag, lang, key);
  });
}

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

    const runLabelById = new Map<string, string>();
    runsWithTime.forEach((item, index) => {
      runLabelById.set(item.runId, `${lang === "zh" ? "第" : "Run "}${index + 1}${lang === "zh" ? "次" : ""}`);
    });

    const assignRunLabel = (artifact: OutputArtifact): string => {
      const artifactTime = parseTime(artifact.createdAt);
      if (artifactTime === null || runsWithTime.length === 0) {
        return lang === "zh" ? "未知" : "Unknown";
      }
      for (let index = 0; index < runsWithTime.length; index += 1) {
        const lowerBound = runsWithTime[index].time;
        const upperBound = index === 0 ? Number.POSITIVE_INFINITY : runsWithTime[index - 1].time;
        if (artifactTime >= lowerBound && artifactTime < upperBound) {
          return runLabelById.get(runsWithTime[index].runId) ?? (lang === "zh" ? "未知" : "Unknown");
        }
      }
      return lang === "zh" ? "未知" : "Unknown";
    };

    const usedNames = new Map<string, number>();
    return uniqueOutputFiles.map((artifact) => {
      const runLabel = lang === "zh" ? `${assignRunLabel(artifact)}生成结果` : `${assignRunLabel(artifact)} Results`;
      const baseName = buildOutputDisplayName(artifact, lang);
      const key = `${runLabel}/${baseName}`;
      const count = (usedNames.get(key) ?? 0) + 1;
      usedNames.set(key, count);
      const fileName = count === 1 ? baseName : `${baseName} (${count})`;
      return {
        virtualPath: `${runLabel}/${fileName}`,
        artifact,
      };
    });
  }, [lang, outputFiles, relatedRuns]);

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
        name: pickUniqueName(buildFormEntryName(index, lang)),
        kind: "form",
        payload: run.request,
        createdAt: run.startedAt
      });

      const bag = new Map<string, InputResourceCandidate>();
      collectInputResources(run.request, bag, lang);
      Array.from(bag.values())
        .filter((item) => !outputFiles.some((file) => file.path === item.path))
        .forEach((item) => {
          if (seenPaths.has(item.path)) return;
          seenPaths.add(item.path);
          entries.push({
            id: `input-file-${item.path}`,
            name: pickUniqueName(buildDisplayNameFromPath(item.path, item.labelHint, lang)),
            kind: "file",
            sourcePath: item.path,
            createdAt: run.startedAt
          });
        });
    });

    return entries;
  }, [lang, outputFiles, relatedRuns]);

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
                <FolderInputIcon width="14" height="14" />
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
                    {inputEntries.map((entry) => {
                      const isActive = selectedInputId === entry.id;
                      return (
                        <li key={entry.id}>
                          <button
                            type="button"
                            className={`ide-tree-row ide-tree-row-file ${isActive ? "active" : ""}`}
                            style={{ ["--tree-depth" as string]: 1 }}
                            onClick={() => {
                              setSelectedInputId(entry.id);
                              if (entry.kind === "form") {
                                onOpenResource({
                                  kind: "input-form",
                                  entry: {
                                    id: entry.id,
                                    name: entry.name,
                                    payload: entry.payload,
                                    createdAt: entry.createdAt
                                  }
                                });
                                return;
                              }
                              if (entry.sourcePath) {
                                onOpenResource({
                                  kind: "input-file",
                                  entry: {
                                    id: entry.id,
                                    name: entry.name,
                                    sourcePath: entry.sourcePath,
                                    createdAt: entry.createdAt
                                  }
                                });
                              }
                            }}
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
      </div>
    </aside>
  );
}
