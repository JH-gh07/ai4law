# AI4Law 当前代码状态、缺口与全覆盖验收方案

> 审计对象：当前工作区 `new` 分支
> 审计基线：`5c8d1e3`
> 初次审计日期：2026-07-21
> 本次迭代日期：2026-07-22
> 文档性质：当前代码事实清单、发布阻断项、逐文件改造清单和可复验方案
> 事实优先级：当前代码与可重复命令 > 当前配置实测 > 历史交接文档 > 规划性描述

## 0. 结论先行

当前系统不是“功能都没有”，也不能因为自动化测试全绿就判断为“已经可交付”。更准确的结论是：

1. 11 个业务模块已经在前后端注册；后端离线测试、前端单元测试和生产构建均通过。
2. CLI 测试框架已经存在，覆盖 10/11 个模块，并能保存输入、输出和事件轨迹；缺少文书审查适配器、Token 汇总、供应商信息、产物校验和全模块批量入口。
3. 前端已经能显示运行事件、节点耗时和部分 Token 数据，不能再把这一能力列为“完全缺失”；问题在于数据未形成持久、统一、可核账的运行清单。
4. Markdown、HTML、DOCX、PDF 的共享渲染基础已经存在，但只有部分模块真正以同一语义文档为源，前端还存在二次规则化改写和嵌套 Markdown 被压平的问题。
5. 引用映射已经覆盖主要报告模块，但当前点击仍可能直接新开外部页面，未知 `source_id` 仍会被错误标记为可跳转，且大量引用只有来源级信息、没有条文定位。
6. 本地知识库不是空壳：目录中有 69 个来源、1,672 条法规条文和完整快照；但存在 34 组重复定位键，这些键已被严格降级为不可精确跳转，仍需法律内容负责人消歧。
7. 得理 API 当前可真实调用，抽样延迟约 2.9–4.0 秒；但是返回适配层只保留标题、来源、摘要，丢弃稳定 ID、条号、效力状态和原文定位，尚不能直接承担可信引用入库。
8. 当前 LLM Key 和接口地址可被识别，但默认腾讯混元模型 `hy3-preview` 返回“模型不存在”；尝试可用模型时又遇到资源包余额不足。因此“已配置”不等于“可运行”。
9. 当前代码发布阻断项集中在数据隔离、证据真实性和检索确定性；当前 LLM 账号/模型不可用另列为外部环境发布阻断，不与代码 P0 混为一类。
10. “小李 AI”在当前代码中没有具名提供商、预置模型或专门配置。系统支持通用 OpenAI-compatible 提供商，但在没有明确 Base URL、模型名和鉴权方式前，不能宣称已自动配置。

因此，后续应按“先锁定契约与发布阻断项，再按纵向功能切片补齐，最后结构化重构”的顺序推进，不能先做大范围目录搬迁。

---

## 1. 本次核验范围与状态定义

### 1.1 已核验范围

- 模块注册、前端任务入口、后端路由和运行编排
- SSE 事件、中间过程、节点耗时、Token 统计和任务生命周期
- CLI 测试框架、真实输入案例、运行产物和查看器
- 引用生成、CitationMap、知识库匹配、前端引用交互
- 本地 RAG、多索引检索、回退逻辑、得理法律与案例检索
- 输入文件、输出文件、预览、下载、历史恢复和权限
- LLM/得理运行时配置、连接测试和客户端刷新
- Markdown 生成、规范化、前端渲染、PDF/DOCX/HTML 生成
- 前端开发测试案例和“一键填充并运行”能力
- 代码体量、模块边界、重复配置和后续可扩展性
- 后端、前端、构建、仓库校验和一次真实外部 API 探测

### 1.2 状态定义

| 状态 | 含义 |
|---|---|
| 已验证 | 当前代码和本次命令都能证明可用 |
| 部分具备 | 已有实现，但契约、覆盖或可靠性不足 |
| 未实现 | 当前仓库不存在对应实现 |
| 已阻断 | 有实现或配置，但真实依赖当前不可用 |
| P0 | 代码发布阻断：数据隔离、结果真实性或当前已满足触发条件的确定性错误 |
| ENV-BLOCK | 外部环境发布阻断：账号、额度、许可或人工确认不足，不能仅靠代码关闭 |
| P1 | 核心功能/体验验收项；不与安全泄露并列，但下一阶段必须完成 |
| P2 | 需要基准或稳定契约后再推进的工程化、维护性和性能项 |

### 1.3 与旧版清单相比必须纠正的事实

| 旧判断 | 当前事实 | 修正结论 |
|---|---|---|
| 当前有 12 个业务模块 | `config/module_registry.json` 当前有 11 个模块，`cn.scc_review` 已退役 | 后续矩阵按 11 个模块验收 |
| CLI 快速测试尚未实现 | `backend/tests/harness/` 已有 runner、viewer、测试和 14 个案例 | 补齐 1 个模块和统一计量，不重建 CLI |
| 前端没有 Token、耗时和中间过程 | `RunTranscript`、`TraceRunHeader`、`TraceNodeView`、`AssistantPanel` 已显示相关信息 | 缺口是持久化、汇总和一致口径 |
| 公共 Markdown/DOCX/PDF 渲染器未落地 | `backend/common/render/` 已存在并有测试 | 缺口是模块接入率和单一语义源 |
| 表格、引用块等完全未样式化 | 前端已配置标题、表格、引用块、代码和引用角标样式 | 仍缺宽表滚动、嵌套节点保真和移动端交互 |
| 引用相关约 33 个测试待迁移 | 当前引用相关测试已覆盖公共规范化与 API 路径 | 应补的是所有权、未知来源、条文唯一性和浏览器交互测试 |
| `backend/modules` 是待迁移的旧实现 | 该目录当前没有被 Git 跟踪的源码，主要是忽略的缓存 | 不应围绕该目录设计迁移方案 |
| 若干 benchmark/check 脚本可直接运行 | 旧文档列出的多个脚本在仓库中不存在 | 本文将“现有命令”和“待创建命令”严格分开 |

### 1.4 2026-07-22 外部核查意见处置记录

本节专门记录本轮反馈的采纳情况。`部分采纳` 不代表意见“错了”，而是其适用范围、落地顺序或技术成熟度不足以直接写成强制架构。

| # | 核查意见 | 处置 | 具体理由与文档调整 |
|---:|---|---|---|
| 1 | 规则只处理确定性格式，不能机械补语义引用 | 采纳 | P0-03 增加“规则边界”和证据先行链路；确定性校验与语义支持判断分开 |
| 2 | 先定义 Citation Policy，避免每段/每句过度引用 | 采纳 | 增加 ClaimType 与所需证据类型；过渡、总结不强制产生新引用 |
| 3 | 使用主张—来源—证据片段—支持关系 | 部分采纳 | 采纳最小 Claim/Evidence/Span/Relation；不把模型的支持判定当作客观真值，低置信度和冲突必须进入人工复核 |
| 4 | ReportDocument 使用最小语义层，不构造万能文档模型 | 采纳 | 只约束标识、关系、状态和核心块；自然语言正文继续由模型/模板生成 |
| 5 | 用 CitationResolution 替代粗糙 `can_jump` | 部分采纳 | 目标模型采纳；为兼容现有前后端，`can_jump` 暂保留为派生字段，待所有消费者迁移后删除 |
| 6 | 稳定哈希只是止血，长期应评估 BM25/Dense/Reranker | 部分采纳 | 稳定哈希立即修；后续检索器必须通过本项目金标基准选择，不因单篇非法律领域论文直接定型 |
| 7 | 得理定位为条件触发的外部证据发现层 | 采纳 | 删除“符合条件即默认并行”的模糊表述，改为可解释触发和候选—核验—入库状态机 |
| 8 | 技术观测对齐 OpenTelemetry，RunManifest 保留业务事实 | 部分采纳 | 采用内部字段到 OTel 的适配层；不让业务对象直接依赖 GenAI 规范，因为官方页面已迁移到独立仓库，当前仓库尚无 release 且 Schema URL 仍为 TODO |
| 9 | CLI 不复刻前端，只共享事件源 | 采纳 | CLI 使用实时表格/树状 trace；Viewer 可提供本地 HTML，三端读取同一持久事件和 manifest |
| 10 | “自动配置”改为自动发现、校验和生效 | 采纳 | 统一命名为 Provider Registry，并增加 capabilities 与不可变 ProviderSnapshot |
| 11 | 区分物理重复、逻辑重复和多格式派生产物 | 采纳 | ArtifactRecord 与 ContentBlob 分离，以内容哈希物理去重，以 role/format 保留合法交付物 |
| 12 | 重新划分 P0/P1/外部阻断 | 部分采纳 | 新开页面降为 P1；LLM 账号问题改为 ENV-BLOCK；运行时热切换改为 P1。哈希风险仍保留 P0，因为当前索引已经持久化并跨服务进程/重启复用，触发条件已满足 |
| 13 | 按可信结果→运行闭环→生成检索→呈现→重构推进 | 采纳 | 第 15 节改为因果顺序，不再将 Markdown、RAG 和目录重构并行启动 |

明确不原样采纳的内容及替代方案：

1. **不立即删除 `can_jump`**：直接删除会同时破坏当前 API 类型、前端组件和历史 CitationMap。先引入 `CitationResolution`，由解析状态派生旧字段；消费者全部迁移并通过回归测试后再删除。
2. **不把某个前沿检索组合直接定为最终架构**：BM25、Dense、Hybrid、Reranker 都是候选。外部论文可以帮助设计实验，但不能替代 AI4Law 自己的法律金标集、延迟和成本结果。
3. **不把 OTel GenAI 规范作为业务数据库 Schema**：OTel 用于技术观测导出，RunManifest 仍是稳定业务账本；通过版本化映射层隔离规范变化。
4. **不将哈希问题降为普通 P1**：意见中的条件“索引跨进程或跨重启复用”在当前仓库已经成立，因此它是当前确定性错误，而不是未来假设。
5. **不要求所有未验证内容从报告中消失**：正式法律结论必须有通过门禁的证据；假设、证据不足和冲突可以在报告的风险/待确认区出现，但必须显式标注，不能伪装成确定事实。

