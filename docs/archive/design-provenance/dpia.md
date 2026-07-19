## 1. **附件解析 & 事实抽取（CPRAAttachmentExtractor）**

### 当前问题

* 仅使用正则/关键词标志化提取。
* 复杂隐私政策、多条 opt-out、SPI声明、合同条款可能被遗漏。
* 只取前160字符摘要，缺乏上下文理解。

### Agent 能解决的点

* **自然语言理解 + 结构化事实生成**：Agent 可以读取整份文档，识别所有 CPI / SPI / DSR / opt-out /合同条款条目，并自动生成结构化数据。
* **交叉验证**：Agent 可以把提取的条款与数据映射、供应商信息、UI字段进行一致性验证。
* **增益效果**：

  * 提升附件解析完整性。
  * 避免关键法规条款被遗漏。
  * 输出直接可供 gap_rules 消费的结构化事实，无需人工干预。

---

## 2. **数据映射 & SPI用途分析（check_data_mapping + check_spi）**

### 当前问题

* SPI + 高风险用途判断依赖结构化字段输入。
* 用户输入不完整或漏填时，规则引擎无法识别。
* 出售/共享、跨上下文广告等逻辑缺少推理能力。

### Agent 能解决的点

* **动态推理**：Agent 可结合自由文本、附件、合同条款、数据映射自动推断哪些数据属于 SPI、高风险目的是否合理、是否存在超范围使用。
* **用途判断**：根据业务描述自动识别广告/营销/保险推荐/跨情境广告等高风险使用。
* **增益效果**：

  * 弥补结构化字段缺失时的判断盲区。
  * 自动生成风险理由与法规引用，提升 gap_item 质量。
  * 对复杂组合条件（SPI + 高风险用途 + 第三方合同）进行逻辑推理。

---

## 3. **消费者权利机制评估（check_dsr）**

### 当前问题

* 规则仅检查渠道数量、免费电话、响应天数。
* 无法评估实际可行性、入口易用性、条款覆盖完整性。

### Agent 能解决的点

* **模拟消费者视角执行DSR请求**：

  * Agent 可以模拟提交请求，验证是否可行、响应是否合规。
* **智能核对条款与事实**：

  * 检查政策文本、UI字段、合同条款是否覆盖访问、删除、更正、opt-out、limit-SPI。
* **增益效果**：

  * 提供真实可行性验证，而非静态规则检查。
  * 自动生成用户友好描述和整改建议。

---

## 4. **出售/共享 + Opt-Out 合规（check_opt_out）**

### 当前问题

* 检查依赖标记或文本关键词。
* 对 GPC、标准化链接、跨上下文广告、未成年人数据无法做深度判断。

### Agent 能解决的点

* **交叉验证多源信息**：Agent 可以整合数据映射、合同条款、附件文本、UI，推断哪些出售/共享行为可能违反 CPRA。
* **动态合规建议生成**：针对具体情形给出整改措施。
* **增益效果**：

  * 精准识别未规范 opt-out 行为。
  * 结合实际 UI / 第三方合同生成高可信度结论。

---

## 5. **供应商管理 & 合同条款（check_vendor）**

### 当前问题

* 规则只检查 DPA 存在与否，缺乏条款细化。
* 复杂多角色、多条约束场景无法自动判断。

### Agent 能解决的点

* **合同文本理解**：

  * Agent 可以解析供应商合同，识别条款是否满足 CPRA 要求（禁止出售/共享、协助DSR、审计、删除/返还）。
* **跨域逻辑推理**：

  * 将合同条款与数据映射和 SPI 使用场景对应，识别潜在冲突。
* **增益效果**：

  * 减少人工审查，自动标记不合规条款。
  * 输出直接可用的整改建议。

---

## 6. **暗模式 & 同意界面评估（check_dark_patterns）**

### 当前问题

* 依赖结构化字段，缺乏 UI截图或文本分析。
* 无法检测复杂暗模式（隐藏按钮、捆绑同意、预选选项、混淆语言）。

### Agent 能解决的点

* **视觉+文本分析**：

  * Agent 可以解析界面截图或 HTML，识别暗模式、按钮突出性、捆绑选项。
* **规则验证**：

  * 与 SPI、数据用途结合，推理同意有效性。
* **增益效果**：

  * 提供比人工填表更精确的暗模式检测。
  * 与 SPI / opt-out / DSR 结合，直接输出合规风险等级。

