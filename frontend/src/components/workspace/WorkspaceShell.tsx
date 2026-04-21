import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "../../lib/app-store";
import type { ModuleRun, OutputArtifact, TaskSpace, WorkflowStepKey } from "../../lib/domain";
import { fetchArtifactPreview, type ArtifactPreview } from "../../lib/artifact-preview";
import { getAuthHeaders } from "../../lib/auth/auth-service";
import { useLang } from "../../lib/language";
import {
  findTaskTemplate,
  getTaskTemplateInputHint,
  getTaskTemplateOutputHint,
  getTaskTemplateTitle
} from "../../lib/task-templates";
import { deriveWorkflowSteps } from "../../lib/workflow";
import { extractArtifacts, extractConsistencyIssues, extractEvidenceHits, extractInsight } from "../../lib/workspace";
import { AssistantPanel } from "./AssistantPanel";
import { ResourcePanel, type ResourceOpenTarget } from "./ResourcePanel";
import { StageSplitView } from "./StageSplitView";
import { WorkspacePromptModal } from "../common/WorkspacePromptModal";
import type { RunOutput } from "./ModuleRunPanel";
import { ChevronToggleIcon, DownloadIcon, EditIcon, HomeIcon } from "../common/AppIcons";

type WorkspaceShellProps = {
  taskSpace: TaskSpace;
};

const LEFT_PANEL_MIN = 220;
const LEFT_PANEL_MAX = 520;
const RIGHT_PANEL_MIN = 260;
const RIGHT_PANEL_MAX = 560;
const CENTER_PANEL_MIN = 360;
const RESIZER_WIDTH = 10;
const PREFERRED_ARTIFACT_ORDER = ["html", "report", "markdown", "md", "docx", "annotated_docx", "pdf"];

type WorkspaceTopTabId = "details" | "canvas" | "docs" | "terminal" | "report";
type WorkspaceTopTab = {
  id: WorkspaceTopTabId;
  key: "workspaceTabDetails" | "workspaceTabCanvas" | "workspaceTabDocs" | "workspaceTabTerminal" | "workspaceTabReport";
  closable: boolean;
};
type ResponseChapter = {
  title: string;
  content: string;
};

type ReportPreviewSection = {
  title: string;
  content: string;
};

type OpenedResource =
  | { kind: "output"; name: string; path: string; fileType: string }
  | { kind: "input-file"; name: string; path: string; fileType: string }
  | { kind: "input-form"; name: string; payload: unknown };

const WORKSPACE_TABS: WorkspaceTopTab[] = [
  { id: "details", key: "workspaceTabDetails", closable: false },
  { id: "canvas", key: "workspaceTabCanvas", closable: true },
  { id: "docs", key: "workspaceTabDocs", closable: true },
  { id: "terminal", key: "workspaceTabTerminal", closable: true },
  { id: "report", key: "workspaceTabReport", closable: true }
];

const clamp = (value: number, min: number, max: number): number => Math.min(max, Math.max(min, value));

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const readString = (value: unknown): string | undefined => (typeof value === "string" ? value : undefined);
const toFileName = (value: string): string => {
  const normalized = value.replace(/\\/g, "/");
  const chunks = normalized.split("/");
  return chunks[chunks.length - 1] || value;
};

const getArtifactExtension = (value: string): string => {
  const fileName = toFileName(value).toLowerCase();
  const dotIndex = fileName.lastIndexOf(".");
  return dotIndex === -1 ? "" : fileName.slice(dotIndex + 1);
};

const getArtifactBaseName = (value: string): string => {
  const fileName = toFileName(value).toLowerCase();
  const dotIndex = fileName.lastIndexOf(".");
  return dotIndex === -1 ? fileName : fileName.slice(0, dotIndex);
};

const readFileType = (pathOrName: string): string => {
  const ext = getArtifactExtension(pathOrName);
  return ext ? ext.toUpperCase() : "FILE";
};

const isHtmlArtifact = (artifact: OutputArtifact): boolean =>
  artifact.kind.toLowerCase() === "html" || getArtifactExtension(artifact.path) === "html";

const isPdfArtifact = (artifact: OutputArtifact): boolean =>
  artifact.kind.toLowerCase() === "pdf" || getArtifactExtension(artifact.path) === "pdf";

const getArtifactPriority = (artifact: OutputArtifact): number => {
  const index = PREFERRED_ARTIFACT_ORDER.indexOf(artifact.kind.toLowerCase());
  return index === -1 ? PREFERRED_ARTIFACT_ORDER.length + 1 : index;
};

const readResponseChapters = (response: unknown): ResponseChapter[] => {
  if (!isRecord(response) || !Array.isArray(response.chapters)) return [];
  return response.chapters
    .filter(isRecord)
    .map((item) => ({
      title: readString(item.title) ?? "Untitled",
      content: readString(item.content) ?? ""
    }))
    .filter((item) => item.content.trim().length > 0);
};

const readStringList = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];

