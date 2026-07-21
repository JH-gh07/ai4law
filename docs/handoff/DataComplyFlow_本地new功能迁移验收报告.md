# DataComplyFlow 本地 new 功能迁移验收报告

> 验收日期：2026-07-21
> 目标底版：`origin/new@a0f26fe638b6832d8e24befd28dfe411c0b50b00`
> 唯一增量源：`archive/local-original@ab4be948adc47afee7e33147018f2fb142584c43`
> 共同祖先：`398e8acdd446a4ee09a67d8b6b893ed933695394`

## 1. 验收结论

本地原始 `new` 相对共同祖先的源码范围共 56 项，已经逐项登记并结案：18 项原语义迁移、25 项按 domains/公共能力重写、5 项保留团队目标实现、5 项历史归档、3 项有证据拒绝。机器清单无 `pending`，且 `--require-complete` 会验证每个结案项有证据、需要落盘的目标真实存在。

损坏的 `archive/local-full@3bbdeb0` 未作为任何代码或文档来源。它只保留在审计记录中，用于说明 `app.css` 和 lockfile 的冲突损坏风险。

## 2. 已恢复和补强的能力

- Citation：公共 writer、API 读取和 domain 引用结构统一重建规范站内 URL；原始 33 项断言进入默认 pytest，并增加 domain 路径覆盖。
- 渲染：补回结构化报告 IR、Markdown 分块适配、Markdown/HTML/DOCX/PDF 渲染器和共享前后端 Golden Cases；没有引入第二模块注册表。
- 模块产物：12 个模块都具有可打开的 PDF；新增 PDF 不删除 Markdown、DOCX、HTML、JSON、XLSX、ZIP、trace、annotated DOCX 或 CitationMap 等既有输出。
- Harness：完整保留原始 15 个案例，使用 `config/module_registry.json` 与 `backend.domains.*` 装配 11 个可直接生成报告的模块；异常会生成 error/FAIL manifest 并返回非零退出码。
- 前端：共享 `PdfViewer` 提供鉴权 Blob 请求、可访问状态、真实重试和 object URL 清理；正文只与完全同 basename 的 PDF 配对；前后端 14 个规范化案例逐字一致。
- v0 隔离：全量回归发现 v0 网关测试会读取本机 LLM 配置，已通过构造器注入统一客户端并在测试中显式禁用外部 LLM/法律 API，保留端到端异步任务与产物下载覆盖。

## 3. 可重复验收证据

| Gate | 实际结果 |
|---|---|
| 来源清单 | `check_local_new_parity.py --require-complete`：56 source candidates，全部结案 |
| 历史设计追溯 | 5/5 来源路径的 Git blob 与归档指针一致 |
| Citation | Citation 全目录 65 项通过；相关 domain 112 项通过 |
| Render 与服务 | 公共 render/service 32 项通过；所有 PDF 均验证 `%PDF` 且可由 `pypdf` 打开 |
| 12 模块矩阵 | CN/EU/API/Service 141 项 + US 45 项通过；12/12 有有效 PDF |
| Harness | 15/15 no-LLM 案例通过；Harness 契约 4 项通过；原始案例 blob 15/15 一致 |
| Frontend | `npm ci` 安装 292 packages、0 vulnerabilities；Vitest 34/34；`tsc` + Vite build 通过 |
| Backend 全量 | 首轮 450 通过、1 个 v0 超时；隔离修复后 451/451 通过 |
| 仓库卫生 | 976 个仓库文件检查通过 |
| Git 格式 | `git diff --check` 通过；用户未跟踪的 `plan/remote_rebase_plan.md` 未修改、未暂存 |

后端全量仅报告一个既有 `StarletteDeprecationWarning`：当前 `fastapi.testclient` 仍通过 `httpx` 兼容层导入。它不是测试失败，后续依赖升级时单独处理，不在本次功能迁移中扩大范围。

## 4. 有证据拒绝或保留目标实现

- 未引入原分支的 ArtifactRegistry：没有生产消费者，现有结果字典与 ReportService 已承担产物契约。
- 未引入 RenderProfile：它复制模块身份，违反 `config/module_registry.json` 唯一权威源。
- 未在运行时加载规范化 JSON：同一 JSON 直接由前后端测试执行即可防漂移，运行时解析只增加故障面。
- 未引入 `jit-pdf`：原实现重试不触发新请求，并绑定受损 lockfile；现有 Artifact API + 浏览器原生 PDF 能以更小依赖面满足需求。
- 未覆盖远程拆分样式：只向 `frontend/src/styles/app/workspace.css` 增加缺失状态，未复制历史 254 KB `app.css`。

## 5. 历史原文恢复方式

五份历史设计材料的归档指针位于 `docs/archive/local-original/`。每份都记录来源提交、完整 blob SHA、字节数以及 `git show` 命令，可从 `archive/local-original` 逐字恢复；旧路径和过时行号不进入活动规范。

## 6. 尚需人工运行的非自动项

当前 Codex 会话没有 Chrome DevTools/浏览器控制工具，因此没有伪造“真实浏览器控制台无错误”的结论。合并前建议人工登录工作区，分别打开一个带精确伴随 PDF 的报告和一个无 PDF 的报告，核对 tab 禁用、加载、失败重试、下载和浏览器控制台。组件测试与生产构建已经覆盖可自动化部分。

## 7. 本地提交序列

1. `431291c` — 冻结来源、清单与运行边界
2. `8878e7a` — 恢复 domain Citation URL
3. `d5bd8a2` — 恢复共享结构化渲染
4. `3d10cb7` — 恢复 12 模块 PDF 产物
5. `a923811` — 恢复 domains-based Harness
6. `9f3ee7d` — 恢复前端 PDF/Markdown 预览
7. 本报告所在提交 — 隔离 v0 外部客户端、归档历史设计并固化最终门禁

本次未执行远程 push、PR、merge、rebase 或历史重写。
