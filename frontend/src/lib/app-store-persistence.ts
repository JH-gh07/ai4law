/**
 * 版本化轻量本地快照持久化（task066）。
 *
 * 设计原则：
 * 1. localStorage 只保存裁剪后的轻量 UI/恢复快照，绝不保存完整
 *    request / response / Trace block / 文档正文 / 敏感数据；
 * 2. 写入失败（QuotaExceededError / SecurityError / 序列化异常）必须 fail-soft，
 *    不能让 AppStoreProvider 崩溃；
 * 3. 快照带 schema version，旧 v1 只读迁移、损坏 JSON 安全丢弃；
 * 4. 清理只针对本地缓存，绝不触碰后端数据。
 *
 * 本模块保持纯函数 + 可注入 storage 接口，便于单元测试（T01/T03/T05）。
 */

import type {
  ConsistencyIssue,
  EvidenceHit,
  ModuleRun,
  OnboardingState,
  OutputArtifact,
  PanelState,
  RunSession,
  StageNode,
  StageNodeStatus,
  SystemMessage,
  TaskSpace,
} from "./domain";

export const STORAGE_KEY_V1 = "ai4law_app_state_v1";
export const STORAGE_KEY_V2 = "ai4law_app_state_v2";

/** 快照体积预算（字节），建议不超过 1 MB。 */
export const SNAPSHOT_BUDGET_BYTES = 1_000_000;

/** 各集合数量上限。 */
export const MAX_SESSIONS = 20;
export const MAX_RUNS_PER_SPACE = 20;
export const MAX_EVIDENCE_PER_SPACE = 100;
export const MAX_ISSUES_PER_SPACE = 100;
export const MAX_SYSTEM_MESSAGES = 200;

/** 单条文本长度上限（字符）。 */
export const SNIPPET_MAX = 600;
export const ISSUE_MESSAGE_MAX = 1000;
export const SYSTEM_TEXT_MAX = 2000;
export const STAGE_SUMMARY_MAX = 600;

// ─────────────────────────────────────────────────────────────────────────
// 持久化 Schema（v2）：裁剪后的轻量字段
// ─────────────────────────────────────────────────────────────────────────

export type PersistedModuleRun = {
  id: string;
  taskSpaceId: string;
  module: ModuleRun["module"];
  runMode: ModuleRun["runMode"];
  startedAt: string;
  finishedAt?: string;
  success: boolean;
  errorCode?: string;
  asyncTaskId?: string;
  asyncState?: string;
};

export type PersistedEvidenceHit = {
  id: string;
  taskSpaceId: string;
  module: EvidenceHit["module"];
  source: string;
  title: string;
  snippet: string;
  createdAt: string;
};

export type PersistedIssue = {
  id: string;
  taskSpaceId: string;
  module: ConsistencyIssue["module"];
  severity: ConsistencyIssue["severity"];
  message: string;
  createdAt: string;
};

export type PersistedSystemMessage = {
  id: string;
  taskSpaceId: string;
  text: string;
  createdAt: string;
  eventType?: string;
  eventSeq?: number;
};

export type PersistedStage = {
  id: string;
  name: string;
  status: StageNodeStatus;
  startedAt?: string;
  completedAt?: string;
  summary?: string;
};

export type PersistedRunSession = {
  id: string;
  taskSpaceId: string;
  taskId: string;
  module: string;
  startedAt: string;
  stages: PersistedStage[];
  isComplete: boolean;
  completedAt?: string;
  totalDurationMs?: number;
};

export type PersistedAppStateV2 = {
  version: 2;
  savedAt: string;
  taskSpaces: TaskSpace[];
  moduleRuns: PersistedModuleRun[];
  artifacts: OutputArtifact[];
  evidenceHits: PersistedEvidenceHit[];
  issues: PersistedIssue[];
  systemMessages: PersistedSystemMessage[];
  runSessions: PersistedRunSession[];
  panelState: PanelState;
  onboarding: OnboardingState;
};

// ─────────────────────────────────────────────────────────────────────────
// 工具函数
// ─────────────────────────────────────────────────────────────────────────

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  if (max <= 1) return text.slice(0, max);
  return text.slice(0, max - 1) + "…";
}

function keepMostRecent<T>(items: T[], max: number, sortKey: (item: T) => string): T[] {
  if (items.length <= max) return items;
  return [...items].sort((a, b) => (sortKey(a) < sortKey(b) ? 1 : -1)).slice(0, max);
}

function capPerSpace<T extends { taskSpaceId: string }>(
  items: T[],
  max: number,
  sortKey: (item: T) => string,
): T[] {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const list = groups.get(item.taskSpaceId) ?? [];
    list.push(item);
    groups.set(item.taskSpaceId, list);
  }
  const result: T[] = [];
  for (const list of groups.values()) {
    const sorted = [...list].sort((a, b) => (sortKey(a) < sortKey(b) ? 1 : -1));
    result.push(...sorted.slice(0, max));
  }
  return result;
}