const normalizeMarkdownForRender = (value: string): string => {
  const normalized = value.replace(/\r\n?/g, "\n");
  return normalized
    .replace(/^(#{1,6})([^\s#])/gm, "$1 $2")
    .replace(/^(\d+)\)\s+/gm, "$1. ")
    .replace(/^\s*•\s+/gm, "- ")
    .trim();
};

const buildFallbackPreviewSections = (response: unknown, lang: "zh" | "en"): ReportPreviewSection[] => {
  if (!isRecord(response)) return [];

  const result = isRecord(response.result) ? response.result : {};
  const sections: ReportPreviewSection[] = [];
  const pushSection = (title: string, lines: string[]) => {
    const cleaned = lines.map((item) => item.trim()).filter((item) => item.length > 0);
    if (cleaned.length === 0) return;
    sections.push({ title, content: cleaned.join("\n") });
  };

  const summary = readString(result.summary);
  if (summary) {
    sections.push({
      title: lang === "zh" ? "执行摘要" : "Executive Summary",
      content: summary
    });
  }

  const hitRules = readStringList(result.hit_rules);
  pushSection(
    lang === "zh" ? "命中规则与判断依据" : "Applied Rules and Basis",
    hitRules
  );

  const citations = Array.isArray(result.citations)
    ? result.citations
        .filter(isRecord)
        .map((item) => [readString(item.source), readString(item.article), readString(item.note)].filter(Boolean).join(" | "))
        .filter((item): item is string => item.trim().length > 0)
    : [];
  pushSection(
    lang === "zh" ? "引用法规与条文" : "Citations",
    citations
  );

  const nextActions = readStringList(result.next_actions);
  pushSection(
    lang === "zh" ? "建议下一步" : "Recommended Next Steps",
    nextActions.map((item, index) => `${index + 1}. ${item}`)
  );

  const consistencyIssues = readStringList(response.consistency_issues);
  pushSection(
    lang === "zh" ? "一致性提示" : "Consistency Notes",
    consistencyIssues
  );

  return sections;
};

export function WorkspaceShell({ taskSpace }: WorkspaceShellProps) {
  const { t, lang } = useLang();
  const { state, dispatch } = useAppStore();
  const navigate = useNavigate();
  const gridRef = useRef<HTMLDivElement | null>(null);
  const [isResizing, setIsResizing] = useState(false);
  const [renameDraft, setRenameDraft] = useState(taskSpace.name);
  const [renameModalOpen, setRenameModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<WorkspaceTopTabId>("details");
  const [openTabs, setOpenTabs] = useState<WorkspaceTopTabId[]>(["details", "report"]);
  const [selectedArtifactPath, setSelectedArtifactPath] = useState<string | null>(null);
  const [artifactPreview, setArtifactPreview] = useState<ArtifactPreview | null>(null);
  const [artifactPreviewLoading, setArtifactPreviewLoading] = useState(false);
  const [artifactPreviewError, setArtifactPreviewError] = useState<string | null>(null);
  const [artifactPdfObjectUrl, setArtifactPdfObjectUrl] = useState<string | null>(null);
  const [artifactDownloadBusy, setArtifactDownloadBusy] = useState(false);
  const [openedResource, setOpenedResource] = useState<OpenedResource | null>(null);
  const [openedResourcePreview, setOpenedResourcePreview] = useState<ArtifactPreview | null>(null);
  const [openedResourceLoading, setOpenedResourceLoading] = useState(false);
  const [openedResourceError, setOpenedResourceError] = useState<string | null>(null);
  const [openedResourcePdfObjectUrl, setOpenedResourcePdfObjectUrl] = useState<string | null>(null);
  const [openedResourceDownloadBusy, setOpenedResourceDownloadBusy] = useState(false);
  const taskRuns = useMemo(
    () => state.moduleRuns.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.moduleRuns, taskSpace.id]
  );
  const taskIssues = useMemo(
    () => state.issues.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.issues, taskSpace.id]
  );
  const taskEvidence = useMemo(
    () => state.evidenceHits.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.evidenceHits, taskSpace.id]
  );
  const taskArtifacts = useMemo(
    () => state.artifacts.filter((item) => item.taskSpaceId === taskSpace.id),
    [state.artifacts, taskSpace.id]
  );

  const latestRun = useMemo<ModuleRun | null>(() => {
    return taskRuns[0] ?? null;
  }, [taskRuns]);
  const taskTemplate = useMemo(() => findTaskTemplate(taskSpace.taskTemplateId), [taskSpace.taskTemplateId]);
  const workflowSteps = useMemo(
    () => deriveWorkflowSteps(taskSpace, latestRun, state.artifacts, state.evidenceHits, state.issues),
    [latestRun, state.artifacts, state.evidenceHits, state.issues, taskSpace]
  );
  const reportArtifacts = useMemo(() => taskArtifacts, [taskArtifacts]);
  const sortedReportArtifacts = useMemo(
    () => [...reportArtifacts].sort((a, b) => getArtifactPriority(a) - getArtifactPriority(b)),
    [reportArtifacts]
  );
  const displayReportArtifacts = useMemo(() => {
    const htmlArtifacts = sortedReportArtifacts.filter(isHtmlArtifact);
    return htmlArtifacts.length > 0 ? htmlArtifacts : sortedReportArtifacts;
  }, [sortedReportArtifacts]);
  const selectedArtifact = useMemo(
    () => sortedReportArtifacts.find((artifact) => artifact.path === selectedArtifactPath) ?? null,
    [selectedArtifactPath, sortedReportArtifacts]
  );
  const selectedHtmlPdfArtifact = useMemo(() => {
    if (!selectedArtifact || !isHtmlArtifact(selectedArtifact)) return null;
    const selectedBaseName = getArtifactBaseName(selectedArtifact.path);
    const sameBatchPdf = sortedReportArtifacts.find((artifact) => isPdfArtifact(artifact) && getArtifactBaseName(artifact.path) === selectedBaseName);
    if (sameBatchPdf) return sameBatchPdf;
    return sortedReportArtifacts.find(isPdfArtifact) ?? null;
  }, [selectedArtifact, sortedReportArtifacts]);
  const responseInsight = useMemo(() => extractInsight(latestRun?.response), [latestRun?.response]);
  const responseChapters = useMemo(() => readResponseChapters(latestRun?.response), [latestRun?.response]);
  const reportPreviewSections = useMemo<ReportPreviewSection[]>(() => {
    if (responseChapters.length > 0) {
      return responseChapters.map((chapter) => ({ title: chapter.title, content: chapter.content }));
    }
    return buildFallbackPreviewSections(latestRun?.response, lang);
  }, [lang, latestRun?.response, responseChapters]);
  const terminalLines = useMemo(() => {
    const lines: string[] = [];
    lines.push(`[workspace] ${taskSpace.name} (${taskSpace.id})`);
    lines.push(`[module] ${taskSpace.module.toUpperCase()} · ${taskSpace.jurisdiction} · ${taskSpace.mode.toUpperCase()}`);
    lines.push(`[time] ${new Date(taskSpace.updatedAt).toLocaleString()}`);
    lines.push("");

    if (taskRuns.length === 0) {
      lines.push("[info] No module run yet. Start from Details tab.");
    } else {
      taskRuns.slice(0, 10).forEach((run) => {
        const at = run.finishedAt ?? run.startedAt;
        lines.push(
          `[run] ${new Date(at).toLocaleString()} ${run.module.toUpperCase()} ${run.success ? "SUCCESS" : "FAILED"}`
        );
        if (run.error) lines.push(`       error: ${run.error}`);
      });
    }

    if (taskIssues.length > 0) {
      lines.push("");
      lines.push(`[issue] total=${taskIssues.length}`);
      taskIssues.slice(0, 6).forEach((item) => lines.push(`  - [${item.severity}] ${item.message}`));
    }
    if (taskEvidence.length > 0) {
      lines.push("");
      lines.push(`[evidence] total=${taskEvidence.length}`);
      taskEvidence.slice(0, 6).forEach((item) => lines.push(`  - ${item.title}`));
    }
    if (taskArtifacts.length > 0) {
      lines.push("");
      lines.push(`[artifact] total=${taskArtifacts.length}`);
      taskArtifacts.slice(0, 8).forEach((item) => lines.push(`  - ${item.kind}: ${toFileName(item.path)}`));
    }

    return lines.join("\n");
  }, [taskArtifacts, taskEvidence, taskIssues, taskRuns, taskSpace.id, taskSpace.jurisdiction, taskSpace.mode, taskSpace.module, taskSpace.name, taskSpace.updatedAt]);
  const closedTabs = useMemo(
    () => WORKSPACE_TABS.filter((item) => !openTabs.includes(item.id)),
    [openTabs]
  );
  const stepLabelMap: Record<WorkflowStepKey, string> = {
    input_validation: t("workflowInputValidation"),
    execution: t("workflowExecution"),
    evidence_binding: t("workflowEvidence"),
    consistency_check: t("workflowConsistency"),
    report_export: t("workflowExport")
  };
  const statusLabelMap = {
    pending: t("workflowPending"),
    running: t("workflowRunning"),
    blocked: t("workflowBlocked"),
    done: t("workflowDone")
  } as const;

  const panelClass = useMemo(() => {
    let cls = "workspace-grid ";
    cls += state.panelState.leftOpen ? "left-open " : "left-hide ";
    cls += state.panelState.rightOpen ? "right-open" : "right-hide";
    if (isResizing) cls += " is-resizing";
    return cls;
  }, [isResizing, state.panelState.leftOpen, state.panelState.rightOpen]);

  const gridTemplateColumns = useMemo(() => {
    if (state.panelState.leftOpen && state.panelState.rightOpen) {
      return `${state.panelState.leftWidth}px ${RESIZER_WIDTH}px minmax(0, 1fr) ${RESIZER_WIDTH}px ${state.panelState.rightWidth}px`;
    }
    if (state.panelState.leftOpen) {
      return `${state.panelState.leftWidth}px ${RESIZER_WIDTH}px minmax(0, 1fr)`;
    }
    if (state.panelState.rightOpen) {
      return `minmax(0, 1fr) ${RESIZER_WIDTH}px ${state.panelState.rightWidth}px`;
    }
    return "minmax(0, 1fr)";
  }, [
    state.panelState.leftOpen,
    state.panelState.leftWidth,
    state.panelState.rightOpen,
    state.panelState.rightWidth
  ]);

  useEffect(() => {
    setActiveTab("details");
    setOpenTabs(["details", "report"]);
    setRenameDraft(taskSpace.name);
    setRenameModalOpen(false);
    setSelectedArtifactPath(null);
    setArtifactPreview(null);
    setArtifactPreviewError(null);
    setOpenedResource(null);
    setOpenedResourcePreview(null);
    setOpenedResourceError(null);
  }, [taskSpace.id]);

  useEffect(() => {
    if (displayReportArtifacts.length === 0) {
      setSelectedArtifactPath(null);
      return;
    }
    setSelectedArtifactPath((current) => {
      if (current && displayReportArtifacts.some((artifact) => artifact.path === current)) {
        return current;
      }
      return displayReportArtifacts[0]?.path ?? null;
    });
  }, [displayReportArtifacts]);

  useEffect(() => {
    if (!selectedArtifactPath) {
      setArtifactPreview(null);
      setArtifactPreviewError(null);
      return;
    }

    let cancelled = false;
    setArtifactPreviewLoading(true);
    setArtifactPreviewError(null);
    fetchArtifactPreview(selectedArtifactPath)
      .then((preview) => {
        if (cancelled) return;
        setArtifactPreview(preview);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setArtifactPreview(null);
        setArtifactPreviewError(error instanceof Error ? error.message : "Failed to load artifact preview");
      })
      .finally(() => {
        if (cancelled) return;
        setArtifactPreviewLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedArtifactPath]);

  useEffect(() => {
    if (!artifactPreview || artifactPreview.render_mode !== "pdf") {
      setArtifactPdfObjectUrl((current) => {
        if (current) URL.revokeObjectURL(current);
        return null;
      });
      return;
    }

    const previewPath = artifactPreview.path || selectedArtifactPath;
    if (!previewPath) return;

    let cancelled = false;
    let createdObjectUrl: string | null = null;
    fetch(`/api/v1/artifacts/file?path=${encodeURIComponent(previewPath)}`, {
      headers: { ...getAuthHeaders() }
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load PDF (${response.status})`);
        }
        const blob = await response.blob();
        return URL.createObjectURL(blob);
      })
      .then((nextObjectUrl) => {
        if (cancelled) {
          URL.revokeObjectURL(nextObjectUrl);
          return;
        }
        createdObjectUrl = nextObjectUrl;
        setArtifactPdfObjectUrl((current) => {
          if (current) URL.revokeObjectURL(current);
          return nextObjectUrl;
        });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setArtifactPdfObjectUrl((current) => {
          if (current) URL.revokeObjectURL(current);
          return null;
        });
        setArtifactPreviewError(
          error instanceof Error ? error.message : "Failed to load PDF preview"
        );
      });

    return () => {
      cancelled = true;
      if (createdObjectUrl) URL.revokeObjectURL(createdObjectUrl);
    };
  }, [artifactPreview, selectedArtifactPath]);

  useEffect(() => {
    if (!openedResource || openedResource.kind === "input-form") {
      setOpenedResourcePreview(null);
      setOpenedResourceError(null);
      return;
    }

    let cancelled = false;
    setOpenedResourceLoading(true);
    setOpenedResourceError(null);
    fetchArtifactPreview(openedResource.path)
      .then((preview) => {
        if (cancelled) return;
        setOpenedResourcePreview(preview);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setOpenedResourcePreview(null);
        setOpenedResourceError(error instanceof Error ? error.message : "Failed to load resource preview");
      })
      .finally(() => {
        if (cancelled) return;
        setOpenedResourceLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [openedResource]);

  useEffect(() => {
    if (!openedResourcePreview || openedResourcePreview.render_mode !== "pdf") {
      setOpenedResourcePdfObjectUrl((current) => {
        if (current) URL.revokeObjectURL(current);
        return null;
      });
      return;
    }

    const previewPath = openedResourcePreview.path;
    if (!previewPath) return;

    let cancelled = false;
    let createdObjectUrl: string | null = null;
    fetch(`/api/v1/artifacts/file?path=${encodeURIComponent(previewPath)}`, {
      headers: { ...getAuthHeaders() }
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load PDF (${response.status})`);
        }
        const blob = await response.blob();
        return URL.createObjectURL(blob);
      })
      .then((nextObjectUrl) => {
        if (cancelled) {
          URL.revokeObjectURL(nextObjectUrl);
          return;
        }
        createdObjectUrl = nextObjectUrl;
        setOpenedResourcePdfObjectUrl((current) => {
          if (current) URL.revokeObjectURL(current);
          return nextObjectUrl;
        });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setOpenedResourcePdfObjectUrl((current) => {
          if (current) URL.revokeObjectURL(current);
          return null;
        });
        setOpenedResourceError(
          error instanceof Error ? error.message : "Failed to load PDF preview"
        );
      });

    return () => {
      cancelled = true;
      if (createdObjectUrl) URL.revokeObjectURL(createdObjectUrl);
    };
  }, [openedResourcePreview]);

  const downloadArtifact = async (path: string) => {
    setArtifactDownloadBusy(true);
    try {
      const response = await fetch(`/api/v1/artifacts/download?path=${encodeURIComponent(path)}`, {
        headers: { ...getAuthHeaders() }
      });
      if (!response.ok) {
        throw new Error(`Download failed (${response.status})`);
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = toFileName(path);
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(objectUrl);
    } catch (error: unknown) {
      setArtifactPreviewError(error instanceof Error ? error.message : "Download failed");
    } finally {
      setArtifactDownloadBusy(false);
    }
  };

  const downloadOpenedResource = async (path: string) => {
    setOpenedResourceDownloadBusy(true);
    try {
      await downloadArtifact(path);
    } finally {
      setOpenedResourceDownloadBusy(false);
    }
  };

  const openArtifactByBlob = async (path: string) => {
    try {
      const response = await fetch(`/api/v1/artifacts/file?path=${encodeURIComponent(path)}`, {
        headers: { ...getAuthHeaders() }
      });
      if (!response.ok) {
        throw new Error(`Open failed (${response.status})`);
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      window.open(objectUrl, "_blank", "noopener,noreferrer");
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    } catch (error: unknown) {
      setArtifactPreviewError(error instanceof Error ? error.message : "Failed to open file");
    }
  };

  const openTab = (tabId: WorkspaceTopTabId) => {
    setOpenTabs((prev) => (prev.includes(tabId) ? prev : [...prev, tabId]));
    setActiveTab(tabId);
  };

  const closeTab = (tabId: WorkspaceTopTabId) => {
    if (tabId === "details") return;
    setOpenTabs((prev) => {
      if (!prev.includes(tabId)) return prev;
      const idx = prev.indexOf(tabId);
      const next = prev.filter((item) => item !== tabId);
      setActiveTab((current) => {
        if (current !== tabId) return current;
        const fallback = next[idx] ?? next[idx - 1] ?? "details";
        return fallback;
      });
      return next;
    });
  };

  const startResize = (side: "left" | "right", startX: number) => {
    const gridWidth = gridRef.current?.getBoundingClientRect().width ?? 0;
    if (!gridWidth) return;

    setIsResizing(true);
    const startLeftWidth = state.panelState.leftWidth;
    const startRightWidth = state.panelState.rightWidth;

    const maxLeftByCenter =
      gridWidth
      - (state.panelState.rightOpen ? state.panelState.rightWidth : 0)
      - CENTER_PANEL_MIN
      - (state.panelState.rightOpen ? RESIZER_WIDTH * 2 : RESIZER_WIDTH);
    const maxRightByCenter =
      gridWidth
      - (state.panelState.leftOpen ? state.panelState.leftWidth : 0)
      - CENTER_PANEL_MIN
      - (state.panelState.leftOpen ? RESIZER_WIDTH * 2 : RESIZER_WIDTH);

    const handlePointerMove = (event: PointerEvent) => {
      const delta = event.clientX - startX;
      if (side === "left") {
        const maxWidth = clamp(maxLeftByCenter, LEFT_PANEL_MIN, LEFT_PANEL_MAX);
        const nextLeftWidth = clamp(startLeftWidth + delta, LEFT_PANEL_MIN, maxWidth);
        dispatch({ type: "set_panel_state", payload: { leftWidth: nextLeftWidth } });
      } else {
        const maxWidth = clamp(maxRightByCenter, RIGHT_PANEL_MIN, RIGHT_PANEL_MAX);
        const nextRightWidth = clamp(startRightWidth - delta, RIGHT_PANEL_MIN, maxWidth);
        dispatch({ type: "set_panel_state", payload: { rightWidth: nextRightWidth } });
      }
    };

    const stopPointerMove = () => {
      setIsResizing(false);
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopPointerMove);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopPointerMove);
  };

  const onLeftResizerPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    startResize("left", event.clientX);
  };

  const onRightResizerPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    startResize("right", event.clientX);
  };

  const onRunDone = (output: RunOutput) => {
    const now = new Date().toISOString();
    const run: ModuleRun = {
      id: `${output.module}-${now}`,
      taskSpaceId: taskSpace.id,
      module: output.module,
      runMode: output.runMode,
      startedAt: now,
      finishedAt: now,
      success: output.success,
      request: output.request,
      response: output.response,
      error: output.error,
      asyncTaskId: output.asyncTaskId,
      asyncState: output.asyncState
    };

    dispatch({ type: "append_run", payload: run });
    dispatch({ type: "touch_task_space", payload: { id: taskSpace.id, updatedAt: now } });

    if (output.response) {
      dispatch({ type: "append_artifacts", payload: extractArtifacts(taskSpace.id, output.module, output.response) });
      dispatch({ type: "append_evidence", payload: extractEvidenceHits(taskSpace.id, output.module, output.response) });
      dispatch({ type: "append_issues", payload: extractConsistencyIssues(taskSpace.id, output.module, output.response) });
      setOpenTabs((prev) => (prev.includes("report") ? prev : [...prev, "report"]));
      setActiveTab("report");
    }
  };

  const handleSelectArtifact = (artifact: OutputArtifact) => {
    setSelectedArtifactPath(artifact.path);
    setOpenTabs((prev) => (prev.includes("report") ? prev : [...prev, "report"]));
    setActiveTab("report");
  };

  const handleOpenResource = (target: ResourceOpenTarget) => {
    if (target.kind === "output") {
      const path = target.artifact.path;
      setSelectedArtifactPath(path);
      setOpenedResource({
        kind: "output",
        name: toFileName(path),
        path,
        fileType: readFileType(path)
      });
    } else if (target.kind === "input-file") {
      const path = target.entry.sourcePath;
      setOpenedResource({
        kind: "input-file",
        name: target.entry.name || toFileName(path),
        path,
        fileType: readFileType(path)
      });
    } else {
      setOpenedResource({
        kind: "input-form",
        name: target.entry.name,
        payload: target.entry.payload
      });
    }
    setOpenTabs((prev) => (prev.includes("report") ? prev : [...prev, "report"]));
    setActiveTab("report");
  };

  const renameTask = () => {
    setRenameDraft(taskSpace.name);
    setRenameModalOpen(true);
  };

  const submitRenameTask = () => {
    const nextName = renameDraft.trim();
    if (!nextName || nextName === taskSpace.name) {
      setRenameModalOpen(false);
      return;
    }
    dispatch({
      type: "rename_task_space",
      payload: {
        id: taskSpace.id,
        name: nextName,
        updatedAt: new Date().toISOString()
      }
    });
    setRenameModalOpen(false);
  };

  const renderTabSurface = () => {
    if (activeTab === "details") {
      return <StageSplitView taskSpace={taskSpace} onRunDone={onRunDone} latestRun={latestRun} />;
    }

    if (activeTab === "canvas") {
      return (
        <section className="workspace-tab-page workspace-tab-canvas">
          <header className="workspace-tab-head">
            <h3>{t("workspaceTabCanvasTitle")}</h3>
            <p>{t("workspaceTabCanvasDesc")}</p>
          </header>
          <section className="workspace-canvas-flow">
            {workflowSteps.map((step) => (
              <article key={step.key} className={`workspace-canvas-step step-${step.status}`}>
                <strong>{stepLabelMap[step.key]}</strong>
                <span>{statusLabelMap[step.status]}</span>
                <p>{step.reason ?? t("workflowNoReason")}</p>
              </article>
            ))}
          </section>
          <section className="workspace-canvas-metrics">
            <article className="workspace-canvas-metric">
              <span>{t("tasksStatRuns")}</span>
              <strong>{taskRuns.length}</strong>
            </article>
            <article className="workspace-canvas-metric">
              <span>{t("copilotContextIssues")}</span>
              <strong>{taskIssues.length}</strong>
            </article>
            <article className="workspace-canvas-metric">
              <span>{t("copilotContextEvidence")}</span>
              <strong>{taskEvidence.length}</strong>
            </article>
            <article className="workspace-canvas-metric">
              <span>{t("copilotContextArtifacts")}</span>
              <strong>{taskArtifacts.length}</strong>
            </article>
          </section>
        </section>
      );
    }

    if (activeTab === "docs") {
      return (
        <section className="workspace-tab-page workspace-tab-docs">
          <header className="workspace-tab-head">
            <h3>{t("workspaceTabDocsTitle")}</h3>
            <p>{t("workspaceTabDocsDesc")}</p>
          </header>
          <section className="workspace-doc-brief">
            <article>
              <strong>{t("taskTemplateLabel")}</strong>
              <p>{taskTemplate ? getTaskTemplateTitle(taskTemplate, lang) : taskSpace.module.toUpperCase()}</p>
            </article>
            <article>
              <strong>{t("moduleInputLabel")}</strong>
              <p>{taskTemplate ? getTaskTemplateInputHint(taskTemplate, lang) : "-"}</p>
            </article>
            <article>
              <strong>{t("moduleOutputLabel")}</strong>
              <p>{taskTemplate ? getTaskTemplateOutputHint(taskTemplate, lang) : "-"}</p>
            </article>
            <article>
              <strong>{t("workspaceUpdatedAt")}</strong>
              <p>{new Date(taskSpace.updatedAt).toLocaleString()}</p>
            </article>
          </section>
        </section>
      );
    }

    if (activeTab === "terminal") {
      return (
        <section className="workspace-tab-page workspace-tab-terminal">
          <header className="workspace-tab-head">
            <h3>{t("workspaceTabTerminalTitle")}</h3>
            <p>{t("workspaceTabTerminalDesc")}</p>
          </header>
          <section className="workspace-terminal-shell">
            <pre className="workspace-terminal-log">{terminalLines}</pre>
          </section>
        </section>
      );
    }

    return (
      <section className="workspace-tab-page workspace-tab-report">
        <header className="workspace-tab-head">
          <h3>{t("workspaceTabReportTitle")}</h3>
          <p>{reportPreviewSections.length > 0 ? (lang === "zh" ? "报告生成完成后会自动进入这里，优先展示可直接阅读的正文内容，再附带导出文件。" : "Generated reports land here automatically with readable in-page content before exported files.") : t("workspaceTabReportDesc")}</p>
        </header>
        {openedResource ? (
          <section className="workspace-resource-viewer">
            <div className="workspace-resource-viewer-head">
              <div>
                <span>{lang === "zh" ? "资源目录 · 已打开文件" : "Resource Explorer · Opened File"}</span>
                <strong>{openedResource.name}</strong>
              </div>
              <div className="workspace-resource-viewer-actions">
                {openedResource.kind !== "input-form" ? (
                  <>
                    <em>{openedResource.fileType}</em>
                    <button
                      type="button"
                      className="workspace-report-download-icon"
                      onClick={() => void downloadOpenedResource(openedResource.path)}
                      aria-label={lang === "zh" ? "下载文件" : "Download file"}
                      title={lang === "zh" ? "下载文件" : "Download file"}
                      disabled={openedResourceDownloadBusy}
                    >
                      <DownloadIcon width="16" height="16" />
                    </button>
                  </>
                ) : (
                  <em>JSON</em>
                )}
                <button
                  type="button"
                  className="pill-btn"
                  onClick={() => {
                    setOpenedResource(null);
                    setOpenedResourcePreview(null);
                    setOpenedResourceError(null);
                  }}
                >
                  {lang === "zh" ? "关闭查看" : "Close"}
                </button>
              </div>
            </div>
            {openedResource.kind === "input-form" ? (
              <article className="workspace-report-chapter workspace-report-preview-block">
                <strong>{lang === "zh" ? "表单提交详情" : "Form Submission Detail"}</strong>
                <pre className="workspace-resource-json">
                  {JSON.stringify(openedResource.payload ?? {}, null, 2)}
                </pre>
              </article>
            ) : (
              <>
                {openedResourceLoading ? (
                  <div className="workspace-report-preview-state">{lang === "zh" ? "正在加载文件预览..." : "Loading file preview..."}</div>
                ) : null}
                {openedResourceError ? (
                  <div className="workspace-report-preview-state workspace-report-preview-error">{openedResourceError}</div>
                ) : null}
                {openedResourcePreview ? (
                  openedResourcePreview.render_mode === "html" ? (
                    <div className="workspace-report-html-frame">
                      <iframe
                        title={openedResourcePreview.file_name}
                        srcDoc={openedResourcePreview.content}
                        sandbox="allow-same-origin"
                      />
                    </div>
                  ) : openedResourcePreview.render_mode === "pdf" && openedResourcePdfObjectUrl ? (
                    <div className="workspace-report-pdf-frame">
                      <iframe title={openedResourcePreview.file_name} src={openedResourcePdfObjectUrl} />
                    </div>
                  ) : openedResourcePreview.render_mode === "text" ? (
                    <article className="workspace-report-chapter workspace-report-preview-block">
                      <strong>{lang === "zh" ? "文件内容预览" : "File Content Preview"}</strong>
                      <div className="workspace-report-richtext">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {normalizeMarkdownForRender(openedResourcePreview.content)}
                        </ReactMarkdown>
                      </div>
                    </article>
                  ) : (
                    <div className="workspace-report-preview-state">
                      <button
                        type="button"
                        className="workspace-report-link-button"
                        onClick={() => void openArtifactByBlob(openedResource.path)}
                      >
                        {lang === "zh"
                          ? "当前文件暂不支持内嵌预览，点击打开原文件"
                          : "Inline preview is not available for this file. Open the source file."}
                      </button>
                    </div>
                  )
                ) : null}
              </>
            )}
          </section>
        ) : null}
        <section className="workspace-report-kpi-row">
          <article>
            <span>{t("reportIssueCount")}</span>
            <strong>{taskIssues.length}</strong>
          </article>
          <article>
            <span>{t("reportEvidenceCount")}</span>
            <strong>{taskEvidence.length}</strong>
          </article>
          <article>
            <span>{t("reportDownloadHint")}</span>
            <strong>{displayReportArtifacts.length}</strong>
          </article>
          <article>
            <span>{t("fieldRisk")}</span>
            <strong>{responseInsight.riskLevel ?? t("workflowPending")}</strong>
          </article>
        </section>
        {artifactPreviewLoading ? (
          <div className="workspace-report-preview-state">{lang === "zh" ? "正在加载文档预览..." : "Loading artifact preview..."}</div>
        ) : null}
        {artifactPreviewError ? (
          <div className="workspace-report-preview-state workspace-report-preview-error">{artifactPreviewError}</div>
        ) : null}
        {artifactPreview ? (
          <section className="workspace-report-selected">
            <div className="workspace-report-selected-head">
              <div>
                <span>{lang === "zh" ? "当前预览" : "Now Previewing"}</span>
                <strong>{artifactPreview.file_name}</strong>
              </div>
              <div className="workspace-report-selected-actions">
                {artifactPreview.render_mode === "html" ? (
                  selectedHtmlPdfArtifact ? (
                    <button
                      type="button"
                      className="workspace-report-download-icon"
                      onClick={() => void downloadArtifact(selectedHtmlPdfArtifact.path)}
                      aria-label={lang === "zh" ? "下载 PDF" : "Download PDF"}
                      title={lang === "zh" ? "下载 PDF" : "Download PDF"}
                      disabled={artifactDownloadBusy}
                    >
                      <DownloadIcon width="16" height="16" />
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="workspace-report-download-icon disabled"
                      aria-label={lang === "zh" ? "暂无 PDF 可下载" : "No PDF available"}
                      title={lang === "zh" ? "暂无 PDF 可下载" : "No PDF available"}
                      disabled
                    >
                      <DownloadIcon width="16" height="16" />
                    </button>
                  )
                ) : null}
              </div>
            </div>
            {artifactPreview.render_mode === "html" ? (
              <div className="workspace-report-html-frame">
                <iframe
                  title={artifactPreview.file_name}
                  srcDoc={artifactPreview.content}
                  sandbox="allow-same-origin"
                />
              </div>
            ) : artifactPreview.render_mode === "pdf" && artifactPdfObjectUrl ? (
              <div className="workspace-report-pdf-frame">
                <iframe title={artifactPreview.file_name} src={artifactPdfObjectUrl} />
              </div>
            ) : artifactPreview.render_mode === "text" ? (
              <article className="workspace-report-chapter workspace-report-preview-block">
                <strong>{lang === "zh" ? "文档正文预览" : "Document Preview"}</strong>
                <div className="workspace-report-richtext">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {normalizeMarkdownForRender(artifactPreview.content)}
                  </ReactMarkdown>
                </div>
              </article>
            ) : artifactPreview.file_url ? (
              <div className="workspace-report-preview-state">
                <button
                  type="button"
                  className="workspace-report-link-button"
                  onClick={() => void openArtifactByBlob(artifactPreview.path)}
                >
                  {lang === "zh" ? "当前文件暂不支持内嵌预览，点击打开原文件" : "Inline preview is not available for this file. Open the source file."}
                </button>
              </div>
            ) : null}
          </section>
        ) : null}
        {reportPreviewSections.length > 0 ? (
          <section className="workspace-report-chapters">
            {reportPreviewSections.map((section, index) => (
              <article key={`${section.title}-${index}`} className="workspace-report-chapter workspace-report-preview-block">
                <strong>{section.title}</strong>
                <div className="workspace-report-richtext">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {normalizeMarkdownForRender(section.content)}
                  </ReactMarkdown>
                </div>
              </article>
            ))}
          </section>
        ) : (
          <p className="resource-empty">{t("reportNoData")}</p>
        )}
        {displayReportArtifacts.length > 0 ? (
          <section className="workspace-report-list">
            {displayReportArtifacts.map((artifact) => (
              <button
                type="button"
                key={artifact.id}
                className={`workspace-report-item workspace-report-item-button ${selectedArtifactPath === artifact.path ? "active" : ""}`}
                onClick={() => handleSelectArtifact(artifact)}
              >
                <span>{toFileName(artifact.path)}</span>
              </button>
            ))}
          </section>
        ) : null}
      </section>
    );
  };

  return (
    <section className={`workspace-shell workspace-style-${taskSpace.workspaceStyle}`}>
      <header className="workspace-header workspace-header-compact">
        <div className="workspace-browser-left">
          <button
            type="button"
            className="workspace-browser-icon-btn workspace-browser-home-btn"
            onClick={() => navigate("/tasks")}
            aria-label={t("navHome")}
            title={t("navHome")}
          >
            <HomeIcon width="16" height="16" />
          </button>
          <span className="workspace-browser-sep">/</span>
          <span className="workspace-browser-task">{taskSpace.name}</span>
        </div>

        <div className="workspace-browser-tabs">
          {openTabs.map((tabId) => {
            const tab = WORKSPACE_TABS.find((item) => item.id === tabId);
            if (!tab) return null;
            return (
              <button
                key={tab.id}
                className={`workspace-browser-tab ${activeTab === tab.id ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span>{t(tab.key)}</span>
                {tab.closable ? (
                  <span
                    className="workspace-browser-tab-close"
                    role="button"
                    aria-label={`close-${tab.id}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      closeTab(tab.id);
                    }}
                  >
                    ×
                  </span>
                ) : null}
              </button>
            );
          })}
          {closedTabs.map((tab) => (
            <button
              key={`add-${tab.id}`}
              className="workspace-browser-tab-add"
              onClick={() => openTab(tab.id)}
            >
              + {t(tab.key)}
            </button>
          ))}
        </div>

        <div className="workspace-browser-actions">
          <div className="workspace-header-actions">
            <button
              type="button"
              className="workspace-browser-icon-btn workspace-browser-rename-btn"
              onClick={renameTask}
              aria-label={t("tasksRenameAction")}
              title={t("tasksRenameAction")}
            >
              <EditIcon width="16" height="16" />
            </button>
          </div>
        </div>
      </header>

      <div className={panelClass} ref={gridRef} style={{ gridTemplateColumns }}>
        {state.panelState.leftOpen ? (
          <ResourcePanel
            taskSpace={taskSpace}
            onToggleCollapse={() => dispatch({ type: "set_panel_state", payload: { leftOpen: false } })}
            onOpenResource={handleOpenResource}
            selectedOutputPath={selectedArtifactPath}
          />
        ) : null}
        {state.panelState.leftOpen ? (
          <div
            className="workspace-resizer workspace-resizer-left"
            role="separator"
            aria-orientation="vertical"
            onPointerDown={onLeftResizerPointerDown}
          />
        ) : null}

        <main className="pane center-pane">
          {!state.panelState.leftOpen ? (
            <button
              className="workspace-floating-toggle workspace-floating-toggle-left"
              onClick={() => dispatch({ type: "set_panel_state", payload: { leftOpen: true } })}
              aria-label="expand-left-sidebar"
            >
              <ChevronToggleIcon direction="right" width="16" height="16" />
            </button>
          ) : null}
          {!state.panelState.rightOpen ? (
            <button
              className="workspace-floating-toggle workspace-floating-toggle-right"
              onClick={() => dispatch({ type: "set_panel_state", payload: { rightOpen: true } })}
              aria-label="expand-right-sidebar"
            >
              <ChevronToggleIcon direction="left" width="16" height="16" />
            </button>
          ) : null}
          {renderTabSurface()}
        </main>

        {state.panelState.rightOpen ? (
          <div
            className="workspace-resizer workspace-resizer-right"
            role="separator"
            aria-orientation="vertical"
            onPointerDown={onRightResizerPointerDown}
          />
        ) : null}
        {state.panelState.rightOpen ? (
          <AssistantPanel
            taskSpace={taskSpace}
            onToggleCollapse={() => dispatch({ type: "set_panel_state", payload: { rightOpen: false } })}
          />
        ) : null}
      </div>

      <WorkspacePromptModal
        open={renameModalOpen}
        title={t("tasksRenameTitle")}
        description={t("tasksRenameDesc")}
        valueLabel={t("tasksNameField")}
        value={renameDraft}
        valuePlaceholder={t("tasksRenamePrompt")}
        onValueChange={setRenameDraft}
        confirmText={t("tasksRenameConfirmAction")}
        cancelText={t("cancelBtn")}
        confirmDisabled={renameDraft.trim().length === 0}
        onCancel={() => setRenameModalOpen(false)}
        onConfirm={submitRenameTask}
      />
    </section>
  );
}
