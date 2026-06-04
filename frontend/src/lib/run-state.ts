import type { ModuleRun } from "./domain";

const TERMINAL_ASYNC_STATES = new Set(["succeeded", "completed", "failed", "cancelled", "canceled"]);
const SUCCESS_ASYNC_STATES = new Set(["succeeded", "completed"]);
const FAILED_ASYNC_STATES = new Set(["failed", "cancelled", "canceled"]);

export type RunLifecycleState = "idle" | "running" | "success" | "failed";

export function normalizeAsyncState(value: string | undefined): string | null {
  if (!value) return null;
  const normalized = value.trim().toLowerCase();
  return normalized.length > 0 ? normalized : null;
}

export function isRunInProgress(run: ModuleRun | null | undefined): boolean {
  if (!run) return false;
  if (run.runMode !== "async" || !run.asyncTaskId) return false;

  const asyncState = normalizeAsyncState(run.asyncState);
  if (!asyncState) {
    return !run.finishedAt;
  }

  return !TERMINAL_ASYNC_STATES.has(asyncState);
}

export function isRunSuccessful(run: ModuleRun | null | undefined): boolean {
  if (!run) return false;

  const asyncState = normalizeAsyncState(run.asyncState);
  if (asyncState && SUCCESS_ASYNC_STATES.has(asyncState)) {
    return true;
  }

  return !isRunInProgress(run) && !!run.finishedAt && run.success;
}

export function isRunFailed(run: ModuleRun | null | undefined): boolean {
  if (!run) return false;

  const asyncState = normalizeAsyncState(run.asyncState);
  if (asyncState && FAILED_ASYNC_STATES.has(asyncState)) {
    return true;
  }

  return !isRunInProgress(run) && !!run.finishedAt && !run.success;
}

export function getRunLifecycleState(run: ModuleRun | null | undefined): RunLifecycleState {
  if (!run) return "idle";
  if (isRunInProgress(run)) return "running";
  if (isRunFailed(run)) return "failed";
  if (isRunSuccessful(run)) return "success";
  return "idle";
}
