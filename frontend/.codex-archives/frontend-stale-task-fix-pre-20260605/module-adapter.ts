import { getAuthHeaders } from "./auth/auth-service";
import { buildDemoPayload } from "./demoPayloads";
import type { ModuleKey, RunMode } from "./domain";

export class BackendConnectionError extends Error {
  code: "backend_unreachable" | "backend_http_empty" | "backend_http_error";
  status?: number;
  url?: string;

  constructor(
    message: string,
    options: {
      code: "backend_unreachable" | "backend_http_empty" | "backend_http_error";
      status?: number;
      url?: string;
    }
  ) {
    super(message);
    this.name = "BackendConnectionError";
    this.code = options.code;
    this.status = options.status;
    this.url = options.url;
  }
}

export function getModuleRunErrorCode(error: unknown): string | undefined {
  if (error instanceof BackendConnectionError) {
    return error.code;
  }
  return undefined;
}

export type ModuleDefinition = {
  key: ModuleKey;
  label: string;
  jurisdiction: "CN" | "EU" | "US";
  syncEndpoint: string;
  asyncSubmitEndpoint?: string;
  asyncStatusEndpoint?: (taskId: string) => string;
  asyncRetryEndpoint?: (taskId: string) => string;
  asyncCancelEndpoint?: (taskId: string) => string;
};

export type ModuleRunResponse = {
  response: unknown;
  asyncTaskId?: string;
  asyncState?: string;
  runMode: RunMode;
};

export type ModuleRunProgress = {
  state: string;
  progress?: number;
};

export type UploadedTaskFile = {
  fileId: string;
  fileName: string;
  mime: string;
  size: number;
  path: string;
  uploadedAt: string;
};

