# AI4Law 各模块技术栈详解

> 版本：v2.0 | 更新日期：2026-03-24
> 关联文档：[架构设计](../architecture.md) | [原理与流程](../principle.md)

---

## 1 总体设计原则

### 1.1 共享底座 + 差异化重心

五个业务模块（路径诊断、安全评估、认证/标准合同、通用服务、文档智能审查）共享同一套技术底座，在此基础上各有不同的技术侧重点：

| 模块 | 技术重心 | 复杂度分布 |
|---|---|---|
| 合规路径诊断 | 前端规则引擎与状态机 | 前端 > 后端 > AI |
| 安全评估路径 | 后端异步编排 + RAG + 文档生成 | AI = 后端 > 前端 |
| 认证/标准合同 | 复用安全评估底座，独立 Schema/Prompt/模板 | AI = 后端 > 前端 |
| 通用服务 | 插件化文书生成框架 | 后端 > AI > 前端 |
| 文档智能审查 | 条款切分 + 条款级检索与审查编排 | AI > 后端 > 前端 |

### 1.2 共享底座层清单

以下公共层在所有模块间完全共享，各模块不应自行重复建设：

| 公共层 | 技术方案 | 架构文档章节 |
|---|---|---|
| 前端框架 | React 18 + Next.js 14 (App Router) + Ant Design 5 | architecture.md 3.1 |
| 表单引擎 | React Hook Form + Zod + JSON Schema 驱动 | architecture.md 3.4 |
| 状态管理 | Zustand | architecture.md 3.1 |
| 后端 API | Python 3.11 + FastAPI | architecture.md 4.1 |
| 异步任务 | Celery + Redis | architecture.md 4.1 |
| 文件服务 | FileService + MinIO / 腾讯云 COS | architecture.md 4.2 |
| 知识库检索 | Milvus/Qdrant + Elasticsearch + RAG 管线 | architecture.md 5.4 |
| LLM 适配 | LLMAdapter（腾讯元宝） + Prompt 模板系统 (Jinja2) | architecture.md 5.3 |
| 报告渲染 | python-docx + WeasyPrint | architecture.md 4.1 |
| 会话与权限 | SessionService + PostgreSQL + Redis | architecture.md 4.2 |
| 编排调度 | 腾讯元器工作流（Tier 1） | architecture.md 5.2 |
| 结构化中间态 | 统一 JSON Schema 约束 | architecture.md 6 |

### 1.3 共底座分配置层

以下能力共享基础设施，但各模块维护独立的配置文件：

| 配置项 | 说明 | 隔离方式 |
|---|---|---|
| Prompt 模板 | 每个模块/文书类型拥有独立的 Jinja2 模板 | `prompts/{module}/*.j2` |
| JSON Schema | 输入/输出 Schema 按模块和文书类型分别定义 | `schemas/{module}/*.json` |
| 检索过滤规则 | 法域、路径类型、文书类型的元数据过滤条件 | 按模块在 RAG 调用时传入 |
| 报告模板 | docx 模板文件按模块和文书类型独立维护 | `templates/{module}/*.docx` |
| 风险分级规则 | 各模块的 HIGH/MEDIUM/LOW 触发条件可有差异 | `config/{module}/risk_rules.yaml` |
| 表单 Schema | 前端表单结构按模块和文书类型独立定义 | `frontend/schemas/{module}-schema.json` |

---

## 2 合规路径诊断模块

> 对应架构：architecture.md 4.2 `DiagnosisService`
> 对应原理：principle.md 第3节

### 2.1 技术定位

路径诊断模块的核心目标是**快速、确定性地完成路径分流**。其决策逻辑由静态规则定义（是否为 CIIO、数据量级阈值、是否含敏感信息等），不依赖 LLM 推理。这一设计确保了三个关键特性：

- **确定性**：相同输入必然产出相同路径判定，无 LLM 随机性干扰
- **低延迟**：前端本地执行，无网络往返开销，响应时间 < 50ms
- **可解释性**：每一步判定逻辑透明，用户可回退并修改答案

### 2.2 前端层（核心）

