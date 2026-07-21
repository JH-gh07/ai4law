# AI4Law 本地完整 `new` → 团队重构 `new` 全覆盖迁移与验收清单

> 状态：已确认，实施中
> 目标分支：`new`（本地检出的团队重构版，跟踪 `origin/new`）
> 本地功能来源：`archive/local-original`（原本地 `new` 的未 rebase 原始保全快照，唯一增量真源）
> 目标 SHA：`a0f26fe638b6832d8e24befd28dfe411c0b50b00`
> 来源 SHA：`ab4be948adc47afee7e33147018f2fb142584c43`
> 共同祖先：`398e8acdd446a4ee09a67d8b6b893ed933695394`
> 分叉关系：来源侧 15 个独有提交；目标侧 34 个独有提交
> 本地增量：从共同祖先到来源快照共 1793 个文件变化；排除 `storage/`、`runs/`、`.DS_Store` 和 `frontend/tmp.zip` 等运行/归档产物后，保留 56 个源码、配置、测试和文档候选（34 新增、21 修改、1 删除）
> 审计口径：以共同祖先分别审计本地增量与远程重构增量，再把本地语义迁入目标；不以两端 tip 的整树覆盖或 rebase 结果作为真值

```text
398e8ac（共同祖先）
├── remote 34 commits → a0f26fe = new = origin/new（重构底版/目标）
└── local  15 commits → ab4be94 = archive/local-original（原始本地增量真源）

3bbdeb0 = archive/local-full（rebase 冲突妥协版，仅供取证，禁止作为迁移或验收真源）
```

---

## 1. 目标与完成定义

本轮不是把本地旧目录整体覆盖到团队重构版，而是把本地完整版本中的业务能力迁移到团队已经建立的 `backend/domains/{cn,eu,us}`、`config/module_registry.json`、`docs/` 和当前前端架构中。

只有同时满足以下条件，才可称为“全覆盖完成”：

- [ ] 56 个真实本地增量候选均有明确处置：迁移、重写、归档、保留目标现状或有证据地拒绝迁移。
- [ ] 其中 34 个新增、21 个修改和 1 个删除候选全部完成语义审查，不以整文件覆盖团队重构结果。
- [ ] 12 个注册业务模块的既有输出不减少，新增 PDF/引用能力符合统一契约。
- [ ] 本地 citation URL 修复的实现和 33 项验证全部进入可自动发现的测试体系。
- [ ] Test Harness 使用 `backend.domains.*` 和权威模块注册表，不再引用已删除的 `backend.modules.*`。
- [ ] 前后端 Markdown 规范化使用同一组 Golden Cases，结果逐条一致。
- [ ] PDF 前端预览可安装、可构建、可重试、样式完整且不会重复下载同一文件。
- [ ] Diagnosis HTML 的标题、列表、表格、分隔线等表达不低于迁移前。
- [ ] 全量后端测试、前端测试、前端生产构建和仓库卫生检查均通过。
- [ ] 验收报告记录命令、日期、SHA、通过数、失败数和已知非阻断项，不能只写“已验证”。

---

## 2. 迁移原则

1. **团队重构结构优先**：所有业务实现落在 `backend/domains/*`；禁止恢复生产用 `backend/modules/*`。
2. **功能语义优先于文件相同**：路径改变但行为等价的，不恢复旧副本；行为缺失或退化的，按新架构补齐。
3. **测试先行**：每个已确认缺陷先增加能失败的测试，再实现修复。
4. **输出只增不减**：现有 Markdown、DOCX、HTML、JSON、XLSX、ZIP 等输出键不得因 PDF 迁移消失。
5. **权威源唯一**：模块身份继续由 `config/module_registry.json` 管理；不得再建立不受验证的第二份模块清单。
6. **文档服从治理**：历史原文可以归档，但活动文档不得继续引用 `backend/modules/*` 或本机绝对路径。
7. **运行数据与源码分离**：`runs/`、`outputs/`、数据库和 trace 不进入源码迁移，但来源分支必须保留以便追溯。
8. **不推送、不合并远程**：实施期间只在本地目标分支形成小批次可回退提交，最终由人工决定是否推送或合并。

---

## 3. 原始本地增量与语义迁移目标总表