---

## 2. 可重复的当前基线

### 2.1 自动化验证结果

| 检查 | 本次结果 | 能证明什么 | 不能证明什么 |
|---|---:|---|---|
| `uv run --frozen pytest -q` | 448 passed，1 warning，约 95.59 秒 | 后端离线测试基线通过 | 不能证明真实 LLM、得理、浏览器交互正常 |
| `npm --prefix frontend test -- --run` | 11 个文件、41 个测试通过 | 前端现有单元测试通过 | 没有浏览器级端到端覆盖 |
| `npm --prefix frontend run build` | 构建通过，342 modules | 前端可生产构建 | 不证明运行时 API 和用户路径可用 |
| `uv run --frozen python scripts/check_local_new_parity.py` | 通过，56 个来源候选 | 当前迁移账本一致性通过 | 不证明 11 个模块行为完全等价 |
| `uv run --frozen python scripts/check_repository_hygiene.py` | 通过，956 个文件 | 仓库卫生规则通过 | 不检查 `outputs/` 历史膨胀与业务正确性 |
| `uv run --frozen python -m compileall -q backend` | 通过 | Python 语法可编译 | 不证明运行时分支均被执行 |

### 2.2 CLI 抽样实测

执行：

```bash
uv run --frozen python backend/tests/harness/runner.py diagnosis 01_scc_path --no-llm
```

结果：

- 运行通过，耗时约 695 ms。
- Run ID：`20260721_233203_760246_01_scc_path`。
- 保存了 `input/request.json`、输入哈希、`output/result.json`、逐事件 JSON、`trace/manifest.json` 和 `run_manifest.json`。
- 当前 `run_manifest.json` 没有 Token 总量、LLM 调用明细、检索耗时、供应商、模型、回退路径、配置版本和产物校验结果。

### 2.3 外部 API 抽样实测

| 探测 | 结果 | 结论 |
|---|---|---|
| 当前腾讯混元默认模型 `hy3-preview` | HTTP 400，错误码 1006，模型不存在；约 1.66 秒 | Key/地址被读取，但默认模型不可运行 |
| 模型列表接口 | 成功返回 40 个模型 | 接口和凭证能够访问模型端点 |
| `hunyuan-turbo-latest` | 返回模型已下线 | 不能作为自动回退模型 |
| `hunyuan-a13b` | 错误码 3008，资源包余量已用尽 | 需要补充额度或更换供应商/模型 |
| 得理 `search_laws` | 成功，1 条结果；约 3.96 秒 | 法律搜索接口真实可访问 |
| 得理 `search_cases` | 成功，1 条结果；约 2.92 秒 | 案例搜索接口真实可访问 |

注意：本次没有修改 `.env`，也没有把任何密钥写进本文。

### 2.4 资产与历史输出事实

| 项目 | 当前事实 |
|---|---:|
| 法律来源目录 | 69 个来源 ID |
| 法规条文登记 | 1,672 行，覆盖全部 69 个来源 |
| 法律资源总体积 | 约 49 MB |
| RAG 存储体积 | 约 10 MB |
| 缺失来源快照 | 0 |
| 重复定位键 | 34 组 |
| 没有来源 URL 的条文 | 1,273 行，主要为 `reference` 状态 |
| 历史 CitationMap | 650 份 |
| 历史引用项 | 16,681 项 |
| 当前规范化后仍未知来源 | 1 项，来自得理案例 ID，但仍被标记 `can_jump=true` |
| 只有来源、没有条号的已知引用 | 3,126 项 |
| `outputs/` | 约 720 MB、25,519 个文件 |
| `storage/reports` | 当前为空 |

这些数据说明：知识库和报告体系已有规模，但“能生成文件”和“能证明每个引用、产物和用户归属正确”仍是两回事。

---

## 3. 交付验收总契约

只有同时满足以下条件，才能说“所有功能按预期正常进行”。

### 3.1 每次运行必须拥有统一 Run ID

同一个 `run_id` 必须贯穿：

```text
前端提交
  → 后端任务
    → 工作流节点与工具事件
      → RAG/得理/LLM 调用
        → 引用登记
          → 输入快照与输出产物
            → CLI / 前端历史 / 下载 / 审计
```

禁止继续只靠文件时间戳猜测“某个输出属于哪次运行”。

### 3.2 每次运行必须落盘统一 Run Manifest

最小字段：

- `run_id`、`task_id`、`user_id`、模块 ID、案例 ID、开始/结束时间、总耗时、最终状态。
- 配置快照：不可变 ProviderSnapshot，包括提供商、模型、Base URL 指纹、能力/配置版本、健康检查 ID、得理是否启用；不得保存明文 Key。
- 调用汇总：LLM 次数、输入/输出/总 Token、是否估算、检索次数、得理次数、各阶段耗时、错误与回退。
- 输入：逻辑名称、文件名、MIME、大小、SHA-256、用户可见性、来源。
- 输出：逻辑角色、文件名、MIME、大小、SHA-256、主产物标记、预览能力、下载能力。
- 主张与引用：各 ClaimType/SupportRelation 数量、`exact_article`、来源级、外部核验、无法解析和校验失败数。
- 轨迹：事件数、节点数、内部 trace manifest 路径、是否完整和可选 OTel export 状态。

### 3.3 引用解析能力与站内受控交互

目标契约不再让一个 `can_jump: boolean` 同时承担“是否解析成功、跳到哪里、有哪些动作”三种语义，而是引入：

```text
CitationResolution
├── resolution_type
├── target_id
├── confidence
├── failure_reason
└── available_actions[]
```

| `resolution_type` | 解析要求 | 默认站内行为 | 可选后续动作 |
|---|---|---|---|
| `exact_article` | 来源和条号在本地知识库唯一匹配 | 打开具体条文抽屉 | 站内详情、用户主动打开官方来源 |
| `source_overview` | 来源存在，但缺少或无法唯一解析条号 | 打开法规概览并提示定位不足 | 站内搜索、用户主动打开官方来源 |
| `external_verified` | 外部来源已核验，但尚未映射本地对象 | 打开外部来源说明卡 | 用户确认后打开外链、进入待入库流程 |
| `unresolved` | 来源未知、冲突或校验失败 | 显示无法匹配原因 | 补充检索或人工复核，不直接跳转 |

引用点击的统一原则是“进入站内受控交互”，不是“所有状态打开完全相同的抽屉”。只有 `exact_article` 是精确知识库跳转；`source_overview` 是来源级站内导航，不能在文案上宣称已经定位条文。

迁移期间保留 `can_jump` 作为派生兼容字段，且只在 `resolution_type=exact_article` 时为 true。所有 API、前端和历史数据迁移完成后再删除该字段。

### 3.4 非技术用户的输入输出契约

- 前端只展示用户能理解的名称，例如“风险审查报告（PDF）”，不能以任意服务器路径为主信息。
- 同一文件不能因为同时标记为 `report` 和 `docx` 就显示两次。
- 主报告默认打开；相关附件按“输入材料、过程证据、最终报告、数据附件”分组。
- 支持的类型应直接预览；不支持预览的类型明确显示“仅可下载”。
- 所有下载均经过任务所有权校验，不能凭路径访问别人的文件。
- 历史运行恢复后，文件分组、预览、下载和引用跳转必须保持一致。

### 3.5 Provider Registry 的自动发现、校验和生效

“自动配置”不等于自动产生 Key。本文后续统一使用“Provider Registry”，其正确含义是：

1. 从 `.env` 和运行时配置读取候选配置；
2. 校验 Base URL、鉴权、模型列表和最小请求；
3. 显示“可用、模型无效、余额不足、网络错误、未配置”等明确状态；
4. 用户保存后原子切换，并刷新所有模块中已实例化的客户端；
5. 新运行记录实际使用的提供商和模型；
6. 失败时按明确策略回退，并在前端、CLI 和 manifest 同步显示；
7. 密钥不回显、不进日志、不进运行产物。

每个 Provider 至少声明并探测：

```text
ProviderCapabilities
├── chat_completion
├── streaming
├── tool_calling
├── structured_output
├── usage_reporting
├── model_listing
├── context_window
└── embedding
```

每次运行取得不可变 `ProviderSnapshot`，至少包括 `provider_id`、`model_id`、Base URL 指纹、能力版本、配置版本和健康检查 ID。正在运行的任务不随设置页面变更而中途换模型；只有新任务使用新快照。

---

## 4. 11 个业务模块覆盖矩阵

当前模块单一事实源为 `config/module_registry.json`。`us.eo_14117_flow_review` 的前端兼容键仍为 `cn_flow`，但业务归属是美国域。

| 模块 | 前后端入口 | 可编辑案例 | CLI | 一键填充并运行 | 通用 CitationMap/API | 当前结论 |
|---|---|---|---|---|---|---|
| `cn.transfer_diagnosis` | 有 | 有 | 有 | 有 | 特殊链路，未统一 | 部分具备 |
| `cn.security_assessment` | 有 | 有 | 有 | 有 | 有 | 部分具备 |
| `cn.document_review` | 有 | 有 | **无** | 有 | 独立报告链路 | P1 缺口 |
| `cn.pipia` | 有 | 有 | 有 | 有 | 有 | 部分具备 |
| `us.eo_14117_flow_review` | 有 | 有 | 有 | **无** | 有 | P1 缺口 |
| `eu.scc_review` | 有 | 有 | 有 | 有 | 有 | 部分具备 |
| `eu.bcr_review` | 有 | 有 | 有 | 有 | 有 | 部分具备 |
| `eu.dpia` | 有 | 有 | 有 | 有 | 有 | 部分具备 |
| `eu.tia` | 有 | 有 | 有 | 有 | 有 | 部分具备 |
| `us.eo_14117` | 有 | 有 | 有 | **无** | 有 | P1 缺口 |
| `us.cpra` | 有 | 有 | 有 | **无** | 有 | P1 缺口 |

补充说明：

