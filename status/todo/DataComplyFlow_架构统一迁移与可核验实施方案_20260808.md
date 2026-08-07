# DataComplyFlow 架构统一迁移与可核验实施方案

> 文档日期：2026-08-08
> 适用分支：`new`
> 文档状态：执行方案
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

本次文档复核已实际执行：

| 检查 | 结果 | 说明 |
|---|---|---|
| `uv run python scripts/reingest_cn_reg_004.py --dry-run` | 通过 | 当前 20 条记录会被可重复脚本替换为同样的 20 条正式条文，未写盘 |
| `uv run pytest -q backend/common/citation/tests/test_citation_url_normalization.py` | 41 passed | 包含 `CN-REG-004` 第十三条可精确定位断言 |
| Markdown 转换 | 通过 | Pandoc 成功转换本方案 |

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
| assessment 相关回归 | 93 项通过 | 2026-08-08 本地执行记录 |
| 后端全量回归 | 601 通过、1 失败 | 失败为既有管线表格规范化契约测试，见实施记录 |
| 其他模块新流程 | 未迁移 | 不能宣称已完成 |

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
- [ ] 将 `markdown_lint.py` 接入统一验收命令，但保持其现有 advisory 语义。

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
- [ ] 在远端用真实 assessment 输入首跑。
- [ ] 对比旧版和新版 Markdown、DOCX、PDF、CitationMap、ZIP 文件。

远端首跑步骤：

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

### 阶段 3：其他报告模块迁移

按以下顺序执行，每个模块单独提交、单独验收：

| 顺序 | 模块 | 先解决的问题 |
|---:|---|---|
| 1 | `dpia` | 结构化输入和引用编号统一 |
| 2 | `pipia` | 大量法规条文的稳定编号和去重 |
| 3 | `tia` | marker 解析和待核验状态统一 |
| 4 | `bcr` | 无条号法规引用的能力边界 |
| 5 | `cpra` | 用户材料和法规引用区分 |
| 6 | `cn_flow` | source registry 条文补齐和唯一性 |
| 7 | `review` | 上传文件、解析、报告生成的两步流程 |

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

- [ ] 以 `source_id + article_no` 建立唯一键检查。
- [ ] 修复同一法规同一条文的重复记录。
- [x] `CN-REG-004` 删除 9 条网页噪声记录，写入 20 条正式条文。
- [ ] 把 `sources.csv` 或注册表中的 `source_url` 回填到 CitationItem。
- [ ] 没有正式条号的法规只允许作为法规级依据，不得标记为条文级跳转。
- [ ] 统一中文条号到阿拉伯数字的转换规则。
- [ ] 对 `article_not_found`、`article_not_unique`、`article_missing` 分类统计。

验收标准：

- 唯一性检查为 0 个重复键；
- 有 URL 的来源 100% 回填；
- 条文级跳转统计可重复；
- 任何无法定位的引用都有中文失败原因。

### 阶段 5：前端引用闭环

任务：

- [ ] 正文 `[N]` 只从 CitationMap 映射到 CitationPopover。
- [ ] 唯一条文显示跳转入口。
- [x] `【依据：法规名 第X条】` 路径在跳转前调用后端确认条文是否唯一存在。
- [ ] `not_found`、`not_unique`、`missing` 显示具体原因和下一步。
- [ ] `citation_map.json` 不作为普通用户文件标签展示。
- [ ] 支持复制引用、显示条文原文和官方来源 URL。
- [ ] 待核验、证据冲突、缺少依据不显示为可点击引用。

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
| 0 | 基线冻结 | 部分完成 | 现有测试和问题记录 | 远端基线文件清单 |
| 1 | 公共能力 | 基本完成 | reporting/citation 测试 | markdown_lint 统一入口 |
| 2 | assessment | 本地完成 | Golden Snapshot、93 项回归 | 远端真实首跑 |
| 3 | 其他模块 | 未开始 | 无 | 按模块迁移 |
| 4 | 知识库治理 | 部分完成 | 现状分析文档 | URL、条文唯一性、条号清理 |
| 5 | 前端闭环 | 部分完成 | 待核验状态测试 | 全部跳转状态和截图 |
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

## 11. 模块级执行卡

下面的路径是当前仓库事实路径。迁移时必须先从这些入口开始阅读和测试，不能只修改公共层而不确认业务模块是否真的调用了它。

| 模块 | 请求 Schema | 服务入口 | 输出入口 | 当前主要风险 | 迁移状态 |
|---|---|---|---|---|---|
| `assessment` | `backend/domains/cn/security_assessment/schema.py` | `service.py:AssessmentService.generate_report` | `report_renderer.py:AssessmentReportRenderer.render` | 引用 marker、报告模板、条文数据 | 已有 DocumentIR 开关，待远端首跑 |
| `dpia` | `backend/domains/eu/dpia/schema.py` | `service.py:generate_report` | `chapter_generator.py`、`service.py` | 表单输入和结构化章节 | 未迁移 |
| `pipia` | `backend/domains/cn/pipia/schema.py` | `service.py:generate_report` | `service.py` | 输入字段多、规则引用多 | 未迁移 |
| `tia` | `backend/domains/eu/tia/schema.py` | `service.py:generate_report` | `service.py` | marker 和待核验混用 | 未迁移 |
| `bcr` | `backend/domains/eu/bcr_review/schema.py` | `service.py:generate_report` | `bcr_report_renderer.py` | 法规引用经常没有条号 | 未迁移 |
| `cpra` | `backend/domains/us/cpra/schema.py` | `service.py:generate_report` | `service.py` | 用户资料、RAG 证据和法规混合 | 未迁移 |
| `cn_flow` | `backend/domains/us/eo14117_flow_review/schema.py` | `service.py:generate_report` | `service.py` | source registry 条文不完整 | 未迁移 |
| `eu_scc` | `backend/domains/eu/scc_review/schema.py` | `service.py:generate_report` | `service.py` | 文件审查和报告生成耦合 | 未迁移 |
| `review` | `backend/domains/cn/document_review/` | `service.py:generate_report` | `review_report_renderer.py` | 必须先上传文件再生成 | 未迁移 |

每个模块迁移前，必须在模块目录下补齐以下文件：

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
| 11 | 在远端跑真实案例 | 运行日志、截图、产物哈希 | 远端失败立即关闭开关 |
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

## 15. 远端部署、验证和恢复

### 15.1 部署前检查

```bash
git fetch --all --prune
git branch --show-current
git rev-parse HEAD
git status --short
uv sync --frozen
```

部署前必须确认：

- 当前提交号已记录；
- 工作区没有未提交的生产代码修改；
- `.env` 中没有把开关误设为 `true`；
- RAG 索引、法规数据和模板版本已记录。

### 15.2 首次开启

只允许在测试任务或明确的远端验证窗口开启：

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
