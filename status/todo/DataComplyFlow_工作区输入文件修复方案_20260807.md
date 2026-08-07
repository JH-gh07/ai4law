# DataComplyFlow 工作区输入文件"找不到"与"冗余"修复方案

> 文档性质：待实施技术方案（TODO）
> 编制日期：2026-08-07
> 方案版本：v1
> 适用分支：`new`
> 问题来源：工作台 ResourcePanel 点击输入文件时报 403/404，且"已提交材料"列表随运行次数不断膨胀
> 关联方案：`status/todo/DataComplyFlow_输出与资料冗余治理方案_20260806.md`（输出侧冗余治理）

---

## 一、问题诊断

### 1.1 两个症状

| 症状 | 用户感知 | 触发条件 |
|------|---------|---------|
| **找不到文件** | 工作台左侧"已提交材料"点击某个文件 → 加载旋转 → 报错 403 或 404 | 始终触发（100% 复现） |
| **文件冗余** | "已提交材料"下存在大量重复或已无意义的条目；表单入口随运行次数累积 | 同 task 下多次运行后 |

### 1.2 涉及的完整代码链路

```
用户上传文件 → POST /api/v0/files/upload → 写磁盘 → 返回 path
    → 前端 ModuleRunPanel:uploadFiles() 收集 paths
    → payload-builders/cn.ts|eu.ts|us.ts 把 paths 嵌入 request payload
    → 前端 WorkspaceShell:onRunDone() 把整个 request 存入 zustand state (app-store)
    → ResourcePanel:collectInputResources() 递归扫描 state 中所有 run.request
    → ResourcePanel:inputEntries useMemo 生成左侧文件树列表
    → 用户点击某个文件
    → WorkspaceShell:handleOpenResource() 发起 GET /api/v1/artifacts/preview?path=xxx
    → artifacts.py:_resolve_artifact_path() 路径解析 + 安全检查
    → artifacts.py:_assert_artifact_access() 数据库权限验证
    → ❌ 403/404 报错
```

---

## 二、根因分析

### 2.1 "找不到文件"的两个根因

#### 根因 A：上传未写 DB → `_assert_artifact_access()` 查不到记录

**代码位置：**
- 上传：`backend/api/v0/task_gateway/service.py:80-96`（`upload_file`）
- 验证：`backend/api/v1/endpoints/artifacts.py:59-73`（`_assert_artifact_access`）
- DB 模型：`backend/models/review.py:28-38`（`UploadedFileModel`）

**现状事实链：**

```python
# service.py:80-96 — upload_file() 做了以下操作：
def upload_file(self, upload: UploadFile):
    # 1. 写磁盘 ✅
    out_path = self.upload_dir / safe_name
    out_path.write_bytes(payload)
    # 2. 存内存字典 ⚠️
    with self._lock:
        self._file_index[file_id] = out_path  # ← 进程内内存，重启即丢失
    # 3. 返回路径给前端
    return V0UploadedFileData(path=str(out_path))
    # ❌ 没有写 UploadedFileModel DB 记录
```

```python
# artifacts.py:59-73 — _assert_artifact_access() 查 DB：
def _assert_artifact_access(db, user, resolved):
    upload_stmt = select(UploadedFileModel.id).where(
        UploadedFileModel.user_id == user.id,
        UploadedFileModel.storage_path.in_(candidate_paths),  # ← 需要 DB 里有记录
    )
    upload_hit = db.execute(upload_stmt).scalar_one_or_none()
    # ❌ 因为 upload_file() 没写 DB，这里永远返回 None
    if not upload_hit and not report_hit:
        raise HTTPException(status_code=403, detail="You do not have access...")
```

**结论：** `UploadedFileModel` 表结构已完备（`backend/models/review.py:28-38`），包含 `id`, `user_id`, `task_id`, `filename`, `content_type`, `storage_path`, `extracted_text`, `created_at`——但写入端（`upload_file`）没有使用它。验证端（`_assert_artifact_access`）在查询它。两端的 gap 就是 403 的来源。

#### 根因 B：`_candidate_artifact_paths` 的路径匹配问题

**代码位置：** `backend/api/v1/endpoints/artifacts.py:44-56`