- 当前 CLI 有 14 份 JSON 案例，案例内容可直接编辑。
- 前端 `dev-test-cases.ts` 对 11 个模块都有案例。
- 通用“测试案例”选择器目前只填表，不自动运行。
- 模块专用一键运行只覆盖 8 个模块，形成了重复按钮和不一致操作。
- “有 CitationMap”不等于所有引用都能准确落到唯一条文；这一点必须由引用完整性测试另行证明。

---

## 5. 发布阻断项与详细缺口

优先级总览：

| ID/事项 | 级别 | 定级理由 |
|---|---|---|
| P0-01 产物跨用户读取 | P0 | 数据安全和租户隔离 |
| P0-02 事件/引用无所有权校验 | P0 | 数据隔离和任务信息泄露 |
| P0-03 机械补引用 | P0 | 可能制造不存在的证据关系 |
| P0-04 未知来源被标为可跳转 | P0 | 证据真实性和知识库目标错误 |
| P0-06 Python Hash 跨进程不稳定 | P0 | 当前向量索引已经持久化并跨进程/重启复用，条件已满足 |
| ENV-BLOCK-01 LLM 模型/额度不可用 | ENV-BLOCK | 需要账号额度或供应商选择；代码负责发现和清楚阻断 |
| P1-01 引用默认新开页面 | P1 | 产品交互与知识库闭环，不等同数据泄露 |
| P1-02 运行时配置刷新不全 | P1 | 用户已被提供热切换入口，下一阶段必须保证新任务配置一致 |
| RunManifest/持久事件不完整 | P1 | 复验、CLI/前端一致性和故障恢复 |
| Markdown/证据分层呈现 | P1 | 非技术用户核心体验和引用可理解性 |
| ReportDocument 全模块迁移 | P1→P2 | 先迁移最小语义层，复杂块按真实需要迭代 |
| 得理/Hybrid/Reranker 演进 | P1→P2 | 先完成外部证据归一化和基准，再按收益选型 |
| 大文件和目录重构 | P2 | 必须晚于行为锁定与稳定契约 |

下面按 ID 记录证据、修改边界和验收条件；编号不连续是因为 P1/ENV 项从原 P0 列表重新分类后保留了事实追踪关系。

### P0-01：输出产物存在跨用户读取风险

**证据**

- `backend/api/v1/endpoints/artifacts.py` 的访问判断包含宽泛回退：路径含 `outputs/` 或以 `.html` 结尾时即可通过。
- 这意味着任意已登录用户只要获得或猜到路径，就可能读取并非自己任务产生的文件。

**必须修改**

- 删除基于路径字符串的授权回退。
- 所有产物必须先登记 `artifact_id → run_id/task_id → owner_id`。
- 预览和下载都只接受 `artifact_id`，服务端查询归属后再解析物理路径。
- 历史未登记产物如果要兼容，应通过一次受控迁移建立归属；无法确认归属的不得公开访问。

**验收测试**

- 用户 A 能访问自己的报告。
- 用户 B 使用 A 的 artifact ID、task ID 或已知路径均得到 403/404。
- URL 编码、相对路径、符号链接和 `.html` 后缀不能绕过校验。

### P0-02：事件流和引用接口没有任务所有权校验

**证据**

- `backend/api/v1/endpoints/events.py` 可按 task ID 获取或订阅事件，当前没有用户归属判断。
- `backend/api/v1/endpoints/citations.py` 可按模块和 task ID 读取引用，当前没有任务所有权判断。

**必须修改**

- 创建统一 `assert_task_access(current_user, task_id)`。
- 事件、引用、产物、任务状态、取消操作共用同一授权逻辑。
- CLI 本地运行可使用显式 `local_test` 主体，不允许以关闭授权的方式复用生产路由。

**验收测试**

- 两用户隔离测试覆盖 GET、SSE、取消、引用和产物。
- 不存在的任务统一返回 404，避免泄露任务是否存在。

### P0-03：规则化补引用可能制造虚假支撑

**证据**

- `backend/common/llm/postprocess.py` 中的 `ensure_paragraph_citations()` 会把同一组最多 3 条引用追加到每个段落。
- 没有引用时会生成 `【依据：未检索到】`。
- `module_generator.generate_chapter()` 即使没有稳定的逐主张标记，也会调用该逻辑。

**风险**

- 段落与文献可能没有对应关系，却在视觉上表现为有依据。
- 相同引用被机械重复，既不美观，也无法审计每个主张由哪条原文支撑。

**必须修改**

- 只用规则处理确定性问题：标记是否闭合、Citation ID 是否存在/重复、Markdown AST 是否有效、条文 ID 是否能唯一解析。
- “证据是否支持主张、支持多少、司法辖区和时间是否适用、是否存在冲突”属于语义和法律适用问题，不能由追加角标规则解决。
- 采用证据先行链路：检索并保存证据片段 → 形成待证明主张 → 判断支持关系和法律适用条件 → 生成带引用正文 → 再验证关系。
- 生成阶段使用稳定引用标记，例如 `[[cite:registry_id]]`，但明确它只是传输格式，不是正确性证明。
- CitationRegistry 保存 `claim_id → evidence_id → source_document_id → evidence_span_id → support_relation`。
- 未找到依据时保留结构化 `unsupported_claim`，前端显示风险提示，不伪造成引用。
- 旧规则只允许在历史内容迁移入口使用，并记录降级警告，不能进入新报告主链路。

最小支持关系：

| `support_relation` | 含义 |
|---|---|
| `direct_support` | 证据直接支持主张的完整关键表述 |
| `partial_support` | 只支持主张的一部分或部分限定条件 |
| `background` | 仅提供背景，不能独立支撑结论 |
| `conflict` | 与主张存在实质冲突 |
| `insufficient` | 相关但不足以支持 |
| `user_fact` | 来自用户输入/附件的业务事实，不是外部法律依据 |

模型给出的 relation 是待校验判断，不是客观真值。低置信度、冲突、高风险结论和关键效力判断必须进入人工复核或专门门禁。

**Citation Policy**

| ClaimType | 最小依据要求 | 引用策略 |
|---|---|---|
| `LEGAL_RULE` | 有效法律/监管/司法解释片段 | 必须引用，且校验辖区、时间和层级 |
| `CASE_FACT` | 用户表单或输入文件片段 | 必须追溯用户材料，不伪装成法律引用 |
| `RISK_JUDGMENT` | 事实依据 + 法律规则 | 两类依据都必须存在；缺一则降级 |
| `RECOMMENDATION` | 已确认风险、法律义务或业务约束 | 追溯前提，不要求每个措辞重复角标 |
| `SUMMARY` | 复用本节已验证依据 | 可以复用，不强制新增引用 |
| `TRANSITION` | 无 | 不要求引用 |
| `ASSUMPTION` | 无或待确认材料 | 必须显式标为假设，不能写成事实 |

**验收测试**

- 每个引用标记都能反查到证据片段。
- 删除证据后，相应主张变为“不足证据”而不是自动换用无关文献。
- 同一引用仅在实际支撑的主张后出现。
- `LEGAL_RULE`、`CASE_FACT`、`RISK_JUDGMENT` 分别满足 Citation Policy；`TRANSITION` 不因无引用而失败。
- 正式结论只使用通过门禁的主张；假设、冲突和证据不足只能在明确标注的待确认/限制区出现。

### P0-04：CitationMap 的 `can_jump` 判定不可信

**证据**

- `backend/common/citation/output.py` 无法解析来源时会保留原始 `source_id`。
- 随后仅依据“source_id 非空且有 URL”设置 `can_jump`，导致未知来源也可能被标记为可跳转。
- 历史规范化后仍有 1 个得理案例 ID 不在知识库，却被标记 `can_jump=true`。
- 3,126 个已知来源引用没有条号，只能定位来源，不能定位具体知识库条文。

**必须修改**

- 引入第 3.3 节的 `CitationResolution`，不能由 URL 或字符串非空推导解析能力。
- 状态至少区分：`exact_article`、`source_overview`、`external_verified`、`unresolved`。
- 兼容字段 `can_jump` 只由 `exact_article` 派生；不能反向决定解析状态。
- 得理案例使用外部稳定标识，不冒充本地 `source_id`。

**验收测试**

- 未知 source、缺条号、重复条号、错误条号均为 `can_jump=false`。
- 69 个知识来源的有效条文抽样能准确打开前后文。
- CitationMap、报告脚注和抽屉正文三方名称、条号一致。

### P1-01：前端引用点击行为违反站内知识库目标

**证据**

- `frontend/src/components/citation/CitationMarkdownRenderer.tsx` 在 `can_jump` 时使用 `window.open(..., "_blank")`。
- 当前默认 `open_mode` 也是 `new_tab`。

**必须修改**

- 引用角标点击统一进入站内受控交互，根据 `CitationResolution` 打开具体条文、法规概览、外部来源说明或无法解析提示。
- 精确条文抽屉内通过前端路由跳到知识库详情页，并保留返回报告的位置。
- 官方来源外链放在抽屉内，标记为“查看官方来源”，由用户主动点击。
- 无法精确定位时明确显示原因：缺少条号、来源未入库、映射冲突或权限不足。

**验收测试**

- 浏览器测试断言点击角标后没有新标签页。
- 抽屉显示当前条文及前后条，并能站内导航。
- 返回报告后滚动位置和高亮引用保持。

### P0-06：RAG 哈希向量跨进程不稳定

**证据**

- `backend/common/rag/orchestrator.py` 的 `HashingEmbedder` 使用 Python 内置 `hash(token)`。
- Python 默认会对每个进程随机化字符串哈希；一个进程建出的向量索引，另一个进程查询时可能映射到不同维度。

**风险**

- 单进程测试可能通过，服务重启后检索排序却漂移。
- 已落盘向量无法证明与当前查询使用同一哈希种子。

**必须修改**

- 使用确定性哈希，如 SHA-256/xxhash 的固定实现，并在索引 manifest 记录 `embedder_id/version/dimension/tokenizer_version`。
- 版本变化时强制重建索引，禁止静默混用。
- 评估哈希检索仅作为轻量基线，后续可替换为正式嵌入模型，但接口契约保持稳定。

**验收测试**

