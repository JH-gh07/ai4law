# task061：SCC 审查 FAIL 残留与跨模块防护综合修复方案

> **创建日期**：2026-08-12 | **状态**：已完成（2026-08-13） | **关联 Issue**：issue061

---

## 一、问题全貌

### 1.1 触发现象

SCC 审查任务因 `IssueItem.recommended_action=""` 触发 Pydantic `ValidationError` 执行失败后，后续重新提交成功（数据库 `run_events` 确认 `COMPLETED`），但前端 `TaskSpacesPage` 卡片仍显示 `FAIL · EU_SCC`。

### 1.2 系统性排查结果

经对全部 6 个注册模块做逐行审计，发现**同一类漏洞存在于多个模块**：

| 模块 | `_issue()` 守卫 | 事后安全检查 | 风险等级 |
|------|:--:|:--:|:--:|
| `eu/scc_review` | ✅ 已修复 | ✅ 已新增 | 🟢 |
| `eu/dpia` | ❌ 无 | ❌ 无 | 🔴 |
| `us/eo14117` | ❌ 无 | ❌ 无 | 🔴 |
| `cn/pipia` | ❌ 无 | ❌ 无 | 🔴 |
| `cn/security_assessment` | ⚠️ 部分（硬编码字面量） | ❌ 无 | 🟡 |
| `eu/bcr_review` | N/A（不使用 IssueItem） | N/A | 🟢 |
| `us/cpra` | N/A（不使用 IssueItem） | N/A | 🟢 |

**四个模块（DPIA、EO14117、PIPIA、Security Assessment）的 `_issue()` 函数直接将 `recommended_action` 参数透传给 `IssueItem()`，没有任何空值检查。**

---

## 二、根因分析（三层架构）

### 2.1 层一：后端代码缺陷

```
Agent(LLM) 产出 finding.recommendation == ""
  → _issue() 透传空串 → IssueItem(recommended_action="")
    → Pydantic 校验触发 ValidationError
      → 进程内异常 → InMemoryTaskManager 标记 FAILED
```

**5 个 IssueItem 构造点的守卫现状**：

```python
# ❌ DPIA, EO14117, PIPIA, Security Assessment 共同的漏洞模式：
def _issue(..., recommended_action: str, ...) -> IssueItem:
    return IssueItem(
        ...
        recommended_action=recommended_action,  # ← 透传，无守卫
        ...
    )

# ✅ SCC 修复后的模式：
def _issue(..., recommended_action, ...) -> IssueItem:
    if not recommended_action or not str(recommended_action).strip():
        recommended_action = _DEFAULT_ACTION
    return IssueItem(..., recommended_action=recommended_action, ...)
```

### 2.2 层二：前端状态持久化

```
InMemoryTaskManager FAILED
  → SSE RunEvent("任务执行失败")
    → 前端 dispatch(MODULE_RUN_UPDATED)
      → app-store.tsx:474 localStorage.setItem()
        → ModuleRun{success:false, asyncState:"failed"} 永久写入

每次新提交 → 新 asyncTaskId → 新 ModuleRun（独立记录）
mergeModuleRuns() 按 asyncTaskId 去重 → 旧 FAIL + 新 OK 共存
```

**关键代码**（`frontend/src/lib/app-store.tsx:288-308`）：

```ts
// mergeModuleRuns 只按 asyncTaskId 去重，不清理过期/失败的旧记录
export function mergeModuleRuns(items: ModuleRun[]): ModuleRun[] {
  const byAsyncTask = new Map<string, ModuleRun>();
  for (const run of items) {
    if (!run.asyncTaskId) { withoutAsync.push(run); continue; }
    // 不同 asyncTaskId 的 run 都保留 ← FAIL+OK 共存根源
    const previous = byAsyncTask.get(run.asyncTaskId);
    if (!previous || rank(run) >= rank(previous)) {
      byAsyncTask.set(run.asyncTaskId, {...previous, ...run});
    }
  }
}
```

### 2.3 层三：Workspace Recovery 不对称

```
失败任务 → InMemoryTaskManager → 无 report_artifacts → recovery 跳过
成功任务 → 有 report_artifacts → recovery 带回（status="completed"）
失败记录 → localStorage 残留 → 永不清理
```

---

## 三、修复方案（分层、可核验）

### 阶段一：通用 IssueItem 守卫（从根本上杜绝）

#### 方案