const MODULES: ModuleDefinition[] = [
  {
    key: "diagnosis",
    label: "Diagnosis",
    jurisdiction: "CN",
    syncEndpoint: "/api/v1/diagnosis/report"
  },
  {
    key: "assessment",
    label: "Assessment",
    jurisdiction: "CN",
    syncEndpoint: "/api/v1/assessment/generate",
    asyncSubmitEndpoint: "/api/v1/assessment/generate_async",
    asyncStatusEndpoint: (taskId) => `/api/v1/assessment/tasks/${taskId}`,
    asyncRetryEndpoint: (taskId) => `/api/v1/assessment/tasks/${taskId}/retry`
  },
  {
    key: "review",
    label: "Review",
    jurisdiction: "CN",
    syncEndpoint: "/api/v1/review/generate",
    asyncSubmitEndpoint: "/api/v1/review/generate_async",
    asyncStatusEndpoint: (taskId) => `/api/v1/review/tasks/${taskId}`
  },
  {
    key: "scc",
    label: "SCC",
    jurisdiction: "CN",
    syncEndpoint: "/api/v1/scc/generate",
    asyncSubmitEndpoint: "/api/v1/scc/generate_async",
    asyncStatusEndpoint: (taskId) => `/api/v1/scc/tasks/${taskId}`,
    asyncRetryEndpoint: (taskId) => `/api/v1/scc/tasks/${taskId}/retry`
  },
  {
    key: "pipia",
    label: "PIPIA",
    jurisdiction: "CN",
    syncEndpoint: "/api/v1/pipia/generate",
    asyncSubmitEndpoint: "/api/v1/pipia/generate_async",
    asyncStatusEndpoint: (taskId) => `/api/v1/pipia/tasks/${taskId}`,
    asyncRetryEndpoint: (taskId) => `/api/v1/pipia/tasks/${taskId}/retry`
  },
  {
    key: "bcr",
    label: "BCR",
    jurisdiction: "EU",
    syncEndpoint: "/api/v1/bcr/generate",
    asyncSubmitEndpoint: "/api/v1/bcr/generate_async",
    asyncStatusEndpoint: (taskId) => `/api/v1/bcr/tasks/${taskId}`,
    asyncRetryEndpoint: (taskId) => `/api/v1/bcr/tasks/${taskId}/retry`
  },
  {
    key: "dpia",
    label: "DPIA",
    jurisdiction: "EU",
    syncEndpoint: "/api/v1/dpia/generate",
    asyncSubmitEndpoint: "/api/v1/dpia/generate_async",
    asyncStatusEndpoint: (taskId) => `/api/v1/dpia/tasks/${taskId}`,
    asyncRetryEndpoint: (taskId) => `/api/v1/dpia/tasks/${taskId}/retry`
  },
  {
    key: "tia",
    label: "TIA",
    jurisdiction: "EU",
    syncEndpoint: "/api/v1/tia/generate",
    asyncSubmitEndpoint: "/api/v1/tia/generate_async",
    asyncStatusEndpoint: (taskId) => `/api/v1/tia/tasks/${taskId}`,
    asyncRetryEndpoint: (taskId) => `/api/v1/tia/tasks/${taskId}/retry`
  },
  {
    key: "cn_flow",
    label: "CN_FLOW",
    jurisdiction: "US",
    syncEndpoint: "/api/v1/cn-flow/generate",
    asyncSubmitEndpoint: "/api/v1/cn-flow/generate_async",
    asyncStatusEndpoint: (taskId) => `/api/v1/cn-flow/tasks/${taskId}`,
    asyncRetryEndpoint: (taskId) => `/api/v1/cn-flow/tasks/${taskId}/retry`
  },
  {
    key: "us_14117",
    label: "US_14117",
    jurisdiction: "US",
    syncEndpoint: "/api/v1/us_14117/generate",
    asyncSubmitEndpoint: "/api/v1/us_14117/generate_async",
    asyncStatusEndpoint: (taskId) => `/api/v1/us_14117/tasks/${taskId}`,
    asyncRetryEndpoint: (taskId) => `/api/v1/us_14117/tasks/${taskId}/retry`
  },
  {
    key: "eu_scc",
    label: "EU_SCC",
    jurisdiction: "EU",
    syncEndpoint: "/api/v1/eu_scc/generate",
    asyncSubmitEndpoint: "/api/v1/eu_scc/generate_async",
    asyncStatusEndpoint: (taskId) => `/api/v1/eu_scc/tasks/${taskId}`,
    asyncRetryEndpoint: (taskId) => `/api/v1/eu_scc/tasks/${taskId}/retry`
  },
  {
    key: "cpra",
    label: "CPRA",
    jurisdiction: "US",
    syncEndpoint: "/api/v1/cpra/generate",
    asyncSubmitEndpoint: "/api/v1/cpra/generate_async",
    asyncStatusEndpoint: (taskId) => `/api/v1/cpra/tasks/${taskId}`,
    asyncRetryEndpoint: (taskId) => `/api/v1/cpra/tasks/${taskId}/retry`
  }
];

const FINAL_STATES = new Set(["succeeded", "completed", "failed", "cancelled", "canceled"]);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const LANG_KEY = "ai4law_ui_lang";
const uiLang = (): "zh" | "en" => {
  const value = globalThis.localStorage?.getItem(LANG_KEY);
  return value === "zh" ? "zh" : "en";
};

