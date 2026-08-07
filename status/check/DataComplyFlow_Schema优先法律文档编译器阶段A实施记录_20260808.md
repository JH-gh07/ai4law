# DataComplyFlow Schema-first 法律文档编译器阶段 A 实施记录

> 实施日期：2026-08-08
> 适用分支：`new`
> 依据方案：`status/todo/DataComplyFlow_Schema优先法律文档编译器架构方案_20260807.md`
> 实施提交：`62e631e`、`0511ec8`、`870bd5c`、`d4ea7bf`、`9d356cf`、`acaaff2`
> 状态：阶段 A 局部完成，旧生成链路保持兼容

## 一、实施结论

本轮按迁移防崩塌原则落地了第一条可回滚垂直切片：

```text
Pydantic semantic IR
  → CitationRegistry（稳定 citation_id）
  → Compiler Gates（输入/引用/去重/结构/渲染残留）
  → legacy citation policy 可观测化
  → 前端待核验状态样式
```

旧的 Markdown 生成器、报告路由和 ReactMarkdown 主渲染入口没有切换到新 IR；因此本轮不会因新编译器未覆盖全部模块而影响现网链路。

## 二、改动清单与原因

| 文件 | 改动 | 原因 |
|---|---|---|
| `backend/common/reporting/schema/blocks.py` | 新增 Paragraph/Claim/List/Table/Warning Block 与 Markdown 禁止校验 | 让 LLM 语义层不再把 Markdown 语法当作数据 |
| `backend/common/reporting/schema/citations.py` | 新增稳定 citation ID 注册和按首次出现编号 | 分离引用身份与展示编号，避免 `[N]` 反查歧义 |
| `backend/common/reporting/schema/document.py` | 新增 SectionIR、DocumentIR、Provenance | 为后续 Template/Compiler/Renderer 提供唯一中间表示 |
| `backend/common/reporting/compiler/core.py` | 新增 Input、Citation、Numbering、Dedup、Structure、Render Gates | 先建立可单测、可回滚的安全网，不直接改生产生成流程 |
| `backend/common/llm/postprocess.py` | 未注册 `{{CIT-*}}` 改为 `【未注册引用：...】`；补窄范围法律义务识别 | 禁止未注册证据静默消失，并让明确“应当/必须”等主张进入待核验路径 |
| `backend/common/citation/{registry.py,postprocess.py}` | marker 识别改为按 `{{CIT-...}}` 边界解析，支持包含连字符的合法 citation_id | 消除生成器缩写含连字符时的 99% marker 漏匹配风险 |
| `backend/api/v1/endpoints/citations.py` | 删除读取期 trace/retrieval 合成 citation_map 及磁盘回写 | API 只能读取生成期事实，不能把检索命中伪装成正文引用 |
| `backend/api/v1/tests/test_citations_api.py` | 将空 footnote_map 回填测试改为不合成、不写盘断言 | 固化 CitationMap 事实基线契约 |
| `backend/common/reporting/compat.py` | 新增 legacy CitationItem/Registry 到 DocumentIR CitationRecord/Registry 的单向适配层 | 在不切换生产链路的前提下收敛双轨，并保留已分配脚注编号 |
| `backend/common/reporting/tests/test_compat.py` | 覆盖字段映射和编号保留 | 防止迁移适配层改变引用身份或展示编号 |
| `backend/domains/cn/security_assessment/schema_first.py` | 将 assessment 章节转换为 DocumentIR，并保留未知 citation ref | 先验证代表模块的语义转换，不从 Markdown 反推结构 |
| `backend/domains/cn/security_assessment/report_renderer.py` | 增加默认关闭的 Schema-first 编译开关；开启时写入 `document_ir.json`，Compiler 非 success 即阻断 | 允许真实模块灰度验证，避免未完成迁移影响默认生产链路 |
| `backend/core/settings.py` | 新增 `AI4LAW_SCHEMA_FIRST_ASSESSMENT_ENABLED` 配置，默认 `false` | 以环境配置控制灰度，不硬编码切换 |
| `backend/domains/cn/security_assessment/tests/fixtures/assessment_document_ir.golden.json` | 固化 assessment DocumentIR Golden Snapshot | 防止模板章节、语义块和 citation ref 结构漂移 |
| `frontend/src/components/citation/CitationMarkdownRenderer.tsx` | `【待核验】`、`【缺少依据】`、`【证据冲突】` 进入待核验样式类 | 不把待核验提示渲染成可点击的 CitationPopover |
| `frontend/src/styles/app/product-pages-and-overrides.css` | 增加 `workspace-legal-callout-pending` 样式 | 让风险状态在用户界面可见、可区分 |

