# 数规通 · 整体现状全景（v1）

> 最后更新：2026-04-04（已同步知识库与 RAG 评测）

## 一、整体架构

```text
用户（企业/律师）
  │
  ▼
Streamlit 前端（app_streamlit/）
  │  HTTP → http://127.0.0.1:8000
  ▼
FastAPI 后端（backend/）
  ├── /api/v1/  ← 各模块路由（main.py + app.py）
  └── /api/v0/  ← 统一任务网关
       │
       ├── LLM（腾讯混元 hunyuan-turbos-latest）
       ├── 知识库 RAG（doc/knowledge/normalized/）
       ├── 得理法搜 API（queryListCase + queryListLaw）
       ├── 任务管理（InMemoryTaskManager）
       ├── SQLite 数据库（storage/ai4law.db）
       └── 文件存储（storage/uploads|reports|drafts）
```

- 技术栈：FastAPI + SQLAlchemy(SQLite) + Streamlit + python-docx + pypdf + openai SDK
- LLM 状态：✅ 已接入腾讯混元 API（`hunyuan-turbos-latest`），OpenAI 兼容协议；未配置 API Key 时自动降级为占位文本
- 部署：本地单机，前后端分进程运行

---

## 二、LLM 集成架构

### 1) LLMClient

`backend/common/llm/client.py`

- 封装 `openai.OpenAI`，`base_url` 指向腾讯混元 v1 接口
- 环境变量：`TENCENT_API_KEY`、`TENCENT_API_URL`（Settings 支持 `AI4LAW_` 前缀别名）
- `enabled` 属性：无 API Key 时为 False，所有模块自动降级为占位内容
- `chat(system, user, temperature, max_tokens) → str`，调用失败时返回错误提示字符串

### 2) 模块章节生成器

`backend/common/llm/module_generator.py`

- `SYSTEM_PROMPTS`：7 个模块（scc / pipia / bcr / dpia / tia / cn_flow / cpra）各自的系统 Prompt
- `CHAPTER_INSTRUCTIONS`：每个模块每个章节的具体写作指令
- `generate_chapter(llm_client, module, chapter_title, context_block) → str`

### 3) 自动服务发现

所有独立模块服务（SCCService、PIPIAService 等）在 `__init__` 中若未传入 `llm_client`，会自动从 `get_settings()` 构建 `LLMClient` 实例。无需修改路由器代码。

---

## 三、知识库现状

### 1) 存储位置

`doc/knowledge/normalized/regulation_articles.jsonl`

### 2) 数据规模

| 指标 | 数值 |
|---|---|
| 总条数 | 1011 条 |
| 中国法规 | 394 条 |
| 欧盟法规 | 398 条 |
| 美国法规 | 219 条 |

### 3) 重点法规覆盖（Top）

| 法规 | 条数 |
|---|---:|
| GDPR（一般数据保护条例）中文版 | 227 |
| California Privacy Rights Act (CPRA) 2020 | 183 |
| EDPB Recommendations 1/2022 on BCR-C | 95 |
| 网络安全法（2025 修正） | 85 |
| 个人信息保护法 | 73 |
| 网络数据安全管理条例 | 65 |
| 数据安全法 | 54 |
| EU Standard Contractual Clauses (2021) | 33 |
| Executive Order 14117 (Feb 2024) | 26 |
| 个人信息出境认证办法 | 20 |
| 《标准合同办法》答记者问 | 19 |
| 促进和规范数据跨境流动规定（全文页） | 14 |
| CLOUD Act (2018) | 6 |

### 4) 检索方式

- 本地：bigram 重叠 + 关键词匹配 + 优先级权重的混合词法检索，无向量嵌入
- **外部补充（新）**：当本地检索结果 < 3 条时，自动调用得理法搜 `queryListLaw` 端点进行语义补充，结果追加到返回列表末尾（`usage_priority=P2`）

### 5) 知识库问题

⚠️ 当前主要问题已从“数量不足”转为“质量治理”：