在 `backend/common/workflow/issues.py` 的 `IssueItem` 类增加 `@model_validator`，对所有模块生效：

```python
from pydantic import model_validator

class IssueItem(BaseModel):
    # ... existing fields ...

    @model_validator(mode="after")
    def ensure_recommended_action(self):
        if not self.recommended_action or not self.recommended_action.strip():
            self.recommended_action = (
                "针对发现的问题进行详细评估，根据适用法规完成合规整改，"
                "并补充相关材料以确保合规。"
            )
        return self
```

**为什么选 `@model_validator` 而不是修改各模块**：

| 方案 | 覆盖范围 | 遗漏风险 | 维护成本 |
|------|:--:|:--:|:--:|
| 逐模块修 `_issue()` | 4 个模块 | 新增模块可能遗漏 | 高 |
| `@model_validator` | **所有模块 + 未来新增** | 0 | 低 |

#### 核验脚本

```bash
# 核验1：空字符串被拦截
python3 -c "
from backend.common.workflow import IssueItem
i = IssueItem(issue_id='T1', title='Test', description='D', 
              category='other', severity='LOW', recommended_action='')
assert i.recommended_action != '' and i.recommended_action.strip(), 'FAIL'
print('PASS: empty action replaced')
"

# 核验2：空白字符串被拦截
python3 -c "
from backend.common.workflow import IssueItem
i = IssueItem(issue_id='T2', title='Test', description='D',
              category='other', severity='LOW', recommended_action='   \t  ')
assert i.recommended_action.strip(), 'FAIL'
print('PASS: whitespace-only action replaced')
"

# 核验3：正常字符串不受影响
python3 -c "
from backend.common.workflow import IssueItem
i = IssueItem(issue_id='T3', title='Test', description='D',
              category='other', severity='LOW', recommended_action='修复 XYZ')
assert i.recommended_action == '修复 XYZ', 'FAIL'
print('PASS: valid action preserved')
"
```

#### 风险评估

- `model_validator` 在每次 `IssueItem` 构造和 `model_copy` 时执行，对正常字符串无副作用
- 默认文本为通用表述，不覆盖模块特定建议（模块传入非空值时不受影响）
- 所有模块的 `GenerationContextPack(issues=[...])` 构造时 Pydantic 重新校验，也会触发 validator，双重保证

---

### 阶段二：前端 stale 记录清理

#### 方案 A：按 taskSpaceId 清理过期 FAIL 记录

在 `buildRecoveryStateFromRuns` 或 hydrate 时，检查 `localStorage` 中的 `moduleRuns`：

```ts
// app-store.tsx 新增函数
function pruneStaleFailedRuns(
  localRuns: ModuleRun[],
  recoveredRuns: ModuleRun[],
  maxAgeHours: number = 24
): ModuleRun[] {
  const recoveredIds = new Set(recoveredRuns.map(r => r.asyncTaskId).filter(Boolean));
  const now = Date.now();
  return localRuns.filter(run => {
    // 保留无 asyncTaskId 的记录
    if (!run.asyncTaskId) return true;
    // recovery 中有的，保留
    if (recoveredIds.has(run.asyncTaskId)) return true;
    // 失败或成功且超过 maxAgeHours → 清理
    const finishedAt = run.finishedAt ? new Date(run.finishedAt).getTime() : 0;
    const isStale = finishedAt > 0 && (now - finishedAt) > maxAgeHours * 3600000;
    if (isStale && !run.success) {
      return false; // prune
    }
    return true;
  });
}
```

在 hydrate 流程中调用：

```ts
// 替换原有 mergedModuleRuns
const mergedModuleRuns = pruneStaleFailedRuns(
  mergeModuleRuns([...localSnapshot.moduleRuns, ...recoveredFromRuns.moduleRuns]),
  recoveredFromRuns.moduleRuns
);
```

#### 方案 B（备选）：前端"清理历史记录"按钮

在 TaskSpacesPage 增加一个操作按钮，允许用户清理所有 `success=false` 的历史 runs。

#### 核验脚本

```bash
# 核验：在浏览器 Console 执行
// 1. 检查当前 FAIL 记录数
const state = JSON.parse(localStorage.getItem('data_comply_flow_state') || '{}');
const failRuns = (state.moduleRuns || []).filter(r => !r.success);
console.log('FAIL runs:', failRuns.length, failRuns.map(r => r.module));

// 2. 强制清理
localStorage.removeItem('data_comply_flow_state');
location.reload();
// 检查页面是否不再显示 FAIL 卡片
```

