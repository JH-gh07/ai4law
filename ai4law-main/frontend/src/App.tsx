import { useState } from "react";
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
import { SettingsPage } from "./pages/SettingsPage";
import { SuperDesign002Page } from "./pages/SuperDesign002Page";
import { TaskSpacesPage } from "./pages/TaskSpacesPage";
import { WorkspacePage } from "./pages/WorkspacePage";

function AppShell() {
  const QUICK_START_DISMISSED_KEY = "ai4law_quick_start_dismissed_v1";
  const navigate = useNavigate();
  const location = useLocation();
  const { state, dispatch } = useAppStore();
  const isWorkspaceRoute = location.pathname.startsWith("/workspace");
  const hideGlobalTopNav = isWorkspaceRoute;

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

    dispatch({
      type: "set_onboarding",
      payload: {
        active: true,
        completed: false,
        stepIndex: 1,
        source: "task_create",
        targetTaskId: id
      }
    });
    setSelectedMode(null);
    setModeModalOpen(false);
    navigate(`/workspace/${id}`);
  };

  const onboardingActive = state.onboarding.active;
  const closeOnboarding = () => {
    const source = state.onboarding.source;
    const targetTaskId = state.onboarding.targetTaskId;

    dispatch({
      type: "set_onboarding",
      payload: {
        active: false,
        completed: true,
        stepIndex: 0,
        source: undefined,
        targetTaskId: undefined
      }
    });

    if (source === "task_create" && targetTaskId) {
      navigate(`/workspace/${targetTaskId}`, { replace: true });
    }
  };

  return (
    <div className="app-root">
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
                targetTaskId: undefined
              }
            })
          }
        />
      )}

      <main className={`app-main ${isWorkspaceRoute ? "workspace-main workspace-main-embedded" : ""}`}>
        <Routes>
          <Route path="/" element={<HomePage onStart={startFlow} onQuickCreate={createTask} />} />
          <Route path="/jurisdictions/:code" element={<JurisdictionHubPage onStart={startFlow} />} />
          <Route path="/tasks" element={<TaskSpacesPage onStart={startFlow} onQuickCreate={createTask} />} />
          <Route path="/workspace" element={<WorkspacePage />} />
          <Route path="/workspace/:taskId" element={<WorkspacePage />} />
          <Route path="/reports" element={<ReportCenterPage />} />
          <Route path="/evidence" element={<EvidenceCenterPage />} />
          <Route path="/docs" element={<DocsPlaceholderPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/superdesign/002" element={<SuperDesign002Page />} />
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
            dispatch({
              type: "set_onboarding",
              payload: {
                active: true,
                completed: false,
                stepIndex: 0,
                source: "replay",
                targetTaskId: undefined
              }
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
