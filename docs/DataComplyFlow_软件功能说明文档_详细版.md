# DataComplyFlow（数规通）软件功能说明文档

> 文档版本：V2.0
> 编制日期：2026-08-01
> 适用范围：DataComplyFlow 仓库 `new` 分支（Commit `7b6ba12`），覆盖后端 FastAPI 应用、前端 React/Vite 应用、CLI 测试框架、评测体系及完整运行配置
> 文档性质：面向软件工程交付的功能说明，依据当前代码与可重复测试结果编写
> 事实优先级：当前可运行代码和测试结果 → 当前配置与调用链 → 现行规范 → 有日期事实快照 → 历史材料
 

## 1. 系统概述

> 本章回答：**这个项目是做什么的**

### 1.1 项目定位

DataComplyFlow（数规通）是一套面向企业数据合规与跨境数据治理的 **Legal Agentic RAG 工作台**。系统围绕中国、欧盟、美国三大司法辖区的数据合规场景，构建了覆盖"合规路径诊断 → 安全评估报告生成 → 合同条款智能审查 → 影响评估"的完整工具链。

平台采用 **规则引擎 + 大语言模型 + 工作流编排** 的组合架构。规则引擎承担确定性法律判断（如"是否触发安全评估申报义务"），大模型承担语义理解与文书生成（如"起草评估报告正文"），两者之间通过结构化的上下文组装和引用注册表衔接。这样设计的原因是：法律合规场景下，**结论必须有依据、依据必须可追溯、不确定时必须告知用户**——这些要求纯大模型无法满足。

系统面向企业法务、合规咨询顾问和法律学习者。用户登录后进入任务空间，选择法域和任务类型，填写业务信息，系统自动完成法规检索、路径判断、报告生成，所有结论均标注法律依据并可点击溯源。

### 1.2 技术栈概览

| 层级 | 技术选型 | 说明 |
|---|---|---|
| 后端框架 | FastAPI (Python 3.11) | ASGI 应用，`backend/main:app` 为唯一入口 |
| 前端框架 | React 18 + Vite + TypeScript | SPA 架构，`frontend/src/main.tsx` 为入口 |
| 数据库 | SQLite（开发阶段） | 通过 SQLAlchemy ORM 访问，自动建表 |
| 包管理 | uv (Python) / npm (前端) | 依赖锁定于 `uv.lock` 与 `package-lock.json` |
| 大语言模型 | OpenAI-compatible Provider | 通过统一 Provider Registry 管理，支持腾讯混元等多供应商，含健康探测与自动回退 |
| 法规检索 | 本地多索引 RAG + 得理 API | SHA-256 确定性哈希向量 + 关键词混合检索，RRF 融合排序，15 个逻辑索引覆盖 3 法域 × 5 资源类型 |
| 法律知识库 | 69 个来源、1,672 条条文 | 位于 `resources/legal/`，含完整快照与索引 |
| 报告渲染 | Markdown → HTML / DOCX / PDF | 共享渲染管线，位于 `backend/common/render/` |
| 测试框架 | pytest 528 项 (后端) / Vitest 48 项 (前端) | 含 CLI Smoke 全模块离线测试与 Benchmark 评测体系 |
| 版本控制 | Git | 仓库根目录 `.git`，分支 `new` |

### 1.3 系统部署与运行

```bash
# 后端启动
uv run uvicorn backend.main:app --reload --port 8000

# 前端启动
cd frontend && npm ci && npm run dev

# 全量测试
uv run --frozen pytest -q                          # 后端：528 passed, 1 warning
npm --prefix frontend test -- --run                 # 前端：15 files, 48 tests passed
npm --prefix frontend run build                     # 生产构建：342 modules
python -m backend.tests.harness.runner all --no-llm # 11模块CLI Smoke：15 PASS
```

---

## 2. 系统总体架构

> 本章回答：**系统是怎么组织的**

### 2.1 架构分层

```text
┌─────────────────────────────────────────────────┐
│              前端层 (React/Vite SPA)              │
│  首页  │  任务空间  │  工作台  │  知识库中心  │  设置  │
├─────────────────────────────────────────────────┤
│              API 网关层 (FastAPI)                  │
│     /api/v0 (历史兼容)  │  /api/v1 (主入口, 93条)  │
├─────────────────────────────────────────────────┤
│              业务领域层 (按司法辖区)                │
│     CN 中国域 (4模块)  │  EU 欧盟域 (4模块)         │
│     路径诊断/安全评估    │  SCC审查/BCR审查          │
│     文档审查/PIPIA      │  DPIA/TIA                │
│                         │                          │
│     US 美国域 (3模块)                              │
│     EO 14117 / EO 14117流程审查 / CPRA合规         │
├─────────────────────────────────────────────────┤
│               公共能力层                           │
│  LLM Provider │ RAG检索 │ 引用管理 │ 报告渲染        │
│  事件追踪 │ 运行账本 │ 任务调度 │ 产物管理          │
├─────────────────────────────────────────────────┤
│               基础设施层                           │
│  配置管理 │ 数据库 │ 文件存储 │ 密钥管理 │ 健康检查    │
└─────────────────────────────────────────────────┘
```

系统从上到下分五层。前端层提供四个主要页面区域（首页、任务空间、工作台、知识库中心）和一个设置页。API 网关层保留 v0 兼容路由（文件上传、历史任务网关），主线功能全部通过 v1 路由（101 条显式路由，含 `/health`、v0 7 条、v1 93 条）。业务领域层按 CN/EU/US 三个司法辖区组织 11 个模块，每个模块是一个独立的 FastAPI 子路由 + 前端表单 + 后端领域包。公共能力层为所有模块提供 LLM 调用、RAG 检索、引用管理、报告渲染、事件追踪和产物管理，模块通过依赖注入获取这些能力而不自行创建客户端。基础设施层管理配置加载、数据库连接、文件存储路径和密钥安全。

### 2.2 仓库目录结构