下列清单的唯一来源是 `398e8ac..archive/local-original`。其中 49 项组成核心功能语义迁移目标；另外 7 项是原始分支中曾被 rebase 妥协版漏掉或掩盖的配置、样式、锁文件与文档变化，也必须逐项结案。

### 3.0 原始快照补回的 7 个直接候选

| 编号 | 原始本地路径 | 处置要求 |
|---|---|---|
| S01 | `.gitignore` | 语义合并 `runs/` 等运行目录规则，不覆盖团队新增规则 |
| S02 | `.streamlit/config.toml`（本地删除） | 核查目标是否已淘汰 Streamlit；只有无入口、无文档、无 CI 消费者时才确认删除已满足 |
| S03 | `.vscode/settings.json` | 只迁移团队共享且与仓库运行相关的设置，个人 IDE 偏好不迁移 |
| S04 | `frontend/DESIGN.md` | 与现有 `docs/` 治理文档比对，仍有效内容迁移，重复内容归档或拒绝 |
| S05 | `frontend/package-lock.json` | 禁止复制旧锁文件；以目标 `package.json` 的最终依赖重新生成并用 `npm ci` 验证 |
| S06 | `frontend/src/styles/app.css` | 禁止用原始 254KB 文件覆盖目标 162B 聚合入口；仅把仍缺少的 PDF/双视图样式迁入现有拆分样式体系 |
| S07 | `doc/AI4Law 下一阶段业务逻辑.md` | 核对仍有效的产品逻辑，按当前 `docs/` 治理迁移；不得恢复过时路径 |

### 3.1 本地新增的渲染与规范化文件（10 个）

| ID | 来源文件 | 目标处置 | 验收重点 |
|---|---|---|---|
| R01 | `backend/common/render/pdf_renderer.py` | 迁移并修正引擎探测、异常降级和接口测试 | 三种入口均生成有效 `%PDF` 文件；异常必须确定性回退 |
| R02 | `backend/common/render/report_model.py` | 迁移为模块与渲染器之间的 IR 契约 | 标题、段落、列表、表格、分隔线、引用均可表达 |
| R03 | `backend/common/render/content_adapter.py` | 重写 Markdown→Block 适配，禁止整篇 Markdown 塞入单个 Paragraph | Diagnosis HTML 不丢标题、列表和表格 |
| R04 | `backend/common/render/markdown_renderer.py` | 迁移并补 round-trip/Golden Tests | ReportDocument 输出稳定且引用不丢失 |
| R05 | `backend/common/render/html_renderer.py` | 迁移并补结构/XSS测试 | 结构不退化，所有不可信文本正确转义 |
| R06 | `backend/common/render/docx_renderer.py` | 迁移并补有效 DOCX 测试 | python-docx 可重新打开，表格/列表/标题存在 |
| R07 | `backend/common/render/render_profile.py` | 不直接复制第二份模块表；改为读取或校验 `module_registry.json` 中的渲染元数据 | 12 个模块身份与格式配置一一对应 |
| R08 | `backend/common/render/artifact_registry.py` | 迁移、补路径安全和重复格式测试；只在有明确消费者后启用 | task/module 不可路径穿越；重复注册规则明确 |
| R09 | `backend/common/render/normalization_rules.json` | 保留为规范说明，不再虚称运行时 SSOT | 与实现差异由测试门禁发现 |
| R10 | `backend/common/render/normalization_test_cases.json` | 作为前后端共享行为契约；保留现有 14 项并补边界用例 | Python 与 TypeScript 对每个 case 输出完全相同 |

### 3.2 本地新增的 Harness 与案例文件（17 个）

| ID | 来源文件/目录 | 目标处置 |
|---|---|---|
| H01 | `backend/tests/harness/runner.py` | 重写模块装配层，使用 `config/module_registry.json` 和 `backend.domains.*` |
| H02 | `backend/tests/harness/viewer.py` | 迁移；补不存在结果、错误结果、跨模块查找测试 |
| H03 | `backend/tests/diagnosis/cases/*.json`（3 项） | 保留并映射 `cn.transfer_diagnosis` |
| H04 | `backend/tests/assessment/cases/*.json`（2 项） | 保留并映射 `cn.security_assessment` |
| H05 | `backend/tests/dpia/cases/*.json`（2 项） | 保留并映射 `eu.dpia` |
| H06 | `backend/tests/{pipia,scc,bcr,tia,eu_scc,cn_flow,cpra,us_14117}/cases/*.json`（各 1 项） | 保留并映射相应 domains 模块 |