- 部分英文 PDF 条目存在断词/OCR 噪声（会影响检索排序与摘要可读性）
- `path/doc_type` 标签仍有可细化空间，影响模块内命中精度
- 评测显示 `diagnosis/assessment/review` 仍是相对薄弱模块（见第七部分评测结果）

### 6) 文章数据格式

```json
{
  "article_id": "CN-LAW-001-001",
  "jurisdiction": "cn",
  "path": "all",
  "law_name": "...",
  "article_ref": "第一条",
  "content": "...",
  "keywords": ["..."],
  "source_url": "...",
  "snapshot_path": "..."
}
```

---

## 四、各模块整体情况

### 1) 模块分布

- 中国合规路径：2.1 合规路径诊断、2.2 安全评估、2.3 PIPIA 生成、2.4 通用服务（空壳）、2.5 合同审查
- 欧盟合规工具：3.1 SCC 审查、3.2 BCR 审查、3.3 DPIA 起草、3.4 TIA 起草
- 美国合规工具：4.1 EO14117 合规、4.2 CPRA 合规

### 2) 实现程度评级

| 模块 | 代码存在 | 流程完整 | LLM 接入 | 知识库充足 | 测试 |
|---|---|---|---|---|---|
| 2.1 诊断 | ✅ | ✅ | ✅ LLM rationale | ✅ | ✅ |
| 2.2 安全评估 | ✅ | ✅ | ✅ 8 章 LLM | ✅ | 部分 |
| 2.3 PIPIA | ✅ | ✅ | ✅ 7 章 LLM | ✅ | 部分 |
| 2.4 通用服务 | ⚠️ 占位 | ❌ | ❌ | - | ❌ |
| 2.5 合同审查 | ✅ | ⚠️ Mode A | ✅ LLM + 规则降级 | ✅ | 部分 |
| 3.1 SCC 审查 | ✅ | ✅ | ✅ 6 章 LLM | ✅（本地+外部补充） | 部分 |
| 3.2 BCR 审查 | ✅ | ✅ | ✅ 4 章 LLM | ✅（本地+外部补充） | 部分 |
| 3.3 DPIA | ✅ | ✅ | ✅ 7 章 LLM | ✅（本地+外部补充） | 部分 |
| 3.4 TIA | ✅ | ✅ | ✅ 6 章 LLM | ✅（本地+外部补充） | 部分 |
| 4.1 EO14117 | ✅ | ✅ | ✅ 4 章 LLM | ✅（本地+外部补充） | 部分 |
| 4.2 CPRA | ✅ | ✅ | ✅ 6 章 LLM | ✅（本地+外部补充） | 部分 |

---

## 五、各模块具体流程与输入输出

### 2.1 合规路径诊断（V2）

**流程**：用户填写 8 题问卷 → 提交答案 → 决策树评估 → LLM 生成专业说明 → 调用得理 API（案例 + 法规）→ 返回合规路径

**决策树逻辑（9 条规则，豁免优先）**：

豁免规则（先匹配，命中即返回 `exemption`）：

1. 无个人信息且不涉及重要数据
2. 履行合同/向消费者提供服务所必需（且规模未达门槛）
3. 跨国公司集团内部人力资源管理（且规模未达门槛）
4. 紧急情况保护自然人生命健康财产
5. 履行法定职责或法定义务

强制申报规则：

6. 是否 CIIO → `security_assessment`
7. 涉及重要数据出境 → `security_assessment`
8. 个人信息出境总量 ≥ 100 万 → `security_assessment`
9. 敏感个人信息出境 ≥ 1 万 → `security_assessment`

默认：`scc_or_certification`

**法规依据**：《促进和规范数据跨境流动规定》第 4-7 条、《个人信息保护法》第 38-40 条

**输入（8 题）**：

```json
{
  "q1_is_ciio": "yes|no|unknown",
  "q2_has_important_data": "yes|no|unknown",
  "q3_pii_count": 0,
  "q4_spi_count": 0,
  "q5_no_personal_info": "yes|no",
  "q6_scenario": "contract_performance|hr_management|emergency|legal_duty|other",
  "q7_receiver_type": "intra_group|third_party",
  "q8_purpose": "出境目的简述"
}
```

