import { describe, expect, it } from "vitest";

import {
  MAX_EVIDENCE_PER_SPACE,
  MAX_ISSUES_PER_SPACE,
  MAX_RUNS_PER_SPACE,
  MAX_SESSIONS,
  MAX_SYSTEM_MESSAGES,
  clearLocalSnapshot,
  parsePersistedSnapshot,
  persistedToAppState,
  persistSnapshot,
  snapshotSizeBytes,
  toPersistedState,
  type StorageLike,
} from "./app-store-persistence";
import type {
  ConsistencyIssue,
  EvidenceHit,
  ModuleRun,
  OnboardingState,
  OutputArtifact,
  PanelState,
  RunSession,
  StageNode,
  SystemMessage,
  TaskSpace,
} from "./domain";

// ── 构造助手 ──────────────────────────────────────────────────────────────

const makeTaskSpace = (id: string): TaskSpace => ({
  id,
  name: `space-${id}`,
  mode: "rapid",
  jurisdiction: "CN",
  taskTemplateId: "review",
  module: "review",
  workspaceStyle: "cn_document_review",
  createdAt: "2026-08-10T00:00:00.000Z",
  updatedAt: "2026-08-10T00:00:00.000Z",
});

const makeRun = (id: string, extra: Partial<ModuleRun> = {}): ModuleRun => ({
  id,
  taskSpaceId: "space-1",
  module: "review",
  runMode: "async",
  startedAt: `2026-08-1${Number(id) % 10}T00:00:00.000Z`,
  success: true,
  request: {},
  ...extra,
});

const makeStage = (id: string): StageNode => ({
  id,
  name: `stage-${id}`,
  status: "done",
  startedAt: "2026-08-10T00:00:00.000Z",
  completedAt: "2026-08-10T00:00:01.000Z",
  summary: `summary-${id}`,
  detail: { trace_block: `TRACE_BLOCK_MARKER_${id}`, raw: "x".repeat(5000) },
});

const makeSession = (id: string): RunSession => ({
  id,
  taskSpaceId: "space-1",
  taskId: "task-1",
  module: "review",
  startedAt: `2026-08-1${Number(id) % 10}T00:00:00.000Z`,
  stages: [makeStage("a"), makeStage("b")],
  isComplete: true,
});

const makeEvidence = (id: string): EvidenceHit => ({
  id,
  taskSpaceId: "space-1",
  module: "review",
  source: "src",
  title: `title-${id}`,
  snippet: "x".repeat(5000),
  createdAt: `2026-08-1${Number(id) % 10}T00:00:00.000Z`,
});

const makeIssue = (id: string): ConsistencyIssue => ({
  id,
  taskSpaceId: "space-1",
  module: "review",
  severity: "high",
  message: "y".repeat(5000),
  createdAt: `2026-08-1${Number(id) % 10}T00:00:00.000Z`,
});

const makeArtifact = (id: string): OutputArtifact => ({
  id,
  taskSpaceId: "space-1",
  module: "review",
  kind: "pdf",
  path: `path/${id}`,
  createdAt: "2026-08-10T00:00:00.000Z",
});

const makeSystemMessage = (id: string): SystemMessage => ({
  id,
  taskSpaceId: "space-1",
  text: "z".repeat(5000),
  createdAt: `2026-08-1${Number(id) % 10}T00:00:00.000Z`,
});

function baseState(overrides: Record<string, unknown> = {}) {
  return {
    taskSpaces: [makeTaskSpace("1")],
    moduleRuns: [makeRun("1")],
    artifacts: [makeArtifact("1")],
    evidenceHits: [makeEvidence("1")],
    issues: [makeIssue("1")],
    systemMessages: [makeSystemMessage("1")],
    runSessions: [makeSession("1")],
    panelState: {
      leftOpen: true,
      rightOpen: true,
      leftWidth: 260,
      rightWidth: 300,
      topOpen: true,
      focusMode: "split",
      stageLayout: "split",
      primaryPlugin: "run",
      secondaryPlugin: "preview",
    } as PanelState,
    onboarding: { active: false, stepIndex: 0, completed: false } as OnboardingState,
    ...overrides,
  };
}

function memoryStorage(): StorageLike & { data: Map<string, string> } {
  const data = new Map<string, string>();
  return {
    data,
    getItem: (k) => data.get(k) ?? null,
    setItem: (k, v) => {
      data.set(k, v);
    },
    removeItem: (k) => {
      data.delete(k);
    },
  };
}

function quotaStorage(): StorageLike {
  return {
    getItem: () => null,
    setItem: () => {
      const err = new Error("quota");
      err.name = "QuotaExceededError";
      throw err;
    },
    removeItem: () => {},
  };
}