说明：这里实际是 **2 个 Harness 文件 + 15 个案例文件 = 17 个新增文件**。Harness 覆盖 11 个可直接生成报告的模块；`cn.document_review` 另由其 API/Service 集成测试覆盖。

### 3.3 引用修复验证（1 个）

| ID | 来源文件 | 目标处置 |
|---|---|---|
| C01 | `backend/common/citation/tests/verify_citation_url_fix.py` | 重命名/迁移为默认 pytest 可发现的 `test_citation_url_normalization.py`，保留全部 33 个断言 |

### 3.4 前端新增文件（1 个）

| ID | 来源文件 | 目标处置 |
|---|---|---|
| F01 | `frontend/src/components/common/PdfViewer.tsx` | 迁移后修复重试、样式、重复请求、依赖稳定性和无障碍状态 |

### 3.5 文档与设计原文（4 个）

以下原文需要保存，但不能原样作为活动文档发布，因为仍包含 `backend/modules/*` 和本机绝对路径。

| ID | 来源文件 | 目标处置 |
|---|---|---|
| D01 | `CODE_MODULE_ARCHITECTURE.md` | 原文归档；有效内容按 12 模块 domains 架构重写进活动架构文档 |
| D02 | `doc/RENDER_ARCHITECTURE_REFERENCE.md` | 原文归档；有效契约迁入 `docs/standards/` |
| D03 | `doc/arch/citation-url-flow.md` | 更新路径、行号和公共写入链路后迁入 `docs/standards/` |
| D04 | `plan/rendering_architecture_plan.md` | 作为历史设计来源归档；本文件成为新的活动执行清单 |

### 3.6 核心功能需要语义映射或合并的目标文件（16 个）

| ID | 目标文件 | 本地能力 | 不能直接复制的原因 |
|---|---|---|---|
| M01 | `backend/common/llm/postprocess.py` | Golden Cases 加载与执行 | 要改为自动测试入口，且与前端共享同一 cases 文件 |
| M02 | `backend/common/render/artifacts.py` | 旧调用统一委托 `PdfRenderer` | 必须保留现有 XLSX、bundle 等公共能力 |
| M03 | `backend/services/report_service.py` | PDF 从 Canvas 改为统一 Markdown 渲染 | 要保持持久化、owner、preview 和路径契约不变 |
| M04 | `frontend/package.json` | 增加 `jit-pdf` | 必须同步 lockfile、CSS 和许可证/构建验证 |
| M05 | `frontend/src/lib/fallback-markdown.ts` | 前端规范化行为 | 必须由共享 Golden Cases 验证，不接受仅靠注释“对称” |
| M06 | `frontend/src/components/workspace/WorkspaceShell.tsx` | Markdown/PDF 双视图 | 要删除冗余 Blob 请求并稳定 headers/effect 依赖 |
| M07 | `backend/domains/cn/document_review/service.py` | 生成并持久化 PDF 产物 | 保留现有 DOCX/JSON/annotated DOCX 流程 |
| M08 | `backend/domains/cn/security_assessment/report_renderer.py` | PDF、body Markdown、公共 citation writer | 拆成 citation 与渲染两个可回退增量 |
| M09 | `backend/domains/cn/transfer_diagnosis/report_renderer.py` | ReportDocument/HtmlRenderer 接入 | 本地实现会损坏 Markdown 结构，必须先写回归测试再迁移 |
| M10 | `backend/domains/cn/pipia/service.py` | PDF 及 ZIP 接入 | 保持原 ZIP 文件和输出键，并验证 PDF 被正确打包 |
| M11 | `backend/domains/cn/scc_review/service.py` | PDF 接入 | 保持 annotated DOCX 与 citation 输出 |
| M12 | `backend/domains/eu/dpia/report_renderer.py` | PDF、公共 citation writer | 保持风险矩阵、整改计划和现有 JSON/XLSX/ZIP 输出 |
| M13 | `backend/domains/eu/bcr_review/service.py` | 两种 BCR 路径都输出 PDF | 表单驱动与文档驱动必须分别测试 |
| M14 | `backend/domains/eu/scc_review/service.py` | PDF、引用知识 URL | 不混淆 EU SCC 与中国 SCC 的模块身份 |
| M15 | `backend/domains/eu/tia/service.py` | PDF、ZIP、引用知识 URL | 验证 ZIP 新增 PDF 但不减少旧文件 |
| M16 | `backend/domains/us/cpra/service.py` | 引用知识 URL | CPRA 已经经公共 helper 生成 PDF，本文件只迁移 citation 修复 |

