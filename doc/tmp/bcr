# 1. BCR 类型判定 Agent

**问题场景：**
当前 `actual=unknown → fallback BCR-C` 会导致类型误判，BCR-C 与 BCR-P checklist 不一致，可能全链路都走错。

**Agent 作用：**
综合标题、正文、附件、信号词、角色描述，判断文档实际类型（BCR-C / BCR-P / mixed / unknown）。

**预期处理逻辑：**

1. **输入**：文档标题、正文前 8k 字、附件摘要、申报类型、规则信号词列表。
2. **步骤**：

   * 提取标题、定义章节、适用范围、责任角色、Article 28 / 处理者条款、客户指令条款；
   * 使用推理模型判断文档覆盖的是控制者还是处理者责任；
   * 如果文档中同时出现 BCR-C 与 BCR-P 信号，生成 “mixed”；
   * 输出 confidence score 和 reasoning summary。
3. **输出**：

```json
{
  "type_judgment": "mixed",
  "confidence": 0.75,
  "reasoning_summary": "...",
  "recommended_path": "拆分 BCR-C/BCR-P 检查",
  "risk_level": "MEDIUM"
}
```

---

# 2. Requirement 覆盖 Agent（实质覆盖判断）

**问题场景：**
5状态 checklist 依赖关键词和结构，容易误判 FULLY_COVERED 或 PARTIALLY_COVERED。

**Agent 作用：**
判断 requirement 是否真正“实质满足”，考虑可执行性、责任主体、流程完整性。

**预期处理逻辑：**

1. **输入**：章节文本、关键词命中、5状态初步判断、附件引用。
2. **步骤**：

   * 对每条 requirement，检查是否满足核心义务；
   * 检查条款是否模糊（vague）、可执行；
   * 对 PARTIALLY_COVERED、VAGUE、高风险 requirement 强制复核。
3. **输出**：

```json
{
  "requirement_id": "BCR-C-1.3",
  "coverage_status": "PARTIALLY_COVERED",
  "missing_elements": ["未指定具体 EU 责任主体", "未承诺赔偿责任"],
  "risk_level": "HIGH",
  "should_generate_finding": true
}
```

---

# 3. 实体角色识别 Agent

**问题场景：**
正则无法可靠识别 EU liable entity、集团成员、客户控制者、处理者角色。

**Agent 作用：**
基于上下文识别实体角色，提供可用角色表供专项 checker 和条款审查使用。

**预期处理逻辑：**

1. **输入**：全文实体列表、句子上下文。
2. **步骤**：

   * NLP 模型识别实体；
   * 判断其角色（EU责任主体 / BCR成员 / 客户控制者 / 外部接收方）；
   * 关联责任条款、赔偿承诺和第三方受益人权利。
3. **输出**：

```json
{
  "entities": [
    {"name": "GlobalTech Ltd", "location": "Ireland", "roles": ["EU liable entity", "liable entity"], "evidence": "..."},
    {"name": "GlobalTech France", "location": "France", "roles": ["BCR member"], "evidence": "..."}
  ]
}
```

---

# 4. Onward Transfer Agent

**问题场景：**
规则只检查 SCC / adequate safeguards，但容易漏掉“substantially similar obligations”或模糊承诺的情况。

**Agent 作用：**
判断 Onward Transfer 是否达到实质等同保护水平。

**预期处理逻辑：**

1. **输入**：条款文本、第三方列表、SCC 关键词命中情况。
2. **步骤**：

   * 检查是否提到“trusted partner”或“substantially similar”；
   * 判断是否包含 SCC / adequate safeguards / equivalent protection；
   * 输出风险等级及缺失点。
3. **输出**：

```json
{
  "finding_type": "ONWARD_TRANSFER_WEAK_STANDARD",
  "risk_level": "MEDIUM",
  "finding": "...",
  "recommendation": "明确要求第三方使用 SCC 或等效保障"
}
```

---

# 5. TIA 完整性 Agent

**问题场景：**
TIA 清单关键词式检查不能判断流程完整性。

**Agent 作用：**
复核 TIA 是否形成完整、可执行的评估机制。

**预期处理逻辑：**

1. **输入**：TIA章节、附件、政府访问条款。
2. **步骤**：

   * 检查评估方法、频率、责任方、记录要求、补充措施、暂停机制；
   * 判断是否符合 EDPB 01/2020 六步法。
3. **输出**：

```json
{
  "tia_completeness": "incomplete",
  "missing_elements": ["未说明定期评估", "未说明补充措施"],
  "risk_level": "MEDIUM",
  "suggested_revision_points": ["增加六步法记录", "明确补充措施"]
}
```

---

# 6. 附件证据覆盖 Agent

**问题场景：**
附件证据未区分正文与附件来源，可能误判 requirement 已覆盖。

**Agent 作用：**
判断正文 vs 附件覆盖，并生成补充意见。

**预期处理逻辑：**