| 技术 | 用途 |
|---|---|
| XState / 轻量自定义状态机 | 表达决策树，管理节点转移、回退、终态判定 |
| Zustand | 维护问答状态、当前节点、回退历史、结果缓存 |
| React Hook Form + Zod | 管理每一步的问题输入与校验 |
| `DecisionTreeStepper` 组件 | 步进式问答 UI，顶部进度条，卡片式选项 |

**决策树数据结构**：决策树以声明式 JSON 配置文件定义，包含节点（问题）、边（条件跳转）和叶节点（路径判定结论）。状态机负责根据用户选择在节点间转移，前端渲染器根据当前节点配置动态渲染问题和选项。

```
决策树执行流程

用户选择 → 状态机接收事件 → 查找目标节点 → 渲染新问题
                                   │
                            到达叶节点？
                            ├── 否 → 继续问答
                            └── 是 → 输出路径判定结论
                                     │
                                     ▼
                            调用后端生成诊断报告
```

### 2.3 后端层（轻量）

该模块后端仅承担三项职责：

| 职责 | 技术 | 说明 |
|---|---|---|
| 保存问答记录 | FastAPI + PostgreSQL | 存储最终诊断会话记录，供下游模块复用 |
| 生成诊断报告 | WeasyPrint / HTML 模板 | 将规则判断结果渲染为 PDF/HTML 报告 |
| 上下文传递 | Redis + SessionService | 将诊断结果（路径判定、企业特征）传递给安全评估或认证模块预填 |

### 2.4 AI 层（最轻量）

该模块仅在以下两个环节使用 LLM：

1. **诊断说明生成**：将结构化的规则判定结果转化为自然语言说明，并附加行动建议
2. **条文引用补充**：为诊断结论匹配法规条文（轻量 RAG 检索），生成引用说明

不需要完整的五步编排流程，不需要长链检索，不需要元器工作流。

### 2.5 工程目录

```
frontend/
  app/diagnosis/              # 诊断页面
  schemas/diagnosis-schema.json
  lib/decision-tree.ts        # 决策树数据结构 + 状态机逻辑
  lib/decision-tree-data.json # 决策树配置（节点/边/叶节点）

backend/
  api/diagnosis.py            # 诊断 API
  services/DiagnosisService/  # 诊断服务
  templates/diagnosis_report.html

ai_engine/
  prompts/diagnosis/          # 诊断说明生成 Prompt
```

### 2.6 设计约束

- **禁止**在问答过程中逐题调用 LLM。这会同时损失确定性、响应速度和可解释性
- 决策树变更只需修改配置文件，无需改动前端渲染代码
- 诊断报告为轻量级输出（1~2页），不需要 python-docx，HTML/PDF 即可

---

## 3 安全评估路径模块

> 对应架构：architecture.md 4.2 `AssessmentService`，5.2 元器工作流设计
> 对应原理：principle.md 第4节

### 3.1 技术定位

安全评估是系统中**最复杂的模块**，本质是一条完整的文档生产线：从材料收集到解析、检索、推理、校验、渲染，涉及多步异步编排。其复杂性主要体现在：

- 输入多样（表单 + 多类型附件）
- 流程长（五步生成流程，总耗时 30s~2min）
- 输出严格（官方报告模板格式要求）
- 引用要求高（每个章节必须引用法规原文）

### 3.2 前端层

重点不是规则引擎，而是**复杂表单管理与长时任务状态跟踪**。

| 技术 | 用途 |
|---|---|
| React Hook Form + Zod + JSON Schema | 多步表单校验、分段提交、条件字段展示 |
| Zustand | 保存当前步骤、草稿状态、上传文件元信息、生成进度 |
| localStorage + 服务端草稿 | 双重暂存机制，防止用户意外关闭页面丢失填写进度 |
| `FormWizard` 组件 | 多步表单渲染，左侧导航显示填写进度 |
| `FileUploader` 组件 | 分片上传、格式校验、进度展示 |
| `ReportPreview` 组件 | 分章节可折叠报告预览 + 引用气泡 |
| 轮询 / WebSocket | 报告生成进度实时展示（进度条 + 当前步骤说明） |

### 3.3 后端层（核心）