---

## 4. 迁移时必须补充或重新生成的目标文件

X01—X03 对应原始本地增量中的直接候选，但不能整文件复制，必须在目标结构中语义合并或重新生成；其余项目是为了让迁移结果可安装、可测试、可追踪而新增的目标文件。

| ID | 计划文件 | 作用 |
|---|---|---|
| X01 | `.gitignore` | 加入 `runs/`，防止 Harness 运行结果污染源码状态 |
| X02 | `frontend/package-lock.json` | 锁定 `jit-pdf` 及其传递依赖，确保 `npm ci` 成功 |
| X03 | `frontend/src/styles/app/workspace.css` | 补 PDF viewer shell、loading、error、toolbar 容器和双视图 tab 样式 |
| X04 | `frontend/src/components/common/PdfViewer.test.tsx` | 覆盖成功加载、HTTP 失败、SDK 失败、重试、卸载清理 |
| X05 | `frontend/src/lib/fallback-markdown.test.ts` | 读取共享 Golden Cases 验证前端规范化 |
| X06 | `backend/common/render/tests/test_pdf_renderer.py` | 三入口、中文、表格、引擎回退、文件有效性 |
| X07 | `backend/common/render/tests/test_report_renderers.py` | IR→Markdown/HTML/DOCX 结构和安全测试 |
| X08 | `backend/common/render/tests/test_normalization_contract.py` | 后端执行全部共享 Golden Cases |
| X09 | `backend/common/render/tests/test_artifact_registry.py` | 路径、格式、重复注册和序列化契约 |
| X10 | `backend/tests/harness/test_runner.py` | 注册表映射、错误捕获、manifest 和退出码测试 |
| X11 | `config/local_new_parity_manifest.json` | 机器可读列出功能 ID、目标文件、验证命令和 12 模块覆盖 |
| X12 | `scripts/check_local_new_parity.py` | 检查旧 import、必需文件、lockfile、模块覆盖、文档旧路径和测试发现 |
| X13 | `docs/standards/DataComplyFlow_统一渲染与产物契约.md` | 当前有效的渲染、格式和输出契约 |
| X14 | `docs/standards/DataComplyFlow_引用跳转与CitationMap契约.md` | 当前有效的 citation 写入与跳转契约 |
| X15 | `docs/archive/design-provenance/local-new-20260719/` | 保存四份本地设计原文，避免错误内容成为活动权威源 |
| X16 | `docs/handoff/DataComplyFlow_本地new功能迁移验收报告.md` | 最终记录实际命令和证据，不预填“通过” |

---

## 5. 12 模块功能覆盖矩阵

