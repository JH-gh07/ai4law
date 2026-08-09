# DataComplyFlow 全模块运行结果全面审计报告

> 审计日期：2026-08-09  
> 审计范围：`tmp/` 下 11 个模块共计 98 个文件（最新一次运行结果）  
> 审计维度：格式、渲染、功能能力、业务能力、模块内文件关系与数据链路

---

## 一、每个功能内的文件关系与数据链路

### 通用层次模型

所有使用渲染管线的模块（除 diagnosis）均遵循以下文件产出链：

```text
用户输入 ──→ payload
              │
              ▼
    ┌─── 规则引擎层 ────┐
    │ rule_engine_result │  ← 确定性规则判断（us_14117/eu_scc/cpra/bcr）
    │ path_judgment       │  ← 路径判断（assessment）
    │ need_assessment     │  ← 需求预判（dpia）
    │ route_decision      │  ← 路径决策（tia）
    └────────────────────┘
              │
              ▼
    ┌─── 事实层 ─────────┐
    │ facts_json          │  ← FactItem[]：结构化事实提取
    └────────────────────┘
              │
              ▼
    ┌─── 问题层 ─────────┐
    │ issue_list_json     │  ← IssueItem[]：合规问题识别
    │ findings_json       │  ← (eu_scc专用) 条款级审查发现
    └────────────────────┘
              │
              ▼
    ┌─── 证据层 ─────────┐
    │ evidence_chain_json │  ← EvidenceItem[]：证据链构建
    └────────────────────┘
              │
              ▼
    ┌─── LLM 生成层 ─────┐
    │ compliance_reasoning│  ← 合规推理（assessment专用）
    │ legal_grounding     │  ← 法律依据映射
    │ writing_strategy    │  ← 写作策略
    │ generation_basis    │  ← 生成上下文包（传给LLM的完整prompt material）
    │ document_ir         │  ← 文档中间表示（pipia/bcr/tia/eu_scc）
    └────────────────────┘
              │
              ▼
    ┌─── 渲染输出层 ─────┐
    │ markdown.md         │  ← 正文 Markdown
    │ docx.docx           │  ← 渲染后的 Word 文档
    │ pdf.pdf             │  ← 渲染后的 PDF
    │ xlsx.xlsx           │  ← 结构化数据Excel（如有）
    │ zip.zip             │  ← 全量产物包
    │ citation_map_json   │  ← 引用→脚注映射
    │ trace_manifest      │  ← 执行轨迹清单
    │ internal_markdown    │  ← 内部审查版报告
    │ internal_review_md   │  ← AI内部检验文本
    │ annotated_docx       │  ← 带标注的审查文档（eu_scc专用）
    └────────────────────┘
```

---

### 1.1 assessment — 文件关系链

```text
用户输入 payload
    │
    ├── path_judgment_json     ← 规则引擎：路径判断(scc_or_certification, MEDIUM)
    ├── facts_json (22项)      ← 结构化事实提取
    ├── issue_list_json (10项) ← 合规问题识别（包含severity BLOCKER/HIGH/MEDIUM）
    ├── evidence_chain_json (4项) ← 证据链（但legal_basis/document_refs全空）
    │
    ├── compliance_reasoning_json/md ← 合规推理（8维度逐项评估）
    ├── legal_grounding_json    ← 法律依据映射（by_issue: 10个issue→法规）
    ├── writing_strategy_json   ← 写作策略
    ├── generation_basis_pack_json (464KB) ← 传给LLM的完整上下文包
    │
    ├── markdown.md (113行)     ← 对客报告正文
    ├── body_markdown.md        ← 仅正文内容（无元数据）
    ├── official_markdown.md    ← 对外版（当前与markdown.md相同）
    ├── internal_markdown.md    ← 内部工程版（含【待核验】标注）
    ├── internal_review_md.md   ← AI审查评语（内外表达策略）
    ├── compliance_reasoning_md.md ← 合规推理说明
    ├── docx.docx (38KB)        ← Word渲染
    ├── pdf.pdf (7KB)           ← PDF渲染
    ├── material_checklist_json/xlsx ← 材料清单（仅1项）
    ├── citation_map_json       ← 引用映射（10条引用，0条脚注）
    ├── trace_manifest.json     ← 执行轨迹
    └── zip.zip (134KB)         ← 全量打包
```