```python
def _candidate_artifact_paths(resolved: Path) -> set[str]:
    candidates = {str(resolved), resolved.as_posix()}      # 绝对路径 POSIX 和 native 两种
    cwd = Path.cwd().resolve()
    try:
        relative = resolved.relative_to(cwd)
    except ValueError:
        relative = None
    if relative is not None:
        relative_posix = relative.as_posix()
        candidates.update({str(relative), relative_posix, f"./{relative_posix}"})
    return candidates
```

`upload_file` 返回的 path 是通过 `str(out_path)`（即 `out_path` 的 native 表示），而 `out_path` 由 `self.upload_dir / safe_name` 拼接。如果 `self.upload_dir` 是相对路径 `storage/uploads`（第 77 行），那么 `out_path` 解析为 CWD 下的 `storage/uploads/f_xxx.pdf`。这个路径的 `str()` 和 `.as_posix()` 表示不同（macOS 上相同，但 Linux 上不同），但都在 `candidate_paths` 中生成。**这不是 404 的根因**，但它是 `_candidate_artifact_paths` 生成多达 5 种路径变体却仍未匹配的理由——问题出在 DB 里根本没有记录，不是路径匹配问题。

#### 根因 C：临时文件被清理 → 404

`upload_file()` 写的磁盘路径是 `storage/uploads/f_xxx.pdf`。如果运维清理了这个目录下的过期文件，或服务重启后 `self.upload_dir` 指向不同位置，文件在磁盘上不存在时，`_resolve_artifact_path()` 直接返回 404。这是一条**次要**但现实存在的路径，因为临时上传文件的持久化策略从未明确定义。

### 2.2 "冗余"的四个根因

#### 根因 D：表单入口按 run 逐条累积

**代码位置：** `frontend/src/components/workspace/ResourcePanel.tsx:399-406`

```typescript
sortedRuns.forEach((run, index) => {
  entries.push({
    id: `input-form-${run.id}`,
    name: pickUniqueName(buildFormEntryName(index, lang)),  // ← "基础信息表单（第1次）"
    kind: "form",
    payload: run.request,
    createdAt: run.startedAt
  });
  // ...
});
```

**问题：** 每次 `ModuleRun` 记录都是独立的——即便是同一个 Task 下、用完全相同的输入参数重新提交。`state.moduleRuns` 不做 run 级别的合并或去重（这是对的——每次运行都应该被记录），但 ResourcePanel 把它当作"需要展示的条目"逐条列出，这就是错的。

公式：运行 N 次 → "已提交材料"下至少有 N 条"基础信息表单（第X次）" + N 次上传文件的并集。

#### 根因 E：`collectInputResources` 全量递归扫描

**代码位置：** `frontend/src/components/workspace/ResourcePanel.tsx:245-295`

```typescript
function collectInputResources(value: unknown, bag: Map<...>, lang, keyHint?) {
  if (typeof value === "string") {
    if (looksLikeFilePath(value)) { bag.set(value, ...) }
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item) => collectInputResources(item, bag, lang, keyHint));
    return;
  }
  if (isRecord(value)) {
    // 找 storage_uri / path / file_path
    const maybePath = value.storage_uri ?? value.path ?? value.file_path;
    // ...
    // 然后递归这个对象的所有字段 ↓
    Object.entries(value).forEach(([key, nested]) => {
      collectInputResources(nested, bag, lang, key);  // ← 递归全量！
    });
  }
}
```

**问题：** 诊断（diagnosis）的 `answers` 对象有 60+ 个字段。`company_name` 的值 "智造未来科技有限公司" 被递归扫描（不带扩展名、不包含斜杠，不匹配 `looksLikeFilePath`——侥幸不触发）。但如果某个字段的值碰巧包含 `.json`、`.md` 等扩展名（比如 "请补充 .json 格式的数据清单"），就会被误判为文件路径。

根本问题不是误判（目前未发生），而是**不必要的 O(n) 全量递归**——对一个大 payload 来说，99.9% 的字段都不是文件路径，但都被遍历了。

#### 根因 F：`looksLikeFilePath` 正则过于宽松

