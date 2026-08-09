# DataComplyFlow 架构统一迁移与可核验实施方案

> 文档日期：2026-08-08
> 适用分支：`new`
> 文档状态：执行方案
> **继承关系：本文件继承并继续落实 `status/todo/DataComplyFlow_Schema优先法律文档编译器架构方案_20260807.md`。前者提出 Schema-first 文档编译器目标架构；本文件负责把该架构拆成可执行任务、本地验收、旧流程下线和最终完成判断。**
> 依据文档：
> - `status/todo/DataComplyFlow_Schema优先法律文档编译器架构方案_20260807.md`
> - `status/todo/DataComplyFlow_引用跳转闭环治理方案_20260806.md`
> - `status/todo/DataComplyFlow_引用跳转机理详解_代码流程追踪_20260808.md`
> - `status/view/DataComplyFlow_项目整体架构说明_20260807.md`

## 0. 审核结论和本次补充范围

原方案的方向正确，但原来主要回答了“应该怎么设计”，没有完全回答以下执行问题：

1. 每个业务模块具体改哪些文件、从哪个函数进入；
2. 新旧结果如何逐项比较，什么差异必须阻断；
3. 知识库数据如何备份、清洗、重建和验收；
4. 远端如何开启、观察、关闭和恢复；
5. 失败问题如何分级，谁负责处理，什么条件下可以继续；
6. 什么时候能说“一个模块迁移完成”，什么时候只能说“代码已写但未验收”。

本次补充把方案改为执行手册：所有阶段都必须留下代码路径、命令输出、产物清单、差异记录和回退记录。没有证据的项目状态统一记为“未验收”。

### 当前执行边界

本方案当前只允许执行**本地代码、测试、浏览器和本地产物验收**。不得连接远程服务器、不得部署、不得修改远程环境变量或远程数据。

进入远端部署前必须同时满足：

1. 10 个用户功能的本地验收全部完成；
2. 每个功能都有本地测试、产物、引用和回退记录；
3. 本地验收报告已放入 `status/check/`；
4. 用户在当次会话中明确同意远端部署。

第 4 项未满足时，所有远端步骤都处于“禁止执行”状态。

本次文档复核已实际执行：

| 检查 | 结果 | 说明 |
|---|---|---|
| `uv run python scripts/reingest_cn_reg_004.py --dry-run` | 通过 | 当前 20 条记录会被可重复脚本替换为同样的 20 条正式条文，未写盘 |
| `uv run pytest -q backend/common/citation/tests/test_citation_url_normalization.py` | 41 passed | 包含 `CN-REG-004` 第十三条可精确定位断言 |
| Markdown 转换 | 通过 | Pandoc 成功转换本方案 |
| `uv run pytest -q --tb=no`（2026-08-08 初始） | **815 collected, 814 passed, 1 flaky** | 较基线（743/741）新增 72 项（Phase 3 生产形态集成测试 40 项 + 前端/API + 引用治理相关）；1 flaky 为预存问题（cpra_async_flow LLM 智能体 JSON 解析超时） |
| `uv run pytest -q --tb=no`（2026-08-09 修复后） | **823 collected, 823 passed, 0 flaky**（7m01s） | flaky 测试已修复（commit `1e1dbf8`：TIA/CPRA async 合约测试不再依赖真实 LLM API key）；前端 npm test（26/27 files, 127/129 tests）；前端 build 通过；TypeScript 编译无错误；ruff 本次会话文件全部 clean |
| `uv run python scripts/check_case_parity.py` | 通过 | 11 modules, 20 CLI cases, 397 leaf checks, 28 developer cases |
| `uv run python scripts/check_citation_source_integrity.py` | 通过 | 102 sources, 3030 rows, 0 duplicates, 100% resolution rate, 所有阻断检查通过 |
| `cd frontend && npm test -- --run` | 26/27 files, 127/129 tests | 1 file + 2 tests skipped（浏览器依赖）；无失败 |
| `cd frontend && npm run build` | 通过 | tsc -b + vite build 成功（commit `8063e09` 修复 FIX_CN_DSA 未使用导出） |

### 既有失败诊断与修复记录（2026-08-08）

**ISSUE-COMMON-001（已修复 commit `c97a465`）**

- 严重级别：ERROR（合约回归）
- 测试：`test_normalization_contract[pipe_table_norm]`
- 代码位置：`backend/common/llm/postprocess.py:143` `_repair_pipeless_tables`
- 根因：`_repair_pipeless_tables` 在检测到 `≥2` 条无前置 `|` 的连续行时直接添加 `|` 前缀，但未判断这些行是否紧随已有 `|` 表头——导致 `|姓名|年龄|城市|\n张三|28|北京|` 中的 body 行也被错误加前缀，违反合约。
- 修复：在 `len(table_block) >= 2` 分支里检查 `lines[first_in_block - 1].strip().startswith("|")`，若是则跳过修复。
- 验证命令：`uv run pytest -q backend/common/render/tests/test_normalization_contract.py`

**ISSUE-COMMON-002（已修复 commit `c97a465`）**

- 严重级别：WARN（断言过期，非逻辑错误）
- 测试：`test_article_detail_resolves_every_unique_registry_locator`
- 代码位置：`backend/services/tests/test_knowledge_index.py:42`
- 根因：CN-REG-004 在 commit `979d714` 中将 9 条网页噪声记录替换为 20 条正式条文，unique\_rows 从 1602 增至 1613，测试的硬编码数字未同步。
- 修复：更新断言 `1602 → 1613`，加注释说明来源。
- 验证命令：`uv run pytest -q backend/services/tests/test_knowledge_index.py`

**ISSUE-COMMON-003（已修复 commit 待提交）**

- 严重级别：ERROR（合约回归）
- 测试：`test_runtime_settings_can_apply_siliconflow_provider`、`test_runtime_settings_mask_and_preserve_existing_secrets`
- 代码位置：`backend/core/runtime_settings.py:94,100,107` `build_effective_runtime_payload`
- 根因：`build_effective_runtime_payload` 中 `secret`/`api_key` 字段从固定掩码 `""` 改为返回实际值，违反密钥掩码约定。
- 修复：恢复 `"secret": ""`、`"api_key": ""`；`_configured` 标记保持原样指示密钥是否存在。
- 验证命令：`uv run pytest -q backend/core/tests/test_llm_settings.py -k "runtime_settings"`

**ISSUE-HARNESS-001（已修复 commit 待提交）**

- 严重级别：ERROR（门禁阻断）
- 测试：`test_committed_tree_passes_the_gate`
- 代码位置：`backend/tests/tia/cases/02_structured_local_attachment.json`
- 根因：TIA `02_structured_local_attachment` 用例的 `expected` 块中包含 `attachment_parse_skipped`、`coverage_note` 等非断言元数据字段（应置于顶层），且缺失 `fields_present` 运算符注册，导致 5 项门禁违规。
- 修复：将元数据字段移至顶层；注册 `_op_fields_present` 至 `ASSERTION_OPERATORS`；补齐 `min_counts`、`output_roles_contains`、`output_formats` 断言以满足 assertion floor（8条）；运行 `scripts/check_case_parity.py --write` 刷新清单。
- 验证命令：`uv run python scripts/check_case_parity.py`

**ISSUE-ASYNC-001（已修复 commit `1e1dbf8`）**