---

## 7. **法规检索与证据关联（CPRALegalRetriever）**

### 当前问题

* RAG 查询固定，缺乏动态与输入事实的匹配。
* 法规引用与 gap_item 不总是精准对应。

### Agent 能解决的点

* **动态法规检索与匹配**：

  * 根据每条 gap_item 生成上下文化 query，检索最相关条文。
  * 生成 rationale 和引用 snippets。
* **增益效果**：

  * 提升报告可信度和可复核性。
  * 每条 gap_item 自动带法规依据，无需人工匹配。

---

### ✅ 总结：适合加 Agent 的关键环节

| 模块              | 加 Agent 的作用            | 增益 / 效果        |
| --------------- | ---------------------- | -------------- |
| 附件解析            | NLP解析隐私政策、SOP、数据映射、合同  | 自动生成结构化事实，避免遗漏 |
| SPI + 数据映射      | 推理SPI用途和风险             | 高风险场景自动识别      |
| DSR评估           | 模拟消费者请求、核对条款           | 可验证可行性，生成整改建议  |
| 出售/共享 + Opt-Out | 跨附件、UI、合同推理            | 准确识别违规出售/共享行为  |
| 供应商合同           | 自动解析合同条款、角色、约束         | 自动标注不合规条款，减少人工 |
| 暗模式             | 分析UI文本或截图              | 检测预选、捆绑、拒绝不突出等 |
| 法规检索            | 动态 RAG / 法规匹配 gap_item | 提高证据可信度与可复核性   |

---
下面补上 **DPIA 加 Agent 后的具体处理逻辑**。重点不是“多加几个 Agent 名字”，而是说明：

```text
Agent 放在哪一步
输入什么
处理什么
输出什么
输出如何进入后续 Pipeline
如何避免 Agent 乱判断、乱生成、乱引用
```

DPIA 预期本身是按“识别需求 → 描述处理活动 → 咨询过程 → 必要性与相称性 → 风险识别与评估 → 降低风险措施 → 签署与记录”生成草案，这几个模块分别映射 GDPR 第 35 条、WP248/EDPB 指南、DPO 咨询、风险评估和问责制要求。 当前实现有 assessment 式 Pipeline 基础：ProfileExtractor、Fact Builder、RAG、Issue Builder、Evidence Builder、Per-Issue RAG、ContextPack、ChapterGenerator、ConsistencyChecker、Repair、Renderer 等。 DPIA Agent 的合理做法是复用这些工程底座，但换成 DPIA 专属 Agent 链路。

---

# 一、DPIA Agent 总体接入位置

## 当前基础 Pipeline

当前代码基础大概是：

```text
Request
→ ProfileExtractor
→ FactBuilder
→ RAG
→ IssueBuilder
→ EvidenceBuilder
→ Per-Issue RAG
→ ContextPack
→ ChapterGenerator
→ ConsistencyChecker
→ Repair
→ Renderer
```

## 加 Agent 后的 DPIA 预期 Pipeline

建议改成：

```text
DPIARequest
        ↓
DPIAFactBuilder
        ↓
DPIANeedDetector（规则）
        ↓
DPIA Need Agent
        ↓
Processing Activity Agent
        ↓
Necessity & Proportionality Agent
        ↓
Risk Assessment Agent
        ↓
Mitigation Mapping Agent
        ↓
DPO / Prior Consultation Agent
        ↓
Legal Grounding + Citation Builder
        ↓
GenerationBasisPack Builder
        ↓
External DPIA Draft Agent
        ↓
Internal Review Agent
        ↓
DPIA Consistency Agent
        ↓
Repair Agent
        ↓
Renderer
```

这里要注意：

```text
规则层负责“先判定基础事实和触发信号”；
Agent 层负责“综合解释、补充推理、生成结构化判断”；
Renderer 负责“输出 docx / md / json / xlsx / zip”。
```

---

# 二、Agent 1：DPIA Need Agent

## 1. 现有问题

规则可以判断是否命中：

```text
自动化决策
大规模处理
特殊类别数据
系统性监控
新技术
弱势群体
数据匹配
权利影响
```

但规则只能给出“命中项”，无法写出高质量的 DPIA 触发理由。

例如 AI 招聘系统不仅是“自动化决策”，还涉及候选人画像、大规模处理、视频面试分析、特殊类别数据推断、就业机会影响。测试案例中也明确要求系统要说明这些因素共同构成 DPIA 触发理由。