- 两个独立 Python 进程对同一文本生成完全一致向量。
- 重启服务后固定查询的 Top-K 和分数一致。
- 旧版本索引被拒绝或显式迁移。

### ENV-BLOCK-01：当前 LLM 账号/模型真实不可用

**证据**

- 当前配置能解析到 `tencent_hunyuan`，但默认模型 `hy3-preview` 实测不存在。
- 其他候选模型分别遇到下线或余额不足。

**必须修改**

- 保存配置前调用模型发现和最小请求探测。
- 将“模型不存在”“模型下线”“额度不足”“鉴权失败”分别呈现。
- 不允许仅因 Key 非空就把提供商标记为可用。
- 对生产运行，若没有任何健康 LLM，任务开始前直接给出可理解的阻断信息；`--no-llm` 测试仍可运行。

以上是代码侧必须补齐的发现和呈现能力；它不能消除下面的账号/额度阻断。

**外部条件**

- 需要补充腾讯混元额度，或选择另一个有额度且已验证的模型/供应商。
- 这不是代码能自动绕过的问题。

### P1-02：运行时设置没有刷新全部模块实例

**证据**

- `backend/services/runtime_client_refresher.py` 能刷新一部分共享客户端。
- `eu_scc`、`us_14117` 等路由级全局 service 实例没有全部重新绑定。
- 模块服务普遍在 import 时初始化，设置保存后可能继续使用旧客户端。

**必须修改**

- 不再让业务模块持有不可替换的全局 LLM/得理客户端。
- 由请求级或 run 级依赖容器获取客户端快照。
- 过渡期内建立完整实例注册表，保存配置后原子刷新并测试 11 个模块。

**验收测试**

- 运行中修改提供商后，新任务使用新配置，旧任务仍使用启动时快照。
- 11 个模块都记录实际 provider/model，不出现前端显示新配置、后端仍调用旧配置。

---

## 6. 中间过程、Token、耗时与任务协调

### 6.1 已有能力

- `backend/common/trace/recorder.py` 能记录工具开始和结果事件。
- `LLMClient.chat_with_metadata()` 能将供应商返回的输入、输出、总 Token 和来源写入事件。
- `frontend/src/lib/useTaskEvents.ts` 能聚合 workflow/copilot Token。
- `RunTranscript`、`TraceRunHeader`、`TraceNodeView` 能显示事件、节点、耗时和 Token。
- `AssistantPanel` 能显示会话 Token。

### 6.2 仍需补齐

1. 当前持久化 trace manifest 只有创建时间、事件数和事件文件，没有总耗时、Token、provider、fallback、run_id。
2. `backend/common/workflow/trace.py` 另有更丰富的 `TraceManifest` 模型，但实际 `TraceRecorder.write_manifest()` 没有采用，形成双契约。
3. SSE 事件只在内存中，任务结束 30 分钟后清理，服务重启即丢失。
4. 任务管理器也是内存态；取消操作可能只改状态，已启动的后台逻辑仍继续执行。
5. `_execute` 在 runner 包装器返回后再读取 `current_trace`，上下文可能已经重置，最终事件补发不可靠。
6. `TaskEventBridge` 以栈方式匹配 tool start/result，并发或嵌套工具可能配错。
7. 当前没有统一价格表和成本字段；Token 只代表供应商返回或估算量，不等于可核账费用。

### 6.3 目标实现

- 合并当前重复 Trace 模型，明确分层：RunManifest 是 AI4Law 业务运行账本，技术 trace 可通过版本化适配层导出 OpenTelemetry。
- 每个节点记录 `queued_at/started_at/ended_at/duration/status`。
- 每次 LLM 调用记录 provider、model、input/output/total token、usage source、latency、retry、error、fallback。
- 每次 RAG/得理调用记录 query ID、索引、Top-K、命中数、耗时和降级路径，不在日志中泄露敏感全文。
- 事件增量写入持久存储，SSE 只是读取通道，不是事实存储。
- 真正取消要把取消令牌传入工作流、检索和 LLM 调用边界。
- 前端同时提供“普通用户进度”和“开发者详细轨迹”，避免非技术用户直接面对原始 JSON。

分工如下：

| 层 | 负责内容 | 不负责内容 |
|---|---|---|
| RunManifest | 用户、模块、案例、输入输出、CitationMap、配置快照、审计和结论状态 | 不绑定某个监控厂商或 OTel 版本 |
| Trace/Span | workflow、retrieval、LLM、tool、renderer、artifact 的耗时、Token、重试、异常 | 不作为业务所有权和产物账本 |
| OTel adapter | 将内部 trace 字段映射到选定版本的 GenAI semantic conventions | 不反向控制核心业务 Schema |

采用映射层而不直接依赖的原因：OpenTelemetry 原 GenAI 页面已经迁移到独立仓库；该仓库当前没有正式 release，Schema URL 仍是 TODO。应锁定兼容版本、保留 contract test，并允许在不迁移业务数据的情况下升级映射。

### 6.4 验收条件

- CLI、前端实时视图、前端历史视图读取同一个 run manifest，数值一致。
- 服务重启后仍能打开已完成运行的时间线。
- Token 汇总等于各调用之和，并标明 `provider_reported` 或 `estimated`。
- 无 LLM 模式下 Token 明确为 0，不显示空白或伪造数据。
- 取消后不再产生新 LLM 调用和新最终报告。
- OTel 导出关闭或不可用时不影响 RunManifest 落盘；开启后 span 汇总与 RunManifest 的耗时/Token 可对账。

---

## 7. 知识库、CitationMap 与引用跳转

### 7.1 当前真实链路

```text
模块证据/脚注
  → backend/common/citation/output.py 规范化
    → outputs/<module>/<task>/outputs/citation_map.json
      → citations API 再规范化
        → CitationMarkdownRenderer
          → 当前可能新开页面，或打开引用抽屉
```

主要报告模块已经使用 CitationMap；诊断和文书审查仍有特殊报告链路，应统一到同一引用注册表，但不要求强行使用完全相同的报告正文结构。

### 7.2 知识库正确性检查项

- 目录中的 69 个 source ID 必须是唯一、稳定、可版本化的规范来源标识。
- 34 组重复定位键必须查明是版本差异、章节重复还是脏数据，并建立确定性消歧规则。
- 来源快照、条文登记、法规状态和 URL 之间应有机器校验。
- `effective` 与 `reference` 必须影响 RAG 使用政策，参考材料不得被当作现行法直接支撑最终结论。
- 得理返回结果必须经过来源对齐；匹配本地法规后才获得内部 source ID。
- 案例是 L3/参考证据，必须与法律法规类型分开显示和排序。

### 7.3 CitationMap 目标结构

每个引用至少包含：

- `citation_id`、`claim_id`、`evidence_id`、`evidence_span_id`、展示序号；
- 证据类型：法律、监管文件、合同条款、案例、用户材料；
- 规范化 `source_id`，或明确 `external_source_id`；
- 标题、条号、版本/生效状态、精确证据片段；
- 知识库匹配状态、唯一条文 ID、官方 URL；
- `support_relation`、关系置信度和验证状态；
- `CitationResolution`：解析类型、目标、可用动作和失败原因；
- 检索来源、检索时间和证据质量层级。

其中 `claim_id/evidence_id/span_id` 解决可追溯性，`support_relation` 表达证据与主张的关系，`CitationResolution` 只负责交互能力；三者不能合并成一个 `can_jump` 或“相关度”字段。

### 7.4 必须新增的完整性门禁

1. CitationMap JSON Schema 校验。
2. 所有内部引用都能在 `regulation_articles.jsonl` 唯一解析。
3. 报告中的引用序号与 CitationMap 一一对应，无孤儿、无重复冲突。
4. 得理外部 ID 不得写入本地 source ID 字段。
5. 报告引用的法规状态符合模块所在司法辖区和日期。
6. 文书审查中的“用户合同第 X 条”与外部法律引用分开处理。
7. 站内抽屉、知识库详情、官方外链三种路径在浏览器端分别验证。
8. 支持关系检查主体、时间、辖区、规范层级和冲突证据；模型判断为低置信度时不得静默放行。

---

## 8. RAG 原理、当前实现与得理 API 结合方案

### 8.1 当前 RAG 原理

当前多索引 RAG 在中国、欧盟、美国三个域下，按以下五类资源建立索引：

- 法律法规 `legal`
- 工作流知识 `workflow`
- 标准条款 `standard_clause`
- 报告模板 `template`
- 测试案例 `testcase`

共 15 个逻辑索引，每个索引包含文档和向量数据。检索时：

1. 查询文本被分词并转换为 384 维哈希向量；
2. 同时进行向量相似度和关键词检索；
3. 使用 Reciprocal Rank Fusion 合并排名；
4. 使用 UsagePolicyFilter 限制不同层级材料能否进入最终报告；
5. 稳定服务依次尝试多索引、单索引和兼容回退。

这一设计的优点是本地、快速、可离线和可解释；当前最大技术风险是哈希向量跨进程不稳定，且缺少系统检索质量基准。

### 8.2 当前得理结合方式

当前不是统一的混合检索：

- 安全评估会对 HIGH/BLOCKER 问题额外搜索得理法律和案例。
- 文书审查会对部分条款搜索得理案例。
- 诊断旧链路可搜索得理法律和案例。
- 通用兼容回退主要搜索法律，而且通常只有本地多索引和单索引都没有结果时才触发。
- BCR 等模块虽然接受法律服务依赖，但实际主链路仍以本地检索为主。

因此，得理目前更像“局部增强或兜底”，尚未形成统一、可审计、可衡量的 RAG 数据源。

### 8.3 当前得理适配器丢失的关键信息

`DeliLegalService.search_laws/search_cases` 当前仅归一化为：

- `title`
- `source`
- `summary`

至少还需要保留：

- 得理稳定 ID/gid；
- 资源类型（法律、行政法规、监管文件、案例等）；
- 精确条号、案号、发布日期、生效/失效状态；
- 司法辖区；
- 原文或可核验片段；
- 官方 URL/得理来源 URL；
- 检索时间与原始响应版本。

