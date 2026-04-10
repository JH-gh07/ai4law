import { Suspense, lazy, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { TopNav } from "./components/common/TopNav";
import { CreateWorkspaceModal } from "./components/modals/CreateWorkspaceModal";
import { ModeSelectModal } from "./components/modals/ModeSelectModal";
import { QuickStartModal } from "./components/modals/QuickStartModal";
import { OnboardingOverlay } from "./components/onboarding/OnboardingOverlay";
import type { Jurisdiction, LaunchMode } from "./lib/domain";
import { AppStoreProvider, useAppStore } from "./lib/app-store";
import { LanguageProvider } from "./lib/language";
import { findTaskTemplate, getDefaultTaskTemplate } from "./lib/task-templates";
import { DocsPlaceholderPage } from "./pages/DocsPlaceholderPage";
import { EvidenceCenterPage } from "./pages/EvidenceCenterPage";
import { HomePage } from "./pages/HomePage";
import { JurisdictionHubPage } from "./pages/JurisdictionHubPage";
import { ReportCenterPage } from "./pages/ReportCenterPage";
import { TaskSpacesPage } from "./pages/TaskSpacesPage";
import { WorkspacePage } from "./pages/WorkspacePage";

const SuperDesign002Page = lazy(() => import("./pages/SuperDesign002Page").then((mod) => ({ default: mod.SuperDesign002Page })));

function AppShell() {
  const QUICK_START_DISMISSED_KEY = "ai4law_quick_start_dismissed_v1";
  const navigate = useNavigate();
  const location = useLocation();
  const { state, dispatch } = useAppStore();
  const isWorkspaceRoute = location.pathname.startsWith("/workspace");

  const [modeModalOpen, setModeModalOpen] = useState(false);
  const [selectedMode, setSelectedMode] = useState<LaunchMode | null>(null);
  const [quickStartOpen, setQuickStartOpen] = useState<boolean>(
    () => globalThis.localStorage?.getItem(QUICK_START_DISMISSED_KEY) !== "1"
  );

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
    const taskTemplate = findTaskTemplate(params.taskTemplateId) ?? getDefaultTaskTemplate(params.jurisdiction);

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
        updatedAt: now
      }
    });

    dispatch({ type: "set_onboarding", payload: { active: true, completed: false, stepIndex: 0 } });
    setSelectedMode(null);
    setModeModalOpen(false);
    navigate(`/workspace/${id}`);
  };

  const onboardingActive = state.onboarding.active;

  return (
    <div className="app-root">
      <TopNav
        onStart={startFlow}
        onReplayGuide={() => dispatch({ type: "set_onboarding", payload: { active: true, stepIndex: 0 } })}
      />

      <main className={`app-main ${isWorkspaceRoute ? "workspace-main" : ""}`}>
        <Routes>
          <Route path="/" element={<HomePage onStart={startFlow} />} />
          <Route path="/jurisdictions/:code" element={<JurisdictionHubPage onStart={startFlow} />} />
          <Route path="/tasks" element={<TaskSpacesPage onStart={startFlow} onQuickCreate={createTask} />} />
          <Route path="/workspace" element={<WorkspacePage />} />
          <Route path="/workspace/:taskId" element={<WorkspacePage />} />
          <Route path="/reports" element={<ReportCenterPage />} />
          <Route path="/evidence" element={<EvidenceCenterPage />} />
          <Route path="/docs" element={<DocsPlaceholderPage />} />
          <Route
            path="/superdesign/002"
            element={
              <Suspense fallback={<section className="page-shell">Loading SuperDesign component...</section>}>
                <SuperDesign002Page />
              </Suspense>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
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
            dispatch({ type: "set_onboarding", payload: { active: true, stepIndex: 0 } });
          }}
        />
      ) : null}

      <OnboardingOverlay
        active={onboardingActive}
        onClose={() => dispatch({ type: "set_onboarding", payload: { active: false, completed: true } })}
      />
    </div>
  );
}

export default function App() {
  return (
    <LanguageProvider>
      <AppStoreProvider>
        <BrowserRouter>
          <AppShell />
        </BrowserRouter>
      </AppStoreProvider>
    </LanguageProvider>
  );
}