## 2. 期望目标

生成一份结构化的 DPIA 触发判断：

```json
{
  "dpia_required": true,
  "trigger_reasons": [
    "automated_decision_making",
    "large_scale_processing",
    "special_category_inference"
  ],
  "explanation": "...",
  "legal_basis_refs": [
    "GDPR_ART35",
    "WP248_HIGH_RISK_CRITERIA"
  ],
  "confidence": "HIGH"
}
```

## 3. 具体处理逻辑

```text
Step A：规则层先识别 high-risk signals
Step B：Agent 读取 signals + 用户事实
Step C：Agent 生成“为什么需要 DPIA”的解释
Step D：LegalGrounding 绑定 GDPR Art 35 / WP248
Step E：写入 generation_basis_pack.section["need_identification"]
```

## 4. 输入

```json
{
  "project_profile": {
    "project_name": "AI 招聘筛选与候选人评估系统",
    "project_goal": "...",
    "data_categories": ["简历", "视频面试", "在线测试", "面部特征数据"],
    "data_subject_count": "超过10万人/年"
  },
  "rule_signals": {
    "automated_decision_making": true,
    "large_scale_processing": true,
    "special_category_inference": true,
    "systematic_monitoring": true
  },
  "legal_candidates": [
    "GDPR Article 35",
    "WP29 WP248 rev.01"
  ]
}
```

## 5. 输出

```json
{
  "agent_name": "DPIANeedAgent",
  "dpia_required": true,
  "trigger_reasons": [
    {
      "type": "automated_decision_making",
      "fact_refs": ["FACT-automated-ranking"],
      "reason": "系统对候选人进行自动化评分和排名，可能影响其获得面试或就业机会。"
    },
    {
      "type": "large_scale_processing",
      "fact_refs": ["FACT-data-subject-count"],
      "reason": "预计每年处理超过10万名求职者数据，具有大规模处理特征。"
    }
  ],
  "draft_text": "该项目因涉及自动化评估、大规模处理求职者数据，并可能通过视频面试间接推断特殊类别数据，可能对候选人的就业机会、公平待遇和透明度权利产生高风险，因此应在上线前开展 DPIA。"
}
```

## 6. 后续怎么用

```text
draft_text
→ DPIA 草案 “1. 识别需求”

trigger_reasons
→ risk_matrix 初始化

legal_basis_refs
→ legal_grounding / citation
```

---

# 三、Agent 2：Processing Activity Agent

## 1. 现有问题

DPIA 的“描述处理活动”不能只是摘要。它要对应 GDPR 第 35(7)(a)，系统性描述处理操作及目的。功能说明明确，这一模块应整合数据流、数据类型、数据量、保留期和跨境传输。

当前如果只靠字段拼接，容易漏掉：

```text
数据来源
系统流向
第三方参与方
模型训练位置
保留期限
跨境传输节点
数据主体类别
```

## 2. 期望目标

把用户输入和附件解析成一个处理活动包：

```json
{
  "processing_steps": [],
  "data_sources": [],
  "data_categories": [],
  "data_subjects": [],
  "recipients": [],
  "retention_periods": [],
  "cross_border_transfer": {},
  "ambiguities": []
}
```

## 3. 具体处理逻辑

```text
Step A：读取表单字段 + 附件摘要 / 数据流程图摘要
Step B：Agent 抽取数据流节点
Step C：Agent 区分数据来源、处理环节、接收方、存储位置
Step D：Agent 标出模糊项
Step E：输出 processing_activity_pack
```

## 4. 输入

```json
{
  "raw_inputs": {
    "data_flow": "求职者→招聘网站/第三方平台→AWS欧盟服务器→AI模型→HR系统",
    "data_types": ["身份信息", "视频/音频记录", "在线测试答案", "面部特征数据"],
    "retention": "未成功候选人6个月，成功候选人转员工档案",
    "cross_border": "美国团队可能访问训练数据进行模型优化"
  },
  "attachments": [
    {
      "type": "data_flow_diagram",
      "summary": "显示数据从求职者进入招聘平台并进入欧盟 AWS 服务器"
    }
  ]
}
```

## 5. 输出

