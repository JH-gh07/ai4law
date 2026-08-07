# DataComplyFlow 工作区输入文件修复方案

> 文档性质：经代码链路复核的实施方案（v2，待实施）
> 编制日期：2026-08-07
> 代码基线：`new` 分支，审计提交 `0532ff6`；其后提交截至 `899b705` 未改动本文引用的 `backend/`、`frontend/` 链路
> 问题范围：工作区“已提交材料”中的输入文件身份、权限、预览、历史展示和生命周期
> 关联方案：`status/todo/DataComplyFlow_输出与资料冗余治理方案_20260806.md`

## 〇、核心结论

这不是一个“在上传时补一条 DB 记录”就能成熟解决的问题。当前设计把服务器文件路径同时当作：

- 上传结果的公开身份；
- 模块请求中的文件引用；
- 前端工作区的持久化数据；
- 预览 API 的查询参数；
- 输入/输出类别推断依据。

但上传端、模块运行端和预览端对这个路径的信任模型并不一致，因此产生 403/404、重启丢失、多进程不一致和工作区虚假文件条目。

成熟终态必须改为：

```text
稳定 file_id = 公开身份
DB owner/workspace binding = 授权事实
storage_path = 服务器私有实现细节
ModuleRun.inputFiles = 工作区输入文件的唯一展示来源
run history = 可折叠审计历史，不是应删除的“重复数据”
```

建议分两步交付：先在不破坏现有 10 个模块请求的前提下完成认证、权属登记和 ID 预览；再把模块契约从原始路径迁移到不透明文件引用。

## 一、当前事实链路

### 1.1 用户真实上传链路

```text
ModuleRunPanel.uploadFiles()
  → frontend uploadTaskFile()
  → POST /api/v0/files/upload（前端携带 Authorization，后端路由未消费）
  → V0TaskGatewayService.upload_file()
       ├─ 固定写入 CWD/storage/uploads
       ├─ 只写进程内 _file_index
       ├─ 不写所有权 DB 记录
       └─ 返回服务器 path
  → payload builder 把 path 写入 uploaded_files/attachments/storage_uri
  → WorkspaceShell 把整个 request 保存为 ModuleRun
  → app-store 同时持久到 localStorage 和 /api/v1/workspace-state
  → ResourcePanel 递归猜测 request 中的路径
  → GET /api/v1/artifacts/preview?path=...
  → 文件存在/允许根检查 + DB owner 检查
```

上传端没有写 `UploadedFileModel`，但预览端只接受归属于当前用户的 `UploadedFileModel` 或 `ReportArtifactModel`。对真实上传文件，这是 403 的直接条件。

### 1.2 开发预置文件是另一条 403 路径

开发加速模式会把 `resources/...` 和 `benchmarks/sample-inputs/...` 等仓库文件路径直接写入请求。`ResourcePanel` 会把它们识别为“已提交材料”，但 `artifacts.py` 的预览根只包含 `outputs`、`storage`、`reports` 和 `uploads`。

因此，开发预置文件会在所有权 DB 查询之前就因越出允许根而 403。这些文件是测试 fixture，不是用户上传；正确做法是分类展示或不展示，不是扩大生产预览允许根到整个仓库。

### 1.3 403/404 必须按路径来源分类

| 路径来源 | 磁盘状态 | 权属记录 | 当前结果 | 根因 |
|---|---|---|---|---|
| `/api/v0/files/upload` 真实上传 | 存在且在 upload root | 无 | 403 | 上传与预览权限契约断开 |
| 开发预置 `resources/`/`benchmarks/` | 存在但不在允许根 | 无 | 403 | fixture 被错当用户输入 |
| 其他用户的已登记文件 | 存在 | owner 不同 | 403 | 正常的跨用户拒绝 |
| localStorage/远端 workspace 中的旧路径 | 已清理、移动或挂载变更 | 不确定 | 404 | 工作区持久化了不稳定物理路径 |
| 非默认 `storage_dir` 环境 | 文件写入了硬编码 CWD 路径 | 无 | 403/404 | v0 upload 未使用 `AppContainer.settings` |