| 技术 | 用途 |
|---|---|
| FastAPI | 统一 API 入口 |
| Celery + Redis | 报告生成异步任务调度（耗时 30s~2min） |
| PostgreSQL | 存储表单数据、企业画像、任务元数据、报告状态 |
| MinIO / 腾讯云 COS | 存储用户上传材料和输出文档 |
| python-docx | 生成官方风格 docx 报告 |
| WeasyPrint | 预览版 PDF 导出 |

**任务状态流转**：

```
CREATED → PARSING → RETRIEVING → GENERATING → VALIDATING → RENDERING → COMPLETED
                                                                         │
                                                              任一步骤失败 → FAILED
                                                              （支持断点恢复）
```

### 3.4 AI / 编排层（完整管线）

该模块使用完整的两级编排体系（参见 architecture.md 5.1）：

| Tier | 承担者 | 职责 |
|---|---|---|
| Tier 1 | 腾讯元器 | 五步工作流编排（材料理解→法规检索→逐章生成→一致性校验→渲染输出） |
| Tier 2 | 自建 Python | 各工具插件的具体执行逻辑 |

**关键工具插件**：

| 工具插件 | 功能 |
|---|---|
| `file_parser` | 解析 PDF/Word → 纯文本 |
| `profile_extractor` | 从文本中抽取结构化企业画像（`CompanyProfile` JSON） |
| `rag_search` | 混合检索法规条文（向量 + 全文 + RRF + Reranker） |
| `chapter_generator` | 逐章生成报告内容（LLM + 引用链 + 风险分级） |
| `consistency_checker` | 跨章节一致性校验 |
| `report_renderer` | JSON 中间态 → docx 文件渲染 |

### 3.5 检索层

安全评估路径引用法规范围最广，检索配置如下：

| 参数 | 设置 |
|---|---|
| 查询类型路由 | 多数为"报告生成类"→ 语义检索权重调高 |
| 法域过滤 | 以中国大陆法规为主体，按境外接收方所在地补充对应法域 |
| 法规范围 | 《数据安全法》《个保法》《数据出境安全评估办法》《数据出境安全评估申报指南》等 |
| 检索粒度 | 条文级对象（`RegulationArticle`），保留层级路径和交叉引用 |
| 候选数量 | Top-30 候选 → Reranker 精排 → 最终 8~12 条送入 LLM |

### 3.6 中间态对象

该模块的核心中间态对象链路：

```
用户表单 + 上传文件
        │
        ▼
CompanyProfile（企业画像 JSON）
        │
        ▼
RegulationHit[]（法规命中记录）
        │
        ▼
ChapterContent[]（各章节内容 + 引用链 + 风险发现）
        │
        ▼
RiskFinding[]（汇总风险列表）
        │
        ▼
最终 docx 报告
```

每个中间态对象均由 JSON Schema 约束，支持自动校验、断点恢复和评测对比（参见 principle.md 第9节）。

### 3.7 工程目录

```
frontend/
  app/assessment/             # 评估页面（多步表单 + 报告预览）
  schemas/assessment-schema.json

backend/
  api/assessment.py           # 评估 API
  services/AssessmentService/ # 评估服务
  tasks/assessment_tasks.py   # Celery 异步任务

ai_engine/
  prompts/assessment/         # 各章节生成 Prompt
  schemas/assessment/         # CompanyProfile / ChapterContent 等 Schema
  templates/security_assessment/*.docx  # docx 模板
```

---

## 4 认证 / 标准合同路径模块

> 对应架构：architecture.md 4.2 `SCCService`
> 对应原理：principle.md 第4节

### 4.1 技术定位

该模块与安全评估模块共享技术底座（表单→解析→检索→生成→渲染），但在业务维度上存在明确差异，必须保持独立配置：

| 差异维度 | 安全评估路径 | 认证/标准合同路径 |
|---|---|---|
| 适用条件 | 触发安全评估的场景 | 未触发评估但需认证或标准合同的场景 |
| 输入字段重点 | 数据出境安全评估申报相关字段 | 认证自检清单 / 标准合同备案相关字段 |
| 引用法规集 | 《数据出境安全评估办法》《申报指南》为主 | 《个保法》第38条、《标准合同办法》、GB/T 46068 为主 |
| 输出文书 | 安全评估报告 | PIPIA 报告 / 认证自检清单 / 标准合同备案材料 |
| Prompt 策略 | 面向评估报告的结构与风险分析 | 面向 PIPIA 结构与认证要求 |