**关键断链**：citation_map 有10条引用但footnote_map为空——引用未映射到脚注编号。

---

### 1.2 pipia — 文件关系链

```text
用户输入 payload
    │
    ├── facts / issues / evidence_chain ← 内嵌在result.json中
    ├── document_ir_json (41KB)    ← 文档中间IR（含sections/diagnostics）
    │
    ├── markdown.md (205行, 9236字符) ← 正文报告（11个模块中内容最丰富）
    ├── docx.docx (45KB)
    ├── pdf.pdf (26KB)
    ├── citation_map_json (222KB)  ← 89条引用, 22条脚注（最多）
    └── zip.zip (81KB)
```

**关键断链**：
- citation_map 89条引用项但仅22条脚注（75%缺失映射）
- 正文2处 `{{CIT-xxx}}` 截断标记残留
- 第166行表格行截断

---

### 1.3 dpia — 文件关系链

```text
用户输入 payload
    │
    ├── need_assessment_json  ← 规则判定：需要DPIA（4条触发理由，正确）
    ├── facts_json (37项)
    ├── issue_list_json (7项)
    ├── evidence_chain_json (7项)
    ├── legal_grounding_json (by_issue: 7 keys)
    ├── writing_strategy_json
    ├── generation_basis_pack_json (247KB) ← 上下文包已构建
    │
    ├── markdown.md (52行, 1219字符) ← 仅第0章有内容，1-7章全为占位
    ├── docx.docx (36KB)
    └── pdf.pdf (4KB)
```

**关键断链**：generation_basis_pack构建完毕但9个Agent全未执行——规则层到LLM层断裂。

---

### 1.4 eu_scc — 文件关系链

```text
用户输入 payload
    │
    ├── rule_engine_result_json ← 条款比较 + 附录审查 + TIA审查
    ├── findings_json (8项)     ← 条款级发现（6/8 original_text为空, 7/8 suggested_text为空）
    ├── document_ir_json (29KB)  ← 文档IR
    │
    ├── markdown.md (200行, 5911字符) ← 正文（第158行截断）
    ├── annotated_docx.docx (40KB) ← 带标注的审查文档
    ├── docx.docx (41KB)
    ├── pdf.pdf (16KB)
    └── citation_map_json (16KB)
```

**关键断链**：第158行正文在"健康数据属于GDPR第"处截断；findings原始/建议文本未填充。

---

### 1.5 bcr — 文件关系链

```text
用户输入 payload
    │
    ├── bcr_type_classification ← BCR-C判定
    ├── findings (26项)         ← 条款级发现
    ├── missing_requirements (2项: BCR-C-1.7, BCR-C-1.10)
    ├── document_ir_json (14KB) ← 文档IR（sections为空壳）
    │
    ├── markdown.md (88行) ← 审查表 + 整改建议
    ├── docx.docx (39KB)
    ├── pdf.pdf (18KB)
    ├── citation_map_json (2条引用, 2条脚注) ← 严重不足
    └── zip.zip (59KB)
```

**关键断链**：26个findings但仅2条引用注册——引用系统几乎完全绕过。

---

### 1.6 us_14117 — 文件关系链

```text
用户输入 payload
    │
    ├── rule_engine_result_json ← 红黄绿灯(YELLOW) + 安全措施缺口21项
    ├── facts_json (37项)
    ├── issue_list_json (6项)
    ├── evidence_chain_json (6项)
    │
    ├── markdown.md (13行, 1184字符) ← 正文结构崩坏（超长非换行文本）
    ├── docx.docx ← **0字节空文件（渲染完全失败）**
    ├── pdf.pdf (11KB)
    ├── xlsx.xlsx
    └── zip.zip (19KB)
```