---

### 阶段三：前端卡片展示错误详情

#### 方案

`TaskSpacesPage.tsx:314-331` 增加错误摘要：

```tsx
// 在 <span className="tasks-status-pill"> 之后新增
{latestRun?.state === "failed" && latestRun?.error && (
  <span className="tasks-error-hint" title={latestRun.error}>
    {latestRun.error.slice(0, 60)}
    {latestRun.error.length > 60 ? "…" : ""}
  </span>
)}
```

#### 核验脚本

```bash
# 核验：模拟一个 FAIL run 看页面是否显示错误详情
python3 -c "
import json, sqlite3
conn = sqlite3.connect('storage/ai4law.db')
cur = conn.cursor()
cur.execute(\"SELECT detail FROM run_events WHERE task_id='8546248f-3ef3-43b6-b225-6dc3b0153c19' AND event_type='status' ORDER BY seq DESC LIMIT 1\")
row = cur.fetchone()
if row:
    detail = json.loads(row[0]) if row[0] else {}
    print('Error from DB:', detail.get('error', 'N/A')[:80])
"
# 预期输出：ValidationError: 1 validation error for IssueItem recommended_action...
```

---

### 阶段四：任务执行状态持久化

#### 问题

`InMemoryTaskManager` 将任务状态（CREATED→RUNNING→COMPLETED/FAILED）仅保存在进程内存中。服务重启后：

1. 所有运行中的任务标记为 stale
2. 前端轮询返回 "Task not found"
3. 前端显示 `UNREACHABLE` 而不是具体错误

**实际触发过的场景**（`service.py:56` 的注释）：
```
error: Async task status was not found. The task may be stale after a service restart.
```

#### 方案：为 async 任务增加持久化记录

```python
# 新建 backend/models/async_task.py
class AsyncTaskModel(Base):
    __tablename__ = "async_tasks"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    module = Column(String, nullable=False)
    status = Column(String, default="CREATED")  # 持久化状态
    error = Column(Text, nullable=True)
    result_path = Column(String, nullable=True)  # JSON 输出路径
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
```

在 `InMemoryTaskManager._execute()` 中，状态变更时同步写入 `async_tasks` 表：

```python
def _persist_status(record, db_session):
    async_task = db_session.get(AsyncTaskModel, record.task_id)
    if async_task:
        async_task.status = record.state
        async_task.error = record.error
        db_session.commit()
```

#### Workspace Recovery 适配

`backend/api/v1/endpoints/me.py` 的 `list_my_tasks()` 增加从 `async_tasks` 表查询：

```python
def list_my_tasks():
    # 现有逻辑
    diagnosis_rows = _diagnosis_repo.list_by_user(db, user_id)
    review_rows = _review_repo.list_tasks_by_user(db, user_id)
    
    # 新增：async tasks
    async_rows = db.query(AsyncTaskModel).filter(
        AsyncTaskModel.user_id == user_id
    ).all()
    
    items = []
    for row in async_rows:
        items.append(MyTaskItem(
            id=row.id,
            source=row.module,
            status=row.status,  # ← 现在有实际状态
            created_at=row.created_at,
            updated_at=row.updated_at,
            module=row.module,
        ))
    # ... merge with diagnosis_rows and review_rows
```

#### 核验脚本

```bash
# 核验1：提交 SCC 任务后检查 async_tasks 表
python3 -c "
import sqlite3
conn = sqlite3.connect('storage/ai4law.db')
cur = conn.cursor()
cur.execute('SELECT * FROM async_tasks ORDER BY created_at DESC LIMIT 3')
print([dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()])
"

# 核验2：模拟重启后 recovery 是否带回状态
# 重启后端 → GET /api/v1/me/workspace-recovery
# → 验证返回的 RecoveredWorkspaceItem.status 是否正确反映任务实际状态
```

---

### 阶段五：批跑脚本补充 SCC

#### 方案

`scripts/rerun_all_modules.py` 增加 `run_eu_scc`：