### 4.2 复用与隔离策略

**完全复用**（直接调用安全评估模块的共享组件）：

- `file_parser` -- 文件解析
- `profile_extractor` -- 企业画像抽取
- `rag_search` -- RAG 检索管线
- `consistency_checker` -- 一致性校验
- `report_renderer` -- docx 渲染引擎
- `FormWizard` / `FileUploader` / `ReportPreview` -- 前端组件

**必须独立**：

| 独立配置 | 说明 |
|---|---|
| 表单 Schema | `scc-schema.json` / `pipia-schema.json`，字段定义和校验规则与安全评估不同 |
| Prompt 模板 | `prompts/scc/*.j2`，PIPIA 报告的章节结构、语气、侧重点不同 |
| 输出 Schema | `scc/pipia_output.json`，PIPIA 报告的 JSON 结构与安全评估报告不同 |
| docx 模板 | `templates/scc/*.docx`，格式和章节编排不同 |
| 检索过滤 | 法规过滤标签偏向个保法、标准合同办法、GB/T 46068、认证规范 |

### 4.3 设计约束

- 不要将 `SCCService` 实现为 `AssessmentService` 的复制品。正确做法是：两者调用相同的底层工具插件，但各自维护独立的 Schema、Prompt 和模板配置
- 如果未来认证和标准合同的流程差异进一步扩大，可将 `SCCService` 拆分为 `CertificationService` 和 `StandardContractService`，但当前阶段统一管理以减少维护成本

### 4.4 工程目录

```
frontend/
  app/scc/                    # 认证/标准合同页面
  schemas/scc-schema.json
  schemas/pipia-schema.json

backend/
  api/scc.py                  # 认证/标准合同 API
  services/SCCService/        # 认证/标准合同服务
  tasks/scc_tasks.py          # Celery 异步任务

ai_engine/
  prompts/scc/                # PIPIA 各章节 / 认证自检 Prompt
  schemas/scc/                # PIPIA 输出 Schema
  templates/scc/*.docx        # PIPIA / 自检清单 docx 模板
```

---

## 5 通用服务模块

> 对应架构：architecture.md 4.2~4.3 `GeneralService` 插件化架构
> 对应原理：principle.md 第5节

### 5.1 技术定位

通用服务模块面临的核心挑战不是技术难度，而是**需求分散性**：需要生成 TIA、尽调报告、合规备忘录、整改建议清单等多种类型文书。采用插件化文书生成框架解决此问题。

### 5.2 插件化框架设计

所有文书类型共享一条生成管线，差异通过配置文件表达：

```
用户选择文书类型
        │
        ▼
DocumentTypeRegistry 查找注册配置
        │
        ├── 输入 Schema → 动态渲染表单
        ├── Prompt 模板 → 指导 LLM 生成
        ├── 输出 Schema → 校验 LLM 输出
        └── docx 模板  → 渲染最终文件
        │
        ▼
BaseDocumentGenerator 统一管线执行
（文件解析 → 法规检索 → LLM 推理 → 风险分级 → 报告渲染）
        │
        ▼
最终文书文件 (docx)
```

**当前注册的文书类型**（参见 architecture.md 4.3）：

| 文书类型 | Generator | 输入 Schema | Prompt 模板 | docx 模板 |
|---|---|---|---|---|
| 跨境传输风险评估 (TIA) | `TIAGenerator` | `tia_input.json` | `general/tia.*.j2` | `tia.docx` |
| 境外接收方尽调报告 | `DueDiligenceGenerator` | `dd_input.json` | `general/dd.*.j2` | `dd.docx` |
| 合规差距分析备忘录 | `MemoGenerator` | `memo_input.json` | `general/memo.*.j2` | `memo.docx` |
| 风险与整改建议清单 | `GapAnalysisGenerator` | `gap_input.json` | `general/gap.*.j2` | `gap.docx` |

### 5.3 前端层

不应为每种文书类型建设独立页面。应构建统一的 `GeneralServiceHub`：

