import { lazy, Suspense, useEffect, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { LazyRouteErrorBoundary } from "./components/common/LazyRouteErrorBoundary";
import { TopNav } from "./components/common/TopNav";
import { CreateWorkspaceModal } from "./components/modals/CreateWorkspaceModal";
import { ModeSelectModal } from "./components/modals/ModeSelectModal";
import { QuickStartModal } from "./components/modals/QuickStartModal";
import { OnboardingOverlay } from "./components/onboarding/OnboardingOverlay";
import { AuthProvider } from "./lib/auth/AuthContext";
import type { Jurisdiction, LaunchMode } from "./lib/domain";
import { AppStoreProvider, useAppStore } from "./lib/app-store";
import { LanguageProvider } from "./lib/language";
import { findTaskTemplate, getDefaultTaskTemplate } from "./lib/task-templates";
import { checkBackendHealth } from "./api/modules";
import { HomePage } from "./pages/HomePage";
import { JurisdictionHubPage } from "./pages/JurisdictionHubPage";
import { LoginPage } from "./pages/auth/LoginPage";
import { RegisterPage } from "./pages/auth/RegisterPage";
import { GlobalTaskWatcher } from "./components/workspace/GlobalTaskWatcher";

const DocsPlaceholderPage = lazy(() =>
  import("./pages/DocsPlaceholderPage").then((module) => ({
    default: module.DocsPlaceholderPage,
  })),
);
const EvidenceCenterPage = lazy(() =>
  import("./pages/EvidenceCenterPage").then((module) => ({
    default: module.EvidenceCenterPage,
  })),
);
const LawViewerPage = lazy(() =>
  import("./pages/LawViewerPage").then((module) => ({
    default: module.LawViewerPage,
  })),
);
const ProfilePage = lazy(() =>
  import("./pages/ProfilePage").then((module) => ({
    default: module.ProfilePage,
  })),
);
const ReportCenterPage = lazy(() =>
  import("./pages/ReportCenterPage").then((module) => ({
    default: module.ReportCenterPage,
  })),
);
const SettingsPage = lazy(() =>
  import("./pages/SettingsPage").then((module) => ({
    default: module.SettingsPage,
  })),
);

const TaskSpacesPage = lazy(() =>
  import("./pages/TaskSpacesPage").then((module) => ({
    default: module.TaskSpacesPage,
  })),
);
const WorkspacePage = lazy(() =>
  import("./pages/WorkspacePage").then((module) => ({
    default: module.WorkspacePage,
  })),
);

function PageLoadingFallback() {
  return (
    <div className="page-loading" role="status" aria-live="polite">
      页面加载中…
    </div>
  );
}

function AppShell() {
  const QUICK_START_DISMISSED_KEY = "ai4law_quick_start_dismissed_v1";
  const navigate = useNavigate();
  const location = useLocation();
  const { state, dispatch } = useAppStore();
  const isWorkspaceRoute = location.pathname.startsWith("/workspace");
  const isAuthRoute =
    location.pathname === "/login" || location.pathname === "/register";
  const hideGlobalTopNav = isWorkspaceRoute || isAuthRoute;

  const [modeModalOpen, setModeModalOpen] = useState(false);
  const [selectedMode, setSelectedMode] = useState<LaunchMode | null>(null);
  const [backendHealth, setBackendHealth] = useState<{
    checked: boolean;
    ok: boolean;
    detail?: string;
  }>({ checked: false, ok: true });
  const [quickStartOpen, setQuickStartOpen] = useState<boolean>(
    () => globalThis.localStorage?.getItem(QUICK_START_DISMISSED_KEY) !== "1",
  );

  useEffect(() => {
    let cancelled = false;

    const syncBackendHealth = async () => {
      const health = await checkBackendHealth();
      if (cancelled) return;
      setBackendHealth({
        checked: true,
        ok: health.ok,
        detail: health.detail,
      });
    };

    void syncBackendHealth();
    const timer = globalThis.setInterval(() => {
      void syncBackendHealth();
    }, 30000);

    return () => {
      cancelled = true;
      globalThis.clearInterval(timer);
    };
  }, []);

  const startFlow = () => {
    setModeModalOpen(true);
  };

  const closeQuickStart = (neverRemind = false) => {
    setQuickStartOpen(false);
    if (neverRemind) {
      globalThis.localStorage?.setItem(QUICK_START_DISMISSED_KEY, "1");
    }
  };

  const createTask = (params: {
    mode: LaunchMode;
    name: string;
    jurisdiction: Jurisdiction;
    taskTemplateId: string;
  }) => {
    const id = `task-${Date.now()}`;
    const now = new Date().toISOString();
    const taskTemplate =
      findTaskTemplate(params.taskTemplateId) ??
      getDefaultTaskTemplate(params.jurisdiction);

    dispatch({
      type: "create_task_space",
      payload: {
        id,
        name: params.name,
        mode: params.mode,
        jurisdiction: params.jurisdiction,
        taskTemplateId: taskTemplate.id,
        module: taskTemplate.module,
        workspaceStyle: taskTemplate.workspaceStyle,
        createdAt: now,
        updatedAt: now,
      },
    });
    setSelectedMode(null);
    setModeModalOpen(false);
    navigate(`/workspace/${id}`);
  };

  const onboardingActive = state.onboarding.active;
  const closeOnboarding = () => {
    dispatch({
      type: "set_onboarding",
      payload: {
        active: false,
        completed: true,
        stepIndex: 0,
        source: undefined,
        targetTaskId: undefined,
      },
    });
  };

  return (
    <div className="app-root">
      {backendHealth.checked && !backendHealth.ok ? (
        <div className="backend-health-banner" role="status" aria-live="polite">
          <strong>后端未连通</strong>
          <span>
            当前只能查看与编辑，本轮执行请求可能失败。
            {backendHealth.detail ? ` 诊断信息：${backendHealth.detail}` : ""}
          </span>
        </div>
      ) : null}

      {hideGlobalTopNav ? null : (
        <TopNav
          onStart={startFlow}
          onReplayGuide={() =>
            dispatch({
              type: "set_onboarding",
              payload: {
                active: true,
                completed: false,
                stepIndex: 0,
                source: "replay",
                targetTaskId: undefined,
              },
            })
          }
        />
      )}

      <main
        className={`app-main ${isWorkspaceRoute ? "workspace-main workspace-main-embedded" : ""}`}
      >
        <LazyRouteErrorBoundary>
          <Suspense fallback={<PageLoadingFallback />}>
            <Routes>
            <Route
              path="/"
              element={
                <HomePage onStart={startFlow} onQuickCreate={createTask} />
              }
            />
            <Route
              path="/jurisdictions/:code"
              element={<JurisdictionHubPage onStart={startFlow} />}
            />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
              path="/tasks"
              element={
                <ProtectedRoute>
                  <TaskSpacesPage
                    onStart={startFlow}
                    onQuickCreate={createTask}
                  />
                </ProtectedRoute>
              }
            />
            <Route
              path="/workspace"
              element={
                <ProtectedRoute>
                  <WorkspacePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/workspace/:taskId"
              element={
                <ProtectedRoute>
                  <WorkspacePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports"
              element={
                <ProtectedRoute>
                  <ReportCenterPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/evidence"
              element={
                <ProtectedRoute>
                  <EvidenceCenterPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/knowledge/laws/:sourceId"
              element={
                <ProtectedRoute>
                  <LawViewerPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/docs"
              element={
                <ProtectedRoute>
                  <DocsPlaceholderPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <SettingsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <ProfilePage />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </LazyRouteErrorBoundary>
      </main>

      {modeModalOpen ? (
        <ModeSelectModal
          onClose={() => setModeModalOpen(false)}
          onSelect={(mode) => {
            setSelectedMode(mode);
            setModeModalOpen(false);
          }}
        />
      ) : null}

      {selectedMode ? (
        <CreateWorkspaceModal
          mode={selectedMode}
          onClose={() => setSelectedMode(null)}
          onCreate={(config) => createTask(config)}
        />
      ) : null}

      {quickStartOpen && location.pathname === "/" ? (
        <QuickStartModal
          onClose={() => closeQuickStart(false)}
          onNeverRemind={() => closeQuickStart(true)}
          onStart={() => {
            closeQuickStart(false);
            startFlow();
          }}
          onGuided={() => {
            closeQuickStart(false);
            dispatch({
              type: "set_onboarding",
              payload: {
                active: true,
                completed: false,
                stepIndex: 0,
                source: "replay",
                targetTaskId: undefined,
              },
            });
          }}
        />
      ) : null}

      <OnboardingOverlay
        active={onboardingActive}
        initialStepIndex={state.onboarding.stepIndex}
        targetTaskId={state.onboarding.targetTaskId}
        onClose={closeOnboarding}
      />

      <GlobalTaskWatcher />
    </div>
  );
}

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <AppStoreProvider>
          <BrowserRouter>
            <AppShell />
          </BrowserRouter>
        </AppStoreProvider>
      </AuthProvider>
    </LanguageProvider>
  );
}
