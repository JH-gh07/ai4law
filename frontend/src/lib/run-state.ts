import type { ModuleRun } from "./domain";

// ---------------------------------------------------------------------------
// Async state constants
// ---------------------------------------------------------------------------

const TERMINAL_ASYNC_STATES = new Set(["succeeded", "completed", "failed", "cancelled", "canceled"]);
const SUCCESS_ASYNC_STATES = new Set(["succeeded", "completed"]);
const FAILED_ASYNC_STATES = new Set(["failed", "cancelled", "canceled"]);
const RECONCILIABLE_ERRORS = new Set(["async task timeout", "review generation failed"]);

export type RunLifecycleState = "idle" | "running" | "success" | "failed";
export type ExtendedRunLifecycleState = "idle" | "running" | "success" | "failed" | "unreachable";

// ---------------------------------------------------------------------------
// Normalization helpers
// ---------------------------------------------------------------------------

export function normalizeAsyncState(value: string | undefined): string | null {
  if (!value) return null;
  const normalized = value.trim().toLowerCase();
  return normalized.length > 0 ? normalized : null;
}

/**
 * Check if an async state string (from backend) means the task has finished.
 * Used by GlobalTaskWatcher to decide whether to stop polling.
 */
export function isFinalAsyncState(state: string | undefined): boolean {
  const norm = normalizeAsyncState(state);
  if (!norm) return false;
  return TERMINAL_ASYNC_STATES.has(norm);
}

/**
 * Check if an async state string means the task completed successfully.
 */
export function isSuccessAsyncState(state: string | undefined): boolean {
  const norm = normalizeAsyncState(state);
  if (!norm) return false;
  return SUCCESS_ASYNC_STATES.has(norm);
}

// ---------------------------------------------------------------------------
// ModuleRun lifecycle helpers
// ---------------------------------------------------------------------------

export function isRunInProgress(run: ModuleRun | null | undefined): boolean {
  if (!run) return false;
  if (run.runMode !== "async" || !run.asyncTaskId) return false;

  const asyncState = normalizeAsyncState(run.asyncState);
  if (!asyncState) {
    // No asyncState set yet → still running if no finishedAt
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

export function isRunUnreachable(run: ModuleRun | null | undefined): boolean {
  if (!run) return false;
  return !isRunInProgress(run) && !!run.finishedAt && run.errorCode === "backend_unreachable";
}

export function isRunFailed(run: ModuleRun | null | undefined): boolean {
  if (!run) return false;
  if (isRunUnreachable(run)) return false;

  const asyncState = normalizeAsyncState(run.asyncState);
  if (asyncState && FAILED_ASYNC_STATES.has(asyncState)) {
    return true;
  }

  return !isRunInProgress(run) && !!run.finishedAt && !run.success;
}

export function getRunLifecycleState(run: ModuleRun | null | undefined): ExtendedRunLifecycleState {
  if (!run) return "idle";
  if (isRunInProgress(run)) return "running";
  if (isRunUnreachable(run)) return "unreachable";
  if (isRunFailed(run)) return "failed";
  if (isRunSuccessful(run)) return "success";
  return "idle";
}

// ---------------------------------------------------------------------------
// Global polling selectors
// ---------------------------------------------------------------------------

/**
 * Select all ModuleRuns that the GlobalTaskWatcher should actively poll.
 *
 * Criteria:
 * - asyncTaskId exists
 * - asyncState is not terminal
 * - finishedAt is not set (hasn't already been finalized)
 */
export function selectRunningModuleRuns(runs: ModuleRun[]): ModuleRun[] {
  return runs.filter((run) => {
    if (!run.asyncTaskId) return false;
    const asyncState = normalizeAsyncState(run.asyncState);
    if (asyncState && TERMINAL_ASYNC_STATES.has(asyncState)) {
      // A client timeout or the Review endpoint's generic error can race with
      // the real backend task. Reconcile each such terminal record once.
      if (run.statusCheckedAt) return false;
      return RECONCILIABLE_ERRORS.has((run.error ?? "").trim().toLowerCase());
    }
    // If finishedAt is already set, we've already finalized it
    if (run.finishedAt) return false;
    return true;
  });
}

// ---------------------------------------------------------------------------
// ModuleRun merge helpers
// ---------------------------------------------------------------------------

/**
 * Build a stable identity key for a ModuleRun.
 * Prefers asyncTaskId > id > module + taskSpaceId + startedAt.
 */
export function getRunIdentityKey(run: ModuleRun): string {
  if (run.asyncTaskId) return `task:${run.asyncTaskId}`;
  return `run:${run.id}`;
}

/**
 * Merge two ModuleRun objects. The "server" (newer) record wins for
 * state fields (success, asyncState, response, error, finishedAt).
 * The "local" (older) record keeps its startedAt and request.
 */
export function mergeRunResults(local: ModuleRun, server: ModuleRun): ModuleRun {
  return {
    ...local,
    success: server.success,
    asyncState: server.asyncState ?? local.asyncState,
    response: server.response ?? local.response,
    error: server.error ?? local.error,
    errorCode: server.errorCode ?? local.errorCode,
    finishedAt: server.finishedAt ?? local.finishedAt,
    asyncTaskId: server.asyncTaskId ?? local.asyncTaskId,
    runMode: server.runMode ?? local.runMode,
  };
}

function readRunTimestamp(run: ModuleRun): number {
  // A reconciliation can refresh finishedAt long after an attempt ended.
  // Use the attempt start time to keep historical runs in their true order.
  const candidate = run.startedAt;
  const value = new Date(candidate).getTime();
  return Number.isFinite(value) ? value : 0;
}

export function compareRunsByRecency(left: ModuleRun, right: ModuleRun): number {
  return readRunTimestamp(right) - readRunTimestamp(left);
}

export function selectPreferredRun(runs: ModuleRun[]): ModuleRun | null {
  if (runs.length === 0) return null;

  const runningRuns = runs.filter((run) => isRunInProgress(run)).sort(compareRunsByRecency);
  if (runningRuns.length > 0) {
    return runningRuns[0];
  }

  return [...runs].sort(compareRunsByRecency)[0] ?? null;
}