没有这些字段，就不能可靠去重、入库、判断效力或生成站内精确引用。

### 8.4 证据对象与条件触发的外部发现链路

检索结果先归一化为最小 EvidenceRecord：

```text
EvidenceRecord
├── evidence_id
├── source_type
├── source_id / external_source_id
├── article_id / case_id
├── span_id + exact_text
├── jurisdiction
├── effective_from / effective_to
├── authority_level
├── retrieval_score
└── provenance
```

`exact_text`/span 不能用标题、摘要或 URL 代替；如果外部 API 没有返回可核验片段，该结果只能作为发现候选，不能直接支撑正式法律结论。

```text
业务问题与司法辖区
  → QueryPlan：需要法律、案例、条款还是用户材料
    → 本地多索引检索 + 置信度/覆盖检查
    → 触发条件判断
       ├─ 本地证据充分且有效 → 不调用得理
       └─ 本地置信度不足 / HIGH-BLOCKER / 用户要求最新法规或案例 /
          本地版本可能过期 / 需要裁判实践 → 调用得理
         ↓
      external_candidate
         ↓
  来源对齐 + 效力/类型/版权/稳定ID核验
    ├─ 匹配本地唯一条文 → exact_article
    ├─ 外部证据可核验 → external_verified
    └─ 信息不足或冲突 → unresolved / human_review_required
         ↓
  去重、效力校验、证据分层、混合排序
         ↓
  Claim–Evidence 支持关系验证
         ↓
  报告、CitationMap、审计轨迹
```

得理的正式定位是：外部法规发现器、版本/效力核验器和案例增强器，不是所有中国法查询的默认并行检索器，也不是本地知识库的自动覆盖源。

### 8.5 如何充分发挥得理优势而不放大风险

- 法规发现：本地库缺口、最新法规或用户提及但本地未收录的规范。
- 条文校对：核验规范名称、条号、状态和文本差异；不能自动覆盖本地版本，必须记录差异。
- 案例增强：为高风险结论补充指导案例和裁判思路，但明确标为案例证据。
- 评估问题扩展：对 HIGH/BLOCKER 议题生成补充检索，而非对每个普通段落盲目调用。
- 知识库候选入库：外部结果先进入待审核区，经稳定 ID、版权、版本和效力校验后再入正式库。
- 成本控制：以司法辖区、问题类型、风险等级和本地命中质量决定是否调用，并在 run manifest 中记录原因。

### 8.6 RAG/得理验收基准

- 建立每个司法辖区的金标查询集，至少覆盖精确条文、同义问法、失效法规、跨境场景和案例查询。
- 指标至少包括 Recall@K、MRR、唯一条文命中率、失效法规误用率、未知来源误跳转率、得理增益、延迟和调用次数。
- 对比四组：关键词、本地混合、本地+得理、无 RAG LLM。
- 得理“有增益”必须体现在正确条文/案例召回或风险发现提升，不能只看返回数量。
- Live 测试使用显式开关和预算上限，默认离线测试不得偷偷调用外部 API。

### 8.7 检索器演进：立即修复与实验候选分开

**立即工程修复**

- 固定哈希算法和 tokenizer，索引记录版本；当前索引已经落盘并跨重启使用，因此 P0-06 的触发条件已经成立。
- 查询和索引版本不一致时拒绝服务并要求重建。
- 建立本项目法律金标集，先得到当前关键词/哈希/RRF 基线。

**通过基准再决定的候选链路**

```text
司法辖区/日期/文献类型/效力过滤
  → BM25 稀疏检索
  → Dense 向量候选
  → RRF 或学习权重融合
  → Cross-Encoder 或受控 LLM Reranker
  → 条文级 span 提取
  → 法律效力、主体和冲突校验
```

上述顺序是实验候选，不是已经批准的最终架构。2026 年一项文本与表格金融问答基准显示，Hybrid＋神经重排优于单阶段方法，BM25 也可能优于单独 Dense；但其领域不是法律，不能直接外推为 AI4Law 的生产结论。AI4Law 必须用自己的法律金标集比较准确率、失效法规误用率、延迟和成本后再选择。

暂不默认引入多轮 Query Expansion、HyDE 或复杂 Agentic RAG；只有基准证明对明确查询类型有净收益时才启用。

---

## 9. 输入输出文件与非技术用户体验

### 9.1 已有能力

- `ResourcePanel` 能显示每次提交表单、递归发现的输入文件和输出文件。
- `ModuleRunPanel` 能打开、下载报告，并自动切换 Markdown/PDF 视图。
- 产物接口支持 HTML、PDF、DOCX、MD、TXT、JSON、CSV 预览。
- XLSX、ZIP 当前主要是下载；文书审查另有局部文件预览能力。

### 9.2 具体不足

1. 产物和运行的关联部分依赖时间范围推断，没有持久 `run_id`，恢复历史时可能错组。
2. 同一路径可能以不同 kind 被重复登记，前端目前只是在展示时按路径去重。
3. 物理路径泄露到前端契约，既不友好，也增加越权面。
4. 输入没有统一的不可变快照契约，无法保证复跑时使用的就是当时那份文件。
5. 主报告、附件、证据包、机器 JSON 的用户可见级别没有统一定义。
6. 图片、XLSX、ZIP 等预览能力在不同模块表现不一致。
7. `outputs/` 已约 720 MB，需要保留策略、去重和清理机制；但清理前必须先建立归属和可恢复策略。

### 9.3 目标文件模型

“不冗余”必须区分物理内容重复和合法的多格式交付。Markdown、DOCX、PDF 可以来自同一报告，但仍是用户需要的不同格式；同一路径被重复扫描成两个条目则是逻辑重复。

建立两层模型：

```text
ContentBlob
├── content_hash
├── storage_key
├── size
└── mime

ArtifactRecord
├── artifact_id
├── run_id / owner_id
├── role / format / display_name
├── blob_hash
├── derived_from
└── preview/download policy
```

ArtifactRecord 至少包括：

- `artifact_id`、`run_id`、`owner_id`；
- `role`：input/report/evidence/data/trace/debug；
- 用户展示名、原始文件名、MIME、大小、SHA-256；
- `primary`、`user_visible`、`previewable`、`downloadable`；
- 生成器、创建时间、来源 artifact；
- 受控 storage key，禁止对外暴露任意本地路径。

物理内容按 `content_hash` 去重，逻辑产物按 `artifact_id/role/format` 保留；PDF/DOCX 通过 `derived_from` 追溯同一个 ReportDocument。不得用“哈希相同”直接删除业务上需要独立展示或下载的格式。

### 9.4 验收条件

- 11 个模块的真实案例均能在前端看到输入快照和主输出。
- 报告 Markdown、PDF、DOCX 内容来自同一语义源，标题、表格、引用一致。
- 同一文件只出现一次；机器调试文件默认折叠或隐藏。
- 下载后校验 SHA-256 与 manifest 一致。
- 无技术背景用户能从名称和说明判断“这是什么、能否预览、为什么只有下载”。

---

## 10. LLM、小李 AI 与得理 Provider Registry

### 10.1 已有能力

- 后端设置支持全局得理配置和多个 OpenAI-compatible LLM 提供商。
- 前端设置页可以新增、删除、启用、选中提供商并测试 LLM 连接。
- `.env` 与 `storage/runtime_settings.json` 有配置优先级，接口返回有效配置时隐藏密钥。
- LLM 连接测试可返回延迟和 Token 使用。

### 10.2 具体缺口

- 已有得理专用“测试连接”接口和前端按钮，使用最小法规查询区分缺配置、鉴权、额度、限流、超时、网络和响应格式错误。
- 得理上次健康结果和最后成功时间尚未持久化，任务启动前也还没有基于健康快照执行条件阻断。
- 运行时设置以明文 JSON 保存密钥，至少需要严格文件权限；生产应接密钥管理服务。
- 任何已认证用户目前可能修改全局提供商，应增加管理员权限。
- 客户端刷新不完整，详见 P1-02。
- 没有按日/按运行的 Token、调用次数、预算和成本汇总。
- 当前代码中没有“小李 AI”这个具名提供商；只有通用 OpenAI-compatible 能力。

### 10.3 小李 AI 接入前必须明确的外部事实

- 正式 Base URL；
- 鉴权 Header/Token 格式；
- 模型名和上下文长度；
- 是否兼容 OpenAI chat completions、stream、usage 字段和 tool calls；
- 计费或额度接口；
- 错误码和限流规则。

拿到这些后，应通过提供商配置模板接入，而不是在业务模块里写“小李 AI 特判”。

### 10.4 Provider Registry 验收

- 设置页同时显示 LLM 和得理的配置来源、健康状态、延迟和上次测试结果。
- 保存前可测试；保存后 11 个模块的新任务都使用新配置。
- CLI 可通过案例文件引用 provider profile，但不能保存密钥。
- 前端、CLI、run manifest 的 provider/model/token/duration 完全一致。
- 额度不足时显示明确阻断，不自动反复重试消耗请求。
- 每个 Provider 能报告实际支持的 capabilities；不支持的 streaming/tool/structured output 不得由前端臆测为可用。
- 已开始运行的任务保持原 ProviderSnapshot，新任务使用新版本，不在单次运行中混用新旧配置。

---

## 11. CLI 与前端自动化测试入口

### 11.1 当前 CLI 结构

```text
backend/tests/harness/
├── runner.py
├── viewer.py
├── cases/
└── tests/
```

runner 当前会保存：

```text
runs/<adapter>/<run_id>/
├── input/request.json
├── input/hash.txt
├── output/result.json 或 error.json
├── trace/*.json
├── trace/manifest.json
└── run_manifest.json
```

这已经是可复用基础，不应另起一套 CLI。

### 11.2 CLI 补齐清单