| 目录 | 职责 | 说明 |
|---|---|---|
| `backend/` | FastAPI 应用与业务实现 | 分 `api/`（路由）、`common/`（公共能力）、`domains/`（法域业务）、`core/`（配置） |
| `backend/api/v1/` | v1 主 API 路由 | 93 条路由，含诊断、评估、审查、PIPIA、SCC、BCR、DPIA、TIA、EO14117、CPRA 等 |
| `backend/api/v0/` | v0 兼容网关 | 7 条路由，承担文件上传和历史任务兼容 |
| `backend/domains/cn/` | 中国法域业务 | 4 个模块：transfer_diagnosis、security_assessment、document_review、pipia |
| `backend/domains/eu/` | 欧盟法域业务 | 4 个模块：scc_review、bcr_review、dpia、tia |
| `backend/domains/us/` | 美国法域业务 | 3 个模块：eo14117、eo14117_flow_review、cpra |
| `backend/common/` | 公共能力 | LLM Provider、RAG 检索、引用(Citation)、报告渲染、事件追踪、工作流、运行时刷新 |
| `backend/core/` | 核心配置 | 应用工厂、Settings、运行时配置管理 |
| `backend/integrations/` | 第三方集成 | 得理法律 API 适配器 |
| `frontend/src/` | React 前端源码 | `pages/`（页面）、`components/`（组件）、`api/`（API 客户端）、`lib/`（状态管理） |
| `benchmarks/` | 评测体系 | 数据集、评测 Runner、Product Smoke 案例、规模化 RAG 评测 |
| `resources/` | 静态资源 | `legal/`（法规条文与知识库）、`rules/`（静态规则）、`templates/`（报告模板） |
| `config/` | 跨语言静态配置 | `module_registry.json`——模块身份唯一权威源，前后端共用 |
| `scripts/` | 仓库级脚本 | 索引构建、知识库生成、合规性检查、评测执行 |
| `docs/` | 文档中心 | `standards/`（现行规范）、`handoff/`（事实快照）、`archive/`（历史材料） |
| `storage/` | 本地运行状态 | SQLite 数据库、用户上传文件、会话数据 |
| `outputs/` | 运行产物 | 按 `{module}/{task}/` 组织，含 Markdown/PDF/DOCX 报告、CitationMap、Trace 事件 |

---

## 3. 模块功能说明

> 本章回答：**系统有哪些功能模块，各自能做什么**

系统共注册 11 个业务模块，按司法辖区（CN/EU/US）划分为三组。模块身份以 `config/module_registry.json` 为唯一权威源——API 路由、前端任务模板、CLI 案例和评测入口均以此为绑定键。模块的业务功能可分为三种类型：**路径判断类**（一个模块，诊断应该走哪种合规路径）、**审阅类**（审查已有合同/SCC/BCR 是否符合法规）、**草案生成类**（基于用户输入的事实信息，生成安全评估、DPIA、TIA、PIPIA 等合规报告）。

### 3.1 中国法域（CN）

#### 3.1.1 合规路径诊断（cn.transfer_diagnosis）

| 属性 | 说明 |
|---|---|
| 模块ID | `cn.transfer_diagnosis` |
| 前端键 | `diagnosis` |
| API前缀 | `/api/v1/diagnosis` |
| 生命周期 | active |
| 功能类型 | 路径判断 |

**功能描述：**

这是整个中国数据出境合规链路的入口模块——"先判断走哪条路"。用户输入企业类型（是否为 CIIO）、数据类别（是否含个人信息/重要数据）、数据量级和接收方信息后，系统基于代码规则引擎进行结构化判断。规则引擎不调用大模型，而是加载静态规则文件进行确定性 `true/false` 判断：是否触发安全评估？是否可以走标准合同/认证路径？是否属于豁免情形？

规则引擎输出结构化结论（路径类型、命中规则 ID 列表、缺失事实提示），再由 RAG 检索补充对应法规条文作为依据，最终以模板化报告输出。当前支持三态输入：结构化字段填表、自然语言描述、混合模式。

**核心能力：**
- 规则引擎驱动的确定性路径判断（豁免短路、重要数据、CIIO、敏感个人信息阈值）
- 三态输入采集（结构化字段 / 自然语言 / 混合）
- RAG 法规检索补充法律依据
- `source_id` 匹配——每条规则绑定的法规在知识库中能否找到原文
- 缺失事实识别与追问建议（如"重要数据状态未知"）
- 路径结论结构化输出 + 报告渲染

#### 3.1.2 安全评估（cn.security_assessment）

| 属性 | 说明 |
|---|---|
| 模块ID | `cn.security_assessment` |
| 前端键 | `assessment` |
| API前缀 | `/api/v1/assessment` |
| 生命周期 | active |
| 功能类型 | 草案生成 |

**功能描述：**

面向诊断结论为"需要进行安全评估"的企业用户。模块引导用户填写企业画像（数据处理者信息、境外接收方、数据字段、安全保障措施等），系统自动构建事实包、组织证据链，并按安全评估申报指南的结构逐章节生成报告草案。

该模块是系统中 AI 调用链路最完整的模块之一：用户事实经结构化处理 → RAG 检索获取法规依据 → 构建 GenerationContextPack（规则结论 + 检索结果 + 引用允许列表）→ LLM 按章节模板生成正文 → 引用规范化 → 生成 Markdown/HTML/DOCX/PDF 四种格式报告。对 HIGH/BLOCKER 级别风险额外触发得理法律 API 进行增强检索。

**核心能力：**
- 分步表单采集企业画像和数据处理事实
- 合规差距项（gap_items）生成与风险等级（HIGH/MEDIUM/LOW/BLOCKER）分级
- 本地多索引 RAG 检索 + 条件触发得理 API 增强
- GenerationContextPack 上下文组装（规则结论 + 法规条文 + 引用允许列表）
- LLM 辅助章节正文生成（Prompt 约束：只能用允许列表中的 citation_id、不确定内容标注"待确认"）
- 四种格式报告输出（Markdown / HTML / DOCX / PDF）
- 全链路 Trace 记录（LLM 调用次数、Token、耗时、Retrieval 命中）

#### 3.1.3 文档专项智能审查（cn.document_review）

| 属性 | 说明 |
|---|---|
| 模块ID | `cn.document_review` |
| 前端键 | `review` |
| API前缀 | `/api/v1/review` |
| 生命周期 | active |
| 功能类型 | 审阅 |

**功能描述：**

面向已有合规文档的专项审查。用户上传 PDF/DOCX/MD 文件后，系统自动解析文本、按条款结构切分、逐条与法规和标准条款模板匹配审查，定位不合规点和风险项，生成逐条修改建议和批注版文件。该模块区别于通用合同审查——审查规则聚焦数据合规专项（如数据出境条款、个人信息保护条款、安全义务条款等），检索的知识库也限定在对应法域的法规范围。

**核心能力：**
- 文件上传与解析（支持 PDF / DOCX / MD 格式）
- 条款自动切分与分类（按合同结构识别 + 按审查维度归类）
- 法规依据检索（限定法域的 RAG 检索）
- 条款逐条审查 + 风险等级标注
- 修改建议生成（保留原文对照）
- 双输出：审查报告 + 批注修订版 DOCX
- 行内引用与来源预览

#### 3.1.4 个人信息保护影响评估（cn.pipia）

| 属性 | 说明 |
|---|---|
| 模块ID | `cn.pipia` |
| 前端键 | `pipia` |
| API前缀 | `/api/v1/pipia` |
| 生命周期 | active |
| 功能类型 | 草案生成 |