// ── T01：测量 + 敏感数据排除 ─────────────────────────────────────────────

describe("toPersistedState：体积裁剪与敏感数据排除", () => {
  it("排除完整 request/response/error 长正文", () => {
    const state = baseState({
      moduleRuns: [
        makeRun("1", {
          request: { Authorization: "Bearer secret-token", apiKey: "sk-123456", prompt: "x".repeat(50000) },
          response: { report_body: "FULL_REPORT_BODY_MARKER", docx: "y".repeat(50000) },
          error: "z".repeat(50000),
          errorCode: "E_QUOTA",
        }),
      ],
    });

    const persisted = toPersistedState(state);
    const run = persisted.moduleRuns[0] as Record<string, unknown>;

    expect("request" in run).toBe(false);
    expect("response" in run).toBe(false);
    expect("error" in run).toBe(false);
    expect(run.errorCode).toBe("E_QUOTA");
  });

  it("截断超长证据摘要与 issue 消息", () => {
    const persisted = toPersistedState(baseState());
    expect(persisted.evidenceHits[0].snippet.length).toBeLessThanOrEqual(600);
    expect(persisted.issues[0].message.length).toBeLessThanOrEqual(1000);
  });

  it("丢弃 stage.detail 大对象，仅保留短 summary", () => {
    const persisted = toPersistedState(baseState());
    const stage = persisted.runSessions[0].stages[0] as Record<string, unknown>;
    expect("detail" in stage).toBe(false);
    expect("command" in stage).toBe(false);
    expect(typeof stage.summary).toBe("string");
  });

  it("序列化结果不包含 Authorization、api key、完整正文、Trace block", () => {
    const state = baseState({
      moduleRuns: [
        makeRun("1", {
          request: { Authorization: "Bearer secret-token", apiKey: "sk-123456" },
          response: { body: "FULL_REPORT_BODY_MARKER" },
        }),
      ],
      evidenceHits: [makeEvidence("1")],
      runSessions: [makeSession("1")],
    });

    const serialized = JSON.stringify(toPersistedState(state));
    expect(serialized).not.toContain("Bearer secret-token");
    expect(serialized).not.toContain("sk-123456");
    expect(serialized).not.toContain("Authorization");
    expect(serialized).not.toContain("FULL_REPORT_BODY_MARKER");
    expect(serialized).not.toContain("TRACE_BLOCK_MARKER");
  });

  it("普通快照体积远低于 1MB 预算", () => {
    const persisted = toPersistedState(baseState());
    expect(snapshotSizeBytes(persisted)).toBeLessThan(1_000_000);
  });
});

// ── T02：数量上限 ─────────────────────────────────────────────────────────

describe("toPersistedState：数量上限", () => {
  it("run session 最多保留 MAX_SESSIONS 个", () => {
    const sessions = Array.from({ length: MAX_SESSIONS + 10 }, (_, i) => makeSession(String(i)));
    const persisted = toPersistedState(baseState({ runSessions: sessions }));
    expect(persisted.runSessions.length).toBe(MAX_SESSIONS);
  });

  it("每个 task space 的 module run 最多 MAX_RUNS_PER_SPACE 个", () => {
    const runs = Array.from({ length: MAX_RUNS_PER_SPACE + 5 }, (_, i) => makeRun(String(i)));
    const persisted = toPersistedState(baseState({ moduleRuns: runs }));
    expect(persisted.moduleRuns.length).toBe(MAX_RUNS_PER_SPACE);
  });

  it("每个 task space 的 evidence 最多 MAX_EVIDENCE_PER_SPACE 个", () => {
    const items = Array.from({ length: MAX_EVIDENCE_PER_SPACE + 10 }, (_, i) => makeEvidence(String(i)));
    const persisted = toPersistedState(baseState({ evidenceHits: items }));
    expect(persisted.evidenceHits.length).toBe(MAX_EVIDENCE_PER_SPACE);
  });

  it("每个 task space 的 issue 最多 MAX_ISSUES_PER_SPACE 个", () => {
    const items = Array.from({ length: MAX_ISSUES_PER_SPACE + 10 }, (_, i) => makeIssue(String(i)));
    const persisted = toPersistedState(baseState({ issues: items }));
    expect(persisted.issues.length).toBe(MAX_ISSUES_PER_SPACE);
  });

  it("全局 system message 最多 MAX_SYSTEM_MESSAGES 条", () => {
    const items = Array.from({ length: MAX_SYSTEM_MESSAGES + 20 }, (_, i) => makeSystemMessage(String(i)));
    const persisted = toPersistedState(baseState({ systemMessages: items }));
    expect(persisted.systemMessages.length).toBe(MAX_SYSTEM_MESSAGES);
  });
});