- 为 `cn.document_review` 增加 `review` adapter 和真实文件案例。
- 案例支持 `input_files` 相对路径，复制到运行目录并保存哈希。
- run manifest 使用第 3.2 节统一契约。
- viewer 增加：分阶段耗时、Token、provider、模型、RAG 命中、得理调用、引用检查、产物列表。
- 增加 `--all-modules --no-llm`，至少每模块跑一个 smoke case。
- 增加 `--live-llm`、`--live-delilegal` 显式开关和最大调用数；默认绝不调用真实外部 API。
- 增加 `--case-file <path>`，用户可以复制 JSON 后直接修改，不必改 Python。
- 运行失败仍必须保存输入、错误、已有轨迹和部分产物。

CLI 的“可视化中间过程”不复刻前端 UI，而是从同一事件源输出实时、可复制的结构化时间线，例如：

```text
[00:00.000] RUN_STARTED
[00:00.121] PROFILE_EXTRACTED       121 ms
[00:00.482] RAG_RETRIEVAL           361 ms / 8 hits
[00:03.731] LLM_GENERATION         3249 ms / 3,842 tokens
[00:03.810] CITATION_VALIDATION      79 ms / 6 passed / 1 unresolved
[00:04.031] REPORT_RENDERED         221 ms
```

同一事件源按场景呈现：前端使用时间线和证据抽屉；CLI 使用表格/树状 trace；viewer 可以生成本地 HTML。验收重点是事件和汇总一致，而不是三者界面相同。

### 11.3 前端“一套按钮”目标

当前同时存在通用案例选择器和多个模块专用一键按钮，行为不一致。目标是：

- 开发环境仅显示一个“开发测试”入口；生产构建不显示。
- 入口读取与 CLI 同源或由同一 Schema 生成的案例定义。
- 提供“仅填充”和“填充并运行”两个明确动作，默认主按钮为“填充并运行”。
- 11 个模块全部使用正常的表单校验、payload builder 和提交 API，禁止测试专用旁路。
- 浏览器自动化点击同一个入口，验证表单、提交、事件、报告、文件和引用。

### 11.4 真实案例要求

- 每个模块至少一个最小成功案例和一个关键失败/边界案例。
- 文书审查必须包含真实可解析的 PDF/DOCX/MD 样本。
- RAG 案例应声明期望命中的 source/article，而不是只断言“返回非空”。
- 得理案例应声明是否必须调用、期望类型、外部稳定 ID 和是否允许入库。
- 案例文件不得包含密钥、真实个人信息或无法再分发的材料。

---

## 12. Markdown 生成与前端渲染

### 12.1 已有能力

- 后端已有 `ReportDocument`、`ContentAdapter`、Markdown/HTML/DOCX/PDF 渲染器。
- 安全评估已较明确地使用共享语义文档；其他模块接入程度不一。
- 前端使用 `react-markdown` 和 GFM，已有标题、表格、引用块、代码和引用角标样式。

### 12.2 具体缺口

1. `normalizeMarkdownBasics`、`normalizeFallbackMarkdown` 和后端法律 Markdown 规范化存在重复规则，容易漂移。
2. 规则化修标题/列表只能作为旧内容兼容，不能代替生成阶段的结构化文档。
3. `CitationMarkdownRenderer` 对段落、列表、引用块、表格单元格提取纯文本，会丢失链接、强调和行内代码等嵌套 Markdown。
4. 表头 `th` 没有与 `td` 同等的引用处理。
5. 宽表缺少稳定横向滚动容器。
6. 引用 popover 主要依赖 hover，触摸设备和键盘焦点体验不足。
7. 没有 Citation renderer、popover、drawer 和完整报告页面的组件/浏览器测试。
8. 最大问题不是 CSS，而是第 P0-03 所述主张—证据关系被规则化处理破坏。

### 12.3 推荐的单一语义源

```text
最小 ReportDocument
  ├─ metadata
  ├─ sections[]
  │    └─ blocks[]：heading / paragraph / table / cited_claim
  ├─ claims[]：claim_id / type / evidence_refs / support_status
  ├─ citations[]
  └─ artifacts[]
       ├─ Markdown renderer
       ├─ HTML renderer
       ├─ DOCX renderer
       ├─ PDF renderer
       └─ 前端安全渲染
```

- 模块负责产生语义块，不负责手搓 Markdown 字符串。
- Markdown 是输出格式之一，不是内部事实模型。
- 前端只做 AST 渲染和引用组件替换，不再重排中文标题和列表。
- 旧报告在读取边界做一次兼容规范化，并标记 `legacy_normalized=true`。

第一阶段只覆盖标题、普通段落、表格和带引用主张，不重新实现全部 Markdown 语法，也不要求模型一次输出一个庞大的完整报告 JSON。结构化约束集中在 `claim_id`、`claim_type`、`evidence_refs`、`support_status` 和 `section_id`；分析、建议、总结等自然语言仍按小节生成。

这样处理的原因是：结构化生成可以提高 Schema 合规性，但复杂约束也可能迫使 instruction-tuned 模型选择低置信度表达。应分别测试格式合规率和内容保真度，不能只因 JSON 验证通过就认为报告正确。

### 12.4 前端证据分层呈现

| 视图 | 展示内容 |
|---|---|
| 普通用户 | 结论、引用角标、简短依据摘要、证据不足提示 |
| 展开证据 | 具体条文、精确片段、支持关系、法规状态 |
| 审计模式 | Claim/Evidence/Span ID、检索轨迹、验证结果和 ProviderSnapshot |

Claim–Evidence 界面有助于暴露不支持的主张，但全部平铺会增加认知负担。因此默认视图保持简洁，证据关系按需展开；“可视化中间过程”不等于把原始 trace 全部展示给非技术用户。

### 12.5 Markdown 验收语料

至少覆盖：

- 中文多级标题、有序/无序/嵌套列表；
- GFM 表格、宽表、单元格内引用；
- 链接、粗体、斜体、删除线、行内代码；
- 引用块、代码块、换行和空段落；
- 同句多个引用、引用紧邻标点、无法解析引用；
- PDF/DOCX/HTML/前端之间的结构和引用一致性。

---

## 13. 代码结构与可扩展性

### 13.1 当前主要热点

| 文件 | 约 LOC | 问题 |
|---|---:|---|
| `frontend/src/components/workspace/ModuleRunPanel.tsx` | 3,751 | 11 模块表单、校验、payload、运行与按钮混在一起 |
| `frontend/src/components/workspace/WorkspaceShell.tsx` | 1,494 | 页面状态、恢复、报告和交互职责过多 |
| `frontend/src/lib/dev-test-cases.ts` | 1,412 | 案例巨大且与表单 payload 逻辑可能漂移 |
| `frontend/src/lib/app-store.tsx` | 768 | 跨模块状态集中 |
| `frontend/src/components/workspace/ResourcePanel.tsx` | 616 | 文件发现、分组、命名和 UI 混合 |
| `frontend/src/lib/trace-adapter.ts` | 612 | 事件兼容和展示模型耦合 |
| `backend/common/knowledge/builders_v2.py` | 1,321 | 知识库构建职责集中 |
| `backend/domains/us/eo14117/rule_engine.py` | 1,302 | 规则体量大，需要用测试保护后拆分 |

### 13.2 重复事实源

- 模块身份以 `config/module_registry.json` 为主，但前端 endpoint、表单、模板仍散落于 `frontend/src/api/modules.ts`、`features/module-runner/model.ts`、`task-templates.ts`。
- 当前 parity 脚本能检查迁移候选，不等于检查运行时 endpoint/schema/payload 完全一致。
- Trace 有两个 manifest 方向。
- Markdown 有前后端两套规范化。
- 产物既有通用注册，又有文书审查独立报告服务。

### 13.3 推荐目录边界

在行为测试锁定后，将前端按模块纵向拆分：

```text
frontend/src/features/module-runner/
├── core/                  # 统一提交、事件、产物、错误、测试入口
├── cn-transfer-diagnosis/
│   ├── schema.ts
│   ├── form.tsx
│   ├── build-payload.ts
│   └── cases.ts
├── cn-security-assessment/
└── ...其余模块
```

后端保持领域模块，公共契约集中于：

```text
backend/common/
├── runs/                  # RunManifest、任务归属、持久事件
├── artifacts/             # ArtifactRecord、预览下载
├── citation/              # CitationRegistry、知识库解析
├── rag/                   # QueryPlan、检索器、EvidenceRecord
├── providers/             # LLM/得理配置与健康检查
└── renderers/             # ReportDocument 多格式渲染
```

### 13.4 重构原则

- 先为现有行为补集成/E2E 测试，再移动文件。
- 每次只迁移一个纵向切片，并保持 11 模块矩阵可运行。
- 共享的是稳定契约和确定性机制，不把司法辖区差异硬抽象掉。
- 得理、LLM、RAG、引用、产物通过接口注入，不在模块内重新创建全局客户端。
- 大文件拆分以职责和数据边界为准，不以行数达标为目的。

---

## 14. 逐文件修改清单

### 14.1 第一批：发布阻断与统一契约

| 文件/目录 | 修改内容 | 对应验收 |
|---|---|---|
| `backend/api/v1/endpoints/artifacts.py` | 删除路径回退，改为 artifact 所有权 | P0-01 |
| `backend/api/v1/endpoints/events.py` | 增加任务归属校验 | P0-02 |
| `backend/api/v1/endpoints/citations.py` | 增加归属校验并返回 CitationResolution | P0-02/04 |
| `backend/common/citation/output.py` | 以知识库解析结果生成 CitationResolution，并派生兼容 `can_jump` | P0-04 |
| `backend/common/rag/orchestrator.py` | 确定性哈希和索引版本 | P0-06 |
| `backend/common/llm/postprocess.py` | 移除新报告机械补引用 | P0-03 |

### 14.2 第二批：运行、CLI、配置和产物