1. 用户选择文书类型
2. 前端从 `DocumentTypeRegistry` 获取对应的输入 Schema
3. `FormWizard` 根据 Schema 动态渲染表单
4. 提交后路由到对应的 Generator

这一模式意味着：**新增文书类型无需前端代码修改，只需添加 Schema 文件**。

### 5.4 后端层

```
GeneralService
├── DocumentTypeRegistry    # 文书类型注册表（配置驱动）
├── BaseDocumentGenerator   # 生成管线基类
│   ├── parse_input()       # 校验输入 → 文件解析
│   ├── retrieve()          # RAG 检索法规
│   ├── generate()          # LLM 推理 → 结构化输出
│   ├── grade_risk()        # 风险分级
│   └── render()            # docx 渲染
├── TIAGenerator(BaseDocumentGenerator)
├── DueDiligenceGenerator(BaseDocumentGenerator)
├── MemoGenerator(BaseDocumentGenerator)
└── GapAnalysisGenerator(BaseDocumentGenerator)
```

每个 Generator 继承 `BaseDocumentGenerator`，必要时重写特定步骤（如 TIA 的风险矩阵评估逻辑），但大多数情况下仅通过配置差异化。

### 5.5 扩展新文书类型的标准流程

1. 定义输入 Schema（`schemas/general/new_type_input.json`）
2. 定义输出 Schema（`schemas/general/new_type_output.json`）
3. 编写 Prompt 模板（`prompts/general/new_type.*.j2`）
4. 准备 docx 模板（`templates/general/new_type.docx`）
5. 在 `DocumentTypeRegistry` 中注册
6. （可选）继承 `BaseDocumentGenerator` 实现自定义 Generator

步骤 1~5 不涉及核心代码修改，仅步骤 6 在需要定制逻辑时才涉及代码。

### 5.6 工程目录

```
frontend/
  app/general/                # 通用服务页面（统一 Hub）
  schemas/general-tia-schema.json
  schemas/general-dd-schema.json
  schemas/general-memo-schema.json
  schemas/general-gap-schema.json

backend/
  api/general.py              # 通用服务 API（统一入口 + type 路由）
  services/GeneralService/
    registry.py               # DocumentTypeRegistry
    base_generator.py         # BaseDocumentGenerator
    tia_generator.py
    dd_generator.py
    memo_generator.py
    gap_generator.py

ai_engine/
  prompts/general/            # 各文书类型 Prompt
  schemas/general/            # 各文书类型输入/输出 Schema
  templates/general/*.docx    # 各文书类型 docx 模板
```

---

## 6 文档智能审查模块

> 对应架构：architecture.md 4.2 `ReviewService`
> 对应原理：principle.md 第6节

### 6.1 技术定位

文档智能审查与前四个模块的技术模式有本质差异：

| 对比维度 | 前四个模块 | 文档智能审查 |
|---|---|---|
| 核心任务 | 从企业材料**生成**合规文书 | 对现有法律文件**逐条审查** |
| 输入形态 | 表单字段 + 附件 | 完整的合同/隐私政策文档 |
| AI 调用模式 | 按章节生成 | 按条款并行审查 |
| 检索目标 | 报告所需的法规依据 | 每条条款对应的合规要求 |
| 输出形态 | 结构化报告 | 条款级问题清单 + 修改建议 |

### 6.2 前端层

重点不是多步表单，而是**审查结果的定位展示与交互**：

| 组件 | 功能 |
|---|---|
| 文件上传区 | 上传合同/隐私政策文档 |
| 审查进度条 | 实时显示条款审查进度（已审查/总条款数） |
| 双栏对照视图 | 左栏：原文结构（可折叠条款树）；右栏：对应条款的审查意见 |
| 问题定位 | 点击右栏问题项 → 左栏高亮对应条款原文 |
| 风险筛选器 | 按 HIGH/MEDIUM/LOW 筛选显示问题项 |
| 导出按钮 | 导出 docx 格式审查报告 |

### 6.3 后端层 -- 审查管线

文档审查的后端采用四阶段管线架构（参见 architecture.md 4.2 `ReviewService`）：