**关键断链**：docx.docx为0B空文件；markdown正文严重格式崩坏。

---

### 1.7 cn_flow — 文件关系链

```text
用户输入 payload
    │
    ├── facts_json (9项)
    ├── issue_list_json (2项)
    ├── evidence_chain_json (2项)
    │
    ├── markdown.md (43行, 556字符) ← 5章中3章为"LLM未配置"占位
    ├── docx.docx (36KB)
    └── pdf.pdf (5KB)
```

**关键断链**：3/5章LLM未配置占位——LLM章节生成半失效。

---

### 1.8 cpra — 文件关系链

```text
用户输入 payload
    │
    ├── gap_items (5条: 3 HIGH + 2 MEDIUM)
    │
    ├── markdown.md (27行, 437字符) ← 4章中3章为"LLM未配置"占位
    ├── docx.docx (36KB)
    ├── pdf.pdf (6KB)
    ├── citation_map_json (3条引用, footnote_map为空)
    └── zip.zip (41KB)
```

**关键断链**：3/4章LLM未配置占位；citation完全未生效。

---

### 1.9 tia — 文件关系链

```text
用户输入 payload
    │
    ├── route_decision ← 路径决策(full_tia_scc)
    ├── country_risk   ← 国家风险评估
    ├── measure_assessments ← 措施评估
    ├── document_ir_json (34KB) ← 文档IR（sections为空壳）
    │
    ├── markdown.md (181行, 7308字符) ← 正文（6处【待核验】标记泄漏）
    ├── docx.docx (43KB)
    ├── pdf.pdf (20KB)
    └── citation_map_json (4KB)
```

**关键断链**：确定性评估结论与Agent生成文本脱节；工程标记泄漏到对外报告。

---

### 1.10 review — 文件关系链

```text
用户输入 payload
    │
    ├── result.risk_level = "高风险"
    ├── result.issue_counts = {HIGH:23, MEDIUM:15, LOW:3}  ← 共41个问题
    │
    ├── docx.docx (48KB)  ← 审查报告
    ├── report.docx (48KB) ← 与docx.docx是同一文件
    └── pdf.pdf (90KB)
```

**关键断链**：无markdown输出；无JSON中间产物；docx和report是同一路径的副本。

---

### 1.11 diagnosis — 文件关系链

```text
用户输入 payload
    │
    └── result.json (仅此1个文件)
          ├── recommended_path: "exemption"
          ├── matched_rule_id: "no_personal_info"
          ├── conclusion_source: "rule"  ← 9规则决策树，非LLM
          └── confidence: "HIGH"
```

**无渲染产物**（预期行为，纯诊断不产生报告文件）。

---

## 二、渲染问题

### R1 【严重】us_14117 DOCX 渲染完全失败
- **文件**：`tmp/us_14117/docx.docx`
- **症状**：0 字节空文件
- **影响**：用户无法获取 Word 格式报告
- **根因**：render path→文件系统路径映射失败，或 docx 模板变量替换异常导致写入空文件

### R2 【严重】assessment citation_map footnotes 回写失败
- **文件**：`tmp/assessment/citation_map_json.json`
- **症状**：`all_items` 有10条引用，`footnote_map` 为 `{}`（空字典）
- **影响**：报告正文虽无 `{{CIT-xxx}}` 残留，但无任何脚注编号映射，脚注列表无法生成
- **根因**：CitationRegistry.assign_footnote_number() 未被调用，或 postprocessor 仅做了 marker 删除但未调用 build_citation_map_section()

### R3 【严重】pipia 正文残留 `{{CIT-xxx}}` 截断标记
- **文件**：`tmp/pipia/markdown.md`
- **位置1**（第117行）：`{{CIT-CN-CNLAW003-ART50` — 标记未闭合即截断
- **位置2**（第139行）：`{{CIT-CN-CN_` — 标记在途中截断
- **影响**：报告正文出现原始引用标记污染
- **根因**：LLM 输出的 `{{CIT-xxx}}` 在生成中途因 token 限制被截断，postprocessor 正则无法匹配不完整标记