验收报告不能只写“点击输入文件失败”。必须同时记录 `file_id`、路径来源、HTTP 状态、后端 detail、磁盘存在性和权属记录命中情况。

### 1.4 “冗余”是展示模型错位，不是 run 数据应去重

`ResourcePanel` 对每个 run 平铺一条“基础信息表单（第 N 次）”。多次运行本身是有价值的审计历史，不应在 store 或展示层按内容哈希合并。真正问题是“最新输入”和“历史运行”没有分层，导致审计历史占据主工作面。

文件条目则由递归扫描任意 request 字符串推测而来，存在三个逻辑缺陷：

1. 文件身份不来自上传回执，而来自正则猜测；
2. 任意带扩展名或斜杠的业务文本可被误判为文件；
3. 输入身份又被 `!outputFiles.some(...)` 反向定义，同一资产合法具有两种角色时会从输入侧消失。

### 1.5 当前上传还缺少必要资源与类型门禁

v0 `upload_file()` 使用 `upload.file.read()` 一次性读取整个文件，没有字节上限、扩展名允许集、MIME/文件特征验证或失败原子性。document review 的 `FileService` 已有扩展名白名单，但同样整件读入内存且没有大小上限。

因此，“预览可用”不能是本项唯一验收目标。如果为了修 403 直接将任意大小、任意类型文件登记为可用资产，会把可用性缺陷变成资源耗尽和恶意文件处理风险。

## 二、对 v1 方案的审核结果

| v1 设计 | 审核 | 修正 |
|---|:---:|---|
| 上传时补写 `UploadedFileModel` | 方向部分正确 | 先明确通用 workspace file 与 review task file 的 owner 语义，不能用空 `task_id` 冒充有效关联 |
| DB 写入失败后 `except: pass` 仍返回上传成功 | P0 错误 | 这会制造已返回但不可预览/不可清理的幽灵文件；必须回滚文件并明确失败 |
| DB 失败时“降级为 download-only” | 事实不成立 | preview/file/download 三个端点都执行同一权属检查，无 DB 记录同样无法下载 |
| 返回 `out_path.resolve()` 绝对路径 | P0 错误 | 绝对路径会泄露服务器布局、破坏跨环境恢复；终态 API 不应返回任何物理路径 |
| `user_id=""` 作为兼容默认 | P0 错误 | 上传是需要所有权的操作，必须认证；空 owner 只能拒绝，不能降级成功 |
| 服务层临时 import DB context | P1 不合适 | 沿用 `get_db`/`get_container` 依赖注入与可测试 service，不建第二套 session 获取方式 |
| 用自制 16-bit 哈希去重表单 | P0 错误 | 碰撞空间小；JSON replacer 会丢失嵌套字段；更重要的是历史 run 不应被合并 |
| 在 `ResourcePanel` 硬编码模块文件字段白名单 | P1 过渡可用 | 最终应由 `ModuleRun.inputFiles` 显式传入；否则白名单会与 OpenAPI/payload builder 再建一个漂移源 |
| 白名单声称已覆盖全部模块 | 事实错误 | TIA 是 `attachments[].storage_uri`，US 14117 是 `attachments: string[]`；BCR 同时存在 `attachments` 与 `uploaded_files` |
| 用路径后缀作为文件真实性依据 | 不充分 | 后缀只是声明，上传端仍须验证大小、类型特征、安全和模块允许集 |
| 估算总工时 2.5 天 | 只够做临时止血 | 完成身份化、契约迁移、历史兼容和生命周期需分阶段交付 |

## 三、目标、非目标与强制不变量

### 3.1 目标

1. 用户上传必须认证，文件元数据和所有权持久化，服务重启/多 worker 后仍可预览。
2. 前端、workspace state 和公开 API 使用 `file_id` 和文件元数据，不依赖服务器绝对路径。
3. 模块运行前，后端按当前用户解析文件引用，拒绝未登记或他人文件。
4. `ResourcePanel` 只消费显式输入资产，不递归猜测任意 request 文本。
5. 主界面显示最新一次输入，历史 run 可折叠查看；完整审计历史不被删除或哈希合并。
6. 文件预览、下载、绑定、删除和过期都通过同一所有权与生命周期模型。