// ─────────────────────────────────────────────────────────────────────────
// 序列化：AppState → 裁剪后的 PersistedAppStateV2
// ─────────────────────────────────────────────────────────────────────────

function persistStage(stage: StageNode): PersistedStage {
  return {
    id: stage.id,
    name: stage.name,
    status: stage.status,
    startedAt: stage.startedAt,
    completedAt: stage.completedAt,
    summary: stage.summary ? truncate(stage.summary, STAGE_SUMMARY_MAX) : undefined,
  };
}

/**
 * 把运行时 AppState 裁剪为可落盘的轻量快照。
 * 明确排除 request/response/error 长正文、stage.detail、Trace block 等。
 */
export function toPersistedState(state: {
  taskSpaces: TaskSpace[];
  moduleRuns: ModuleRun[];
  artifacts: OutputArtifact[];
  evidenceHits: EvidenceHit[];
  issues: ConsistencyIssue[];
  systemMessages: SystemMessage[];
  runSessions: RunSession[];
  panelState: PanelState;
  onboarding: OnboardingState;
}): PersistedAppStateV2 {
  const moduleRuns = capPerSpace(state.moduleRuns, MAX_RUNS_PER_SPACE, (r) => r.startedAt).map(
    (r): PersistedModuleRun => ({
      id: r.id,
      taskSpaceId: r.taskSpaceId,
      module: r.module,
      runMode: r.runMode,
      startedAt: r.startedAt,
      finishedAt: r.finishedAt,
      success: r.success,
      errorCode: r.errorCode,
      asyncTaskId: r.asyncTaskId,
      asyncState: r.asyncState,
    }),
  );

  const evidenceHits = capPerSpace(state.evidenceHits, MAX_EVIDENCE_PER_SPACE, (e) => e.createdAt).map(
    (e): PersistedEvidenceHit => ({
      id: e.id,
      taskSpaceId: e.taskSpaceId,
      module: e.module,
      source: e.source,
      title: e.title,
      snippet: truncate(e.snippet, SNIPPET_MAX),
      createdAt: e.createdAt,
    }),
  );

  const issues = capPerSpace(state.issues, MAX_ISSUES_PER_SPACE, (i) => i.createdAt).map(
    (i): PersistedIssue => ({
      id: i.id,
      taskSpaceId: i.taskSpaceId,
      module: i.module,
      severity: i.severity,
      message: truncate(i.message, ISSUE_MESSAGE_MAX),
      createdAt: i.createdAt,
    }),
  );

  const systemMessages = keepMostRecent(state.systemMessages, MAX_SYSTEM_MESSAGES, (m) => m.createdAt).map(
    (m): PersistedSystemMessage => ({
      id: m.id,
      taskSpaceId: m.taskSpaceId,
      text: truncate(m.text, SYSTEM_TEXT_MAX),
      createdAt: m.createdAt,
      eventType: m.eventType,
      eventSeq: m.eventSeq,
    }),
  );

  const runSessions = keepMostRecent(state.runSessions, MAX_SESSIONS, (s) => s.startedAt).map(
    (s): PersistedRunSession => ({
      id: s.id,
      taskSpaceId: s.taskSpaceId,
      taskId: s.taskId,
      module: s.module,
      startedAt: s.startedAt,
      stages: s.stages.map(persistStage),
      isComplete: s.isComplete,
      completedAt: s.completedAt,
      totalDurationMs: s.totalDurationMs,
    }),
  );

  return {
    version: 2,
    savedAt: new Date().toISOString(),
    taskSpaces: state.taskSpaces,
    moduleRuns,
    artifacts: state.artifacts,
    evidenceHits,
    issues,
    systemMessages,
    runSessions,
    panelState: state.panelState,
    onboarding: state.onboarding,
  };
}

// ─────────────────────────────────────────────────────────────────────────
// 反序列化：PersistedAppStateV2 → 运行时 AppState（轻量占位，无完整正文）
// ─────────────────────────────────────────────────────────────────────────

