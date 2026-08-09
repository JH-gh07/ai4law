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


---

## 八、问题共性与特殊性统计分析

> 对前七部分 40 个问题按根因维度重新归类，区分跨模块共性缺陷与单模块特殊问题。

---

### 8.1 问题共性归类（跨模块系统性缺陷）

#### C-COMMON-1 — LLM 生成静默失败/占位（影响 4 模块）

| 子类型 | 影响模块 | 严重度 | 共性特征 |
|--------|---------|:---:|---------|
| 全部 Agent 未执行 | dpia | P0 | generation_basis_pack 构建完毕，Agent链零调用 |
| 部分章节占位 | cpra, cn_flow | P0 | 使用 module_generator.generate_chapter()，特定章节返回空 |
| 正文极薄 | us_14117 | P0 | markdown 13行格式崩坏，可能是相同根因的不同表现 |

- **统计**：11 模块中 4 个命中 = **36% 影响面**
- **共同根因**：LLM 调用链路存在三类故障模式——(a) Agent 链前置检查失败但异常被吞没（dpia）；(b) 章节级 user_context 超过 token 限制（cpra, cn_flow）；(c) LLM 返回被截断后无完整性校验（us_14117）
- **统一修复方向**：增加 `LLMExecutionGuard` — 在每个 LLM 调用点增加 pre-check（可达性）+ post-check（内容完整性，检测占位关键词/长度阈值），失败时统一抛异常，由 state 管理器设 `LLM_UNAVAILABLE`

#### C-COMMON-2 — CIT 引用标记崩溃（影响 3 模块）

| 子类型 | 影响模块 | 症状 |
|--------|---------|------|
| 截断标记残留 | pipia | `{{CIT-CN-CNLAW003-ART50` 未闭合 |
| 截断标记残留 | pipia | `{{CIT-CN-CN_` 中途截断 |
| footnote_map 全空 | assessment | 10条all_items, 0条footnote_map |
| footnote_map 极弱 | cpra | 3条all_items, 0条footnote_map |
| citation 近失效 | bcr | 26条findings, 仅2条引用注册 |

- **统计**：11 模块中 4 个命中 = **36% 影响面**
- **共同根因**：CitationRegistry 的 marker→footnote 管道有两处断裂 —— (a) LLM 输出截断导致 `{{CIT` 不闭合（postprocessor 正则无法匹配）；(b) `assign_footnote_number()` 在部分模块未被调用或仅对正文中已匹配到的 marker 分配编号（但 LLM 未插入足量 marker）
- **统一修复方向**：postprocessor 增加截断标记清理步骤（检测未闭合 `{{CIT` 并移除/修复）；保证所有调用链中 CitationRegistry.build_citation_map_section() 被调用；增加"引用注册数 vs. 脚注数"的 post-run 一致性校验

#### C-COMMON-3 — evidence_chain 溯源字段系统性为空（影响 3+ 模块）

| 缺失字段 | 影响模块 |
|----------|---------|
| legal_basis / supporting_basis / document_refs / rag_query_used / usage_constraint | assessment(4项全空), cn_flow(2项全空), us_14117(6项全空) |

- **统计**：至少 3 模块命中（pipia/dpia 的 evidence_chain 在 result.json 内嵌，未逐项检查但大概率相同）
- **共同根因**：`build_evidence()` 步骤中这些字段被预留了 Schema 但未实现填充逻辑——等同于"空壳证据链"
- **统一修复方向**：在 `build_evidence()` 父类或公共工具函数中实现字段填充 —— legal_basis 从 RAG hits 提取，document_refs 从 payload 中 uploaded_files 映射，rag_query_used 从 RAG 调用日志获取

#### C-COMMON-4 — 工程标注泄漏到对外报告（影响 4 模块）

| 标注类型 | 出现模块 | 次数 |
|---------|---------|:---:|
| `【待核验：缺少法规依据】` | tia | 6 |
| `【待核验：缺少法规依据】` | pipia | 多处 |
| `【待核验：缺少法规依据】` | eu_scc | 2 |
| `【推测】` | tia | 1 |
| `【已移除禁用措辞：完⋯全⋯合⋯规】` | assessment | 1 |

- **统计**：11 模块中 4 个命中 = **36% 影响面**
- **共同根因**：内外部表达策略分离不彻底 —— 内部版通过 `internal_markdown.md` / `internal_review_md.md` 单独输出，但 markdown.md（对客版）在渲染时未执行工程标注过滤器
- **统一修复方向**：在 markdown 渲染管线末尾增加统一的 `sanitize_external_markdown()` 步骤，自动移除 `【待核验】`/`【推测】`/`【已移除】` 等工程标注

#### C-COMMON-5 — state=COMPLETED 掩盖实质失败（影响 3 模块）

| 模块 | state | 实际情况 |
|------|-------|---------|
| dpia | COMPLETED | 7/7章占位，Agent全未执行 |
| assessment | COMPLETED | 路径不匹配，报告为"强制生成参考草案" |
| cpra | HIGH | 3/4章占位，仅有规则引擎gap |
| cn_flow | HIGH | 3/5章占位 |