### 3.2 非目标

- 不通过扩大 artifacts 允许根来开放任意仓库文件预览；
- 不删除多次运行历史来制造“不冗余”的视觉效果；
- 不把 SHA-256 相同当作两次业务提交相同；哈希可用于完整性和物理存储优化，不用于抹掉审计语义；
- 不在本方案中重写输出 artifact 体系；只对齐其删除和保留边界；
- 不在一个提交中同时强制迁移全部历史 workspace state。

### 3.3 强制不变量

| 编号 | 不变量 |
|---|---|
| I1 | 对外响应不含服务器绝对路径 |
| I2 | 没有当前 user owner 记录的文件不可预览、下载或提交给模块 |
| I3 | DB 记录和 blob 必须同成功或同失败，不返回幽灵文件 |
| I4 | 文件输入身份来自显式 `inputFiles`，不来自路径正则或“不是输出” |
| I5 | 相同文件允许同时作为输入和输出展示，角色不互相抵消 |
| I6 | 历史 run 保持可追溯；“最新输入”是视图，不是数据删除 |
| I7 | 开发 fixture 不获得生产用户上传文件的权限语义 |
| I8 | 项目删除与过期清理同时对账 DB 和 blob，不制造悬空记录 |

## 四、目标架构

### 4.1 通用输入文件身份

不建议直接把 `UploadedFileModel.task_id=""` 当作通用 workspace 资产。该模型当前由 document review 流程使用，`task_id` 是必填的 review task 关联，项目删除也按该字段清理。

建议新增通用 `InputFileAssetModel`，与 review 旧模型在一个明确迁移窗口内并存，迁移结束后 document review 也改用通用服务，禁止无期双轨。

| 字段 | 用途 |
|---|---|
| `id` | 稳定不透明 `file_id` |
| `user_id` | 所有者，必填并建索引 |
| `workspace_id` | 用户工作区/TaskSpace 归属 |
| `bound_task_id` | 可选的后端运行 task ID |
| `file_name` | 用户可见原始文件名，完成 basename 清理 |
| `declared_content_type` / `detected_content_type` | 客户声明与服务端检测结果 |
| `size_bytes` / `sha256` | 大小门禁、完整性、对账 |
| `storage_key` | 内部相对存储键，不对前端暴露 |
| `status` | `staging/ready/quarantined/deleted/error` |
| `created_at` / `deleted_at` | 审计和生命周期 |

v1 不支持跨 workspace 共享同一逻辑文件资产。相同 SHA-256 可在存储层实现受控去重，但每次上传仍保留独立的 owner/workspace/审计记录。

### 4.2 身份化 API

```text
POST   /api/v1/input-files
GET    /api/v1/input-files/{file_id}
GET    /api/v1/input-files/{file_id}/preview
GET    /api/v1/input-files/{file_id}/content
GET    /api/v1/input-files/{file_id}/download
DELETE /api/v1/input-files/{file_id}
```

`POST` 使用 multipart 接收 `file`、`workspace_id`、`module_key` 和可选 `file_role`，必须消费 `get_current_user`、`get_db` 和 `get_container`。响应只返回：

```json
{
  "file_id": "file_...",
  "file_name": "data_inventory.xlsx",
  "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "size_bytes": 12345,
  "sha256": "...",
  "status": "ready",
  "created_at": "...",
  "reference_uri": "input-file://file_.../data_inventory.xlsx",
  "preview_url": "/api/v1/input-files/file_.../preview",
  "download_url": "/api/v1/input-files/file_.../download"
}
```

响应不包含 `storage_path`、`storage_key` 或绝对路径。`reference_uri` 是一个带原始扩展名的不透明兼容引用，不是可直接打开的物理路径。预览和下载按 `file_id + current_user` 查询，在查询到 owner 记录后才解析私有存储键。建议对“不存在”和“不属于当前用户”统一返回 404，避免泄露文件存在性。

当前 TaskSpace 只存在于用户的 `workspace_states.state_json` 中，不是独立关系表。因此 `workspace_id` 在本阶段是当前用户范围内的分组/生命周期键，不能替代 `user_id` 成为授权根。上传端应验证其格式并绑定当前用户，不应依赖 500 ms workspace-state 保存防抖完成强外键检查，否则会引入创建工作区后立即上传的竞态。