### R4 【严重】dpia 正文 7/7 章全为占位文本
- **文件**：`tmp/dpia/markdown.md`
- **症状**：第1~7章均为 `（X. 章节名：LLM未配置，此处为占位内容。请根据...人工撰写。）`
- **状态矛盾**：`_result.json` 中 `state: COMPLETED`，`chapters_count: 7`——但7章全空
- **特殊之处**：第0章（必要性预判）由规则引擎生成了实际内容，说明**规则层→LLM层断裂**
- **根因**：9个DPIA Agent（processing_activity → ... → consistency_repair）全部未触发执行，直接fallback到占位文本

### R5 【严重】cpra markdown 3/4 章节为占位文本
- **文件**：`tmp/cpra/markdown.md`
- **症状**：4章中仅第3章(差距与风险)有规则引擎产出的5条gap，其余3章占位
- **正文量**：仅 437 字符，不可用
- **对比**：`_result.json` 中 `chapters: 6章` 和 `gap_items: 5条` 数据齐全——结构化数据层正常，渲染层失联

### R6 【严重】cn_flow markdown 3/5 章节为占位文本
- **文件**：`tmp/cn_flow/markdown.md`
- **症状**：第1章(业务概览)、第2章(数据清单)、第5章(缓释措施)为占位
- **异常特征**：第3章(实体筛查)和第4章(风险矩阵)有实际内容——说明**部分Agent执行成功，部分失败**（混合失效）

### R7 【高】eu_scc 正文在 Clause 处截断
- **文件**：`tmp/eu_scc/markdown.md`
- **位置**：第158行 `健康数据属于GDPR第` — 内容戛然而止
- **影响**："Annex I.B 特殊类别数据误判" 小节内容不完整

### R8 【高】us_14117 markdown 正文格式崩坏
- **文件**：`tmp/us_14117/markdown.md`
- **症状**：13行正文每行都是超长连续文本（无换行），`## 风险详情` 一节在单行内包含了表格数据、人员清单、风险矩阵全部信息的原始文本dump
- **根因**：LLM 生成阶段丢失了换行符，或 markdown 格式化未执行

### R9 【中】pipia 正文第166行表格截断
- **文件**：`tmp/pipia/markdown.md`
- **症状**：整改计划表第3行 `| 3 | 敏感信息识别与保护不足："ProductCategoryPreference"` 后无后续行

### R10 【中】tia 工程标注 `【待核验：缺少法规依据】` 泄漏到对外报告
- **文件**：`tmp/tia/markdown.md`
- **出现次数**：6处（第26/45/93/148/173/177/179行）
- **同样波及**：`pipia`（多处）、`eu_scc`（2处）、`assessment internal_markdown`（多处）

### R11 【低】assessment markdown 双句号
- **位置**：第95行 `可走标准合同备案或认证路径。。`

### R12 【低】assessment 内容审查元文本泄漏
- **位置**：第91行 `"【已移除禁用措辞：完⋯全⋯合⋯规】"` — 系统删改了什么措辞暴露给用户

---

## 三、格式问题

### F1 【严重】pipia `{{CIT-xxx}}` 截断标记（同R3，格式+渲染双维度）
- 第117行 `{{CIT-CN-CNLAW003-ART50`
- 第139行 `{{CIT-CN-CN_`

### F2 【高】BCR 整改建议含未填充模板占位符
- **位置**：第82/85/86行
- **症状**：`[Company Name]`、`[EU Member State]`、`[Insert specific clause addressing the identified requirement...]`
- **根因**：模板变量替换步骤未执行

