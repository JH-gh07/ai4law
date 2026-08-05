import { getAuthHeaders } from "./auth";
import { apiFetch } from "./client";

export type TaskEventsResponse<TEvent> = {
  events?: TEvent[];
  latest_seq?: number;
  has_more?: boolean;
};

export type RunManifest = {
  run_id: string;
  module: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  duration_ms?: number;
  observability?: {
    event_count?: number;
    llm_calls?: number;
    tokens?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };
};

export function getTaskEventStreamUrl(taskId: string): string {
  return `/api/v1/events/task/${encodeURIComponent(taskId)}/stream`;
}

export async function fetchTaskEvents<TEvent>(
  taskId: string,
  since: number,
): Promise<TaskEventsResponse<TEvent>> {
  const response = await apiFetch(
    `/api/v1/events/task/${encodeURIComponent(taskId)}/events?since=${since}`,
    { headers: getAuthHeaders() },
  );
  return (await response.json()) as TaskEventsResponse<TEvent>;
}

// ── Stream token (for EventSource which can't carry Authorization header) ────

export type StreamTokenResponse = {
  stream_token: string;
  expires_at: string;
};

export async function fetchStreamToken(taskId: string): Promise<StreamTokenResponse> {
  const response = await apiFetch(
    `/api/v1/events/task/${encodeURIComponent(taskId)}/token`,
    { method: "POST", headers: getAuthHeaders() },
  );
  return (await response.json()) as StreamTokenResponse;
}

export async function fetchTaskManifest(taskId: string): Promise<RunManifest> {
  const response = await apiFetch(
    `/api/v1/events/task/${encodeURIComponent(taskId)}/manifest`,
    { headers: getAuthHeaders() },
  );
  if (!response.ok) throw new Error(`Manifest request failed (${response.status})`);
  return (await response.json()) as RunManifest;
}