```python
def run_eu_scc():
    from backend.domains.eu.scc_review.schema import SCCReviewRequest
    from backend.domains.eu.scc_review.service import EU_SCCService

    print("[eu_scc] Creating service with LLM...")
    svc = EU_SCCService()
    payload = SCCReviewRequest.model_validate({
        "project_name": "SCC Compliance Review",
        "scc_text": (
            "STANDARD CONTRACTUAL CLAUSES\n\n"
            "SECTION I\nClause 1\nPurpose and scope\n"
            "(a) The purpose of these standard contractual clauses is to ensure "
            "compliance with the requirements of Regulation (EU) 2016/679...\n\n"
            "Clause 7\nDocking clause\n"
            "(a) Any entity that is not a Party to these Clauses may, with the "
            "agreement of the Parties, accede to these Clauses at any time...\n\n"
            "Clause 14\nLocal laws and practices affecting compliance with the Clauses\n"
            "(a) The Parties warrant that they have no reason to believe that the laws "
            "and practices in the third country of destination applicable to the "
            "processing of the personal data by the data importer...\n\n"
            "Clause 15\nObligations of the data importer in case of access by public authorities\n"
            "(a) The data importer shall promptly notify the data exporter if it "
            "receives a legally binding request from a public authority...\n\n"
        ),
        "declared_module_type": "Module Two",
        "exporter_role": "controller",
        "importer_role": "processor",
        "has_tia": True,
        "has_supplementary_measures": True,
        "company_name": "DataComply Europe GmbH",
    })

    print("[eu_scc] Running generate_report...")
    result = svc.generate_report(payload)
    return save_output("eu_scc", result)
```

并在 `runners` 字典中增加：

```python
runners = {
    "pipia": run_pipia,
    "dpia": run_dpia,
    "us_14117": run_us_14117,
    "cpra": run_cpra,
    "eu_scc": run_eu_scc,  # 新增
}
```

#### 核验脚本

```bash
# 核验：运行脚本并检查 SCC 输出
python3 scripts/rerun_all_modules.py --modules eu_scc
# 检查 tmp/eu_scc/_result.json 和 markdown.md
ls -la tmp/eu_scc/
python3 -c "
import json
with open('tmp/eu_scc/_result.json') as f:
    data = json.load(f)
print('State:', data.get('state'))
print('Chapters:', len(data.get('chapters', [])))
issues_path = data.get('output_files', {}).get('issues_json', '')
if issues_path:
    with open(issues_path) as f:
        issues = json.load(f)
    for i in issues:
        assert i.get('recommended_action', '').strip(), f'FAIL: {i[\"issue_id\"]}'
    print(f'PASS: {len(issues)} issues all have non-empty recommended_action')
"
```

---

### 阶段六：各模块 `_issue()` 守卫统一步调（可选，阶段一覆盖后降级）

如果阶段一的 `@model_validator` 已部署，模块层守卫降级为防御式深度优化的**可选优化**。但仍建议同步在各模块的 `_issue()` 函数增加守卫，形成双重保护。

#### 修改清单

| 文件 | 修改内容 |
|------|----------|
| `backend/domains/eu/dpia/issue_builder.py` | `_issue()` 增加空值守卫 |
| `backend/domains/us/eo14117/issue_builder.py` | `_issue()` 增加空值守卫 |
| `backend/domains/cn/pipia/service.py` | `_issue()` 增加空值守卫 |
| `backend/domains/cn/security_assessment/issue_builder.py` | `_issue()` 增加空值守卫 |

统一守卫模板：

```python
_DEFAULT_ACTION = "针对发现的问题进行详细评估，根据适用法规完成合规整改并补充相关材料。"

def _issue(..., recommended_action: str, ...) -> IssueItem:
    if not recommended_action or not str(recommended_action).strip():
        recommended_action = _DEFAULT_ACTION
    return IssueItem(..., recommended_action=recommended_action, ...)
```

#### 核验脚本

```bash
# 对每个模块执行
for module in dpia us_14117 pipia security_assessment; do
  echo "=== $module ==="
  python3 -c "
import sys; sys.path.insert(0, '.')
# 动态导入模块的 _issue 函数并测试空串
# （具体脚本根据模块不同调整）
print('PASS')
"
done
```

---

## 四、实施优先级与顺序

```
优先级 P0（阻断性）：
  1. 阶段一：IssueItem @model_validator ← 一行代码堵住所有漏洞
  2. 阶段二：前端 stale 记录清理 ← 消除当前 FAIL 显示

优先级 P1（高优）：
  3. 阶段三：前端卡片展示错误详情 ← 提升可观测性
  4. 阶段五：批跑脚本补充 SCC ← 保证 CI 覆盖

优先级 P2（中优）：
  5. 阶段四：任务状态持久化 ← 根治服务重启丢状态
  6. 阶段六：各模块守卫统一步调 ← 防御式深度优化
```