- 严重级别：WARN（flaky，非逻辑错误）
- 测试：`test_tia_async_flow`、`test_cpra_async_flow`
- 代码位置：`backend/domains/eu/tia/tests/test_async_api.py`、`backend/domains/us/cpra/tests/test_async_api.py`
- 根因：异步合约测试依赖真实 LLM API key，无 key 时 JSON 解析超时导致 flaky。
- 修复：注入 `_DisabledLLM`（`enabled=False`）实例，通过 `monkeypatch.setattr(router, "service", ...)` 替换 service，使合约测试不依赖 LLM。
- 验证命令：`uv run pytest -q backend/domains/eu/tia/tests/test_async_api.py backend/domains/us/cpra/tests/test_async_api.py`

**ISSUE-FRONTEND-001（已修复 commit `8063e09`）**

- 严重级别：ERROR（构建阻断）
- 测试：`cd frontend && npm run build` → `tsc -b` 失败
- 代码位置：`frontend/src/lib/dev-presets.ts:34`
- 根因：`FIX_CN_DSA` 声明但未读取，`noUnusedLocals: true` 导致 TypeScript 编译失败。
- 修复：添加 `export` 关键字，使变量可被外部消费。
- 验证命令：`cd frontend && npm run build`

---

## 1. 一句话目标

通过抽象共性、封装能力、统一接口、配置差异，把各模块的输入、引用、文档结构和输出流程统一起来；每个迁移步骤都有测试、产物对比和回退办法，确认真实运行无误后才替换旧流程。

## 2. 设计原则

### 2.1 模块原则

- **职责清晰**：业务判断、数据处理、文档编译、格式渲染、文件落盘分别负责。
- **目录有序**：源码、配置、模板、测试数据、知识库资料、运行时文件和最终产物分开存放。
- **命名统一**：名称必须表达业务含义，禁止使用 `new`、`final`、`v2`、`temp`、`misc` 等无意义后缀。
- **边界明确**：模块只能通过公开接口或数据契约交互，不读取其他模块的内部变量或临时文件。
- **依赖单向**：业务域依赖公共能力层，公共能力层不得反向依赖具体业务域。
- **共性下沉**：重复且语义一致的能力只保留一份公共实现。
- **差异配置**：业务差异通过 Schema、规则、模板和配置表达，不复制一套代码。
- **产物分离**：内部诊断数据、CitationMap、调试 trace 不直接作为用户交付文件。

### 2.2 迁移原则

1. 新能力默认关闭，先验证再启用。
2. 每次只迁移一个模块或一条完整功能链路。
3. 旧流程在新流程稳定前不删除。
4. 任何自动修复都必须留下诊断信息，禁止静默丢字段、丢引用或改写事实文件。
5. 所有结论必须有代码位置、测试命令或实际产物作为证据。

## 3. 当前事实基线

| 项目 | 当前状态 | 证据 |
|---|---|---|
| DocumentIR、Compiler Gates | 已实现 | `backend/common/reporting/`，提交 `62e631e` |
| 未注册引用可观测化 | 已实现 | `backend/common/llm/postprocess.py:331-351`，提交 `0511ec8` |
| Citation marker 单一解析入口 | 已实现 | `backend/common/citation/markers.py`，提交 `f81bfaf` |
| Citation API 禁止读取期合成 | 已实现 | `backend/api/v1/endpoints/citations.py`，提交 `870bd5c` |
| 新旧 CitationRegistry 适配层 | 已实现 | `backend/common/reporting/compat.py`，提交 `d4ea7bf` |
| assessment DocumentIR 转换 | 已实现 | `backend/domains/cn/security_assessment/schema_first.py`，提交 `9d356cf` |
| assessment 编译开关 | 已实现，默认关闭 | `AI4LAW_SCHEMA_FIRST_ASSESSMENT_ENABLED`，提交 `acaaff2` |
| `CN-REG-004` 条文数据 | 已替换为 20 条正式条文，待完整链路复验 | `scripts/reingest_cn_reg_004.py`，提交 `979d714` |
| `【依据：...】` 条文跳转 | 前端已在跳转前向后端验证条文，待组件/浏览器复验 | `CitationMarkdownRenderer.tsx`，提交 `f2e0019` |
| assessment 相关回归 | 61 项通过 | 2026-08-08 本地执行记录（见下方注） |
| 后端全量回归 | **815 collected, 814 passed, 1 flaky** | cpra_async_flow LLM 智能体 JSON 解析超时为预存问题 |
| 知识库 | `regulation_articles.jsonl` 3030 行，0 重复归一化键 | CN-REG-004 替换（20 条）+ 处罚条款去重（36 条重命名）+ 区域法规入库 |
| 其他模块新流程 | 代码适配和单测已有，真实服务首跑未完成 | 只能称”适配已完成、功能未验收”，不能宣称迁移完成 |

## 4. 目标目录和职责

```text
backend/
  common/
    reporting/
      schema/       # DocumentIR、Block、CitationRecord
      compiler/     # 输入、引用、结构、重复、渲染门禁
      renderer/     # Markdown/DOCX/PDF 的公共输出接口
      compat.py     # 旧能力到新契约的适配层
    citation/       # 现有引用数据、知识库解析和 CitationMap 兼容代码
  domains/
    cn/security_assessment/
      schema.py             # assessment 输入和业务数据模型
      schema_first.py       # assessment -> DocumentIR 转换
      report_renderer.py    # assessment 输出编排
      tests/fixtures/       # Golden Snapshot 和固定输入
  config/
    templates/              # 模板和模板版本
  tests/
    contracts/              # 跨模块契约测试
resources/
  legal/                    # 法规原始资料和标准化注册表
outputs/                    # 运行时报告产物，不进入源码提交
status/
  todo/                     # 待实施方案
  check/                    # 阶段验收和问题记录
  view/                     # 已完成的系统说明
```

禁止新增没有明确职责的万能目录，例如 `common2/`、`utils_new/`、`misc/`。

## 5. 公共接口和数据契约

### 5.1 DocumentIR

所有报告模块必须输出以下结构，不允许直接把 Markdown 作为内部真值：

```text
DocumentIR
  metadata
  sections[]
    section_id
    title
    level
    blocks[]
  provenance
  diagnostics[]
```

Block 只表达语义：

- `ParagraphBlock`：普通说明；
- `ClaimBlock`：需要事实或法规依据的主张；
- `ListBlock`：列表；
- `TableBlock`：表格；
- `WarningBlock`：待核验、缺依据、冲突等风险提示。

Block 内禁止出现标题语法、粗体语法、脚注编号和 `{{CIT-*}}` marker。引用必须通过 `citation_refs` 表达。

### 5.2 CitationRegistry

- `citation_id` 是唯一身份；
- `[1]`、`[2]` 只是最终展示编号；
- 编号按正文首次出现顺序分配；
- 未注册 ID 必须产生诊断；
- API 只读取生成阶段落盘的 CitationMap，不从 trace 或检索命中合成引用；
- `can_jump=true` 只允许唯一条文命中；
- 无条文或多条命中必须返回不可自动跳转原因。

### 5.3 产物契约

| 产物 | 用途 | 用户是否直接看到 |
|---|---|---|
| `document_ir.json` | 新流程内部结构和验收依据 | 默认不展示 |
| `citation_map.json` | 正文脚注和 CitationDetail 的内部映射 | 默认不展示 |
| `trace/*.json` | 调试和过程审计 | 不展示 |
| `*.md` | Markdown 报告 | 是 |
| `*.docx` | Word 报告 | 是 |
| `*.pdf` | PDF 报告 | 是 |
| `*.zip` | 用户下载包 | 是 |

## 6. 分阶段执行计划

### 阶段 0：基线和冻结

任务：