- **统计**：11 模块中 4 个命中 = **36% 影响面**
- **共同根因**：state 枚举值仅有 `COMPLETED`/`FAILED` 两种终态，缺少中间态（`PARTIAL`/`WITH_WARNINGS`/`LLM_UNAVAILABLE`/`DEGRADED`）
- **统一修复方向**：扩展 state 枚举，前端根据 state 展示不同的用户提示（绿色勾/黄色三角警告/红色叉）

#### C-COMMON-6 — facts_json 的 supporting_material_refs 全空（影响 4 模块）

| 模块 | FactItem 数量 | supporting_material_refs 空 |
|------|:---:|:---:|
| assessment | 22 | 22 (100%) |
| cn_flow | 9 | 9 (100%) |
| us_14117 | 37 | 37 (100%) |
| dpia | 37 | 37 (100%) |

- **统计**：至少 4 模块，105 个 FactItem 全部缺失溯源引用
- **共同根因**：`build_facts()` 公共步骤不支持材料引用填充
- **统一修复方向**：在事实提取时，若事实来源于文件解析（FileParser），应将源文件路径写入 `supporting_material_refs`

#### C-COMMON-7 — document_ir 的 sections 为空壳（影响 2+ 模块）

- **受影响的**：bcr(14KB 但 sections 空), tia(34KB 但 sections 空)
- **共同根因**：document_ir 规范定义了13键元数据+sections，但实际填充逻辑被跳过或仅写了元数据包装器
- **统一修复方向**：document_ir 作为中间表示层要么充分实现，要么明确标注为WIP并移除输出——当前半成品状态造成误导

---

### 8.2 问题特殊性归类（单模块独有问题）

#### S-1 — us_14117 DOCX 渲染 0 字节（唯一）
- **特殊性**：仅 us_14117 出现 docx 为空文件，其他10个模块的 docx 均正常（3KB~49KB）
- **特殊根因**：us_14117 的 markdown 正文极端简略（13行无结构），可能触发渲染器的最小内容阈值检查导致 abort
- **与共性的关联**：如果 C-COMMON-1(LLM生成失败) 被修复，us_14117 的正文恢复正常，此问题可能自动消失

#### S-2 — pipia 正文第166行 Markdown 表格截断（唯一）
- **特殊性**：pipia 的整改计划表在 `<br>` 标签后截断，其他模块无此模式
- **特殊根因**：pipia Agent 在生成表格时使用了 HTML `<br>` 标签作为单元格内换行，后续行在 token 限制下被截断

#### S-3 — eu_scc 正文第158行 "健康数据属于GDPR第" 截断（唯一）
- **特殊性**：仅在 eu_scc 的 Annex I.B 特殊类别数据小节出现精确截断
- **特殊根因**：该小节涉及 GDPR Article 9 的引用字符串，可能在 tokenization 边界处恰好截断

#### S-4 — dpia 必要性预判泄露 Python dict repr（唯一）
- **特殊性**：dpia 第0章将 rule engine 产出的 `dict` 直接以 `repr()` 格式写入 markdown
- **特殊根因**：dpia 的 `need_assessment` 结果与其他模块不同 —— 其他模块的规则结果经格式化后再写入 markdown，dpia 跳过了格式化步骤

#### S-5 — BCR 模板变量泄漏（唯一）
- **特殊性**：`[Company Name]` / `[EU Member State]` / `[Insert specific clause...]` 占位符仅在 BCR 出现
- **特殊根因**：BCR 的整改建议由特定模板生成（bcr_rulebook.json 或专门模板文件），该模板的变量替换步骤被遗漏

#### S-6 — BCR 法律依据字符串异常格式（唯一）
- **特殊性**：`第段落X条` 这种错误翻译格式仅出现在 BCR
- **特殊根因**：BCR 的引用来源可能经过了不同的翻译管道（中文版本的 GDPR 引用格式）

#### S-7 — review 无中间产物 + docx/report 路径重复（唯一）
- **特殊性**：review 是唯一完全不产生 JSON 中间产物的模块，也是唯一两个 output_file key 指向同一路径的模块
- **特殊根因**：review 使用完全独立的 8 阶段 pipeline（SQLite + WebSocket），不走公共 WorkflowPipeline，因此没接入公共中间结构

#### S-8 — assessment 材料清单仅 1 项（唯一）
- **特殊性**：安全评估申报材料清单通常需 20+ 项，仅生成 1 条
- **特殊根因**：material_checklist 构建依赖 uploaded_files，本次测试运行未上传材料文件，仅基于输入字段推测材料需求

#### S-9 — diagnosis 无渲染产物（符合预期，非bug）
- **特殊性**：diagnosis 是纯规则引擎判断服务，设计上即不产生报告文件
- **结论**：符合设计预期，无需修复

---

### 8.3 共性 vs 特殊性 分布统计