```json
{
  "agent_name": "ProcessingActivityAgent",
  "processing_steps": [
    {
      "step": "数据收集",
      "actor": "TechGiant EU",
      "data_sources": ["招聘网站", "LinkedIn", "视频面试平台"],
      "data_categories": ["简历", "视频/音频", "在线测试答案"]
    },
    {
      "step": "模型分析与评分",
      "actor": "AI 招聘系统",
      "processing": "自动生成候选人综合评分和排名",
      "risk_notes": ["可能构成画像和自动化评估"]
    },
    {
      "step": "HR 复核",
      "actor": "HR",
      "processing": "根据模型结果作最终决策"
    }
  ],
  "cross_border_transfer": {
    "exists": true,
    "destination": "美国",
    "description": "部分训练数据可能传至美国团队用于模型优化"
  },
  "ambiguities": [
    "美国团队是否可访问原始求职者数据仍需明确",
    "面部特征数据是否会被保留未明确"
  ]
}
```

## 6. 后续怎么用

```text
processing_activity_pack
→ “2. 描述处理活动”
→ necessity_agent 输入
→ risk_assessment_agent 输入
→ evidence_chain 输入
```

---

# 四、Agent 3：Necessity & Proportionality Agent

## 1. 现有问题

必要性与相称性是 DPIA 中最不适合纯规则的部分。功能说明明确，该模块对应 GDPR 第 35(7)(b)，要评估处理是否为实现合法目的所必需，是否遵循数据最小化。

如果没有 Agent，系统容易写成：

```text
用户认为该处理是必要的。
```

但合格 DPIA 应该指出：

```text
哪些处理有必要；
哪些处理必要性不足；
有没有低风险替代方案；
哪些数据项应删除或弱化。
```

## 2. 期望目标

输出必要性和相称性分析：

```json
{
  "necessary_processing": [],
  "questionable_processing": [],
  "excessive_data_items": [],
  "less_intrusive_alternatives": [],
  "data_minimisation_recommendations": []
}
```

## 3. 具体处理逻辑

```text
Step A：读取 project_goal + processing_activity_pack
Step B：按每个处理环节判断目的相关性
Step C：识别高侵入性数据项
Step D：提出替代方案
Step E：输出 necessity_findings
```

## 4. 输入

```json
{
  "project_goal": "提高招聘效率，减少人工偏见，识别适合岗位候选人",
  "processing_activity_pack": "...",
  "lawful_basis": ["同意", "合同履行", "合法利益"],
  "data_categories": ["简历", "视频面试", "面部特征数据", "打字/点击行为数据"]
}
```

## 5. 输出

```json
{
  "agent_name": "NecessityProportionalityAgent",
  "necessary_processing": [
    {
      "processing": "简历、工作经历和在线测试分析",
      "reason": "与岗位匹配和候选人能力评估直接相关。"
    }
  ],
  "questionable_processing": [
    {
      "processing": "面部表情分析",
      "reason": "与岗位胜任力之间的必要关联不足，并可能推断健康状况、情绪状态或种族等敏感信息。"
    }
  ],
  "less_intrusive_alternatives": [
    "仅分析语言内容和回答质量",
    "提供非视频申请渠道",
    "取消微表情分析功能"
  ],
  "draft_text": "自动化筛选对于处理大规模申请具有一定必要性，但面部表情分析的必要性不足，且可能导致特殊类别数据推断风险。建议取消微表情分析，仅保留与岗位能力直接相关的语言内容和测试结果分析。"
}
```

## 6. 后续怎么用

```text
questionable_processing
→ IssueBuilder 生成 proportionality_weak issue

less_intrusive_alternatives
→ mitigation_mapper 输入

draft_text
→ “4. 必要性与相称性”
```

---

# 五、Agent 4：Risk Assessment Agent

## 1. 现有问题

风险评估是 DPIA 的核心。功能说明明确，“识别与评估风险”与“降低风险的措施”共同满足 GDPR 第 35(7)(c)(d)。

规则可以识别几个风险标签，但难以评估：

```text
影响哪些权利
可能性
严重性
综合等级
风险原因
与处理活动的关系
```

例如智慧城市案例的风险重点是功能蔓延、重识别、歧视性规划、大规模监控和寒蝉效应。 这些风险不能只靠关键词判断。

## 2. 期望目标

输出风险矩阵：