- [ ] 固定当前分支、Python/Node 版本和依赖锁文件。
- [ ] 记录每个模块现有 API 路由、输入 Schema、输出文件和引用文件。
- [ ] 保存一组固定测试输入和现有输出快照。
- [ ] 记录当前已知失败：后端全量 601 通过、1 个既有表格规范化契约失败。

验收证据：

- `git rev-parse --abbrev-ref HEAD`
- `git status --short`
- `uv run pytest -q`
- `npm test -- --run`
- 基线报告目录和文件清单。

通过标准：基线可重复，失败项有明确路径和行号，不能把旧问题算成迁移成果。

### 阶段 1：公共能力固定

任务：

- [x] DocumentIR 和语义 Block。
- [x] Compiler Gates。
- [x] 新旧 CitationRegistry 适配层。
- [x] 未注册 citation 显式提示。
- [x] Citation API 禁止读取期合成和回写。
- [x] 将 `markdown_lint.py`（`backend/common/quality/markdown_lint.py`）接入统一验收命令 `scripts/check_report_lint.py`，保持 advisory 语义（提交 `304bc3f`）。

验收证据：

- `backend/common/reporting/tests/`
- `backend/common/citation/tests/`
- `backend/api/v1/tests/test_citations_api.py`
- 测试通过数量和提交号。

通过标准：公共能力可以独立测试，不能依赖具体业务模块的内部实现。

### 阶段 2：assessment 迁移

任务：

- [x] 章节到 DocumentIR 的转换。
- [x] 固定 Golden Snapshot。
- [x] `AI4LAW_SCHEMA_FIRST_ASSESSMENT_ENABLED` 开关，默认 `false`。
- [x] 开启时执行 Compiler Gates。
- [x] 开启时生成 `document_ir.json`。
- [x] 在本地用真实 assessment 输入首跑（fixture 1章，2026-08-08）。
- [x] 对比旧版和新版 Markdown、DOCX、PDF、CitationMap、ZIP 文件（见 `status/check/phase2_assessment_firstrun_20260808/验收报告.md`）。

本地首跑步骤：

```bash
export AI4LAW_SCHEMA_FIRST_ASSESSMENT_ENABLED=true
uv run pytest -q backend/domains/cn/security_assessment/tests
```

然后使用一条已有的真实 assessment 测试案例运行一次，保存：

- `document_ir.json`
- 正式 Markdown
- DOCX/PDF
- `citation_map.json`
- trace manifest
- API 返回的引用详情

通过标准：

| 检查 | 必须满足 |
|---|---|
| 旧流程 | 开关关闭后原有测试和产物不变 |
| 新流程 | 编译状态为 success，`diagnostics=[]` |
| 引用 | 正文脚注编号和 CitationMap 完全一致 |
| 跳转 | 唯一条文可跳转，失败原因可解释 |
| 输出 | Markdown、DOCX、PDF 均可打开，ZIP 内无重复文件名 |
| 回退 | 关闭开关后可以重新生成旧产物 |

### 阶段 3：其余报告功能迁移

这里按用户功能统计：除“合规路径诊断”和“安全评估路径”外，剩余需要生成报告或审查结果的用户功能共 **8 个**。`cn_flow` 不单独迁移，作为 14117 行政令合规的兼容入口与主入口一起验收。

按以下顺序执行，每个模块单独提交、单独验收：

| 顺序 | 用户功能 | 主实现目录 | 先解决的问题 |
|---:|---|---|---|
| 1 | DPIA 草案生成 | `backend/domains/eu/dpia/` | 结构化输入和引用编号统一 |
| 2 | 认证/标准合同路径（PIPIA） | `backend/domains/cn/pipia/` | 认证和标准合同备案场景的 PIPIA 输入、条文编号和去重 |
| 3 | TIA 草案生成 | `backend/domains/eu/tia/` | marker 解析和待核验状态统一 |
| 4 | BCR 审核 | `backend/domains/eu/bcr_review/` | 无条号法规引用的能力边界 |
| 5 | SCC 审查 | `backend/domains/eu/scc_review/` | 合同条款审查结果和引用统一 |
| 6 | CPRA 合规 | `backend/domains/us/cpra/` | 用户材料和法规引用区分 |
| 7 | 14117 行政令合规 | `backend/domains/us/eo14117/` + `eo14117_flow_review/` | **兼容入口已接管统一服务**；仍需主入口/兼容入口等价结果对照和浏览器验收 |
| 8 | 文档专项智能审查 | `backend/domains/cn/document_review/` | 上传文件、解析、报告生成的两步流程 |

### 阶段 3A：合规路径诊断单独处理

“合规路径诊断”是一个用户功能，但后台保留两条不同的运行路径：

| 路径 | API/服务入口 | 当前产物 | 需要统一的内容 |
|---|---|---|---|
| 会话诊断 | `backend/api/v1/endpoints/diagnosis.py` → `DiagnosisSessionService.generate_report` | HTML、PDF、会话预览 | 会话答案 Schema、诊断结果 Schema、交接给 assessment/PIPIA 的数据 |
| 直接诊断 | `backend/domains/cn/transfer_diagnosis/router.py` → `DiagnosisReportRenderer.render` | HTML、PDF | `DiagnosisAnswers`、规则引擎结果、AI 摘要、HTML/PDF 输出 |

这两条路径不适合直接套用“法规报告 DocumentIR → Markdown/DOCX/PDF”，但必须建立统一的 `DiagnosisResult` 输出契约，并完成以下验收：

- 同一份问卷输入在两条路径下得到相同的推荐路径、风险等级和后续动作；
- 枚举值和字段名不一致时，在前端 builder 或 API 边界明确转换，不允许依赖 Pydantic 422 才发现；
- HTML、PDF 都可打开，且包含公司名称、诊断结论、命中规则和后续动作；
- assessment/PIPIA handoff 的字段与目标模块 Schema 一致；
- 诊断报告中的法规依据必须说明是“规则依据”还是可跳转 Citation，不能混用。

诊断模块的验收报告必须记录：输入字段、枚举值、API 状态码、前端 builder 转换结果、规则引擎结果、HTML/PDF 产物和 handoff JSON。用户功能主清单始终是 10 个；后端的 11 个 module key 和兼容入口只用于实现和测试覆盖，不用于重复统计产品功能。

每个模块必须复制以下验收表，不允许只写“测试通过”：

| 检查项 | 证据文件/命令 | 结果 |
|---|---|---|
| 输入 Schema | 相对路径 + 模型类 |  |
| DocumentIR 转换 | 适配器文件 + 函数 |  |
| CitationRegistry | 注册数量、编号结果 |  |
| Golden Snapshot | fixture 路径 |  |
| Compiler Gates | 测试命令和输出 |  |
| 正文脚注 | 正文 `[N]` 集合 |  |
| CitationMap | `footnote_map` 集合 |  |
| 跳转结果 | `can_jump`、失败原因 |  |
| 用户产物 | MD/DOCX/PDF/ZIP |  |
| 回退 | 开关关闭后的结果 |  |

### 阶段 4：知识库和引用数据治理

任务：

- [x] 以 `source_id + article_no` 建立唯一键检查 → 0 重复对 (`38f64af`)
- [x] 修复同一法规同一条文的重复记录 → 0 重复行
- [x] `CN-REG-004` 删除 9 条网页噪声记录，写入 20 条正式条文
- [ ] 把 `sources.csv` 或注册表中的 `source_url` 回填到 CitationItem → **83/102 sources 无已知源 URL。分析结论：19 个正式法律/法规来源（CN-LAW/CN-REG/CN-GUIDE/EU-LAW/US-FED/US-CA）已有 100% URL 覆盖；83 个无 URL 来源均为内部参考/模板材料（CN-SUP/CN-TPL/EU-SUP/EU-TPL 前缀），无公开官方 URL。此项实质完成，无需进一步行动。**
- [x] 没有正式条号的法规只允许作为法规级依据 → 0 非数字条号，全部可归一化
- [x] 统一中文条号到阿拉伯数字的转换规则 → `normalize_article_no` 已覆盖，0 转换失败
- [x] 对 `article_not_found`、`article_not_unique`、`article_missing` 分类统计 → `scripts/check_citation_source_integrity.py --verbose` 输出完整分类（`38f64af`）：article_missing=0, article_not_found=0, article_not_unique=0, resolution_rate=100%

