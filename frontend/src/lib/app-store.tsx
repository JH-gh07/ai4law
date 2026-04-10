import { createContext, useContext, useEffect, useReducer, type Dispatch, type ReactNode } from "react";
import type {
  ConsistencyIssue,
  EvidenceHit,
  ModuleRun,
  OnboardingState,
  OutputArtifact,
  PanelState,
  TaskSpace
} from "./domain";

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
  | { type: "touch_task_space"; payload: { id: string; updatedAt: string } }
  | { type: "append_run"; payload: ModuleRun }
  | { type: "append_artifacts"; payload: OutputArtifact[] }
  | { type: "append_evidence"; payload: EvidenceHit[] }
  | { type: "append_issues"; payload: ConsistencyIssue[] }
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
    topOpen: true,
    focusMode: "split",
    stageLayout: "split",
    primaryPlugin: "run",
    secondaryPlugin: "preview"
  },
  onboarding: {
    active: false,
    stepIndex: 0,
    completed: false
  }
};

const AppStoreContext = createContext<{
  state: AppState;
  dispatch: Dispatch<Action>;
} | null>(null);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

function loadState(): AppState {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return initialState;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed)) return initialState;
    return {
      ...initialState,
      ...parsed,
      panelState: { ...initialState.panelState, ...(isRecord(parsed.panelState) ? parsed.panelState : {}) },
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
      return { ...state, artifacts: [...action.payload, ...state.artifacts] };
    case "append_evidence":
      return { ...state, evidenceHits: [...action.payload, ...state.evidenceHits] };
    case "append_issues":
      return { ...state, issues: [...action.payload, ...state.issues] };
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

  useEffect(() => {
    persistState(state);
  }, [state]);

  return <AppStoreContext.Provider value={{ state, dispatch }}>{children}</AppStoreContext.Provider>;
}

export function useAppStore() {
  const ctx = useContext(AppStoreContext);
  if (!ctx) {
    throw new Error("useAppStore must be used inside AppStoreProvider");
  }
  return ctx;
}