**代码位置：** `frontend/src/components/workspace/ResourcePanel.tsx:137-146`

```typescript
const hasFileExtension = (value: string): boolean =>
  /\.(docx?|pdf|md|html|txt|csv|xlsx?|png|jpg|jpeg|json)$/i.test(value);

const looksLikeFilePath = (value: string): boolean => {
  if (!trimmed) return false;
  if (hasFileExtension(trimmed)) return true;           // 任何带这些扩展名的都算
  if (/^(storage\/|outputs\/|uploads\/|\/|[a-zA-Z]:\\)/.test(trimmed)) return true;
  if (/[\\/]/.test(trimmed) && !/\s\/\s/.test(trimmed)) return true;
  return false;
};
```

**问题：**
1. `hasFileExtension` 只用正则后缀匹配——"这是一份 .pdf 报告" 会被误判为文件路径
2. "任何包含 `/` 或 `\` 的字符串" 过于宽泛——`"Q: yes/no, 路径: 未确认"` 不会被触发（因为 `\s\/\s` 排除），但 `"uploads/缺省路径"` 会被匹配
3. 没有做"这个路径是否真的存在于 `uploaded_files` 数组中"的二次确认

#### 根因 G：输入文件用输出文件做"排除过滤器" → 类别混淆

**代码位置：** `frontend/src/components/workspace/ResourcePanel.tsx:410-411`

```typescript
Array.from(bag.values())
  .filter((item) => !outputFiles.some((file) => file.path === item.path))
  // ↑ 逻辑是"不在 output 里 → 就是 input"
```

这是**逆向定义**——输入文件的身份不来自"这是什么"，而来自"这不是什么"。如果某条路径同时出现在 input 和 output 中（例如中间文件），在 input 侧会被过滤掉，用户看不到它。

---

## 三、修复方案

### 3.1 修复策略概述

| 修复项 | 优先级 | 类型 | 影响范围 |
|--------|--------|------|---------|
| P0-A: upload 写 DB | P0 | 后端补齐 | `service.py` + 依赖注入 |
| P1-B: ResourcePanel 表单去重 | P1 | 前端重构 | `ResourcePanel.tsx` |
| P1-C: collectInputResources 白名单 | P1 | 前端重构 | `ResourcePanel.tsx` |
| P2-D: looksLikeFilePath 收紧 | P2 | 前端加固 | `ResourcePanel.tsx` |
| P2-E: 输入正向定义 | P2 | 前端重构 | `ResourcePanel.tsx` |
| P3-F: 前端按 run 折叠/归档 | P3 | 前端 UX | `ResourcePanel.tsx` |

### 3.2 P0-A：上传时写入 `UploadedFileModel` DB 记录

**这是"找不到文件"的唯一根治方案。完成此修复后，所有输入文件点击可正常预览。**

#### 3.2.1 需要改什么

**文件：** `backend/api/v0/task_gateway/service.py`

`V0TaskGatewayService` 当前构造函数不持有数据库 session。需要两种方式之一：

**方案 A（推荐——最小改动）：** 在 `upload_file` 方法签名中接受 `user_id` 参数，调用方（router）传入。在 `upload_file` 内部使用独立的 DB session 写入。

```python
# service.py 改动点

def __init__(self, ..., db_session_factory=None):
    # 新增：接受 session factory 用于 upload_file 写入 DB
    self._db_session_factory = db_session_factory or _default_session_factory

def upload_file(self, upload: UploadFile, user_id: str = "") -> V0UploadedFileData:
    original_name = Path(upload.filename or "uploaded.bin").name
    file_id = f"f_{uuid.uuid4().hex[:16]}"
    safe_name = f"{file_id}_{original_name}"
    out_path = self.upload_dir / safe_name
    payload = upload.file.read()
    out_path.write_bytes(payload)
    with self._lock:
        self._file_index[file_id] = out_path

    # ===== 新增：写入 UploadedFileModel DB =====
    storage_path_str = str(out_path.resolve())  # 统一为绝对路径
    try:
        from backend.models.review import UploadedFileModel
        from backend.core.dependencies import get_db_context
        with get_db_context() as db:
            db.add(UploadedFileModel(
                user_id=user_id,
                task_id="",  # upload 时不绑定 task，create_task 时回填
                filename=original_name,
                content_type=upload.content_type or "application/octet-stream",
                storage_path=storage_path_str,
                created_at=datetime.now(timezone.utc),
            ))
            db.commit()
    except Exception:
        # 写 DB 失败不应阻断上传——文件已在磁盘，预览降级为 download 模式
        pass
    # =============================================

    return V0UploadedFileData(
        file_id=file_id,
        file_name=original_name,
        mime=upload.content_type or "application/octet-stream",
        size=len(payload),
        path=storage_path_str,   # ← 返回绝对路径，与 DB 中 storage_path 一致
        uploaded_at=datetime.now(timezone.utc),
    )
```