| 权威 module_id | 本地能力迁移 | PDF 接入方式 | Citation 修复 | 必须验证的原有输出 |
|---|---|---|---|---|
| `cn.transfer_diagnosis` | 统一 HTML/IR | 公共 `render_pdf_report` 间接接入 | 公共链路既有 | HTML、PDF、结构化诊断结果 |
| `cn.security_assessment` | PDF、body Markdown | 直接 `PdfRenderer` | 改公共 writer | MD、DOCX、ZIP、JSON、XLSX、trace |
| `cn.document_review` | PDF 产物 | 直接 `PdfRenderer` + ReportService | 公共链路既有 | DOCX、JSON、annotated DOCX、PDF |
| `cn.scc_review` | PDF | 直接 `PdfRenderer` | 公共链路既有 | MD、DOCX、annotated DOCX、citation map |
| `cn.pipia` | PDF/ZIP | 直接 `PdfRenderer` | 公共链路既有 | MD、DOCX、ZIP、citation map |
| `us.eo_14117_flow_review` | 统一 PDF helper | 公共 `render_pdf_report` 间接接入 | 公共链路既有 | MD、DOCX、PDF、XLSX、JSON、ZIP |
| `eu.scc_review` | PDF | 直接 `PdfRenderer` | `build_knowledge_url` | MD、DOCX、findings、annotated DOCX |
| `eu.bcr_review` | 两路径 PDF | 直接 `PdfRenderer` | 公共链路既有 | MD、DOCX、ZIP、citation map |
| `eu.dpia` | PDF | 直接 `PdfRenderer` | 改公共 writer | MD、DOCX、JSON、XLSX、ZIP、trace |
| `eu.tia` | PDF/ZIP | 直接 `PdfRenderer` | `build_knowledge_url` | MD、DOCX、ZIP、citation map |
| `us.eo_14117` | 统一 PDF helper | 公共 `render_pdf_report` 间接接入 | 公共链路既有 | MD、DOCX、PDF、XLSX、JSON、ZIP |
| `us.cpra` | 统一 PDF helper | 公共 `render_pdf_report` 间接接入 | `build_knowledge_url` | MD、DOCX、PDF、XLSX、JSON、ZIP |

每个模块的 PDF 验收至少包括：输出键存在、路径位于允许目录、文件非空、前四字节为 `%PDF`、`pypdf` 可打开且页数不少于 1。仅检查字符串以 `.pdf` 结尾不算通过。

---

## 6. 分批实施任务

### Phase 0：安全基线与机器可读清单

#### Task 0.1：冻结基线和保护运行目录

涉及文件：`.gitignore`、`config/local_new_parity_manifest.json`、`scripts/check_local_new_parity.py`。

验收条件：

- [x] manifest 记录共同祖先、两个 tip、56 个真实本地增量候选及其处置结论，并关联 12 模块矩阵。
- [x] `runs/` 被忽略，但现有本地 `runs/` 内容不删除。
- [x] 校验脚本能在差异缺项、错误变更类型、错误来源快照或模块覆盖不足时返回非零状态；旧 import 继续由仓库卫生门禁负责。

验证：

```bash
uv run --frozen python scripts/check_local_new_parity.py
git status --short
```

### Phase 1：Citation URL 修复独立迁移

#### Task 1.1：先恢复可发现的 33 项测试

涉及文件：`backend/common/citation/tests/test_citation_url_normalization.py`。

验收条件：测试迁入后，原始 33 项公共契约通过；新增 5 项 domain 链路测试在修复前全部失败、修复后全部通过。

- [x] 原始 33 项测试以标准 `test_*.py` 名称进入默认 pytest 收集。
- [x] Assessment、DPIA、CPRA、TIA、EU SCC 的真实写入/DTO 链路均有回归测试。

#### Task 1.2：统一 assessment 与 DPIA 的 citation writer

涉及文件：M08、M12 及对应模块测试。

- [x] 两个模块不再私自序列化 `citation_map.json`，统一委托公共 writer，并保留真实 `task_id`。

#### Task 1.3：补 CPRA、TIA、EU SCC 的 `knowledge_url`

- [x] 三个模块的引用 DTO 均通过公共 `build_knowledge_url` 生成规范跳转地址。

涉及文件：M14、M15、M16 及对应模块测试。

Checkpoint 1：✅ Citation 目录 65 项通过；五个相关 domain 测试目录 112 项通过；citation map 原字段未减少。

### Phase 2：统一渲染基础设施

#### Task 2.1：PdfRenderer 与有效 PDF 测试

涉及文件：R01、M02、M03、X06。

后端只承诺已有 ReportLab 生产路径，不引入未实现的 Python `jit-pdf-sdk` 和虚假降级层。

- [x] Markdown、sections、template 三种入口生成的文件均有 `%PDF` 签名且可由 `pypdf` 打开。
- [x] 缺失模板明确抛出 `FileNotFoundError`，不生成伪成功产物。
- [x] ReportService 已从 Canvas 字面量绘制切换到公共 Markdown PDF 入口。