## 三、测试证据

| 检查 | 结果 |
|---|---|
| `uv run pytest -q backend/common/reporting/tests` | 10 passed |
| `uv run pytest -q backend/common/citation/tests/test_postprocess.py` | 17 passed |
| `npm test -- --run src/components/citation/CitationMarkdownRenderer.test.tsx` | 2 passed |
| `uv run ruff check backend/common/llm/postprocess.py backend/common/reporting` | 通过 |
| `git diff --check` | 通过 |

### 全量回归

| 检查 | 结果 | 说明 |
|---|---|---|
| `uv run pytest -q backend/tests` | 601 passed, 1 failed | 失败为既有 `backend/common/render/tests/test_normalization_contract.py::test_backend_matches_normalization_contract[pipe_table_norm]`；与本轮新增文件无交集，列入独立渲染契约遗留项 |
| `npm test -- --run` | 113 passed, 2 skipped | 22 个测试文件通过；测试中已有的 chunk load failed 模拟日志不影响退出码 |
| `npm run build` | 通过 | 347 modules transformed，无构建错误 |

| 引用闭环 P0 定向测试 | 20 passed | marker 兼容性、API 不合成、不写盘 |
| reporting 适配层测试 | 12 passed | DocumentIR registry 与 legacy registry 转换及编号保持 |
| assessment Schema-first 定向测试 | 24 passed | Golden Snapshot、renderer 开关、阻断条件、service 回归 |
| assessment/reporting/citation/API 组合回归 | 93 passed | 本轮相关后端测试全部通过 |
| Ruff 组合扫描 | 发现 6 个既有告警 | 位于 assessment 既有文件的未使用导入/变量，与本轮变更无文件交集，未混入本轮修复 |

本轮不修改管线表格规范化逻辑，避免在 Schema-first 迁移切片中引入无关的渲染行为变更。该失败项必须在阶段 A 完整验收前单独定位并补齐契约测试。

## 四、未覆盖边界

1. Schema-first 已接入 assessment renderer，但默认关闭；其他模块尚未接入。
2. 阶段 A 的 `StructureValidationPass` 和 `DedupValidationPass` 目前校验 DocumentIR，不替代既有 `markdown_lint.py` 的 Markdown 检查。
3. 阶段 B 的旧 `CitationRegistry` 与新 reporting registry 仍是双轨；尚未迁移既有 citation_map 输出协议。
4. 阶段 C 的结构化 LLM 输出、JSON Schema response format、有限重试和 TemplateAssembly 尚未开始。
5. 阶段 D 的 DocumentRenderer、SourceMap UI、Pandoc Adapter 尚未开始。
6. 未运行真实 LLM、RAG、得理 API 或法律内容质量验收；本记录只证明确定性结构与引用门禁行为。

## 五、后续进入条件

阶段 B 开始前必须满足：

- 阶段 A 新增测试在后端/前端全量回归中保持通过；
- 已明确并测试新旧 CitationRegistry 的单向迁移适配层；assessment 已具备 Golden Snapshot 和显式开关；
- 仍需在远端/测试环境开启 `AI4LAW_SCHEMA_FIRST_ASSESSMENT_ENABLED=true` 完成首跑，对比旧 Markdown、DOCX、CitationMap 和压缩包产物后，才能扩大灰度；
- 选定一个代表模块先完成 DocumentIR → Markdown 的 Golden Snapshot；
- 不得在没有真实模块回归证据时删除 `convert_citation_markers` 或 `CitationMarkdownRenderer`。