**文件：** `backend/api/v0/task_gateway/router.py`

```python
# router.py 改动点

@router.post("/files/upload", response_model=APIEnvelope)
def upload_file(
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(get_current_user),  # ← 新增：获取用户
) -> APIEnvelope:
    uploaded = service.upload_file(file, user_id=current_user.id)
    return APIEnvelope(data=uploaded.dict())
```

#### 3.2.2 改动影响分析

- **前向兼容：** `user_id=""` 时写 DB 仍然执行，只是 `user_id` 字段为空字符串，`_assert_artifact_access()` 中 `user_id == user.id` 匹配不到（老数据不自动修复，但新上传的文件可以）
- **性能影响：** 每次上传多一次 INSERT，可忽略（上传本身涉及磁盘 IO，远大于 DB 写入）
- **回滚安全性：** 上传成功但 DB 写入失败 → 文件在磁盘上存在但无法通过 artifacts API 预览 → 降级为 download-only 体验（比当前完全不可用的状态好）
- **需要同时修复的配套：** `V0UploadedFileData.path` 字段当前是 `str(out_path)`（可能是相对路径），改为 `str(out_path.resolve())` 确保与 DB 中 `storage_path` 使用相同的路径表示

#### 3.2.3 测试覆盖

```python
# backend/api/v1/tests/test_artifacts_access.py 
# 新增：上传 → 预览 的端到端测试

def test_upload_then_preview_input_file(client, auth_headers, test_file):
    """上传文件后，通过 artifacts preview API 可以正常预览"""
    # 1. 上传
    resp = client.post("/api/v0/files/upload", files={"file": test_file}, headers=auth_headers)
    assert resp.status_code == 200
    path = resp.json()["data"]["path"]
    
    # 2. 预览
    resp = client.get(f"/api/v1/artifacts/preview?path={quote(path)}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["render_mode"] in ("text", "download")
```

### 3.3 P1-B：ResourcePanel 表单入口按内容指纹去重

**代码位置：** `frontend/src/components/workspace/ResourcePanel.tsx:387-426`

#### 修改目标

将"每次 run 加一条 form entry"改为"相同内容的 form 只显示一次"。

#### 具体改动