**功能描述：**

依据《个人信息保护法》第 55-56 条要求，辅助企业完成个人信息保护影响评估（PIPIA）。用户通过表单输入个人信息的处理目的、处理方式、信息类型、安全措施等信息，系统进行合规判断和风险评估，按监管要求模板生成 PIPIA 报告。同时承担标准合同备案相关材料的处理能力——即"认证/标准合同路径"下需要的备案文书也可通过此模块生成。

**核心能力：**
- 分步表单采集处理场景信息
- 处理目的/方式/信息类型的合规判断
- RAG 法规检索（《个人信息保护法》及相关配套规定）
- 风险评估与整改建议生成
- 模板化报告渲染输出
- 标准合同备案材料支持
- 中间产物 JSON + Trace 保存

### 3.2 欧盟法域（EU）

#### 3.2.1 标准合同条款审查（eu.scc_review）

| 属性 | 说明 |
|---|---|
| 模块ID | `eu.scc_review` |
| 前端键 | `eu_scc` |
| API前缀 | `/api/v1/eu_scc` |
| 生命周期 | active |
| 功能类型 | 审阅 |

**功能描述：**

对涉及欧盟数据跨境传输的标准合同条款（Standard Contractual Clauses, SCC）进行逐条合规审查。系统根据 GDPR 第 46 条要求和欧盟委员会最新 SCC 模板（2021 版），逐条分析合同条款是否符合 GDPR 数据转移要求，识别缺失条款、不充分的保障措施和潜在法律风险，生成逐条修改建议。

**核心能力：**
- SCC 文件上传与结构识别（条款号自动匹配模板）
- GDPR 合规分类（数据处理者义务、数据主体权利、监管合规等维度）
- RAG 法规检索（GDPR 正文 + EDPB 指南）
- 条款逐条审查 + 风险等级（含替代条款推荐）
- 审查报告 + 批注修订版 DOCX 双输出

#### 3.2.2 约束性公司规则审查（eu.bcr_review）

| 属性 | 说明 |
|---|---|
| 模块ID | `eu.bcr_review` |
| 前端键 | `bcr` |
| API前缀 | `/api/v1/bcr` |
| 生命周期 | active |
| 功能类型 | 审阅 |

**功能描述：**

对跨国企业集团的约束性公司规则（Binding Corporate Rules, BCR）进行合规审查。BCR 是 GDPR 第 47 条认可的跨境数据转移合法工具之一，要求企业内部规则满足 EDPB 的 WP256/257 各项要求。系统自动识别 BCR 文件结构，对照 EDPB 要求逐要素检查，生成差距分析报告。

**核心能力：**
- BCR 文件解析与 EDPB 要求要素映射
- 差距分析（已满足/部分满足/缺失）
- 法规依据检索（GDPR + EDPB BCR 建议文件）
- 审查报告生成

#### 3.2.3 数据保护影响评估（eu.dpia）

| 属性 | 说明 |
|---|---|
| 模块ID | `eu.dpia` |
| 前端键 | `dpia` |
| API前缀 | `/api/v1/dpia` |
| 生命周期 | active |
| 功能类型 | 草案生成 |

**功能描述：**

依据 GDPR 第 35 条，辅助企业完成数据保护影响评估（Data Protection Impact Assessment, DPIA）。用户描述数据处理活动后，系统自动判断是否属于"可能对自然人权利和自由造成高风险"的处理场景（如大规模处理特殊类别数据、自动化决策、系统性监控等），对高风险场景强制进入完整评估流程，生成结构化 DPIA 报告。

**核心能力：**
- 数据处理活动描述输入
- 高风险处理场景自动识别（基于 EDPB 高风险清单）
- 必要性和比例性评估
- 风险识别（原风险 + 残余风险）与缓解措施建议
- 结构化 DPIA 报告渲染

#### 3.2.4 传输影响评估（eu.tia）

| 属性 | 说明 |
|---|---|
| 模块ID | `eu.tia` |
| 前端键 | `tia` |
| API前缀 | `/api/v1/tia` |
| 生命周期 | active |
| 功能类型 | 草案生成 |

**功能描述：**

依据 EDPB"Schrems II"后发布的建议（Recommendations 01/2020），辅助完成数据跨境传输影响评估（Transfer Impact Assessment, TIA）。评估第三国的法律环境（政府访问权限、数据主体救济机制等）是否对转移后的数据保护构成实质性损害，判断是否需要补充措施（如加密、假名化）以及这些措施是否足以弥补保护差距。

**核心能力：**
- 第三国法律环境评估（政府访问、监管框架、救济机制）
- 数据传输风险等级评估
- 补充措施识别与有效性判断
- TIA 报告生成

### 3.3 美国法域（US）

#### 3.3.1 EO 14117 风险评估（us.eo_14117）

| 属性 | 说明 |
|---|---|
| 模块ID | `us.eo_14117` |
| 前端键 | `us_14117` |
| API前缀 | `/api/v1/us_14117` |
| 生命周期 | active |
| 功能类型 | 路径判断 + 风险评估 |

**功能描述：**

依据美国第 14117 号行政令"防止受关注国家获取美国人大量敏感个人数据和美国政府相关数据"（2024 年 2 月），进行数据交易风险评估。系统内置 EO 14117 规则引擎（1,302 行规则代码），判断交易是否涉及六类敏感个人数据（基因组、生物识别、个人健康、地理位置、金融、个人标识符）或政府相关数据，以及是否涉及受关注国家/主体、数据经纪、云服务、投资/雇佣/供应商关系等触发条件。

**核心能力：**
- EO 14117 规则引擎（1,302 行代码，覆盖合规判断的全部触发条件）
- 六类敏感数据类型自动识别
- 受限主体/国家匹配
- 风险等级评估（禁止交易/受限交易/允许交易）
- 合规建议输出

#### 3.3.2 EO 14117 流程审查（us.eo_14117_flow_review）

| 属性 | 说明 |
|---|---|
| 模块ID | `us.eo_14117_flow_review` |
| 前端键 | `cn_flow`（历史兼容键） |
| API前缀 | `/api/v1/cn-flow` |
| 生命周期 | legacy-compatible |
| 功能类型 | 数据流审查 |

**功能描述：**

在 EO 14117 框架下对数据流进行系统性审查。与 `us.eo_14117` 不同，该模块侧重"数据流分析"而非"单点交易风险评估"——关注数据从收集到跨境的完整流转路径中的每个节点。注意：前端键 `cn_flow` 是历史遗迹，不影响其美国法域的实质归属；独立的中国 SCC 审查入口已退役，标准合同备案材料由 `cn.pipia` 处理。