#### Task 2.2：ReportDocument 与 Markdown/HTML 渲染

涉及文件：R02、R03、R04、R05、X07。

- [x] 增加 `HeadingBlock`，标题、段落、列表、表格、分隔线均可独立表达。
- [x] ContentAdapter 不再把整篇 Markdown 塞入单个 Paragraph；畸形表格保留为文本而非丢弃。
- [x] HTML 渲染对不可信内容转义，Markdown/HTML 结构回归通过。

#### Task 2.3：DOCX 渲染与模板兼容

涉及文件：R06、X07。

- [x] 生成的 DOCX 可由 python-docx 重新打开，标题、列表和表格结构存在。

#### Task 2.4：规范化共享行为契约

涉及文件：R09、R10、M01、X08。

- [x] 原始 14 个 Golden Cases 进入默认后端 pytest 并全部通过。
- [x] 规则 JSON 明确降级为行为说明，禁止继续虚称运行时 SSOT；前端对称验证留在 Phase 5。

#### Task 2.5：产物注册和渲染配置去双源

涉及文件：R07、R08、`config/module_registry.json`、X09、现有模块注册表测试。

- [x] 原始 `ArtifactRegistry` 和 `render_profile` 均无生产消费者，明确拒绝迁移。
- [x] `config/module_registry.json` 保持唯一模块身份源，未建立第二份 12 模块配置表。

Checkpoint 2：✅ Render 与 services 相关测试 32 项通过；模块注册表仍为唯一模块身份源；无未使用且无测试的生产基础设施。

### Phase 3：12 模块纵向接入

#### Task 3.1：中国合同审查、SCC、PIPIA

涉及文件：M07、M10、M11 及各自 service 测试。

- [x] 文档审查通过现有 `ReportService` 持久化并返回有效 PDF，DOCX 主报告契约保持不变。
- [x] 中国 SCC 输出新增有效 PDF，原 Markdown、DOCX、annotated DOCX 流程保持通过。
- [x] PIPIA 输出新增有效 PDF，且 ZIP 同时包含原 Markdown、DOCX 和新增 PDF。

#### Task 3.2：中国安全评估

涉及文件：M08 及 renderer/service 测试；验证 PDF、body Markdown 和原 ZIP 全量内容。

- [x] 有效 PDF 与结构化 `body_markdown` 均已恢复，并被原 ZIP 收录；JSON、XLSX、trace 等原产物无减少。

#### Task 3.3：Diagnosis HTML 无损迁移

涉及文件：M09、R03、R05、transfer diagnosis 测试。

必须先证明本地待迁移实现会丢列表/表格，再以结构化 Block 解析修复；禁止直接删除旧 HTML 逻辑后再观察结果。

- [x] 核查发现目标版现有实现已经无损处理标题、列表、表格、分隔线与 HTML 转义；用特征测试锁定该行为，按 Ponytail 原则保留目标实现，拒绝无收益替换。

#### Task 3.4：EU DPIA/BCR/SCC/TIA

涉及文件：M12–M15 及四个模块测试；BCR 两条路径分别验收。

- [x] DPIA、EU SCC、TIA 均新增有效 PDF；DPIA/TIA 的原 ZIP 内容只增不减。
- [x] BCR 表单驱动与文档驱动两条渲染路径分别生成并打包有效 PDF。

#### Task 3.5：US 两个 EO 14117 模块与 CPRA 的间接覆盖

涉及文件：M02、M16 及三个模块测试；验证统一 helper 不改变原有 PDF 内容基本结构。

- [x] 三个模块均验证 `%PDF`、`pypdf` 可打开及 ZIP 收录；并修复 EO 14117 二次写 ZIP 导致完整包被 DOCX 覆盖的既有缺陷。

Checkpoint 3：✅ 12 模块矩阵全部有可执行测试证据；相关 CN/EU/API/Service 回归 141 项通过，US 三模块回归 45 项通过；原有输出键不减少，ZIP 覆盖缺陷已修复。

### Phase 4：Harness 重构迁移

#### Task 4.1：基于权威注册表的适配器

涉及文件：H01、X10、`config/local_new_parity_manifest.json`。