```
上传文档
    │
    ▼
┌──────────────────────────────────────────────────┐
│ Stage 1: ClauseSegmenter（条款切分器）               │
│                                                    │
│ 输入：PDF/Word 原始文档                              │
│ 处理：按标题编号/段落结构/表格边界切分为独立条款单元     │
│ 输出：Clause[] （条款对象列表，含原文、位置、编号）      │
│                                                    │
│ 关键技术：PyMuPDF / pdfplumber / python-docx         │
│          正则 + 启发式规则识别条款边界                  │
│          保留页码/段落号用于结果定位回溯                │
└───────────────────────┬──────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────┐
│ Stage 2: ClauseClassifier（条款分类器）               │
│                                                    │
│ 输入：Clause[]                                     │
│ 处理：识别每条条款的类型                               │
│ 输出：ClassifiedClause[]（附加 clause_type 标签）     │
│                                                    │
│ 条款类型示例：                                       │
│   - 数据处理目的与范围                                │
│   - 同意机制                                        │
│   - 安全技术措施                                     │
│   - 数据主体权利行使                                  │
│   - 数据跨境传输                                     │
│   - 数据保留期限                                     │
│   - 违约责任                                        │
│                                                    │
│ 关键技术：轻量 LLM 分类 / 关键词匹配 + 规则兜底        │
└───────────────────────┬──────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────┐
│ Stage 3: ClauseReviewer（条款审查器 -- 可并行）       │
│                                                    │
│ 对每条条款独立执行：                                  │
│ 1. 根据 clause_type 选择检索过滤条件                  │
│ 2. RAG 检索该类条款对应的法规要求                      │
│ 3. LLM 对比条款内容与法规要求 → 生成审查意见           │
│ 4. 输出 ReviewIssue JSON（问题类型/修改建议/引用/等级）│
│                                                    │
│ 关键技术：条款级 RAG 检索（按 clause_type 过滤）       │
│          审查专用 Prompt 模板                        │
│          并行执行（多条款同时送审，提高吞吐）            │
└───────────────────────┬──────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────┐
│ Stage 4: ReviewAggregator（审查聚合器）               │
│                                                    │
│ 输入：ReviewIssue[]                                │
│ 处理：                                              │
│   - 合并重复/相似问题                                │
│   - 按风险等级排序（HIGH 优先）                       │
│   - 计算总体合规评级                                 │
│   - 生成优先整改建议排序                              │
│ 输出：AggregatedReview JSON                        │
│                                                    │
│ 关键技术：去重算法 + 风险加权排序                      │
└───────────────────────┬──────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────┐
│ Stage 5: ReviewReportRenderer（审查报告渲染器）        │
│                                                    │
│ 输入：AggregatedReview JSON                        │
│ 输出：docx 格式审查报告                              │
│ 报告结构：                                          │
│   - 文件概要                                        │
│   - 总体合规评级                                     │
│   - 条款级问题清单（含原文引用 + 法规依据 + 修改建议）   │
│   - 风险分析汇总                                     │
│   - 优先整改排序                                     │
└──────────────────────────────────────────────────┘
```

### 6.4 检索层的差异化配置

文档审查模块的 RAG 检索与报告生成模块有显著差异：

| 差异维度 | 报告生成模块 | 文档审查模块 |
|---|---|---|
| 检索触发 | 按报告章节触发，每章 1~2 次 | 按条款触发，每条款 1 次，总计可达数十次 |
| 查询构造 | 基于企业画像 + 章节要求 | 基于条款原文 + 条款类型 |
| 过滤条件 | 按法域 + 路径类型过滤 | 按法域 + 条款类型过滤 |
| 性能要求 | 单次流程，总耗时可接受 1~2min | 并行审查，单条款检索需 < 3s |
| 缓存策略 | 一般不缓存 | 同类型条款的检索结果可缓存复用 |

### 6.5 中间态对象

该模块的核心中间态：

| 中间态 | 说明 |
|---|---|
| `Clause` | 切分后的条款单元：原文、位置（页码/段落号）、编号 |
| `ClassifiedClause` | 分类后的条款：附加 `clause_type` 标签 |
| `ReviewIssue` | 单条审查意见：条款定位、问题类型、严重性、法规依据、修改建议 |
| `AggregatedReview` | 汇总审查结果：总体评级、问题列表（已排序）、整改优先级 |