**核心能力：**
- 数据流描述采集（流转节点、数据类型、处理操作等）
- EO 14117 规则匹配与节点级触发判断
- 数据流安全审查
- 报告生成

#### 3.3.3 CPRA 合规评估（us.cpra）

| 属性 | 说明 |
|---|---|
| 模块ID | `us.cpra` |
| 前端键 | `cpra` |
| API前缀 | `/api/v1/cpra` |
| 生命周期 | active |
| 功能类型 | 填表清单 |

**功能描述：**

依据加州隐私权法（California Privacy Rights Act, CPRA），对企业数据处理实践进行合规差距评估。用户通过问卷形式描述企业的数据实践（收集的数据类别、处理目的、共享情况、消费者权利响应机制等），系统自动对照 CPRA 义务条款逐项检查，生成差距清单（已合规/部分合规/不合规）和整改优先级建议。支持 xlsx 表格 + 摘要报告双输出。

**核心能力：**
- 用户问卷/描述输入（覆盖 CPRA 主要义务域）
- CPRA 义务项自动映射（12 类义务域）
- 差距项（gap_items）生成与优先级排序
- 法规依据绑定（CPRA 原文条款）
- xlsx 表格 + 摘要报告双格式输出
- 行内引用与来源预览

---

## 4. 公共能力与基础设施

> 本章回答：**支撑所有模块运行的底层机制是什么**

### 4.1 LLM Provider 管理

系统通过统一的 Provider Registry 管理大语言模型供应商。核心设计目标是：①支持多供应商（腾讯混元、OpenAI-compatible 等）热切换；②每次运行使用不可变的 ProviderSnapshot，确保运行中配置不被意外更改；③密钥永远不进日志、不进产物；④无健康 LLM 时生产环境直接阻断而非静默失败。

**核心机制：**

- **Provider Registry**：从 `.env` 和运行时配置文件（`storage/runtime_settings.json`）读取候选 Provider 配置（Base URL、API Key、模型名），校验完整性和兼容性。支持新增、删除、启用、选中多个 Provider。

- **健康探测（Health Probe）**：保存配置前执行两步探测——先调模型列表接口确认 Base URL 和鉴权有效，再发起一次最小生成请求（如"回复 OK"）确认模型可用且额度充足。能稳定区分六类错误："模型不存在"、"余额不足"、"鉴权失败"、"限流"、"超时"、"网络错误"。探测结果缓存 15 分钟。

- **ProviderSnapshot（不可变快照）**：每个异步任务提交时，从当前 Provider 复制一份 frozen dataclass 快照（provider_id、model_id、Base URL SHA-256 指纹、enabled 状态、私密 Key），任务线程通过 ContextVar 绑定该快照。即使设置页热更新了 Provider 配置，运行中的旧任务不受影响。

- **生产门禁**：`APP_ENV=production` 时，11 个模块的 LLM 创建/调用/重试入口统一检查 Provider 健康快照——不存在、未探测、超过 15 分钟或配置指纹变更时，任务提交直接返回 `503 / LLM_PROVIDER_UNHEALTHY`，而非到运行时才失败。

- **密钥安全**：API Key 仅从 `.env` 读取，不出现在任何日志、运行产物、Trace 事件和 API 响应中。ProviderSnapshot.sanitized() 方法在写入 RunManifest 前删除 Key 字段并替换为 SHA-256 指纹。

```text
配置保存 → 模型列表探测(URL+鉴权有效性)
          → 最小生成探测(模型可用性+额度)
          → 缓存健康结果(15分钟有效)
          → [生产环境] 任务提交前校验健康快照 → 通过则创建任务 → 任务复制ProviderSnapshot
          → [开发环境/CLI --no-llm] 跳过门禁
```

### 4.2 RAG 法规检索

系统构建了多层级的本地检索增强生成体系。三个法域、五类资源（法律法规、工作流知识、标准条款、报告模板、测试案例）各自建立独立索引，共 15 个逻辑索引，检索时先确定法域和资源类型范围再查询，避免跨法域污染。

**核心机制：**

- **确定性哈希向量化**：使用 SHA-256 固定映射替代 Python 内置 `hash()`（后者在每次进程启动时随机化种子，导致同一文本在不同进程中产生不同向量）。索引文件记录 `sha256-v1` 版本号和维度，不兼容时自动重建索引。

- **混合检索 + RRF 融合**：同时执行向量相似度检索和关键词检索（BM25 风格），使用 Reciprocal Rank Fusion 合并两个排序列表。当前 Vector 和 Hybrid 在规模化评测中结果完全相同——这是已知待修复问题，初步判断与调用链中 Hybrid 模式未实际启用不同策略有关。

- **多索引 Orchestrator**：中国法域优先进入多索引检索器（legal + workflow + standard_clause + template + testcase 并行查询），已有结果时提前返回。检索失败时依次降级：多索引 → 单索引（仅 legal）→ 兼容回退。

- **UsagePolicyFilter**：限制不同效力层级的材料能否进入最终报告。`effective`（现行法）可用于支撑确定性结论，`reference`（参考资料）只能作为背景说明。

- **得理 API 增强**：系统集成得理法律 API 作为外部证据发现层。不是每次检索都并行调用——只有满足条件触发（本地检索置信度不足 / HIGH-BLOCKER 级风险 / 用户要求最新法规或案例 / 本地版本可能过期）时才调用。得理返回结果经过来源对齐、效力校验和稳定 ID 映射后才能进入引用注册表。当前适配器已知限制：仅保留标题、来源、摘要，丢弃了得理的稳定 ID、条号、效力状态和原文定位——因此当前不能直接承担可信引用入库。

```text
用户查询
  → QueryPlan（确定法域、资源类型、检索策略）
  → 分词 + SHA-256 哈希 → 384维向量
  → 向量相似度 + 关键词并行检索
  → RRF 合并排序
  → UsagePolicyFilter 过滤
  → 置信度判断
    ├─ 充分 → 直接返回
    └─ 不足/HIGH风险 → [条件触发] 得理API
       → 来源对齐 → 入库候选
  → 最终结果列表
```

### 4.3 引用管理与 CitationMap

系统建立了贯穿全模块的结构化引用注册体系。核心设计思路：**大模型只允许使用预先批准的 citation_id 列表，不得自行编造引用。** 所有引用在后处理阶段经知识库校验——能在 1,602 个唯一定位中精确匹配的标记为 `exact_article`（可精确跳转），来源存在但条号缺失的标记为 `source_overview`（仅展示法规概览），来自得理等外部来源的标记为 `external_verified`，完全无法解析的标记为 `unresolved`（不提供跳转）。

**引用生成与校验链路：**