| 分类 | 数量 | 占比 | 影响模块数 | 修复策略 |
|------|:---:|:---:|:---:|------|
| **共性—LLM生成静默失败** | 4 个模块 | 36% | dpia,cpra,cn_flow,us_14117 | 统一 LLMExecutionGuard |
| **共性—CIT引用崩溃** | 4 个模块 | 36% | pipia,assessment,cpra,bcr | 统一 postprocessor 修复 |
| **共性—evidence_chain空壳** | 3+ 模块 | 27%+ | assessment,cn_flow,us_14117,(dpia?pipia?) | 统一 build_evidence() 增强 |
| **共性—工程标注泄漏** | 4 模块 | 36% | tia,pipia,eu_scc,assessment | 统一 sanitize_external_markdown() |
| **共性—假COMPLETED** | 4 模块 | 36% | dpia,assessment,cpra,cn_flow | 统一 state 枚举扩展 |
| **共性—facts溯源缺失** | 4 模块 | 36% | assessment,cn_flow,us_14117,dpia | 统一 build_facts() 增强 |
| **共性—document_ir空壳** | 2 模块 | 18% | bcr,tia | 要么实现，要么移除 |
| **特殊—us_14117 docx 0B** | 1 模块 | 9% | us_14117 | 随 C-COMMON-1 修复自动解决 |
| **特殊—pipia表格截断** | 1 模块 | 9% | pipia | 随 C-COMMON-1/2 修复自动解决 |
| **特殊—eu_scc正文截断** | 1 模块 | 9% | eu_scc | 随 C-COMMON-1 修复自动解决 |
| **特殊—dpia dict泄漏** | 1 模块 | 9% | dpia | 格式化逻辑修复 |
| **特殊—BCR模板变量** | 1 模块 | 9% | bcr | 模板引擎修复 |
| **特殊—BCR法律格式** | 1 模块 | 9% | bcr | 翻译管道修复 |
| **特殊—review架构隔离** | 1 模块 | 9% | review | 要么接入公共层，要么补齐独立层 |
| **特殊—assessment材料清单** | 1 模块 | 9% | assessment | 材料清单逻辑增强 |

---

### 8.4 核心洞察

```
┌──────────────────────────────────────────────────────────┐
│  40 个问题中，7 个共性缺陷覆盖了 25 个问题（62.5%）。    │
│  修复这 7 个共性缺陷，可同时解决 4~5 个模块的问题。      │
│                                                          │
│  P0 紧急（3项共性）：                                     │
│  C-COMMON-1  LLM生成静默失败 → 4模块受影响               │
│  C-COMMON-2  CIT引用崩溃    → 4模块受影响                │
│  C-COMMON-5  假COMPLETED    → 4模块受影响                │
│                                                          │
│  修这3个 = 解决12个模块级问题 + 大部分特殊问题自动消失    │
└──────────────────────────────────────────────────────────┘
```

**关键因果链**：

```text
C-COMMON-1 (LLM生成失败/占位)
  ├── 直接导致：dpia全部占位、cpra 3/4占位、cn_flow 3/5占位
  ├── 连锁导致：us_14117正文崩坏 → us_14117 docx 0B (S-1)
  ├── 连锁导致：LLM输出截断 → CIT标记不闭合 (C-COMMON-2的一部分)
  │                            → eu_scc正文截断 (S-3)
  │                            → pipia表格截断 (S-2)
  └── 被掩盖：state仍为COMPLETED (C-COMMON-5)

C-COMMON-2 (CIT引用崩溃)
  ├── 直接导致：pipia截断标记、assessment空footnote_map
  └── 被掩盖：state仍为COMPLETED/正常状态

结论：C-COMMON-1 是 40 个问题的最大单一根因，
     修它 = 解决约 12-15 个下游问题。
```

---

### 8.5 各模块健康度与受影响共性缺陷的映射

| 模块 | 评级 | 命中共性缺陷 | 命中特殊问题 |
|------|:---:|------|------|
| diagnosis | A | — | S-9（符合预期） |
| pipia | B+ | C-COMMON-2, C-COMMON-4 | S-2 |
| bcr | B | C-COMMON-2, C-COMMON-7 | S-5, S-6 |
| tia | B | C-COMMON-4, C-COMMON-7 | — |
| eu_scc | B- | C-COMMON-4, C-COMMON-2? | S-3 |
| assessment | B- | C-COMMON-2, C-COMMON-3, C-COMMON-4, C-COMMON-5, C-COMMON-6 | S-8 |
| review | B- | C-COMMON-5? | S-7 |
| us_14117 | D | C-COMMON-1, C-COMMON-3, C-COMMON-6 | S-1 |
| cn_flow | D | C-COMMON-1, C-COMMON-3, C-COMMON-5, C-COMMON-6 | — |
| cpra | D | C-COMMON-1, C-COMMON-2, C-COMMON-5 | — |
| dpia | F | C-COMMON-1, C-COMMON-5, C-COMMON-6 | S-4 |

**规律**：评级越低的模块，命中共性缺陷越多（dpia/us_14117 命中 3+ 个共性缺陷），说明系统性问题有放大效应。