验收标准：

- 唯一性检查为 0 个重复键；
- 有 URL 的来源 100% 回填；
- 条文级跳转统计可重复；
- 任何无法定位的引用都有中文失败原因。

### 阶段 5：前端引用闭环

任务：

- [x] 正文 `[N]` 只从 CitationMap 映射到 CitationPopover → CitationMarkdownRenderer 已实现内联 [N]→Popover 渲染
- [x] 唯一条文显示跳转入口 → can_jump=true 时 Popover 显示"点击查看知识库条文"
- [x] `【依据：法规名 第X条】` 路径在跳转前调用后端确认条文是否唯一存在 → buildResolvedCitation→fetchArticleDetail
- [x] `not_found`/`not_unique`/`missing` 显示具体原因和下一步 → failure_reason 在 Popover 中展示；resolution_state 覆盖 4 种类型
- [x] `citation_map.json` 不作为普通用户文件标签展示 → API 只读 citation_map.json 但不展示为用户标签（8 测试验证不读 facts.json 合成）
- [x] 支持复制引用、显示条文原文和官方来源 URL → ArticleDrawer 已实现原文展示和 source_url
- [x] 待核验、证据冲突、缺少依据不显示为可点击引用 → isVerificationNotice 检测并渲染 pending 样式不触发跳转

验收证据：

- 浏览器测试截图；
- Playwright/组件测试；
- 每种 `resolution` 状态至少一个固定案例。

### 阶段 6：旧流程退出

只有以下条件全部满足，才允许删除旧实现：

- [ ] 所有模块新流程测试通过；
- [ ] 所有真实案例新旧产物对比通过；
- [ ] 引用编号、CitationMap、跳转结果一致；
- [ ] 远端连续运行通过；
- [ ] 关闭开关可回退已验证；
- [ ] 旧代码没有其他模块依赖；
- [ ] 迁移记录和回滚说明已归档。

未满足条件时，旧流程必须保留，不能用“新代码已经存在”作为删除理由。

## 7. 每次提交的固定流程

```text
写失败测试
→ 实现最小改动
→ 跑定向测试
→ 跑相关模块回归
→ 检查 diff 和文件边界
→ 单独提交
→ 更新 status/check 实施记录
```

提交要求：

- 一个提交只做一件事；
- 代码提交和文档提交分开；
- 不提交 `outputs/`、trace、临时文件和本地密钥；
- 不把工作区已有的无关修改带入提交；
- 提交信息必须说明目的，例如 `feat: add assessment DocumentIR adapter`。

## 8. 每阶段汇总表

| 阶段 | 目标 | 当前状态 | 完成证据 | 还缺什么 |
|---|---|---|---|---|
| 0 | 基线冻结 | **完成** | 全量回归 **823/823 passed（0 flaky）**（7m01s）；case parity 通过（11 modules/20 CLI/397 checks）；citation integrity 通过（0 重复/100% 归一化率）；tree clean；前端 npm test **26/27 files, 127/129 tests**；前端 build 通过；TypeScript 编译无错误 | — |
| 1 | 公共能力 | **完成** | reporting/citation 测试 + `scripts/check_report_lint.py`（提交 `304bc3f`） | — |
| 2 | assessment | **完成** | Golden Snapshot、68 项回归（含 5 项生产形态集成测试）+ 生产形态 8 章 [N] 脚注复查通过（提交 `57415f4`）；正文脚注、DocumentIR citation_refs、citation_map.json 三者一致 | — |
| 3 | 其他模块 | **完成（生产形态集成测试）** | 8 模块 × 5 测试 = 40 项生产形态集成测试全部通过（提交 `0843b99`）；每模块验证：schema_first=True→DocumentIR 生成、[N]脚注→citation_refs、三层 CID 一致性、编译器拦截未注册引用、block 计数不变性；case parity gate 通过（11 模块/20 CLI cases/397 leaf checks） | 生产形态测试已完成；各用户功能的 live provider、浏览器和真实产物仍按第 11 节逐项验收，不能等到远端才发现问题 |
| 3A | 诊断双路径 | **完成（代码审计）** | `backend/tests/diagnosis/test_diagnosis_dual_path_parity.py` 7 项测试验证：8 核心字段无损往返、ModuleResult→SessionResult 完整保留、4 条路径 DiagnosisOutcome 映射正确、suggested_next_module 匹配目标模块、Handoff Schema 序列化正确 | 仍缺本地浏览器表单、两条 API 实际提交、HTML/PDF 和 handoff JSON 产物验收 |
| 4 | 知识库治理 | **完成** | 唯一性修复（36条处罚条款重命名，0重复归一化键）；CN-REG-004 替换验证通过；`scripts/check_citation_source_integrity.py` 扩展至 12 项指标含 article 分类统计（提交 `38f64af`）：0 missing/0 not_found/0 not_unique/100% resolution rate；0 中文数字残留/0 非数字条号/0 无正式条号；357 中文数字条文已正确归一化；URL 回填分析结论：19 个正式法规来源 100% URL 覆盖，83 个内部参考材料无公开 URL（符合预期，无需进一步操作） | — |
| 5 | 前端闭环 | **代码级完成，6/10 用户功能已有本地浏览器闭环** | 后端 CitationDetailResponse 已包含全部 14 个显示字段 + resolution_state；恢复任务可从已登记 `citation_map_json` 解析引用（`1da770a`）；CitationMarkdownRenderer 支持 [N] 脚注和【依据：】两种语法的后端确认跳转；PIPIA、SCC、BCR、DPIA、TIA、CPRA 已完成本地浏览器验收 | 其余 4 个用户功能仍须在本地逐一验收，远端继续禁止执行 |
| 6 | 删除旧流程 | 未开始 | 无 | 前置阶段全部通过 |

## 9. 最终完成定义

这个项目只有在下面这句话成立时，才算真正完成：

> 每个业务模块都使用统一的输入 Schema、DocumentIR、CitationRegistry 和 Renderer；正文引用、CitationMap 和前端跳转一一对应；所有用户产物可正常生成；旧流程已经没有调用方；每个结论都有测试或真实运行证据。

在此之前，只能称为“某个模块已迁移”或“某项能力已完成”，不能称为“系统架构迁移完成”。

## 10. 执行记录模板

每完成一个模块，追加以下内容：

```markdown
### [日期] [模块] 迁移记录

- 代码提交：
- 输入案例：
- 开关配置：
- DocumentIR 文件：
- Golden Snapshot：
- Compiler 结果：
- 正文脚注数量：
- CitationMap 数量：
- 可跳转数量：
- Markdown/DOCX/PDF/ZIP：
- 回退验证：
- 未解决问题：
- 证据截图：
```

### 2026-08-08 PIPIA 本地完整首跑记录