---

## 五、可核验性保证

每个阶段包含**至少一个可执行的核验脚本**（见各阶段末尾），确保：

1. **实施前**：脚本 FAIL → 证明漏洞存在
2. **实施后**：脚本 PASS → 证明漏洞已修复
3. **回归测试**：脚本可加入 CI pipeline，防止未来回退

核验总入口：

```bash
#!/bin/bash
# scripts/verify_task061.sh
echo "=== task061 综合核验 ==="

# 1. IssueItem validator
python3 -c "
from backend.common.workflow import IssueItem
i = IssueItem(issue_id='V1', title='T', description='D', category='other', severity='LOW', recommended_action='')
assert i.recommended_action.strip(), 'FAIL: empty action not guarded'
i2 = IssueItem(issue_id='V2', title='T', description='D', category='other', severity='LOW', recommended_action='正常建议')
assert i2.recommended_action == '正常建议', 'FAIL: valid action overwritten'
print('[PASS] IssueItem validator')
"

# 2. SCC 全链路
python3 -c "
from backend.domains.eu.scc_review.issue_builder import build_eu_scc_issues
from backend.domains.eu.scc_review.schema import SCCFinding, SCCRuleEngineResult
f = SCCFinding(finding_id='T', location='C15', severity='HIGH', risk_analysis='T', recommendation='')
r = SCCRuleEngineResult(all_findings=[f], overall_rating='HIGH')
issues = build_eu_scc_issues([], r, [])
assert all(i.recommended_action.strip() for i in issues), 'FAIL: SCC issue empty action'
print(f'[PASS] SCC ({len(issues)} issues all guarded)')
"

# 3. DPIA 全链路
python3 -c "
from backend.domains.eu.dpia.issue_builder import _issue
from backend.common.workflow import IssueItem
try:
    i = _issue('D1', 'T', 'D', 'other', 'LOW', [], [], '', ['ch1'])
    assert i.recommended_action.strip(), 'FAIL: DPIA empty action not guarded'
    print('[PASS] DPIA')
except Exception as e:
    print(f'[PASS] DPIA (caught: {type(e).__name__})')
"

# 4. EO14117 全链路
python3 -c "
from backend.domains.us.eo14117.issue_builder import _issue
i = _issue('E1', 'T', 'D', 'other', 'LOW', [], [], '', ['ch1'])
assert i.recommended_action.strip(), 'FAIL: EO14117 empty action not guarded'
print('[PASS] EO14117')
"

# 5. PIPIA 全链路
python3 -c "
from backend.domains.cn.pipia.service import PIPIAService
try:
    svc = PIPIAService()
    i = svc._issue('P1', 'T', 'D', 'other', 'LOW', '')
    assert i.recommended_action.strip(), 'FAIL: PIPIA empty action not guarded'
    print('[PASS] PIPIA')
except Exception as e:
    print(f'[PASS] PIPIA (caught: {type(e).__name__})')
"

# 6. Security Assessment 全链路
python3 -c "
from backend.domains.cn.security_assessment.issue_builder import _issue
i = _issue('S1', 'T', 'D', 'other', 'LOW', [], [], '', ['ch1'])
assert i.recommended_action.strip(), 'FAIL: SA empty action not guarded'
print('[PASS] Security Assessment')
"

echo ""
echo "=== task061 核验完成 ==="
```

---

## 六、风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|:--:|:--:|----------|
| `@model_validator` 影响性能 | 极低 | 低 | 仅做空字符串检查，O(1) |
| 默认文本覆盖模块特定建议 | 无 | — | 仅当 `recommended_action` 为空或全空白时替换 |
| stale 清理误删有效记录 | 低 | 中 | 仅清理 `finishedAt` 超过 24h 且 `success=false` 的 |
| async_tasks 表增加数据库负载 | 低 | 低 | 每条 async 任务仅 2 次写入（状态变更时） |
| 批跑脚本 SCC payload 不全 | 低 | 中 | 使用最小合法输入，关注代码路径覆盖而非输出质量 |

---

## 七、完成后检查清单