`/api/v1/artifacts/*` 继续用于输出产物，不再兼任通用输入文件 API。预览文本解析可复用其现有渲染语义，但权限和路由保持输入/输出分离。

### 4.3 上传一致性与安全

上传服务必须执行以下顺序：

```text
认证与 workspace 归属验证
→ 按配置的字节上限流式写临时文件
→ 同步计算 size + SHA-256
→ 验证扩展名、MIME/文件特征和模块允许类型
→ 必要时标记 quarantined
→ 在同一 DB transaction 中写 staging 记录
→ 临时文件原子 rename 到最终 storage_key
→ DB commit 为 ready
→ 返回不透明回执
```

任一步失败都必须清理临时/最终 blob 并回滚 DB，不得吞异常。超限返回 413，不支持类型返回 415 或当前 API 统一错误码。文件大小上限和模块类型允许集必须为配置/契约且有边界测试，不在方案中凭空指定一个数字。

### 4.4 模块请求的迁移

不能只修预览，却继续允许客户端给模块传入任意服务器路径。迁移分两阶段：

**兼容阶段**

- 前端改用已认证 v1 upload，同时获得 `file_id` 和 `input-file://<file_id>/<filename>` 不透明兼容引用；
- 旧模块字段短期继续接受 string，但新前端只发送 `input-file://` URI；所有 v1 模块路由在调用 service 前按 `file_id + current_user` 解析为受控内部路径；
- 历史原始路径仅在 DB 已有同 owner 登记时兼容，不能因为它位于 upload root 就被信任；
- 删除 v0 `_resolve_attachment_paths()` “查不到 ID 就当文件路径”的 fallback；
- v0 upload 或废弃，或改为要求认证并委托同一 InputFileService 的兼容壳，不再保留进程内真源。

**终态阶段**

- 定义统一 `InputFileRef`：`file_id/file_name/file_role/file_format`；
- 前端 payload builder 使用 OpenAPI 生成类型生成文件引用；
- 各模块 router 通过共享 resolver 按 `current_user` 将引用解析为内部路径，service 不相信客户端路径；
- 文件字符串/对象形态的模块差异在 schema/adapter 边界收敛，不在 `ResourcePanel` 重新维护；
- 一个发布窗口后关闭原始路径写入，对仍使用路径的请求返回明确契约错误。

CPRA 中的 HTTP(S) 隐私政策 URL 不是上传文件，保持为独立 `external_url` 输入，不创建本地 `InputFileAsset`。

### 4.5 前端显式输入资产

在 `ModuleRun` 中新增：

```typescript
type InputFileReference = {
  fileId: string;
  fileName: string;
  contentType: string;
  sizeBytes: number;
  role?: string;
  source: "upload" | "dev_fixture";
  previewUrl?: string;
  downloadUrl?: string;
};

type ModuleRun = {
  // existing fields...
  inputFiles: InputFileReference[];
};
```

`ModuleRunPanel` 不再只返回 `string[]`，而是构建一个运行准备结果：

```typescript
type PreparedRun = {
  request: ModuleRequest;
  inputFiles: InputFileReference[];
};
```

`WorkspaceShell.onRunDone()` 把 `request` 与 `inputFiles` 一起存入 run。`ResourcePanel` 只读 `run.inputFiles`，删除对 request 的递归扫描、`looksLikeFilePath` 猜测和输出反向过滤。

为了兼容历史 workspace state，可保留一个单独的 `legacyInputFileAdapter(run)`，仅对已知模块字段做窄提取并标记 `legacyPathOnly=true`。该 adapter 不进入新 run，不与 OpenAPI 契约并行无期维护。

### 4.6 工作区信息架构

建议左侧输入区改为：

```text
已提交材料
├─ 当前输入（最新一次 run，默认展开）
│  ├─ 表单快照
│  └─ 输入文件
└─ 历史提交（N 次，默认折叠）
   ├─ 第 2 次：表单 + 文件
   └─ 第 3 次：表单 + 文件
```