| 文件/目录 | 修改内容 |
|---|---|
| `backend/common/trace/recorder.py` | 统一内部 TraceManifest，并支持 OTel 适配导出 |
| `backend/common/workflow/trace.py` | 合并重复契约，增加 provider/retrieval/artifact 汇总 |
| `backend/services/runtime_client_refresher.py` | 迁移为不可变 ProviderSnapshot；过渡期刷新全部消费者 |
| `backend/tests/harness/runner.py` | 统一 manifest、文件输入、全模块和 live 开关 |
| `backend/tests/harness/viewer.py` | 显示 Token、耗时、RAG、得理、引用和产物校验 |
| `backend/tests/harness/cases/` | 增加 review 与边界案例 |
| 设置 API 与前端设置组件 | 得理测试、模型发现、健康状态、管理员权限 |
| `frontend/src/lib/useTaskEvents.ts` | 对齐持久 manifest 和实时增量 |
| `frontend/src/components/workspace/RunTranscript.tsx` | 普通/开发双层视图 |
| `frontend/src/components/workspace/ResourcePanel.tsx` | 按 run_id/role 展示，不按时间猜测 |
| `frontend/src/lib/dev-test-cases.ts` | 迁移为按模块案例并与 CLI Schema 对齐 |
| `frontend/src/components/citation/CitationMarkdownRenderer.tsx` | 站内受控交互，保留嵌套 Markdown 节点 |
| `frontend/src/components/citation/CitationArticleDrawer.tsx` | 按解析类型显示条文、概览、外部来源或失败原因 |

### 14.3 第三批：RAG、得理与报告单一源

| 文件/目录 | 修改内容 |
|---|---|
| `backend/common/rag/service.py` | 统一 QueryPlan、条件触发得理和可替换检索器实验接口 |
| 得理 service/adapter | 保留稳定 ID、条号、状态、URL、原文片段 |
| `backend/common/citation/` | EvidenceRecord/Claim/SupportRelation → CitationRegistry |
| `resources/legal/catalog/sources.csv` | 来源映射与状态校验 |
| `resources/legal/registry/regulation_articles.jsonl` | 处理 34 组重复定位键 |
| `backend/common/render/` | 扩展语义 CitationRef/UnsupportedClaim/ArtifactLink |
| 各领域报告 builder | 分模块迁移到 ReportDocument |
| 前端 Markdown 样式和组件 | 宽表、键盘/触摸、引用状态和一致渲染 |

---

## 15. 实施顺序与每阶段退出条件

### 阶段 0：冻结事实基线

- 保存本文中的测试结果和当前 11 模块矩阵。
- 建立最小浏览器 smoke 测试骨架。
- 不改业务算法，只把现有行为变成可重复证据。

**退出条件**：离线基线、CLI 抽样、浏览器登录与一个模块运行均可重复。

### 阶段 1：保证系统不输出错误的“可信结果”

- 产物/事件/引用归属校验。
- CitationMap 严格解析，未知来源不得冒充内部条文。
- 移除机械补引用，并区分确定性规则与语义支持判断。
- 确定性哈希索引。
- 增加 LLM/得理健康检查，将代码缺陷与 ENV-BLOCK 清楚呈现。

**退出条件**：P0-01、P0-02、P0-03、P0-04、P0-06 全部关闭；无健康 LLM 时系统在运行前明确阻断；不破坏 448/41 基线。

### 阶段 2：建立 Claim–Evidence–Artifact 运行闭环

- 建立最小 Claim、EvidenceRecord、EvidenceSpan、SupportRelation 和 CitationResolution。
- 持久 RunManifest、事件、Token、耗时、ProviderSnapshot、fallback、输入输出。
- 建立 ContentBlob/ArtifactRecord，完成所有权、逻辑角色和派生关系。
- 补齐 11/11 CLI。
- 完成 Provider Registry 和全部模块客户端刷新。
- 完成引用站内受控交互和普通/审计分层视图。

**退出条件**：同一运行可追踪 InputArtifact → Event/ModelCall → Evidence/Claim → Citation → OutputArtifact；CLI、前端实时和历史页面数值一致；11 模块 no-LLM smoke 全通过。

### 阶段 3：改进生成与检索质量

- 按 Citation Policy 实施证据先行生成和主张—证据验证。
- 得理按置信度、风险、时效和用户意图条件触发；完成来源对齐、效力和层级控制。
- 建立金标数据，对比关键词、当前哈希/RRF、BM25、Dense、Hybrid、Reranker 候选。
- 证据不足、冲突或低置信度时拒绝确定性结论或显式降级。

**退出条件**：主张级支持关系可复验；候选检索器和得理增益、误用率、延迟、成本有量化结果；架构选择有本项目基准而非论文类比。

### 阶段 4：Markdown、多格式与非技术用户呈现

- 模块逐个迁移到最小 ReportDocument。
- 删除主链路前后端二次 Markdown 规则化。
- 普通用户只看结论、摘要、进度和可操作产物；详细证据/trace 按需展开。
- 完成预览下载、多格式派生关系、历史产物迁移和浏览器视觉测试。

**退出条件**：11 个模块的输入、主报告和附件均可正确查看/下载；同一报告在 Web/MD/PDF/DOCX 的结构和引用一致；默认界面不向非技术用户倾倒原始 trace。

### 阶段 5：以稳定契约为边界进行结构化重构

- 拆分 ModuleRunPanel、WorkspaceShell 和大案例文件。
- 合并重复配置与重复 manifest。
- 清理只有在行为已被测试覆盖后进行。

**退出条件**：新增一个模块只需注册领域、Schema、表单/payload、案例和报告 builder，不再修改巨型 switch。

---

## 16. 全覆盖测试矩阵

| 层级 | 必测内容 | 是否已有 | 缺口 |
|---|---|---|---|
| 后端单元 | 规则、模型、规范化、服务 | 有，503 通过 | Live API 与浏览器联动不属于该层 |
| 前端单元 | API、store、PDF、artifact、事件、引用受控交互 | 有，48 通过 | 仍需真实浏览器 E2E 与视觉回归 |
| CLI no-LLM | 真实可编辑案例和落盘 | 10/11 | review、批量入口、统一 manifest |
| 外部 API contract | LLM/得理响应适配 | 零散/不足 | 得理 adapter 基本无测试 |
| Live integration | 真实 Key、模型、额度和延迟 | 手工抽样 | 需要显式开关和预算门禁 |
| 浏览器 E2E | 登录、填充运行、事件、报告、文件、引用 | 无 | 必须新增 |
| 安全 | 双用户任务/事件/引用/产物隔离 | 关键 API 已覆盖并通过；任务归属已持久化 | 仍需 11 模块浏览器 E2E 和部署态复核 |
| RAG 质量 | 跨进程确定性、金标 Top-K、效力、得理增益 | 跨进程确定性已覆盖；无系统质量基准 | 金标质量与得理增益必须新增 |
| 引用完整性 | CitationResolution、主张—证据—条文—UI 一致 | 解析状态与站内受控交互已覆盖；主张门禁为首版 | EvidenceSpan、全 ClaimType 和真实浏览器仍需完善 |
| 多格式一致性 | Web/MD/PDF/DOCX | 部分 | 需要语义快照和视觉测试 |
| 重启恢复 | 任务、事件、文件、引用 | 任务归属已持久化 | 事件进度、运行恢复和全产物恢复仍需故障注入 |
| 取消/异常 | 真取消、部分产物、重试、回退 | 部分 | 需要故障注入 |

### 16.1 当前可以直接运行的命令

```bash
uv run --frozen pytest -q
npm --prefix frontend test -- --run
npm --prefix frontend run build
uv run --frozen python scripts/check_local_new_parity.py
uv run --frozen python scripts/check_repository_hygiene.py
uv run --frozen python -m compileall -q backend
uv run --frozen python backend/tests/harness/runner.py diagnosis 01_scc_path --no-llm
uv run --frozen python backend/tests/harness/viewer.py <run_id>
```

### 16.2 需要实现后才能运行的目标命令

以下是待办接口，不是当前已经存在的脚本：

```bash
# 11 模块离线 smoke
uv run --frozen python backend/tests/harness/runner.py --all-modules --no-llm

# 显式真实服务测试，需限制调用预算
uv run --frozen python backend/tests/harness/runner.py assessment 01_basic --live-llm --live-delilegal

# 引用—知识库完整性
uv run --frozen python scripts/check_citation_integrity.py

# RAG 跨进程确定性与质量基准
uv run --frozen python scripts/check_rag_determinism.py
uv run --frozen python benchmarks/run_rag_benchmark.py

# 浏览器端到端
npm --prefix frontend run test:e2e
```

---

## 17. 外部依赖与不能由代码擅自决定的事项

1. 小李 AI 的 Base URL、模型名、鉴权和 usage 兼容方式需要提供方确认。
2. 当前腾讯混元账号需要补额度或明确替代模型/供应商。
3. 得理结果是否允许长期缓存、全文存储或入库，需要确认许可与版权边界。
4. 69 个法律来源和 34 组重复定位键的最终消歧，需要法律内容负责人确认。
5. Token 单价和预算策略需要产品/运营给出币种、价格版本和告警阈值。

代码可以准确发现并呈现这些阻断，但不能伪造配置、绕过额度或替代法律内容审核。

---

## 18. 完成证据模板

以后每关闭一项任务，必须在本节或对应 PR 中记录：

```text
任务 ID：
涉及模块：
修改文件：
行为变化：
新增测试：
执行命令：
实际结果：
Run ID / Artifact ID：
截图或报告路径：
已知限制：
提交 SHA：
验证日期与验证人：
```

禁止仅写“已完成”“已优化”“测试通过”，而不附具体命令、结果、运行 ID 和可核对产物。

### 18.1 2026-07-22 第一批 P0 落实与验收记录

本记录只关闭已经由代码和自动化测试证明的范围，不把 Live LLM、得理真实调用、11 模块浏览器 E2E 或最终 Definition of Done 误报为完成。