不得通过恢复 `backend/modules` 兼容层解决。不同服务接口应由显式 adapter 处理，不使用隐式猜测类名。

- [x] 11 个 Harness 适配器显式映射 `backend.domains.*`，启动时逐项核对 `config/module_registry.json` 的 module_id 与 implementation_package。
- [x] `--no-llm` 路径不会发起模型请求；独立 Runner 会先初始化数据库 schema，避免 citation audit 缺表被静默吞掉。
- [x] 生产执行异常写入 `output/error.json`，manifest 标记 FAIL，CLI 返回非零。

#### Task 4.2：迁移 15 个案例和 Viewer

涉及文件：H02–H06、Viewer 测试。

- [x] 15 个原始案例文件按 Git blob 校验与 `archive/local-original` 完全一致。
- [x] Viewer 支持跨模块查找、成功结果、错误结果、缺失结果和确定性字段 diff；4 项 Harness 契约测试通过。

Checkpoint 4：✅ 以下命令对 11 个 Harness 模块共 15 个案例执行成功（15 PASS / 0 FAIL）；失败落盘和非零退出码由独立故障注入测试验证：

```bash
uv run --frozen python backend/tests/harness/runner.py diagnosis all --no-llm
# 其余模块由 manifest 驱动逐项执行
```

### Phase 5：前端 PDF 与 Markdown 对称验证

#### Task 5.1：依赖、lockfile 与样式

涉及文件：M04、X02、X03。

验收：`npm ci` 成功；经 Ponytail 审查拒绝引入重试失效且会绑定损坏 lockfile 的 `jit-pdf`，改用现有鉴权 Artifact API 与浏览器原生 PDF；无依赖变化。

- [x] 远程重构版 lockfile 可由 `npm ci` 完整重现：292 packages，0 vulnerabilities。

#### Task 5.2：可恢复的 PdfViewer

涉及文件：F01、X04。

验收：成功、失败、重试、URL 变化和卸载均有测试；同一展示动作只请求一次 PDF。

- [x] 共享 PdfViewer 的成功、失败、真实重试、路径变化与卸载均有组件测试；每个 path 每次挂载只发起一个 PDF Blob 请求。

#### Task 5.3：WorkspaceShell 双视图

涉及文件：M06、workspace 样式/测试。

验收：无 PDF 时按钮禁用；切换后显示对应同批次 PDF；不保留无消费者的 Blob object URL 状态。

- [x] Text/PDF tab 使用原生 button/ARIA tab 语义；PDF 仅按完全相同 basename 配对，禁止回退到其他批次。
- [x] WorkspaceShell 原两套 PDF Blob effect 已删除，报告区与资源区统一复用 PdfViewer。

#### Task 5.4：前端共享 Golden Cases

涉及文件：M05、X05、R10。

- [x] 前端测试直接读取后端 `normalization_test_cases.json`，14/14 逐 case 一致。

Checkpoint 5：✅ `npm ci`、Vitest 34/34、TypeScript 与 Vite 生产构建均通过；当前会话未提供 Chrome DevTools MCP，真实浏览器控制台检查保留为最终人工运行项，不伪造已执行证据。

### Phase 6：文档迁移与最终门禁

#### Task 6.1：历史原文归档和活动文档重写

涉及文件：D01–D04、X13–X15、`docs/README.md`。

验收：活动文档中不存在 `backend/modules/` 或 `/Users/...`；历史原文仍可追溯。

#### Task 6.2：全量回归和验收报告

涉及文件：X12、X16。

执行并记录：

```bash
uv run --frozen pytest -q
uv run --frozen python scripts/check_repository_hygiene.py
uv run --frozen python scripts/check_local_new_parity.py
cd frontend && npm ci
cd frontend && npm test
cd frontend && npm run build
git diff --check
git status --short
```

如果单次全量测试受平台问题中断，必须记录原因并按目录分组执行全部测试；不得把“命令超时”写成“测试通过”。

---

## 7. TDD 与提交顺序

每个行为修改遵循：失败测试 → 最小修复 → 专项通过 → 相关模块回归 → 小提交。

建议本地提交顺序：