```text
模块生成报告（LLM使用[cite:CIT-xxx]标记）
  → 后处理规范化（CitationRegistry 校验 citation_id 有效性）
  → CitationMap JSON 持久化（outputs/{module}/{task}/citation_map.json）
  → Citations API 返回前端
  → CitationMarkdownRenderer 渲染为可点击角标
  → 用户点击 → 站内受控交互
    ├─ exact_article → 打开具体条文抽屉，展示前后条文
    ├─ source_overview → 打开法规概览页，提示"无法定位具体条文"
    ├─ external_verified → 打开外部来源说明卡
    └─ unresolved → 显示"无法匹配依据"，不提供跳转
```

**CitationResolution 类型：**

| 解析类型 | 含义 | 前端行为 |
|---|---|---|
| `exact_article` | 来源 ID 和条号在本地知识库中唯一匹配 | 打开条文抽屉，精确到具体条款，可前后翻阅 |
| `source_overview` | 来源存在但缺少条号或 34 组重复定位键冲突 | 打开法规概览页面，标注"无法精确定位具体条文" |
| `external_verified` | 来自得理等外部 API 的引用，未映射到本地知识库 | 打开外部来源卡片，标注来源 API 和检索时间 |
| `unresolved` | 来源未知、冲突或校验失败 | 显示"无法匹配依据"，灰显，不提供跳转 |

当前知识库有 69 个来源、1,602 个唯一定位（34 组重复定位键已明确拒绝精确跳转），历史 CitationMap 累计 650 份文件、16,681 条引用项。

### 4.4 报告渲染

系统具备统一的报告渲染管线，核心思路是**单一语义源多格式输出**——模块产出一份 ReportDocument（结构化语义文档），由共享渲染器负责生成 Markdown、HTML、DOCX、PDF 四种格式。四种格式的内容（标题层级、表格结构、引用标记、段落划分）必须一致——因为来自同一份语义源，不是各自独立生成。

```text
ReportDocument（结构化语义文档，由模块生成器产出）
  ├─ metadata：标题、法域、日期、模块ID
  ├─ sections[]：章节结构
  │    └─ blocks[]：heading / paragraph / table / cited_claim
  ├─ claims[]：主张ID、类型(法律规则/事实/风险判断/建议/过渡)、证据引用、支持状态
  ├─ citations[]：引用注册表(citation_id↔source_id↔article↔snippet↔resolution)
  └─ 渲染器链
       ├─ Markdown Renderer → .md 文件
       ├─ HTML Renderer → .html 文件
       ├─ DOCX Renderer → .docx 文件（python-docx）
       └─ PDF Renderer → .pdf 文件（pypdf/weasyprint）
            ↓
       前端统一预览（PdfViewer 组件 + react-markdown GFM 渲染）
```

12 个模块（含 v0 legacy）均具有可打开的 PDF 产物，通过 `pypdf` 验证 `%PDF` 文件头有效。前后端共享 14 个规范化 Golden Cases，确保 Markdown 渲染逐字一致。

### 4.5 事件追踪与运行可观测

每次任务运行产生三类记录：

**SSE 事件流（实时推送）**：前端通过 Server-Sent Events 订阅 `GET /api/v1/events/task/{task_id}/stream`。事件类型包括：`task_started`、`tool_start/result`（如"开始/完成法规检索"）、`llm_call`（含 Token 使用量，来源标注 `provider_reported` 或 `estimated`）、`node_completed`（含节点耗时）、`task_completed/failed`。服务重启或任务结束 30 分钟后事件流清理（当前为内存态）。

**RunManifest（运行账本）**：异步任务完成时，在 `outputs/{module}/{task}/run_manifest.json` 原子写入结构化账本，含：`run_id`、`task_id`、`module_id`、状态（CREATED/RUNNING/COMPLETED/FAILED/CANCELED/RETRYING）、开始/结束时间、总耗时、脱敏 ProviderSnapshot、LLM 调用次数与 Token 汇总、fallback 记录、输入摘要（字段名 + SHA-256，不含正文）、输出产物列表（角色/路径/trace manifest 引用）。账本由防路径穿越的安全 Loader 读取，通过 `GET /api/v1/events/task/{task_id}/manifest` 向任务所有者提供。

**Trace Manifest（技术轨迹）**：`TraceRecorder` 记录每个 workflow node 和 tool call 的 `queued_at/started_at/ended_at/duration/status`，保存到 `runs/{run_id}/trace/manifest.json`。同时通过版本化适配层支持 OpenTelemetry GenAI semantic conventions 导出（当前为可选功能，关闭时不影响 RunManifest 落盘）。

### 4.6 任务调度与文件管理

**任务生命周期：**

```text
用户提交表单 → 后端创建 TaskOwnership + 异步任务
CREATED → [Worker拾取] → RUNNING
  → [组件链完成] → COMPLETED（写 RunManifest + 清理 Trace）
  → [任一组件失败] → FAILED（写 RunManifest + 错误信息）
  → [用户取消] → CANCELED
  → [重试] → RETRYING（复用原 ProviderSnapshot）
```

**任务归属与数据隔离：** 每个任务通过 `TaskOwnershipModel` 持久化 `task_id → user_id` 映射。9 个异步模块的事件流、CitationMap、引用详情、状态查询与重试接口统一经 `assert_task_access(current_user, task_id)` 校验——非所有者返回 403/404（不泄露任务是否存在）。产物访问从历史路径字符串回退（含 `outputs/` 或 `.html` 后缀即放行）改为 Artifact ID 所有权校验。

**文件产物管理：** 物理内容按 `content_hash` 去重（Markdown、DOCX、PDF 来自同一 ReportDocument 时共享底层 blob），逻辑产物按 `artifact_id/role/format` 保留（一个报告的三份格式各自独立呈现）。支持 HTML、PDF、DOCX、MD、TXT、JSON、CSV 在线预览，XLSX、ZIP 提供下载。主报告默认打开，附件按"输入材料 / 过程证据 / 最终报告 / 数据附件"分组。

---

## 5. 前端功能模块

> 本章回答：**用户界面上有哪些页面和交互组件**

### 5.1 页面结构

| 页面/组件 | 位置 | 功能 |
|---|---|---|
| 首页（Landing） | `components/landing/` | 平台导览：解决什么问题、核心能力、快速进入任务空间 |
| 认证页面 | `pages/auth/`、`components/auth/` | 用户注册、登录、会话管理 |
| 任务空间 | `components/workspace/` | 任务类型选择（按法域分类展示任务卡片）、案例管理 |
| 工作台 | `components/workspace/` | 核心任务闭环区域：三栏布局（资源目录 + 运行面板 + AI 对话区） |
| 知识库中心 | `components/report-center/` | 法规检索、条文查看、跨法域法规浏览 |
| 设置页 | 设置组件 | Provider 配置与测试、得理 API Key 管理、个人设置 |
| 引导模块 | `components/onboarding/` | 首次使用操作指引、关键路径说明 |

