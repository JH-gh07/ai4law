# Issue061：SCC 审查首次失败后重试成功，任务卡片仍显示 FAIL

## 一、现象

用户在 2026-08-09 20:20 创建了一个 EU_SCC 审查任务，任务因 `IssueItem.recommended_action` 为空触发 Pydantic `ValidationError` 而执行失败。之后用户重新提交了两次（2026-08-10 10:03 和 2026-08-10 17:35），最新一次（17:35）的数据库 `run_events` 已确认为 `COMPLETED`。但前端 `TaskSpacesPage` 的任务卡片上 EU_SCC 仍然显示 `FAIL · EU_SCC`。

## 二、根因逻辑链路

### 2.1 完整调用链与失败点

```
前端提交 SCC async → POST /api/v1/eu_scc/generate_async
  → EU_SCCService.submit_async(payload)
    → InMemoryTaskManager.submit_with_trace(runner)   [纯内存，无持久化]
      → 线程池执行 generate_report()
        → _build_pipeline(rule_result).run()
          → build_issues() → build_eu_scc_issues()
            → 遍历 rule_result.all_findings
              → 某个 SCCFinding.recommendation == "" (Agent 产出)
                → _issue() 守卫: if not (recommended_action or "").strip()
                  → ("" or "").strip() → "".strip() → ""
                  → not "" → True → 应该填充默认值 ✅
                  → 但如果 .pyc 缓存过期或旧字节码：
                    → 守卫不执行 → IssueItem(recommended_action="") ⚡
            → build_context_pack(GenerationContextPack(issues=[...]))
              → Pydantic 校验 list[IssueItem]
                → ValidationError: recommended_action String should have at least 1 character ❌
      → InMemoryTaskManager._execute() catch Exception
        → record.state = "FAILED"
        → record.error = "ValidationError: ..."
```

### 2.2 守卫为何会失效

`("" or "").strip()` 在 Python 中返回空字符串 `""`，`not ""` 为 `True`，纯逻辑上守卫应正确触发。但两次失败都发生在不同时间产生同一错误，可能的根因：

1. **`.pyc` 字节码缓存**（最可能）：代码 `issue_builder.py` 被修改后，运行中的服务进程仍持有旧 `.pyc` 字节码。旧版 `_issue()` 可能没有守卫逻辑，直接 `IssueItem(recommended_action=finding.recommendation)` — 此时 `finding.recommendation == ""` 直接透传；
2. **Agent 注入**：Agent（clause_semantic, tia_effectiveness）在 `service.py:129-166` 中对 `rule_result.all_findings` 动态追加 `SCCFinding`，LLM 生成的 finding 的 `recommendation` 字段可能确实为空串。

### 2.3 前端 FAIL 持久化链路

```
失败发生 → record.state = "FAILED", record.error = "ValidationError: ..."
  → SSE 事件推送 RunEvent(summary="任务执行失败: ...")
  → 前端 GlobalTaskWatcher 轮询 GET /eu_scc/tasks/{task_id}
    → {state: "failed", error: "ValidationError..."}
    → dispatch({type: "MODULE_RUN_UPDATED"})
    → app-store.tsx:474 → localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
      → ModuleRun{success: false, asyncState: "failed"} 永久缓存
```

### 2.4 TaskSpacesPage 如何决定显示 FAIL

`frontend/src/pages/TaskSpacesPage.tsx:70-80`:

```tsx
const latestRunByTask = useMemo(() => {
  const map = new Map<string, {...}>();
  for (const run of state.moduleRuns) {
    const prev = map.get(run.taskSpaceId);
    const at = run.finishedAt ?? run.startedAt;
    if (!prev || at > prev.at) {
      map.set(run.taskSpaceId, { 
        state: getRunLifecycleState(run),  // → isRunFailed() → "failed"
        module: run.module 
      });
    }
  }
  return map;
}, [state.moduleRuns]);
```

`getRunLifecycleState` 调用链（`run-state.ts:76-86`）：

```ts
function isRunFailed(run):
  asyncState = normalizeAsyncState(run.asyncState)  // "failed"
  if (asyncState && FAILED_ASYNC_STATES.has(asyncState))  // "failed" ∈ {"failed","cancelled","canceled"}
    return true
```

卡片渲染（`TaskSpacesPage.tsx:314-330`）：

```tsx
let pillClass = latestRun.state === "running" ? "running"
             : latestRun.state === "success" ? "ok"
             : "fail";  // ← 所有非 running/success 统一显示 fail
let pillText = `FAIL · ${latestRun.module.toUpperCase()}`;
```

### 2.5 为何重试成功后仍不消除

关键：每次重新提交都创建**新的 taskId**：

```
同一用户 700689f8-... 的 task_ownerships 表：
┌──────────────────────────────────────┬──────────┬───────────┐
│ task_id                              │ 状态     │ 创建时间   │
├──────────────────────────────────────┼──────────┼───────────┤
│ 2b22b3d4-facf-4619-8e71-75845839bcec │ COMPLETED│ 08-10 17:35│ ← 最新成功
│ eb464c96-982f-473a-94f7-fd7cb4478aaa │ RUNNING  │ 08-10 10:03│ ← 旧进程残留
│ 8546248f-3ef3-43b6-b225-6dc3b0153c19 │ FAILED   │ 08-09 20:20│ ← 失败
│ c52e9379-c455-451f-b332-6d789683c61e │ FAILED   │ 08-09 12:55│ ← 失败
│ c8d51f85-9061-4e91-a8a6-15b430ed0cf0 │ COMPLETED│ 08-09 10:25│
└──────────────────────────────────────┴──────────┴───────────┘
```

