import type { ModuleKey, TaskSpace } from "../lib/domain";
import { apiFetch } from "./client";

export type CopilotMessagePayload = {
  role: "user" | "assistant";
  content: string;
};

export type CopilotContextPayload = {
  current_step?: string;
  blocker?: string;
  runs_count: number;
  issues_count: number;
  evidence_count: number;
  artifact_count: number;
  top_issues: string[];
  latest_artifacts: string[];
  trace_summary?: string;
  trace_stage?: string;
  trace_status?: "idle" | "running" | "completed" | "failed";
  trace_highlights?: string[];
};

export type TokenUsagePayload = {
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  usage_source?: string;
};

export type CopilotChatRequestPayload = {
  prompt: string;
  action?: string;
  task_id?: string | null;
  task_space: {
    id: string;
    name: string;
    jurisdiction: TaskSpace["jurisdiction"];
    module: ModuleKey;
    mode: TaskSpace["mode"];
    workspace_style: TaskSpace["workspaceStyle"];
  };
  context: CopilotContextPayload;
  messages: CopilotMessagePayload[];
};

export type CopilotChatResponsePayload = {
  reply: string;
  model: string;
  enabled: boolean;
  fallback: boolean;
  usage: TokenUsagePayload;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const errorMessage = (data: unknown): string => {
  if (!isRecord(data)) {
    return "Request failed";
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => {
        if (isRecord(item) && typeof item.msg === "string") return item.msg;
        return JSON.stringify(item);
      })
      .join("; ");
  }

  return "Request failed";
};

export async function requestCopilotChat(
  payload: CopilotChatRequestPayload
): Promise<CopilotChatResponsePayload> {
  const response = await apiFetch("/api/v1/copilot/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const data: unknown = await response.json();
  if (!response.ok) {
    throw new Error(errorMessage(data));
  }

  return data as CopilotChatResponsePayload;
}