同样内容运行 3 次仍是 3 条历史，但主界面只展开最新一次。文件条目以 `file_id` 识别，名称冲突只影响显示后缀，不影响身份。

开发 fixture 仅在 `DEV_ACCEL_ENABLED` 下显示为“测试预置材料”，`source="dev_fixture"`。默认不通过生产 input-files API 预览；如确有浏览需求，只能增加受开发开关和静态 allowlist 约束的专用端点，不扩大通用文件权限。

### 4.7 生命周期与删除

- 用户删除 TaskSpace 时，应按 `workspace_id + user_id` 清理输入文件 DB 记录和 blob，并与输出治理方案的项目删除对账。
- 上传成功但未绑定任何 run 的文件为 orphan，在配置的宽限期后由单一清理器删除。
- `quarantined/error` 文件使用独立短保留期，不进入模块运行。
- 清理默认 dry-run，先对账 DB/blob/workspace refs；不使用直接递归删除 upload root 的策略。
- 运行中或仍被有效 workspace/run 引用的文件不进行 TTL 清理。

## 五、分阶段实施

### Phase 0：失败分类与回归锁定（0.5-1 天）

**工作**

1. 分别复现真实上传 403、开发 fixture 403、跨用户拒绝和旧路径 404；
2. 为每类失败保存 request/response、DB 命中和文件存在性证据；
3. 先写后端上传→预览失败测试与前端 ResourcePanel 现状测试；
4. 记录非默认 `storage_dir`、服务重启和两用户场景。

**Gate 0**：每个问题都有可失败的自动化证明，不再用“403/404 总称”代替根因。

### Phase 1：安全、持久的上传与 ID 预览（4-6 天）

**工作**

- 实现通用 InputFileAsset 数据模型和 service；
- 实现已认证 `/api/v1/input-files` 上传、元数据、预览、文件和下载端点；
- 使用 `Settings.upload_dir`，流式限量写入，完成 DB/blob 失败回滚；
- 前端上传切到 v1 端点，使用 `input-file://` 兼容引用满足现有字符串型模块字段；
- 将 owner-aware `input-file://` resolver 接入所有当前文件型模块的 sync/async 提交边界，保证新上传不仅能预览，也能完成任务运行；
- v0 upload 改为已认证兼容壳或对前端停用。

**Gate 1**：上传→新 App/service instance→预览/下载仍为 200；以新上传文件执行全部文件型模块的代表案例成功；他人文件不可探测；DB/blob 故障不产生单边孤儿；响应无服务器绝对路径。

### Phase 2：显式 `inputFiles` 与工作区历史分层（2-3 天）

**工作**

- 扩展 `ModuleRun`、app-store 标准化与 workspace-state 兼容；
- 将上传回执传入 `PreparedRun.inputFiles`；
- `ResourcePanel` 改为“当前输入 + 历史提交”，删除新 run 的 request 递归猜测；
- 加入有退役边界的 legacy adapter；
- 开发 fixture 与用户上传展示分类。

**Gate 2**：相同表单运行 3 次的审计历史仍为 3 条，主界面只展开最新一条；业务文本中的 `.pdf`/斜杠不产生文件节点；输入/输出角色可并存。

### Phase 3：模块契约去路径化（3-5 天）

**工作**

- 定义 OpenAPI `InputFileRef`，更新相关模块 Schema 和前端生成类型；
- 为各模块 router/adapter 接入 owner-aware resolver；
- 统一处理 `uploaded_files`、`attachments[].storage_uri` 和 `attachments: string[]` 的历史差异；
- 删除任意文件系统路径 fallback，保留一个发布窗口的已登记路径兼容；
- 更新 26 个开发案例、15 个 CLI 案例、OpenAPI 门禁和 Review upload-first 契约。

**Gate 3**：客户端无法通过传入 upload root 外路径或他人 `file_id` 让模块读取文件；新 OpenAPI 类型无漂移；旧路径使用被计数并具有关闭日期。

### Phase 4：生命周期、迁移与回归（2-3 天）

**工作**