### 5.2 工作台核心布局

工作台是用户完成任务的核心区域，采用三栏布局：

| 区域 | 组件 | 功能 |
|---|---|---|
| 左侧：资源目录 | `ResourcePanel` | 按任务组织输入文件和输出产物；支持上传、预览、下载；产物按"输入材料/过程证据/最终报告/数据附件"自动分组 |
| 中间：运行面板 | `ModuleRunPanel` | 表单填写（分步或单页），模块执行（提交→进度条→事件日志→结果预览），报告查看与下载；开发测试模式下提供"一键填充并运行"快速体验入口 |
| 右侧：AI 对话区 | `AssistantPanel` | 法规解释、补充说明、修改建议问答；对话中的引用同样支持点击溯源；会话级 Token 统计显示 |

### 5.3 引用交互系统

前端采用三层引用交互组件，所有引用点击统一进入站内受控交互而非 `window.open` 新开外部页面：

| 组件 | 交互方式 | 功能 |
|---|---|---|
| `InlineCitation` | 正文内角标（如 `[CIT-001]`） | 标记报告正文中的引用位置，角标颜色随 CitationResolution 类型变化（蓝色=exact_article，灰色=source_overview，橙色=external_verified，红色=unresolved） |
| `CitationPopover` | hover / focus 弹出 | 展示法规标题、条文号、原文片段、命中规则、来源类型；2 秒悬停延迟避免误触发 |
| `CitationArticleDrawer` | 点击打开右侧抽屉 | 展示完整条文内容 + 上下文（前后条文），支持站内跳转到知识库详情页，用户可主动打开官方来源外链；返回报告时保留滚动位置和高亮引用 |

### 5.4 运行观察视图

系统提供双层运行观察视图，面向不同技术水平的用户：

| 视图层级 | 受众 | 展示内容 |
|---|---|---|
| 普通用户视图 | 非技术用户 | 任务进度条、阶段说明文字、最终结论摘要、产物预览入口、证据不足提示；不暴露原始事件 JSON |
| 开发/审计视图 | 技术用户/审计人员 | 事件时间线（RunTranscript 组件逐节点展示）、节点耗时、LLM 调用次数与 Token 统计、RAG 命中数、Provider/Model 信息；CLI 通过 `viewer.py --events` 查看持久化事件 |

---

## 6. CLI / 开发者工具

> 本章回答：**开发者和运维人员如何通过命令行操作**

### 6.1 工具结构

```
backend/tests/harness/
├── runner.py          # 命令行执行入口（单案例 / 全模块批量）
├── viewer.py          # 运行结果查看器（--events 查看事件流, --summary 查看汇总）
├── cases/             # 15 个可编辑 JSON 案例（覆盖 11 模块）
└── tests/             # Harness 自身测试（4 项契约测试）
```

### 6.2 运行模式

```bash
# 单案例执行（no-LLM 模式，不调用外部 AI 服务）
python -m backend.tests.harness.runner diagnosis 01_scc_path --no-llm

# 全模块批量 Smoke（15 案例，覆盖 11 模块）
python -m backend.tests.harness.runner all --no-llm --quiet

# 运行结果查看（汇总）
python -m backend.tests.harness.viewer <run_id> --summary

# 运行结果查看（事件流）
python -m backend.tests.harness.viewer <run_id> --events
```

### 6.3 输出结构

```
runs/<module>/<run_id>/
├── input/request.json          # 输入快照（原始请求体）
├── input/hash.txt              # 输入 SHA-256（用于去重和复跑验证）
├── output/result.json          # 输出结果（或 error.json）
├── trace/*.json                # 逐事件 SSE 事件流持久化
├── trace/manifest.json         # Trace 技术轨迹
└── run_manifest.json           # 统一运行账本（含 ProviderSnapshot、Token、产物清单）
```

CLI 独立于前端——不消费前端组件，但从同一事件源（模块的 `TraceRecorder`）读取数据并输出结构化时间线。因此 CLI 结果和前端实时视图的 Token/耗时/状态数值一致。

---

## 7. 评测体系

> 本章回答：**如何衡量系统效果和质量**

### 7.1 Product Smoke 评测

固定小样本的功能回归测试（固定 17 个检索案例 + 14 个生成案例），每次代码变更后跑，保证核心能力不回退：

| 评测维度 | 案例数 | 关键指标 | 当前基线 |
|---|---|---|---|
| 检索（Retrieval） | 17 例 | Recall@K, MRR, 跨法域污染率 | Recall@K 1.0 / MRR 0.7471 / 跨法域污染 0 |
| 生成（Generation） | 14 例 | Issue Recall, Citation correctness, Forbidden-source leakage, Unsupported-claim rate | Issue Recall 0.7143 / Citation correctness 1.0 / Leakage 0 / Unsupported-claim 0 |

> 说明：Smoke 指标只证明固定小样本调用链的确定性回归情况。Citation correctness 当前是期望 source ID 覆盖率，Unsupported Claim 只检查案例列出的禁止性文本——均不等同于完整法律正确性。

### 7.2 规模化 RAG 评测

数据集包含 240 个合成正例和 140 个合成负例（共 380 例），Top-K 为 5。评测目标是衡量一般化场景（非固定案例）下检索的效果：

| 模式 | Recall@K | Top1 | MRR | SafeReject |
|---|---|---|---|---|
| vector | 0.150 | 0.133 | 0.140 | 0.243 |
| hybrid | 0.150 | 0.133 | 0.140 | 0.243 |

模块级分析：BCR、CN Flow、SCC 三个模块正例 Recall 为 0（知识库覆盖或查询与索引不匹配，待排查）；CPRA 为 0.042，Diagnosis 为 0.125。Vector 与 Hybrid 完全相同——说明当前评测调用链没有实际启用 Hybrid 的不同策略，这是 P1 待修复项。

### 7.3 评测命令

```bash
# 运行 Smoke 评测
uv run --frozen python scripts/run_smoke_benchmark.py

# 运行规模化 RAG 评测
uv run --frozen python scripts/run_rag_retrieval_benchmark.py
```

---

## 8. 自动化验证基线

> 本章回答：**怎么证明系统当前是可运行的**

### 8.1 当前验证结果