**输出**：

```json
{
  "recommended_path": "security_assessment|scc_or_certification|exemption",
  "risk_level": "HIGH|MEDIUM|LOW",
  "rationale": "LLM 生成的专业法律说明",
  "legal_basis": ["促进和规范数据跨境流动规定 第5条..."],
  "action_items": ["后续行动建议..."]
}
```

---

### 2.2 安全评估报告生成

**流程**：输入表单 → ProfileExtractor → AssessmentRetriever（本地 RAG + DeliLegal 补充）→ AssessmentChapterGenerator（LLM × 8 章）→ ConsistencyChecker → 渲染 DOCX/MD

**8 章结构**：

1. 出境活动概述
2. 数据类型与规模
3. 出境必要性与合法性基础
4. 境外接收方保障能力
5. 个人信息权益影响分析
6. 安全措施与传输机制
7. 剩余风险与整改建议
8. 综合评估结论

**输入（10 大类字段）**：

- 基础数据：公司名称、行业、是否 CIIO、是否含重要数据
- 出境信息：出境目的、接收方名称/国家地区、个人信息规模、敏感信息规模
- 应急预案、安全保障措施、数据处理协议（可上传文件）

**输出**：

- `assessment_report.docx`（8 章 Word）
- `assessment_report.md`（Markdown）
- 任务结果 JSON（含进度、状态、章节内容）

---

### 2.3 PIPIA 生成（SCC 备案 / 认证路径）

**流程**：输入（含附件）→ 附件解析 → RAG 检索 → LLM 7 章生成 → ConsistencyChecker → 渲染 MD + DOCX + ZIP

**7 章结构**：

1. 处理者与出境活动基础信息
2. 个人信息出境处理活动说明
3. 境外接收方信息与保护能力
4. 个人信息主体权益影响评估
5. 技术与组织措施有效性评估
6. 事件响应与整改计划
7. PIPIA 结论与备案建议

**输入**：

- `company_profile`：公司基本信息（CIIO、PI/SPI 规模等）
- `transfer_context`：出境场景、接收方国家、目的、法定基础
- `route_type`：`scc_filing` | `certification`
- `attachments`：上传文件列表（协议文本等）
- `emergency_plan`：应急预案 SLA

**输出**：

- `pipia_report.md`
- `pipia_report.docx`
- `pipia_output_bundle.zip`

---

### 2.5 合同审查（当前：单模式；设计：双模式）

**当前流程**：

上传合同文件 → ClauseSegmenter（条款切分）→ ClauseClassifier（条款分类）→ ClauseReviewer（LLM 分析 + 规则降级）→ ReviewAggregator（汇总）→ ReviewReportRenderer → 输出审查报告

**ClauseReviewer LLM 模式（新）**：

- 对每个分类条款调用 LLM，输出结构化 JSON 问题列表
- 每个问题包含：`severity`（HIGH/MEDIUM/LOW）、`title`、`problem_type`、`risk_analysis`、`recommendation`
- LLM 不可用或解析失败时自动降级为关键词匹配规则引擎

**输入**：

```json
{
  "file": "上传合同文件(.pdf/.docx)"
}
```

**输出（当前 Mode A）**：单一审查报告（含条款级问题清单、整体评级）

**设计目标（Mode B 尚未实现）**：

- `RevisionInstructionGenerator` → `ContractRewriter` → `DiffGenerator`
- 输出：`revised_contract.docx` + diff 视图

⚠️ 与设计文档差距：

- 未实现 Mode B（修订合同生成）
- 无 `review_mode/review_stance/contract_type` 参数
- 无 `GET /revised-contract` 和 `GET /diff` 端点

---

### 3.1 SCC 审查（PIPIA 报告）

**流程**：表单输入 → 企业画像构建 → RAG 检索（本地 + DeliLegal 补充）→ LLM 6 章生成 → 渲染 DOCX/MD