```json
{
  "risks": [
    {
      "risk_id": "",
      "risk_name": "",
      "affected_rights": [],
      "likelihood": "",
      "impact": "",
      "overall_level": "",
      "reasoning": "",
      "related_facts": [],
      "related_legal_basis": []
    }
  ]
}
```

## 3. 具体处理逻辑

```text
Step A：读取 processing_activity_pack
Step B：读取 dpia_need_pack 和 necessity_findings
Step C：按风险类别生成候选风险
Step D：评估 likelihood / impact / overall_level
Step E：输出 risk_matrix
```

## 4. 输入

```json
{
  "dpia_need_pack": "...",
  "processing_activity_pack": "...",
  "necessity_findings": "...",
  "user_identified_risks": [
    "歧视性决策",
    "数据泄露",
    "决策不透明"
  ],
  "legal_grounding": [
    "GDPR_ART35",
    "GDPR_ART22"
  ]
}
```

## 5. 输出

```json
{
  "agent_name": "RiskAssessmentAgent",
  "risk_matrix": [
    {
      "risk_id": "RISK-ai-discrimination",
      "risk_name": "算法歧视性决策风险",
      "description": "训练数据偏差可能导致特定性别、年龄、种族或残障群体被系统性低估。",
      "affected_rights": ["公平就业机会", "非歧视权利", "透明度权利"],
      "likelihood": "MEDIUM",
      "impact": "HIGH",
      "overall_level": "HIGH",
      "related_processing_steps": ["模型分析与评分"],
      "reasoning": "系统自动评分可能影响候选人是否进入面试，且模型训练数据偏差可能放大既有招聘歧视。"
    },
    {
      "risk_id": "RISK-special-category-inference",
      "risk_name": "特殊类别数据推断风险",
      "description": "视频面试和面部特征分析可能间接推断健康状况、种族或情绪状态。",
      "likelihood": "MEDIUM",
      "impact": "HIGH",
      "overall_level": "HIGH"
    }
  ]
}
```

## 6. 后续怎么用

```text
risk_matrix
→ “5. 识别与评估风险”
→ mitigation_mapping_agent 输入
→ prior_consultation_agent 输入
→ risk_matrix.xlsx/json
```

---

# 六、Agent 5：Mitigation Mapping Agent

## 1. 现有问题

DPIA 不能只列措施。必须证明：

```text
每个高风险都有对应措施；
措施具体；
措施可验证；
措施能降低风险；
剩余风险如何。
```

测试案例三要求健康保险项目必须有冷静期、退出机制、替代激励方案、禁止惩罚性定价、聚合共享等具体措施。

## 2. 期望目标

输出风险—措施映射表：

```json
{
  "mitigation_plan": [
    {
      "risk_id": "",
      "measures": [],
      "residual_risk": "",
      "additional_actions_required": []
    }
  ]
}
```

## 3. 具体处理逻辑

```text
Step A：读取 risk_matrix
Step B：读取用户已提供措施
Step C：逐个 HIGH/MEDIUM 风险匹配措施
Step D：判断措施状态：planned / implemented / missing
Step E：评估 residual risk
Step F：输出 mitigation_plan
```

## 4. 输入

```json
{
  "risk_matrix": "...",
  "user_measures": [
    "每季度公平性审计",
    "解释功能上线",
    "取消面部表情分析",
    "人工复核机制"
  ],
  "reference_measures": [
    "data minimisation",
    "human review",
    "transparency notice",
    "bias audit"
  ]
}
```

## 5. 输出

```json
{
  "agent_name": "MitigationMappingAgent",
  "mitigation_plan": [
    {
      "risk_id": "RISK-ai-discrimination",
      "measures": [
        {
          "measure": "每季度开展公平性审计，并按性别、年龄、民族等维度检查模型输出差异。",
          "status": "planned",
          "effect": "降低训练数据偏差导致的系统性歧视风险",
          "verification": "审计报告和模型版本记录"
        },
        {
          "measure": "对候选人提供人工复核渠道。",
          "status": "planned",
          "effect": "降低自动化评分对个人权利产生不可纠正影响的风险"
        }
      ],
      "residual_risk": "MEDIUM",
      "additional_actions_required": [
        "上线前完成首次公平性审计",
        "明确人工复核处理时限"
      ]
    }
  ]
}
```

## 6. 后续怎么用

```text
mitigation_plan
→ “6. 降低风险措施”
→ DPO / Prior Consultation Agent
→ mitigation_plan.xlsx/json
```