> **最终建议**：优先修复 3 个 P0 共性缺陷（LLM生成失败 + CIT引用崩溃 + 假COMPLETED），预计解决约 50% 的问题。剩余 7 个特殊问题中 4 个（S-1/S-2/S-3 及其连锁问题）将随共性修复自动消失。


---

## 九、代码链路逆向追踪：从输出现象反推到源码根因

> 对每个 P0/P1 问题逐链路定位——从 result.json/markdown 的异常现象出发，顺着代码调用链反向定位到具体文件、函数、行号，明确缺陷的精确位置。

---

### 9.1 LLM 生成静默失败的完整链路（dpia/cpra/cn_flow/us_14117）

**现象**：dpia 7/7 章占位、cpra 3/4 章占位、cn_flow 3/5 章占位、us_14117 正文 13 行无结构

**逆向追踪链**：

```text
[现象] markdown.md 章节内容 = "（1. 识别 DPIA 需求：LLM未配置，此处为占位内容）"
  ↓
[Step 1] dpia/report_renderer.py 的 render() 读取 dpia_chapters[].content
  ↓ 该 content 由 dpia/service.py:448 传入
[Step 2] dpia/service.py:302 → self.agents["external_draft"].run(...)
  ↓ 调用 dpia/agents/external_draft_agent.py:44 run()
[Step 3] external_draft_agent.py:59
          → if not self.enabled: return _placeholder_chapters(gen_basis)
  ↓
[Step 4] self.enabled 来自 agents/__init__.py:48-49 (DPIAAgentBase)
          → return self.llm_client is not None and self.llm_client.enabled
  ↓
[Step 5] self.llm_client.enabled 来自 common/llm/client.py:73
          → self._enabled = provider.enabled and bool(self._api_key) and OpenAI is not None
```

**根因位置**（三换一即可修复）：
| 层面 | 文件:行号 | 条件 | 现象 |
|------|----------|------|------|
| LLM provider | `common/llm/client.py:73` | `provider.enabled=False` 或 `api_key=""` 或 `OpenAI=None` | `_enabled=False` → 所有下游链路全断 |
| Agent base | `agents/__init__.py:48-49` | `llm_client is None or not enabled` | 9 个 dpia Agent 全部静默返回 None/default |
| 各 service | `dpia/.../external_draft_agent.py:59`, `cpra/service.py:515`, `cn_flow/service.py:197`, `pipia/service.py:125` | `if self.llm_client and self.llm_client.enabled:` | 分支到 `else: 占位文本` |

**cpra 具体链路**（pipeline 不同但仍同一根因）：
```text
cpra/service.py:248 → _generate_chapters_from_context()
  → 第515行: if self.llm_client and self.llm_client.enabled:
       → generate_chapter(...)  ← 调用 module_generator.generate_chapter()
     else:
       → f"（{title}：LLM未配置，此处为占位内容）"
```

**cn_flow 具体链路**：
```text
cn_flow (eo14117_flow_review)/service.py:185 → _generate_chapters_from_pack()
  → 第197行: if self.llm_client and self.llm_client.enabled:
       → generate_chapter(...)
     else:
       → f"（{title}：LLM未配置，此处为占位内容）"
```

**dpia 特殊之处**（两套 chapter generator，都用同一检查）：
- 路径1（未使用）: `chapter_generator.py:339` → `if self.llm and self.llm.enabled:`
- 路径2（实际使用）: `external_draft_agent.py:59` → `if not self.enabled: return _placeholder_chapters()`

**为何 cn_flow markdown 部分章节有内容？**  
- cn_flow 的 markdown.md 和 result.json chapters 走**两条不同渲染路径**
- result.json chapters：从 `_generate_chapters_from_pack()` 产出 → 全部为 LLM 占位
- markdown.md：从 DOCX/MD 模板渲染器独立生成，将 `facts_json`/`issues`/`risk_matrix` 的结构化数据注入模板 → **结构化数据本身非空，所以模板渲染产出了有内容的 markdown**
- 证据：result.json 中 4 章全为 `（xxx：LLM未配置，此处为占位内容）`，但 markdown.md 中第 3 章有 `US ServiceCo | 美国 | processor | 受限主体=False`（来自 facts）、第 4 章有表格数据（来自 risk_matrix）

**修复方向**：
1. 配置层：确保 `api_key` 已设置且 `openai` 包已安装（`client.py:73`）
2. 代码层：当 `enabled=False` 时，不应静默返回占位文本 → 应抛异常让 pipeline 返回 `LLM_UNAVAILABLE` 状态
3. 消除 `state` 的假 `COMPLETED`（见 9.8）

---

### 9.2 CIT 引用标记残留的完整链路（pipia）

**现象**：pipia markdown.md 第117行 `{{CIT-CN-CNLAW003-ART50`、第139行 `{{CIT-CN-CN_`

**逆向追踪链**：