function parseErrorMessage(data: unknown): string {
  if (!isRecord(data)) {
    return "Request failed";
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => {
        if (isRecord(item) && typeof item.msg === "string") {
          return item.msg;
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }

  return "Request failed";
}

async function requestJson(url: string, method: "GET" | "POST", body?: unknown): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
  } catch (error) {
    if (url.startsWith("/api/")) {
      throw new BackendConnectionError(
        uiLang() === "zh"
          ? "无法连接后端服务。请确认前端代理与后端服务均已启动后重试。"
          : "Cannot connect to backend. Please ensure the frontend proxy and backend service are both running.",
        { code: "backend_unreachable", url }
      );
    }
    throw error;
  }

  const rawText = await response.text();
  const hasBody = rawText.trim().length > 0;
  let data: unknown = null;

  if (hasBody) {
    try {
      data = JSON.parse(rawText);
    } catch {
      const hint = response.ok ? "invalid JSON payload" : `HTTP ${response.status}`;
      throw new Error(`${hint} from ${url}: non-JSON or truncated response body`);
    }
  }

  if (!response.ok) {
    if (hasBody) {
      throw new Error(parseErrorMessage(data));
    }
    if (url.startsWith("/api/")) {
      throw new BackendConnectionError(
        uiLang() === "zh"
          ? `后端请求失败（HTTP ${response.status}，空响应）。请检查服务是否可用。`
          : `Backend request failed (HTTP ${response.status}, empty response). Please verify the service is available.`,
        { code: "backend_http_empty", status: response.status, url }
      );
    }
    throw new Error(`HTTP ${response.status} from ${url}: empty response body`);
  }

  if (!hasBody) {
    throw new Error(`Request succeeded but response body is empty: ${url}`);
  }

  return data;
}

export async function checkBackendHealth(): Promise<{ ok: boolean; status: string; detail?: string }> {
  try {
    const response = await fetch("/health", { method: "GET" });
    if (!response.ok) {
      return {
        ok: false,
        status: "error",
        detail: `HTTP ${response.status}`,
      };
    }
    const data = (await response.json()) as { status?: string };
    return {
      ok: (data.status ?? "").toLowerCase() === "ok",
      status: typeof data.status === "string" ? data.status : "unknown",
    };
  } catch (error) {
    return {
      ok: false,
      status: "unreachable",
      detail: error instanceof Error ? error.message : "unknown error",
    };
  }
}

export async function uploadTaskFile(file: File): Promise<UploadedTaskFile> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/v0/files/upload", {
    method: "POST",
    headers: { ...getAuthHeaders() },
    body: formData
  });

  const data: unknown = await response.json();
  if (!response.ok) {
    throw new Error(parseErrorMessage(data));
  }

  if (!isRecord(data) || !isRecord(data.data)) {
    throw new Error("Upload API returned invalid payload");
  }

  const payload = data.data;
  if (
    typeof payload.file_id !== "string" ||
    typeof payload.file_name !== "string" ||
    typeof payload.mime !== "string" ||
    typeof payload.size !== "number" ||
    typeof payload.path !== "string" ||
    typeof payload.uploaded_at !== "string"
  ) {
    throw new Error("Upload API payload missing required fields");
  }

  return {
    fileId: payload.file_id,
    fileName: payload.file_name,
    mime: payload.mime,
    size: payload.size,
    path: payload.path,
    uploadedAt: payload.uploaded_at
  };
}

function parseAsyncTaskId(data: unknown): string {
  if (!isRecord(data) || typeof data.task_id !== "string") {
    throw new Error("Async submit did not return task_id");
  }
  return data.task_id;
}

function parseTaskState(data: unknown): string {
  if (isRecord(data) && typeof data.state === "string") {
    return data.state.toLowerCase();
  }
  if (isRecord(data) && typeof data.status === "string") {
    return data.status.toLowerCase();
  }
  return "unknown";
}

function parseTaskProgress(data: unknown): number | undefined {
  if (isRecord(data) && typeof data.progress === "number" && Number.isFinite(data.progress)) {
    return data.progress;
  }
  return undefined;
}

function parseTaskResult(data: unknown): unknown {
  if (isRecord(data) && "result" in data) {
    return data.result;
  }
  return undefined;
}

export function listModules(): ModuleDefinition[] {
  return MODULES;
}

export function findModule(key: ModuleKey): ModuleDefinition {
  const matched = MODULES.find((item) => item.key === key);
  if (!matched) {
    throw new Error(`Unknown module: ${key}`);
  }
  return matched;
}

