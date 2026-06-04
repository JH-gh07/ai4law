import { getAuthHeaders } from "./auth/auth-service";

export type MyTaskItem = {
  id: string;
  source: string;
  status: string;
  created_at: string;
  updated_at: string;
  module?: string | null;
};

export type MyReportItem = {
  id: string;
  owner_type: string;
  owner_id: string;
  artifact_type: string;
  file_path: string;
  created_at: string;
  preview?: Record<string, unknown>;
};

export type RecoveredModuleRunItem = {
  id: string;
  task_space_id: string;
  module: string;
  run_mode: "sync" | "async";
  started_at: string;
  finished_at?: string | null;
  success: boolean;
  request?: Record<string, unknown>;
  response?: Record<string, unknown> | null;
  error?: string | null;
  async_task_id?: string | null;
  async_state?: string | null;
};

export type RecoveredWorkspaceItem = {
  task_id: string;
  module: string;
  status: string;
  created_at: string;
  updated_at: string;
  run?: RecoveredModuleRunItem | null;
  artifacts: MyReportItem[];
};

export type WorkspaceStatePayload = {
  task_spaces: Record<string, unknown>[];
  module_runs: Record<string, unknown>[];
  artifacts: Record<string, unknown>[];
  evidence_hits: Record<string, unknown>[];
  issues: Record<string, unknown>[];
};

export async function fetchMyTasks(): Promise<MyTaskItem[]> {
  const response = await fetch("/api/v1/me/tasks", { headers: { ...getAuthHeaders() } });
  if (!response.ok) return [];
  const data = (await response.json()) as { items?: MyTaskItem[] };
  return Array.isArray(data.items) ? data.items : [];
}

export async function fetchMyReports(): Promise<MyReportItem[]> {
  const response = await fetch("/api/v1/me/reports", { headers: { ...getAuthHeaders() } });
  if (!response.ok) return [];
  const data = (await response.json()) as { items?: MyReportItem[] };
  return Array.isArray(data.items) ? data.items : [];
}

export async function fetchWorkspaceRecovery(): Promise<RecoveredWorkspaceItem[]> {
  const response = await fetch("/api/v1/me/workspace-recovery", { headers: { ...getAuthHeaders() } });
  if (!response.ok) return [];
  const data = (await response.json()) as { items?: RecoveredWorkspaceItem[] };
  return Array.isArray(data.items) ? data.items : [];
}

export async function fetchWorkspaceState(): Promise<WorkspaceStatePayload | null> {
  const response = await fetch("/api/v1/workspace-state", { headers: { ...getAuthHeaders() } });
  if (!response.ok) return null;
  const data = (await response.json()) as { state?: WorkspaceStatePayload };
  return data.state ?? null;
}

export async function saveWorkspaceState(payload: WorkspaceStatePayload): Promise<void> {
  await fetch("/api/v1/workspace-state", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });
}
