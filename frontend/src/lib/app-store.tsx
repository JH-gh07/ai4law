import { createContext, useContext, useEffect, useReducer, useRef, type Dispatch, type ReactNode } from "react";
import type {
  ConsistencyIssue,
  EvidenceHit,
  Jurisdiction,
  ModuleRun,
  OnboardingState,
  OutputArtifact,
  PanelState,
  TaskSpace
} from "./domain";
import { useAuth } from "./auth/AuthContext";
import { fetchMyReports, fetchMyTasks, fetchWorkspaceState, saveWorkspaceState, type MyReportItem, type MyTaskItem } from "./me-api";
import { findTaskTemplate, getDefaultTaskTemplate } from "./task-templates";

const STORAGE_KEY = "ai4law_app_state_v1";

type AppState = {
  taskSpaces: TaskSpace[];
  moduleRuns: ModuleRun[];
  artifacts: OutputArtifact[];
  evidenceHits: EvidenceHit[];
  issues: ConsistencyIssue[];
  panelState: PanelState;
  onboarding: OnboardingState;
};

type Action =
  | { type: "create_task_space"; payload: TaskSpace }
  | { type: "rename_task_space"; payload: { id: string; name: string; updatedAt: string } }
  | { type: "delete_task_space"; payload: { id: string } }
  | { type: "touch_task_space"; payload: { id: string; updatedAt: string } }
  | { type: "append_run"; payload: ModuleRun }
  | { type: "append_artifacts"; payload: OutputArtifact[] }
  | { type: "append_evidence"; payload: EvidenceHit[] }
  | { type: "append_issues"; payload: ConsistencyIssue[] }
  | {
      type: "hydrate_remote_state";
      payload: {
        taskSpaces: TaskSpace[];
        moduleRuns: ModuleRun[];
        artifacts: OutputArtifact[];
        evidenceHits: EvidenceHit[];
        issues: ConsistencyIssue[];
      };
    }
  | { type: "set_panel_state"; payload: Partial<PanelState> }
  | { type: "set_onboarding"; payload: Partial<OnboardingState> }
  | { type: "reset_all" };

const initialState: AppState = {
  taskSpaces: [],
  moduleRuns: [],
  artifacts: [],
  evidenceHits: [],
  issues: [],
  panelState: {
    leftOpen: true,
    rightOpen: true,
    leftWidth: 260,
    rightWidth: 300,
    topOpen: true,
    focusMode: "split",
    stageLayout: "split",
    primaryPlugin: "run",
    secondaryPlugin: "preview"
  },
  onboarding: {
    active: false,
    stepIndex: 0,
    completed: false,
    source: undefined,
    targetTaskId: undefined
  }
};

const AppStoreContext = createContext<{
  state: AppState;
  dispatch: Dispatch<Action>;
} | null>(null);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const clamp = (value: number, min: number, max: number): number => Math.min(max, Math.max(min, value));

const MODULE_TEMPLATE_ID_MAP: Record<string, string> = {
  diagnosis: "cn_diagnosis",
  assessment: "cn_assessment",
  pipia: "cn_pipia",
  review: "cn_document_review",
  scc: "eu_scc",
  bcr: "eu_bcr",
  dpia: "eu_dpia",
  tia: "eu_tia",
  cn_flow: "us_14117",
  cpra: "us_cpra",
  us_14117: "us_14117",
};

const MODULE_JURISDICTION_MAP: Record<string, Jurisdiction> = {
  diagnosis: "CN",
  assessment: "CN",
  pipia: "CN",
  review: "CN",
  scc: "EU",
  bcr: "EU",
  dpia: "EU",
  tia: "EU",
  cn_flow: "US",
  cpra: "US",
  us_14117: "US",
};

function normalizePanelState(raw: unknown): PanelState {
  if (!isRecord(raw)) {
    return initialState.panelState;
  }

  const merged: PanelState = { ...initialState.panelState, ...(raw as Partial<PanelState>) };
  return {
    ...merged,
    leftWidth: clamp(
      typeof merged.leftWidth === "number" ? merged.leftWidth : initialState.panelState.leftWidth,
      220,
      520
    ),
    rightWidth: clamp(
      typeof merged.rightWidth === "number" ? merged.rightWidth : initialState.panelState.rightWidth,
      260,
      560
    )
  };
}