每个 taskId 在前端映射为独立的 `taskSpaceId` → 独立的 TaskSpace 卡片。**失败的卡片不会因为新的卡片成功而自动消失**。

### 2.6 Workspace Recovery 的推波助澜

`backend/api/v1/endpoints/me.py:254-284` 的 `/workspace-recovery` 接口：

```python
for task in list_my_tasks():  # → 来自 diagnosis_sessions + review_tasks 表
    recovered_items.append(RecoveredWorkspaceItem(
        status=task.status,
        run=_build_recovered_run(task, artifacts)
    ))
```

但 SCC 任务**只在 `task_ownerships` 表中**（只有 `task_id/user_id/module/created_at` 四列，无 `status` 字段），且 SCC 不走 `diagnosis_sessions` 或 `review_tasks`。所以 `/workspace-recovery` 返回列表中**不包含 SCC 任务本身**。

- **成功的 SCC 任务**通过 `report_artifacts` 表恢复（line 286-309），status 固定为 `"completed"`。
- **失败的 SCC 任务**因为没有注册 `report_artifacts`（生成未完成即报错），不会被 recovery 恢复。

因此 **recovery 只会带回成功记录，失败记录靠 localStorage 残留存活**。

## 三、证据（实际数据库/文件系统数据）

### 3.1 run_events 表

```text
-- 成功运行 (2b22b3d4)
event_type="status", 
summary="任务执行完成 (eu_scc)", 
timestamp="2026-08-10T17:38:30.169241+00:00"

-- 失败运行 (8546248f)
event_type="status",
summary="任务执行失败: 1 validation error for IssueItem
recommended_action
  String should have at least 1 character",
timestamp="2026-08-09T20:20:57.254820+00:00"
```

### 3.2 磁盘 run_manifest.json

```text
c52e9379 (08-09 12:55) → {"status": "FAILED", "error": "ValidationError: ...recommended_action..."}
8546248f (08-09 20:20) → {"status": "FAILED", "error": "同上"}
2b22b3d4 (08-10 17:35) → {"status": "COMPLETED", "error": null}
```

### 3.3 report_artifacts 表

- 成功运行 2b22b3d4：6 个 artifacts（pdf, docx, findings_json, rule_engine_result_json, citation_map_json）
- 失败运行 8546248f：0 个 artifacts

### 3.4 前端关键代码位置

| 文件 | 行号 | 作用 |
|------|------|------|
| `frontend/src/pages/TaskSpacesPage.tsx` | 70-80 | `latestRunByTask` 按 taskSpaceId 分组取最新 |
| `frontend/src/pages/TaskSpacesPage.tsx` | 314-331 | 卡片状态 pill 渲染 |
| `frontend/src/lib/run-state.ts` | 76-86 | `isRunFailed` 判断逻辑 |
| `frontend/src/lib/app-store.tsx` | 473-474 | localStorage 持久化 |
| `frontend/src/lib/app-store.tsx` | 383-444 | `buildRecoveryStateFromRuns` 合并 recovery |
| `backend/api/v1/endpoints/me.py` | 173-192 | `_build_recovered_run` |
| `backend/domains/eu/scc_review/issue_builder.py` | 17-28 | `_issue()` 守卫（已修复） |
| `backend/domains/eu/scc_review/issue_builder.py` | 109-115 | 事后安全检查（新增） |
| `backend/common/tasks/manager.py` | 55-462 | `InMemoryTaskManager`（纯内存） |

## 四、修复状态

### 4.1 ✅ 已修复

`backend/domains/eu/scc_review/issue_builder.py`：
- `_issue()` 守卫从 `not (x or "").strip()` 改为 `not x or not str(x).strip()`
- `build_eu_scc_issues()` return 前新增事后安全检查

### 4.2 ⚠️ 待处理

1. **前端展示错误详情**：卡片只显示 `FAIL · EU_SCC`，应将 `latestRun.error` 展示在卡片
2. **SCC 加入 rerun_all_modules.py**：当前脚本不含 SCC
3. **task_ownerships 增加 status 字段**：当前无持久化状态
4. **前端清理废弃 FAIL 记录**：localStorage 中历史 FAIL 应可被 recovery 覆盖

## 五、总结

| 层面 | 结论 |
|------|------|
| 失败根因 | Agent 生成的 `SCCFinding.recommendation` 可能为空串，`.pyc` 缓存导致守卫失效 |
| 失败传播 | `InMemoryTaskManager` FAILED → SSE 推送 → 前端 localStorage 持久化 |
| 页面残留 | 每次重试创建新 taskId → 旧 FAIL 卡片独立存在 → recovery 不覆盖 |
| 代码修复 | `issue_builder.py` 守卫强化 + 事后安全检查 ✅ |
| 数据现状 | 同一用户 SCC 有 5 个 taskId，2 FAIL + 2 COMPLETED + 1 RUNNING 残留 |