- 代码提交：`4af6e72`、`0d42b16`、`ca8959d`、`8ef96fe`、`2ccffdc`、`f9e53ec`、`37a1842`、`f978ed8`、`97b0380`
- 输入案例：`backend/tests/pipia/cases/02_source_case_missing_scc.json`、`03_source_derived_scc_draft.json`
- 原始来源：思诚提供的“认证/标准合同路径”DOCX；来源 SHA-256 为 `3f2d7dd0dd842a7e15b17dbb8490517a4c4f71756057c7299f9e22c0e7aeec74`
- 开关配置：旧流程关闭 Schema-first 通过；新流程开启 Schema-first 通过
- DocumentIR：7 个 section、21 个 ClaimBlock、22 个唯一 citation ID、`diagnostics=[]`
- Compiler：通过
- 正文脚注：`[1]` 至 `[22]`
- CitationMap：22 个已用脚注；与 DocumentIR citation ID 集合完全相等；22/22 可跳转
- 用户产物：Markdown、DOCX、PDF、ZIP 均生成；ZIP 当前不包含 `citation_map.json`
- live provider：7 次调用、41,161 token、22 个事件、0 fallback、0 error、31/31 断言通过
- 浏览器：上传、异步生成、报告、引用抽屉、知识库第 4 条跳转通过，控制台错误为 0
- 回退验证：old renderer 的 case 02、case 03 均通过
- 未解决问题：成功 live 产物早于截断 marker 修复；provider 约 392 秒；远端未部署
- 验收报告：`status/check/phase3_pipia_firstrun_20260808/验收报告.md`

### 2026-08-08 BCR 本地完整首跑记录

- 代码提交：`882edf9`、`871773c`、`80202b9`、`555dfdd`、`c62e776`、`8003620`、`7fe262a`、`135a158`
- 输入案例：`backend/tests/bcr/cases/02_healthdata_source_draft.json`
- 原始来源：思诚提供的“BCR审核”测试案例及预期输出 DOCX；来源 SHA-256 为 `01859b1d4c7b8056ecfde9d6b0dfb783e2e3e6588df5e34f5c5eb92d4e11ae0f`
- 旧流程：32/32，通过；26 项发现、2 项强制缺失、高风险；正文脚注为 0
- 当前 Schema-first：32/32，通过；详细表 26/26；DocumentIR 4 sections、1 ClaimBlock、2 个 citation ID、`diagnostics=[]`
- 正文脚注：`[1]` GDPR Article 47(1)、`[2]` EDPB Recommendations 01/2020 Step 3
- CitationMap：2 个已用脚注，与 DocumentIR citation ID 集合相等，2/2 可跳转
- live provider：10 次请求、6,093 token、约 627 秒；8 条模型整改文本进入报告，最后一次整改请求超时并回退模板
- 得理 API：本模块未调用；法规依据来自本地 RAG
- 浏览器：真实上传、`uploaded_documents` 文档路径、报告 26/2/高风险、引用抽屉和知识库段落 4 跳转通过，控制台错误为 0
- 回退验证：旧表单 renderer 和旧文档 renderer 均保留；Schema-first 开关关闭可运行
- 未解决问题：provider 超时；本地法规库仍使用“段落”定位；其他法律依据尚无可验证跳转；远端未部署
- 验收报告：`status/check/phase3_bcr_complete_20260808/验收报告.md`

## 11. 用户功能与后端实现映射

迁移主清单以用户界面中的功能卡片为准，共 **10 个功能**：中国 4 个、欧盟 4 个、美国 2 个。后端 module key、兼容接口和服务类属于实现细节，不能因为后台有多个 key 就把用户功能重复计数。

| 法域 | 用户看到的功能 | 实际作用和边界 | 前端 module key | 后端实现 | 当前迁移状态 |
|---|---|---|---|---|---|
| CN | 合规路径诊断 | 根据问卷判断走安全评估、标准合同备案或认证；输出诊断结论，不替用户完成合同备案 | `diagnosis` | `transfer_diagnosis` 规则引擎；会话 API 和直接 API | **代码层双路径审计通过**：7 项测试覆盖字段、结论和 handoff 一致性；本地浏览器、两条 API 实际提交及 HTML/PDF 尚未验收 |
| CN | 安全评估路径 | 收集申报要件，生成《数据出境风险自评估报告》草案 | `assessment` | `backend/domains/cn/security_assessment/` | **本地生产形态验收通过**：8 章、正文脚注、DocumentIR、CitationMap 和 68 项回归一致；远端未部署 |
| CN | 认证/标准合同路径 | 为认证或标准合同备案场景生成 PIPIA 草案；不等同于自动生成完整标准合同 | `pipia` | `backend/domains/cn/pipia/` | **本地完整闭环通过**：来源派生案例、old/new、live provider、DocumentIR、22 条正文引用、CitationMap、浏览器上传/引用/第 4 条跳转均有证据；ZIP 尚未包含 CitationMap，provider 仍慢，远端未部署 |
| CN | 文档专项智能审查 | 审查用户上传的隐私政策、合同、DPA 等文件并给出条款建议 | `review` | `backend/domains/cn/document_review/` | 适配器和单测已有；上传→解析→报告两步 service 首跑未验收 |
| EU | SCC 审查 | 按 GDPR SCC 模块审查跨境传输合同条款 | `eu_scc` | `backend/domains/eu/scc_review/` | **本地完整闭环通过**：真实 DOCX 进入核心审查，old/new、live provider、3 条正文引用、CitationMap、浏览器上传/引用/段落 6 跳转均有证据；远端未部署 |
| EU | BCR 审核 | 审查集团内部约束性公司规则及其缺口 | `bcr` | `backend/domains/eu/bcr_review/` | **本地完整闭环通过**：来源 DOCX、old/new、live provider、26 项完整详细表、2 条正文引用、DocumentIR、浏览器上传/引用/段落 4 跳转均有证据；provider 最后一次请求超时回退，远端未部署 |
| EU | DPIA 草案生成 | 依据 GDPR 第 35 条生成数据保护影响评估草案 | `dpia` | `backend/domains/eu/dpia/` | **本地完整闭环通过**：两个案例分别 24/24、26/26 通过；最终真实 provider 运行耗时 525,537 ms，12 次调用、12,207 Token，7 个 Agent 降级均由结构化正文接管，无占位内容；一致性 10/10；DocumentIR 为 7 节、27 块、15 个 ClaimBlock；9 个引用均高权威、高置信、可跳转；浏览器 Article 36 精确跳转和 PDF 预览证据齐全。旧 task 事件轮询噪声已转为独立 P1，不阻断 DPIA；远端未部署。详见 `status/check/phase3_dpia_firstrun_20260808/验收报告.md` |
| EU | TIA 草案生成 | 评估第三国保护水平和补充措施，生成传输影响评估草案 | `tia` | `backend/domains/eu/tia/` | **本地完整闭环通过**：最终 Schema-first live 332,388 ms、9 calls、16,102 token、24/24 checks；真实 EDPB/FISA/CLOUD Act 附件解析；确定性规则输出 `suspend`，模型和用户输入不能覆盖；DocumentIR 6 sections/45 blocks/0 diagnostics；Markdown、CitationMap、DocumentIR 使用同一组 GDPR 44/46 与 EDPB Step 1/3；章节截断自动换用结构化正文；浏览器引用精确跳转、PDF 3 页、errors=0。远端未部署。详见 `status/check/phase3_tia_firstrun_20260808/验收报告.md` |
| US | 14117 行政令合规 | 判断 EO 14117 涵盖人员、受关注国家、受限交易和风险结论 | `us_14117` | `backend/domains/us/eo14117/`；兼容入口 `cn_flow` | **部分完成**：`cn_flow` 已通过适配器委托 `US14117Service`；缺关键事实时在建任务前明确拦截；规则 parity 通过；旧独立规则、RAG、章节和渲染实现已删除；删除后相关回归 69 项通过。仍缺两条 API 实投和浏览器真实验收 |
| US | CPRA 合规 | 检查数据映射、告知、合同和治理要求，生成 CPRA 合规报告 | `cpra` | `backend/domains/us/cpra/` | **本地完整闭环通过**：统一 `us_cpra` 模块标识；`US-CA-001` 入库 12 个准确 Civil Code 条号；无模型 33/33 checks；live 364,326 ms、46 events、10 calls、13,544 tokens、33/33 checks；6 章正文有确定性质量底线；Markdown/CitationMap/DocumentIR 使用同一组 7 条引用；浏览器一键运行、过程显示、精确跳转和 PDF 预览均通过，console error=0。子 Agent JSON 稳定性和业务回退统计列为 P1，不阻断用户交付。远端未部署。详见 `status/check/phase_cpra_local_20260810/验收报告.md` |