function normalizeTaskSpace(raw: unknown): TaskSpace | null {
  if (!isRecord(raw)) return null;
  if (typeof raw.id !== "string") return null;
  if (typeof raw.name !== "string") return null;
  if (raw.mode !== "rapid" && raw.mode !== "draft" && raw.mode !== "matrix") return null;
  if (raw.jurisdiction !== "CN" && raw.jurisdiction !== "EU" && raw.jurisdiction !== "US") return null;
  if (typeof raw.createdAt !== "string" || typeof raw.updatedAt !== "string") return null;

  const rawTemplateId = typeof raw.taskTemplateId === "string" ? raw.taskTemplateId : "";
  const template = findTaskTemplate(rawTemplateId) ?? getDefaultTaskTemplate(raw.jurisdiction);

  return {
    id: raw.id,
    name: raw.name,
    mode: raw.mode,
    jurisdiction: raw.jurisdiction,
    taskTemplateId: template.id,
    module: template.module,
    workspaceStyle: template.workspaceStyle,
    createdAt: raw.createdAt,
    updatedAt: raw.updatedAt
  };
}

const ensureTaskSpaces = (value: unknown): TaskSpace[] => {
  if (!Array.isArray(value)) return [];
  const normalized = value
    .map((item) => normalizeTaskSpace(item))
    .filter((item): item is TaskSpace => !!item);
  return normalized;
};

function normalizeModuleRun(raw: unknown): ModuleRun | null {
  if (!isRecord(raw)) return null;
  if (typeof raw.id !== "string") return null;
  if (typeof raw.taskSpaceId !== "string") return null;
  if (typeof raw.module !== "string") return null;
  if (raw.runMode !== "sync" && raw.runMode !== "async") return null;
  if (typeof raw.startedAt !== "string") return null;
  return {
    id: raw.id,
    taskSpaceId: raw.taskSpaceId,
    module: raw.module as ModuleRun["module"],
    runMode: raw.runMode,
    startedAt: raw.startedAt,
    finishedAt: typeof raw.finishedAt === "string" ? raw.finishedAt : undefined,
    success: !!raw.success,
    request: raw.request,
    response: raw.response,
    error: typeof raw.error === "string" ? raw.error : undefined,
    asyncTaskId: typeof raw.asyncTaskId === "string" ? raw.asyncTaskId : undefined,
    asyncState: typeof raw.asyncState === "string" ? raw.asyncState : undefined
  };
}

function normalizeOutputArtifact(raw: unknown): OutputArtifact | null {
  if (!isRecord(raw)) return null;
  if (typeof raw.id !== "string") return null;
  if (typeof raw.taskSpaceId !== "string") return null;
  if (typeof raw.module !== "string") return null;
  if (typeof raw.kind !== "string") return null;
  if (typeof raw.path !== "string") return null;
  if (typeof raw.createdAt !== "string") return null;
  return {
    id: raw.id,
    taskSpaceId: raw.taskSpaceId,
    module: raw.module as OutputArtifact["module"],
    kind: raw.kind,
    path: raw.path,
    createdAt: raw.createdAt
  };
}

function normalizeEvidenceHit(raw: unknown): EvidenceHit | null {
  if (!isRecord(raw)) return null;
  if (typeof raw.id !== "string") return null;
  if (typeof raw.taskSpaceId !== "string") return null;
  if (typeof raw.module !== "string") return null;
  if (typeof raw.source !== "string") return null;
  if (typeof raw.title !== "string") return null;
  if (typeof raw.snippet !== "string") return null;
  if (typeof raw.createdAt !== "string") return null;
  return {
    id: raw.id,
    taskSpaceId: raw.taskSpaceId,
    module: raw.module as EvidenceHit["module"],
    source: raw.source,
    title: raw.title,
    snippet: raw.snippet,
    createdAt: raw.createdAt
  };
}