export function persistedToAppState(p: PersistedAppStateV2): {
  taskSpaces: TaskSpace[];
  moduleRuns: ModuleRun[];
  artifacts: OutputArtifact[];
  evidenceHits: EvidenceHit[];
  issues: ConsistencyIssue[];
  systemMessages: SystemMessage[];
  runSessions: RunSession[];
  panelState: PanelState;
  onboarding: OnboardingState;
} {
  const moduleRuns: ModuleRun[] = p.moduleRuns.map((r) => ({
    id: r.id,
    taskSpaceId: r.taskSpaceId,
    module: r.module,
    runMode: r.runMode,
    startedAt: r.startedAt,
    finishedAt: r.finishedAt,
    success: r.success,
    request: {},
    response: undefined,
    error: undefined,
    errorCode: r.errorCode,
    asyncTaskId: r.asyncTaskId,
    asyncState: r.asyncState,
  }));

  const runSessions: RunSession[] = p.runSessions.map((s) => ({
    id: s.id,
    taskSpaceId: s.taskSpaceId,
    taskId: s.taskId,
    module: s.module,
    startedAt: s.startedAt,
    stages: s.stages.map((st): StageNode => ({
      id: st.id,
      name: st.name,
      status: st.status,
      startedAt: st.startedAt,
      completedAt: st.completedAt,
      summary: st.summary,
      detail: null,
    })),
    isComplete: s.isComplete,
    completedAt: s.completedAt,
    totalDurationMs: s.totalDurationMs,
  }));

  return {
    taskSpaces: p.taskSpaces,
    moduleRuns,
    artifacts: p.artifacts,
    evidenceHits: p.evidenceHits,
    issues: p.issues,
    systemMessages: p.systemMessages,
    runSessions,
    panelState: p.panelState,
    onboarding: p.onboarding,
  };
}

/** 解析 v2 快照，任何异常（损坏 JSON、未知版本、缺字段）都返回 null（fail-soft）。 */
export function parsePersistedSnapshot(raw: string | null): PersistedAppStateV2 | null {
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed)) return null;
    if (parsed.version !== 2) return null;
    const arrayFields = [
      "taskSpaces",
      "moduleRuns",
      "artifacts",
      "evidenceHits",
      "issues",
      "systemMessages",
      "runSessions",
    ] as const;
    for (const field of arrayFields) {
      if (!Array.isArray(parsed[field])) return null;
    }
    if (!isRecord(parsed.panelState) || !isRecord(parsed.onboarding)) return null;
    return parsed as unknown as PersistedAppStateV2;
  } catch {
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────
// 体积测量
// ─────────────────────────────────────────────────────────────────────────

export function snapshotSizeBytes(p: PersistedAppStateV2): number {
  try {
    return new TextEncoder().encode(JSON.stringify(p)).length;
  } catch {
    return Number.POSITIVE_INFINITY;
  }
}

// ─────────────────────────────────────────────────────────────────────────
// 安全写入 + 容量降级
// ─────────────────────────────────────────────────────────────────────────

export type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export type TrimLevel = 0 | 1 | 2 | 3 | 4;

/** 降级顺序：旧 session → 旧 evidence/issues → 旧 module runs → 非必要 system messages。 */
function applyTrim(p: PersistedAppStateV2, level: TrimLevel): PersistedAppStateV2 {
  switch (level) {
    case 1:
      return { ...p, runSessions: keepMostRecent(p.runSessions, 5, (s) => s.startedAt) };
    case 2:
      return {
        ...p,
        evidenceHits: capPerSpace(p.evidenceHits, 50, (e) => e.createdAt),
        issues: capPerSpace(p.issues, 50, (i) => i.createdAt),
      };
    case 3:
      return { ...p, moduleRuns: capPerSpace(p.moduleRuns, 5, (r) => r.startedAt) };
    case 4:
      return { ...p, systemMessages: [] };
    default:
      return p;
  }
}

const isStorageError = (err: unknown): boolean => {
  if (!(err instanceof Error)) return false;
  return (
    err.name === "QuotaExceededError" ||
    err.name === "NS_ERROR_DOM_QUOTA_REACHED" ||
    err.name === "SecurityError"
  );
};

export type PersistResult = { ok: boolean; level: TrimLevel };

/**
 * 写入轻量快照。写入失败时按顺序降级裁剪并重试；最终仍失败则 fail-soft，
 * 返回 ok:false，绝不向上抛异常。
 */
export function persistSnapshot(
  persisted: PersistedAppStateV2,
  storage: StorageLike,
  onTrim?: (level: TrimLevel) => void,
): PersistResult {
  let current = persisted;
  for (let level = 0 as TrimLevel; level <= 4; level = (level + 1) as TrimLevel) {
    if (level > 0) {
      current = applyTrim(current, level);
      onTrim?.(level);
    }
    try {
      const serialized = JSON.stringify(current);
      storage.setItem(STORAGE_KEY_V2, serialized);
      return { ok: true, level };
    } catch (err) {
      if (!isStorageError(err)) {
        // 非配额类异常（如 JSON 循环引用）也 fail-soft，但不再继续降级。
        return { ok: false, level };
      }
      // 配额/安全异常：继续下一级裁剪
    }
  }
  return { ok: false, level: 4 };
}

/** 只清理本地缓存，不调用任何后端删除接口。 */
export function clearLocalSnapshot(storage: StorageLike = window.localStorage): void {
  storage.removeItem(STORAGE_KEY_V1);
  storage.removeItem(STORAGE_KEY_V2);
}