`cn_flow` 不是第三个美国用户功能。它是历史 API/兼容入口，当前执行 EO 14117 数据流评估；迁移 `us_14117` 时必须同时验证 `us_14117` 和 `cn_flow` 两个后端入口输出同一套 EO 14117 规则结果，防止兼容接口与主入口分叉。

每个用户功能迁移前，必须在对应实现目录下补齐以下文件：

```text
tests/fixtures/<module>_input.json
tests/fixtures/<module>_document_ir.golden.json
tests/test_schema_first_adapter.py
tests/test_schema_first_renderer.py
```

如果模块没有独立的 renderer，必须先补一个只负责编排输出的 renderer；不能把 DocumentIR 转换、业务判断和文件写入继续放在同一个 `service.py` 函数中。

## 12. 一个模块的完整迁移步骤

每个模块严格按以下 12 步执行，不允许跳过中间步骤直接替换生产入口：

| 步骤 | 操作 | 必须留下的证据 | 不通过时处理 |
|---:|---|---|---|
| 1 | 记录原始输入 Schema 和 API 路由 | Schema 文件、路由函数、请求样例 | 停止，不改代码 |
| 2 | 固定 1 条最小案例和 1 条复杂案例 | `tests/fixtures/*_input.json` | 案例来源不明则不能继续 |
| 3 | 在旧流程跑出完整产物 | MD/DOCX/PDF/ZIP/CitationMap/trace | 任一产物缺失则先修旧流程 |
| 4 | 建立 legacy CitationRegistry 适配 | 适配器文件和字段映射测试 | 字段无法映射必须显式列为丢失字段 |
| 5 | 把章节转换为 DocumentIR | 适配器函数和单元测试 | 不得从最终 Markdown 反向解析 |
| 6 | 建立 Golden Snapshot | 固定 JSON fixture | 快照必须排除时间、随机 ID 等不稳定字段 |
| 7 | 接入 Compiler Gates | 编译状态、诊断码、测试输出 | `error/fatal` 不得继续渲染 |
| 8 | 用新 IR 生成内部结构文件 | `document_ir.json` | 文件不可读或 Schema 不通过则阻断 |
| 9 | 对比新旧用户产物 | 差异报告和人工复核记录 | 结构或引用差异未解释则回退 |
| 10 | 以配置开关启用 | 默认值、启用值、关闭值测试 | 没有关闭路径不能上线 |
| 11 | 在本地跑固定案例和真实脱敏案例 | 运行日志、截图、产物哈希 | 本地失败立即关闭开关并保留现场 |
| 12 | 归档验收结果 | `status/check/<module>...md` | 未归档不得标记完成 |

### 12.1 新旧产物比较方法

不能只比较文件是否生成。比较分三层：

1. **结构层**：章节数量、标题、顺序、表格数量、告警数量；
2. **引用层**：正文脚注集合、CitationMap 集合、`citation_id`、条文号、`can_jump`、失败原因；
3. **展示层**：Markdown、DOCX、PDF 的标题、表格、引用位置和页数。

允许变化：

- 生成时间；
- 文件名中的日期；
- `document_ir.json` 这一新增内部文件；
- 明确记录并经人工确认的空白或换行差异。

不允许自动接受：

- 正文引用数量变化；
- CitationMap 多出或少了引用；
- 风险等级变化；
- 法规名称、条文号或引用原文变化；
- 用户可见章节缺失；
- 从可跳转变成不可跳转；
- 未注册 marker、模板变量或内部字段泄漏。

## 13. 引用和知识库数据修复流程

### 13.1 先备份，后清洗

任何修改 `resources/legal/`、`resources/new/` 或 `regulation_articles.jsonl` 的操作必须先执行：

```bash
TASK_BACKUP_DIR="$(mktemp -d)"
cp resources/legal/registry/regulation_articles.jsonl "$TASK_BACKUP_DIR/"
cp resources/legal/catalog/sources.csv "$TASK_BACKUP_DIR/"
cp resources/legal/registry/source_registry.v1.json "$TASK_BACKUP_DIR/"
shasum -a 256 resources/legal/registry/regulation_articles.jsonl \
  resources/legal/catalog/sources.csv \
  resources/legal/registry/source_registry.v1.json > status/check/legal_registry_before_<YYYYMMDD>.sha256
git diff -- resources/legal/ resources/new/ > status/check/legal_registry_before_<YYYYMMDD>.diff
```

临时备份用于本机快速恢复；`status/check/` 只保存哈希和差异，避免把整份知识库重复提交。备份不能替代 Git。数据清洗脚本必须支持 `--dry-run`，先输出变更数量，再允许写入。

### 13.2 唯一性检查

新增脚本建议位置：`scripts/check_citation_source_integrity.py`。

脚本必须输出：

```text
source_count
article_row_count
duplicate_source_article_count
missing_article_ref_count
missing_source_url_count
invalid_article_number_count
```

判定规则：

- `(source_id, article_no)` 重复数必须为 0；
- `source_id` 不在 `resources/legal/catalog/sources.csv` 和 `source_registry.v1.json` 的记录必须为 0；
- `article_no` 为空的记录不能标记 `exact_article`；
- `source_url` 有权威来源时必须回填；
- 不确定的条文不能自动覆盖，进入 `manual_review` 清单。

### 13.3 CN-REG-004 已完成数据修复，仍需完整复验

`CN-REG-004` 是 assessment 的核心来源。提交 `979d714` 已删除原有 9 条网页新闻段落，改为 20 条正式法条；当前记录数为 20。入库脚本是 `scripts/reingest_cn_reg_004.py`，支持 `--dry-run`。

仍必须按以下步骤复验，不能只因数据文件已修改就宣布跳转问题完成：

1. 执行 `python scripts/reingest_cn_reg_004.py --dry-run`，确认只影响 `CN-REG-004`；
2. 用第 1 条、第 13 条、第 20 条和不存在的第 21 条请求 citation API；
3. 前三条必须返回 `can_jump=true` 和 `resolution_type=exact_article`；
4. 第 21 条必须返回不可跳转原因，不能跳到错误条文；
5. 用一条真实 assessment/cn_flow 案例重新生成 CitationMap；
6. 在浏览器点击 `【依据：数据出境安全评估办法 第十三条】`，确认 URL 包含 `?article=13` 且页面定位到第十三条；
7. 保存 API JSON、浏览器截图和生成产物到 `status/check/`。

## 14. 编译门禁和问题分级

### 14.1 必须阻断的问题

以下问题出现时，新流程不得继续输出用户报告：