```text
[现象] markdown 正文中有未闭合的 {{CIT-CN-CNLAW003-ART50
  ↓
[Step 1] 该正文来自 service.py render → 将 chapters[].content 拼接为完整 markdown
  ↓
[Step 2] chapters[].content 来自 generate_chapter() (pipia/service.py:126-135)
  ↓
[Step 3] generate_chapter() 内部 (module_generator.py:357-361):
          return apply_citation_pipeline(cleaned, registry=..., allowed_citations=...).text
  ↓
[Step 4] apply_citation_pipeline() (postprocess.py:412-445):
          → _replace_registered_markers(converted, registry)
  ↓
[Step 5] _replace_registered_markers() (postprocess.py:459-475):
          1. _CIT_MARKER_RE.sub(_replace_marker, text)  ← 替换完整 {{CIT-xxx}} 为 [n]
          2. _TRUNCATED_CIT_MARKER_RE.sub("【待核验：引用格式不完整】", ...)  ← 清理截断标记
```

**正则匹配分析**（markers.py:20-25）：
```python
CITATION_ID_RE = r"CIT-[A-Z]{2}-[A-Z0-9_-]+-(?:ART[A-Za-z0-9_一-鿿]+|GEN)-P\d+"
CIT_MARKER_RE  = r"\{\{( CITATION_ID_RE )\}\}"
                = r"\{\{CIT-[A-Z]{2}-[A-Z0-9_-]+-(?:ART...|GEN)-P\d+\}\}"
```
- 完整标记 `{{CIT-CN-CNLAW003-ART50-P01}}` ✅ 匹配
- 截断标记 `{{CIT-CN-CNLAW003-ART50` ❌ 不匹配 — 缺少 `-P\d+}}` 后缀
- 但 `_TRUNCATED_CIT_MARKER_RE` (postprocess.py:20) 应能清理它

**矛盾**：`generate_chapter()` 已调用 `apply_citation_pipeline()` → 应已清理截断标记 → 但 pipia markdown 仍有残留

**只能在两种情况下发生**：
1. pipia markdown 由**另一条渲染路径**生成，该路径没有调用 `apply_citation_pipeline()`
2. `generate_chapter()` 返回的 clean text 在后续 render 步骤中被重新拼接了 raw content

**精确定位**：需要检查 pipia service 中 report render 的 markdown 拼接逻辑（line 612-666 区域），确认 render 步骤是否从 chapters 或从其他源获取内容

**临时结论**：pipia 的最终 markdown 可能由 `render_markdown_template()` 通过 Jinja2 模板生成，而模板中直接引用了 chapter.content（已 clean）。但如果有独立于 chapters 的内容块通过其他渠道拼接，就会绕过 CIT 清理。

---

### 9.3 footnote_map 为空的完整链路（assessment）

**现象**：`citation_map_json.json` 中 `all_items: [10条]` 但 `footnote_map: {}`

**逆向追踪链**：

```text
[现象] footnote_map = {}（空字典）
  ↓
[Step 1] citation_map_json 由 CitationRegistry.build_citation_map_section() 或 write_citation_map_json() 生成
  ↓
[Step 2] footnote_map 来自 CitationRegistry.get_footnote_map()
          该 map 由 assign_footnote_number(citation_id) 调用填充
  ↓
[Step 3] assign_footnote_number() 在 postprocess._replace_registered_markers() 中被调用 (line 464)
          → cid = match.group(1)
          → num = registry.assign_footnote_number(cid)
  ↓
[Step 4] 该调用仅在 CIT_MARKER_RE 匹配到正文中的 {{CIT-xxx}} 时触发 (line 471)
          → _CIT_MARKER_RE.sub(_replace_marker, text)
  ↓
[Step 5] 当 assessment 的 chapters 正文中无 {{CIT-xxx}} 标记时（LLM 可能未插入），
          assign_footnote_number() 不被调用 → footnote_map 保持为空
```

**根因位置**：
| 层级 | 文件:行号 | 逻辑 |
|------|----------|------|
| 标记生成 | `module_generator.py:334-339` | system prompt 指示 LLM 使用 `{{CIT-xxx}}` 标记，但 LLM 可能不遵从 |
| 标记替换 | `postprocess.py:471` | `_CIT_MARKER_RE.sub(replace, text)` — 仅匹配到才调用 `assign_footnote_number()` |
| 脚注映射 | `CitationRegistry.assign_footnote_number()` | 仅在 `_replace_marker` 回调中被调用 |

**核心矛盾**：`all_items` 有 10 条引用（说明 `CitationRegistry.register()` 被调用了 10 次），但 `footnote_map` 为空（说明 `assign_footnote_number()` 被调用了 0 次）。这表示：
- 引用**注册**正常：10 个 CitationItem 通过 `register()` 写入了 registry
- 引用**映射**失败：LLM 生成的章节正文中未插入 `{{CIT-xxx}}` 标记，或者标记插入后未被 `CIT_MARKER_RE` 匹配到

**或者**：assessment 的 render 链可能**完全绕过了** `_replace_registered_markers()` —— 章节生成和渲染在不同步骤完成，render 步骤可能直接使用了 chapter content 而没有经过 CIT 管道。

---