```typescript
// 新增：计算表单内容指纹
const hashFormInput = (request: unknown): string => {
  try {
    // 对 request 做确定性序列化后取 SHA-256 前 16 位
    const normalized = JSON.stringify(request, Object.keys(request as object).sort());
    return normalized.length.toString(36) + "-" + 
           Array.from(normalized).reduce((h, c) => (h * 31 + c.charCodeAt(0)) & 0xffff, 0).toString(36);
  } catch {
    return `form-${Date.now()}`;
  }
};

// 修改后的 inputEntries useMemo
const inputEntries = useMemo<InputEntry[]>(() => {
  const sortedRuns = [...relatedRuns].sort((a, b) => (a.startedAt < b.startedAt ? 1 : -1));
  const entries: InputEntry[] = [];
  const usedNames = new Map<string, number>();
  const seenPaths = new Set<string>();
  const seenFormHashes = new Map<string, number>();  // ← 新增：表单指纹 → 出现次数

  const pickUniqueName = (baseName: string): string => {
    const count = (usedNames.get(baseName) ?? 0) + 1;
    usedNames.set(baseName, count);
    return count === 1 ? baseName : `${baseName} (${count})`;
  };

  sortedRuns.forEach((run, _index) => {
    // ===== 修改：表单入口按指纹去重 =====
    const formHash = hashFormInput(run.request);
    const seenCount = seenFormHashes.get(formHash) ?? 0;
    seenFormHashes.set(formHash, seenCount + 1);
    
    if (seenCount === 0) {
      // 第一次出现：显示
      entries.push({
        id: `input-form-${formHash}`,
        name: pickUniqueName(buildFormEntryName(entries.filter(e => e.kind === "form").length, lang)),
        kind: "form",
        payload: run.request,
        createdAt: run.startedAt
      });
    }
    // 如果 seenCount > 0：跳过（相同内容的表单已有一条）
    // ==========================================

    const bag = new Map<string, InputResourceCandidate>();
    collectInputResources(run.request, bag, lang);
    Array.from(bag.values())
      .filter((item) => !outputFiles.some((file) => file.path === item.path))
      .forEach((item) => {
        if (seenPaths.has(item.path)) return;
        seenPaths.add(item.path);
        entries.push({
          id: `input-file-${item.path}`,
          name: pickUniqueName(buildDisplayNameFromPath(item.path, item.labelHint, lang)),
          kind: "file",
          sourcePath: item.path,
          createdAt: run.startedAt
        });
      });
  });

  return entries;
}, [lang, outputFiles, relatedRuns]);
```

#### 设计选择说明

- **为什么不直接去重所有 run？** run 的去重是正确的需求——每次都记录。问题在 ResourcePanel 的"展示侧"。不去改 store，改展示侧。
- **为什么用 hash 而非值比较？** 同一 task 下多次用相同参数提交是常见场景（调试、重试），hash 比较可避免 JSON.stringify 的 60+ 字段逐项对比。
- **去重后历史记录还在吗？** 在数据库和 state 中都在。只是在左侧面板不再重复展示。用户仍然可以通过"时间线" tab 看到每次运行。这是"展示精简"而非"数据删除"。

### 3.4 P1-C：`collectInputResources` 改为白名单字段扫描

**代码位置：** `frontend/src/components/workspace/ResourcePanel.tsx:245-295`

#### 修改目标

不再递归遍历整个 `request` JSON，而是只扫描已知的文件字段。

#### 具体改动

```typescript
// 定义每个模块已知的文件路径字段
const MODULE_FILE_FIELDS: Record<string, string[]> = {
  assessment: ["uploaded_files"],
  pipia: ["attachments"],           // attachments[].storage_uri
  review: ["uploaded_files"],
  cn_flow: ["attachments", "data_inventory", "entity_inventory"],  // attachments[].storage_uri
  eu_scc: ["uploaded_files"],
  bcr: ["uploaded_files"],
  dpia: ["uploaded_files"],
  tia: ["uploaded_files"],
  us_14117: ["attachments"],        // attachments[{path}]
  cpra: ["attachments"],            // attachments[{storage_uri, file_path}]
};

function extractPathsFromField(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) {
    // 数组元素可能是纯路径字符串或对象（含 storage_uri/path/file_path）
    return value.flatMap((item) => {
      if (typeof item === "string") return [item];
      if (isRecord(item)) {
        const p = item.storage_uri ?? item.path ?? item.file_path;
        return typeof p === "string" ? [p] : [];
      }
      return [];
    });
  }
  return [];
}

function collectInputResources(
  module: string,         // ← 新增：模块标识
  request: unknown,
  bag: Map<string, InputResourceCandidate>,
  lang: "zh" | "en",
) {
  if (!isRecord(request)) return;
  
  const fields = MODULE_FILE_FIELDS[module] ?? [];
  for (const field of fields) {
    const value = request[field];
    if (value === undefined || value === null) continue;
    for (const path of extractPathsFromField(value)) {
      if (!looksLikeFilePath(path)) continue;
      const existing = bag.get(path);
      bag.set(path, {
        path,
        labelHint: existing?.labelHint ?? inferLabelHint(path, field, lang),
      });
    }
  }
}
```

调用处修改（`ResourcePanel.tsx:408-409`）：
```typescript
// 之前：
collectInputResources(run.request, bag, lang);

// 之后：
collectInputResources(run.module, run.request, bag, lang);
```