### F3 【高】BCR 法律依据字符串拼接异常
- **症状1**（第34行）：`；GDPR Article 33, 34` — 多余的前导分号
- **症状2**（第46-50行）：`GDPR (EU) 2016/679 第段落1条` — "第段落X条" 是错误的中文翻译格式，应为 `Art. 1`
- **症状3**（第35行）：`；EDPB Recommendations 01/2020, 1/2022` — 多余分号

### F4 【中】tia/assessment 内部枚举值泄漏为正文
- **tia**（第26行）：`"fulltiascc"` 应为 `"full TIA SCC"`
- **assessment**（多处）：`"sccorcertification"` 应为 `"标准合同或认证"`

### F5 【中】dpia 必要性预判含原始 Python dict 格式
- **位置**：第8-12行
- **症状**：`{'type': 'automated_decision_making', 'fact_refs': ['FACT-automated-decision'], 'reason': '系统涉及对个人的自动化评估或决策'}`
- **影响**：用户看到 Python repr 格式，非人类友好描述

### F6 【低】review result.json 缺空格
- **症状**：`"共识别 41 个问题7 个全局缺失项"` — "问题" 与 "7" 之间缺少空格

### F7 【低】BCR 空证据字段
- **位置**：第29/32行 `证据：` 后直接换行，无内容

### F8 【低】eu_scc 引用行过长且拥挤
- **位置**：第44行，多个引用拼接在一行内无分隔

### F9 【低】tia 正文含推测性语言
- **位置**：第28行 `【推测】基于数据出口方为控制者...`

---

## 四、功能能力问题

### C1 【严重】dpia Agent 链全部静默失败
- **症状**：9个Agent全部未执行，但 `state: COMPLETED`
- **证据**：`generation_basis_pack_json` = 247KB（上下文包已构建），但agent链未触发
- **根因**：Agent链前置条件检查（如LLM endpoint可达性）失败，但异常被吞没，直接走了fallback占位路径
- **业务影响**：dpia 功能实际上不可用

### C2 【严重】cpra/cn_flow LLM 章节生成半失效（混合失效）
- **症状对比**：
  - cpra: 4章中3章占位，仅规则引擎产出gap可显示
  - cn_flow: 5章中3章占位，仅第3/4章有实际内容
- **特征**：两个模块都使用 `module_generator.generate_chapter()` 且都是混合失效
- **根因推测**：某些章节的 `user_context` 超过 token 限制导致 LLM 返回空，或特定章节 system prompt 缺失
- **与dpia的区别**：dpia是全部Agent失效，cpra/cn_flow是部分章节失效——说明LLM连接本身可达，问题在章节级调用

### C3 【高】assessment state=COMPLETED 掩盖路径不匹配
- **症状**：path_judgment 推荐 scc_or_certification，但生成了安全评估报告
- **内部审查**：明确标注 `ISSUE-recommended-path-mismatch`
- **问题**：路径不匹配时不应返回 COMPLETED，应返回 `COMPLETED_WITH_WARNINGS` 或 `PARTIAL`

### C4 【高】pipia 引用映射丢失 75%
- **症状**：`citation_map.all_items` = 89条，`footnote_map` = 仅22条（25%）
- **影响**：67条引用无法获得脚注编号，溯源大规模失效
- **根因**：CitationRegistry.assign_footnote_number() 仅当正文中存在 `{{CIT-xxx}}` marker时才分配编号。LLM生成时未在所有引用处插入marker

### C5 【中】evidence_chain 关键字段系统性为空
- **受影响模块**：assessment, cn_flow, us_14117
- **症状**：所有EvidenceItem的以下字段均为 null/空：
  - `legal_basis`（法律依据）
  - `supporting_basis`（支持性依据）
  - `document_refs`（文档引用）
  - `rag_query_used`（RAG查询记录）
  - `usage_constraint`（使用约束）
- **根因**：build_evidence() 步骤预留了这些字段但未实现填充逻辑