1. **输入**：正文文本、附件文本、requirement 规则。
2. **步骤**：

   * 判断 requirement 是否可由附件支撑；
   * 标记正文/附件来源；
   * 判断 coverage 是否满足要求。
3. **输出**：

```json
{
  "requirement_id": "BCR-C-1.1",
  "coverage_source": "annex_support_only",
  "assessment": "正文提到成员受约束，但具体机制在内部协议附件",
  "risk_level": "MEDIUM"
}
```

---

# 7. INCORRECT 状态 Agent

**问题场景：**
部分条款虽然写了，但写错或写偏（例如 BCR-C 文档写成处理者条款）。

**Agent 作用：**
判断条款方向是否错误或责任主体错误。

**预期处理逻辑：**

1. **输入**：条款文本、requirement、实体角色。
2. **步骤**：

   * 判断条款是否偏离 requirement 核心义务；
   * 结合实体角色判断责任归属；
   * 标记 INCORRECT 并生成说明。
3. **输出**：

```json
{
  "coverage_status": "INCORRECT",
  "finding": "该条款将数据主体权利行使完全指向客户，与文档声明的BCR-C角色不一致",
  "risk_level": "HIGH"
}
```

---

# 8. 法规引用 grounding Agent

**问题场景：**
RAG 检索可能返回不相关法规，影响报告可信度。

**Agent 作用：**
校验法规引用是否真正支撑对应 finding。

**预期处理逻辑：**

1. **输入**：finding、条款文本、RAG 返回法规列表。
2. **步骤**：

   * 区分 primary / supporting / discarded basis；
   * 绑定法规到具体问题。
3. **输出**：

```json
{
  "finding_id": "BCR-F-003",
  "primary_basis": [{"source":"GDPR","article":"47(1)(b)","used_for":"第三方受益人权利"}],
  "supporting_basis": [{"source":"EDPB","used_for":"说明BCR条款应包含第三方受益人权利"}],
  "discarded_basis": [{"source":"SCC","reason":"不直接支撑该问题"}]
}
```

---

# 9. 审批阻断复核 Agent

**问题场景：**
当前 RiskAggregator 平均分可能稀释核心审批阻断项。

**Agent 作用：**
复核核心 requirement 缺失是否触发审批阻断。

**预期处理逻辑：**

1. **输入**：所有 findings、risk_level、rating。
2. **步骤**：

   * 检查核心 requirement（EU责任主体、第三方受益人、BCR类型、Binding Mechanism）是否缺失或错误；
   * 如触发，则强制上调 overall rating。
3. **输出**：

```json
{
  "approval_blockers": ["缺失第三方受益人权利","未指定EU责任主体"],
  "rating_adjustment":"HIGH"
}
```

---

# 10. 可执行整改建议 Agent

**问题场景：**
报告建议固定模板化，不够针对实际缺陷。

**Agent 作用：**
生成可操作、可直接嵌入文档的整改建议。

**预期处理逻辑：**

1. **输入**：finding、原文条款、法规依据、文档语言、BCR类型。
2. **步骤**：

   * 分析缺失或错误条款；
   * 生成可插入文本（遵循法规要求和文档风格）；
   * 绑定到具体章节和 requirement。
3. **输出**：

```json
{
  "fix_type": "INSERT_CLAUSE",
  "insert_location": "After Chapter 8 Liability",
  "suggested_text": "Data subjects shall have third-party beneficiary rights to enforce...",
  "rationale": "补足GDPR Article 47(1)(b)要求的数据主体可执行权利"
}
```

---

# ✅ 总结

**需要 Agent 并且能解决核心问题的地方：**

| 功能模块            | Agent 作用              | 解决问题                                     |
| --------------- | --------------------- | ---------------------------------------- |
| 类型判定            | TypeReasoningAgent    | 纠正 unknown/fallback，区分 BCR-C/BCR-P/mixed |
| Requirement 覆盖  | CoverageAgent         | 实质覆盖判断，纠正关键词误判                           |
| 实体角色识别          | ActorRoleAgent        | EU责任主体、集团成员、客户控制者准确识别                    |
| Onward Transfer | OnwardTransferAgent   | 判断传输保护是否达到实质等同标准                         |
| TIA 完整性         | TIAReasoningAgent     | 判断评估机制是否完整、可执行                           |
| 附件证据            | EvidenceCoverageAgent | 判断正文 vs 附件覆盖，解决材料包问题                     |
| INCORRECT 状态    | IncorrectStatusAgent  | 检测写错条款或责任主体错配                            |
| 法规引用            | LegalGroundingAgent   | 检验法规是否真正支撑 finding                       |
| 审批阻断            | ApprovalRiskAgent     | 复核核心审批阻断项，防止平均分稀释                        |
| 整改建议            | RemediationAgent      | 生成可执行整改条款，替换固定模板                         |

每个 Agent 的逻辑都基于**输入文档 + 规则/信号 + NLP/推理模型 + 输出结构化 finding**，并在 pipeline 中明确触发条件和 fallback。

这套设计能显著提升 BCR 自动审查的**准确性、可解释性、合规可信度**。
