# AI4Law 深度案例剖析：Prompt、规则、RAG、Fact/Issue/Evidence 全拆解

> **阅读前提**：本文档假设你已读过《系统全景架构与流程详解》和《底层引擎详解》。本文不做概述，直接以具体模块为案例，逐层拆解每一个技术细节的真实样貌。

---

## 目录

- [案例选择说明](#案例选择说明)
- [第一部分：Prompt 到底长什么样](#第一部分prompt-到底长什么样)
  - [1.1 重要数据判断代理的完整 Prompt](#11-重要数据判断代理的完整-prompt)
  - [1.2 个人信息分类代理的完整 Prompt](#12-个人信息分类代理的完整-prompt)
  - [1.3 豁免判断代理的完整 Prompt](#13-豁免判断代理的完整-prompt)
  - [1.4 AI 推测路径的完整 Prompt](#14-ai-推测路径的完整-prompt)
  - [1.5 规则解释生成的完整 Prompt](#15-规则解释生成的完整-prompt)
  - [1.6 报告摘要生成的完整 Prompt](#16-报告摘要生成的完整-prompt)
- [第二部分：规则到底怎么判](#第二部分规则到底怎么判)
  - [2.1 决策树的完整结构](#21-决策树的完整结构)
  - [2.2 规则匹配的逐字段逻辑](#22-规则匹配的逐字段逻辑)
  - [2.3 数据规范化的 6 条自动校正规则](#23-数据规范化的-6-条自动校正规则)
  - [2.4 重要数据启发式评分的完整算法](#24-重要数据启发式评分的完整算法)
  - [2.5 个人信息分类的完整决策逻辑](#25-个人信息分类的完整决策逻辑)
  - [2.6 豁免判断的 4 类信号检测](#26-豁免判断的-4-类信号检测)
  - [2.7 AI 推测的触发条件](#27-ai-推测的触发条件)
  - [2.8 规则判别优先级全景图](#28-规则判别优先级全景图)
- [第三部分：RAG 知识库在诊断模块中怎么组织和调用](#第三部分rag-知识库在诊断模块中怎么组织和调用)
- [第四部分：得理 API 在诊断模块中什么时候调用](#第四部分得理-api-在诊断模块中什么时候调用)
- [第五部分：Fact / Issue / Evidence 到底什么样](#第五部分fact--issue--evidence-到底什么样)
  - [5.1 FactItem 的真实案例](#51-factitem-的真实案例)
  - [5.2 IssueItem 的真实案例](#52-issueitem-的真实案例)
  - [5.3 EvidenceItem 的真实案例](#53-evidenceitem-的真实案例)
  - [5.4 三链串联：从事实到证据的完整追溯](#54-三链串联从事实到证据的完整追溯)

---

## 案例选择说明

本文用两个模块做深度拆解：

- **路径诊断模块（diagnosis）**：展示 Prompt、规则引擎、Agent 的全部细节。这是系统中最"规则驱动"的模块，每一个判断步骤都可以精确追溯到具体的代码逻辑。
- **安全自评估模块（assessment）**：展示 Fact、Issue、Evidence 的完整形态和三链串联关系。这是系统中最"数据驱动"的模块，中间产物体系最完整。

这两个模块覆盖了系统的全部核心技术要素。

---

# 第一部分：Prompt 到底长什么样

路径诊断模块中一共有 **5 个 LLM 调用点**，每个都有完整的 System Prompt 和 User Prompt。下面是每个调用的完整 Prompt 原文。

## 1.1 重要数据判断代理的完整 Prompt

**触发条件**：用户对"是否涉及重要数据"回答了"不确定"。

**代理执行前，先跑一套启发式评分**（见本文 2.4 节），得出一个初步结论（例如"可能是重要数据，得分 5 分"），然后将启发式结论连同原始数据一起送给 LLM 做精化判断。

**System Prompt**（所有诊断代理共用）：

```text
你是一名精通中国数据跨境合规的资深律师，深度掌握《个人信息保护法》
《数据安全法》《数据出境安全评估办法》《促进和规范数据跨境流动规定》
及相关部门规章。请根据用户提供的业务信息，辅助判断关键合规事实。
输出 ONLY 有效 JSON，不要任何解释性文字。
当事实不足以确定时，明确标注为低置信度并给出需补充的信息。
```

**User Prompt**（以某金融科技公司为例）：

```text
Determine if the following data may constitute "重要数据" under Chinese law.

Industry: 金融科技
Data description: 向新加坡母公司传输交易数据用于统一风控 用户交易流水 用户基本身份信息
Data types: ['用户姓名', '身份证号', '银行卡号', '交易金额', '交易时间', '手机号码']
Purpose: 向新加坡母公司传输交易数据用于统一风险控制管理
Volume: 100-1000万条
Heuristic result: likely_important_data (score=5, reasons=['用户明确标注涉及重要数据', '行业属于金融高敏领域', '数据规模达千万/百万级'])

Return JSON:
{
  "assessment_type": "important_data",
  "result": "likely_important_data|possible_important_data|unlikely_important_data|insufficient_information",
  "suggested_answer": "yes|no|unknown",
  "confidence": 0.0-1.0,
  "matched_features": ["feature1", "feature2"],
  "legal_basis": ["《数据安全法》第21条", "..."],
  "recommended_user_message": "<one sentence guidance>"
}
```

**LLM 可能返回的 JSON**：

```json
{
  "assessment_type": "important_data",
  "result": "likely_important_data",
  "suggested_answer": "yes",
  "confidence": 0.82,
  "matched_features": [
    "金融行业交易数据可能构成重要数据",
    "数据规模达到百万级，符合大规模特征",
    "跨境传输场景触发额外审查要求"
  ],
  "legal_basis": [
    "《数据安全法》第21条",
    "《数据出境安全评估办法》第4条",
    "《金融数据安全 数据安全分级指南》"
  ],
  "recommended_user_message": "基于贵司所处金融行业、数据规模（百万级）及跨境传输场景，建议按涉及重要数据处理进行合规准备，同时结合金融行业主管部门的最新重要数据目录做最终确认。"
}
```

**如果 LLM 不可用**，代理不报错，而是返回启发式评分的结论作为兜底：

```json
{
  "assessment_type": "important_data",
  "result": "likely_important_data",
  "suggested_answer": "yes",
  "confidence": 0.82,
  "matched_features": ["用户明确标注涉及重要数据", "行业属于金融高敏领域", "数据规模达千万/百万级"],
  "legal_basis": ["《数据安全法》第21条", "《促进和规范数据跨境流动规定》第7条"],
  "recommended_user_message": "基于审慎原则，建议按涉及重要数据处理。最终仍应结合主管部门目录确认。"
}
```

---

## 1.2 个人信息分类代理的完整 Prompt

**触发条件**：用户对"出境数据是否不含个人信息"回答了"不确定"。

**代理执行前，同样先跑启发式检测**——检查用户填写的类型列表中是否包含直接标识符（姓名、身份证号、手机号等）、间接标识符（设备ID、订单号等）、敏感指标（健康、金融、未成年人等）、匿名化信号（"已去除"、"不可逆"等）。

**User Prompt**：

```text
Assess whether the following data contains personal info / sensitive personal info / is sufficiently anonymized.

Data: 向新加坡母公司传输交易数据用于统一风控 用户交易流水
Personal info types claimed: ['用户姓名', '身份证号', '银行卡号', '交易金额', '交易时间', '手机号码']
Sensitive types claimed: ['银行卡号', '交易记录']
Anonymization description:
Heuristic: pi=likely_contains_personal_info, spi=likely_contains_sensitive_pi

Return JSON:
{
  "personal_information_result": "likely_contains|possible|likely_anonymized|insufficient",
  "suggested_q5_no_personal_info": "yes|no|unknown",
  "contains_sensitive_pi": true|false,
  "re_identification_risk": "none|low|medium|high",
  "legal_basis": ["《个人信息保护法》第4条"],
  "risk_note": "<one sentence>",
  "confidence": 0.0-1.0
}
```

这里的关键是 `suggested_q5_no_personal_info` 字段：
- 返回 `"no"` → 意味着"这批数据**含**个人信息"，即 `q5(是否不含个人信息) = 否`
- 返回 `"yes"` → 意味着"这批数据**不含**个人信息"，即 `q5 = 是`
- 返回 `"unknown"` → 意味着"无法判断"

**LLM 返回后，代理只取 `suggested_q5_no_personal_info` 的值（如果是 "yes" 或 "no"），回填到问卷中，然后规则引擎用更新后的问卷重新跑决策树。**

---

## 1.3 豁免判断代理的完整 Prompt

**触发条件**：用户选择的出境场景为"其他"（非合同履行/HR/紧急/法定义务这四个明确类别），可能错过了豁免情形。

**代理执行前，先跑信号检测**——对 4 类豁免场景（合同履行、HR管理、紧急情况、法定义务）各有一套强信号词、弱信号词、反信号词词典。例如：

- **合同履行强信号**：跨境购物、海淘、跨境支付、国际机票、酒店预订、用户主动发起
- **合同履行反信号**：营销、推荐、算法、画像、数据分析、广告
- **HR 管理强信号**：员工、薪酬、绩效、集团内部、母公司、子公司
- **HR 管理反信号**：外包、供应商、第三方服务

启发式规则：（强信号 ≥1 且 反信号 =0）→ 置信度较高；（强信号 ≥1 且 反信号 ≥1）→ 置信度 0.4，附追问；弱信号 ≥2 且集团内传输 → 置信度 0.55。

**User Prompt**（以某金融科技公司，场景为"其他"为例）：

```text
Assess whether this data transfer may qualify for exemption under Chinese law.

Scenario: other
Purpose: 向新加坡母公司传输交易数据用于统一风险控制管理
Data: 用户交易流水
Receiver: 新加坡XX金融控股 (type=intra_group, intra_group=True)
PII: 800000, SPI: 50000
Heuristic candidates: [{'type': 'hr_management', 'confidence': 0.55, 'missing_questions': ['是否已依法制定劳动规章制度或签订集体合同？', '数据出境是否仅限于集团内部人力资源管理所必需？', '是否已向员工告知数据出境情况？']}]

Return JSON:
{
  "candidate_exemptions": [
    {"type": "contract_performance|hr_management|emergency|legal_duty",
     "confidence": 0.0-1.0,
     "missing_questions": ["question to clarify"]}
  ],
  "recommended_next_question": "<key question to ask user>",
  "suggested_scenario": "if likely exempt"
}
```

注意：豁免判断代理的结果**不会**回填到问卷中去改变 `q6_scenario`。它只是生成"候选豁免列表"，供前端展示给用户参考。用户可以基于代理建议自己去修改问卷中的场景选择，然后重新提交诊断。

---

## 1.4 AI 推测路径的完整 Prompt

**触发条件**（见本文 2.7 节详述）：关键布尔字段（是否CIIO、是否重要数据、是否不含个人信息）中有不确定项，且缺乏结构化信号来补充。

此时决策树的所有规则都无法匹配，系统不走默认兜底路径，而是调用 LLM 做一次"全局推测"。

**System Prompt**：

```text
你是一名严谨的中国数据出境合规律师，只输出JSON。
```

**User Prompt**（以信息不完整的案例为例）：

```text
你是中国数据跨境合规律师。请基于给定问答做"推测结论"，仅在规则不足时使用。
请返回JSON，不要额外文本。字段：
recommended_path(仅可为security_assessment/scc_or_certification/exemption),
rationale, risk_level(LOW/MEDIUM/HIGH), legal_basis(string数组),
action_items(string数组，最多4条), confidence(LOW/MEDIUM),
uncertainty_notes(string数组), final_explanation。

输入：{
  "q1_is_ciio": "unknown",
  "q2_has_important_data": "unknown",
  "q3_pii_count": 0,
  "q4_spi_count": 0,
  "q5_no_personal_info": "unknown",
  "q6_scenario": "other",
  "q7_receiver_type": "intra_group",
  "q8_purpose": "数据存储和备份",
  "m1_industry": "云计算",
  "m1_company_size": "中型",
  "m3_processes_personal_info": "",
  "m3_data_volume_range": "",
  ...
}
```

**关键约束**：
- 温度只有 **0.1**（极低随机性，极度保守）
- 最大 tokens 800
- 路径只能是三个枚举值之一：`security_assessment` / `scc_or_certification` / `exemption`
- 返回的 JSON 如果解析失败（格式错误、字段缺失），系统降级为保守推测：推荐路径 = `scc_or_certification`，置信度 = `LOW`
- 结论来源强制标记为 `"ai_inference"`

---

## 1.5 规则解释生成的完整 Prompt

**触发条件**：决策树匹配到一条规则后，系统用 LLM 把规则的简短英文描述扩展为 2-3 句专业中文解释。

**System Prompt**：

```text
你是一名中国数据出境合规律师，仅负责解释规则结论，不改判。
```

**User Prompt**（以匹配到 CIIO 规则为例）：

```text
请基于以下规则判定结果，输出2-3句专业中文解释。要求：
1) 只能解释，不得改判推荐路径；2) 指出关键触发点；3) 给出一句行动建议。

推荐路径：security_assessment
风险等级：HIGH
规则依据：个人信息保护法 第40条；数据出境安全评估办法 第4条第(一)项
判定说明：关键信息基础设施运营者(CIIO)必须申报安全评估
问卷答案：{"q1_is_ciio":"yes","q2_has_important_data":"unknown","q3_pii_count":800000,"q4_spi_count":50000,...}
```

**LLM 可能返回的解释**：

```text
贵司作为关键信息基础设施运营者（CIIO），依据《个人信息保护法》第40条和《数据出境安全评估办法》第4条第（一）项的明确规定，向境外提供个人信息应当申报数据出境安全评估，此为法定强制义务，不因数据规模大小而免除。

同时，贵司个人信息处理规模已达80万人、敏感个人信息达5万人，这进一步强化了走安全评估路径的必要性。

建议立即启动安全评估申报准备工作，包括整理数据出境清单、生成自评估报告草案、补齐与境外接收方的数据处理协议，并按属地网信要求提交申报材料。
```

**关键约束**：温度 0.2，最大 tokens 300，"只能解释，不得改判推荐路径"——这句话确保 AI 不会"推翻"规则引擎的结论。

---

## 1.6 报告摘要生成的完整 Prompt

**触发条件**：诊断完成、生成 HTML/PDF 报告时，系统调用 LLM 生成一份简洁的摘要放在报告顶部。

**System Prompt**：

```text
你是一名精通中国数据出境合规的资深律师，用专业中文简洁总结诊断结论。
```

**User Prompt**（以 CIIO 案例为例）：

```text
企业：星辰支付科技有限公司
推荐路径：安全评估路径（security_assessment）
风险等级：HIGH
判定说明：关键信息基础设施运营者(CIIO)必须申报安全评估

请用2-3句话概括本次合规路径诊断的核心结论和关键注意事项。
```

**LLM 可能返回的摘要**：

```text
本次诊断确认，星辰支付科技有限公司作为CIIO，依法应当通过数据出境安全评估路径完成合规。鉴于企业同时涉及80万条个人信息和5万条敏感个人信息的跨境传输，建议尽快启动自评估报告编制和申报材料准备，关注重要数据识别和协议条款完善等关键事项。
```

---

# 第二部分：规则到底怎么判

## 2.1 决策树的完整结构

路径诊断的决策树存储在一个 JSON 文件中。这不是一个"树"形数据结构，而是一个**有序的规则列表**——按优先级从高到低排列，匹配到第一条就立即返回，不再继续检查后面的规则。

整个决策树共 10 条规则（9 条显式规则 + 1 条默认规则），完整结构如下：

```json
{
  "rules": [
    { "id": "no_personal_info",          "priority": 1 },
    { "id": "exemption_contract",        "priority": 2 },
    { "id": "exemption_hr",              "priority": 3 },
    { "id": "exemption_emergency",       "priority": 4 },
    { "id": "exemption_legal_duty",      "priority": 5 },
    { "id": "ciio",                      "priority": 6 },
    { "id": "important_data",            "priority": 7 },
    { "id": "pii_threshold",             "priority": 8 },
    { "id": "spi_threshold",             "priority": 9 }
  ],
  "default": {
    "path": "scc_or_certification",
    "legal_basis": ["个人信息出境标准合同办法", "GB/T 46068-2025", "促进和规范数据跨境流动规定 第7条"]
  }
}
```

**优先级设计原理**：豁免规则（1-5）排在安全评估规则（6-9）前面。因为逻辑上，先看"能不能免"，如果命中豁免条件，就不需要再看是否需要安全评估。

### 每条规则的完整内容

**规则 1: no_personal_info**（不含个人信息且不涉及重要数据 → 豁免）

```json
{
  "id": "no_personal_info",
  "description": "不含个人信息且不涉及重要数据，无需申报",
  "when": { "q5_no_personal_info": ["yes"] },
  "path": "exemption",
  "exemption_type": "no_personal_info",
  "legal_basis": [
    "促进和规范数据跨境流动规定 第4条",
    "网络数据安全管理条例 第38条"
  ]
}
```

匹配条件：`q5_no_personal_info == "yes"` → 执行很简单——用户确认了出境数据不含个人信息且不涉及重要数据，那就豁免。

**规则 2: exemption_contract**（合同履行场景豁免）

```json
{
  "id": "exemption_contract",
  "description": "因履行合同/向消费者提供服务所必需，且个人信息规模未触发强制评估门槛",
  "when": {
    "q6_scenario": ["contract_performance"],
    "q3_pii_count_lt": 1000000,
    "q4_spi_count_lt": 10000,
    "q1_is_ciio": ["no", "unknown"],
    "q2_has_important_data": ["no", "unknown"]
  },
  "path": "exemption",
  "exemption_type": "contract_performance",
  "legal_basis": [
    "促进和规范数据跨境流动规定 第5条第(一)项",
    "个人信息保护法 第13条第(二)项"
  ]
}
```

匹配条件：**5 个条件全部满足**才匹配：
1. 场景是"合同履行/向消费者提供服务"
2. 个人信息不足 100 万**且**
3. 敏感个人信息不足 1 万**且**
4. 不是 CIIO（或不确定）**且**
5. 不涉及重要数据（或不确定）

关键设计：CIIO 和重要数据这两个条件在豁免规则中用的是 `["no", "unknown"]`，意思是"只要不是明确的是，就可以尝试匹配豁免"。但到了安全评估规则中，用的是 `["yes"]`，意思是"明确的是才触发"。这个不对称设计体现了"从宽匹配豁免、从严匹配强制申报"的原则——即宁可漏过一个豁免机会让用户多填几张表，也不能把一个应该走安全评估的人错误地导向豁免。

**规则 3: exemption_hr**（人力资源管理豁免）

```json
{
  "id": "exemption_hr",
  "description": "跨国公司依法开展的内部人力资源管理，且个人信息规模未触发强制评估门槛",
  "when": {
    "q6_scenario": ["hr_management"],
    "q7_receiver_type": ["intra_group"],
    "q3_pii_count_lt": 1000000,
    "q4_spi_count_lt": 10000,
    "q1_is_ciio": ["no", "unknown"],
    "q2_has_important_data": ["no", "unknown"]
  },
  "path": "exemption",
  "exemption_type": "hr_management",
  "legal_basis": [
    "促进和规范数据跨境流动规定 第5条第(二)项",
    "个人信息保护法 第13条第(三)项"
  ]
}
```

规则 3 比规则 2 多了一个条件：`q7_receiver_type` 必须是 `"intra_group"`（集团内部关联公司）。这是因为 HR 管理豁免只适用于跨国公司内部，如果接收方是独立第三方，就不能适用。

**规则 4: exemption_emergency**（紧急情况豁免）

```json
{
  "id": "exemption_emergency",
  "description": "紧急情况下为保护自然人生命健康财产安全所必需",
  "when": {
    "q6_scenario": ["emergency"],
    "q1_is_ciio": ["no", "unknown"],
    "q2_has_important_data": ["no", "unknown"]
  },
  "path": "exemption",
  "exemption_type": "emergency",
  "legal_basis": [
    "促进和规范数据跨境流动规定 第5条第(三)项",
    "个人信息保护法 第13条第(四)项"
  ]
}
```

紧急情况豁免没有规模限制——即使是大量个人信息，只要是紧急情况下为保护生命健康财产所必需，也可以豁免。但 CIIO 和重要数据这两个条件仍然适用。

**规则 5: exemption_legal_duty**（法定义务豁免）

```json
{
  "id": "exemption_legal_duty",
  "description": "依法履行法定职责或法定义务所必需",
  "when": {
    "q6_scenario": ["legal_duty"],
    "q1_is_ciio": ["no", "unknown"],
    "q2_has_important_data": ["no", "unknown"]
  },
  "path": "exemption",
  "exemption_type": "legal_duty",
  "legal_basis": [
    "促进和规范数据跨境流动规定 第5条第(四)项",
    "个人信息保护法 第13条第(五)项"
  ]
}
```

与紧急情况豁免结构对称，无规模限制。

**规则 6: ciio**（CIIO 强制安全评估）——这是最关键的规则

```json
{
  "id": "ciio",
  "description": "关键信息基础设施运营者(CIIO)必须申报安全评估",
  "when": { "q1_is_ciio": ["yes"] },
  "path": "security_assessment",
  "legal_basis": [
    "个人信息保护法 第40条",
    "数据出境安全评估办法 第4条第(一)项"
  ]
}
```

匹配条件：`q1_is_ciio == "yes"` → 没有其他任何条件。只要是 CIIO，无论传多少数据、传什么数据、传给谁，都必须走安全评估。

**规则 7: important_data**（重要数据强制安全评估）

```json
{
  "id": "important_data",
  "description": "向境外提供重要数据必须申报安全评估",
  "when": { "q2_has_important_data": ["yes"] },
  "path": "security_assessment",
  "legal_basis": [
    "数据安全法 第21条",
    "数据出境安全评估办法 第4条第(二)项"
  ]
}
```

匹配条件：`q2_has_important_data == "yes"` → 同样无其他条件。

**规则 8: pii_threshold**（个人信息 100 万门槛）

```json
{
  "id": "pii_threshold",
  "description": "个人信息出境累计达100万人以上必须申报安全评估",
  "when": { "q3_pii_count_gte": 1000000 },
  "path": "security_assessment",
  "legal_basis": [
    "数据出境安全评估办法 第4条第(三)项",
    "促进和规范数据跨境流动规定 第6条"
  ]
}
```

匹配条件：`q3_pii_count >= 1,000,000` → 个人信息人数 ≥ 100 万。

**规则 9: spi_threshold**（敏感个人信息 1 万门槛）

```json
{
  "id": "spi_threshold",
  "description": "敏感个人信息出境累计达1万人以上必须申报安全评估",
  "when": { "q4_spi_count_gte": 10000 },
  "path": "security_assessment",
  "legal_basis": [
    "数据出境安全评估办法 第4条第(三)项",
    "个人信息保护法 第28条"
  ]
}
```

匹配条件：`q4_spi_count >= 10,000` → 敏感个人信息人数 ≥ 1 万。

**默认规则（兜底）**：如果以上 9 条规则全部不匹配，返回：

```json
{
  "path": "scc_or_certification",
  "legal_basis": [
    "个人信息出境标准合同办法",
    "GB/T 46068-2025",
    "促进和规范数据跨境流动规定 第7条"
  ]
}
```

---

## 2.2 规则匹配的逐字段逻辑

规则匹配函数 `_rule_match` 的完整逻辑：

```python
def _rule_match(when: dict, answers: DiagnosisAnswers) -> bool:
    # 检查1：CIIO状态是否在规则要求的取值列表中？
    if "q1_is_ciio" in when:
        if answers.q1_is_ciio.value not in when["q1_is_ciio"]:
            return False  # 不匹配

    # 检查2：重要数据状态是否在规则要求的取值列表中？
    if "q2_has_important_data" in when:
        if answers.q2_has_important_data.value not in when["q2_has_important_data"]:
            return False

    # 检查3：个人信息数量是否 ≥ 规则要求的下限？
    if "q3_pii_count_gte" in when:
        if answers.q3_pii_count < int(when["q3_pii_count_gte"]):
            return False

    # 检查4：敏感个人信息数量是否 ≥ 规则要求的下限？
    if "q4_spi_count_gte" in when:
        if answers.q4_spi_count < int(when["q4_spi_count_gte"]):
            return False

    # 检查5：个人信息数量是否 < 规则要求的上限？
    if "q3_pii_count_lt" in when:
        if answers.q3_pii_count >= int(when["q3_pii_count_lt"]):
            return False

    # 检查6：敏感个人信息数量是否 < 规则要求的上限？
    if "q4_spi_count_lt" in when:
        if answers.q4_spi_count >= int(when["q4_spi_count_lt"]):
            return False

    # 检查7：是否"不含个人信息"
    if "q5_no_personal_info" in when:
        if answers.q5_no_personal_info.value not in when["q5_no_personal_info"]:
            return False

    # 检查8：出境场景类型
    if "q6_scenario" in when:
        if answers.q6_scenario.value not in when["q6_scenario"]:
            return False

    # 检查9：接收方类型
    if "q7_receiver_type" in when:
        if answers.q7_receiver_type.value not in when["q7_receiver_type"]:
            return False

    # 全部通过 → 匹配！
    return True
```

关键设计点：规则只检查 `when` 字典中明确列出的字段。比如规则 6（CIIO 规则）的 `when` 只有一个条件 `{"q1_is_ciio": ["yes"]}`，那么它只检查这一个字段，不考虑个人信息数量、敏感信息数量等其他字段。这意味着：**CIIO 无论规模多大、传什么数据，都强制走安全评估**。

---

## 2.3 数据规范化的 6 条自动校正规则

在决策树匹配**之前**，系统会先对用户的回答做一轮自动校正。这些校正规则是确定性的，不依赖 AI。

**校正 1：重要数据不明确时，从详细模块推断**

```python
if q2_has_important_data == "unknown" and has_important_data:
    q2_has_important_data = "yes"
elif q2_has_important_data == "unknown" and not has_important_data
     and m3_processes_important_data == "no":
    q2_has_important_data = "no"
```

含义：用户在简答题中说"不确定"，但在详细的数据处理模块中填了重要数据类型 → 自动校正为"是"。用户在简答题中说"不确定"，但在详细模块中明确选了"不处理重要数据" → 校正为"否"。

**校正 2：个人信息不明确时，从详细模块推断**

```python
if q5_no_personal_info == "unknown":
    q5_no_personal_info = "yes" if (not has_personal_info and not has_important_data) else "no"
```

含义：如果既没有填个人信息类型，也没有填重要数据类型 → 校正为"不含个人信息"（`q5 = yes`，即确实不含）；否则校正为"含个人信息"（`q5 = no`）。

**校正 3：个人信息数量为 0 但实际有个人信息时，从体量范围估算**

```python
if q3_pii_count == 0 and has_personal_info:
    q3_pii_count = estimate_pii_count(m3_data_volume_range)
```

估算规则：
- "1000万条以上" → 估算为 10,000,000
- "100-1000万条" → 估算为 2,000,000（取中间值偏保守）
- "10-100万条" → 估算为 300,000
- "10万条以下" → 估算为 50,000

**校正 4：敏感个人信息数量为 0 但实际有敏感信息时，从体量范围估算**

```python
if q4_spi_count == 0 and has_sensitive_info:
    q4_spi_count = 12_000 if volume in {"1000万条以上", "100-1000万条"} else 2_000
```

含义：大体量时估算 12000（超过 1 万门槛），小体量时估算 2000。

**校正 5：接收方类型从"第三方"校正为"集团内部"**

```python
if q7_receiver_type == "third_party":
    if not share_to_third_party and not entrusted_processing:
        q7_receiver_type = "intra_group"
```

含义：用户选了"独立第三方"，但在详细模块中既没有"向第三方共享"也没有"委托处理" → 校正为"集团内部"。这防止了用户随便选错导致错过 HR 管理豁免。

**校正 6：敏感个人信息自动识别**

```python
keywords = ("身份证", "人脸", "指纹", "声纹", "健康", "金融", "未成年人", "精准位")
if any(key in item for key in keywords for item in personal_info_types):
    has_sensitive_info = True
```

含义：即使用户没有把某类信息标记为"敏感"，但系统通过关键词匹配判断它实际上是敏感个人信息。这在后续估算敏感个人信息数量时会被使用。

---

## 2.4 重要数据启发式评分的完整算法

在调用 LLM 之前，重要数据判断代理先用一套启发式评分做初步判断。

### 行业敏感词典

系统内置了一套"行业 → 关键词"的映射关系：

| 行业 | 敏感关键词 | 权重 |
|------|----------|------|
| 医疗 | 病历、基因、临床试验、基因组、患者、罕见病 | 行业敏感度 2 |
| 金融 | 交易记录、征信、银行、证券、保险、支付流水 | 行业敏感度 2 |
| 汽车 | 自动驾驶、VIN、车辆轨迹、地图、高精度地图、路网、车联网 | 行业敏感度 2 |
| 工业 | 工业运行、SCADA、PLC、工业控制、产能、能耗 | 行业敏感度 2 |
| 能源 | 能源调度、电网、油气、电力、管道、石油 | 行业敏感度 2 |
| 通信 | 大规模用户数据、通信内容、信令 | 行业敏感度 2 |
| 科研 | 基因、族群数据、人类遗传、遗传资源 | 行业敏感度 2 |
| 政务 | 政府、公共安全、交通、应急、地理信息、测绘 | 行业敏感度 2 |

### 六类加权因子

| 因子 | 权重 | 触发条件 |
|------|------|---------|
| 人口规模 | 3 分 | 体量范围含"1000万"或"100-1000万"，或文本含"万人/万名/10000/万例" |
| 行业敏感 | 2 分 | 行业名匹配上述 8 个高敏行业 |
| 基因相关 | 3 分 | 文本含"基因/genetic/genomic/dna/rna/遗传" |
| 政务相关 | 3 分 | 文本含"政府/公共安全/地理/测绘/government/public safety" |
| 跨境目的 | 1 分 | 含"国际合作研究" |
| 区域系统 | 2 分 | 含"区域性/系统性" |

加上一条特殊规则：用户如果明确标注了"处理重要数据"或填了重要数据类型 → **直接加 5 分**。

### 评分 → 结论的映射

| 得分范围 | 结论 | 建议回填值 | 置信度 |
|---------|------|-----------|--------|
| ≥ 5 分 | 很可能构成重要数据 | `yes` | 0.5 + 得分 × 0.08（上限 0.9） |
| 3-4 分 | 可能构成重要数据 | `yes` | 0.65 |
| 1-2 分 | 不太可能构成重要数据 | `unknown` | 0.5 |
| 0 分 | 信息不足，无法判断 | `unknown` | 0.4 |

### 实际案例演示

以"星辰支付科技有限公司"为例：

```
输入：
  行业 = "金融科技"
  数据类型 = ["用户姓名", "身份证号", "银行卡号", "交易金额", "交易时间"]
  目的 = "向新加坡母公司传输交易数据用于统一风控"
  体量 = "100-1000万条"

匹配检测：
  1. processes_important_data == "yes" → +5 分（用户明确标注）
  2. 行业"金融科技" 匹配 "金融" → +2 分
  3. 体量"100-1000万条" → +3 分
  4. 文本中无基因关键词 → 0 分
  5. 文本中无政务关键词 → 0 分

总得分 = 5 + 2 + 3 = 10 分

映射：≥ 5 分 → result = "likely_important_data"
              → suggested_answer = "yes"
              → confidence = 0.5 + 10 × 0.08 = 0.5 + 0.8，截断到 0.9
              → confidence = 0.9
```

这个启发式结论会和原始数据一起送给 LLM 做精化（见 1.1 节）。

---

## 2.5 个人信息分类的完整决策逻辑

### 三层标识符词典

**直接标识符**（匹配到即判定包含个人信息）：

```text
姓名、身份证、手机号、电话、邮箱、email、地址、
车牌、VIN、护照、社保号、driver license、passport、
name、phone、address、social security
```

**间接标识符**（需要结合其他信号判断）：

```text
设备ID、device id、订单号、order number、IMEI、IDFA、
精确位置、GPS、经纬度、latitude、longitude、
时间戳、timestamp、IP地址、IP address、cookie、
交易记录、transaction、浏览记录、browsing history
```

**敏感个人信息指标**（匹配到即标记含敏感信息）：

```text
(健康, health), (医疗, medical), (病历, patient),
(金融账户, financial account), (银行, bank), (征信, credit),
(行踪轨迹, location tracking), (精确位置, precise location),
(生物识别, biometric), (指纹, fingerprint), (人脸, face),
(未成年人, minor), (儿童, child), (14岁, under 14),
(宗教信仰, religion), (政治观点, political)
```

### 匿名化信号和重识别风险

**匿名化信号**（说明数据经过了去标识化处理）：

```text
不可逆、irreversible、无法复原、cannot be restored、
已去除、removed、stripped、脱敏、de-identified、
匿名化、anonymized、aggregated、聚合
```

**重识别风险信号**（说明匿名化可能不充分）：

```text
可重识别、可关联、可匹配、re-identifiable、
linkable、matchable、间接识别、indirect identification、
假名化、pseudonymized、去标识化、de-identified (not anonymized)
```

### 决策树（8 种情况，按优先级排列）

| 条件 | 个人信息判断 | q5 建议值 |
|------|-----------|----------|
| 用户明确声明处理个人信息 OR 填了个人信息类型 | 很可能含个人信息 | `no`（即"并非不含个人信息"） |
| 命中直接标识符 | 很可能含个人信息 | `no` |
| 命中间接标识符 AND 无匿名化信号 | 可能含个人信息 | `no` |
| 命中间接标识符 AND 有匿名化信号 AND 无重识别风险 | 匿名化可能充分 | `yes`（即"不含个人信息"） |
| 命中间接标识符 AND 有匿名化信号 AND 有重识别风险 | 匿名化不确定，存在重识别风险 | `no`（保守判断） |
| 有匿名化信号 AND 无直接标识符 AND 无间接标识符 | 已匿名化或本就不含个人信息 | `yes` |
| 以上都不匹配 | 信息不足 | `unknown` |

---

## 2.6 豁免判断的 4 类信号检测

豁免判断代理内置了 4 类豁免场景的信号词典。

### 合同履行豁免信号

| 信号强度 | 信号词 | 含义 |
|---------|--------|------|
| 强信号 | 跨境购物、海淘、跨境支付、国际机票、酒店预订、签证、留学申请、考试报名、跨境寄递、国际物流、用户主动发起、消费者个人、为完成交易 | 这些词强烈暗示用户在主动跨境消费 |
| 弱信号 | 售后服务、退换货、跨境客服、账户管理 | 可能是合同履行的一部分，但不够确定 |
| 反信号 | 营销、推荐、算法、画像、数据分析、广告、精准推送、二次使用 | 这些词暗示数据可能被用于超出合同履行的目的 |

### HR 管理豁免信号

| 信号强度 | 信号词 | 含义 |
|---------|--------|------|
| 强信号 | 员工、薪酬、绩效、考勤、入职、集团内部、母公司、子公司、关联公司、劳动规章、集体合同 | 典型的企业内部HR管理场景 |
| 反信号 | 外包、供应商、第三方服务 | 数据可能流向集团外部 |

### 紧急情况豁免信号

| 信号强度 | 信号词 |
|---------|--------|
| 强信号 | 紧急、生命、健康、安全、财产、不可抗力、自然灾害、事故 |

### 法定义务豁免信号

| 信号强度 | 信号词 |
|---------|--------|
| 强信号 | 法定、监管要求、司法协助、行政执法、反洗钱、税务申报、证券披露 |

### 信号 → 结论的逻辑

```
对每一类豁免场景：
  强信号 ≥ 1 且 反信号 = 0：
    → 候选豁免，置信度 = min(0.85, 0.5 + 强信号数 × 0.15)
  强信号 ≥ 1 且 反信号 ≥ 1：
    → 候选豁免，置信度 = 0.4，附追问"存在反信号 XX，请确认"
  弱信号 ≥ 2 且 反信号 = 0 且 是集团内传输：
    → 候选豁免，置信度 = 0.55
  其他：
    → 不纳入候选
```

---

## 2.7 AI 推测的触发条件

触发 AI 推测需要同时满足两个条件：

**条件 1：关键布尔字段存在不确定性**

三个关键布尔字段中至少有一个为 `unknown`：
- `q1_is_ciio`（是否 CIIO）== `unknown`，或
- `q2_has_important_data`（是否涉及重要数据）== `unknown`，或
- `q5_no_personal_info`（是否不含个人信息）== `unknown`

**条件 2：且缺乏结构化信号来弥补**

即信息规模的信号也很弱：
- 个人信息数量为 0（用户没有填数量）**且** 敏感个人信息数量为 0

但如果详细模块中有明确的结构化信号，则**不触发** AI 推测：
- 用户在详细模块中明确选了"处理/不处理个人信息"
- 用户在详细模块中明确选了"处理/不处理重要数据"
- 用户填了个人信息类型列表
- 用户填了重要数据类型列表

**设计意图**：当用户既没填关键判断题、也没填详细模块时，系统无法用规则引擎得到可靠结论。此时不走默认规则（那会一律导向标准合同），而是让 AI 基于所有可用信息做一个推测——但会明确标注"这是推测，置信度低，请补充信息后重判"。

---

## 2.8 规则判别优先级全景图

整个路径诊断模块的判别优先级从高到低如下：

```
优先级 1：数据规范化（6 条自动校正）
  对用户输入做智能补全，但不改变用户明确填写的内容

优先级 2：AI 代理辅助澄清（3 个代理，按条件触发）
  2a. 重要数据判断代理（q2 == unknown 时）
  2b. 个人信息分类代理（q5 == unknown 时）
  2c. 豁免判断代理（q6 == "other" 时）
  代理结果回填到问卷，校正后的问卷重新进入规则匹配

优先级 3：决策树规则匹配（9 条规则，优先级从高到低）
  规则1: 不含个人信息 → 豁免
  规则2: 合同履行 + 规模未达标 + 非CIIO + 非重要数据 → 豁免
  规则3: HR管理 + 集团内 + 规模未达标 + 非CIIO + 非重要数据 → 豁免
  规则4: 紧急情况 + 非CIIO + 非重要数据 → 豁免
  规则5: 法定义务 + 非CIIO + 非重要数据 → 豁免
  规则6: 是CIIO → 安全评估（无其他条件）
  规则7: 涉及重要数据 → 安全评估（无其他条件）
  规则8: PII ≥ 100万 → 安全评估
  规则9: SPI ≥ 1万 → 安全评估

优先级 4：AI 推测（规则全部不匹配 + 信息不足时）
  所有9条规则都不匹配 + 关键字段 unknown + 缺乏结构化信号
  → LLM 全局推测 → 置信度 LOW → 注明"需人工复核"

优先级 5：默认兜底（AI推测也失败时）
  → scc_or_certification（标准合同备案或认证路径）
```

---

# 第三部分：RAG 知识库在诊断模块中怎么组织和调用

**诊断模块不使用本地 RAG 知识库。**

这是很多人容易误解的地方。诊断模块的"法规依据"来源有两个：

1. **决策树内置的法律依据**：每条规则在 JSON 中已经硬编码了对应的法规条文。例如 CIIO 规则内置了 `"个人信息保护法 第40条"` 和 `"数据出境安全评估办法 第4条第(一)项"`。这些不经过检索，直接作为诊断结果输出。

2. **得理 API（外部法律数据库）**：在生成诊断报告时，会调用得理 API 搜索相关的司法案例和补充法规（详见下文第四部分）。

**为什么诊断模块不使用本地 RAG？**

因为诊断模块的回答是一个"分类"问题（走哪条路径），而不是"生成"问题（写一篇报告）。分类问题的法规依据是固定的——CIIO → 安全评估，法律依据就是个人信息保护法第40条，不需要检索。而草案生成类模块（如安全自评估）需要在报告正文中大段引用法规原文，这才需要 RAG 检索。

**诊断模块如何间接用到 RAG 的"工作流规则"？**

虽然诊断模块不调用 RAG 检索，但它的决策树本身就是"工作流规则"的一种形态。在工作流规则索引（L2 层）中，存有与决策树逻辑一致的知识条目（如"CIIO 判定规则：q1_is_ciio=yes → path=security_assessment"）。这些知识条目会在安全自评估模块的 RAG 检索中被调用——也就是说，诊断模块的决策树规则，在后续的功能层模块中会被 RAG 系统引用。

---

# 第四部分：得理 API 在诊断模块中什么时候调用

**在中国路径诊断完成、生成 HTML/PDF 报告时，会调用得理 API 补充引用。**

具体来说，在 `DiagnosisService._build_citations()` 方法中（这个方法在诊断评估完成后、生成报告前被调用）：

### 调用一：搜索司法案例

```python
search_cases(
    query="数据出境 {用户填写的出境目的}",
    size=2
)
```

例如用户出境目的是"向新加坡母公司传输交易数据用于统一风控"，则搜索：
```text
search_cases("数据出境 向新加坡母公司传输交易数据用于统一风控", size=2)
```

返回最多 2 条相关的司法案例。每条案例在报告中标注为"来自得理法搜的补充检索结果"。

### 调用二：搜索法规条文

```python
search_laws(
    query="数据出境 {用户填写的出境目的} 合规路径",
    size=3
)
```

例如：
```text
search_laws("数据出境 向新加坡母公司传输交易数据用于统一风控 合规路径", size=3)
```

返回最多 3 条相关的法律法规。每条标注为"来自得理法搜的法条检索结果"。

### 调用时序

```text
用户提交诊断问卷
  → _normalize_answers()           # 数据规范化（纯规则，不调API）
  → AI Agent 辅助澄清               # （如触发，调用LLM，不调得理API）
  → 决策树规则匹配                  # （纯规则，不调API）
  → _build_rule_explanation()       # （调用LLM做规则解释，不调得理API）
  → _build_citations()              # ★ 调用得理API ★
  → _build_result()                 # 组装最终结果
  → renderer.render()               # 调用LLM做摘要，生成HTML/PDF
```

### 错误处理

得理 API 调用失败（网络超时/凭证失效/接口报错）不影响诊断主流程——只是诊断报告中少了外部检索的补充引用，但决策树内置的法律依据仍在。

---

# 第五部分：Fact / Issue / Evidence 到底什么样

以下以**安全自评估模块（assessment）**为例，展示一条完整的"事实 → 问题 → 证据"三链串联的真实案例。

背景：星辰支付科技有限公司（金融科技行业，CIIO，向新加坡传输80万条个人信息含5万条敏感信息）。

## 5.1 FactItem 的真实案例

用户填写的每一条信息都被拆解为独立的事实项。以下是安全自评估模块事实构建器输出的真实事实列表（节选）：

### 事实 F-001：企业名称

```json
{
  "fact_id": "F-001",
  "source_type": "schema",
  "source_ref": "AssessmentRequest.company_name",
  "field_path": "request.company_name",
  "value": "星辰支付科技有限公司",
  "normalized_value": "星辰支付科技有限公司",
  "confidence": 1.0,
  "evidence_status": "user_claim_only",
  "supporting_material_refs": [],
  "can_support_external_positive_claim": true,
  "requires_user_confirmation": false,
  "notes": null,
  "jurisdiction": "CN"
}
```

解读：企业名称来自用户表单（source_type = schema），置信度 1.0（用户自己填的，不需要怀疑），证据状态是"仅有用户声明"（没有营业执照附件来证明），但因为企业名称属于基本信息，允许在对外报告中做正面断言。

### 事实 F-003：CIIO 状态

```json
{
  "fact_id": "F-003",
  "source_type": "schema",
  "source_ref": "AssessmentRequest.is_ciio",
  "field_path": "request.is_ciio",
  "value": true,
  "normalized_value": true,
  "confidence": 1.0,
  "evidence_status": "user_claim_only",
  "supporting_material_refs": [],
  "can_support_external_positive_claim": false,
  "requires_user_confirmation": true,
  "notes": "CIIO身份为关键合规判定依据，建议用户补充CIIO认定文件",
  "jurisdiction": "CN"
}
```

解读：CIIO = 是，但 `can_support_external_positive_claim = false`。为什么？因为"用户说自己是 CIIO"不等于"监管机关认定他是 CIIO"。在对外报告中，系统只能写"用户声明其为CIIO"，不能直接断言"该企业是CIIO"。同时，`requires_user_confirmation = true` 表示系统建议用户确认后才能在报告中使用这条事实。

### 事实 F-005：个人信息数量

```json
{
  "fact_id": "F-005",
  "source_type": "schema",
  "source_ref": "AssessmentRequest.pii_count",
  "field_path": "request.pii_count",
  "value": 800000,
  "normalized_value": 800000,
  "confidence": 0.85,
  "evidence_status": "user_claim_only",
  "supporting_material_refs": [],
  "can_support_external_positive_claim": true,
  "requires_user_confirmation": false,
  "notes": "近12个月累计向境外提供个人信息的人数，用户自行填报",
  "jurisdiction": "CN"
}
```

解读：置信度 0.85 而非 1.0——因为"80万"这个数字是用户自己报的，没有附件证明（evidence_status = user_claim_only），但系统仍允许在报告中正面引用这个数字（can_support_external_positive_claim = true），只是措辞上会写"根据企业提供的数据"而非"经核实"。

### 事实 F-013：诊断推荐路径

```json
{
  "fact_id": "F-013",
  "source_type": "diagnosis",
  "source_ref": "diagnosis_result.recommended_path",
  "field_path": "diagnosis_result.recommended_path",
  "value": "security_assessment",
  "normalized_value": "security_assessment",
  "confidence": 1.0,
  "evidence_status": "documented_evidence",
  "supporting_material_refs": ["诊断报告编号"],
  "can_support_external_positive_claim": true,
  "requires_user_confirmation": false,
  "notes": "由上游路径诊断模块判定",
  "jurisdiction": "CN"
}
```

解读：来源类型是"诊断结果"（diagnosis），不是"用户表单"。这意味着这条事实是系统上游模块的判断结论，而非用户直接输入。置信度 1.0 因为它是规则引擎的确定性结论。证据状态是"有文件证明"（因为诊断报告已归档）。

### 事实 F-019：数据处理协议缺少再转移约束条款

```json
{
  "fact_id": "F-019",
  "source_type": "attachment",
  "source_ref": "数据处理协议.pdf",
  "field_path": "attachment_notes.数据处理协议.pdf.clause_gap",
  "value": "合同第5条描述了数据传输但未包含再转移限制条款",
  "normalized_value": "missing_onward_transfer_constraint",
  "confidence": 0.78,
  "evidence_status": "partial_evidence",
  "supporting_material_refs": ["数据处理协议.pdf"],
  "can_support_external_positive_claim": false,
  "requires_user_confirmation": true,
  "notes": "AI附件解析代理从上传文件中检测到条款缺失，建议法务复核确认",
  "jurisdiction": "CN"
}
```

解读：这条事实来自附件提取（source_type = attachment），置信度 0.78（AI 判断可能有误差），需要用户确认（requires_user_confirmation = true）。不能在对外报告中直接断言"合同缺少XX条款"（can_support_external_positive_claim = false），只能委婉表述"建议企业在合同中补充XX内容"。

---

## 5.2 IssueItem 的真实案例

问题构建器基于事实清单 + 诊断结果 + 法规检索结果，用确定性规则逐项检查，生成问题列表。以下是完整的问题示例：

### 问题 I-001：CIIO 触发安全评估（阻断级）

```json
{
  "issue_id": "I-001",
  "title": "企业为CIIO，触发数据出境安全评估路径",
  "description": "该企业被标识为关键信息基础设施运营者（CIIO）。依据《数据出境安全评估办法》第四条第（一）项，CIIO向境外提供个人信息和重要数据的，应当申报数据出境安全评估。此为法定强制义务，不因数据规模或接收方国家而改变。",
  "category": "path",
  "severity": "BLOCKER",
  "issue_certainty": "confirmed_issue",
  "fact_refs": ["F-003"],
  "rule_refs": ["diagnosis:ciio", "数据出境安全评估办法-第4条"],
  "evidence_refs": [],
  "recommended_action": "必须申报数据出境安全评估。建议立即启动自评估报告编制工作，整理数据出境清单、补齐与境外接收方的数据处理协议，按属地网信要求提交全套申报材料。",
  "affects_outputs": ["overview", "data_scope", "necessity_legal_basis", "conclusion"],
  "missing_materials": [],
  "internal_review_required": true,
  "external_report_strategy_required": true,
  "can_enter_external_report": true
}
```

解读：
- **category = "path"**：这是一个路径判断类问题
- **severity = "BLOCKER"**：最高严重级别，不解决就无法推进
- **issue_certainty = "confirmed_issue"**：已确认问题，报告中使用肯定语气
- **fact_refs = ["F-003"]**：这个问题基于事实 F-003（CIIO=是）
- **rule_refs**：依法依据来自诊断规则 `ciio` 和《数据出境安全评估办法》第4条
- **affects_outputs**：这个问题影响报告的概述章、数据范围章、必要性合法性章和结论章
- **can_enter_external_report = true**：可以写入对外报告
- **evidence_refs 暂时为空**：证据链构建完成后会被回填

### 问题 I-002：重要数据状态未知（高风险）

```json
{
  "issue_id": "I-002",
  "title": "重要数据状态未确认，存在合规不确定性",
  "description": "用户未能确认是否涉及重要数据出境。依据《数据出境安全评估办法》第五条第（一）项，向境外提供重要数据同样触发安全评估申报要求。如实际涉及重要数据而未申报，可能面临监管风险。",
  "category": "data_classification",
  "severity": "HIGH",
  "issue_certainty": "suspected_issue",
  "fact_refs": ["F-004"],
  "rule_refs": ["数据出境安全评估办法-第5条", "数据安全法-第21条"],
  "evidence_refs": [],
  "recommended_action": "尽快确认交易数据是否属于金融行业重要数据。建议参照金融行业主管部门发布的重要数据目录进行数据分类分级，并请法务复核确认。",
  "affects_outputs": ["data_scope", "risk_remediation"],
  "missing_materials": ["重要数据识别报告或数据分类分级结果"],
  "internal_review_required": true,
  "external_report_strategy_required": true,
  "can_enter_external_report": true
}
```

解读：
- **severity = "HIGH"**：高风险，但不是阻断级（因为即使用户不确定，CIIO 身份已经决定了安全评估路径）
- **issue_certainty = "suspected_issue"**：疑似问题——系统没有确凿证据说"一定涉及重要数据"，只能说"可能涉及"。报告中使用保留措辞
- **missing_materials**：明确列出了用户应该补充的材料

### 问题 I-004：协议缺少条款（中风险）

```json
{
  "issue_id": "I-004",
  "title": "数据处理协议缺少再转移约束条款",
  "description": "经附件解析，企业与境外接收方签订的数据处理协议中，未明确包含再转移限制条款。根据《数据出境安全评估办法》第九条，数据出境法律文件应包含'境外接收方将数据再转移给其他组织、个人的约束性要求'。",
  "category": "contract",
  "severity": "MEDIUM",
  "issue_certainty": "suspected_issue",
  "fact_refs": ["F-009", "F-019"],
  "rule_refs": ["数据出境安全评估办法-第9条"],
  "evidence_refs": [],
  "recommended_action": "在与境外接收方的数据处理协议中补充再转移约束条款，明确：境外接收方不得将数据再转移给第三方，除非获得数据处理者事先书面同意并与第三方签订不低于原协议保护标准的数据处理协议。",
  "affects_outputs": ["recipient_capability", "security_measures", "risk_remediation"],
  "missing_materials": ["补充后的数据处理协议（含再转移条款）"],
  "internal_review_required": true,
  "external_report_strategy_required": true,
  "can_enter_external_report": true
}
```

解读：
- **category = "contract"**：这是一个合同问题
- **severity = "MEDIUM"**：中风险——虽然缺失了条款，但可以通过补充协议来解决，不阻断申报
- **fact_refs = ["F-009", "F-019"]**：基于两个事实——F-009（用户上传了数据处理协议.pdf）和 F-019（AI 解析发现缺少再转移条款）
- **recommended_action**：给出了非常具体的操作建议（"在协议中补充XX条款，明确XX内容"）

---

## 5.3 EvidenceItem 的真实案例

证据链构建器基于事实、问题和法规，为每个合规结论构建完整的推理链。

### 证据 E-001：CIIO 数据出境的路径判断

```json
{
  "evidence_id": "E-001",
  "claim": "企业作为CIIO，向境外提供个人信息应当申报数据出境安全评估",
  "fact_refs": ["F-003"],
  "rule_refs": ["个人信息保护法-第40条", "数据出境安全评估办法-第4条"],
  "issue_refs": ["I-001"],
  "legal_basis": [
    {
      "source_title": "数据出境安全评估办法",
      "article": "第四条第（一）项",
      "snippet": "数据处理者向境外提供数据，有下列情形之一的，应当……申报数据出境安全评估：（一）关键信息基础设施运营者向境外提供个人信息和重要数据……",
      "support_level": "exact_support",
      "jurisdiction": "CN",
      "effective_date": "2022-09-01",
      "version": "2022年版"
    },
    {
      "source_title": "个人信息保护法",
      "article": "第四十条",
      "snippet": "关键信息基础设施运营者和处理个人信息达到国家网信部门规定数量的个人信息处理者，应当将在中华人民共和国境内收集和产生的个人信息存储在境内。确需向境外提供的，应当通过国家网信部门组织的安全评估……",
      "support_level": "exact_support",
      "jurisdiction": "CN",
      "effective_date": "2021-11-01",
      "version": "2021年版"
    }
  ],
  "supporting_basis": [],
  "discarded_basis": [],
  "document_refs": [],
  "rag_query_used": "金融科技 CIIO 数据出境 安全评估 个人信息",
  "rag_hits_count": 15,
  "conclusion": "该企业同时满足CIIO身份和法定个人信息规模两个条件，依法必须申报数据出境安全评估。建议企业按《数据出境安全评估申报指南（第二版）》准备全套申报材料。",
  "usage_constraint": "可作为路径判断和报告结论的法律依据，但不可用于对外断言企业'必然通过'安全评估审查",
  "confidence": 0.95,
  "used_by": ["overview", "data_scope", "necessity_legal_basis", "conclusion"]
}
```

解读：
- **claim**：这是证据要支撑的具体主张
- **support_level = "exact_support"**：两条法规都是"完全支撑"级别——法条直接适用于此问题，可以独立作为法律依据
- **supporting_basis = []**：不需要辅助依据，两条主要依据已经充分
- **discarded_basis = []**：没有需要丢弃的引用（所有检索到的法规都相关）
- **rag_query_used**：这条证据是通过什么 RAG 查询找到的法规依据
- **usage_constraint**：对证据使用方式的约束——"可用于路径判断，但不可用于断言必然通过审查"
- **confidence = 0.95**：置信度很高（CIIO 身份是用户填写的，唯一的不确定性来自用户填写的准确性）
- **used_by**：这条证据被报告的哪些章节引用

### 证据 E-005：协议条款缺失的法律依据

```json
{
  "evidence_id": "E-005",
  "claim": "数据处理协议缺少再转移约束条款，不符合安全评估办法关于法律文件的要求",
  "fact_refs": ["F-009", "F-019"],
  "rule_refs": ["数据出境安全评估办法-第9条"],
  "issue_refs": ["I-004"],
  "legal_basis": [
    {
      "source_title": "数据出境安全评估办法",
      "article": "第九条",
      "snippet": "数据处理者与境外接收方订立的法律文件中应当明确约定数据安全保护责任义务，至少包括下列内容：……（三）境外接收方将出境数据再转移给其他组织、个人的约束性要求……",
      "support_level": "exact_support",
      "jurisdiction": "CN",
      "effective_date": "2022-09-01",
      "version": "2022年版"
    }
  ],
  "supporting_basis": [
    {
      "source_title": "数据出境安全评估申报指南（第二版）",
      "article": "第二部分 申报材料",
      "snippet": "数据处理者与境外接收方订立的法律文件……应包含数据安全保护责任义务的明确约定",
      "support_level": "partial_support",
      "jurisdiction": "CN",
      "effective_date": "",
      "version": "第二版"
    }
  ],
  "discarded_basis": [],
  "document_refs": [
    {
      "file_name": "数据处理协议.pdf",
      "page": 3,
      "paragraph_range": [5, 7],
      "quote": "第五条 数据传输……甲方将用户交易数据加密后通过专线传输至乙方服务器……"
    }
  ],
  "rag_query_used": "数据出境法律文件 再转移 约束性要求 标准合同必备条款",
  "rag_hits_count": 8,
  "conclusion": "企业当前的数据处理协议确实未包含再转移约束条款，需要在协议中补充相关内容。补充条款应至少包括：再转移需事先书面同意、再转移对象须签订不低于原协议保护标准的数据处理协议、企业对再转移承担监督责任。",
  "usage_constraint": "可用于指出协议缺失项和提出修改建议，但不可断言'协议不合法'或'企业违法'",
  "confidence": 0.78,
  "used_by": ["recipient_capability", "security_measures", "risk_remediation"]
}
```

解读：
- **support_level 有区分**：主要法律依据是"完全支撑"（安全评估办法第9条直接规定了必须包含再转移条款），辅助依据是"部分支撑"（申报指南规定了材料要求但不直接涉及条款内容）
- **document_refs**：具体指向了文件中的位置——数据处理协议.pdf 第3页第5-7段，并引用了原文
- **confidence = 0.78**：比 E-001 低，因为"缺少条款"这个判断是 AI 附件解析代理做的，可能有误差
- **usage_constraint**：严格限制——不能断言"协议不合法"

---

## 5.4 三链串联：从事实到证据的完整追溯

以"CIIO 触发安全评估"这一条最关键的合规判断为例，展示完整的追溯链：

```
事实链层
  F-003: CIIO = 是
    ↑
    │ 来源：用户表单 (source_type = "schema")
    │ 置信度：1.0
    │ 证据状态：仅有用户声明 (user_claim_only)
    │ 能否对外断言：否（需用户确认后才能在报告中使用）

规则链层
  diagnosis:ciio (诊断决策树规则6)
    ↑
  《数据出境安全评估办法》第四条第(一)项
    ↑
  《个人信息保护法》第四十条

问题链层
  I-001 [BLOCKER]: 企业为CIIO，触发数据出境安全评估路径
    ↑
    │ 确定性：已确认问题 (confirmed_issue)
    │ 报告措辞策略：肯定语气 + 引用法律条文
    │ 影响章节：概述、数据范围、必要性合法性、结论

证据链层
  E-001: 企业作为CIIO应当申报安全评估
    ↑
    │ 法律依据：《数据出境安全评估办法》第四条（完全支撑）
    │ 辅助依据：《个人信息保护法》第四十条（完全支撑）
    │ 置信度：0.95
    │ 使用约束：可用于路径判断，不可用于断言"必然通过"
    │ 被引用章节：overview, data_scope, necessity_legal_basis, conclusion

最终报告中的呈现
  第1章（概述）：
    "本公司作为关键信息基础设施运营者（CIIO），
     依据《数据出境安全评估办法》第四条第（一）项[1]及
     《个人信息保护法》第四十条[2]的规定，
     应当依法申报数据出境安全评估。"

  第8章（结论）：
    "综合以上分析，本公司向新加坡母公司传输用户交易数据的行为，
     同时满足CIIO身份和法定个人信息规模两个条件[E-001]，
     建议立即启动安全评估申报准备工作。"
     
  ---
  [1] 《数据出境安全评估办法》第四条第（一）项
  [2] 《个人信息保护法》第四十条
```

这条追溯链条完整地展示了：报告的每一条结论 → 源于哪条证据 → 基于哪个问题 → 依据哪些法规 → 来自哪条事实。任何一环都可以被独立查阅和验证。

---

> **文档版本**：2026年6月6日
> **文档目的**：以诊断模块和评估模块为案例，完整拆解 Prompt、规则引擎、RAG/得理API 调用、Fact/Issue/Evidence/Evidence 的每一个技术细节