export function hasAsync(definition: ModuleDefinition): boolean {
  return !!definition.asyncSubmitEndpoint && !!definition.asyncStatusEndpoint;
}

export function getDefaultPayload(module: ModuleKey): unknown {
  return buildDemoPayload(module);
}

export type RunEvent = {
  event_id: string;
  task_id: string;
  seq: number;
  event_type: "status" | "thought" | "tool_start" | "tool_result" | "intermediate" | "warning" | "final" | "final_brief";
  timestamp: string;
  summary: string;
  detail?: Record<string, unknown> | null;
  level: "audit" | "debug";
};

export async function runModule(
  module: ModuleDefinition,
  payload: unknown,
  runMode: RunMode,
  timeoutMs = 180000,
  onProgress?: (update: ModuleRunProgress) => void,
  onTaskDiscovered?: (taskId: string) => void,
): Promise<ModuleRunResponse> {
  if (runMode === "sync" || !hasAsync(module)) {
    const response = await requestJson(module.syncEndpoint, "POST", payload);
    return { response, runMode: "sync" };
  }

  const submitResponse = await requestJson(module.asyncSubmitEndpoint!, "POST", payload);
  const taskId = parseAsyncTaskId(submitResponse);
  onTaskDiscovered?.(taskId);  // 立即通知调用方 taskId，不等任务完成
  onProgress?.({ state: parseTaskState(submitResponse), progress: parseTaskProgress(submitResponse) });

  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    const statusResponse = await requestJson(module.asyncStatusEndpoint!(taskId), "GET");
    const state = parseTaskState(statusResponse);
    onProgress?.({ state, progress: parseTaskProgress(statusResponse) });

    if (FINAL_STATES.has(state)) {
      const result = parseTaskResult(statusResponse);
      if (state === "failed") {
        const err = isRecord(statusResponse) && typeof statusResponse.error === "string"
          ? statusResponse.error
          : "Async task failed";
        const failure = new Error(err) as Error & { asyncTaskId?: string; asyncState?: string };
        failure.asyncTaskId = taskId;
        failure.asyncState = state;
        throw failure;
      }
      if (result === undefined || result === null) {
        throw new Error("Async task finished without result payload");
      }
      return {
        response: result,
        asyncTaskId: taskId,
        asyncState: state,
        runMode: "async"
      };
    }

    await sleep(1500);
  }

  const timeoutError = new Error("Async task timeout") as Error & {
    asyncTaskId?: string;
    asyncState?: string;
  };
  timeoutError.asyncTaskId = taskId;
  timeoutError.asyncState = "running";
  throw timeoutError;
}

export async function retryModuleTask(module: ModuleDefinition, taskId: string): Promise<unknown> {
  if (!module.asyncRetryEndpoint) {
    throw new Error("Retry is not supported by this module");
  }
  return requestJson(module.asyncRetryEndpoint(taskId), "POST");
}

export async function cancelModuleTask(module: ModuleDefinition, taskId: string): Promise<unknown> {
  if (!module.asyncCancelEndpoint) {
    throw new Error("Cancel is not supported by this module");
  }
  return requestJson(module.asyncCancelEndpoint(taskId), "POST");
}

export async function fetchModuleTaskStatus(module: ModuleDefinition, taskId: string): Promise<{
  state: string;
  progress?: number;
  result?: unknown;
  error?: string;
}> {
  if (!module.asyncStatusEndpoint) {
    throw new Error("Async status is not supported by this module");
  }

  const statusResponse = await requestJson(module.asyncStatusEndpoint(taskId), "GET");
  const state = parseTaskState(statusResponse);
  const progress = parseTaskProgress(statusResponse);
  const result = parseTaskResult(statusResponse);
  const error = isRecord(statusResponse) && typeof statusResponse.error === "string"
    ? statusResponse.error
    : undefined;

  return { state, progress, result, error };
}