| 任务 ID | 已落实行为 | 关键提交 | 可核对测试 |
|---|---|---|---|
| P0-01 | 删除 `outputs/`、任意 HTML 和开发上传目录的预览放行；制品必须由当前用户的 `ReportArtifact` 或 `UploadedFile` 登记 | `245f7b0` | 所有者可访问、其他用户 403、未登记 HTML 403 |
| P0-02 | 新增持久化 `TaskOwnershipModel`；事件流、事件轮询、CitationMap、引用详情、9 个异步模块的状态与重试统一鉴权；未登录 401，非所有者与不存在任务统一 404 | `2ecd30a`、`0ef4b71` | 30 项聚焦测试覆盖持久化、重启语义、9 模块提交/状态/重试与双用户隔离 |
| P0-04 / P1-01 | 引入 `CitationResolution`；仅本地唯一条文为 `exact_article` 和 `can_jump=true`；缺条号、错误条号、34 组重复定位降级为 `source_overview`；前端点击只打开站内受控抽屉；详情接口与解析器共用定位归一化规则并以注册表为唯一真值源 | `3276928`、`d97ba7e`、`7fd8489` | 后端引用/知识库聚焦 114 项、前端引用交互 5 项；逐条核对 1,602 个唯一定位，覆盖 69/69 个来源；34 组重复键明确拒绝精确详情 |
| P0-03 | 检索结果只作为引用允许列表，不再轮流附到每段；拒绝虚构引用、`【依据：未检索到】` 和未登记数字脚注；法律规则/风险判断缺依据时显式标为待核验 | `803c073` | 15 项 Citation Policy 单测；相关渲染、评估和 DPIA 回归合计 119 项通过 |
| P0-06 | 用 `SHA-256` 固定映射替换进程随机 `hash()`；索引记录 `sha256-v1` 与维度，多索引 Schema 升至 `v3.2`；不兼容索引自动重建，禁用重建时拒绝加载 | `0ad52ff` | RAG 18 项；两个不同 `PYTHONHASHSEED` 的独立进程完成建索引→查询并命中同一条文 |
| 测试隔离 | DPIA 异步回归显式注入禁用的 LLM，不再继承开发者 `.env` 密钥或偶然访问真实 Provider | `c10aa80` | 修复前根目录全量为 495 通过 / 1 失败（真实 Provider 返回“模型不存在”并超时）；修复后同一命令 496 通过 |

**整体验收命令与实际结果**

```text
命令：.venv/bin/pytest -q
结果：496 passed, 1 warning in 87.75s；退出码 0
说明：唯一警告为 Starlette TestClient 对 httpx 的弃用提示，无业务测试失败。

命令：npm --prefix frontend test -- --run
结果：14 test files passed，46 tests passed；退出码 0
说明：日志中的 chunk load failed 是 LazyRouteErrorBoundary 测试主动抛出的夹具异常，该测试通过。

命令：npm --prefix frontend run build
结果：TypeScript 与 Vite 生产构建成功，342 modules transformed；退出码 0

命令：.venv/bin/pytest -q backend/services/tests/test_knowledge_index.py backend/common/citation/tests backend/api/v1/tests/test_citations_api.py backend/api/v1/tests/test_knowledge.py backend/api/v1/tests/test_knowledge_review.py backend/domains/cn/security_assessment/tests/test_citation_builder.py
结果：114 passed, 1 warning in 2.11s；退出码 0

命令：.venv/bin/python scripts/check_local_new_parity.py
结果：Local-new parity check passed (56 source candidates).

命令：.venv/bin/python scripts/check_repository_hygiene.py
结果：Repository hygiene check passed (963 repository files checked).

命令：.venv/bin/python -m compileall -q backend
结果：退出码 0
```

**本轮证据边界**

- Run ID / Artifact ID：不适用；本轮为离线自动化与生产构建验收，没有伪造 Live Run。
- 外部 API：最终验收为离线运行，没有成功的小李 AI 或得理生成调用。首次全量审查曾因测试隔离缺陷向 `.env` 中配置的 Provider 发送请求，均被“模型不存在”拒绝，无成功生成或 usage 记录；该泄漏已由 `c10aa80` 阻断。仍不能据此声称真实 Provider、Token 计费、额度、延迟或得理内容质量已经通过。
- 浏览器：已完成组件级受控交互测试，但尚未完成登录后真实页面、多标签页数量、滚动位置和 11 模块端到端验收。
- 引用门禁：已阻断机械补引并覆盖 `LEGAL_RULE`、`RISK_JUDGMENT` 的首版确定性规则；完整 Claim/EvidenceSpan/SupportRelation 和 `CASE_FACT` 证据门禁仍属于后续阶段。
- 法律内容：34 组重复定位键不会再伪装为精确跳转，但最终消歧仍需法律内容负责人确认。
- 工作树：未改动或纳入本轮代码提交的用户既有状态为 `AUDIT_MISSING_FEATURES.md` 删除、`docs/archive/AUDIT_MISSING_FEATURES.md` 和 `plan/`；本文档从 18.2 起作为验收账本纳入 Git 存档。

### 18.2 2026-07-22 LLM Provider 健康探测切片

| 任务 | 已落实行为 | 关键提交 | 可核对证据 |
|---|---|---|---|
| ENV-BLOCK-01 探测契约 | OpenAI-compatible Provider 先执行模型发现，列表中不存在当前模型时不再发送生成请求；最小生成失败稳定区分模型不存在/下线、余额不足、鉴权失败、限流、超时、网络和未分类 Provider 错误；设置页显示稳定错误码并将发现的模型提供给 Model 输入框 | `48ce2a4` | TDD 红灯分别证明旧逻辑仍会对不存在模型发送生成请求，且余额错误只返回 `PROVIDER_ERROR`；绿灯后 Provider 聚焦 17 项、前端全量 47 项、生产构建均通过 |

**当前全量验收**

```text
命令：.venv/bin/pytest -q
结果：499 passed, 1 warning in 89.43s；退出码 0

命令：npm --prefix frontend test -- --run
结果：15 test files passed，47 tests passed；退出码 0

命令：npm --prefix frontend run build
结果：TypeScript 与 Vite 生产构建成功，342 modules transformed；退出码 0
```

**证据边界**：本切片已完成可理解的 LLM 错误发现和前端呈现，但 ENV-BLOCK-01 尚未整体关闭；保存前强制验证、生产任务启动前阻断和真实有额度 Provider 验收仍待后续切片落实。

### 18.3 2026-07-22 得理 API 健康探测切片

| 任务 | 已落实行为 | 关键提交 | 可核对证据 |
|---|---|---|---|
| 得理健康探测 | 新增需认证的 `/api/v1/system/settings/delilegal/test`；复用已保存但前端已脱敏的 Secret；使用一次最小法规查询检查真实能力；稳定区分缺配置、鉴权、额度、限流、超时、网络、无效响应和未分类错误；前端显示延迟、命中数或稳定错误码 | `6bb22f2` | 缺少端点时公开 API 测试先以 404 红灯失败；前端按钮行为测试先因找不到“测试得理连接”失败；绿灯后得理/Provider 聚焦 20 项、前端全量 48 项和生产构建通过 |
| 路由契约补齐 | 得理端点纳入全应用路由基线，路由总数从 100 更新为 101 | `6f825c6` | 首次根目录全量精确捕获 502 通过 / 1 失败，失败原因为新端点未进入 `route_baseline.json`；补齐后路由契约 4 项通过，根目录全量 503 项通过 |

**当前全量验收**

```text
命令：.venv/bin/pytest -q
结果：503 passed, 1 warning in 85.32s；退出码 0

命令：npm --prefix frontend test -- --run
结果：15 test files passed，48 tests passed；退出码 0

命令：npm --prefix frontend run build
结果：TypeScript 与 Vite 生产构建成功，342 modules transformed；退出码 0
```

**证据边界**：本轮没有真实得理凭证和授权额度可用于 Live 验收，因此只能证明探测契约、错误分类、脱敏密钥复用和前端呈现正确，不声称得理真实账号已健康。

---

## 19. 最终 Definition of Done

- 11/11 模块至少各有一个真实可编辑 CLI 案例和一个浏览器端到端案例。
- 后端离线测试、前端测试、生产构建、仓库校验全部通过。
- 外部服务在启用时有真实健康检查；不可用时明确阻断或按记录的策略降级。
- 所有运行都有持久、统一、可核账的 Token/耗时/配置/轨迹/输入输出 manifest。
- 所有任务、事件、引用和产物严格按用户隔离。
- 所有引用都有明确 CitationResolution；`exact_article` 打开唯一正确条文，其他状态进入对应站内受控交互且不伪装成精确跳转。兼容期 `can_jump=true` 只能由 `exact_article` 派生。
- 得理法律和案例经过统一归一化、来源对齐、证据分层和引用登记。
- 报告 Web/Markdown/PDF/DOCX 来自同一语义文档，引用与结构一致。
- 开发环境只有一套统一的“填充并运行”测试入口，生产环境不可见。
- 代码按稳定契约和领域边界拆分；新增模块不需要继续扩大巨型组件和重复配置。
- 每项结论都有命令、测试、Run ID、产物或代码位置作为证据。

---

## 20. 本轮方法参考与适用边界

以下资料用于校准候选方法，不用于替代当前仓库事实、AI4Law 金标测试或法律专家确认：

1. [FullCite：结构化内联引用与精确证据片段](https://arxiv.org/abs/2606.07130)：支持将引用推进到 claim—document—evidence span；论文同时说明精确 span 识别仍是模型薄弱环节，因此本文要求门禁和人工复核，不宣称模型绑定天然正确。
2. [PaperTrail：Claim–Evidence Provenance 界面](https://arxiv.org/abs/2602.21045v1)：支持细粒度证据关系和认知友好的分层呈现；其研究对象是学术问答，不直接证明法律报告的具体 UI 方案。
3. [SLOT：结构化输出转换](https://aclanthology.org/2025.emnlp-industry.32/) 与 [The Hidden Cost of Structure](https://aclanthology.org/2025.ranlp-1.124/)：共同说明 Schema 合规和内容保真必须分别测试，不能把复杂 JSON 或约束解码当作默认正确答案。
4. [文本与表格检索策略基准](https://arxiv.org/abs/2604.01733)：为 BM25/Hybrid/Reranker 实验提供候选，但其数据是金融问答，本文明确不将结果直接外推为法律检索架构。
5. [OpenTelemetry GenAI semantic conventions 独立仓库](https://github.com/open-telemetry/semantic-conventions-genai)：可用于 trace、metric、event 的技术字段映射；截至本次核验，原官方页面已迁移，该仓库没有正式 release 且 Schema URL 仍为 TODO，因此只通过版本化 adapter 接入。