| 验证项 | 结果 | 说明 |
|---|---|---|
| 后端全量测试 | 528 passed, 1 warning | pytest 全量通过 (57.76s)。唯一警告为 Starlette TestClient 对 httpx 的弃用提示——不影响功能，后续依赖升级时处理 |
| 前端单元测试 | 48 passed (15 test files) | Vitest 全量通过 (6.58s)，含 Citation 交互、Auth、PDF 预览、事件 hook 等测试 |
| 前端生产构建 | 通过，342 modules | TypeScript + Vite 生产构建成功，无编译错误 |
| Python 编译检查 | 通过 | `python -m compileall -q backend` 退出码 0 |
| 仓库卫生检查 | 963 个文件通过 | `check_repository_hygiene.py`：无历史目录、缓存、凭据或运行产物越界 |
| 活动文档本地链接 | 0 断链 | 所有活动文档（standards/handoff）中的内部链接有效 |
| API 路由基线 | 101 个显式 Method+Path | `/health` 1、v0 7、v1 93，无重复路由 |
| 11 模块 CLI Smoke | 15 PASS, 0 FAIL | 覆盖全部 11 个模块，no-LLM 模式离线运行 |
| 模块 PDF 产物 | 12/12 有效 PDF | 通过 `pypdf` 验证 `%PDF` 文件头有效 |

### 8.2 验证命令集

```bash
uv run --frozen pytest -q                                          # 后端全量测试
npm --prefix frontend test -- --run                                 # 前端测试
npm --prefix frontend run build                                     # 前端生产构建
uv run --frozen python scripts/check_repository_hygiene.py          # 仓库卫生
uv run --frozen python -m compileall -q backend                     # Python 编译检查
uv run --frozen python -m backend.tests.harness.runner all --no-llm # 11模块CLI Smoke
```

---

## 9. 配置与部署说明

> 本章回答：**如何配置环境和部署系统**

### 9.1 环境变量

| 变量 | 说明 | 是否必需 |
|---|---|---|
| `APP_ENV` | 应用环境：`development` / `production` | 否（默认 development） |
| `LLM_API_KEY` | LLM Provider 的 API Key | 是（生产环境） |
| `LLM_BASE_URL` | LLM Provider 的 Base URL | 是（生产环境） |
| `LLM_MODEL` | 默认模型名称 | 否（可在前端设置页选择） |
| `DELILEGAL_API_KEY` | 得理法律 API Key | 否（不使用得理则不需要） |
| `DATABASE_URL` | 数据库连接字符串 | 否（默认 SQLite） |
| `STORAGE_DIR` | 文件存储根目录 | 否（默认 `storage/`） |
| `OUTPUTS_DIR` | 运行产物根目录 | 否（默认 `outputs/`） |

`.env.example` 提供配置模板，不包含真实密钥。

### 9.2 Provider 配置管理

前端设置页提供完整的图形化配置界面：

- 新增、删除、启用、选中 LLM Provider（支持多个并存，运行时选择一个）
- "测试连接"按钮——执行健康探测（模型列表 + 最小生成请求），返回延迟和可用模型列表，稳定区分六类错误码（模型不存在/余额不足/鉴权失败/限流/超时/网络错误）
- 得理 API 专用"测试连接"——使用一次最小法规查询验证 API Key 有效性
- 探测结果在前端展示（绿色=可用，黄色=待确认，红色=不可用），不暴露密钥明文

### 9.3 模块注册表

`config/module_registry.json` 是跨前后端模块身份的唯一权威源。后端通过它装配 FastAPI Router 和异步任务执行器，前端通过它生成任务卡片和表单。每个模块注册项包含：

```json
{
  "module_id": "cn.transfer_diagnosis",
  "jurisdiction": "cn",
  "frontend_key": "diagnosis",
  "task_template_id": "cn_diagnosis",
  "implementation_package": "backend.domains.cn.transfer_diagnosis",
  "v1_api_prefix": "/api/v1/diagnosis",
  "lifecycle": "active"
}
```

修改模块身份必须同步检查 6 类消费者：API 路由定义（`backend/api/v1/endpoints/`）、前端任务模板（`frontend/src/lib/task-templates.ts`）、前端模块注册表（`frontend/src/lib/module-registry.ts`）、CLI 案例（`backend/tests/harness/cases/`）、评测数据集（`benchmarks/datasets/`）、测试文件。不得建立第二注册表或同义实现。

---

## 10. 安全与权限控制

> 本章回答：**系统如何保证数据和访问安全**

### 10.1 认证机制

系统采用 Token-based 认证。前端 `auth/` 模块管理登录状态和 Token 存储，后端通过 FastAPI 依赖注入（`Depends(get_current_user)`）校验每个请求的 Authorization Header。未登录请求统一返回 401。

### 10.2 数据隔离

| 隔离维度 | 机制 | 说明 |
|---|---|---|
| 任务归属 | `TaskOwnershipModel` | `task_id → user_id` 持久化映射，数据库级强关联 |
| 产物访问 | Artifact 所有权校验 | 预览和下载均通过 `artifact_id` 查询归属（`artifact→run→task→owner`），删除路径字符串回退授权 |
| 事件流访问 | `assert_task_access` | 9 个异步模块的 SSE 订阅、CitationMap、引用详情共用同一鉴权函数 |
| 引用访问 | 任务归属校验 | 引用详情 API 校验请求者是否为任务所有者 |
| 跨用户防护 | 统一 403/404 | 不存在的任务和非所有者任务统一 404——不泄露任务存在与否 |

### 10.3 敏感信息保护

- **密钥不回显**：API 返回 Provider 配置时，`api_key` 字段被脱敏为 `"****"`，前端设置页不展示已保存的 Key 值
- **不进日志**：日志配置类过滤 `api_key`、`secret`、`token`、`password` 等敏感字段名
- **不进产物**：RunManifest.sanitized() 删除 API Key 后写入，仅保留 SHA-256 指纹用于配置一致性校验
- **ProviderSnapshot 禁 repr**：`__repr__` 方法不输出 `api_key` 字段，防止调试输出泄露
- **文件权限**：`storage/runtime_settings.json`（保存 Provider 配置）设置 `0o600` 权限
- **生产建议**：接入密钥管理服务（如环境变量注入），不在配置文件中以明文存储密钥

---

## 附录 A：模块功能矩阵