---

# 七、Agent 6：DPO / Prior Consultation Agent

## 1. 现有问题

签署与记录不是末尾客套话。功能说明明确，该模块体现 GDPR 问责制，记录 DPIA 负责人和 DPO 意见是证明履行 DPIA 义务的关键证据。

DPO 意见要进入结论，并影响是否可以上线、是否需要监管事先咨询。

## 2. 期望目标

输出：

```json
{
  "dpo_position": "",
  "conditions": [],
  "prior_consultation_recommended": true,
  "reason": ""
}
```

## 3. 具体处理逻辑

```text
Step A：读取 risk_matrix
Step B：读取 mitigation_plan
Step C：判断是否仍有 HIGH residual risk
Step D：读取 DPO 意见
Step E：判断 approval / conditional_approval / objection
Step F：判断是否建议 GDPR Art 36 prior consultation
```

## 4. 输入

```json
{
  "risk_matrix": "...",
  "mitigation_plan": "...",
  "dpo_opinion": "DPO 要求上线前完成公平性审计，并确保解释功能上线。",
  "remaining_high_risks": ["RISK-special-category-inference"]
}
```

## 5. 输出

```json
{
  "agent_name": "DPOPriorConsultationAgent",
  "dpo_position": "conditional_approval",
  "conditions": [
    "取消或停用面部表情分析功能",
    "完成首次公平性审计",
    "上线候选人解释和人工复核机制"
  ],
  "prior_consultation_recommended": false,
  "reason": "若上述措施在上线前落实，剩余风险可降至中等；如措施不能落实，则应重新评估是否需要监管机构事先咨询。",
  "draft_text": "DPO 对项目上线持有条件同意意见，前提是完成公平性审计、解释功能和人工复核机制，并取消面部表情分析。"
}
```

## 6. 后续怎么用

```text
dpo_decision_pack
→ “7. 签署与记录”
→ 结论章节
→ ConsistencyChecker
```

如果输出：

```text
prior_consultation_recommended = true
```

则 DPIA 草案结论必须写：

```text
建议在项目实施前考虑依据 GDPR 第 36 条向监管机构进行事先咨询。
```

---

# 八、Agent 7：External DPIA Draft Agent

## 1. 现有问题

普通 ChapterGenerator 可以写正文，但 DPIA 草案需要强模板控制，不能自由发挥。

## 2. 期望目标

按 ICO DPIA 模板结构生成可编辑草案。功能说明中明确系统输出为 `ICO_DPIA_Template.docx` 类型草案。

## 3. 具体处理逻辑

```text
Step A：读取 generation_basis_pack
Step B：按 7 个 DPIA 模板章节逐章生成
Step C：只允许使用 citation_registry 中的 citation_id
Step D：对 user_claim_only 事实使用保守表达
Step E：输出 external_dpia_draft
```

## 4. 输入

```json
{
  "section_pack": {
    "section_id": "risk_assessment",
    "facts": [],
    "risk_matrix": [],
    "legal_grounding": [],
    "citations": [],
    "writing_strategy": []
  }
}
```

## 5. 输出

```json
{
  "chapters": [
    {
      "section_id": "risk_assessment",
      "title": "5. 识别与评估风险",
      "content": "...",
      "citations": ["CIT-EU-GDPR-ART35-P01"]
    }
  ]
}
```

## 6. Prompt 关键约束

```text
你生成的是 DPIA 草案，不是法律意见书。
必须严格按照模板章节输出。
不得编造事实。
不得编造法规引用。
不得将 planned measure 写成 implemented measure。
不得写“风险已完全消除”。
高风险必须说明可能性、影响和缓解措施。
```

---

# 九、Agent 8：Internal Review Agent

## 1. 现有问题

对外 DPIA 草案语言正式，用户不一定看得出真实风险。

## 2. 期望目标

生成内部 AI 检验文本，直接告诉用户：

```text
哪些风险最高
哪些措施还没落实
哪些只是用户自称
哪些内容不能写太满
是否建议暂缓上线
是否建议监管事先咨询
```

## 3. 具体处理逻辑

```text
Step A：读取 risk_matrix
Step B：读取 mitigation_plan
Step C：读取 dpo_decision_pack
Step D：读取 user_claim_only facts
Step E：输出 internal_ai_review.md
```

## 4. 输出结构