### C6 【中】facts_json 的 supporting_material_refs 系统性为空
- **受影响模块**：assessment(22项), cn_flow(9项), us_14117(37项), dpia(37项)
- **症状**：所有FactItem的 `supporting_material_refs` 为空数组 `[]`
- **影响**：无法追踪事实来源（哪个事实来自哪个上传文件）

### C7 【中】eu_scc findings 原文/建议文本未填充
- **症状**：8项发现中 `original_text` 6/8为null，`suggested_text` 7/8为null
- **影响**：标注无原文对比，annotated_docx 中无法显示差异

### C8 【中】BCR citation 系统几乎绕过
- **症状**：26个findings有法律依据标注，但citation_map仅2条引用
- **根因**：Agent直接生成了引用文本（如"GDPR Article 47(1)(a) [1]"），绕过了CitationRegistry→marker→脚注的标准流程

### C9 【中】tia/bcr document_ir_json sections 为空壳
- **症状**：两个模块的document_ir都有13个元数据键但核心 `sections` 为空
- **根因**：document_ir规范已定义但实际填充逻辑未实现

### C10 【低】review 无中间产物 JSON 导出
- **症状**：41个问题仅以docx存在，无结构化issue_list/evidence_chain
- **影响**：review结果无法被其他模块消费或交叉校验

### C11 【低】diagnosis fact_provenance 序列化截断
- **症状**：`sensitive_personal_info_count` 字段值在JSON prettify后被截断

---

## 五、业务能力问题

### B1 【严重】LLM 不可用时多个模块标注假 COMPLETED
- **受影响的**：dpia, cpra, cn_flow
- **症状**：正文含"LLM未配置，此处为占位内容"，但state仍为COMPLETED/HIGH
- **业务风险**：用户收到表面完整但内容空洞的报告，可能基于空洞报告做出错误合规决策
- **建议**：当检测到占位文本时，state 必须设为 `PARTIAL_GENERATION` 或 `LLM_UNAVAILABLE`

### B2 【高】tia 确定性评估与 Agent 生成内容脱节
- **症状**：`route_decision`、`country_risk`、`measure_assessments` 三个确定性评估产出完整正确，但Agent生成正文时可能不引用或偏离这些结论
- **业务风险**：用户读到的Agent生成结论可能与底层确定性评估结论不一致
- **建议**：增加 post-generation consistency check，验证Agent输出与确定性结论是否一致

### B3 【中】BCR 整改建议模板变量泄漏
- **症状**：`[Company Name]` / `[EU Member State]` / `[Insert specific clause...]` 在对外报告中可见
- **业务影响**：降低报告专业可信度

### B4 【中】review 无结构化问题导出
- **症状**：41个问题(HIGH 23 + MEDIUM 15 + LOW 3)仅以docx存在
- **业务影响**：用户无法将问题导入项目管理工具逐条跟踪

### B5 【中】assessment material_checklist 仅1项
- **症状**：安全评估申报材料清单（通常20+项）仅检查了1条
- **业务影响**：用户无法判断材料是否齐备

### B6 【低】tia 正式报告中含推测性措辞
- **位置**：第28行 `【推测】基于...`
- **建议**：正式TIA不应使用推测性语言

### B7 【低】assessment 内容审查痕迹暴露
- **位置**：第91行 `【已移除禁用措辞：完⋯全⋯合⋯规】`
- **建议**：内容审查应做隐性替换，不应保留删除标记

### B8 【中】pipia 引用质量最高但完整性受损
- **正项**：89条引用(全模块最多)、22条脚注、205行正文(最丰富)、每段分析有法规引用
- **问题**：2处CIT截断+1处表格截断——**生成完成度校验缺失**
- **建议**：增加post-generation完整性检查（检测未闭合CIT标记、截断的表格行）

---

## 六、综合评分