#### 为什么不用递归全量扫描

递归方案的初衷是"无论后端 payload 结构怎么变，前端都能自动发现文件路径"。但实际：
1. Payload 结构由 `payload-builders/*.ts` 严格控制，字段名可预知
2. 递归 60+ 字段的纯文本值没有意义（它们永远不会是文件路径）
3. 白名单语义更清晰：前端显式声明"这个模块有哪些文件字段"，新增模块时同步添加 → 这本身是健康的契约意识

### 3.5 P2-D：收紧 `looksLikeFilePath` 判断

**代码位置：** `frontend/src/components/workspace/ResourcePanel.tsx:137-146`

#### 修改目标

在 P1-C（白名单化）之后，`looksLikeFilePath` 不再需要处理"从任意文本中猜测文件路径"的场景，可以收紧为"文件扩展名 + 合理路径前缀"的组合判断。

```typescript
const hasFileExtension = (value: string): boolean =>
  /\.(docx?|pdf|md|html|txt|csv|xlsx?|png|jpg|jpeg|json)$/i.test(value);

const looksLikeFilePath = (value: string): boolean => {
  const trimmed = value.trim();
  if (!trimmed) return false;
  // 规则1: 以已知存储前缀开头（storage/ | outputs/ | uploads/）
  if (/^(storage\/|outputs\/|uploads\/|\/)/.test(trimmed)) return true;
  // 规则2: 有合法文件扩展名
  if (hasFileExtension(trimmed)) return true;
  // 规则3: 不再匹配"任意包含斜杠的字符串"
  return false;
};
```

### 3.6 P2-E：输入文件正向定义

**代码位置：** `frontend/src/components/workspace/ResourcePanel.tsx:410-411`

#### 问题

当前用 `!outputFiles.some(...)` 来判断"这是输入文件"——逻辑反转，且如果路径同时出现在两侧则输入侧隐藏。

#### 修改

在完成 P1-C（白名单扫描）后，`collectInputResources` 已经天然只扫描输入侧的已知字段。不再需要 `outputFiles` 做反向过滤。

```typescript
// 之前：
Array.from(bag.values())
  .filter((item) => !outputFiles.some((file) => file.path === item.path))

// 之后：直接使用，不做反向过滤
Array.from(bag.values())
```

### 3.7 P3-F（远期）：左侧面板按 run 折叠/归档

当同 task 下有多次历史运行时，可在输入文件列表展示"最新一次运行的文件（展开）+ N 次历史运行（折叠）"的交互模式。这属于 UX 优化，不阻塞功能。建议在 P1-B 上线后根据用户反馈决定是否实现。

---

## 四、实施计划

### 4.1 阶段划分

| 阶段 | 内容 | 预估工时 | 前置依赖 |
|------|------|---------|---------|
| **Phase 1（P0-A）** | upload_file 写 DB | 0.5d | 无 |
| **Phase 2（P1-B + P1-C）** | 表单去重 + 白名单扫描 | 1d | Phase 1 |
| **Phase 3（P2-D + P2-E）** | 正则收紧 + 正向定义 | 0.5d | Phase 2 |
| **Phase 4（测试 + 验证）** | 端到端测试 + 手动验证 | 0.5d | Phase 1-3 |

**总计：2.5 个工作日**

### 4.2 执行顺序

```
Day 1 上午: Phase 1 → 后端 upload_file 写 DB + router 传 user_id
Day 1 下午: Phase 1 验证 → 上传文件后用 artifacts API 验证 200
Day 2 上午: Phase 2 → ResourcePanel 表单去重 + collectInputResources 白名单化
Day 2 下午: Phase 3 → looksLikeFilePath 收紧 + 输出过滤移除
Day 3 上午: Phase 4 → 全链路测试 + 修复文档更新
```

### 4.3 验收标准