```text
一、总体风险判断
二、高风险问题
三、证据不足事项
四、计划措施与已落实措施差异
五、DPO 前置条件
六、是否建议暂缓上线
七、材料补充优先级
八、下一步整改建议
```

---

# 十、Agent 9：Consistency / Repair Agent

## 1. 现有问题

生成后必须检查，不然 LLM 可能漏风险、乱引用、过度正面。

## 2. 期望目标

专门检查 DPIA 草案是否合格。

## 3. 具体处理逻辑

```text
Step A：读取 DPIA 草案
Step B：读取 generation_basis_pack
Step C：读取 risk_matrix / mitigation_plan / dpo_decision_pack
Step D：检查一致性
Step E：若有 blocking issue，调用 Repair Agent
Step F：二次检查
Step G：输出 final draft 或 needs_manual_review
```

## 4. 检查项

```text
1. DPIA 触发理由是否覆盖全部 high-risk signals
2. 处理活动描述是否包含数据流、数据类型、数量、保留期、跨境情况
3. 必要性与相称性是否指出不必要 / 过度处理项
4. 每个 HIGH 风险是否有 mitigation
5. 每个 mitigation 是否有状态：planned / implemented
6. DPO 条件是否进入结论
7. residual HIGH risk 是否触发 Art 36 prior consultation 提示
8. 是否出现禁止表达
9. 是否编造 citation
10. 是否把 user_claim_only 写成已证实事实
```

## 5. Repair 规则

```text
缺少触发理由
→ 补写识别需求段落

HIGH 风险无措施
→ 在草案中标记“尚需补充措施”，不能写“已控制”

planned measure 被写成 implemented
→ 改为“计划采取 / 上线前应完成”

DPO 条件漏写
→ 追加到结论和签署记录

剩余高风险未提示 Art 36
→ 追加“建议考虑监管机构事先咨询”

引用缺失
→ 使用 citation_registry 补引用
```

---

# 十一、Agent 输出如何进入最终文件

最终每个 Agent 的产物不是孤立文本，而是进入统一包：

```json
{
  "dpia_need_pack": {},
  "processing_activity_pack": {},
  "necessity_findings": {},
  "risk_matrix": {},
  "mitigation_plan": {},
  "dpo_decision_pack": {},
  "external_dpia_draft": {},
  "internal_ai_review": {},
  "consistency_report": {}
}
```

Renderer 输出：

```text
DPIA草案.docx
DPIA草案.md
risk_matrix.json / xlsx
mitigation_plan.json / xlsx
dpia_need_assessment.json
processing_activity_description.json
necessity_proportionality.json
dpo_opinion.json
internal_ai_review.md
legal_grounding.json
citation_map.json
trace_manifest.json
zip
```

---

# 十二、最小可行 Agent 版本

不建议一开始做 9 个 Agent。可以分 3 阶段。

## 第一阶段：4 个核心 Agent

先做最有价值的：

```text
1. Necessity & Proportionality Agent
2. Risk Assessment Agent
3. Mitigation Mapping Agent
4. DPO / Prior Consultation Agent
```

这四个直接决定 DPIA 质量。

## 第二阶段：生成和检查 Agent

```text
5. External DPIA Draft Agent
6. Internal Review Agent
7. Consistency / Repair Agent
```

解决内外文本和生成质量。

## 第三阶段：前置理解 Agent

```text
8. DPIA Need Agent
9. Processing Activity Agent
```

提升输入理解和触发理由质量。

---

# 十三、最终推荐链路

```text
DPIARequest
        ↓
规则层：字段校验 + 高风险信号识别
        ↓
DPIA Need Agent
        ↓
Processing Activity Agent
        ↓
Necessity & Proportionality Agent
        ↓
Risk Assessment Agent
        ↓
Mitigation Mapping Agent
        ↓
DPO / Prior Consultation Agent
        ↓
LegalGrounding + CitationRegistry
        ↓
GenerationBasisPack
        ↓
External DPIA Draft Agent
        ↓
Internal Review Agent
        ↓
Consistency / Repair Agent
        ↓
Renderer
```

一句话总结：**DPIA 里 Agent 最应该负责“复杂判断和解释”：必要性与相称性、风险矩阵、措施匹配、DPO 条件、监管事先咨询、内部真实风险解释和生成后修复。规则和程序继续负责字段校验、模板映射、引用生成、RAG 检索和 docx 渲染。**
？