### 9.4 工程标注泄漏的完整链路（tia/pipia/eu_scc，跨4模块）

**现象**：tia markdown 中 6 处 `【待核验：缺少法规依据】`、pipia 多处、eu_scc 2 处、assessment 1 处

**逆向追踪链**：

```text
[现象] 对外报告中出现 `【待核验：缺少法规依据】`
  ↓
来源有两条代码路径：

路径A — LLM 遵从 system prompt 主动生成:
[Step A1] dpia/chapter_generator.py:31 (或 module_generator.py:339)
          → prompt: "若无可核验依据，写「【待核验：缺少法规依据】」"
[Step A2] LLM 在 chapter 正文中生成该字符串
[Step A3] 无任何 post-generation 过滤器移除该标记

路径B — postprocessor 注入:
[Step B1] postprocess.py:469 → `return "【待核验：引用无法映射】"` 
          (当 CIT marker 不匹配任何注册引用时)
[Step B2] postprocess.py:473 → `return "【待核验：引用格式不完整】"`
          (当 CIT marker 被截断时)
```

**根因位置**：
| 源 | 文件:行号 | 内容 | 影响面 |
|----|----------|------|--------|
| LLM prompt 指令 | `dpia/chapter_generator.py:28-29` | `"禁止使用其他引用格式...若无可核验依据，写「【待核验：缺少法规依据】」"` | dpia(直接), 扩散到其他使用同 prompt 的模块 |
| 通用 prompt 指令 | `module_generator.py:339` | `"若无可引用依据，不要编造引用。"` | 所有用 `generate_chapter()` 的模块 |
| postprocessor 注入 | `postprocess.py:469` | `"【待核验：引用无法映射】"` | 所有使用 CIT pipeline 的模块 |
| postprocessor 注入 | `postprocess.py:473` | `"【待核验：引用格式不完整】"` | 所有有截断标记的模块 |

**修复缺环**：
- `apply_citation_pipeline()` 清理了 CIT 标记但**不清理工程标注**
- 需要对客 markdown 渲染管线中增加 `sanitize_external_markdown()` 步骤
- 过滤关键词：`【待核验` / `【推测】` / `【已移除`

---

### 9.5 evidence_chain 溯源字段全空的完整链路（assessment/cn_flow/us_14117）

**现象**：所有 EvidenceItem 的 `legal_basis`/`supporting_basis`/`document_refs`/`rag_query_used` 均为 null/空

**逆向追踪链**：

```text
[现象] evidence_chain_json 中所有 EvidenceItem 的这些字段为空
  ↓
[Step 1] evidence_chain 由各模块的 build_xxx_evidence() 函数构造
  ↓
[Step 2] 以 assessment 为例:
          common/workflow/pipeline.py → 调用注入的 build_evidence 函数
  ↓
[Step 3] assessment 的 evidence_builder 创建 EvidenceItem 时:
          → 填充了 evidence_id, claim, conclusion, fact_refs, rule_refs
          → 未填充 legal_basis, supporting_basis, document_refs, rag_query_used
```

**根因位置**（代码精确行）：

检查各模块的 evidence builder：

| 模块 | evidence builder 文件 | 缺失字段 |
|------|------|------|
| assessment | 通过 WorkflowPipeline 注入的 build_evidence callable | `legal_basis`, `supporting_basis`, `document_refs`, `rag_query_used`, `usage_constraint` |
| cn_flow | `backend/domains/us/eo14117_flow_review/evidence_builder.py` | 同上 |
| us_14117 | 通过 WorkflowPipeline 注入的 build_evidence callable | 同上 |

**代码特征**：这些字段在 `EvidenceItem` schema 中被定义（`common/workflow/evidence.py`），但所有 evidence builder 实现中都未填充它们。这属于**Schema 已定义但实现未跟进**的典型半成品状态。

---

### 9.6 state=COMPLETED 掩盖失败的完整链路（dpia/assessment/cpra/cn_flow）

**现象**：正文含 "LLM未配置" 占位但 state=COMPLETED

**逆向追踪链**：

```text
[现象] _result.json 中 state = "COMPLETED"
  ↓
[Step 1] 各模块 service 的 return 语句中硬编码 state
  ↓
  dpia/service.py:443     → return DPIAResult(..., state="COMPLETED", ...)
  cpra/service.py         → return CPRAResult(..., risk_level=risk_level, ...)
  cn_flow/service.py      → 通过 WorkflowPipeline 返回，pipeline 默认 state
  assessment (WorkflowPipeline) → pipeline 返回 WorkflowRunResult → 默认标记为 completed
```

**根因位置**：

| 模块 | 文件:行号 | 硬编码 |
|------|----------|--------|
| dpia | `service.py:443` | `state="COMPLETED"` — 无条件设置，不检查 placeholder |
| cpra | `service.py` (return 语句) | `risk_level` 由规则引擎计算正确，但未单独设 state |
| cn_flow | WorkflowPipeline 返回 | pipeline 不区分 LLM 成功/失败 |
| assessment | WorkflowPipeline 返回 | 同上 |