| 编号 | 标准 | 验证方式 |
|------|------|---------|
| A1 | 上传文件后，在 ResourcePanel 点击 → 不报 403/404 → 正常显示预览 | 手动：创建 task → 上传 → 跑一遍 → 回工作台点击输入文件 |
| A2 | 输入文件预览支持：纯文本（markdown/txt/json/csv）渲染、PDF 内嵌、不支持格式的 download 降级 | 手动：上传不同类型的文件验证 |
| B1 | 同 task 下用相同参数提交 3 次 → 左侧"已提交材料"只显示 1 条表单入口 | 单元测试 + 手动 |
| B2 | 同 task 下用不同参数提交 3 次 → 左侧显示 3 条不同的表单入口 | 单元测试 + 手动 |
| C1 | diagnosis 模块的 60+ answers 字段不再被递归扫描 | 代码审查：`collectInputResources` 不再接受 request 全文，只接受 module + 白名单字段 |
| D1 | 纯文本字段中含 `.pdf` 等字样不被误判为文件路径 | 单元测试 |
| E1 | 同时出现在 input 和 output 中的文件路径在 input 面板中可见 | 手动验证 |

---

## 五、风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| upload_file 写 DB 失败导致上传被阻断 | 低 | try/except 包裹 DB 写入，失败时降级为 download-only（不阻断上传） |
| hashFormInput 对复杂嵌套对象产生碰撞 | 低 | 使用完整 JSON.stringify + 累积 hash，碰撞概率可忽略 |
| 白名单遗漏了某个模块的文件字段 | 中 | `MODULE_FILE_FIELDS` 的初始值基于现有 6 个 payload builder 全部扫描得出（见下方附录），新增模块时在代码审查中强制检查 |
| 相对路径 vs 绝对路径不一致导致 DB 查不到 | 中 | `upload_file` 改为返回 `str(out_path.resolve())`（绝对路径），DB 中 `storage_path` 存相同值。同时在 `_candidate_artifact_paths` 中已有 `resolve()` 归一化逻辑 |
| ResourcePanel 重构后老数据不兼容 | 低 | 不修改 state schema，只修改展示逻辑。老 run 的 request 中 `uploaded_files` 字段依然存在且白名单支持 |

---

## 六、改动人天汇总

| 文件 | 改动行数 | 类型 |
|------|---------|------|
| `backend/api/v0/task_gateway/service.py` | ~25 行新增 | 后端 |
| `backend/api/v0/task_gateway/router.py` | ~3 行修改 | 后端 |
| `backend/api/v1/tests/test_artifacts_access.py` | ~20 行新增 | 测试 |
| `frontend/src/components/workspace/ResourcePanel.tsx` | ~60 行修改 / ~40 行删除 | 前端 |
| **总计** | **~148 行** | — |

---

## 附录

### A. 全部模块的 `uploaded_files` / `attachments` 字段速查

基于对 6 个 payload builder 源码的完整扫描：

| 模块 | 文件字段 | 路径存储方式 | Payload Builder |
|------|---------|-------------|-----------------|
| diagnosis | 无文件字段 | — | `cn.ts:buildDiagnosisPayload` |
| assessment | `uploaded_files: string[]` | 纯路径数组 | `cn.ts:buildAssessmentPayload:168` |
| pipia | `attachments: [{storage_uri, file_role, file_name, file_format}]` | 对象数组 | `cn.ts:buildPipiaPayload:225-230` |
| review | `uploaded_files: string[]` | 纯路径数组 | `cn.ts:buildDocumentReviewPayload:248` |
| cn_flow | `attachments: [{storage_uri, file_role, file_name, file_format}]` | 对象数组 | `cn.ts:buildCnFlowPayload:294-301` |
| eu_scc | `uploaded_files: string[]` | 纯路径数组 | `eu.ts:buildEuSccPayload:88` |
| bcr | `uploaded_files: string[]` | 纯路径数组 | `eu.ts:buildBcrPayload:136` |
| dpia | `uploaded_files: string[]` | 纯路径数组 | `eu.ts:buildDpiaPayload:246` |
| tia | `uploaded_files: string[]` | 纯路径数组 | `eu.ts:buildTiaPayload:?` |
| us_14117 | `attachments: string[]` | 纯路径数组 | `us.ts:buildUs14117Payload:54` |
| cpra | `attachments: [{storage_uri, file_role, ...}]` | 对象数组 | `us.ts:buildCpraPayload:96-106` |

### B. 完整文件位置速查