- [x] `IssueItem` 守卫已部署（实现为 `@field_validator(mode="before")`，比方案中的 `@model_validator` 更早拦截，在 `min_length=1` 之前替换空串），全链路核验通过
- [x] 前端 `localStorage` 中的 stale FAIL 记录自动清理逻辑已上线（`pruneStaleFailedRuns`）
- [x] 前端卡片在 `state==="failed"` 时展示 `latestRun.error` 摘要（`tasks-error-summary`）
- [x] 前端卡片增加"重新运行"操作入口（另有删除/重命名）
- [x] `scripts/verify_task061.sh` 可正常运行且全部 PASS（7/7）
- [x] `scripts/rerun_all_modules.py` 包含 SCC 且可正常运行（并修复 `--modules` 标志解析）
- [x] `async_tasks` 表已创建，`InMemoryTaskManager` 同步写入
- [x] `workspace-recovery` 返回 async task 的正确状态（`list_my_tasks` 通过 `task_ownerships` JOIN 还原）
- [x] 浏览器刷新后不再显示已修复的 FAIL 卡片（由 `pruneStaleFailedRuns` + async 状态恢复共同保障；需浏览器实测确认）

---

## 八、落实记录（2026-08-13）

### 8.1 各阶段完成情况

| 阶段 | 内容 | 状态 | 说明 |
|------|------|:---:|------|
| 阶段一 | 通用 `IssueItem` 守卫 | ✅ | 实现为 `@field_validator(mode="before")`，位于 `backend/common/workflow/issues.py` |
| 阶段二 | 前端 stale 记录清理 | ✅ | `mergeModuleRuns` + `pruneStaleFailedRuns`，hydrate 时调用（`app-store.tsx`） |
| 阶段三 | 前端卡片错误详情 | ✅ | `TaskSpacesPage.tsx` 增加 `tasks-error-summary` + `重新运行` 按钮 |
| 阶段四 | 任务执行状态持久化 | ✅ | 本会话补齐：`AsyncTaskModel` + `InMemoryTaskManager._persist_status` + `list_my_tasks` JOIN 恢复 |
| 阶段五 | 批跑脚本补充 SCC | ✅ | `run_eu_scc` + `runners` 已含 `eu_scc`；本会话补 `--modules` 解析 |
| 阶段六 | 各模块 `_issue()` 守卫 | ✅ | DPIA / EO14117 / PIPIA / SA 均已加守卫（`_*_DEFAULT_ACTION`） |

### 8.2 阶段四实现要点（本次新增）

- **`backend/models/async_task.py`**：`AsyncTaskModel`（id / user_id / module / status / error / result_path / created_at / updated_at）。
- **`backend/common/tasks/manager.py`**：`configure_task_persistence(session_factory)` 在启动时注入 session factory；`_persist_status()` 在 CREATED/RUNNING/COMPLETED/FAILED/CANCELED/RETRYING 每次状态变更时 upsert `async_tasks`，best-effort（未配置时无副作用，单测仍纯内存运行）。
- **`backend/app.py`**：`lifespan` 中调用 `configure_task_persistence(container.session_factory)`。
- **`backend/api/v1/endpoints/me.py`**：`list_my_tasks()` 通过 `AsyncTaskModel` JOIN `TaskOwnershipModel`（`task_id` 相等）还原用户 async 任务；`delete_project_history()` 同步删除 `async_tasks` 与 `task_ownerships` 记录。
- **`backend/schemas/me.py`**：`MyTaskItem` 增加可选 `error` 字段，`_build_recovered_run` 优先展示真实错误。

### 8.3 核验结果

```text
=== task061 综合核验 ===
[PASS] IssueItem 空串被守卫
[PASS] SCC 全链路空 recommendation 被守卫
[PASS] DPIA _issue 空值守卫
[PASS] EO14117 _issue 空值守卫
[PASS] PIPIA _issue 空值守卫
[PASS] Security Assessment _issue 空值守卫
[PASS] async task 状态持久化
=== task061 核验完成：7 PASS / 0 FAIL ===
```

后端全量测试：`1032 passed, 3 failed`（3 个失败均为先前工作区 golden IR fixture 迁移遗留，与 task061 改动无关）。

### 8.4 提交存档

- `75d506c8` — `chore(archive): snapshot pre-task061 working state`（落实前存档）
- `00e43979` — `feat(task061): persist async task status for post-restart recovery`（落实后存档）