| 模块 | 格式 | 渲染 | 功能 | 业务 | 综合 |
|------|:---:|:---:|:---:|:---:|:---:|
| **pipia** | ⚠️ | ⚠️ | ✅ | ✅ | **B+** |
| **bcr** | ⚠️ | ✅ | ✅ | ⚠️ | **B** |
| **tia** | ⚠️ | ✅ | ✅ | ⚠️ | **B** |
| **eu_scc** | ⚠️ | ⚠️ | ✅ | ✅ | **B-** |
| **assessment** | ⚠️ | ⚠️ | ⚠️ | ⚠️ | **B-** |
| **diagnosis** | ✅ | N/A | ✅ | ✅ | **A** |
| **review** | ⚠️ | ✅ | ✅ | ⚠️ | **B-** |
| **us_14117** | ❌ | ❌ | ❌ | ❌ | **D** |
| **cn_flow** | ❌ | ⚠️ | ❌ | ❌ | **D** |
| **cpra** | ❌ | ⚠️ | ❌ | ❌ | **D** |
| **dpia** | ❌ | ⚠️ | ❌ | ❌ | **F** |

---

## 七、优先修复路线图

### P0 — 阻塞性（本周）

| # | 问题 | 模块 | 修复方向 |
|---|------|------|---------|
| 1 | Agent链全静默失败，假COMPLETED | dpia | 增加Agent执行前可达性检查 + 失败时设state=LLM_UNAVAILABLE而非COMPLETED |
| 2 | DOCX渲染0字节 | us_14117 | 排查render_path→文件系统映射 + docx模板渲染异常处理 |
| 3 | LLM章节生成混合失效 | cpra, cn_flow | 排查章节级user_context token超限 + system prompt配置缺失 |

### P1 — 高优先级（本月）

| # | 问题 | 模块 | 修复方向 |
|---|------|------|---------|
| 4 | CIT标记截断残留 | pipia | postprocessor增加未闭合标记检测 + 截断处重试或清理 |
| 5 | footnote_map为空 | assessment | 确保CitationRegistry.assign_footnote_number()被调用 |
| 6 | evidence_chain字段全空 | assessment,cn_flow,us_14117 | 填充legal_basis/document_refs/rag_query_used |
| 7 | 工程标注泄漏到对外报告 | tia,pipia,eu_scc | 内外部文本过滤器分离 |
| 8 | BCR模板变量未替换 | bcr | 模板渲染前执行变量替换 |

### P2 — 中优先级（下个迭代）

| # | 问题 | 模块 | 修复方向 |
|---|------|------|---------|
| 9 | LLM输出截断检测与重试 | eu_scc,pipia | post-generation完整性检查 |
| 10 | state语义细化 | 全模块 | 增加PARTIAL_GENERATION/LLM_UNAVAILABLE/WITH_WARNINGS |
| 11 | tia确定性评估→Agent一致性校验 | tia | post-generation consistency check |
| 12 | material_checklist增强 | assessment | 从1项扩展到完整申报材料清单 |
| 13 | review增加JSON中间产物 | review | 输出结构化issue_list |
| 14 | document_ir填充实际内容 | tia,bcr | sections字段真实填充 |

### P3 — 低优先级（持续改进）

| # | 问题 | 模块 |
|---|------|------|
| 15 | 路径标识符格式化 (sccorcertification→标准合同或认证) | assessment |
| 16 | 法律依据拼接修正(去除前导分号/修正"第段落X条") | bcr |
| 17 | dpia necessity dict→自然语言 | dpia |
| 18 | eu_scc findings original_text/suggested_text填充 | eu_scc |
| 19 | review "问题"与数字间缺空格 | review |

---

> **审计总结**：11个模块、98个文件全覆盖。共发现问题 **R(渲染)12项 + F(格式)9项 + C(功能)11项 + B(业务)8项 = 合计40项**。  
> 核心结论：**pipia/bcr/tia/eu_scc 4个模块基本可用，需修复标记泄漏和截断；dpia/cpra/cn_flow/us_14117 4个模块存在严重LLM生成失效，实际不可用；assessment有路径匹配和引用映射问题；diagnosis状态最好。**