**修复方向**：在 `return` 前增加 placeholder 检测：
```python
has_placeholder = any("LLM未配置" in ch.content for ch in chapters)
state = "PARTIAL" if has_placeholder else "COMPLETED"
```

---

### 9.7 us_14117 docx 0字节 + markdown 崩坏的完整链路

**现象**：docx.docx = 0B，markdown.md 仅 13 行且无段落结构

**逆向追踪链**：

```text
[现象A] docx.docx 文件大小 0B
  ↓
[Step A1] DOCX 渲染器 render_docx_template() 读取模板 + 填充变量
  ↓
[Step A2] 模板变量映射失败 → docx 生成 abort → 空文件写入
  或：docx 模板文件本身不存在/路径错误
  ↓
[Step A3] us_14117 的 report renderer 调用链: 
          render_docx_template(TEMPLATE_PATH, context)
          需要检查 TEMPLATE_PATH 是否存在及 context 填充是否完整

[现象B] markdown.md 13 行超长无换行文本
  ↓
[Step B1] markdown 由 render_markdown_template() 生成（Jinja2 模板）
  ↓
[Step B2] 模板中 LLM 生成的章节内容通过 {{ chapter.content }} 注入
          由于 LLM disabled → chapter.content = "（xxx：LLM未配置..." 短字符串
  ↓
[Step B3] 但 markdown 中的结构化数据（风险详情、合规措施）来自模板绑定
          而非 LLM → 规则引擎产出的数据通过模板变量注入
  ↓
[Step B4] 模板中的 for 循环将 rule_engine_result 的 21 项安全措施缺口
          逐行渲染，但 LLM 未生成段落间换行 → 导致超长单行
```

**根因位置**（需进一步检查）：
| 层 | 文件 | 可疑点 |
|----|------|--------|
| DOCX 渲染 | `common/render/report.py` 的 `render_docx_template()` | 变量缺失时返回空文档而非抛异常 |
| us_14117 模板 | `resources/templates/us/` 下的 docx 模板 | 占位变量 `{{ chapter.content }}` 为空时模板行为 |
| markdown 渲染 | `common/render/report.py` 的 `render_markdown_template()` | markdown 模板中缺少换行控制 |

---

### 9.8 CIT postprocessor 正则覆盖缺口（pipia 特化分析）

**现象**：pipia markdown 第 117 行 `{{CIT-CN-CNLAW003-ART50`、第 139 行 `{{CIT-CN-CN_`

**精确正则分析**：

```python
# markers.py:20-22 — 完整 citation ID 格式
CITATION_ID_RE = r"CIT-[A-Z]{2}-[A-Z0-9_-]+-(?:ART[A-Za-z0-9_一-鿿]+|GEN)-P\d+"
#                          ^^^^^^  ^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                          法域    缩写             ART段落号/GEN    -P序号(必需)

# markers.py:25 — 完整标记格式  
CIT_MARKER_RE = r"\{\{( CITATION_ID_RE )\}\}"
# 要求: {{CIT-CN-XXXX-ARTxxx-P01}} 完整闭合

# postprocess.py:20 — 截断标记清理
_TRUNCATED_CIT_MARKER_RE = r"\{\{CIT-[A-Z0-9_-]*(?:\}\}?)?"
```

`{{CIT-CN-CNLAW003-ART50` 的匹配情况：
- `\{\{CIT-` → 匹配 `{{CIT-`
- `[A-Z0-9_-]*` → 匹配 `CN-CNLAW003-ART50`（⚠️ 包含两个连字符 `CNLAW003-ART50`）

**这里有问题**：`CITATION_ID_RE` 要求 `[A-Z0-9_-]+` 后接 `-(?:ART...|GEN)-P\d+`。但 `_TRUNCATED_CIT_MARKER_RE` 中的 `[A-Z0-9_-]*` 是贪婪匹配，会吃掉所有字符包括 `-ART50`。所以 `_TRUNCATED_CIT_MARKER_RE` 应该匹配 `{{CIT-CN-CNLAW003-ART50` 并替换它。

**然而 pipia 输出中仍然有原始截断标记**，这意味着：
1. `_replace_registered_markers()` 未被调用（最可能），或
2. pipia 的 content 经过了二次拼接，标记在 `apply_citation_pipeline()` 之后被重新引入

**结论**：pipia 的 markdown 渲染路径未使用 `apply_citation_pipeline()` 或使用了但 content 来自非 pipeline 源。

---

### 9.9 BCR citation 系统绕过（BCR 特化分析）

**现象**：26 个 findings 标注了法律依据（如 "GDPR Article 47(1)(a) [1]"），但 citation_map 仅 2 条注册引用

**逆向追踪链**：