- 项目删除链接入 InputFileAsset；
- 增加 orphan/quarantine 默认 dry-run 清理器和 DB/blob/workspace 对账报告；
- 对历史 workspace state 执行非破坏兼容，不批量猜测 owner；
- document review 上传迁入通用 service，退役并行上传实现；
- 运行后端、前端、Schema、HTTP、E2E 和仓库卫生门禁。

**Gate 4**：删除项目后该 workspace 输入不再可预览，DB/blob 都无悬空；清理 dry-run 结果稳定；输出产物删除与本方案无冲突。

## 六、测试与验收矩阵

### 6.1 后端强制测试

| 场景 | 预期 |
|---|---|
| 未认证上传 | 401/403，不写 blob/DB |
| 合法用户上传并预览 | upload 2xx，通过 `file_id` 预览 200 |
| 用户 B 访问用户 A 文件 | 不可探测，建议统一 404 |
| 服务重启/新 service instance | 不依赖 `_file_index`，预览仍 200 |
| 非默认 `storage_dir` | 写入与预览均使用 Settings 路径 |
| DB commit 失败 | API 失败，最终 blob 不存在 |
| 磁盘写入/rename 失败 | API 失败，无 ready DB 记录 |
| 大小边界 | 上限内成功，超限 413，不整件读入内存 |
| 后缀/MIME 冲突或不支持类型 | 拒绝或 quarantine，不进模块 |
| 任意路径/路径穿越/符号链接 | 不可读取 upload root 外文件 |
| 项目删除 | owner/workspace DB 记录和 blob 同步清理 |

### 6.2 前端强制测试

- `ResourcePanel` 单元/组件测试：当前输入、历史折叠、文件 ID、同名文件、输入/输出同路径角色并存；
- 请求文本含 `.pdf`、`a/b`、URL 时不生成文件节点；
- 相同请求提交 3 次：当前视图 1 条，历史记录 3 条；
- localStorage 和远端 workspace-state 水化后 `inputFiles` 保留；
- 历史 path-only run 由 legacy adapter 显示为不可验证/不可预览时有明确状态，不无限转圈；
- `dev_fixture` 不调用生产 input-files 预览 API。

### 6.3 端到端场景

```text
注册用户
→ 创建 TaskSpace
→ 上传文件
→ 提交模块运行
→ 点击当前输入并预览
→ 刷新页面/重启后端
→ 再次预览
→ 使用另一用户验证隔离
→ 删除项目
→ 验证记录/blob/工作区全部收敛
```

同时保持：26 个开发案例 HTTP 契约、11 个浏览器主路径、15 个 CLI 强断言案例、Review upload-first 场景和前端全量测试不回归。

## 七、门禁与完成证据

| Gate | 必须证据 | 失败处理 |
|---|---|---|
| G0 诊断 | 4 类 403/404/拒绝路径的自动测试和网络/DB 证据 | 不准以单一根因动工 |
| G1 上传与权限 | 认证、所有权、重启、配置路径、原子性和大小/类型测试 | 不切前端上传 |
| G2 工作区语义 | 显式 inputFiles、当前/历史分层、fixture 分类和不猜测文件证据 | 保留旧展示，不删历史 |
| G3 契约去路径 | OpenAPI、owner resolver、任意路径负例、旧契约使用计数 | 不关闭兼容窗口 |
| G4 生命周期 | 项目删除、orphan dry-run、DB/blob/workspace 对账 | 禁止实际清理 |
| G5 全量回归 | 后端、前端、26 HTTP、11 E2E、15 CLI、构建与 `git diff --check` | 不合入 |

每个阶段验收文档需记录命令、退出码、提交、测试数、失败详情、截图/网络证据和未覆盖边界。不得用“手动点开正常”代替跨用户、重启、删除和失败原子性测试。

## 八、变更范围

### 8.1 预计新增/修改