// ── T02：反序列化 fail-soft ───────────────────────────────────────────────

describe("parsePersistedSnapshot：损坏/未知版本/缺字段 fail-soft", () => {
  it("正常 v2 快照可解析", () => {
    const persisted = toPersistedState(baseState());
    const parsed = parsePersistedSnapshot(JSON.stringify(persisted));
    expect(parsed?.version).toBe(2);
  });

  it("旧 v1 快照（version 1）返回 null", () => {
    const v1 = { version: 1, taskSpaces: [] };
    expect(parsePersistedSnapshot(JSON.stringify(v1))).toBeNull();
  });

  it("损坏 JSON 返回 null", () => {
    expect(parsePersistedSnapshot("{ not valid json")).toBeNull();
  });

  it("未知版本（version 3）返回 null", () => {
    const v3 = toPersistedState(baseState());
    expect(parsePersistedSnapshot(JSON.stringify({ ...v3, version: 3 }))).toBeNull();
  });

  it("缺少数组字段返回 null", () => {
    const p = toPersistedState(baseState());
    const missing = { ...p } as Record<string, unknown>;
    delete missing.moduleRuns;
    expect(parsePersistedSnapshot(JSON.stringify(missing))).toBeNull();
  });

  it("null 输入返回 null", () => {
    expect(parsePersistedSnapshot(null)).toBeNull();
  });
});

// ── T03：安全写入 + 容量降级 ──────────────────────────────────────────────

describe("persistSnapshot：安全写入与降级", () => {
  it("正常写入到 v2 key", () => {
    const storage = memoryStorage();
    const persisted = toPersistedState(baseState());
    const result = persistSnapshot(persisted, storage);
    expect(result.ok).toBe(true);
    expect(storage.data.has("ai4law_app_state_v2")).toBe(true);
  });

  it("QuotaExceededError 不向上抛出，返回 ok:false", () => {
    const persisted = toPersistedState(baseState());
    const result = persistSnapshot(persisted, quotaStorage());
    expect(result.ok).toBe(false);
  });

  it("首次超限后触发降级回调", () => {
    const persisted = toPersistedState(baseState());
    const levels: number[] = [];
    persistSnapshot(persisted, quotaStorage(), (level) => levels.push(level));
    expect(levels.length).toBeGreaterThan(0);
    expect(levels[0]).toBe(1);
  });

  it("降级级别按顺序推进：session → evidence/issues → runs → system messages", () => {
    const persisted = toPersistedState(
      baseState({
        runSessions: Array.from({ length: 20 }, (_, i) => makeSession(String(i))),
        evidenceHits: Array.from({ length: 100 }, (_, i) => makeEvidence(String(i))),
        issues: Array.from({ length: 100 }, (_, i) => makeIssue(String(i))),
        moduleRuns: Array.from({ length: 20 }, (_, i) => makeRun(String(i))),
        systemMessages: Array.from({ length: 200 }, (_, i) => makeSystemMessage(String(i))),
      }),
    );
    const levels: number[] = [];
    persistSnapshot(persisted, quotaStorage(), (level) => levels.push(level));
    expect(levels).toEqual([1, 2, 3, 4]);
  });
});

// ── T02/T04：往返与清理边界 ───────────────────────────────────────────────

describe("persistedToAppState：往返与清理边界", () => {
  it("toPersistedState → persistedToAppState 保留身份字段，丢失完整正文", () => {
    const state = baseState({
      moduleRuns: [makeRun("1", { response: { huge: "x".repeat(5000) } })],
    });
    const roundtrip = persistedToAppState(toPersistedState(state));

    expect(roundtrip.moduleRuns[0].id).toBe("1");
    expect(roundtrip.moduleRuns[0].response).toBeUndefined();
    expect(roundtrip.moduleRuns[0].request).toEqual({});
  });

  it("clearLocalSnapshot 只删除本地缓存 key，不触碰后端", () => {
    const storage = memoryStorage();
    storage.setItem("ai4law_app_state_v1", "legacy");
    storage.setItem("ai4law_app_state_v2", "current");
    storage.setItem("ai4law_ui_lang", "zh"); // 无关 key，不应被删除

    clearLocalSnapshot(storage);

    expect(storage.data.has("ai4law_app_state_v1")).toBe(false);
    expect(storage.data.has("ai4law_app_state_v2")).toBe(false);
    expect(storage.data.get("ai4law_ui_lang")).toBe("zh");
  });
});