```text
[现象] comment_map all_items 仅2条，但 findings 表中有 26 条带法律依据
  ↓
[Step 1] BCR 的 findings 由 BCRRuleEngine 生成（bcr_rulebook.json 驱动）
  ↓
[Step 2] 每条 finding 的 legal_basis 字段是 JSON 中的静态文本
          （如 "GDPR Article 47(1)(a); EDPB Recommendations 1/2022"）
  ↓
[Step 3] 这些法律依据字符串被 BCR Agent 直接嵌入 chapter 正文
          如 markdown 中: `依据：GDPR Article 47(1)(a) [1]；EDPB Recommendations 1/2022`
  ↓
[Step 4] Agent 在生成正文时手动写了 `[1]` 而非 `{{CIT-xxx}}` 标记
          → 引用信息是硬编码在正文中的，未经过 CitationRegistry 注册流程
```

**根因位置**：
| 层 | 文件 | 问题 |
|----|------|------|
| 规则引擎 | `backend/domains/eu/bcr_review/` 下的 bcr_rulebook.json | legal_basis 字段是纯文本，未被注册为 CitationItem |
| Agent 生成 | `backend/domains/eu/bcr_review/agents/` 下的 Agent | 正文直接写 `[1]` 而非 `{{CIT-CIT-xxx}}` 标记 |
| 引用注册 | `CitationRegistry.register()` | 仅对 Agent 显式提交的引用注册，不对 rulebook 静态 legal_basis 注册 |

**修复方向**：在 build pipeline 中为 rulebook 中的每条 legal_basis 调用 `CitationRegistry.register()`，并在 Agent 指令中要求使用 `{{CIT-xxx}}` 标记格式。

---

### 9.10 dpia necessity 预判格式化缺失（dpia 特化分析）

**现象**：dpia markdown 第 8-12 行出现 Python dict repr(`{'type': '...', 'fact_refs': [...]}`)

**逆向追踪链**：

```text
[现象] markdown 中有 Python 字典格式的触发理由
  ↓
[Step 1] markdown 由 report_renderer 渲染 → 使用了 need_assessment.trigger_reasons
  ↓
[Step 2] trigger_reasons 来自 need_agent_result (dpia/service.py:149)
          → dpia_need_output = DPIANeedAgentOutput(**need_agent_result)
  ↓
[Step 3] need_agent_result 是 Agent 返回的 dict
          → {..., "trigger_reasons": [{"type": "automated_decision_making", ...}, ...]}
  ↓
[Step 4] 在 build_generation_basis_pack 或 renderer 中，
          trigger_reasons 的 dict item 被以 str()/repr() 方式插入 markdown
          而非格式化为自然语言描述
```

**根因位置**：
| 层 | 文件 | 行 | 问题 |
|----|------|----|------|
| 中间转换 | `dpia/service.py:430-438` | `need_assessment.trigger_reasons` | 将 dict 直接转为 str 列表 |
| 渲染器 | `dpia/report_renderer.py` | 渲染 need_assessment 时 | 对 dict 类型 trigger_reasons 未做自然语言格式化 |

**对比**：dpia `chapter_generator.py` 的 `build_context_block_from_pack()` (line 120-289) 正确构建了 chapter 级上下文，但 `need_assessment` 的独立渲染路径未使用相同的格式化逻辑。

---

### 9.11 完整缺陷定位总表

| # | 问题 | 现象 | 根因文件:行号 | 精确缺陷 |
|---|------|------|-------------|---------|
| 1 | LLM 全静默失败 | 4模块占位文本 | `common/llm/client.py:73` | `_enabled = ... OpenAI is not None` — runtime 条件不满足 |
| 2 | dpia Agent 链断裂 | 7章占位 | `dpia/agents/external_draft_agent.py:59` | `if not self.enabled` → fallback |
| 3 | cpra 半失效 | 4/6章占位 | `cpra/service.py:515` | `if self.llm_client.enabled` else 占位 |
| 4 | cn_flow 半失效 | 4/4章占位(result.json) | `eo14117_flow_review/service.py:197` | 同模式 |
| 5 | pipia CIT 标记残留 | `{{CIT-CN-...}}` | `module_generator.py:357` vs pipia render | pipeline 产出已 clean，render 路径可能绕过 |
| 6 | assessment footnote_map 空 | `{}` | `postprocess.py:464` → `registry.assign_footnote_number(cid)` | LLM 未插入 marker → 无调用 |
| 7 | 工程标注泄漏 | `【待核验】` 等 | `dpia/chapter_generator.py:28-29` + `postprocess.py:469,473` | prompt 指令 + postprocessor 注入，无后过滤 |
| 8 | evidence_chain 空字段 | legal_basis=null | 各 `evidence_builder.py` | Schema 已定义，实现未填充 |
| 9 | state 假 COMPLETED | 正文占位但 COMPLETED | `dpia/service.py:443` 等 | 硬编码 `state="COMPLETED"` |
| 10 | us_14117 docx 0B | 空文件 | `common/render/report.py` | 变量缺失时返回空文档 |
| 11 | BCR citation 绕过 | 26→2 | BCR Agent 正文 | Agent 手动写 `[1]` 而非 `{{CIT-xxx}}` |
| 12 | dpia dict 泄漏 | Python repr | `dpia/service.py:430-438` | trigger_reasons dict→str 未格式化 |