**6 章结构**：

1. 处理活动与出境背景
2. 个人信息类型与规模
3. 境外接收方保护能力
4. 合同与组织措施
5. 个人信息权益影响分析
6. PIPIA 结论与备案建议

**输入**：企业名称、接收方名称/国家、出境目的、PI/SPI 规模、是否已有合同草案、上传附件

**输出**：`{company}_pipia_report.docx` + `.md`

---

### 3.2 BCR 审查

**流程**：提交 10 维度审查项 → 问题提取 → 评级计算 → LLM 生成报告摘要/整改建议 → 渲染

**10 个合规维度（3.2-C1 ~ C10）**：约束力/可执行性、数据主体权利、透明度、跨集团数据流、充分性保障、数据安全、跨境再转移、主导实体义务、合作监管、责任机制

**输入**：`review_items`（每项含 `code`、`title`、`score`、`finding`、`recommendation`）、附件

**输出**：`{company}_bcr_review_report.docx` + `.md` + `.zip`（含综合评级、问题清单、LLM 整改建议）

---

### 3.3 DPIA 起草

**流程**：表单输入 → RAG 检索 GDPR 条款（本地 + DeliLegal 补充）→ LLM 7 章生成 → 渲染

**7 章结构**：

1. DPIA 项目背景与范围
2. 数据处理活动描述
3. 目的必要性与合法性评估
4. 风险识别与影响分析
5. 控制措施与缓解方案
6. 剩余风险与可接受性判断
7. DPO 复核与后续行动

**输入**：项目名称、处理活动描述、目的/必要性、合法基础、风险评估、缓解措施、剩余风险、附件

**输出**：`{project}_dpia_report.docx` + `.md` + `.zip`

---

### 3.4 TIA 起草

**流程**：输入 → RAG 检索（本地 + DeliLegal 补充）→ LLM 6 章生成 → 渲染

**6 章结构**：

1. 跨境传输场景与角色识别
2. 传输工具适用性判断
3. 第三国法律与实践评估
4. 补充措施可执行性评估
5. 剩余风险与合规结论
6. 持续复审与行动计划

**输入**：传输工具类型、出口方/进口方描述、第三国评估、补充措施、最终结论、附件

**输出**：`{transfer_tool}_tia_report.docx` + `.md` + `.zip`

---

### 4.1 EO14117 合规（cn_flow）

**流程**：数据盘点 + 实体清单 → 风险项构建 → RAG 检索（本地 + DeliLegal 补充）→ LLM 4 章生成 → 渲染

**4 章结构**：

1. 场景定义与适用范围
2. 数据类型与实体结构分析
3. 限制条件命中分析
4. 风险分级与处置建议

**输入**：企业名称、传输目的、数据类别、接收方实体（是否受限）、传输链路、敏感数据标志、附件

**输出**：`{company}_cn_flow_compliance_report.docx` + `.md` + `.pdf` + `.xlsx`（风险清单）+ `.zip`

---

### 4.2 CPRA 合规

**流程**：4 类输入 → 合规差距构建 → RAG 检索（本地 + DeliLegal 补充）→ LLM 6 章生成 → 渲染

**6 章结构**：

1. 执行摘要
2. 企业适用性与范围
3. 数据处理活动合规分析
4. 消费者权利保障评估
5. 敏感信息与第三方管理
6. 行动清单与优先级

**输入**：企业名称、业务模型、数据生命周期、告知同意、消费者权利流程、出售/共享机制、供应商管理、附件

**输出**：`{company}_cpra_panorama_report.docx` + `.md` + `.pdf` + `.xlsx`（整改路线图）+ `.zip`

---

## 六、外部 API 集成

### 得理法搜（DeliLegalService）

| 端点 | 功能 | 调用方 |
|---|---|---|
| `queryListCase` | 案例/裁判检索 | 合同审查 RAG、诊断法律依据 |
| `queryListLaw` | 法规/法条检索 | 诊断法律依据补充、RAG 检索器（本地结果 < 3 条时自动补充） |