1. `chore: add local-new parity manifest and runtime boundaries`
2. `test: restore citation URL normalization coverage`
3. `fix: port citation URL normalization to domain modules`
4. `test: define unified render contracts`
5. `feat: port unified report rendering foundation`
6. `feat: add PDF outputs to CN domain modules`
7. `feat: add PDF outputs to EU and US domain modules`
8. `test: port domain-aware module harness`
9. `feat: restore resilient PDF workspace preview`
10. `docs: record local-new parity and migration evidence`

实施期间不执行远程 push、PR、merge 或历史重写。

---

## 8. 风险与阻断条件

| 风险 | 级别 | 处理方式 |
|---|---|---|
| 误用 `archive/local-full` | 阻断 | parity 脚本固定拒绝该 ref；`app.css` 254915→162 bytes、lockfile 174784→170534 bytes 仅作为冲突损坏证据 |
| Diagnosis HTML 结构退化 | 阻断 | 回归测试先行；列表/表格/标题不等价则不替换旧实现 |
| Harness 仍依赖 `backend.modules` | 阻断 | parity 脚本和 import 测试直接失败 |
| `package.json` 与 lockfile 不一致 | 阻断 | `npm ci` 必须成功 |
| 12 模块任一原输出键消失 | 阻断 | 输出矩阵测试失败，不允许以“统一”为由删旧能力 |
| PDF 只有路径、文件无效 | 阻断 | 文件签名 + pypdf 打开检查 |
| Citation 专项未被默认 pytest 收集 | 阻断 | 使用标准 `test_*.py` 文件名并核对 collected tests |
| 活动文档继续指向旧目录 | 高 | 文档静态检查失败 |
| `jit-pdf` bundle/依赖显著增加 | 中 | 保持动态加载，记录构建产物大小和许可证 |
| ArtifactRegistry 引入路径穿越 | 高 | task/module 输入校验和安全测试 |
| 本地运行数据被误删 | 阻断 | 只增加 ignore，不删除现有 `runs/`、storage 或 trace |

---

## 9. 最终验收证据表（实施时填写）

| Gate | 命令/检查 | 预期 | 实际 | 状态 |
|---|---|---|---|---|
| G01 | 共同祖先、两个 tip 与本地增量清单 | 15/34 分叉；排除运行产物后 34 A / 21 M / 1 D，共 56 项 | 5 个单元测试通过；Git 复算 56 项通过 | ✅ |
| G02 | Citation 专项 | 33 项及新增模块断言通过 | 原始 33 + domain 5 通过；Citation 全目录 65 通过；相关 domain 112 通过 | ✅ |
| G03 | Backend normalization | 全部共享 cases 通过 | 原始 14/14 Golden Cases 通过 | ✅ |
| G04 | Frontend normalization | 与后端逐 case 一致 | 共享 JSON Golden Cases 14/14 通过 | ✅ |
| G05 | Render unit tests | PDF/MD/HTML/DOCX 全通过；未使用 registry 有证据地拒绝 | Render + services 32 项通过 | ✅ |
| G06 | 12 模块输出矩阵 | 12/12，不减少旧输出 | 12/12 有可执行有效 PDF 证据；CN/EU/API/Service 141 项 + US 45 项通过 | ✅ |
| G07 | Harness | 11 模块、15 cases 可运行 | 15/15 no-LLM 案例通过；4 项契约测试通过；原始案例 blob 15/15 一致 | ✅ |
| G08 | Frontend install | `npm ci` 成功 | 292 packages installed，0 vulnerabilities | ✅ |
| G09 | Frontend tests/build | Vitest 与 Vite build 成功 | Vitest 34/34；tsc + Vite build 成功 | ✅ |
| G10 | Backend full suite | 全量通过或逐目录全覆盖通过 | 待执行 | ⬜ |
| G11 | Repository hygiene | 通过 | 待执行 | ⬜ |
| G12 | Git scope | 无意外文件、无 secrets、`git diff --check` 通过 | 待执行 | ⬜ |

---

## 10. 当前结论

本文件已经把“本地完整 `new` 的 15 个功能提交”转换为面向团队重构架构的迁移任务。当前只完成计划与审计口径修正，尚未修改业务代码，也尚未把任何 Gate 标记为通过。人工确认本清单后，按 Phase 0 → Phase 6 顺序实施。