```
后端：
  backend/api/v0/task_gateway/service.py:80-96         ← upload_file 写磁盘
  backend/api/v0/task_gateway/service.py:246-248       ← _build_assessment_payload resolve uploaded_files
  backend/api/v0/task_gateway/service.py:340-345       ← CPRA _resolve_attachment_paths
  backend/api/v0/task_gateway/router.py:15-17          ← POST /files/upload 路由
  backend/api/v1/endpoints/artifacts.py:28-41           ← _resolve_artifact_path
  backend/api/v1/endpoints/artifacts.py:44-73           ← _candidate_artifact_paths + _assert_artifact_access
  backend/api/v1/endpoints/artifacts.py:76-151          ← preview / file / download handlers
  backend/models/review.py:28-38                        ← UploadedFileModel (DB)
  backend/api/v1/tests/test_artifacts_access.py         ← 现有 artifacts test

前端：
  frontend/src/components/workspace/ResourcePanel.tsx:137-146  ← looksLikeFilePath
  frontend/src/components/workspace/ResourcePanel.tsx:245-295  ← collectInputResources
  frontend/src/components/workspace/ResourcePanel.tsx:387-426  ← inputEntries useMemo
  frontend/src/components/workspace/ResourcePanel.tsx:537-580  ← 文件树渲染 + onClick
  frontend/src/components/workspace/WorkspaceShell.tsx:846-871 ← handleOpenResource
  frontend/src/components/workspace/WorkspaceShell.tsx:582-610 ← useEffect → fetchArtifactPreview
  frontend/src/components/workspace/ModuleRunPanel.tsx:502-509 ← uploadFiles
  frontend/src/api/artifacts.ts:13-20                          ← fetchArtifactPreview
  frontend/src/api/modules.ts:294-333                          ← uploadTaskFile
  frontend/src/features/module-runner/payload-builders/cn.ts   ← CN payload builders
  frontend/src/features/module-runner/payload-builders/eu.ts   ← EU payload builders
  frontend/src/features/module-runner/payload-builders/us.ts   ← US payload builders
```

### C. `_assert_artifact_access` 完整逻辑

```python
# artifacts.py:59-73
def _assert_artifact_access(db: Session, user: AuthUser, resolved: Path) -> None:
    # 生成 5 种路径变体（绝对路径 native、绝对路径 POSIX、相对路径、相对路径 POSIX、./相对路径）
    candidate_paths = tuple(_candidate_artifact_paths(resolved))
    
    # 查询1: ReportArtifactModel（后端生成的报告产物）
    report_stmt = select(ReportArtifactModel.id).where(
        ReportArtifactModel.user_id == user.id,
        ReportArtifactModel.file_path.in_(candidate_paths),
    )
    
    # 查询2: UploadedFileModel（用户上传的文件）← 这个表存在但从未被写入
    upload_stmt = select(UploadedFileModel.id).where(
        UploadedFileModel.user_id == user.id,
        UploadedFileModel.storage_path.in_(candidate_paths),
    )
    
    report_hit = db.execute(report_stmt).scalar_one_or_none()
    upload_hit = db.execute(upload_stmt).scalar_one_or_none()
    
    if report_hit or upload_hit:
        return  # ✅ 有权限
    raise HTTPException(status_code=403, detail="You do not have access to this artifact.")
```

### D. 根因追溯表

| 症状 | 直接原因 | 代码位置 | 根本原因 |
|------|---------|---------|---------|
| 点击输入文件 → 403 | `upload_hit` 为 None | `artifacts.py:71` | `service.py:80-96` 没写 DB |
| 点击输入文件 → 404 | 文件磁盘不存在 | `artifacts.py:32` | 临时文件无持久化策略 |
| 表单入口重复 N 条 | forEach run 不加去重 | `ResourcePanel.tsx:399` | 展示侧把 run 数量 = 条目数量 |
| 文件列表遍历整个 payload | 全文递归 | `ResourcePanel.tsx:293` | 设计选择了"自发现"而非"契约声明" |
| 文件路径无类别归属 | `!outputFiles.some()` | `ResourcePanel.tsx:411` | 输入身份靠反向排除而非正向声明 |