- 环境变量：`AI4LAW_DELILEGAL_BASE_URL`、`AI4LAW_DELILEGAL_APP_ID`、`AI4LAW_DELILEGAL_SECRET`
- `enabled` 属性：未配置时静默跳过，不影响本地 RAG 功能
- 所有模块服务通过 `retrieve_regulations()` 的 `legal_service` 参数（或自动发现的默认单例）透明使用

---

## 七、整体设计现状与核心问题

### 1) 完成度总结

| 维度 | 状态 |
|---|---|
| API 框架/路由 | ✅ 完整 |
| 数据库/任务管理 | ✅ 完整 |
| 前端页面框架 | ✅ 完整 |
| 中国知识库 | ✅ 基本完整 |
| 报告模板/渲染 | ✅ 可用 |
| LLM 接入（全模块） | ✅ 已完成 |
| 诊断 V2（8 题+豁免规则） | ✅ 已完成 |
| 合同审查 LLM 升级 | ✅ 已完成 |
| DeliLegal queryListLaw | ✅ 已接入 |
| 欧美知识库 | ✅ 基础规模已补齐（EU 398 / US 219） |
| 2.5 双模式合同审查 Mode B | ❌ 未实现 |
| 2.4 通用服务 | ❌ 空壳 |
| 向量嵌入检索 | ❌ 仍为词法检索 |

### 2) 当前开发阶段定位

当前处于 **v1（LLM 接入阶段）**：架构、流程、API 接口、数据模型已就位，真实 LLM 已注入所有报告生成模块，端到端流程可产出有实质内容的合规报告。

剩余核心工作：

1. 完成 2.5 双模式合同审查（Mode B：修订合同生成 + diff 视图）
2. 清洗欧盟/美国条文文本噪声并细化 `path/doc_type` 标注
3. 引入向量嵌入检索替换现有词法 RAG
4. 完成 2.4 通用服务模块
5. WebSocket 实时进度推送完整化

### 3) 知识库仍有欠缺

- 欧盟：各国 DPA 执法口径、行业场景案例仍偏少
- 美国：州法层面（除 CPRA）与执法案例仍需补齐

### 4) 最新 RAG 评测（2026-04-04）

数据集：`doc/knowledge/evaluation/rag_eval_v2_queries.csv`（300） + `rag_eval_v2_hard_negatives.csv`（80）

| 模式 | 正例数 | Recall@5 | Top1 Acc | 负例数 | SafeReject |
|---|---:|---:|---:|---:|---:|
| vector | 240 | 0.887 | 0.688 | 140 | 0.857 |
| hybrid | 240 | 0.854 | 0.675 | 140 | 0.936 |

结论：

- `SafeReject >= 0.70` 已达标（两种模式均达标）
- `vector` 召回更高，`hybrid` 拒答更稳
- 目前薄弱模块主要集中在 `diagnosis / assessment / review`

---

## 附：关键文件索引

| 文件 | 用途 |
|---|---|
| `backend/common/llm/client.py` | LLMClient（腾讯混元封装） |
| `backend/common/llm/module_generator.py` | 各模块章节 Prompt 集中管理 |
| `backend/common/rag/retriever.py` | 本地 RAG 检索器（含 DeliLegal 补充逻辑） |
| `backend/services/legal_api_service.py` | DeliLegal 案例 + 法规检索 |
| `backend/modules/diagnosis/decision_tree.json` | 诊断 V2 决策树（9 条规则） |
| `backend/modules/assessment/chapter_generator.py` | 安全评估 8 章 LLM 生成 |
| `backend/services/review_service/clause_reviewer.py` | 合同审查 LLM + 规则降级 |
| `backend/core/settings.py` | 全局配置（LLM / DeliLegal / 存储） |
| `backend/core/container.py` | 服务依赖注入（主 app.py 路径） |
| `doc/knowledge/normalized/regulation_articles.jsonl` | 本地法规知识库（1011 条） |