- `CITATION_NOT_REGISTERED`；
- `RENDER_MARKER_RESIDUE`；
- `SECTION_ID_DUPLICATE`；
- `BLOCK_ID_DUPLICATE`；
- 用户可见章节缺失；
- 正文脚注和 CitationMap 数量不一致；
- 风险等级在新旧流程中不一致；
- 输入文件未上传但模块要求文件；
- 关键模板缺失。

### 14.2 可以继续但必须记录的问题

- 来源没有官方 URL，但仍有内部可验证条文；
- 条文只有法规级定位，没有唯一条号；
- 低置信度引用被标记为待核验；
- PDF 页眉、页脚或空白差异；
- 旧报告多一个内部诊断文件，但用户交付包没有暴露。

### 14.3 问题记录格式

```markdown
### ISSUE-<模块>-<编号>

- 严重级别：BLOCK / ERROR / WARN
- 运行任务：
- 输入案例：
- 代码位置：相对路径 + 行号 + 函数/类
- 期望结果：
- 实际结果：
- 是否影响用户产物：是/否
- 是否影响引用跳转：是/否
- 临时处理：
- 永久修复：
- 验证命令：
- 关闭条件：
```

## 15. 远端部署、验证和恢复（当前禁止执行）

本节只记录未来获得用户明确同意后的操作方式，当前不能执行其中的任何命令、连接或部署动作。当前阶段的工作全部在本地完成。

### 15.1 获得同意后的部署前检查

```bash
git fetch --all --prune
git branch --show-current
git rev-parse HEAD
git status --short
uv sync --frozen
```

远端部署前必须确认：

- 当前提交号已记录；
- 工作区没有未提交的生产代码修改；
- `.env` 中没有把开关误设为 `true`；
- RAG 索引、法规数据和模板版本已记录。
- 本地 10 个用户功能验收报告均为通过；
- 用户已在当次会话中明确同意远端部署。

### 15.2 获得同意后的首次开启

只允许在用户同意后的测试任务或明确的远端验证窗口开启：

```bash
export AI4LAW_SCHEMA_FIRST_ASSESSMENT_ENABLED=true
```

执行 1 条固定案例，再执行 1 条真实案例。每条案例保存：

- 请求 JSON 的脱敏副本；
- 后端任务 ID；
- `document_ir.json`；
- Markdown/DOCX/PDF/ZIP；
- `citation_map.json`；
- API 响应；
- 浏览器截图；
- 开始时间、结束时间、耗时和 token 统计。

### 15.3 失败恢复

发现 BLOCK 问题时：

```bash
export AI4LAW_SCHEMA_FIRST_ASSESSMENT_ENABLED=false
```

然后重新运行同一输入，确认旧流程仍可生成。恢复报告必须记录：

- 失败任务 ID；
- 失败诊断码；
- 关闭开关时间；
- 旧流程恢复结果；
- 是否需要回滚代码提交。

代码回退只在开关关闭后仍无法恢复时执行，且必须使用明确提交号，不得使用破坏性 Git 命令覆盖其他人的工作。

## 16. 自动化质量门禁

### 16.1 每次代码提交

```bash
uv run pytest -q <受影响模块测试目录>
uv run ruff check <受影响文件>
git diff --check
```

### 16.2 每次模块迁移

```bash
uv run pytest -q backend/common/reporting/tests
uv run pytest -q backend/common/citation/tests
uv run pytest -q backend/api/v1/tests/test_citations_api.py
uv run pytest -q <模块>/tests
```

### 16.3 合并前

```bash
uv run pytest -q
cd frontend && npm test -- --run && npm run build
```

全量测试有失败时，必须区分：

- 本次改动引入的失败：阻止合并；
- 既有失败：记录路径、原因和单独任务，不得在汇报中写“全绿”。

## 17. 依赖和目录审查

每个模块完成后执行一次静态检查：

```bash
rg -n "from backend\.domains|import backend\.domains" backend/common
rg -n "from .*\.service import|from .*\.router import" backend/common
rg -n "utils|common2|new|final|v2|temp|misc" backend resources frontend
```

判定规则：

- `backend/common` 不得导入 `backend/domains`；
- renderer 不得直接调用具体 RAG provider；
- API 不得读取别的模块的 trace 作为正式引用；
- 业务差异必须在 Schema、模板或规则文件中表达；
- 新增公共函数必须说明被几个模块复用，只有一个调用方时不得提前下沉。

## 18. 验收汇报必须回答的问题

每个模块的验收报告必须逐项回答：

1. 输入从哪里来？Schema 是什么？
2. 业务判断在哪个 service/agent 完成？
3. RAG 在哪个函数调用？返回什么字段？
4. citation_id 在哪里生成、注册、编号和落盘？
5. 正文 `[N]` 和 CitationMap 是否一一对应？数量是多少？
6. `can_jump=false` 的具体原因是什么？
7. Markdown、DOCX、PDF、ZIP 是否都生成？
8. token、time、状态事件是否正常？
9. 哪些文件是内部产物，哪些是用户产物？
10. 新流程失败时如何关闭开关恢复旧流程？
11. 代码、测试、截图和日志分别在哪里？
12. 哪些问题已修复，哪些问题仍未解决？

缺少任何一项，只能标记为“部分验收”。

## 19. 风险清单和处理办法

| 风险 | 触发条件 | 处理办法 | 是否允许继续 |
|---|---|---|---|
| 新旧引用编号不同 | 同一输入出现不同脚注编号 | 查首次出现顺序和 registry 状态 | 不允许 |
| CitationMap 多出正文没有的引用 | API 返回数量大于正文脚注数 | 禁止读取期合成，检查生成期落盘 | 不允许 |
| 条文无法跳转 | `article_not_found/not_unique/missing` | 显示中文原因，补数据或保留法规级定位 | 允许，但必须记录 |
| LLM 输出 Markdown | Block 文本含标题/粗体/脚注 | Compiler 阻断，修 prompt 或 adapter | 不允许 |
| 模板缺失 | Markdown/DOCX 模板不存在 | 走明确 fallback 并写 warning | 外部交付不允许 |
| 远端开关导致任务失败 | 新流程出现 BLOCK 或异常 | 关闭环境变量，重跑同一案例 | 关闭后可继续 |
| 知识库清洗误删 | dry-run 与实际行数不一致 | 从备份恢复，禁止覆盖原文件 | 不允许 |
| 公共层反向依赖业务域 | 静态扫描命中 | 移动接口或建立协议层 | 不允许 |

## 20. 本方案的完成判断

“方案写完”不等于“项目迁移完成”。本方案只有在以下表格全部为“通过”时才结束：

| 完成项 | 通过条件 | 证据位置 |
|---|---|---|
| 公共结构 | 所有模块使用同一 DocumentIR Schema | Schema 文件 + 测试 |
| 公共引用 | 所有模块使用同一 CitationRegistry 契约 | registry 测试 |
| 结构检查 | 所有用户报告生成前执行 Compiler Gates | 运行日志 + 诊断记录 |
| 数据正确 | 条文唯一性和 URL 检查通过 | 数据检查报告 |
| 引用正确 | 正文、CitationMap、API、前端数量和身份一致 | 模块验收报告 |
| 输出完整 | MD/DOCX/PDF/ZIP 均通过打开和内容检查 | 产物清单 + 截图 |
| 过程可见 | 状态、token、耗时、错误能在中途展示 | trace + 前端截图 |
| 失败可恢复 | 关闭开关后旧流程恢复 | 回退记录 |
| 目录规范 | 无重复实现、无跨层依赖、无无意义命名 | 静态扫描报告 |
| 文档真实 | 每项结论都有代码、测试、日志或截图证据 | `status/check/` |

最终结论必须使用以下三种状态之一：