### 6.6 性能优化要点

| 优化策略 | 说明 |
|---|---|
| 条款并行审查 | 多个条款同时送入 Stage 3，利用 Celery 或 asyncio 并发执行 |
| 同类缓存 | 相同 `clause_type` 的法规检索结果可在同一文档内缓存复用 |
| 批量分类 | Stage 2 可将多条条款合并为一次 LLM 调用进行批量分类 |
| 渐进返回 | 前端通过 WebSocket 逐条接收已完成的审查结果，无需等待全部完成 |

### 6.7 工程目录

```
frontend/
  app/review/                 # 审查页面（双栏对照视图）
  schemas/review-schema.json

backend/
  api/review.py               # 审查 API
  services/ReviewService/
    clause_segmenter.py       # 条款切分器
    clause_classifier.py      # 条款分类器
    clause_reviewer.py        # 条款审查器
    review_aggregator.py      # 审查聚合器
    review_report_renderer.py # 审查报告渲染器
  tasks/review_tasks.py       # Celery 异步任务

ai_engine/
  prompts/review/             # 审查 Prompt（分类 + 审查）
  schemas/review/             # ReviewIssue / AggregatedReview Schema
  templates/review/*.docx     # 审查报告 docx 模板
```

---

## 7 模块间协作与数据流

### 7.1 模块间上下文传递

```
路径诊断 ──DiagnosisResult──→ 安全评估 / 认证标准合同
   │                              │
   │  诊断结果自动预填：            │  可复用的企业基础信息：
   │  - 路径判定                   │  - CompanyProfile
   │  - 企业基本特征               │  - 上传文件列表
   │  - 数据规模                   │
   │                              ▼
   │                         通用服务
   │                         （可基于已有 CompanyProfile
   │                           快速生成 TIA/尽调等文书）
```

传递机制：`SessionService` 通过 Redis 缓存 `DiagnosisResult` 和 `CompanyProfile`，下游模块在创建任务时自动查询并预填。

### 7.2 全局工程目录总览

```
frontend/
  app/
    diagnosis/                # 路径诊断
    assessment/               # 安全评估
    scc/                      # 认证/标准合同
    general/                  # 通用服务
    review/                   # 文档审查
    report/[id]/              # 报告预览
  components/
    FormWizard.tsx            # 多步表单渲染引擎
    FileUploader.tsx          # 文件上传组件
    ReportPreview.tsx         # 报告预览组件
    CitationBubble.tsx        # 引用气泡组件
    RiskBadge.tsx             # 风险等级标签
    DecisionTreeStepper.tsx   # 决策树步进器
  schemas/                    # 各模块表单 Schema
  lib/
    decision-tree.ts          # 决策树引擎
    decision-tree-data.json   # 决策树配置

backend/
  api/
    diagnosis.py
    assessment.py
    scc.py
    general.py
    review.py
  services/
    DiagnosisService/
    AssessmentService/
    SCCService/
    GeneralService/           # 含 registry + base_generator + 各 Generator
    ReviewService/            # 含 segmenter + classifier + reviewer + aggregator + renderer
    FileService/
    SessionService/
  tasks/
    assessment_tasks.py
    scc_tasks.py
    general_tasks.py
    review_tasks.py

ai_engine/
  llm_adapter.py              # LLM 适配层
  rag/                        # RAG 管线（共享）
    query_router.py
    query_rewriter.py
    hybrid_search.py
    reranker.py
    context_assembler.py
    citation_tagger.py
    audit_logger.py
  prompts/
    diagnosis/
    assessment/
    scc/
    general/
    review/
  schemas/                    # 各模块 JSON Schema
    diagnosis/
    assessment/
    scc/
    general/
    review/
  citation/                   # 引用链生成器
  risk_grader/                # 风险分级 + 门控
  templates/                  # docx 模板
    security_assessment/
    scc/
    general/
    review/

evaluation/                   # 评测框架
  golden_sets/
  metrics/
  runners/
```

---

> 本文档定义了各模块在共享底座上的差异化技术安排。架构层面的全局设计请参阅 [architecture.md](../architecture.md)，系统原理与流程详解请参阅 [principle.md](../principle.md)。