function normalizeIssue(raw: unknown): ConsistencyIssue | null {
  if (!isRecord(raw)) return null;
  if (typeof raw.id !== "string") return null;
  if (typeof raw.taskSpaceId !== "string") return null;
  if (typeof raw.module !== "string") return null;
  if (raw.severity !== "high" && raw.severity !== "medium" && raw.severity !== "low") return null;
  if (typeof raw.message !== "string") return null;
  if (typeof raw.createdAt !== "string") return null;
  return {
    id: raw.id,
    taskSpaceId: raw.taskSpaceId,
    module: raw.module as ConsistencyIssue["module"],
    severity: raw.severity,
    message: raw.message,
    createdAt: raw.createdAt
  };
}

const ensureModuleRuns = (value: unknown): ModuleRun[] =>
  Array.isArray(value) ? value.map(normalizeModuleRun).filter((item): item is ModuleRun => !!item) : [];

function dedupeArtifacts(items: OutputArtifact[]): OutputArtifact[] {
  const seen = new Set<string>();
  const result: OutputArtifact[] = [];
  for (const item of items) {
    const key = `${item.taskSpaceId}::${item.module}::${item.path}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(item);
  }
  return result;
}

const ensureArtifacts = (value: unknown): OutputArtifact[] =>
  Array.isArray(value)
    ? dedupeArtifacts(value.map(normalizeOutputArtifact).filter((item): item is OutputArtifact => !!item))
    : [];

const ensureEvidenceHits = (value: unknown): EvidenceHit[] =>
  Array.isArray(value) ? value.map(normalizeEvidenceHit).filter((item): item is EvidenceHit => !!item) : [];

const ensureIssues = (value: unknown): ConsistencyIssue[] =>
  Array.isArray(value) ? value.map(normalizeIssue).filter((item): item is ConsistencyIssue => !!item) : [];

const hasWorkspaceData = (state: Pick<AppState, "taskSpaces" | "moduleRuns" | "artifacts" | "evidenceHits" | "issues">): boolean =>
  state.taskSpaces.length > 0 ||
  state.moduleRuns.length > 0 ||
  state.artifacts.length > 0 ||
  state.evidenceHits.length > 0 ||
  state.issues.length > 0;

const dedupeById = <T extends { id: string }>(items: T[]): T[] => {
  const seen = new Set<string>();
  const result: T[] = [];
  for (const item of items) {
    if (seen.has(item.id)) continue;
    seen.add(item.id);
    result.push(item);
  }
  return result;
};

const mergeTaskSpaces = (...groups: TaskSpace[][]): TaskSpace[] => {
  const seen = new Set<string>();
  const result: TaskSpace[] = [];
  for (const group of groups) {
    for (const item of group) {
      if (seen.has(item.id)) continue;
      seen.add(item.id);
      result.push(item);
    }
  }
  return result.sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
};

const inferModuleKey = (item: MyTaskItem): string => {
  if (typeof item.module === "string" && item.module.length > 0) {
    return item.module;
  }
  return item.source;
};

const inferJurisdiction = (module: string): Jurisdiction => MODULE_JURISDICTION_MAP[module] ?? "CN";

const resolveTaskTemplate = (module: string, jurisdiction: Jurisdiction) => {
  const templateId = MODULE_TEMPLATE_ID_MAP[module];
  return findTaskTemplate(templateId) ?? getDefaultTaskTemplate(jurisdiction);
};

const buildRecoveredTaskName = (item: MyTaskItem, module: string, jurisdiction: Jurisdiction): string => {
  const template = resolveTaskTemplate(module, jurisdiction);
  const stamp = item.updated_at.slice(0, 10);
  return `${template.title.zh} ${stamp}`;
};

function buildRecoveredWorkspaceState(tasks: MyTaskItem[], reports: MyReportItem[]) {
  const taskSpacesFromTasks = tasks.map((item) => {
    const module = inferModuleKey(item);
    const jurisdiction = inferJurisdiction(module);
    const template = resolveTaskTemplate(module, jurisdiction);
    return {
      id: item.id,
      name: buildRecoveredTaskName(item, module, jurisdiction),
      mode: "rapid" as const,
      jurisdiction,
      taskTemplateId: template.id,
      module: template.module,
      workspaceStyle: template.workspaceStyle,
      createdAt: item.created_at,
      updatedAt: item.updated_at
    };
  });

  const taskSpacesFromReports = reports
    .filter((item) => typeof item.owner_type === "string" && item.owner_type.length > 0)
    .map((item) => {
      const module = item.owner_type;
      const jurisdiction = inferJurisdiction(module);
      const template = resolveTaskTemplate(module, jurisdiction);
      return {
        id: item.owner_id,
        name: `${template.title.zh} ${item.created_at.slice(0, 10)}`,
        mode: "rapid" as const,
        jurisdiction,
        taskTemplateId: template.id,
        module: template.module,
        workspaceStyle: template.workspaceStyle,
        createdAt: item.created_at,
        updatedAt: item.created_at
      };
    });

  const taskSpaces = mergeTaskSpaces(taskSpacesFromTasks, taskSpacesFromReports);

  const taskIds = new Set(taskSpaces.map((item) => item.id));
  const artifacts = dedupeArtifacts(
    reports
      .filter((item) => taskIds.has(item.owner_id) && typeof item.owner_type === "string" && item.owner_type.length > 0)
      .map((item) => ({
        id: item.id,
        taskSpaceId: item.owner_id,
        module: (item.owner_type || "diagnosis") as OutputArtifact["module"],
        kind: item.artifact_type,
        path: item.file_path,
        createdAt: item.created_at
      }))
  );

  return {
    taskSpaces,
    moduleRuns: [] as ModuleRun[],
    artifacts,
    evidenceHits: [] as EvidenceHit[],
    issues: [] as ConsistencyIssue[]
  };
}

function loadState(): AppState {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return initialState;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed)) return initialState;
    return {
      ...initialState,
      ...parsed,
      taskSpaces: ensureTaskSpaces(parsed.taskSpaces),
      moduleRuns: ensureModuleRuns(parsed.moduleRuns),
      artifacts: ensureArtifacts(parsed.artifacts),
      evidenceHits: ensureEvidenceHits(parsed.evidenceHits),
      issues: ensureIssues(parsed.issues),
      panelState: normalizePanelState(parsed.panelState),
      onboarding: { ...initialState.onboarding, ...(isRecord(parsed.onboarding) ? parsed.onboarding : {}) }
    } as AppState;
  } catch {
    return initialState;
  }
}

function persistState(state: AppState) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "create_task_space":
      return { ...state, taskSpaces: [action.payload, ...state.taskSpaces] };
    case "rename_task_space":
      return {
        ...state,
        taskSpaces: state.taskSpaces.map((task) =>
          task.id === action.payload.id
            ? { ...task, name: action.payload.name, updatedAt: action.payload.updatedAt }
            : task
          )
      };
    case "delete_task_space":
      return {
        ...state,
        taskSpaces: state.taskSpaces.filter((task) => task.id !== action.payload.id),
        moduleRuns: state.moduleRuns.filter((run) => run.taskSpaceId !== action.payload.id),
        artifacts: state.artifacts.filter((artifact) => artifact.taskSpaceId !== action.payload.id),
        evidenceHits: state.evidenceHits.filter((hit) => hit.taskSpaceId !== action.payload.id),
        issues: state.issues.filter((issue) => issue.taskSpaceId !== action.payload.id)
      };
    case "touch_task_space":
      return {
        ...state,
        taskSpaces: state.taskSpaces.map((task) =>
          task.id === action.payload.id ? { ...task, updatedAt: action.payload.updatedAt } : task
        )
      };
    case "append_run":
      return { ...state, moduleRuns: [action.payload, ...state.moduleRuns] };
    case "append_artifacts":
      return { ...state, artifacts: dedupeArtifacts([...action.payload, ...state.artifacts]) };
    case "append_evidence":
      return { ...state, evidenceHits: [...action.payload, ...state.evidenceHits] };
    case "append_issues":
      return { ...state, issues: [...action.payload, ...state.issues] };
    case "hydrate_remote_state":
      return {
        ...state,
        taskSpaces: action.payload.taskSpaces,
        moduleRuns: action.payload.moduleRuns,
        artifacts: dedupeArtifacts(action.payload.artifacts),
        evidenceHits: action.payload.evidenceHits,
        issues: action.payload.issues
      };
    case "set_panel_state":
      return { ...state, panelState: { ...state.panelState, ...action.payload } };
    case "set_onboarding":
      return { ...state, onboarding: { ...state.onboarding, ...action.payload } };
    case "reset_all":
      return initialState;
    default:
      return state;
  }
}

export function AppStoreProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, loadState);
  const { isAuthenticated, loading } = useAuth();
  const hydratedRef = useRef(false);
  const savingTimerRef = useRef<number | null>(null);
  const localSnapshotRef = useRef<AppState>(state);

  useEffect(() => {
    localSnapshotRef.current = state;
  }, [state]);

  useEffect(() => {
    persistState(state);
  }, [state]);

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated) {
      hydratedRef.current = false;
      return;
    }

    let cancelled = false;
    Promise.all([fetchWorkspaceState(), fetchMyTasks(), fetchMyReports()]).then(([remote, myTasks, myReports]) => {
      if (cancelled) return;

      const localSnapshot = localSnapshotRef.current;
      const normalizedRemote = remote
        ? {
            taskSpaces: ensureTaskSpaces(remote.task_spaces),
            moduleRuns: ensureModuleRuns(remote.module_runs),
            artifacts: ensureArtifacts(remote.artifacts),
            evidenceHits: ensureEvidenceHits(remote.evidence_hits),
            issues: ensureIssues(remote.issues)
          }
        : {
            taskSpaces: [],
            moduleRuns: [],
            artifacts: [],
            evidenceHits: [],
            issues: []
          };
      const recovered = buildRecoveredWorkspaceState(myTasks, myReports);

      const mergedTaskSpaces = mergeTaskSpaces(
        normalizedRemote.taskSpaces,
        localSnapshot.taskSpaces,
        recovered.taskSpaces
      );
      const mergedModuleRuns = dedupeById([
        ...normalizedRemote.moduleRuns,
        ...localSnapshot.moduleRuns,
        ...recovered.moduleRuns
      ]);
      const mergedArtifacts = dedupeArtifacts([
        ...normalizedRemote.artifacts,
        ...localSnapshot.artifacts,
        ...recovered.artifacts
      ]);
      const mergedEvidenceHits = dedupeById([
        ...normalizedRemote.evidenceHits,
        ...localSnapshot.evidenceHits,
        ...recovered.evidenceHits
      ]);
      const mergedIssues = dedupeById([
        ...normalizedRemote.issues,
        ...localSnapshot.issues,
        ...recovered.issues
      ]);

      const mergedState = {
        taskSpaces: mergedTaskSpaces,
        moduleRuns: mergedModuleRuns,
        artifacts: mergedArtifacts,
        evidenceHits: mergedEvidenceHits,
        issues: mergedIssues
      };

      if (hasWorkspaceData(mergedState)) {
        dispatch({
          type: "hydrate_remote_state",
          payload: mergedState
        });
      }
      hydratedRef.current = true;
    });

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, loading]);

  useEffect(() => {
    if (loading || !isAuthenticated || !hydratedRef.current) return;
    if (savingTimerRef.current) {
      window.clearTimeout(savingTimerRef.current);
    }
    savingTimerRef.current = window.setTimeout(() => {
      void saveWorkspaceState({
        task_spaces: state.taskSpaces as unknown as Record<string, unknown>[],
        module_runs: state.moduleRuns as unknown as Record<string, unknown>[],
        artifacts: state.artifacts as unknown as Record<string, unknown>[],
        evidence_hits: state.evidenceHits as unknown as Record<string, unknown>[],
        issues: state.issues as unknown as Record<string, unknown>[]
      });
    }, 500);

    return () => {
      if (savingTimerRef.current) {
        window.clearTimeout(savingTimerRef.current);
      }
    };
  }, [isAuthenticated, loading, state]);

  return <AppStoreContext.Provider value={{ state, dispatch }}>{children}</AppStoreContext.Provider>;
}

export function useAppStore() {
  const ctx = useContext(AppStoreContext);
  if (!ctx) {
    throw new Error("useAppStore must be used inside AppStoreProvider");
  }
  return ctx;
}