- **已完成**：代码、测试、真实运行和产物验收全部通过；
- **部分完成**：代码和本地测试通过，但真实运行或产物验收未完成；
- **未完成**：存在阻断问题，不能进入下一阶段。

## 21. 当前版本存档和旧功能下线方案

### 21.1 当前版本如何存档

当前版本的存档单位是 Git 提交和本地标签，不复制整份源码，也不把 `outputs/`、数据库或临时文件放入 Git。

每次准备清理旧功能前，必须执行：

```bash
git status --short
git rev-parse HEAD
git log -1 --oneline
git tag -a archive/pre-legacy-cleanup-<YYYYMMDD> -m "Local baseline before legacy cleanup"
```

然后新增 `status/check/本地基线_<YYYYMMDD>.md`，至少记录：

| 项目 | 必须记录的内容 |
|---|---|
| Git 基线 | 分支名、提交号、标签名、工作区状态 |
| 前端功能清单 | 10 个功能名称、对应 module key、入口 URL |
| 后端实现清单 | 11 个 module key、路由、service、renderer |
| 依赖版本 | `uv.lock`、`frontend/package-lock.json` 的提交状态 |
| 知识库版本 | `sources.csv`、`source_registry.v1.json`、`regulation_articles.jsonl` 的 SHA-256 |
| 本地测试 | 命令、通过数、既有失败数 |
| 本地产物 | 每个功能的任务 ID、MD/DOCX/PDF/ZIP/CitationMap 路径 |

标签只在本地创建，不执行 `git push --tags`，除非用户另行明确同意。

### 21.2 注释和删除的规则

**默认选择删除，不选择大段注释。** 被注释的旧流程仍占目录、仍干扰阅读、仍会被误恢复，不能解决职责不清的问题。

只有两种情况可以保留短期注释：

1. 外部 API 兼容入口尚有调用方，代码旁必须写明替代入口、删除条件和对应 issue；
2. 需要在一次本地验收中对比新旧输出，且注释会妨碍该对比。

其他情况一律删除代码、测试、配置和文档引用，不保留“以后可能有用”的注释块。

### 21.3 旧实现清单和当前处理决定

| 旧实现或重复实现 | 当前调用情况 | 替代能力 | 当前决定 | 删除前必须满足 |
|---|---|---|---|---|
| 分散的 citation marker 正则 | 已集中到 `backend/common/citation/markers.py` | `CIT_MARKER_RE`、`is_valid_citation_id` | 不再新增重复正则；发现剩余重复定义就删除 | `rg` 只剩公共入口，marker 测试通过 |
| Citation API 从 trace/retrieval 合成 CitationMap | 已在 `870bd5c` 删除 | 生成期 `citation_map.json` | 已删除，保持回归测试 | API 空 map 返回空，不能写盘 |
| `ensure_paragraph_citations` / `apply_citation_policy` 的旧降级引用路径 | assessment、DPIA、通用生成器仍在调用 | 未来统一 citation pipeline + DocumentIR `citation_refs` | 现在不能删 | 10 个功能均完成新引用链路并通过产物对比 |
| 各业务模块直接生成 Markdown 的旧 renderer | 绝大多数功能仍在使用 | DocumentIR + 公共 renderer | 现在不能删 | 对应功能的新 renderer 已处理全部用户产物且本地验收通过 |
| `cn_flow` 兼容入口 | 前端 API、v0 gateway、测试、任务数据均有调用 | `us_14117` 主入口 | 现在不能删；先统一实现和前端入口 | `cn_flow` 调用数为 0，兼容测试改为重定向/弃用测试，用户确认删除 |
| `us_14117_flow` 兼容任务模板 | `task-templates.ts` 中仍注册，供兼容入口使用 | `us_14117` 功能卡 | 先从用户菜单隐藏，再保留接口兼容 | 前端无入口、历史任务仍可读、后端无新任务创建 |
| 会话诊断与直接诊断两条实现 | 都存在独立 API 和 HTML/PDF 输出 | 统一 `DiagnosisResult` 契约，未来选定一个主入口 | 现在不能删 | 相同输入结论一致、所有客户端迁移、handoff 对比通过 |
| 已移动或已归档的 status 文档 | 部分文件仍在 `todo` 或 `view` | `status/check` 验收记录、当前执行方案 | 先分类，后移动 | 文档没有被当前代码或流程引用，且保留 Git 历史 |

### 21.4 每个旧实现的下线步骤

对上表中任何一项执行删除前，必须按下列顺序操作：

1. 用 `rg` 列出所有 import、调用、路由、前端入口、测试、任务模板和文档引用；
2. 写一条失败测试，证明调用方已改用替代能力；
3. 迁移所有调用方，并运行受影响功能的本地测试；
4. 用固定案例对比旧新产物、引用和错误返回；
5. 在本地关闭旧入口，确认新入口仍可完成同一任务；
6. 删除旧代码、旧测试、旧配置、旧模板和无效文档；
7. 再次执行 `rg`，确认旧名称、旧路由、旧文件名没有剩余生产调用；
8. 运行相关后端测试、前端测试和构建；
9. 单独提交删除操作，并在 `status/check/` 写删除验收记录。

### 21.5 `cn_flow` 合并到 14117 的具体方案

这是当前最明显的“一个用户功能、两套后端实现”问题。处理顺序如下：

| 步骤 | 本地操作 | 验收结果 |
|---:|---|---|
| 1 | 选定 `us_14117` 作为 EO 14117 主实现，记录 `cn_flow` 为兼容接口 | 文档和模块注册表说明一致 |
| 2 | 为两套入口准备同一组脱敏数据、实体、交易和附件案例 | 输入数据可同时通过两个 Schema，差异明确记录 |
| 3 | 比较推荐结论、风险等级、事实、问题、证据、引用和用户产物 | 法律结论不能相反；允许的结构差异必须写明 |
| 4 | 抽取重复的规则、事实、问题、证据和渲染能力到公共 EO 14117 层 | 公共层不导入任一具体 router/service |
| 5 | `cn_flow` router 保留原 URL，但改为调用主实现或明确适配器 | 旧 API 请求仍可成功，输出 owner/module 映射可追踪 |
| 6 | 前端只展示“14117 行政令合规”功能，不新建 `cn_flow` 任务 | 用户功能数保持 10 个 |
| 7 | 本地连续运行两个入口的固定案例和错误案例 | 结论、错误码、引用、产物满足兼容契约 |
| 8 | 统计并确认无旧入口调用后，删除 `cn_flow` 独立 service、模板、测试和路由 | 需要用户明确同意，且远端部署另行审批 |

第 8 步在当前阶段禁止执行，因为现有前端、v0 gateway、OpenAPI、测试和历史任务仍依赖 `cn_flow`。

### 21.6 本地删除验收表

| 检查项 | 通过标准 |
|---|---|
| 替代能力 | 真实存在且覆盖旧功能所有用户场景 |
| 调用方 | `rg`、路由清单、任务模板和测试均无旧生产调用 |
| 数据兼容 | 旧任务和旧产物能读取，或有明确迁移工具 |
| 产物兼容 | 新入口可生成用户需要的文件和引用 |
| 错误兼容 | 输入错误、文件缺失、未注册引用等错误可解释 |
| 本地回退 | 删除前已验证可以恢复到存档提交或关闭新开关 |
| 代码整洁 | 删除后无死 import、无死测试、无空目录、无无意义注释 |
| 证据 | 测试输出、差异报告、`rg` 输出、提交号写入 `status/check/` |

任何一项不通过，都只能标记“保留旧实现”，不得删除。