| 模块 ID | 法域 | 名称 | 功能类型 | 核心输出 | CLI | 前端一键测试 | 生命期 |
|---|---|---|---|---|---|---|---|
| `cn.transfer_diagnosis` | CN | 合规路径诊断 | 路径判断 | 路径结论报告 | ✅ | ✅ | active |
| `cn.security_assessment` | CN | 安全评估 | 草案生成 | MD/HTML/DOCX/PDF 报告 | ✅ | ✅ | active |
| `cn.document_review` | CN | 文档智能审查 | 审阅 | 审查报告 + 批注版 DOCX | ✅ | ✅ | active |
| `cn.pipia` | CN | 个人信息保护影响评估 | 草案生成 | PIPIA 报告 + 标准合同备案材料 | ✅ | ✅ | active |
| `eu.scc_review` | EU | 标准合同条款审查 | 审阅 | 审查报告 + 批注版 DOCX | ✅ | ✅ | active |
| `eu.bcr_review` | EU | 约束性公司规则审查 | 审阅 | 审查报告 | ✅ | ✅ | active |
| `eu.dpia` | EU | 数据保护影响评估 | 草案生成 | DPIA 报告 | ✅ | ✅ | active |
| `eu.tia` | EU | 传输影响评估 | 草案生成 | TIA 报告 | ✅ | ✅ | active |
| `us.eo_14117` | US | EO 14117 风险评估 | 路径判断+评估 | 风险评估报告 | ✅ | ❌ | active |
| `us.eo_14117_flow_review` | US | EO 14117 流程审查 | 数据流审查 | 数据流审查报告 | ✅ | ❌ | legacy-compatible |
| `us.cpra` | US | CPRA 合规评估 | 填表清单 | xlsx 差距清单 + 摘要报告 | ✅ | ❌ | active |

---

## 附录 B：API 路由总览

| 路由前缀 | 版本 | 说明 |
|---|---|---|
| `/health` | — | 健康检查 |
| `/api/v0/` | v0（兼容） | 文件上传网关、历史任务接口（7 条路由） |
| `/api/v1/diagnosis` | v1 | CN 合规路径诊断 |
| `/api/v1/assessment` | v1 | CN 安全评估 |
| `/api/v1/review` | v1 | CN 文档智能审查 |
| `/api/v1/pipia` | v1 | CN 个人信息保护影响评估 |
| `/api/v1/eu_scc` | v1 | EU 标准合同条款审查 |
| `/api/v1/bcr` | v1 | EU 约束性公司规则审查 |
| `/api/v1/dpia` | v1 | EU 数据保护影响评估 |
| `/api/v1/tia` | v1 | EU 传输影响评估 |
| `/api/v1/us_14117` | v1 | US EO 14117 风险评估 |
| `/api/v1/cn-flow` | v1 | US EO 14117 流程审查（历史兼容键） |
| `/api/v1/cpra` | v1 | US CPRA 合规评估 |
| `/api/v1/system/settings/` | v1 | Provider 配置与健康检查 |
| `/api/v1/events/` | v1 | 任务事件流订阅与 RunManifest 读取 |
| `/api/v1/citations/` | v1 | 引用详情查询 |
| `/api/v1/artifacts/` | v1 | 产物预览与下载 |

合计 101 条显式路由（Method + Path），无重复。

---

## 附录 C：技术指标

| 指标 | 数值 | 说明 |
|---|---|---|
| 后端测试通过数 | 528 | pytest 全量，含 API 路由契约、9 模块异步隔离、Provider 健康探测、引用交互等 |
| 前端测试通过数 | 48 (15 test files) | Vitest 全量，含组件渲染、用户交互、API mock |
| 前端生产构建 | 342 modules | TypeScript + Vite，构建成功 |
| 注册业务模块 | 11 | CN 4 / EU 4 / US 3，含 1 个 legacy-compatible |
| API 路由 | 101 | v0 7 + v1 93 + health 1 |
| RAG 逻辑索引 | 15 | 3 法域 × 5 资源类型（legal/workflow/standard_clause/template/testcase） |
| 法律来源 | 69 | 覆盖 CN/EU/US 主要法规，含完整快照 |
| 法规条文登记 | 1,672 行 | 含 1,602 个唯一可精确定位 + 34 组重复定位键（已降级处理） |
| 知识库总体积 | ~49 MB | 法规原文 + 索引 |
| RAG 向量索引 | ~10 MB | SHA-256 哈希 384 维 |
| CLI 案例数 | 15 | 覆盖 11 个模块，JSON 格式可编辑 |
| 历史 CitationMap | 650 份 | 含 16,681 条引用项 |
| `outputs/` 历史产物 | ~720 MB, 25,519 文件 | 需建立清理策略 |
| `check_repository_hygiene.py` | 963 个文件检查通过 | 覆盖历史目录、缓存、凭据与运行产物边界 |
| 活动文档本地链接 | 0 断链 | standards/ + handoff/ 全量有效 |

---

## 附录 D：已知限制与后续规划

### D.1 当前已知限制

1. **规模化 RAG 检索质量不足**：380 例评测中 Recall@5 仅 0.150，BCR/CN Flow/SCC 三个模块 Recall 为 0（知识库覆盖不足或查询-索引不匹配），Vector 与 Hybrid 结果完全相同（检索策略可能未差异生效）。Smoke 的 Recall@K 1.0 只证明固定案例回归通过。

2. **EU/US 模块生成 Issue 覆盖缺口**：Product Smoke 14 个生成案例中 EU SCC、EU BCR、US EO 14117、US Privacy 四个案例 Issue Recall 为 0——系统生成了报告但 Issue 标识未命中 Gold。

3. **US 域三个模块缺少前端一键测试**：`us.eo_14117`、`us.eo_14117_flow_review`、`us.cpra` 有 CLI Smoke 覆盖但无可用的"一键填充并运行"前端入口。

4. **运行持久化不完整**：任务执行器和 SSE 事件流为内存态——服务重启后能查看 RunManifest 账本文件但无法恢复运行状态或历史事件时间线。

5. **外部 API 可用性依赖外部条件**（ENV-BLOCK）：当前默认腾讯混元模型 `hy3-preview` 不可用，其他候选模型遇到下线或余额不足。得理 API 可真实调用但适配器丢弃了稳定 ID、条号和效力状态，尚不能直接承担可信引用入库。

6. **知识库 34 组重复定位键待消歧**：已通过 CitationResolution 机制降级为 `source_overview`（不提供精确跳转），但最终消歧（区分版本差异、章节重复、脏数据）仍需法律内容负责人确认。

### D.2 后续规划优先级

```text
P0 发布阻断修复（已完成：数据隔离、证据真实性、确定性哈希、Provider健康门禁）
  → P1 Benchmark 数据与索引一致性审计（排查 BCR/SCC Recall=0 根因）
  → P1 RAG 路由/模式/拒答修复（修复 Vector=Hybrid 问题，提升 Recall@5）
  → P1 EU/US Issue 失败案例归因与回归
  → P1 中国路径专家 Gold 建设（12-20 个案例）
  → P2 Claim/Evidence/Citation 最小试点（从诊断+安全评估开始）
  → P2 运行持久化（任务执行器 + 事件流从内存态迁移到持久存储）
  → P3 代码质量（Ruff/Mypy/ESLint）、依赖升级、输出清理策略
```
 