| 边界 | 主要文件 | 作用 |
|---|---|---|
| 输入资产模型 | `backend/models/input_file.py`、`backend/core/db.py` | 通用 file identity/owner/workspace/lifecycle |
| 输入资产服务 | `backend/services/input_file_service.py` | 上传、解析、权限、对账和删除 |
| API/Schema | `backend/api/v1/endpoints/input_files.py`、`backend/schemas/input_file.py`、`backend/api/v1/router.py` | 已认证 ID 端点 |
| v0 兼容 | `backend/api/v0/task_gateway/router.py`、`service.py` | 委托通用服务，删除内存真源/任意路径 fallback |
| 模块契约 | 相关 domain schema/router 和共享 resolver | `InputFileRef` 与 owner-aware 解析 |
| 前端 API/类型 | `frontend/src/api/modules.ts`、`api/generated/openapi.d.ts`、`lib/domain.ts` | 上传回执和 `ModuleRun.inputFiles` |
| 运行准备 | `ModuleRunPanel.tsx`、payload builders | `PreparedRun` 和文件引用 |
| 工作区 | `ResourcePanel.tsx`、`WorkspaceShell.tsx`、`app-store.tsx` | 显式输入、历史分层、兼容水化 |
| 删除/清理 | `backend/api/v1/endpoints/me.py`、新 dry-run 对账脚本 | 输入生命周期 |
| 测试 | 后端 input-file/API 测试、ResourcePanel 组件测试、Playwright | 功能、安全、历史与回归 |

### 8.2 有意不改

- 输出 artifact 分级、ZIP 和 trace 存储形态；
- 法律 RAG 与用户材料索引策略；
- 模块业务规则和报告内容；
- 历史数据的破坏性批量迁移。

## 九、风险与缓解

| 风险 | 等级 | 缓解 |
|---|:---:|---|
| 上传 API 切换破坏 10 模块 | 高 | 兼容阶段保留已登记 path resolver，然后逐模块迁移 |
| 并行两套 upload 实现长期漂移 | 高 | 兼容壳必须委托同一 service，设置退役日期和使用计数 |
| 历史 workspace 只有路径没有 owner | 高 | 不自动授权；标记 legacy/unavailable，只对能证明 owner 的记录回填 |
| 旧请求仍可传任意路径 | 高 | 兼容期也必须 DB owner + allowed root 双校验，删除直接 path fallback |
| 上传过程中 DB/blob 单边成功 | 高 | staging 状态、原子 rename、transaction rollback 和对账器 |
| 大文件读入内存导致资源耗尽 | 高 | 流式读写、字节上限和 413 测试 |
| 后缀伪造或恶意文档 | 高 | 扩展名 + MIME/特征检查 + quarantine + 安全解析 |
| 通过 403/404 探测他人文件 | 中 | 未找到与非 owner 统一对外 404 |
| SHA 相同被误当业务重复 | 中 | 哈希只用于完整性/存储优化，不合并 run 引用 |
| 开发 fixture 扩大仓库预览面 | 高 | fixture 分类，默认不可点击；专用 dev allowlist 与生产隔离 |
| 项目删除误删共享文件 | 中 | v1 不支持跨 workspace 共享；未来引入引用计数后再放开 |

## 十、排期与决策

### 10.1 条件化估算

| 范围 | 参考工期 | 交付结果 |
|---|---:|---|
| P0 可用性与权限止血 | 4-6 工程日 | 认证上传、DB owner、ID 预览、`input-file://` resolver、真实上传不再 403 |
| 前端显式输入与历史分层 | 2-3 工程日 | `inputFiles`、ResourcePanel 视图和 legacy adapter |
| 10 模块契约去路径化 | 3-5 工程日 | OpenAPI `InputFileRef`、owner resolver、兼容退役 |
| 生命周期与全量验收 | 2-3 工程日 | 删除/对账、E2E、证据文档 |
| **完整终态** | **11-17 工程日** | 不含恶意文件扫描基础设施或对象存储改造 |

以上以 1 名熟悉前后端契约的工程师为口径。如与其他 Schema 或 workspace state 迁移并行，应按冲突面重新估算，不应继续承诺 2.5 天完成终态。

### 10.2 待决策项

