# Rule-Agent Boundary Charter

> 中文名：规则-Agent 边界宪章  
> 性质：平台级架构约束文件，具有最高约束力  
> 状态：生效中  
> 版本：1.0  
> 制定日期：2026-06-04

---

## 目录

1. [宪章目的](#一宪章目的)
2. [边界总则](#二边界总则)
3. [规则的不可让渡领域](#三规则的不可让渡领域)
4. [Agent 的合法干预领域](#四agent-的合法干预领域)
5. [置信度门禁机制](#五置信度门禁机制)
6. [冲突裁决规则](#六冲突裁决规则)
7. [各模块边界清单](#七各模块边界清单)
8. [边界违规判定标准](#八边界违规判定标准)
9. [开发 Checklist](#九开发-checklist)
10. [附：典型违规案例](#十附典型违规案例)

---

## 一、宪章目的

### 1.1 为什么需要这份宪章

平台上有两类判断能力在同时运行：

```text
规则引擎：关键词匹配、阈值比较、模式检测、checklist 状态机
Agent：    LLM 推理、语义理解、上下文推断、模糊判断
```

Agent 编程体验好、调试快、效果直观。不加约束的情况下，开发者会自然倾向用 Agent 替代规则。这在原型阶段无害，但在合规产品中是致命缺陷：

```text
❌ 规则引擎只剩 3 条规则，其他全由 Agent 判断
❌ 同一输入两次运行得到不同路径结论
❌ 用户问"为什么这么判"，系统无法给出确定性解释
❌ 监管审查时无法证明判断依据是法律条文而非 LLM 的统计建模
```

### 1.2 宪章的约束力

本宪章是平台最高优先级的架构约束。

```text
任何模块的 service.py 实现、Agent 接入代码、报告生成逻辑，
如果与本宪章冲突，以本宪章为准。

如果确实需要突破某条边界，必须在代码中：
  1. 添加注释引用本宪章的具体条款号
  2. 在 PR 描述中说明突破理由
  3. 获得架构审查批准
```

---

## 二、边界总则

### 2.1 核心原则

```
原则 1：规则拥有"阻断权"（Rule Veto）
    → 任何 Agent 输出不能覆盖或删除规则引擎的判断结论
    → 规则引擎的输出永远是最终结论的基础

原则 2：Agent 拥有"建议权"（Agent Advisory）
    → Agent 可以生成建议值、风险提示、解释文本
    → 建议值必须通过置信度门禁才能进入规则输入
    → 建议值必须保留原始用户输入可回溯

原则 3：最终路径判断属于规则引擎
    → 路径判断（安全评估 / 标准合同 / 认证 / 豁免）由规则引擎统一计算
    → Agent 可以生成"建议路径"和"路径置信度"，但不能直接设定 final_path

原则 4：最终风险评级属于规则引擎
    → overall_rating / 最终风险等级由规则引擎聚合计算
    → Agent 可以生成 risk_hint / risk_chain，但不能直接设定 final_rating

原则 5：Agent 可以写"解释"，不能改"结论"
    → Agent 可以生成 rationale / explanation / context
    → 不能修改 rule_result.matched_rules / overall_rating / recommended_path
```

### 2.2 职责划分总表

| 能力 | 规则引擎 | Agent | 说明 |
|------|:---:|:---:|------|
| 阈值判断（>100万, >2500万, >10万…） | ✅ 独占 | ❌ | 纯数值比较 |
| CIIO / 重要数据定性 | ✅ 独占 | ⚠️ 可建议 | Agent 只能给 suggested_answer |
| 豁免情形适用性 | ✅ 最终判断 | ✅ 辅助判断 | Agent 核验证据充分性，规则做最终判定 |
| Module 适用性（SCC） | ✅ 独占 | ❌ | 确定性角色匹配 |
| 标准条款不可克减性 | ✅ 独占 | ❌ | 强制性法律规则 |
| 条款语义比对 | ⚠️ 关键词匹配 | ✅ 语义推理 | 规则做第一层信号检测，Agent 做语义级复核 |
| 字段分类（PII/SPI/匿名化） | ⚠️ 关键词表 | ✅ 上下文推理 | 规则做基础模式匹配，Agent 做模糊项判断 |
| 风险等级聚合计算 | ✅ 独占 | ❌ | 确定性聚合 |
| 风险链推理（多因素组合） | ❌ | ✅ 独占 | 规则无法穷举组合 |
| 法规引用绑定 | ❌ | ✅ 独占 | 自然语言 → 条文映射 |
| 整改建议生成 | ❌ | ✅ 独占 | 自然语言生成 |
| 报告表达优化 | ❌ | ✅ 独占 | 语言校准 |
| 最终一致性审校 | ⚠️ 模式检查 | ✅ 语义检查 | 规则检查模式（禁止词），Agent 检查语义 |

图例：
- ✅ 独占 = 该层拥有最终决定权
- ⚠️ = 该层做第一轮判断，另一层做复核
- ❌ = 该层不参与

---

## 三、规则的不可让渡领域

以下判断**永远属于规则引擎**，Agent 不得介入（即使是"辅助"）：

### 3.1 硬阈值（CN 法域）

| 规则 ID | 判断内容 | 阈值 | 法律依据 |
|---------|---------|------|---------|
| `ciio` | CIIO 判定 | `is_ciio == True` | 个保法第40条 |
| `important_data` | 重要数据判定 | `has_important_data == True` | 数据安全法第21条 |
| `pii_threshold` | 个人信息规模触发安全评估 | `pii_count >= 1,000,000` | 安全评估办法第4条 |
| `spi_threshold` | 敏感个人信息规模触发安全评估 | `spi_count >= 10,000` | 安全评估办法第4条 |

**Agent 可以做的**：当用户回答 "unknown" 时，Agent 生成 `suggested_answer`（是/否）和 `reasoning`，由规则引擎消费后做最终判断。

### 3.2 硬阈值（US 法域）

| 规则 ID | 判断内容 | 阈值 |
|---------|---------|------|
| `cpra_revenue` | 年收入门槛 | `annual_revenue_usd > 25,000,000` |
| `cpra_consumer_count` | 消费者数量门槛 | `ca_consumer_count >= 100,000` |
| `cpra_revenue_ratio` | 出售/分享收入占比 | `sell_share_revenue_ratio >= 0.5` |

### 3.3 硬阈值（EU 法域）

| 规则 ID | 判断内容 | 规则逻辑 |
|---------|---------|---------|
| `scc_module_validation` | SCC Module 适用性 | exporter_role × importer_role → Module |
| `scc_clause_invariability` | 标准条款不可克减 | EU 2021/914 Recital 3 |
| `third_country_adequacy` | 第三国充分性认定 | 欧盟充分性认定列表 |
| `schrems_ii_trigger` | Schrems II 触发 | 第三国非充分性 + 无补充措施 |

### 3.4 风险等级聚合

```text
所有模块的 final overall_rating 必须由规则引擎统一计算：

计算逻辑（不可 Agent 化）：
  if any finding.severity == "BLOCKER" → "BLOCKER"
  elif any finding.severity == "HIGH" → "HIGH"
  elif any finding.severity == "MEDIUM" → "MEDIUM"
  else → "LOW"

Agent 不能：
  - 下调规则引擎计算的风险等级
  - 因为"描述温和"而降低风险等级
  - 因为"缺少材料"而忽略已确认的高风险
```

### 3.5 路径最终决策

```text
路径决策树（CN）：
  CIIO? → YES → security_assessment
  Important Data? → YES → security_assessment
  PII >= 1M? → YES → security_assessment
  SPI >= 10K? → YES → security_assessment
  No PII + No Important Data? → exemption (no_personal_info)
  Contract Performance + under threshold? → exemption
  HR Management + intra-group + under threshold? → exemption
  ...
  default → scc_or_certification

这棵决策树的最终输出（recommended_path）永远由规则引擎计算。
Agent 只能：
  - 给 suggested_answer 填 unknown 字段
  - 解释为什么某个路径不适用
  - 标记路径判断的不确定性
```

---

## 四、Agent 的合法干预领域

### 4.1 可以做的事（完整清单）

```
1. 从非结构化材料中抽取结构化事实
   → 输入：合同全文、隐私政策、数据清单
   → 输出：FactItem[]，source_type="attachment"
   → 约束：每条 FactItem 必须带 source_ref 指向原文位置

2. 判断模糊字段
   → 用户回答 "unknown" / "不确定" 时
   → 输出：suggested_answer + reasoning + confidence
   → 约束：confidence < 0.65 不进规则输入

3. 条款语义比对
   → 规则已做关键词检测后，Agent 做语义级复核
   → 输出：additional_findings（不删除规则 finding）
   → 约束：只能追加，不能删除

4. 数据敏感性和重识别风险评估
   → 输入：字段名、字段描述、处理方式
   → 输出：DataFieldClassification + risk
   → 约束：不能覆盖用户确认的分类

5. 法规引用精确匹配
   → 输入：IssueItem + RAG 检索结果
   → 输出：CitationBinding（含 support_level）
   → 约束：background_only 引用不得在外报中使用

6. 整改建议生成
   → 输入：IssueItem + FactPack + 文档上下文
   → 输出：RemediationAction + suggested_text
   → 约束：不能建议违法操作

7. 报告表达优化
   → 输入：draft_chapter + ExpressionStrategy
   → 输出：calibrated_chapter
   → 约束：不能改变事实、不能删除风险、不能降低评级

8. 最终一致性审校
   → 输入：完整报告 + FactPack + IssueItem[]
   → 输出：QAProblem[]
   → 约束：修复时不能新增事实、不能降级风险
```

### 4.2 绝对不能做的事

```
❌ 不能直接设定 recommended_path
❌ 不能直接设定 overall_rating / final_risk_level
❌ 不能删除规则引擎已命中的 finding
❌ 不能把 user_claim_only 证据的事实写成确认句
❌ 不能把 planned measure 写成 implemented
❌ 不能生成新的法规引用（只能从 RAG 结果中选择和绑定）
❌ 不能建议用户做违法行为
❌ 不能写 "企业违法" / "企业违规"
❌ 不能在报告中使用 forbidden_expressions 中的任何表达
❌ 不能替用户补齐缺失的材料（只能说 "建议补充"）
```

---

## 五、置信度门禁机制

### 5.1 三级门禁

```text
Agent 输出必须携带 confidence (0.0–1.0)：

┌─────────────────────────────────────────────────────────────┐
│ confidence ≥ 0.85                                           │
│   → 可以进入规则引擎输入层（字段回填）                         │
│   → 在 FactItem 中标记 source_type="attachment",              │
│     evidence_status="documented_evidence" 或 "partial_evidence"│
│   → 在报告中可以使用，但须标注 "系统辅助判断"                  │
├─────────────────────────────────────────────────────────────┤
│ 0.65 ≤ confidence < 0.85                                    │
│   → 可以进入规则引擎输入层，但必须标记                        │
│     source_ref="agent_assisted"                              │
│   → FactItem.requires_user_confirmation = True               │
│   → 报告中只能使用 cautious / conditional 表达               │
├─────────────────────────────────────────────────────────────┤
│ confidence < 0.65                                            │
│   → 不能进入规则引擎输入层                                    │
│   → 只能写入 Trace（审计层）                                  │
│   → 报告中不能引用，内部审查中可以提示"存在不确定性"          │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 每个 Agent 的置信度计算要求

```text
DataClassificationAgent:
  confidence 基于：字段名匹配强度 + 上下文一致性 + 反例存在性

LegalGroundingAgent:
  confidence 基于：RAG 语义相似度 + 条文适用范围匹配 + 法域一致性

ClauseReviewAgent:
  confidence 基于：标准条款相似度 + 削弱信号强度 + 条款完整性

FactExtractionAgent:
  confidence 基于：文档解析质量 + 抽取模式确定性 + 交叉验证一致性

RiskReasoningAgent:
  confidence 基于：事实确定性 × 法规确定性 × 推理链完整性
  注意：RiskReasoning 的 confidence 上限 = min(依赖事实的 confidence)
```

### 5.3 门禁执行点

```text
每个 Agent 的输出在被消费前，必须经过 Gate：

class AgentGate:
    def pass_through(self, agent_output, min_confidence=0.65):
        if agent_output.confidence < min_confidence:
            → 写入 Trace (audit layer)
            → 触发降级路径
            → 返回 fallback 结果
        elif agent_output.confidence < 0.85:
            → 写入 FactPack（标记 requires_user_confirmation=True）
            → 写入 Trace (audit layer)
            → 返回带标记结果
        else:
            → 正常消费
```

---

## 六、冲突裁决规则

### 6.1 当 Agent 和规则引擎冲突时

```text
场景 A：Agent 认为路径应该走 X，规则引擎判定走 Y
  → 最终路径：Y（规则引擎胜出）
  → Agent 的异议写入 Trace
  → 如果 Agent confidence > 0.85，在报告的"不确定事项"中提及

场景 B：Agent 产生了规则引擎没有的 finding
  → 追加到 all_findings（规则 finding 不删除）
  → 标记 source="agent_generated"
  → 不影响规则引擎的 overall_rating 计算（规则评级独立）
  → 在报告中以 issue_certainty="suspected_issue" 表达

场景 C：Agent 认为规则引擎的某个 finding 过于严苛
  → Agent 不能删除或降级规则 finding
  → Agent 可以追加 context / explanation
  → 在报告中以注释形式补充说明

场景 D：规则引擎判定阈值触发，但 Agent 认为实际数量可能低于阈值
  → 规则引擎判定为最终判定
  → Agent 的异议写入 Trace
  → 报告中使用规则判定结果，但标注 "该判定基于用户提供的数据规模"
```

### 6.2 当多个 Agent 冲突时

```text
场景 E：两个 Agent（如 DataClassification 和 RiskReasoning）给出矛盾结论
  → 取 confidence 更高的那个
  → 如果 confidence 接近（差值 < 0.1），都写入 Trace
  → 在报告中标记 "存在不同判断"

场景 F：FactExtractionAgent 和 DataClassificationAgent 对同一字段判断不同
  → DataClassificationAgent 结果优先（它专门做分类）
  → FactExtractionAgent 的结果作为补充上下文
```

---

## 七、各模块边界清单

### 7.1 合规路径诊断

| 判断项 | 拥有者 | Agent 角色 |
|--------|:---:|------|
| `recommended_path` 最终输出 | **规则** (`decision_tree.json`) | 不参与 |
| `q1_is_ciio` 回填 | **规则** | Agent 可建议（important_data_agent） |
| `q2_has_important_data` 回填 | **规则** | Agent 可建议（important_data_agent） |
| `q3_pii_count` 估计 | **规则** | Agent 可建议（pi_classify_agent） |
| `q4_spi_count` 估计 | **规则** | Agent 可建议（pi_classify_agent） |
| `q5_no_personal_info` 判断 | **规则** | Agent 可建议（pi_classify_agent） |
| `q6_scenario` 细化 | **规则** | Agent 可建议（exemption_agent） |
| 阈值触发逻辑 | **规则** | 不参与 |
| Unknown 字段辅助判断 | **Agent** | 独占 |
| 豁免证据充分性 | **Agent** | 独占 |
| 法规解释文本 | **Agent** | 独占 |
| 诊断报告可读性 | **Agent** | 独占 |

### 7.2 CN SCC（标准合同路径）

| 判断项 | 拥有者 | Agent 角色 |
|--------|:---:|------|
| 安全评估门槛触发 | **规则** (`rule_engine.py`) | 不参与 |
| 豁免可能性标记 | **规则** | Agent 核验证据 |
| 路径最终确认 | **规则** | Agent 补充解释 |
| 字段误标检测 | **规则** (关键词表) | Agent 语义复核 |
| 合法性基础论证强度 | **Agent** | 独占 |
| 合同条款级审查 | **Agent** (contract_review_agent) | 独占 |
| 证据核验 | **Agent** (evidence_verification_agent) | 独占 |
| RAG 检索规划 | **Agent** (rag_planning_agent) | 独占 |
| 报告审稿 | **Agent** (report_review_agent) | 独占 |
| 用户追问 | **Agent** (clarification_agent) | 独占 |
| 可解释链路 | **Agent** (explanation_agent) | 独占 |

### 7.3 EU SCC

| 判断项 | 拥有者 | Agent 角色 |
|--------|:---:|------|
| Module 匹配 | **规则** (`validate_module_selection`) | 不参与 |
| 标准条款偏差检测 | **规则** (削弱信号 regex) | Agent 语义级复核 |
| Annex 完整性 | **规则** (`review_annexes`) | Agent 补全字段 |
| 特殊类别数据误分类 | **规则** (健康关键词检测) | Agent 上下文分析 |
| TIA 缺失检测 | **规则** | 不参与 |
| 补充措施有效性 | **Agent** (如实现) | 独占 |
| 传输链推理 | **Agent** (如实现) | 独占 |
| 风险评分聚合 | **规则** (`score_scc_risk`) | 不参与 |

### 7.4 安全评估

| 判断项 | 拥有者 | Agent 角色 |
|--------|:---:|------|
| 路径再判断 | **禁用**（应消费上游 PathDiagnosisResult） | — |
| 输入归一 | **Agent** (`input_normalization`) | 独占 |
| 附件解析 | **Agent** (`attachment_parsing`) | 独占 |
| 数据分类 | **Agent** (`data_classification`) | 独占 |
| 法规引用校验 | **Agent** (`legal_citation`) | 独占 |
| 文书规划 | **Agent** (`document_planning`) | 独占 |
| 表达校准 | **Agent** (`expression_calibration`) | 独占 |
| 受控修复 | **Agent** (`controlled_repair`) | 独占 |
| Issue 分类（confirmed/suspected/default） | **规则** (issue_builder) | Agent 补充 |
| 风险等级最终计算 | **规则** | 不参与 |

### 7.5 CPRA

| 判断项 | 拥有者 | Agent 角色 |
|--------|:---:|------|
| 适用性阈值（收入/消费者数/收入占比） | **规则** (`check_applicability`) | 不参与 |
| 业务角色判定（business/sp/contractor） | **规则** (关键词匹配) | Agent 语义推理 |
| SPI + 高风险目的组合 | **规则** (类别匹配) | Agent 上下文推理 |
| 暗模式检测 | **规则** (consent_ui 字段) | Agent UI 分析 |
| 供应商合同条款完整性 | **Agent** (如实现) | 独占 |
| 法规引用绑定 | **Agent** (如实现) | 独占 |
| 跨材料一致性 | **Agent** (如实现) | 独占 |

### 7.6 BCR

| 判断项 | 拥有者 | Agent 角色 |
|--------|:---:|------|
| Checklist 5-state 判定 | **规则** (`BCRChecklistChecker`) | Agent 实质覆盖复核 |
| BCR 类型判定 | **规则** (标题/角色关键词) | Agent 语义推理 |
| 实体角色识别 | **Agent** (`actor_role_agent`) | 独占 |
| Onward Transfer 实质等同 | **Agent** (`onward_transfer_agent`) | 独占 |
| TIA 完整性 | **Agent** (`tia_reasoning_agent`) | 独占 |
| 附件证据覆盖 | **Agent** (`evidence_coverage_agent`) | 独占 |
| INCORRECT 状态检测 | **Agent** (`incorrect_status_agent`) | 独占 |
| 法规引用 grounding | **Agent** (`legal_grounding_agent`) | 独占 |
| 审批阻断复核 | **Agent** (`approval_risk_agent`) | 独占 |
| 整改建议 | **Agent** (`remediation_agent`) | 独占 |
| 风险等级最终计算 | **规则** | 不参与 |

### 7.7 DPIA

| 判断项 | 拥有者 | Agent 角色 |
|--------|:---:|------|
| DPIA 触发信号检测 | **规则** (`need_detector.py`) | 不参与 |
| DPIA 触发理由解释 | **Agent** (如实现) | 独占 |
| 处理活动描述 | **Agent** (如实现) | 独占 |
| 必要性与相称性 | **Agent** (如实现) | 独占 |
| 风险评估矩阵 | **Agent** (如实现) | 独占 |
| 措施映射 | **Agent** (如实现) | 独占 |
| DPO 意见 | **Agent** (如实现) | 独占 |

### 7.8 文档专项审查

| 判断项 | 拥有者 | Agent 角色 |
|--------|:---:|------|
| 文档类型识别 | **规则** (DocumentClassifier) | Agent 兜底 |
| 条款分类（23 种 ClauseType） | **规则** (关键词 + LLM 兜底) | Agent 兜底 |
| 缺失项检测 | **规则** (MissingItemChecker) | Agent 补充 |
| DSL 规则 | **规则** | 不参与 |
| 隐含出境场景识别 | **Agent** (`scenario_facts_agent`) | 独占 |
| 数据类型敏感性识别 | **Agent** (`data_sensitivity_agent`) | 独占 |
| 标准合同强制条款审查 | **Agent** (`scc_mandatory_clause_agent`) | 独占 |
| 隐私政策告知矩阵 | **Agent** (`privacy_notice_matrix_agent`) | 独占 |
| 跨文档语义一致性 | **Agent** (`cross_doc_semantic_agent`) | 独占 |
| 法规绑定 | **Agent** (`legal_binding_agent`) | 独占 |
| 修改条款生成 | **Agent** (`revision_drafting_agent`) | 独占 |
| 审查边界与追问 | **Agent** (`review_boundary_agent`) | 独占 |
| 报告质检 | **Agent** (`report_qa_agent`) | 独占 |

---

## 八、边界违规判定标准

### 8.1 违规等级

```text
BLOCKER 违规——代码不能合入：
  - Agent 直接设定了 recommended_path
  - Agent 直接设定了 overall_rating
  - Agent 删除了规则引擎的 finding
  - Agent 在报告中使用了 forbidden_expressions
  - Agent 将 planned 写成 implemented

HIGH 违规——必须在下一个 commit 修复：
  - Agent 输出未带 confidence 字段
  - Agent 输出 confidence < 0.65 但进入了规则输入
  - Agent 生成的 FactItem 缺少 source_ref
  - Agent 将 user_claim_only 事实写成确认句

MEDIUM 违规——本周内修复：
  - Agent 接入位置与宪章规定的顺序不一致
  - Agent 未实现 fallback 降级路径
  - Agent 输出未写入 Trace
```

### 8.2 代码审查检查点

```text
每次 PR 涉及 Agent 代码时，审查者必须检查：

[ ] Agent 是否修改了 recommended_path？
[ ] Agent 是否修改了 overall_rating？
[ ] Agent 是否删除了规则引擎产生的 finding？
[ ] Agent 输出是否包含 confidence？
[ ] Agent 输出是否包含 source_ref？
[ ] Agent 是否有 fallback 路径？
[ ] Agent 的接入位置是否符合本模块的边界清单？
[ ] 报告中是否出现了 forbidden_expressions？
[ ] 报告是否将 user_claim_only 事实写成了确认句？
```

---

## 九、开发 Checklist

### 9.1 新增规则时

```
[ ] 该规则是否属于不可 Agent 化的判断？（参见第三条）
[ ] 如是，在规则函数上加 @inalienable_rule 装饰器（或注释）
[ ] 规则输出是否包含 rule_id + conditions + consequences？
[ ] 规则是否支持全量扫描（不只第一条命中即返回）？
[ ] 规则输出是否进入 Trace？
```

### 9.2 新增 Agent 时

```
[ ] 该 Agent 的职责是否在本宪章第四条允许的范围内？
[ ] Agent 是否只会追加 finding，不会删除规则 finding？
[ ] Agent 输出是否包含 confidence 字段？
[ ] Agent 是否有 fallback 降级路径？
[ ] Agent 接入位置是否在本模块边界清单（第七条）中登记？
[ ] Agent 输出是否写入 Trace？
[ ] 是否在 service.py 中添加了注释，引用本宪章的条款号？
```

### 9.3 新增报告模板时

```
[ ] 报告中的每个正面结论是否至少有一条 evidence_status ≥ documented_evidence 的 FactItem？
[ ] 报告是否包含 forbidden_expressions 中的表达？
[ ] 报告是否区分了 confirmed_issue / suspected_issue / default_review_item 的表达方式？
[ ] 是否包含审查边界说明？
[ ] 是否包含免责声明？
```

---

## 十、附：典型违规案例

### 案例 1：Agent 僭主路径判断

```python
# ❌ 违规
def generate_report(self, payload):
    # Agent 直接决定了路径
    path = self.path_agent.decide(payload)  # ← BLOCKER 违规
    if path == "security_assessment":
        return self.generate_security_assessment(payload)

# ✅ 正确
def generate_report(self, payload):
    # 规则引擎做路径判断
    rule_result = self.rule_engine.evaluate(payload)
    path = rule_result.recommended_path  # ← 规则引擎输出

    # Agent 给辅助判断
    agent_suggestion = self.path_agent.suggest(payload, rule_result)
    # agent_suggestion 只记录在 trace 中，不覆盖 rule_result
```

### 案例 2：Agent 降级 HIGH 风险

```python
# ❌ 违规
def review_finding(self, finding):
    if finding.severity == "HIGH":
        agent_view = self.risk_agent.reason(finding)
        if agent_view.risk == "MEDIUM":
            finding.severity = "MEDIUM"  # ← HIGH 违规：Agent 降级了规则判断

# ✅ 正确
def review_finding(self, finding):
    if finding.severity == "HIGH":
        agent_view = self.risk_agent.reason(finding)
        # 规则结果不变，Agent 结果作为补充上下文
        finding.agent_notes = agent_view.explanation
        # 如果 agent confidence 很高且严重分歧，写入 trace
        trace.log("agent_rule_divergence", {
            "rule_severity": "HIGH",
            "agent_view": agent_view.risk,
            "agent_confidence": agent_view.confidence,
        })
```

### 案例 3：Agent 编造法规引用

```python
# ❌ 违规
def bind_law(self, issue):
    prompt = f"为以下问题找到适用的法律条文：{issue.description}"
    law_text = self.llm.complete(prompt)  # ← BLOCKER 违规：Agent 可能 hallucinate 法条
    issue.legal_basis = law_text

# ✅ 正确
def bind_law(self, issue):
    # 只从 RAG 检索结果中选择
    rag_results = self.retriever.search(issue.category, issue.description)
    selected = self.grounding_agent.select(issue, rag_results)
    # selected 中的每条 citation 都来自 rag_results，不新增
    issue.legal_basis = [r.source_title + " " + r.article for r in selected]
```

### 案例 4：Agent 把用户声称写成确认事实

```python
# ❌ 违规
# 用户的 FactItem (evidence_status="user_claim_only"):
#   "接收方具备完善的安全保障能力"
# 报告生成：
context = f"境外接收方具备完善的数据安全保障能力。"  # ← HIGH 违规

# ✅ 正确
# 根据 ExpressionStrategy:
#   claim: "接收方具备安全保障能力"
#   fact_status: "user_claim_only"
#   allowed: "用户已说明境外接收方具备一定安全保障能力"
#   forbidden: ["境外接收方已充分具备安全保障能力", "已通过安全审计确认"]
context = (
    "用户已说明境外接收方具备一定数据安全保障能力，"
    "但当前材料尚未提供认证报告、审计结论或安全制度文件，"
    "建议在正式申报前补充相关证明材料。"
)
```

### 案例 5：Agent 缺少 Fallback 导致管道断裂

```python
# ❌ 违规
def extract_facts(self, document):
    agent_result = self.fact_agent.extract(document)  # 如果 LLM 挂了，这里抛异常
    return agent_result.facts  # ← MEDIUM 违规：没有 fallback

# ✅ 正确
def extract_facts(self, document):
    try:
        agent_result = self.fact_agent.extract(document)
        return agent_result.facts, False  # fallback_used=False
    except Exception as e:
        trace.log("agent_fallback", {"agent": "FactExtractionAgent", "error": str(e)})
        # 降级到规则提取器
        rule_result = self.attachment_extractor.extract(document)
        return rule_result.facts, True  # fallback_used=True
```

---

## 附录 A：@inalienable_rule 装饰器规范

```python
# 建议在 backend/common/workflow/rules.py 中定义
import functools

def inalienable_rule(rule_id: str, reason: str):
    """标记一个规则函数为'不可 Agent 化的判断'。

    被标记的函数的返回值不能被任何 Agent 覆盖或修改。
    Agent 只能读取、解释、补充上下文。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper._inalienable = True
        wrapper._rule_id = rule_id
        wrapper._reason = reason
        return wrapper
    return decorator

# 使用示例：
@inalienable_rule(
    rule_id="ciio",
    reason="CIIO 判定是法律定义的确定性判断，Agent 不能替代"
)
def check_ciio(is_ciio: bool) -> bool:
    return is_ciio
```

## 附录 B：宪章修订程序

```text
1. 任何人对宪章内容有异议 → 在 PR 中提出具体条款号和修改建议
2. 架构审查者评估修改是否削弱规则引擎的阻断权
3. 如果削弱 → 拒绝，除非提供充分的合规理由和法律意见支撑
4. 如果增强 → 接受，更新版本号
5. 每次修订在 Git 中保留完整 diff，commit message 引用条款号
```
