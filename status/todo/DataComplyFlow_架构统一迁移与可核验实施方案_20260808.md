# DataComplyFlow 架构统一迁移与可核验实施方案

> 文档日期：2026-08-08
> 适用分支：`new`
> 文档状态：执行方案
> 依据文档：
> - `status/todo/DataComplyFlow_Schema优先法律文档编译器架构方案_20260807.md`
> - `status/todo/DataComplyFlow_引用跳转闭环治理方案_20260806.md`
> - `status/todo/DataComplyFlow_引用跳转机理详解_代码流程追踪_20260808.md`
> - `status/view/DataComplyFlow_项目整体架构说明_20260807.md`

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