| 编号 | 决策 | 默认建议 | 最晚时点 |
|---|---|---|---|
| D1 | P0 如何兼容旧 builder 的字符串型文件字段 | 返回 `input-file://` 不透明 URI，不返回相对或绝对物理路径 | Phase 1 |
| D2 | v0 upload 是废弃还是兼容 | 前端立即切 v1；v0 委托同一 service 一个发布窗口后退役 | Phase 1 |
| D3 | 历史 path-only run 是否自动回填 owner | 仅能通过 DB 证明 owner 时回填，其余保持 unavailable | Phase 2 |
| D4 | 开发 fixture 是否支持点击预览 | 默认否；有需求再建 dev-only allowlist 端点 | Phase 2 |
| D5 | 非 owner 响应保持 403 还是统一 404 | 新 input-files API 统一 404；旧 artifacts API 另行兼容决策 | Phase 1 |

## 十一、完成定义

只有以下条件同时成立，才能将本项标记为完成：

```text
真实上传、开发 fixture、跨用户和旧路径失败已分类
且上传已认证、限量、可持久且 DB/blob 一致
且公开输入文件 API 以 file_id 授权，不暴露绝对路径
且模块不能读取未登记、他人或 upload root 外文件
且 ResourcePanel 只使用显式 inputFiles，不猜测 request
且当前输入与历史审计已分层，没有哈希合并历史
且开发 fixture 与用户上传权限语义分离
且项目删除/orphan 清理通过 DB/blob/workspace 对账
且 26 HTTP、11 E2E、15 CLI、前后端全量与安全负例通过
且历史路径兼容有使用计数、截止日期和退役证据
```

## 附录 A：主要代码证据

| 事实 | 证据 |
|---|---|
| v0 upload 固定写 `storage/uploads`、只写 `_file_index`、返回 path | `backend/api/v0/task_gateway/service.py:73-95` |
| v0 upload 路由没有认证/DB/container 依赖 | `backend/api/v0/task_gateway/router.py:15-18` |
| 前端携带 auth 调用 v0 upload 并要求 path | `frontend/src/api/modules.ts:294-332` |
| 上传回执被降为 `string[]` path | `frontend/src/components/workspace/ModuleRunPanel.tsx:502-509` |
| artifacts 先检查存在/允许根，再查所有权 DB | `backend/api/v1/endpoints/artifacts.py:28-73` |
| ResourcePanel 递归扫描任意 request | `frontend/src/components/workspace/ResourcePanel.tsx:245-295` |
| ResourcePanel 每 run 平铺表单并用输出反向过滤输入 | `frontend/src/components/workspace/ResourcePanel.tsx:387-426` |
| ModuleRun 只存 request，无显式 input files | `frontend/src/lib/domain.ts:44-58` |
| 工作区同时保存 localStorage 和远端 workspace state | `frontend/src/lib/app-store.tsx:451-475`、`frontend/src/lib/app-store.tsx:737-750` |
| 开发案例直接使用 `resources/`/`benchmarks/` 后端路径 | `frontend/src/lib/dev-test-cases.ts:375`、`frontend/src/lib/dev-test-cases.ts:493`、`frontend/src/lib/dev-test-cases.ts:896` |
| review upload 已有认证、DB 与 task 归属实现 | `backend/domains/cn/document_review/router.py:62-70`、`backend/domains/cn/document_review/service.py:168-189` |
| 现有 FileService 有扩展名白名单，但仍整件读入且无大小上限 | `backend/services/file_service.py:11-28` |
| `UploadedFileModel.task_id` 当前必填 | `backend/models/review.py:28-38` |
| TaskSpace 当前保存为用户级 workspace JSON，非独立关系表 | `backend/models/workspace.py:9-17`、`backend/api/v1/endpoints/workspace_state.py:77-93` |
| 项目删除当前按 task/user 对账 uploaded file 与 blob | `backend/api/v1/endpoints/me.py:353-402` |
| v0 ID 查不到时直接把字符串当路径 | `backend/api/v0/task_gateway/service.py:417-442` |

## 附录 B：阅读者应能直接回答的问题

1. 为什么补写 DB 不是完整终态？
2. 真实上传文件和开发预置文件为什么都可能返回 403？
3. 为什么不能向前端返回绝对路径？
4. 为什么不应按表单内容哈希删除重复 run？
5. P0 止血与终态 `InputFileRef` 迁移的边界是什么？
6. 历史 path-only workspace 无法证明 owner 时怎么处理？
7. 项目删除时如何保证 DB、blob 和 workspace 不互相悬空？
