# DataComplyFlow 全模块运行结果全面审计报告

> 原始审计日期：2026-08-09
>
> 原始审计范围：当时盘点的 `tmp/` 下 11 个模块、98 个文件；当前目录已有 106 个文件，且产物日期横跨 2026-08-07 至 2026-08-10，**不是同一次运行，更不是当前系统的“最新一次运行结果”**
>
> 审计维度：格式、渲染、功能能力、业务能力、模块内文件关系与数据链路
>
> 当前复核基准：2026-08-13，本地工作区 `HEAD=878b64dd`；工作区存在未提交改动，本文分别标注“已提交”“当前工作区”“仅有方案”和“尚未复验”

## 事实复核说明（更新至 2026-08-13）

本文件主体是对 `tmp/` 历史产物的审计。原文曾把它概括为 **2026-08-07 09:56 左右生成的离线快照**，这一说法仍不够准确：当前 106 个文件中，66 个日期为 08-07、21 个为 08-08、7 个为 08-09、12 个为 08-10。它是一个**跨日期、跨代码版本的混合审计夹具集合**，不能用于证明任一版本的 11 模块同时运行结果。

### 复核结论

| 项目 | 原文说法 | 复核后的准确说法 | 证据 |
|---|---|---|---|
| DPIA Agent | “9个Agent全未执行” | **不准确**。快照的执行轨迹包含 `agent_dpia_need`、`agent_processing_activity`、`agent_risk_assessment`、`agent_consistency_repair` 等事件；Agent/规则中间态已执行，失败的是最终章节生成降级 | `tmp/dpia/trace_manifest.json` |
| CPRA / CN Flow / US 14117 | “LLM生成失效” | 对应快照确有占位或格式问题，但原因不能统一写成同一个根因；必须分别区分 LLM 未启用、章节降级、输出渲染和引用映射 | `tmp/*/markdown.md`、各模块 `trace_manifest.json` |
| US 14117 DOCX | “0字节，渲染完全失败” | 对 **2026-08-07 快照**成立；不代表当前代码状态。2026-08-10 新生成的 `outputs/us_14117/.../*.docx` 已有约 38 KB，并通过有效 DOCX/ZIP 测试 | `tmp/us_14117/`；`outputs/us_14117/`；提交 `9abfe5a` |
| CN Flow | “4/4章全部占位” | 对快照中的旧独立流程成立；当前 `cn_flow` 已委托 `us_14117`，旧重复章节流水线已删除，不能再用该结论描述当前实现 | `tmp/cn_flow/`；`status/check/DataComplyFlow_cn_flow兼容适配本地验收_20260810.md`；提交 `f622da4` |
| 索引修复 | “修复后全部可用” | 当前只能确认索引文件重建和静态计数完成；尚未证明 11 个模块重新运行后的 RAG 命中、引用注册和最终报告质量全部恢复 | `storage/rag/v3/*.jsonl`、`status/todo/DataComplyFlow_知识库索引修复方案_20260810.md` |
| 任务卡 FAIL | “系统当前失败” | 截图中的 FAIL 是 2026-08-09 工作区恢复出的历史运行结果。三个具体错误分别是 Review 文件路径越界、SCC `recommended_action` 为空、BCR Agent 参数不匹配；不能归为一个统一故障 | `storage/ai4law.db` 的 `workspace_states.state_json`；`backend/api/v1/endpoints/me.py` |

### 时间口径与证据等级

- `tmp/` 报告正文和本文件主体：以 2026-08-07 产物为主，混有 08-08 至 08-10 的后续产物；逐模块事实必须以对应文件时间为准。
- 数据库截图中的失败任务：2026-08-09 运行记录。
- 索引修复结果：2026-08-10 本地重建结果。
- 14117、CN Flow、引用和产物相关修复：以各自 Git 提交和 `status/check/` 验收文档为准。
- 2026-08-12/13 后续变化：以 Git 提交、当前代码、结构化验收 JSON 和真实运行记录交叉确认；仅写入 todo 的方案不算已完成。

因此，本文适合作为“历史问题基线 + 后续修复索引”，不适合作为未经分层说明的“当前全系统状态”。下文中未注明“当前”的模块输出、行数、文件大小、引用覆盖率和业务结论，均只描述相应历史产物。

## 当前状态总览（2026-08-13）

> 本节是当前事实入口，优先级高于后文历史快照结论。状态分为“已修复并有验收”“部分修复”“当前仍存在”“方案已写但未实施”和“尚未重新实跑”，不以代码文件存在或单次测试通过冒充全链路完成。

| 事项 | 当前准确状态 | 证据与边界 |
|---|---|---|
| `resources/new` 迁移 | **已完成并提交**。活动目录已删除，资源分层迁移提交为 `992ef071`、`5590843f` | `status/check/DataComplyFlow_RESOURCES-NEW全量迁移执行记录_20260812.md`；历史文档中的旧路径仅作来源追溯 |
| 共享案例 | **22 个 Scenario，覆盖 10 个独立业务模块；`cn_flow` 复用 `us_14117`，因此校验口径为 11 个注册模块** | `benchmarks/README.md`；当前门禁口径为 26 CLI cases / 603 leaf checks / 28 developer cases |
| Seed 案例 | **Level A 已完成，Level B 尚无可执行案例**。50/50 DOCX 已抽取；其中 40 条因匿名化或关键事实缺失被拒绝，10 条属于产品能力 gap，`converted=0` | 提交 `c117719d`、`6444b5be`；`status/check/task065/T01_T02_验收报告.md`、`T03_T04_验收报告.md`。不得把“50 条已抽取”写成“50 条 Gold/业务测试已接入” |
| PIPIA | **三条共享场景的确定性本地 HTTP、上传、SSE、报告、引用和 PDF canvas 已验收；整体仍为实施中** | `status/check/DataComplyFlow_PIPIA共享案例与浏览器本地验收_20260812.md`。浏览器服务使用确定性 LLM，不证明生产模型文案质量 |
| 其他模块浏览器闭环 | **尚未按 task065 对 11 模块形成统一、同一基线的完整复验** | `status/todo/task065_全模块本地闭环与生产报告质量整改实施方案_20260813.md` 中 T05-T09、T11-T12 尚无对应完整验收目录 |
| Review / SCC 历史 FAIL | **已分别修过事件链、重跑归并和旧失败状态水合；不能再把旧卡片 FAIL 当作当前任务失败** | Review 专项验收；提交 `164c7d77`。仍应通过 task065 的跨模块失败/恢复矩阵复验，不能外推为所有模块完成 |
| BCR 内容占位符 | 08-10 某次复跑可证明旧 `[Company Name]` 泄漏被清除，但**不能证明当前 BCR 报告合格** | 后文 §18 是阶段性复跑；内容是否正确、不同案例是否均清除仍需正式场景复验 |
| BCR 三格式排版 | **当前仍不合格；task067 只有 T00 基线冻结完成，T01-T11 未开始** | 实际 DOCX 11 段、0 原生表格；实际 PDF 5 页、字体未嵌入、六列表格异常换行；见 `issue067_*.md`、`task067_*.md` |
| 远程部署 | **未执行** | 本报告和 task065/task067 均限定本地范围 |

### 已找到的最新全模块运行证据

仓库中确实存在比 `tmp/` 更新、覆盖面更大的运行记录，但必须准确限定其证据范围：

| 证据 | 实际覆盖 | 可以证明 | 不能证明 |
|---|---|---|---|
| `status/check/DataComplyFlow_统一Scenario全模块迁移验收_20260811.md` | 11 个注册模块、26/26 CLI 案例、无 LLM 全量回归、全模块 LLM 回归；报告同时登记 PIPIA 的本地 HTTP/SSE/PDF 增量验收 | 统一 Scenario 适配、CLI 强断言、`--verbose-trace`、案例语义门禁和该次模型回归在报告所述基线下通过 | 不能证明当前 `HEAD=878b64dd` 下所有模块重新运行；不能证明 11 模块浏览器、SSE、DOCX/PDF 视觉全部通过；不能证明真实模型法律文案已经专家认可 |
| `status/check/DataComplyFlow_重新核查验收_20260810.md` | 8 月 10 日系统/API/引用/构建核查；登记“6/10 浏览器闭环、4/10 待浏览器验收” | 该次本地 API、引用完整性、构建和部分模块闭环结果 | 不能覆盖 8 月 11 日之后的共享案例、资源迁移、Seed 和认证改动 |
| `status/check/DataComplyFlow_PIPIA共享案例与浏览器本地验收_20260812.md` | PIPIA 三条共享案例的真实本地 HTTP、上传、SSE、报告、引用、PDF canvas | PIPIA 确定性浏览器链路已经通过 | 使用确定性 LLM，不能外推生产模型内容质量，也不能外推其他模块 |

这三份记录解决了“是否有全模块运行结果”的疑问：**有，最新可引用的是 2026-08-11 的全模块 CLI/LLM 回归；但没有找到一份在当前 2026-08-13 HEAD 上完成 11 模块真实浏览器、SSE、三格式产物和截图的单次全量报告。** 因此本文不能把它们合并表述为“当前全系统已完成”。

### 区域知识库更新

审计报告后文原先关于“区域法域完全无索引、registry 静默丢弃、前端无法浏览”的结论，已被当前工作区的 T10 实现和验收取代，但这些改动目前仍在工作区，不能描述为已经形成远程发布版本。

| 项目 | 当前工作区事实 | 限制 |
|---|---|---|
| 区域来源 | registry 共 120 条，其中区域 51 条；49 条绑定现有 PDF | `JP-LAW-009`、`KR-GUIDE-006` 仍缺对应 PDF；另有 2 份冗余 PDF 未归属 |
| 国际索引 | `legal_index_intl` **1,035 条**：HK 58、JP 265、KR 266、MO 80、MY 221、SG 23、TW 122 | VN 为 0；六份越南 PDF 当前没有生成结构化条文 |
| 索引隔离 | 区域 registry 的 `modules=[]`，国际 chunk 的 `module=""`，区域条文不会进入默认 CN/EU/US 模块池 | `intl_module` 仅作为 metadata/路由提示；当前不是“按业务模块检索区域法”的实现 |
| Evidence Center | 来源/案例法域选项由后端返回；区域来源可浏览，条文详情可打开 | 条文搜索栏仍只显示 CN/EU/US 三个快捷按钮；这不等同于来源浏览只支持三法域 |
| 增量导入脚本 | 当前 `--dry-run` 为 **33 processed / 18 skipped / 0 added** | `0 added` 是现有条文键已存在；18 条因无可解析条文、图片型或两份 PDF 缺失而跳过。旧文“0 processed / 51 skipped，路径完全失效”已经失实 |

结构化证据见 `status/check/task065/T10_regional_knowledge_verification.json` 和 `T10_区域知识库闭环_验收报告.md`。其中“可核验闭环”仅指 registry、独立索引、隔离和浏览链路；JP/KR 来源身份、VN OCR、模块字段和法律专家签署仍是明确缺口。

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

**关键断链（2026-08-07 快照）**：generation_basis_pack 构建完毕，但最终章节没有消费这些中间态并生成有效正文；`tmp/dpia/trace_manifest.json` 显示多个 Agent/规则阶段已执行。因此断点在“中间态 → 最终章节生成/降级门禁”，不能写成“9 个 Agent 全未执行”。

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

**关键断链（2026-08-07 快照）**：该次 `us_14117` DOCX 为 0B、Markdown 格式异常。后续已通过公共渲染器、模板和产物打包修复；2026-08-10 新生成 DOCX 约 38KB，0B 结论仅保留为历史快照事实。

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

> **原始审计总结（混合历史产物）**：当时按 11 个模块、98 个文件记录 40 项问题；现已确认这些文件并非同一次 2026-08-07 运行。该统计只保留为历史问题基线，不是当前代码状态；14117、cn_flow、索引和引用链已有后续修复，其他模块需在同一代码基线下重新运行判定。


---

## 八、问题共性与特殊性统计分析

> 对前七部分 40 个问题按根因维度重新归类，区分跨模块共性缺陷与单模块特殊问题。

---

### 8.1 问题共性归类（跨模块系统性缺陷）

#### C-COMMON-1 — LLM 生成静默失败/占位（影响 4 模块）

| 子类型 | 影响模块 | 严重度 | 共性特征 |
|--------|---------|:---:|---------|
| 最终章节全部降级为占位 | dpia | P0（快照） | 中间 Agent/规则阶段已执行；最终章节生成因 LLM 未启用而降级 |
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
| dpia | COMPLETED | 7/7章占位（2026-08-07 快照）；中间 Agent 已执行 |
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
| **特殊—us_14117 docx 0B（快照）** | 1 模块 | 9% | us_14117 | 2026-08-07 产物问题；2026-08-10 已有新 DOCX，内容需复验 |
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
  ├── 快照中的连锁表现：us_14117正文崩坏 → us_14117 docx 0B (S-1)
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

**现象（2026-08-07 快照）**：docx.docx = 0B，markdown.md 仅 13 行且无段落结构；2026-08-10 已生成约 38 KB 的新 DOCX，以下链路仅解释历史故障。

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
| 10 | us_14117 docx 0B（快照） | 空文件 | `common/render/report.py` | 历史产物为空；当前代码已有无模板渲染与完整打包修复，需重新验收内容 |
| 11 | BCR citation 绕过 | 26→2 | BCR Agent 正文 | Agent 手动写 `[1]` 而非 `{{CIT-xxx}}` |
| 12 | dpia dict 泄漏 | Python repr | `dpia/service.py:430-438` | trigger_reasons dict→str 未格式化 |


---

## 十、内容业务问题清单（结论质量与法律逻辑缺陷）

> 逐模块审查报告正文、中间结构化数据、结论推演链，发现以下业务逻辑/法律分析层面的实质问题。

---

### BIZ-1 【严重】assessment 路径矛盾：诊断推荐 scc，却生成了安全评估报告

- **模块**：assessment
- **现象**：`path_judgment_json.recommended_path = "scc_or_certification"`，`path_warning` 明确警告"未触发强制安全评估门槛"，但系统仍生成了题为"数据出境风险自评估报告"的全文
- **正文自认**：第 79 行 `综合风险等级：MEDIUM（路径不匹配，本报告为强制生成的参考草案）`
- **一致性检查也确认了矛盾**：`consistency_issues[0] = "诊断推荐路径为 scc_or_certification：未触发强制安全评估门槛，可走标准合同备案或认证路径。"`
- **业务问题**：用户输入触发的是**安全评估路径**的工作台，系统明知路径不匹配，仍然完整生成了 8 章报告并标注 `COMPLETED`。用户收到的是一份**系统自己承认"路径错了"的报告**——若用户不仔细读警告直接用于申报，将导致合规导向错误
- **正确行为**：应中断 pipeline，返回 `PATH_MISMATCH` 状态，提示用户切换到 SCC 认证路径

### BIZ-2 【严重】assessment 法规检索 98 条→引用注册 10 条→脚注映射 0 条——RAG 结果大面积浪费

- **模块**：assessment
- **数据链**：`regulations_count = 98` → `citation_map.all_items = 10` → `footnote_map = {}`
- **利用率**：98 → 10（10.2%）→ 0（0%）
- **业务影响**：RAG 检索了 98 条法规，仅 10 条被注册为引用，且**零条映射到脚注**。正文中仅出现 1 处《个人信息保护法》——98 条检索结果的实际利用率趋近于 0%，RAG 成本完全浪费
- **根因**：LLM 在生成章节时未被有效要求插入 `{{CIT-xxx}}` 标记（prompt 有指令，但 LLM 未遵从），且无 post-generation 的引用覆盖率校验

### BIZ-3 【高】pipia 结构化问题仅 1 条，但正文分析覆盖 5+ 法律维度——结构化层与生成层严重脱节

- **模块**：pipia
- **现象**：`issues = [{"issue_id": "PIPIA-ISSUE-001", "title": "风险等级较高"}]`——仅 1 条结构化 Issue，描述为"当前出境规模触发高风险画像"
- **但正文实际分析的维度**：告知同意缺陷、敏感信息误分类、境外接收方保障不足、标准合同关键条款缺失、数据主体行权机制缺位——至少 **5 个独立的法律分析维度**
- **业务问题**：结构化 Issue 层应该是驱动正文生成的数据源，但 pipia 的 LLM Agent 在生成正文时自行扩展了分析维度，而扩展的分析没有被回写到结构化层。这意味着——(a) 正文质量完全依赖 LLM 单次生成的"灵感"，无结构化约束和一致性校验；(b) 下次运行同一输入，正文分析维度可能完全不同（非确定性）；(c) consistency_checker 无法交叉校验这些隐性分析维度
- **根因**：pipia 的 `_build_structured_issues()` 仅产出 1 条聚合 Issue，而非将"告知不足/分类错误/保障缺失/条款缺失/行权缺位"**拆解为多个独立 IssueItem**。LLM Agent 收到的 prompt 包含了完整的 facts/regulation 上下文，Agent 自行发现了这些维度并展开分析——这恰好证明结构化层**漏掉了**本应识别的 4 个 Issue

### BIZ-4 【高】tia 降级逻辑缺乏量化支撑：国家风险 HIGH + 加密措施 → 结论 MEDIUM

- **模块**：tia
- **现象**：`country_risk.risk_level = "HIGH"`（美国，FISA 702/CLOUD Act/EO 12333），补充措施为"端到端加密+欧盟密钥管理"，最终结论 `MEDIUM`
- **正文降级论证**：`"该措施被评估为充足，能够有效缓解多数政府访问风险，因为它使得数据进口方及第三国当局在无法获取密钥的情况下无法访问明文数据"` + `"本次传输有条件地达到了欧盟基本同等的保护水平"`
- **业务问题**：
  1. 论证仅依赖单一技术措施（E2E encryption）将国家风险从 HIGH 降为 MEDIUM，但**未评估**：(a) 加密算法强度（AES-256?）；(b) 密钥管理方案（HSM? 谁运维? 是否有备份密钥?）；(c) 数据在内存中解密处理时的风险窗口；(d) 法律强制密钥披露风险（美国法律是否可以强制欧盟实体披露密钥？）
  2. 未提及 EDPB Recommendations 01/2020 对加密措施的评估标准（如"数据进口方无法访问明文数据"≠"政府无法强制要求交出密钥"）
  3. 结论说"有条件地达到了欧盟基本同等的保护水平"——但实际上条件是"加密措施持续有效"+"进口方严格履约"，这两个条件本身存在被第三国法律架空的风险
- **风险评级应有的严谨度**：TIA 的最终结论应有加密措施的**有效性量化分析**，而非一句"被评估为充足"

### BIZ-5 【高】eu_scc 12 处"未提供"——报告在说用户缺了什么，而非分析用户提供了什么

- **模块**：eu_scc
- **统计**：12 处"未提供"（签署日期、适用法律、数据输出/输入方身份、数据主体类别、传输目的、附录III、附录IV、TIA 文件、补充措施等）
- **业务问题**：合规审查报告的核心价值是"根据你提供的文档，发现了什么问题"。但 eu_scc 的 report 大量篇幅在逐项说"没提供这个、没提供那个"——这些是**输入校验**的职责，应该在表单阶段或 payload validation 阶段就拦截，不应等到报告正文才暴露
- **对比**：pipia 同样面临材料缺失（50 万用户的同意记录），但 pipia 的正文是在"现有材料下"做分析，指出缺陷但同时也给出了具体条款引用和建议。eu_scc 则偏向"清单式列举缺失项"
- **建议**：前端上传文件时即校验必填项；报告正文聚焦"已提供材料的质量审查"，而非"材料清单核对"

### BIZ-6 【高】BCR 整改建议 11 处 `[Company Name]`/`[EU Member State]` 模板变量泄漏

- **模块**：bcr
- **统计**：`[Company Name]` 3 处、`[EU Member State]` 7 处、`[Insert specific clause...]` 2 处
- **位置**：均在"可直接采用的建议条款"部分——这是给用户的整改建议，但全部是不可用的模板骨架
- **示例**：`"[Company Name], established in [EU Member State], shall act as the EU liable entity..."`——用户看到的是"请在此处填入公司名"，而非可操作的整改条款
- **业务影响**：BCR 报告最有价值的部分（具体整改建议）因模板变量未填充而完全不可用
- **根因**：`bcr_rulebook.json` 中的 `suggested_text` 字段包含模板变量，但 Agent/renderer 未执行 `company_name` 等已知变量的替换

### BIZ-7 【中】eu_scc 8 项发现中 6 项未提取原始条款文本——"改了什么"未展示

- **模块**：eu_scc
- **数据**：`findings` 8 项，`original_text` 仅 2 项有值（Clause 15(a)、Annex I.B），6 项为 null；`suggested_text` 仅 1 项有值，7 项为 null
- **业务问题**：SCC 审查的核心价值是"对比标准条款 vs. 实际文本，指出哪里被修改/缺失"。当 `original_text=null` 时，报告只能说"这里有问题"，但用户看不到"原来的文本是什么"和"应该改成什么"——报告从"条款级审查"降级为"清单式标注"
- **对比**：`EU-SCC-CLAUSE-15-DEVIATION` 正确提取了原文 `"as soon as legally permissible"` 并标注了应改为 `"promptly"`——这是唯一一条正确填充的 finding，也是仅有的一条对用户有实际操作指导价值的发现
- **根因**：`compare_standard_clauses()` 在文件解析结果中未找到可匹配的段落文本时，仅标记为 `issue_type` 和 `severity`，未 fallback 为"无法定位原文位置"

### BIZ-8 【中】assessment compliance_reasoning 8 维度全部判定"不可正面肯定"——但报告未传达这一"全盘否定"信号

- **模块**：assessment
- **数据**：`compliance_reasoning_json` 中 8 个评估维度（CIIO认定、重要数据认定、接收方保障能力、法律文件约定、告知同意、再转移约束、必要性相称性、安全措施有效性）的**事实状态全部为 `user_claim_only` 或 `partially_supported`**，**全部判定为"不可正面肯定"**
- **但正文**的总体结论为 `风险等级MEDIUM`，且推荐路径为 `scc_or_certification`
- **业务问题**：8/8 维度"不可正面肯定"意味着**没有任何一个法律要件有充分证据支撑**，在这种情况下定 MEDIUM 风险等级是严重低估。更合理的结论应该是"当前材料不足以支撑任何合规路径的正面结论，建议补充材料后重新评估"或至少定为 HIGH
- **根因**：`compliance_reasoning` 的内部审查结论未被纳入 `risk_level` 的计算——risk_level 仅由 `path_judgment`（规则引擎）决定，而规则引擎只看数字阈值（人数、CIIO、重要数据），不看证据充分性

### BIZ-9 【中】cpra 10 条规则域仅命中了 4 个 domain——6 个 domain 未被检查

- **模块**：cpra
- **数据**：`gap_items` 共 5 条，覆盖 domain 为：`notice_and_consent`(2条)、`consumer_rights_process`(1条)、`opt_out_and_sale_sharing`(1条)、`consent_ui`(1条)
- **未覆盖的 domain**：`sensitive_pi`、`data_minimization`、`purpose_limitation`、`vendor_management`、`data_retention`、`security_safeguards`
- **业务问题**：CPRA 全景诊断检查了 4 个领域但遗漏了 6 个——这个"全景"不完整。`gap_rules.py` 定义了 `run_all_rules()` 应该覆盖 10 个 domain，但 6 个规则的触发条件未满足（因为本次测试运行未上传隐私政策/数据地图/供应商列表等文件）
- **这属于测试输入不足导致的业务能力展示不全，而非代码缺陷**——但客户端（前端/报告）未明确告知用户"因缺少 xxx 文件，以下 6 项检查未执行"

### BIZ-10 【中】pipia 正文中"合同履行必要性"与"单独同意"的法律基础矛盾未解决

- **模块**：pipia
- **正文**：第 55-57 行同时陈述了"基于个人同意"和"为履行合同所必需"两个法律基础，但正文仅说"此论证较为宽泛...有待复核"，未给出明确结论
- **业务问题**：《个保法》下这两个法律基础是互斥的——如果确实是为履行合同所必需，则不需要单独同意；如果依赖单独同意，则不能同时主张合同履行必要性。pipia 正文指出了这个矛盾但**悬置不决**——用户在读完报告后仍然不知道应该走哪个法律基础
- **建议**：Agent 应被指示在发现此类法律基础冲突时给出明确推荐（如"建议优先以单独同意为基础，补充完整同意记录"），而非仅标注"有待复核"

### BIZ-11 【中】assessment 材料清单仅 1 项——用户无法判断申报材料是否齐备

- **模块**：assessment
- **数据**：`material_checklist_json` 仅 1 条 `{source_ref: "user_claim", summary: "根据用户输入字段推断的材料需求", status: "待补充"}`
- **业务问题**：安全评估申报材料清单通常包含 20+ 项（营业执照、数据出境合同、隐私政策、安全评估报告、数据清单、接收方保障文件等），但系统仅生成了 1 条泛化条目。用户拿着这份报告**完全不知道还缺什么材料**
- **根因**：`material_checklist` 构建依赖上传文件的自动检测，本次无上传文件时只产出了兜底条目

### BIZ-12 【中】us_14117 24 条规则命中 + 21 项安全措施缺口，但报告正文未能结构化呈现

- **模块**：us_14117
- **数据**：`rule_hits = 24条`（含交易分类、阈值触发、受限制主体识别、安全措施检查各类型），正文仅以一段连续文本 dump 了所有信息
- **业务问题**：EO 14117 合规评估的核心输出应该是：(a) 红黄绿灯判定及理由；(b) 受限制主体清单；(c) 触发阈值的具体数据项；(d) **逐条的**安全措施缺口状态表。但正文将这 4 类信息挤压为 3 段无格式文本——用户无法快速定位"具体缺了哪个安全措施、优先级是什么"
- **对比**：bcr 和 eu_scc 都生成了结构化的 findings 表格——us_14117 也应该有类似的结构化呈现

### BIZ-13 【中】pipia 50 万用户的同意有效性——法律分析触及了核心问题但未给出可操作的整改验收标准

- **模块**：pipia
- **正文分析**："企业已提供单独同意界面截图，但尚未能提供覆盖全部50万目标用户的批量同意记录清单，同意有效性存疑"——分析正确
- **但整改建议**："2. 梳理并修复同意管理系统的日志记录功能...对历史同意记录进行审计与补全"——这是系统修复建议，不是法律合规建议
- **缺失的**：未说明——
  - 50 万用户中有多少已取得有效同意、多少缺失（如果有数据的话）
  - 对于缺失同意的用户，应该采取什么法律措施（补取同意？删除数据？暂停传输？）
  - 整改完成后的验收标准是什么（"能够提供覆盖全部 50 万用户的同意日志"）
- **业务问题**：PIPIA 报告的结论章节应给出**可验证的整改完成标准**，而非仅"修复系统功能"

### BIZ-14 【低】eu_scc 模块验证与 SCC 审查脱节——模块选择正确但报告未利用这一正面发现

- **模块**：eu_scc
- **数据**：`module_validation = {expected: "Module Two", actual: "Module Two", is_correct: true}`
- **现象**：模块验证通过了（正确识别为 Module Two: C→P），但正文中这个正面发现被淹没在大量"未提供"中
- **业务建议**：正面发现应作为报告的**合格项**明确列出，而不是只在 result.json 中存在——用户需要知道"哪些是做对的"而不仅是"哪些是错的"

### BIZ-15 【低】tia "推测"语言泄漏到正式 TIA 报告

- **位置**：第 28 行 `【推测】基于数据出口方为控制者、数据进口方为处理者的角色设定...`
- **业务问题**：TIA 是正式合规评估文件，在正式结论中不应出现"推测"——如果信息不足应标注"需补充信息以确认"，如果信息充分应做确定性陈述

### BIZ-16 【低】pipia 附件摘要暴露了测试夹具的元信息

- **模块**：pipia
- **位置**：正文末尾 `附件摘要` 小节
- **内容**：`"文件性质：本文件根据'认证/标准合同路径'测试案例一派生，仅用于本地自动化验收；不是案例原文附件，不是正式签署文本，也不能作为真实备案材料"`
- **业务问题**：这段**测试夹具的免责声明**被完整地嵌入了报告正文——如果是给真实客户的报告，这段文字将严重损害专业性

---

## 十一、全部问题跨维度交叉矩阵

| # | 问题 | 维度 | 模块 | 严重度 | 关联根因 |
|---|------|------|------|:---:|------|
| BIZ-1 | 路径矛盾仍生成报告 | 业务逻辑 | assessment | P0 | C-COMMON-5 假COMPLETED |
| BIZ-2 | RAG 98→0 完全浪费 | 内容质量 | assessment | P0 | C-COMMON-2 CIT崩溃 |
| BIZ-3 | 1个Issue→5维正文分析 | 结构化层vs生成层脱节 | pipia | P0 | pipia issue builder |
| BIZ-4 | 降级逻辑无加密量化 | 法律推理严谨性 | tia | P1 | tia TIA评估逻辑 |
| BIZ-5 | 12处"未提供"替代分析 | 报告内容空洞 | eu_scc | P1 | eu_scc 报告策略 |
| BIZ-6 | 11处模板变量泄漏 | 内容可用性 | bcr | P0 | bcr模板渲染 |
| BIZ-7 | 6/8条original_text=null | 内容完整性 | eu_scc | P1 | eu_scc clause_compare |
| BIZ-8 | 8维全否→MEDIUM | 风险结论逻辑 | assessment | P1 | risk_level计算 |
| BIZ-9 | 6/10 domain未检查 | 覆盖度不完整 | cpra | P2 | gap_rules触发条件 |
| BIZ-10 | 法律基础矛盾悬置 | 法律分析完整性 | pipia | P2 | Agent指令 |
| BIZ-11 | 材料清单仅1项 | 业务实用性 | assessment | P2 | material_checklist |
| BIZ-12 | 24条hits无结构化 | 信息呈现质量 | us_14117 | P1 | us_14117 渲染 |
| BIZ-13 | 整改缺少验收标准 | 可操作性 | pipia | P2 | Agent prompt |
| BIZ-14 | 正面发现被淹没 | 报告平衡性 | eu_scc | P3 | 报告策略 |
| BIZ-15 | "推测"在正式报告 | 措辞专业性 | tia | P3 | C-COMMON-4 |
| BIZ-16 | 测试元信息泄漏 | 生产就绪度 | pipia | P2 | 内容过滤 |

---

> **审计最终总结（快照基线）**：11 模块、98 文件，约 76 个问题定位点。该结论只代表 2026-08-07 快照，不能直接代表 2026-08-10 当前系统；后续修复必须以最新产物和测试证据重新判定。


---

## 十二、深度链路追踪：tia `【待核验】` 注入的完整执行链（postprocess.py ↔ 正文对照）

> 用户提供了 `backend/common/llm/postprocess.py` 和 `tmp/tia/markdown.md`，要求从缺陷现象反推精确的代码执行链路。

### 核心发现：双路径 Citation 处理不一致

tia 模块存在**两条独立的 citation 处理路径**，在 markdown 渲染路径中对 `[N]` 格式的脚注存在系统性的误判：

| 路径 | 处理器 | 支持的引用格式 | 结果 |
|------|--------|:---:|------|
| Markdown 生成路径 | `apply_citation_pipeline()` (postprocess.py:412) | 仅 `{{CIT-xxx}}` | ❌ `[1]` 被标记为未验证 → 注入 `【待核验】` |
| DocumentIR 构建路径 | `build_tia_document_ir()` (schema_first.py:53) | `{{CIT-xxx}}` + `[N]` | ✅ `[1]` 被正确解析并注册 |

### 精确触发链（6个段落逐一验证）

```
postprocess.py:354  ── has_verified_marker = bool(valid_citations) or bool(
                                       numeric_footnotes & verified_footnotes)
                                = False or ({1} & set()) = False or False = False
postprocess.py:355  ── if claim_type != "NONE" and not has_verified_marker:
postprocess.py:356  ──     paragraph += " 【待核验：缺少法规依据】"  ← 6次触发
```

**为什么 `verified_footnotes` 是空的？**

```
postprocess.py:435  ── verified_footnotes = set(registry.get_footnote_map())
                         = set({})  因为 assign_footnote_number() 从未被调用
                                        因为 _replace_registered_markers() 从未匹配到 {{CIT-xxx}}
postprocess.py:471  ── converted = _CIT_MARKER_RE.sub(replace_marker, text)
                         → 零匹配, 零替换
```

**为什么 citation_map_json 最终却有 footnote_map？**

DocumentIR 构建路径（`schema_first.py:78-80`）在 markdown 渲染之后执行：
```python
citation_free, citation_refs = extract_citation_refs(paragraph, citation_registry)
# → 解析 [1] 并注册到 registry, 此时 footnote_map 才被填充
```
但此时 markdown.md 已经生成完毕，`【待核验】` 已经写死。

### 触发段落实例

| 段落 | 触发正则 | 匹配片段 |
|:---:|------|------|
| 10 | `_LEGAL_RULE_RE` | `必须进行完整的传输影响评估（TIA），包括对补充措施的评估` |
| 19 | `_LEGAL_RULE_RE` | `必须采取补充措施以弥补第三国法律环境造成的保护` |
| 41 | `_LEGAL_RULE_RE` | `禁止数据进口方（US Importer）在未获得数据` |
| 67 | `_LEGAL_RULE_RE` | `必须根据GDPR第46条及SCCs的规定，评估` |
| 79 | `_LEGAL_RULE_RE` | `必须启动重新评估` |
| 80 | (none) | 无法律主张匹配，但因上段上下文被带入（段落边界切分问题） |

### 修复建议

1. **P0**：在 `apply_citation_pipeline()` 中增加 `[N]` 格式解析——先扫描文本中所有 `\[(\d+)\]`，反向查 registry 中已注册的 `citation_id` 是否被 assign 到该数字，构造 `verified_footnotes_candidates`
2. **P0**：在 `module_generator.py:generate_chapter()` 的 system prompt 中强化 `{{CIT-xxx}}` 格式要求（当前有指令但 LLM 不遵从），增加后置校验：若生成文本中无 `{{CIT-xxx}}` 标记但有 `[N]` 引用，打印 warning
3. **P1**：统一 markdown 和 DocumentIR 两条 citation 路径，消除双路径不一致

> 此问题同时影响 **bcr** 模块（Agent 同样写 `[N]` 不写 `{{CIT-xxx}}`），但 bcr 的 markdown 未经过 `apply_citation_pipeline()` 处理（走的是模板渲染路径），所以没有 `【待核验】` 注入——仅表现为脚注列表完全不存在（已在 R11/F2 中记录）。



---

## 十三、中间结构化数据质量问题（非 Markdown 输出）

> 针对用户要求：不只审查最终渲染的 markdown/docx，更要审查 `_result.json` 中的 facts/issues/evidence_chain/gap_items/risk_matrix/法规列表等中间结构化数据。

---

### 13.1 跨模块 EvidenceItem Schema 填充率 → 趋近于零

EvidenceItem Schema 定义了 5 个关键引用字段：`legal_basis`、`supporting_basis`、`document_refs`、`rag_query_used`、`usage_constraint`。跨 11 模块检查结果：

| 模块 | 有 EvidenceItem 的字段 | legal_basis 填充 | supporting_basis | document_refs | rag_query_used |
|------|:---:|:---:|:---:|:---:|:---:|
| pipia (evidence_chain) | ✅ 全字段存在 | **0/5** (全部空数组) | **0/5** | **0/5** | **0/5** (空字符串) |
| bcr (findings) | 仅部分字段 | 26/26 ✅ | **0/26** | **0/26** | **0/26** |
| cpra (gap_items) | 仅部分字段 | 5/5 ✅ | **0/5** | **0/5** | **0/5** |
| eu_scc (findings) | 仅部分字段 | 8/8 ✅ | **0/8** | **0/8** | **0/8** |
| dpia (evidence_chain) | **字段根本不存在** | N/A | N/A | N/A | N/A |
| assessment | 无 evidence_chain | N/A | N/A | N/A | N/A |

**结论**：`legal_basis` 有字符串填充但 `supporting_basis`（支撑依据）、`document_refs`（文档引用）、`rag_query_used`（RAG查询记录）三个字段**在所有模块的所有条目中全部为空**。这意味着即使证据链在结构上存在，也无法从证据追溯到具体支撑材料——这有悖于 evidence-based compliance 的设计初衷。

---

### 13.2 pipia：facts 全空引用 + evidence_chain 空壳

**facts 层（22条）：**
- `supporting_material_refs`：**22/22 全部为空数组 `[]`**
- `evidence_refs`：**22/22 全部为空**
- `source` 字段：不存在于 fact schema
- `category` 字段：全部为 `null`
- 每条 fact 只有一个 `field_path`（如 `request.route_type`）+ `value`，没有任何外部引用

**evidence_chain 层（5条）：**
- 5 条 evidence 使用完整的 EvidenceItem Schema（共 15 个字段），但：
  - `legal_basis`：5/5 为 `[]`
  - `supporting_basis`：5/5 为 `[]`
  - `document_refs`：5/5 为 `[]`
  - `rag_query_used`：5/5 为空字符串
  - `rag_hits_count`：5/5 为 `0`
  - `confidence`：0.75-0.95（这是唯一的"真实"数据）
- 5 条 evidence 对应的 `rule_refs` 全部引用相同的 2 条法规（`网络数据安全管理条例第四十二条`、`个人信息保护法第二十四条`）——意味着 RAG 根本没有对每条 evidence 做独立的法规检索

**issue 层（1条）：**
- `related_facts: []` — 尽管有 22 条 fact 可用，issue 没有关联任何一条
- `related_laws: []` — 没有关联任何法律条款
- `fact_refs: []` + `rule_refs: []` + `evidence_refs: []` — 三空

**material_gaps 层：0 条**
- `filing_readiness.status = "supplement_required"` 但 `material_gaps` 为空 —— **矛盾**：系统知道需要补充材料，但没有记录具体缺什么

---

### 13.3 assessment：4 个嵌套 JSON 字符串全部为空

```json
path_judgment_json: ""        → 路径判断逻辑丢失
compliance_reasoning_json: "" → 合规推理链丢失
material_checklist_json: ""   → 材料清单丢失
consistency_report_json: ""   → 一致性报告丢失
```

这 4 个字段在 `profile` dict 中作为字符串存在但全部为空——意味着所有需要结构化输出的 Agent 阶段**仅在最终 markdown 正文中以自然语言形式存在**，未回写到 `_result.json` 的结构化字段中。

**法规列表（98条）：**
- `citation_id`：字段不存在
- `article_no`：**98/98 为空**
- `quote_text`：字段不存在（仅有 `snippet`，也全部为空）
- 仅有 `source_id` + `title` + `article`（空）+ `snippet`（空）
- → 98 条法规检索结果实际上是一份**无条款编号、无条文引文**的标题清单

---

### 13.4 dpia：Agent 中间态数据泄漏 + Python repr 污染

**Agent state 泄漏到结构化字段：**
- `necessity_findings.questionable_processing[0].processing` 的值是 Python dict 的 repr 字符串：
  ```
  "{'step': '数据处理', 'actor': '未指明', 'data_sources': ['数据主体'], ..."
  ```
  这是 `str(dict)` 的原始输出，而非 JSON 序列化或结构化对象

- `internal_ai_review.insufficient_evidence_items[4]` 包含字符串 `'False'`（布尔值被转为字符串）

- `internal_ai_review.insufficient_evidence_items[3]` 包含 Python list 的 repr：
  ```
  "['学生ID', '邮箱', '专业', '浏览记录', '课程完成率', '测试成绩', '学习时长', '互动行为']"
  ```

**evidence_chain（7条，在 generation_basis_snapshot 中）：**
- 7 条全部**缺失** `legal_basis`、`supporting_basis`、`document_refs` 字段（field does not exist at all）
- 每条仅有 `evidence_id` + `claim` + `fact_refs` + `rule_refs` + `issue_refs`
- → 与 pipia 的 evidence_chain 处于完全不同的 Schema 版本

---

### 13.5 cpra：5/10 domain 覆盖 + gap_items 字段部分充实

**domain 覆盖：**
- 命中 4 个 domain：`notice_and_consent`、`consent_ui`、`consumer_rights_process`、`opt_out_and_sale_sharing`
- 未命中 6 个：`sensitive_pi`、`data_minimization`、`purpose_limitation`、`vendor_management`、`data_retention`、`security_safeguards`

**gap_items 内部质量（相对较好）：**
- 5 条 gap 全部有 `legal_basis`（CPRA 条款号精确到 § 编号）
- 5 条全部有 `recommendation`
- 5 条全部有 `citations` + `citation_refs`
- 但 `supporting_basis`、`document_refs` 全部为空——证据薄弱

---

### 13.6 us_14117：24 条 rule_hits 缺失分类字段

- `rule_hits` 24 条，**全部没有 `category` 字段**（我在 Python 中用 `h.get('category', '?')` 全部返回 `'?'`）
- 仅有 `rule_id` + `rule_name` + `section_ref` + `hit`(bool) + `reason`
- `traffic_light_result` 结构完整（有 `overall_light`、`per_entity_lights`、`is_restricted`、`required_security_measures`），但与 `rule_hits` 之间没有双向引用——无法从 traffic_light 追溯到具体的 rule_hit

---

### 13.7 cn_flow：1 条 risk_item 承载全部分析

- `risk_items` = 1 条 `{risk_id: "CNF-R1", risk_level: "HIGH", title: "存在敏感数据跨境流动"}`
- **过于聚合**：EO 14117 分析应产出（a）实体分类结果（b）阈值触发明细（c）受限主体清单（d）逐安全措施评估——但这些全部被压缩为 1 条 risk_item + 4 章占位文本
- `attachment_notes` 2 条，全部是文件未找到错误（而非文件解析结果）

---

### 13.8 eu_scc：findings 文本提取完整性

- 8 条 finding，6 条 `original_text = null`（即字段缺失或空串）
- 2 条有 original_text 的都是实际匹配到的（Clause 15(a)、Annex I.B）
- chapter 3（条款级审查发现）1433 字符，`truncated_end=True`
- chapter 4（法规依据与修改建议）1231 字符，`truncated_end=True`
- → 内容截断不仅影响渲染，也影响中间数据的完整性

---

### 13.9 bcr：review_metadata 暴露全部模板生成

```json
{
  "review_mode": "rule_only",
  "llm_remediation_count": 0,
  "template_remediation_count": 9,
  "total_findings": 26,
  "total_missing": 2
}
```

- 26 条 findings 全部来自规则引擎（`rule_only`），无 LLM 参与深度分析
- 9 条整改建议全部是模板生成（`template_remediation_count=9`），且模板变量未填充（见 BIZ-6）
- `risk_level` 字段存在于 finding schema 但我的快速扫描未提取到值（实际字段名是 `risk_level` 不是 `severity`）

---

### 13.10 跨模块 cross-reference 完整性检查

| 模块 | facts 数量 | issues 数量 | fact→issue 引用 | 完整性 |
|------|:---:|:---:|:---:|:---:|
| pipia | 22 | 1 | issue.fact_refs=[] | ❌ 0/22 被引用 |
| dpia | 37 (gbs) | 4 (gbs) | 通过 evidence 间接引用 | ⚠️ 部分 |
| assessment | 0 | 0 | N/A | N/A |
| cpra | 0 | 5 (gaps) | N/A | N/A |
| us_14117 | 0 | 24 (hits) | N/A | N/A |
| eu_scc | 0 | 8 (findings) | N/A | N/A |
| bcr | 0 | 26 (findings) | N/A | N/A |

**关键发现**：只有 pipia 和 dpia 有独立的 `facts` 层，其他模块的事实数据或是内嵌在 agent 输出中（dpia 的 section_packs），或是根本没有结构化事实层。而 pipia 尽管有完整的 22 条事实，唯一的 issue 却没有关联任何一条。

---

### 13.11 中间数据质量问题总结

| 问题编号 | 问题 | 涉及模块 | 严重度 |
|:---:|------|------|:---:|
| ID-1 | EvidenceItem 5 个字段全模块零填充 | pipia/bcr/cpra/eu_scc/dpia | P0 |
| ID-2 | facts 22条全无 supporting_material_refs | pipia | P0 |
| ID-3 | evidence_chain 5条 legal_basis/supporting_basis 全空 | pipia | P0 |
| ID-4 | issue 无任何 fact/rule/evidence 引用 | pipia | P1 |
| ID-5 | material_gaps=0 但 filing_readiness=supplement_required | pipia | P1 |
| ID-6 | 4 个嵌套 JSON 字符串全部空值 | assessment | P0 |
| ID-7 | 98 条法规 article_no 全部为空 | assessment | P1 |
| ID-8 | Python repr 泄漏到结构化字段 | dpia | P1 |
| ID-9 | evidence_chain 字段 schema 版本不一致 | pipia vs dpia | P1 |
| ID-10 | 6/10 domain 未命中但无 "未检查原因" 标注 | cpra | P2 |
| ID-11 | 24 条 rule_hits 无 category 字段 | us_14117 | P2 |
| ID-12 | 1 条 risk_item 承载全部 EO 14117 分析 | cn_flow | P1 |
| ID-13 | 6/8 findings 无 original_text | eu_scc | P1 |
| ID-14 | 9 条整改全部模板生成 + 变量未替换 | bcr | P0 |
| ID-15 | review_mode="rule_only" 无 LLM 深度分析 | bcr | P2 |

---

## 十四、业务需求对照：功能说明文档规定的预期产出 vs 实际运行结果

> 依据来源：
> - 原始来源曾位于 `resources/new/数规通功能路径描述/`；迁移后活动副本位于 `benchmarks/source-materials/{cn,eu,us}/legacy-docx/`
> - 每任务“功能说明与路径描述”的 **“系统输出”** 章节和“测试案例及预期输出”的 **“预期输出”** 章节；来源 Hash 与归置关系见 `status/check/task065/case-disposition.v1.json`
> - `tmp/` 下 `_result.json` + `markdown.md` + `docx.docx` 实际运行结果

---

### 14.1 模块对照：需求规定 → 实际差距

#### ✅ pipia — 认证/标准合同路径

| 维度 | 需求文档规定的产出 | 实际运行结果 | 差距 |
|------|------|------|------|
| 交付物 | `《个人信息保护影响评估报告（草案）》` — 严格按网信办《备案指南》附件5模板 | `markdown.md` 24,154B，7章8567字符，docx 45,701B | ✅ 完整 |
| 报告结构 | 7章：处理者基础信息 → 出境处理活动说明 → 接收方保护能力 → 权益影响 → 技术组织措施 → 事件响应 → 结论与备案建议 | 7章全部有实质内容，每章1100-1340字符 | ✅ 结构完整 |
| 业务结论 | 判定合规路径、风险等级、备案准备度、整改建议 | `route_type=scc_filing`，`risk_level=HIGH`，`filing_readiness=supplement_required`，结论章指出告知同意缺陷+敏感信息误分类+接收方保障不足+标准合同条款缺失+行权机制缺位**共5个法律分析维度** | ✅ 业务结论明确 |
| 中间数据 | 事实清单、法律问题（Issue）、证据链、材料缺口 | `facts`=22条（全部`supporting_material_refs=[]`），`issues`=1条（`related_facts=[]`），`evidence_chain`=5条（`legal_basis=[]`/`supporting_basis=[]`），`material_gaps=[]`（但`filing_readiness=supplement_required`） | ⚠️ facts引用链全空、issue无关联fact、material_gaps与filing_readiness矛盾 |
| 需求中提出的测试风险点 | 隐私政策关联方未明确列出新加坡运营中心；哈希化Device_ID未提供算法分析；Product_Category_Preference含隐含敏感标签；Hashed_Device_ID被用户误标为"非个人信息" | 报告正文**实际触及了**告知同意缺陷+敏感信息误分类，**也触及了**50万用户同意的有效性分析。但哈希算法安全性和"非个人信息"误标的分析**不够深入** | ⚠️ 核心风险点覆盖了一半 |

#### ✅ tia — TIA草案生成

| 维度 | 需求文档规定的产出 | 实际运行结果 | 差距 |
|------|------|------|------|
| 交付物 | `TIA草案` — 按EDPB六步法：了解传输→识别工具→评估目的地法律→识别补充措施→实施步骤→定期复审 | `markdown.md` 19,040B，6章7179字符，docx 44,089B | ✅ 完整 |
| 报告结构 | 6章：跨境传输场景与角色识别 → 传输工具适用性判断 → 第三国法律与实践评估 → 补充措施可执行性评估 → 剩余风险与合规结论 → 持续复审与行动计划 | 6章全部有实质内容，最长章(第三国法律评估)1391字符 | ✅ 六步法严格执行 |
| 核心检验点（需求规定） | 明确指出美国FISA 702和CLOUD Act法律可能妨碍SCCs有效性；端到端加密+欧盟密钥管理为核心技术措施；基于补充措施判断传输可进行；DPO有条件同意 | 第三国法律分析完整列出FISA 702/CLOUD Act/EO 12333；补充措施：端到端加密+欧盟密钥管理+合同加强+定期审计；最终结论：MEDIUM，"有条件地达到欧盟基本同等保护水平"；DPO意见："No objection" | ✅ 全部触及 |
| 需求规定的高风险提示 | 补充措施有效性依赖加密强度；建议独立第三方安全审计 | 正文明确写了"若法律要求直接针对数据进口方迫使其削弱加密或交出密钥则此措施可能失效"，但**未展开评估加密算法强度/密钥管理方案/内存解密风险窗口/法律强制密钥披露风险** | ⚠️ 降级逻辑（HIGH→MEDIUM）依赖单一技术措施，缺乏量化支撑 |
| 工程问题 | 不应出现"推测"措辞、不应出现`【待核验】`标记 | 第28行有`【推测】`措辞（"推测"在正式TIA报告中不应出现）；6处`【待核验：缺少法规依据】`注入 | ⚠️ 工程标记+非正式措辞泄漏到正式报告 |

#### ⚠️ assessment — 安全评估路径

| 维度 | 需求文档规定的产出 | 实际运行结果 | 差距 |
|------|------|------|------|
| 交付物 | `《数据出境风险自评估报告（草案）》` — 严格按网信办《申报指南》模板 | `markdown.md` 8,472B，8章2758字符，docx 38,539B。**另有** body/internal/internal_review/compliance_reasoning/official 五个markdown变体 | ✅ 报告本体完整 |
| 需求规定的模板8章 | 自评估工作情况 → 出境活动整体情况(含数据处理者/出境数据/安全保障/接收方/法律文件) → 出境影响评估 → 结论 | 8章各有内容，每章134-445字符 | ✅ 模板覆盖 |
| **核心业务矛盾**（需求文档未预期的情况） | 需求文档假设：触发安全评估门槛 → 生成安全评估报告。测试案例一的CIIO金融机构案例预期生成安全评估报告 | **实际**：`profile.path_judgment_json`=空字符串；但一致性检查指出"诊断推荐路径为scc_or_certification：未触发强制安全评估门槛，可走标准合同备案或认证路径"；报告第79行自认"路径不匹配，本报告为强制生成的参考草案" | 🔴 **路径矛盾**：系统明知不应该生成安全评估报告，仍然生成了完整的8章报告并标注COMPLETED |
| 需求规定的结构调整 | `交付2：生成草案的逻辑` | `path_judgment_json`=`""`，`compliance_reasoning_json`=`""`，`material_checklist_json`=`""`，`consistency_report_json`=`""` — profile内4个关键中间数据字段全部空字符串 | ⚠️ 需求规定的"生成草案的逻辑"在结构化层完全缺失 |
| 需求规定的材料清单 | 评估报告模板附带的材料清单（20+项：营业执照/数据出境合同/隐私政策/安全评估报告/数据清单/接收方保障文件等） | `material_checklist_json`仅包含1条泛化条目`{source_ref:"user_claim", summary:"根据用户输入字段推断的材料需求", status:"待补充"}` — 实际生成的 `material_checklist_json.json` 仅196B | ⚠️ 材料清单远未覆盖需求规定的20+项 |

#### ⚠️ eu_scc — SCC审查

| 维度 | 需求文档规定的产出 | 实际运行结果 | 差距 |
|------|------|------|------|
| 交付物 | `《SCC合规审查报告》`：文件概要→总体评级→**条款级审查发现（每项含6要素：定位/原文引用/问题类型/风险分析/法规依据/修改建议）** | `markdown.md` 12,937B，4章5156字符，`docx`+`annotated_docx`各41KB | ✅ 格式完整 |
| **条款级发现的6要素** | 逐条含：定位(条款号)、**原文引用**(有问题的原文)、问题类型、风险分析、法规/标准依据、修改建议（提供具体可参考的修改文本） | 8条findings：**6/8条`original_text=null`**（缺原文引用）；**7/8条`suggested_text`有值但仅1条给出具体对比**（其余为通用描述如"Restore the standard EU 2021/914 text"） | 🔴 **核心要素缺失**：6条发现无法告诉用户"原来写的是什么"；条款级审查降级为清单级标注 |
| 需求测试案例的核心预期 | "总体合规评级：高风险……完全缺失了Schrems II判决和EDPB建议01/2020所要求的核心合规步骤：对数据最终存储地（美国）的法律环境进行影响评估，并实施有效的补充措施" | 实际有TIA缺失和补充措施不足的发现，但正文用了大量篇幅逐项说"未提供"——共12处 | ⚠️ 报告偏向"输入校验"（什么东西没提供）而非需求规定的"条款深度分析" |
| 特殊产出 | 需求未明确要求但有价值 | `annotated_docx.docx` 41KB — 含修订批注的SCC文档 | ✅ 超预期 |
| 模块验证 | 需求未明确要求但有价值 | `module_validation: {expected:"Module Two", actual:"Module Two", is_correct:true}` — 正确识别了C→P模块类型 | ✅ 验收通过但未在正文中突出 |

#### ⚠️ bcr — BCR审核

| 维度 | 需求文档规定的产出 | 实际运行结果 | 差距 |
|------|------|------|------|
| 交付物 | `《BCR-C合规审查报告》`：总体评级+**逐条发现含改进建议的具体修改文本** | `markdown.md` 13,747B，4章9100字符 | ✅ 格式完整 |
| 需求测试案例核心预期 | "总体合规评级：部分缺失……发现的问题总数：3个中风险问题"；**逐条给出具体改进建议文本**：如"修改为：'...且该第三方已通过签订包含SCCs的协议……'" | `findings`=26条，`missing_requirements`=2条，`review_mode=rule_only`，`llm_remediation_count=0` | ⚠️ 26条发现覆盖远超需求的3条，但全部是规则引擎驱动，**无LLM深度分析** |
| **修改建议的具体性** | 需求明确要求提供**具体的、可直接采用的修改文本** | 整改建议章节含11处模板占位符：`[Company Name]`3处，`[EU Member State]`7处，`[Insert specific clause...]`2处。`review_metadata.template_remediation_count=9` — 9条整改全部由模板生成 | 🔴 **关键交付物不可用**：需求规定的"具体修改文本"变成了未填充的模板骨架 |
| BCR类型判定 | 判定BCR-C/BCR-P类型 | `bcr_type_classification: {declared:"BCR-C", actual:"BCR-C", type_consistency:"consistent"}` | ✅ 判定正确 |

#### ⚠️ diagnosis — 合规路径诊断

| 维度 | 需求文档规定的产出 | 实际运行结果 | 差距 |
|------|------|------|------|
| 交付物 | `《合规路径诊断报告》`：用户答案摘要+判定逻辑树+逐条法规依据+核心风险提示+后续行动建议 | `_result.json` 1,126B，**无渲染文档**（diagnosis模块不出markdown/docx） | 🔴 **核心缺口**：需求规定交付诊断报告文档，实际仅有JSON |
| 核心结论 | 明确的合规路径（exemption/scc/certification/安全评估） | `recommended_path=exemption`，`rationale="不含个人信息且不涉及重要数据，无需申报"`，`confidence=HIGH`，`conclusion_source=rule` | ✅ 结论准确 |
| 用户答案摘要 | 表格形式列明所有问题与答案 | `fact_provenance`=8键，记录了每个事实的来源（全部`"user"`） | ⚠️ 有来源但无表格形式呈现 |
| 判定逻辑树 | 可视化或文本化的判定链路 | **无** — `_result.json`中没有`logic_tree`或`decision_path`字段 | 🔴 缺失 |
| 逐条法规依据 | 每条判定附引用法规 | `legal_basis`=2条（促进规范数据跨境流动规定第4条、网络数据安全管理条例第38条） | ✅ 有依据但未展开条文内容 |
| 核心风险提示 | 明确的风险提示 | `uncertainty_notes`=1条（"豁免情形辅助判断: hr_management 置信度65%"） | ⚠️ 有风险提示但过于简略 |
| 后续行动建议 | 具体的行动清单 | `action_items`=3条（确定实施路径/生成PIPIA报告/准备备案材料） | ✅ 行动清单完整 |

#### 🔴 dpia — DPIA草案生成

| 维度 | 需求文档规定的产出 | 实际运行结果 | 差距 |
|------|------|------|------|
| 交付物 | `DPIA草案` — 按ICO模板7章：识别需求→描述处理→咨询→必要性与相称性→风险评估→缓解措施→签署与记录 | `markdown.md` 2,137B（其中正文仅占位文本），docx 37,076B（内容同为占位） | 🔴 7章正文=7句"LLM未配置，此处为占位内容" |
| 需求测试案例核心预期 | 风险评估矩阵"以表格形式列出5项风险，附可能性和影响评级，综合评级多为高风险"；缓解措施"针对歧视、不透明、过度监控三大高风险列出具体可验证的措施"；DPO给出"有条件同意并列出必须满足的三大前置条件" | 9个Agent**全部跑完**：`need_assessment`（触发4项理由）→`processing_activity_pack`（识别1个处理环节+8类数据）→`necessity_findings`（发现浏览记录/互动行为过度收集）→`risk_matrix`（2条风险：特殊类别推断HIGH+透明度MEDIUM）→`mitigation_plan`（2条，全部planned状态）→`dpo_decision_pack`（有条件同意+3条件）→`internal_ai_review`（建议暂缓上线）→`consistency_report`（10/10通过） | 🔴 **最可惜的模块**：9个Agent产出了253KB的完整中间态数据（`generation_basis_pack_json.json`=474KB），证明了架构正确性。但最终7章正文因LLM未启用（`common/llm/client.py:73` `_enabled=False`）全部降级为占位文本。用户收到的是一份含7句空话的报告 |
| Agent中间态质量 | 需求未明确要求Agent中间态，但实际产出的中间态极具价值 | `necessity_findings.questionable_processing[0].processing`=Python repr字符串 `"{'step': '数据处理', 'actor': ...}"`（未JSON序列化）。`internal_ai_review.insufficient_evidence_items`含`'False'`字符串+`"['学生ID', ...]"` repr | ⚠️ Python repr泄漏到结构化字段，需修复序列化 |

#### 🔴 us_14117 — 14117行政令合规

| 维度 | 需求文档规定的产出 | 实际运行结果 | 差距 |
|------|------|------|------|
| 交付物 | `《14117行政令风险评估结论报告》` — 格式PDF/HTML | **2026-08-07 快照**：`markdown.md`仅1,961B、`docx.docx`=0B；2026-08-10 新产物 DOCX 约 38 KB，仍需重新核对实体清单、数据分布表和风险矩阵 | 🔴 快照失败，当前待复验 |
| 需求规定：**首页红黄绿灯标签** | "在报告首页以显著标签形式，给出明确的红/黄/绿灯结论" | `overall_traffic_light=YELLOW`，`traffic_light_result`结构完整（含受限原因+21项安全措施清单） | ⚠️ 数据有但标记在正文中仅以文字形式呈现，无显著标签格式 |
| 需求规定：**高风险实体清单** | "列出所有被识别为'被涵盖的人'的实体，并说明判定依据（股权结构显示由关注国控股、注册在关注国、受该国法律管辖等）" | `risk_matrix`=1条，包含实体判定依据（"Registered in country of concern: China；Governed by law of country of concern；Access person resides in China"）。**但**无独立实体清单表格 | ⚠️ 信息分散在risk_matrix的一条记录中，未结构化展示 |
| 需求规定：**敏感数据分布** | "以表格和图表形式，展示各类'批量敏感个人数据'和'美国政府相关数据'在业务系统中的存量、涉及数据主体规模以及计划出境体量" | **无**表格/图表。正文仅一段无格式文本提及数据项名称和阈值 | 🔴 完全缺失 |
| 需求规定：**风险匹配矩阵** | "清晰展示'哪些高风险实体'计划接收'哪些类别的敏感数据'" | **无**矩阵 | 🔴 完全缺失 |
| 需求规定：**合规措施建议与行动清单** | 安全措施框架（加密/访问控制/日志审计/安全培训）+具体行动步骤 | `traffic_light_result.restriction_reasons`=1条，`required_security_measures`=21项（含logical_isolation/MFA/least_privilege/RBAC/encryption_at_rest等） | ✅ 21项安全措施列表完整，但正文未逐一展开说明 |
| 规则引擎产出 | 24条rule_hits覆盖交易分类+阈值触发+受限制主体识别+安全措施检查 | rule_hits全无`category`字段，无法区分规则命中类型 | ⚠️ 缺少分类维度 |

#### 🔴 cpra — CPRA合规

| 维度 | 需求文档规定的产出 | 实际运行结果 | 差距 |
|------|------|------|------|
| 交付物 | `《加州CPRA合规全景报告》`：执行摘要→企业适用性→数据处理活动合规分析→消费者权利保障→敏感信息与第三方管理→行动清单与优先级 | **2026-08-07 快照**：`markdown.md` 807B、6/6章占位；2026-08-10 已有非占位 Markdown 产物，但引用完整性、业务域覆盖和 DOCX/PDF 仍未完成复验 | 🔴 快照失败，当前待复验 |
| 需求测试案例核心预期 | "总体合规评级：部分缺失"；"核心发现：选择退出机制不符合法规格式要求、广告合作伙伴数据共享安排未明确CPRA义务、Cookie横幅存在暗模式风险"；"DSR机制：在线表单和邮箱渠道符合要求但缺少免费电话提交方式" | 5条`gap_items`覆盖4/10 domain（notice_and_consent、consumer_rights_process、opt_out_and_sale_sharing、consent_ui），全部有legal_basis（CPRA §编号精确）。**但6/6章正文=占位** | 🔴 结构化gap有数据（5条），但最终报告正文完全不可用。LLM未启用导致全景分析的叙述性内容全部丢失 |
| 章节覆盖 | 需求规定的执行摘要/企业适用性/数据处理合规/消费者权利/敏感信息/行动清单六大板块 | `chapters`=6章全部占位文本，每章21-27字符 | 🔴 6/6章空白 |
| domain覆盖 | 需求隐含应覆盖CPRA全部核心领域 | 仅4/10 domain有gap，6个domain（sensitive_pi/data_minimization/purpose_limitation/vendor_management/data_retention/security_safeguards）无任何检查结果 | ⚠️ 覆盖率40% |

#### 🔴 cn_flow — 中国数据出境(美视角EO14117)

| 维度 | 需求文档规定的产出 | 实际运行结果 | 差距 |
|------|------|------|------|
| 交付物 | 代码衍生模块——EO14117框架的"中国方向"视角，应产出4章风险评估报告 | **2026-08-07 旧独立流程快照**：4/4章占位；当前已统一委托 `us_14117`，旧章节流水线已删除，需按新入口重新验收 | 🔴 旧快照失败，当前待复验 |
| 结构化数据 | 风险项+事实+证据链 | `risk_items`=1条（"存在敏感数据跨境流动", HIGH）；`facts_json`=5,732B；`evidence_chain_json`=1,295B | ⚠️ 结构化层有数据但仅1条risk_item承载全部分析，过于聚合 |
| 附件解析 | 上传的data_inventory.csv+entity_inventory.csv应被解析填充到报告中 | `attachment_notes`=2条，**全部为文件未找到错误** —— csv解析失败 | 🔴 附件未成功解析 |

#### 🔴 review — 文档专项智能审查

| 维度 | 需求文档规定的产出 | 实际运行结果 | 差距 |
|------|------|------|------|
| 交付物 | `《数据出境合同合规审查报告》`：文件概要→总体评级→**逐条条款级审查发现**（每项含6要素：定位/原文引用/问题类型/风险分析/法规依据/修改建议） | `_result.json`仅含摘要数据；docx+pdf存在（各49KB/92KB），但实际是聚合报告而非逐条审查报告 | 🔴 **最大差距** |
| 需求明确规定的6要素 | **定位**（问题所在文件/章节/页码/条款号）→ **原文引用**（摘录有问题的合同原文）→ **问题类型**（缺失条款/定义模糊/责任限制过度/与法规冲突/与实践不一致）→ **风险分析**（解释可能引发的法律/商业/操作风险）→ **法规/标准依据**（引用条文/监管要求/行业最佳实践）→ **修改建议**（提供具体可参考的修改文本或新增条款草案） | `result={risk_level:"高风险", summary:"共识别41个问题7个全局缺失项其中HIGH23个MEDIUM15个LOW3个", issue_counts:{HIGH:23,MEDIUM:15,LOW:3}}` — **仅有计数，无任何逐条6要素** | 🔴 需求规定的是**条款级审查报告**（逐条含原文引用→法规依据→修改建议），实际产出的是**问题计数摘要**（23高+15中+3低）。这完全不是同一个产物 |
| 需求测试案例的预期 | "总体合规评级：高风险……条款级审查发现（部分示例）：定位：全局性缺失；问题类型：缺失条款（重大遗漏）；风险分析：协议未约定数据处理的地理位置……法规依据：《个人信息保护法》第三十八条……修改建议：增加'数据处理地点'条款……" | 无 | 🔴 完全缺失 |

---

### 14.2 差距严重度分级

| 等级 | 数量 | 模块 | 判据 |
|:---:|:---:|------|------|
| ✅ **基本满足需求** | 2 | pipia、tia | 报告结构+核心结论+关键分析维度全部到位，仅存在工程标记/措辞等可修复的轻度问题 |
| ⚠️ **部分满足** | 5 | assessment、eu_scc、bcr、diagnosis、review（实际为docx聚合） | 主体产出存在但存在 **关键业务逻辑矛盾**(assessment路径矛盾)、**核心要素缺失**(eu_scc原文引用/scc报告)、**关键交付物不可用**(bcr模板变量) 或 **输出形态不对**(review只有计数无逐条分析) |
| 🔴 **严重不满足（快照）** | 4 | dpia、us_14117、cpra、cn_flow | 2026-08-07 快照中报告正文不可用；14117、CN Flow 已有后续代码修复，不能直接作为当前结论 |

---

### 14.3 按法域的跨模块总结

#### 中国法域（4任务）

| 任务 | 需求核心 | 达标情况 | 一句话差距 |
|------|------|:---:|------|
| 合规路径诊断 | 给出豁免/scc/认证/安全评估的明确结论+法规依据+行动建议 | ⚠️ | 结论正确但无渲染文档，缺判定逻辑树 |
| 安全评估路径 | 按网信办模板生成8章评估报告 | ⚠️ | 报告完整但路径结论自相矛盾（推荐scc却生成了安全评估报告） |
| 认证标准合同路径 | 按备案指南模板生成7章PIPIA报告 | ✅ | 内容覆盖完整，关键风险点触及一半 |
| 文档专项智能审查 | 逐条条款级审查（定位+原文引用+问题类型+风险分析+法规依据+修改建议）→ **6要素** | 🔴 | 仅有41问题的计数聚合，**0条逐条6要素** |

#### 欧盟法域（4任务）

| 任务 | 需求核心 | 达标情况 | 一句话差距 |
|------|------|:---:|------|
| SCC审查 | 条款级发现（6要素）→ 逐条定位/原文引用/修改建议 | ⚠️ | 8条发现但6/8无原文引用，报告偏"材料核对" |
| BCR审核 | 逐条发现+**具体修改文本** | ⚠️ | 26条发现覆盖全但修改建议=11处未填充模板变量 |
| DPIA草案生成 | 按ICO模板7章：风险评估矩阵+缓解措施+DPO意见 | 🔴 | 9Agent中间态满分，7章正文全部占位→差LLM一行配置 |
| TIA草案生成 | 按EDPB六步法：法律分析+补充措施+最终结论 | ✅ | 核心逻辑链清晰，仅工程标记泄漏 |

#### 美国法域（2任务）

| 任务 | 需求核心 | 达标情况 | 一句话差距 |
|------|------|:---:|------|
| 14117行政令合规 | 红黄绿灯+实体清单+敏感数据分布表+风险匹配矩阵+安全措施清单 | 🟡（快照） | 快照中结构化引擎输出完整但报告无格式呈现、DOCX=0B；当前产物已修复生成，业务版式仍待复验 |
| CPRA合规 | 6章全景报告：消费者权利+敏感信息+第三方管理+行动清单 | 🟡（快照） | 快照中 5 条 gap 有数据、6/6 章占位；当前已有非占位产物，尚未完成全链路复验 |

---

### 14.4 差距集中根因

```
        需求规定的最终交付物形态
        ↓
┌───────────────────────────────────────┐
│  逐条条款审查报告 (Review)              │  ← 🔴 完全未实现
│  逐条6要素：定位+原文引用+问题类型+       │
│  风险分析+法规依据+修改建议               │
├───────────────────────────────────────┤
│  结构化报告：红黄绿灯+实体清单+矩阵+图表   │  ← 🔴 快照中 us_14117 docx=0B
├───────────────────────────────────────┤
│  7/6/4章专业分析报告正文                 │  ← 🔴 dpia/cpra/cn_flow 全占位
│  (由LLM生成的叙述性分析)                │      根因: client.py:73 _enabled=False
├───────────────────────────────────────┤
│  中间结构化数据层 (facts/evidence/gaps)  │  ← ⚠️ pipia引用链空壳
│  (规则引擎+Agent产出)                   │      assessment 4个JSON字段全空
├───────────────────────────────────────┤
│  法规检索+规则引擎判定层                 │  ← ✅ 全部模块此层运行正常
│  (RAG/rule_engine)                     │
└───────────────────────────────────────┘

三层缺口自下而上：
  L1 规则引擎层  → 11/11 模块正常
  L2 中间数据层  → 6/11 模块有字段空值/引用断链问题
  L3 LLM叙述层   → 2026-08-07 快照中 4/11 模块出现未启用/降级或渲染失败；当前状态需重新运行确认
  L4 条款审查层   → review模块产出形式完全不符合需求规定的6要素格式
```



---

## 十五、业务需求差距分析：需求文档规定的预期产出 vs 实际运行结果

> 数据来源：原 `resources/new/数规通功能路径描述（含reference）、流程描述、测试案例/` 已迁移并删除；当前依据为 `benchmarks/source-materials/{cn,eu,us}/legacy-docx/` 中的来源文档及 `status/check/task065/case-disposition.v1.json` 的来源 Hash，对照 `tmp/` 下历史 `_result.json` 和渲染文件。
>
> 本节回答一个问题：**业务需求要什么 vs 代码实际给了什么，差距在哪**。

---

### 15.0 需求中的10个任务与代码中11个模块的映射

| 需求任务 | 代码模块 | 法域 |
|------|:---:|:---:|
| 任务1: 合规路径诊断 | diagnosis | 中国 |
| 任务2: 安全评估路径 | assessment | 中国 |
| 任务3: 认证/标准合同路径 | pipia | 中国 |
| 任务4: 文档专项智能审查 | review | 中国 |
| 任务5: SCC审查 | eu_scc | 欧盟 |
| 任务6: TIA草案生成 | tia | 欧盟 |
| 任务7: GDPR合规诊断 | *(待确认，可能为dpia或独立模块)* | 欧盟 |
| 任务8: BCR审核 | bcr | 欧盟 |
| 任务9: 14117行政令合规 | us_14117 | 美国 |
| 任务10: CPRA合规 | cpra | 美国 |
| *(需求未独立定义)* | dpia | 欧盟 |
| *(需求未独立定义)* | cn_flow | 美国→中国 |

> 注：dpia 在需求文档中对应"DPIA草案生成"（任务3-欧盟），cn_flow 在需求文档中无独立任务定义。

---

### 15.1 diagnosis — 合规路径诊断

**需求规定的预期产出** (`资源/中国/任务1/功能说明`):

> 《合规路径诊断报告》，包含：
> 1. **核心结论**：以逻辑推导出的最终合规路径
> 2. **结构化诊断报告**：用户答案摘要、判定逻辑树、逐条法规依据、核心风险提示、后续行动建议

**需求规定的测试案例预期** (`测试案例一：电商用户数据出境`):
> 输入：跨境电商平台，45万用户订单数据→新加坡，非CIIO，不含敏感信息
> 预期输出：**"应当通过订立个人信息出境标准合同或者通过个人信息保护认证的途径"** + 用户答案摘要表 + 逐条法规依据

| 需求要求 | 实际产出 | 差距 |
|------|------|------|
| 核心结论：标准合同/认证路径 | recommended_path=**exemption**（豁免） | 🔴 **结论错误** — 45万用户应走标准合同，不应豁免 |
| 结构化诊断报告 | result.json 仅有字符串字段，无表格/逻辑树 | 🟡 有结构但缺"诊断报告"格式 |
| 用户答案摘要 | fact_provenance 有8键映射 | ✅ |
| 判定逻辑树 | 缺失 — 仅有 matched_rule_id 和 conclusion_source | ❌ 需求规定的逐步骤决策过程不可见 |
| 逐条法规依据 | legal_basis 有2条（促进规范跨境流动规定第4条 + 网络数据安全管理条例第38条） | ⚠️ 仅2条，测试案例预期应引用《个保法》第38条等多条 |
| 逐步骤决策过程可追溯 | 不可见 — 需求文档规定了5步判定流程，但结果中无步骤中间态 | ❌ |
| 渲染文档（.docx/.pdf） | 无 — diagnosis不生成任何渲染文档 | ❌ 需求要求"生成并交付文件" |

**业务的实质差距**：
1. **路径判定错误**：测试案例"45万用户+非敏感+非CIIO"应出标准合同路径，实际出了exemption，完全无法使用
2. **无渲染文档**：需求明确说"生成并交付文件《合规路径诊断报告》"，实际只有JSON，用户看不到报告
3. **不可追溯**：需求规定的5步诊断流程（识别重要数据→识别个人信息→查豁免→确认CIIO→量化个人信息），在结果中无任何步骤记录

---

### 15.2 assessment — 安全评估路径

**需求规定的预期产出** (`资源/中国/任务2/功能说明`):

> 交付1：《数据出境风险自评估报告（草案）》
> - 严格遵循网信办《数据出境安全评估申报指南》所附模板
> - 包含：自评估工作情况、出境活动整体情况（含数据处理者基本情况→拟出境数据情况→数据安全保障能力→境外接收方情况→法律文件约定）、拟出境数据风险评估、风险防范和整改措施、自评估结论
> 交付2：《生成草案的逻辑》

**需求规定的测试案例预期** (`测试案例一：CIIO金融机构`):
> 输入：东方信托（CIIO金融机构），向香港母公司传输交易结算+高净值客户数据
> 预期输出：触发安全评估路径，输出完整的自评估报告

| 需求要求 | 实际产出 | 差距 |
|------|------|------|
| 8章完整报告按网信办模板 | 8章2758字符，章节结构完整 | ✅ 结构符合 |
| 报告应是安全评估路径结论 | consistency_issues[0] = "诊断推荐路径为 scc_or_certification：未触发强制安全评估门槛" | 🔴 **路径矛盾** — 系统知道自己判的是scc路径，但仍然生成了安全评估报告 |
| CIIO/重要数据判定 | profile中 is_ciio=False, contains_important_data=False | ✅ 判定正确（测试案例使用了另一个场景） |
| 材料清单 | material_checklist_json = ""（空字符串） | ❌ 需求要求的材料清单完全缺失 |
| 合规推理（为什么得出此结论） | compliance_reasoning_json = ""（空字符串） | ❌ 需求要求的合规推理链完全缺失 |
| 一致性审查 | consistency_report_json = ""（空字符串） | ❌ |
| 生成草案的逻辑（交付2） | path_judgment_json = ""（空字符串） | ❌ 需求明确要求的第二份交付物缺失 |
| 法规引用 | regulations=98条，但article_no全部为空，quote_text为空 | ❌ 98条法规全是标题清单，无条款正文 |

**业务的实质差距**：
1. **路径矛盾是最致命的业务问题**：系统自己判定"推荐路径=scc_or_certification，不需要安全评估"，但依然生成了完整的《数据出境风险自评估报告》并标记COMPLETED。用户收到的是一份**系统自认"不需要"的报告**
2. **profile中4个关键JSON全空**：路径判断、合规推理、材料清单、一致性审查——这些正是需求文档要求"生成草案的逻辑"应包含的内容
3. **无法规条款正文**：98条检索结果全部没有 article_no 和 quote_text，无法在报告中做条款级引用

---

### 15.3 pipia — 认证/标准合同路径

**需求规定的预期产出** (`资源/中国/任务3/功能说明`):

> 交付1：《个人信息保护影响评估报告（草案）》
> - 严格遵循《个人信息出境标准合同备案指南（第二版）》附件5模板
> - 7章：处理者与出境活动基础信息 → 个人信息出境处理活动说明 → 境外接收方信息与保护能力 → 个人信息主体权益影响评估 → 技术与组织措施有效性评估 → 事件响应与整改计划 → PIPIA结论与备案建议

**需求规定的测试案例预期** (`测试案例一：跨境电商50万会员数据`):
> 输入：海淘优选，50万高价值会员→新加坡，声称"单独同意"+"合同履行必要性"双基础
> 预期输出：识别3个风险点——(1)隐私政策关联方列举不明确、(2)"个性化服务"作为合同必要性的论证宽泛、(3)设备ID哈希化未提供防碰撞分析、(4)母婴/医疗标签未被标为敏感信息
> 预期结论：需补充同意记录、明确关联方、重新评估敏感信息分类

| 需求要求 | 实际产出 | 差距 |
|------|------|------|
| 7章完整PIPIA报告 | 7章8567字符，质量最高 | ✅ |
| 识别"合法性基础双重主张"矛盾 | 正文明确指出了"基于个人同意"与"为履行合同所必需"的逻辑矛盾 | ✅ |
| 识别设备ID哈希化风险 | 正文提到了哈希化的去标识化局限性 | ✅ |
| 识别商品偏好标签的敏感信息风险 | 正文对ProductCategoryPreference做了详细分析 | ✅ |
| 备案准备度判定 | filing_readiness.status=supplement_required, 建议先完成高风险整改再推进备案 | ✅ |
| 材料缺口 | material_gaps=[]（空列表） | 🔴 需求要求的4个风险点中，"提供防碰撞分析报告"和"补充同意记录"应在material_gaps中列出，但实际为空 |
| 结构化Issue | issues=1条（"风险等级较高"），但正文实际分析了5+独立维度 | 🔴 Issue层严重落后于正文——正文分析了告知不足/分类错误/保障缺失/条款缺失/行权缺位，但结构化层只产出了1条聚合Issue |
| facts→issue引用 | issue.fact_refs=[]，22条facts零条被关联 | ❌ facts层完全孤立 |

**业务的实质差距**：
1. **正文质量合格，但结构化层跟不上**：用户如果只看正文可以接受，但如果需要结构化的风险清单（如在系统中做逐条跟踪和整改），则完全不可用
2. **材料缺口为零但确实缺材料**：系统知道需要补充材料（filing_readiness=supplement_required），但没有列出具体缺什么——用户不知道该去补什么
3. **测试案例的4个风险点，正文覆盖了3个**（"提供防碰撞分析报告"这项在正文中提到了但未作为明确的整改建议列出）

---

### 15.4 review — 文档专项智能审查

**需求规定的预期产出** (`资源/中国/任务4/功能说明`):

> 《数据出境合同（法律文件）合规审查报告》
> 格式：.docx
> 内容结构：
> 1. **文件概要**：列出已审查的文件名称、审查所依据的主要法律法规框架
> 2. **总体合规评级**：总结性判断
> 3. **条款级审查发现（报告主体）**：以清单形式**逐项**列出，每项含：
>    - **定位**：问题所在的文件、章节、页码/条款号
>    - **原文引用**：摘录有问题的合同原文
>    - **问题类型**：缺失条款/定义模糊/责任限制过度/与法规冲突/与实践不一致
>    - **风险分析**：解释可能引发的法律、商业或操作风险
>    - **法规/标准依据**：引用法律法规条文
>    - **修改建议**：具体的、可供参考的修改文本或新增条款草案

**需求规定的测试案例预期** (`测试案例一：金陵科技学院数据安全保密协议`):
> 植入5个风险点：缺失数据出境条款、安全义务模糊(缺少时限)、管辖权对委托方不利、未区分数据类型、缺乏审计权条款
> 预期输出：总体合规评级=高风险，逐条列出5个问题的6要素分析，每条含具体修改建议文本

| 需求要求 | 实际产出 | 差距 |
|------|------|------|
| .docx格式报告 | docx=49KB, pdf=92KB | ✅ |
| 文件概要 | 缺失 | ❌ |
| 总体合规评级 | risk_level=高风险, result.summary="共识别41个问题7个全局缺失项其中HIGH 23个" | ⚠️ 有总体描述但结构简陋 |
| **逐条条款级发现（6要素）** | **完全缺失** — result.json中只有聚合计数，没有逐条发现的结构化列表 | 🔴 **最严重差距** |
| 每条的原文引用 | 缺失 | ❌ 需求的核心要求 |
| 每条的修改建议文本 | 缺失 | ❌ 需求的核心要求 |
| 每条的法规依据 | 缺失 | ❌ |
| 每条的定位（章节/条款号） | 缺失 | ❌ |
| 每项的问题类型分类 | 缺失 | ❌ |

**业务的实质差距**：
review模块是**需求与实际差距最大的模块**。需求文档明确规定了"条款级审查发现（6要素）"的格式——这是文档审查报告的核心价值所在。但实际产出只有一句聚合摘要。用户拿到的报告中**完全看不到逐条分析**，不知道具体哪个文件的哪个条款有什么问题、应该怎么改。

---

### 15.5 eu_scc — SCC审查

**需求规定的预期产出** (`资源/欧盟/任务1/功能说明`):

> 《SCC合规审查报告》，格式.docx
> 内容结构：
> 1. 文件概要
> 2. 总体合规评级
> 3. **条款级审查发现**（逐条6要素：定位/原文引用/问题类型/风险分析/法规依据/修改建议）

**需求规定的测试案例预期** (`测试案例一：C2C模块缺失补充措施`):
> 植入风险点：缺失TIA评估、缺失补充措施、数据类别描述模糊
> 预期输出：总体评级=高风险。逐条发现含原文引用和具体修改建议

| 需求要求 | 实际产出 | 差距 |
|------|------|------|
| 文件概要 | 有（4章之一，1222字符） | ✅ |
| 总体合规评级 | overall_rating=HIGH | ✅ |
| 条款级发现（6要素） | 8条findings，每条有 clause_ref+issue_type+severity+suggested_text | ⚠️ 结构有 |
| **每条的原文引用** | 8条中仅2条有original_text（Clause 15(a)和Annex I.B），**6条original_text=null** | 🔴 缺失75% |
| **每条的修改建议文本** | 8条finding中仅1条有suggested_text，**7条为null** | 🔴 缺失87.5% |
| 每条的法规依据 | 8/8有legal_basis | ✅ |
| 每项的定位 | 有clause_ref标注 | ✅ |

**业务的实质差距**：
eu_scc 的finding结构是完整的（8条有clause_ref/issue_type/severity），但**最有业务价值的两个字段——原文引用和修改建议——大面积缺失**。没有原文引用，用户不知道"原来的文本是什么"；没有修改建议，用户不知道"应该改成什么"。报告从"条款审查"退化成了"问题标注清单"。

此外，报告正文偏向**"材料核对"**（12处"未提供"）而非**"条款质量分析"**——需求文档描述的是后者。

---

### 15.6 bcr — BCR审核

**需求规定的预期产出** (`资源/欧盟/任务2/功能说明`):

> 《BCR-C合规审查报告》，格式.pdf/.docx
> 报告核心结构：（需求文档未逐项列明，但测试案例预期了）
> - 总体合规评级
> - 主要发现摘要（问题总数 + 高/中/低风险计数）
> - **条款级审查发现**：每项含定位/审查结果/问题描述/**改进建议**

**需求规定的测试案例预期** (`测试案例一：基本合规但有中风险问题的BCR-C`):
> 植入风险点：TIA描述笼统、投诉流程不具体、向集团外传输限制模糊
> 预期：总体评级=部分缺失，3个中风险问题，每条有具体的改进建议文本

| 需求要求 | 实际产出 | 差距 |
|------|------|------|
| 总体评级 | rating=高风险（3字） | ⚠️ 测试案例预期"部分缺失"，实际"高风险" — 评分可能过严 |
| 问题计数 | findings=26条, missing_requirements=2条 | ✅ 数量充足 |
| 条款级发现 | 26条findings，每条有 finding_id/requirement_id/location/clause_excerpt/finding/legal_basis/recommendation/suggested_revision | ⚠️ 结构完整 |
| 具体的改进建议文本 | suggested_revision字段存在但有**11处模板变量未替换**（[Company Name]×3、[EU Member State]×7、[Insert specific clause...]×2） | 🔴 整改建议不可用 |
| LLM参与深度分析 | review_metadata: review_mode="rule_only", llm_remediation_count=0, template_remediation_count=9 | ⚠️ 需求未明确要求LLM，但26条全是规则引擎 |

**业务的实质差距**：
1. **整改建议不可用**：需求要求"具体的、可供参考的修改文本"，实际建议全是含 `[Company Name]`、`[EU Member State]` 的模板骨架——用户拿到后还需要自己逐条填入公司名和成员国名
2. **26条发现全是规则引擎**：对比需求文档测试案例的3个风险点，规则引擎覆盖了更多（26条），但深度不足——例如"投诉流程不具体"这类需要自然语言分析的缺陷，规则引擎只能标记为"条款存在但内容不具体"，而无法像测试案例预期的那样给出具体的流程重构建议

---

### 15.7 dpia — DPIA草案生成

**需求规定的预期产出** (`资源/欧盟/任务3/功能说明` + ICO DPIA模板):

> DPIA草案，按ICO模板7章：
> 1. 识别DPIA需求（依据WP248九项标准判断是否触发）
> 2. 描述处理活动（系统性描述数据流/数据类型/数据量/保留期/跨境传输）
> 3. 咨询过程（DPO意见 + 数据主体咨询）
> 4. 必要性与相称性评估（是否为实现目的所必需、是否遵循数据最小化）
> 5. 识别与评估风险（**风险评估矩阵**：可能性×影响→风险等级）
> 6. 降低风险的措施（**具体、可验证的缓解措施**）
> 7. 签署与记录
> 另含：DPO意见、结论与建议

**需求规定的测试案例预期** (`测试案例一：AI招聘筛选系统`):
> 预期输出：
> - 风险评估矩阵：5项风险，附可能性和影响评级
> - 具体缓解措施：公平性审计（每6个月）、解释功能的实现方案
> - DPO意见："有条件同意" + 三大前置条件
> - 建议6个月后全面复审

| 需求要求 | 实际产出 | 差距 |
|------|------|------|
| 7章完整DPIA草案 | 7/7章全文占位（每章63-67字，"LLM未配置，此处为占位内容"） | 🔴 **报告完全不可用** |
| 风险评估矩阵 | risk_matrix有2条（特殊类别推断风险=HIGH + 透明度风险=MEDIUM），在generation_basis_snapshot中有完整矩阵 | ⚠️ 中间数据有，但用户看不到（因章节占位） |
| 具体缓解措施 | mitigation_plan有2条（取消推断环节 + 上线解释功能），状态均为planned | ⚠️ 中间数据有，但用户看不到 |
| DPO意见 | dpo_decision_pack: "conditional_approval" + 3个前置条件 | ⚠️ 中间数据有 |
| 必要性与相称性分析 | necessity_findings: 识别出"浏览记录""互动行为"为过度收集项，建议数据最小化 | ⚠️ 中间数据有 |
| 一致性审查 | consistency_report: 10/10通过 | ⚠️ 中间数据有 |
| 最终可交付的.docx | docx=37KB，内容=7句占位文本 | 🔴 |

**业务的实质差距**：
dpia 是**最分裂的模块**——9个Agent流水线完整执行了，generation_basis_snapshot 253KB的中间数据证明了**所有合规推理都已正确完成**，但最终报告的7章正文全部是占位文本。用户拿到的是一份**空壳报告**，完全无法用于任何合规场景。

---

### 15.8 tia — TIA草案生成

**需求规定的预期产出** (`资源/欧盟/任务4/功能说明`):

> TIA草案，按EDPB六步法：
> 1. 了解您的传输
> 2. 识别所用传输工具（依据GDPR第46条 + EDPB 01/2020步骤2）
> 3. **评估目的地法律与实践**（依据Schrems II判决 + EDPB 01/2020步骤3，**TIA核心**）
> 4. 识别补充措施（技术性/合同性/组织性）
> 5. 实施步骤与意见
> 6. 定期复审
> 附加：**生成逻辑与风险提示**——特别是目的地国法律风险提示

**需求规定的测试案例预期** (`测试案例一：德国→美国SaaS`):
> 预期：明确美国FISA 702/CLOUD Act构成高风险 → 加密+本地密钥管理为核心补充措施 → 最终判断可进行（附条件） → 建议第三方安全审计

| 需求要求 | 实际产出 | 差距 |
|------|------|------|
| EDPB六步法完整结构 | 6章7179字符，结构符合六步法 | ✅ |
| 目的地国法律分析 | country_risk: 美国未获充分性认定, FISA 702/CLOUD Act/EO 12333均被识别和分析 | ✅ |
| 补充措施充分性评估 | measure_assessments有1条：端到端加密+欧盟密钥管理=充足 | ✅ |
| 最终结论 | risk_level=MEDIUM，"有条件地达到了欧盟基本同等的保护水平" | ⚠️ 降级逻辑合理但缺少量化支撑 |
| **生成逻辑与风险提示** | 有，但6处被注入 `【待核验：缺少法规依据】` | 🔴 工程标记泄漏到正式报告 |
| "推测"措辞 | 第28行：`【推测】基于数据出口方为控制者...` | ❌ 正式TIA报告不应出现推测性语言 |
| citation | footnote_map={}（空），6处"待核验"标记 | 🔴 Citation管道对[1]格式不兼容 |

**业务的实质差距**：
1. 分析质量在11个模块中属于上游，但**6处"待核验：缺少法规依据"标记破坏专业性**——这是发给监管机构的正式文件
2. "推测"措辞在正式TIA中不可接受
3. 降级逻辑（HIGH→MEDIUM）缺少量化加密强度的支撑

---

### 15.9 us_14117 — 14117行政令合规

**需求规定的预期产出** (`资源/美国/任务1/功能说明`):

> 《14117行政令风险评估结论报告》，格式PDF/HTML，内容包含：
> 1. **总体结论与传输可行性**：首页显著红/黄/绿标签
>    - 红灯：明确禁止的交易
>    - 黄灯：限制性交易，需实施安全措施
>    - 绿灯：低风险放行
> 2. **风险详情与分析**：
>    - **高风险实体清单**：列出所有"被涵盖人员"及判定依据
>    - **敏感数据分布**：以**表格和图表**展示各类敏感数据的存量/涉及人数/出境体量
>    - **风险匹配矩阵**：展示"哪些高风险实体"接收"哪些类别的敏感数据"
> 3. **合规措施建议与行动清单**：逐条安全措施+实施指引

**需求规定的测试案例预期** (`测试案例一：红灯/案例二：黄灯/案例三：绿灯`):
> 红灯案例(基因组数据→中国)预期：🚨红灯，列出华源生命为"被涵盖人员"，基因组数据超100人阈值
> 黄灯案例预期：🟡黄灯，列出具体的安全措施缺口

| 需求要求 | 实际产出 | 差距 |
|------|------|------|
| 首页红黄绿标签 | overall_traffic_light=YELLOW，traffic_light_result完整 | ✅ |
| **高风险实体清单** | risk_matrix有但仅1条，"covered_person_reason"长达200+字符但未以清单形式呈现 | 🔴 需求要求的是"列出所有实体"的表格，实际是单条混合文本 |
| **敏感数据分布（表格和图表）** | 缺失 — 24条rule_hits无数据分类统计 | 🔴 需求要求的可视化完全缺失 |
| **风险匹配矩阵** | 缺失 | 🔴 需求的核心分析工具缺失 |
| 安全措施缺口清单 | traffic_light_result.required_security_measures有9项，missing有21项 | ✅ 缺口清单完整 |
| 行动清单 | 章节3有1456字符的建议 | ⚠️ 有内容但为无格式文本 |
| 渲染文档 | **快照中 docx=0B（完全空文档）** | 🔴 需求要求的报告文件在快照中无法生成；当前已产出新 DOCX，待内容复验 |

**业务的实质差距**：
1. **docx完全失败**：用户拿不到报告
2. **核心分析工具缺失**：需求明确要求的"高风险实体清单表格"+"敏感数据分布图表"+"风险匹配矩阵"——这些是14117合规分析最核心的交付物——全部缺失
3. 正文虽有内容但全部挤压在3段无格式文本中，用户无法按实体/按数据类型/按风险等级快速定位

---

### 15.10 cpra — CPRA合规

**需求规定的预期产出** (`资源/美国/任务2/功能说明`):

> 《加州CPRA合规全景报告》
> 5章：执行摘要 → 企业适用性与范围 → 数据处理活动合规分析 → 消费者权利保障评估 → 敏感信息与第三方管理 → 行动清单与优先级

**需求规定的测试案例预期** (`测试案例一：电商TrendyGoods.com`):
> 预期：总体评级=部分缺失。3项核心发现：选择退出链接不合规、广告合作合同缺失CPRA义务、Cookie同意横幅有暗模式风险
> 各章有具体的合规分析和建议

| 需求要求 | 实际产出 | 差距 |
|------|------|------|
| 6章全景报告 | 6/6章全文占位（每章21-27字"LLM未配置，此处为占位内容"） | 🔴 **报告完全不可用** |
| 执行摘要 | 21字占位 | 🔴 |
| 数据处理合规分析 | 27字占位 | 🔴 |
| 消费者权利保障 | 26字占位 | 🔴 |
| 行动清单 | 25字占位 | 🔴 |
| gap_items（结构化数据） | 5条，覆盖4/10 domain，legal_basis精确到CPRA §编号 | ⚠️ 结构化层有数据，但用户看不到 |
| 3项核心发现 | 缺失 | 🔴 |

**业务的实质差距**：
与dpia同样的根因——LLM未配置导致6章全部占位。gap_items层有5条结构性数据（CPRA法律依据精确），但报告正文不可用。测试案例要求的"选择退出链接不合规""Cookie暗模式分析"等具体的基于自然语言的内容分析完全缺少。

---

### 15.11 cn_flow — 中国数据出境（美国视角）

**需求状态**：cn_flow 在需求文档中无独立的"功能说明与路径描述"文档，是代码层从 us_14117 衍生的模块（EO 14117 框架应用于中国方向）。其预期产出可参照 us_14117 的报告结构。

| 隐含预期 | 实际产出 | 差距 |
|------|------|------|
| 4章风险报告 | 4/4章全文占位（每章25-28字） | 🔴 |
| 风险项分析 | 1条risk_item（"存在敏感数据跨境流动"，HIGH） | 🔴 1条风险项承载全部分析 |
| 实体/数据分类 | 缺失 | 🔴 |

---

### 15.12 跨模块业务差距总表

| # | 模块 | 需求满足度 | 最关键的单一业务差距 |
|:---:|------|:---:|------|
| 1 | pipia | 🟢 85% | 结构化层落后于正文（22条facts零引用） |
| 2 | tia | 🟡 75% | 6处工程标记泄漏到正式报告 |
| 3 | assessment | 🟡 60% | 路径矛盾：自己判scc却生成了安全评估报告 |
| 4 | eu_scc | 🟡 55% | 6/8条发现无原文引用，报告从"条款审查"退化为"标注清单" |
| 5 | bcr | 🟡 50% | 11处模板变量泄漏，整改建议不可用 |
| 6 | diagnosis | 🟡 45% | **结论错误**（豁免 vs 应为标准合同），且无渲染文档 |
| 7 | review | 🔴 20% | 需求规定的6要素逐条审查报告完全缺失，只有聚合计数 |
| 8 | dpia | 🔴 15%（快照） | Agent/规则中间态已执行，但7/7章占位；当前仍需验证最终正文 |
| 9 | us_14117 | 🔴 10%（快照） | 快照 docx=0B；当前约38KB新产物已生成，实体清单/分布表/矩阵待复验 |
| 10 | cpra | 🔴 10% | 6/6章占位，用户拿到6句"LLM未配置" |
| 11 | cn_flow | 🔴 5% | 4/4章占位，1条risk_item承载全部分析 |

---

### 15.13 三层业务能力的系统性问题

需求文档规定的核心业务流程是：**用户输入 → 系统分析 → 生成专业报告**。但从实际产出看，系统在三层能力上都存在系统性问题：

```
L1 规则引擎层  → 大部分模块可用（diagnosis路径判定除外）
L2 结构化数据层 → 6/11模块存在字段空值或引用断链
L3 LLM叙述层   → 2026-08-07 快照中 3/11 模块因未启用/降级而失败；当前状态需重新运行确认
L4 条款审查层   → review模块产出形式完全不符合需求规定的6要素格式
```

**三个最紧急的业务修复优先级**：

| 优先级 | 修复项 | 影响模块 | 业务收益 |
|:---:|------|------|------|
| P0 | 启用LLM (`client.py:73` 改为 `_enabled=True`) | dpia, cpra, cn_flow | 3个模块报告从"全占位"变为"可用" |
| P0 | 修复 us_14117 DOCX 渲染 | us_14117 | 用户能拿到报告文件 |
| P0 | review 模块重建为条款级逐条审查 | review | 从"聚合计数"变为需求要求的"6要素逐条发现" |
| P1 | 修复 assessment 路径矛盾 | assessment | 避免给用户推荐错误合规路径 |
| P1 | 修正 diagnosis 路径判定逻辑 | diagnosis | 避免用户走错误路径 |
| P1 | 补充 eu_scc findings 的 original_text/suggested_text | eu_scc | 报告从"标注清单"升级为"条款审查" |



---

## 十六、知识库索引审查

> 数据来源：`storage/rag/` 下的 v2 legacy 索引、v3 分法域分层索引、`backend/common/rag/` 检索管线代码、各模块实际检索结果。

---

### 16.1 索引总体规模与结构

```
storage/rag/
├── regulation_index_v2.json          14.5 MB  3026条法规条款 (legacy)
└── v3/
    ├── legal_index_cn.jsonl          549  chunk, 28 source docs
    ├── legal_index_cn.vector.json    5.1 MB (sparse vector)
    ├── legal_index_eu.jsonl          897  chunk, 30 source docs
    ├── legal_index_eu.vector.json    2.9 MB
    ├── legal_index_us.jsonl          285  chunk, 11 source docs
    ├── legal_index_us.vector.json    0.8 MB
    ├── standard_clause_index_{cn,eu,us}.jsonl  (各3-5条)
    ├── template_index_{cn,eu,us}.jsonl         (各3-10条)
    ├── testcase_index_{cn,eu,us}.jsonl         (各3-5条)
    └── workflow_index_{cn,eu,us}.jsonl         (各4-7条)
```

v3 采用 **L1-L4 四层架构**：

| Layer | 名称 | 用途 | CN | EU | US |
|:---:|------|------|:---:|:---:|:---:|
| L1 | regulatory_evidence | 法规条文原文 | 549 | 897 | 285 |
| L2 | business_rule | 业务流程规则 | 7 | 4 | 7 |
| L3 | testcase | 测试案例上下文 | 5 | 4 | 3 |
| L4 | template | 报告模板槽位 | 10 | 4 | 3 |
| — | standard_clause | 标准条款参考 | 5 | 3 | 3 |

所有索引条目均有 **26 个统一字段**（chunk_id/source_id/title/content/layer/template_type/source_kind/module/jurisdiction/doc_type/authority_level/binding_force/allowed_usage/can_be_cited/can_enter_external_report/reference_ids/citation_anchor/scenario_tags/chunk_strategy/article_no/path/source_url/snapshot_path/keywords/structured_payload）。

所有 snapshot_path 引用的源文件 **全部存在**（0 缺失）。

---

### 16.2 EU 索引：🔴 94% 条目为噪音

EU 索引是三个法域中问题最严重的。

**数量分布**：

| 来源 | 类型 | chunk 数 | 内容 |
|------|:---:|:---:|------|
| GDPR (EU) 2016/679 | law | 52 | GDPR 正文 —— 仅有 52 条，覆盖约 13 个条款 |
| EDPB Recommendations 01/2020 | guide | 6 | SCC/TIA 核心指南 —— 仅 6 条 |
| EDPB BCR Guide v2 | guide | 30 | BCR 审查指南 |
| EDPB guidelines 2018 derogations | guide | 30 | 豁免指南 |
| EDPB guidelines territorial scope | guide | 30 | 地域范围指南 |
| EDPB guidelines codes of conduct transfers | guide | 30 | 行为准则指南 |
| ICO DPIA Template | template | 29 | DPIA 模板 |
| **18 份 CELEX 充分性认定决定 (2002-2023)** | regulation | **540** | **瑞士/加拿大/阿根廷/冰岛/乌拉圭/新西兰/以色列/日本/韩国/英国等国的欧盟充分性认定决定，每份盲切 30 段，article_no 全部为 "段落1" ~ "段落30"** |
| 3 份 JUST SCC 模板 | template | 90 | 标准合同条款草案模板 |
| 1 份 TIA 模板 | template | 30 | TIA 模板 |

**三个核心问题**：

| 问题 | 数据 | 影响 |
|------|------|------|
| **噪音率 94%** | 839/897 条目 article_no 为 "段落N"，是盲切结果 | 检索时大量返回 2002-2023 年的旧充分性认定决定，与 SCC 审查/DPIA/TIA/BCR 业务**完全无关** |
| **GDPR 覆盖严重不足** | 仅 52 条，仅约 13 个条款 | DPIA 需要大量 GDPR 原文支持（Art 5/6/9/13/14/24/25/28/30/32/35/36），检索池中几乎找不到 |
| **核心指南极度稀薄** | EDPB 01/2020 仅 6 条（Step 1, Step 3） | TIA 六步法的核心法律依据仅有 6 个片段可供检索 |

**根本原因**：18 份 CELEX 充分性认定 PDF 被盲目切割，每份默认切成 30 段，产生了 540 条噪音条目。这些原文的 authority_level 标记为 "medium"，binding_force 标记为 "binding"（因为 EU 充分性认定决定确实具有约束力），检索打分时与真正的 GDPR 条文混在一起竞争排名。

---

### 16.3 CN 索引：法律覆盖全面，但模块分配失衡且内容过短

**数量分布**：

| 来源 | 类型 | chunk 数 |
|------|:---:|:---:|
| 网络安全法 (2025修正) | law | 85 |
| 数据安全法 | law | 54 |
| 个人信息保护法 | law | 73 |
| 网络数据安全管理条例 | regulation | 65 |
| 数据出境安全评估办法 | regulation | 20 |
| 促进和规范数据跨境流动规定 | regulation | 25 (发布页11+全文页14) |
| 个人信息出境标准合同办法 | regulation | 9 |
| 个人信息出境认证办法 | regulation | 19 |
| 数据出境安全评估申报指南 (第三版) | guide | 8 |
| 标准合同备案指南 (第二版) | guide | 2 |
| 个人信息出境标准合同办法答记者问 | qa | 19 |
| 数据出境安全管理政策问答 (4月+5月) | qa | 6 |
| 技术标准/规范 (金融数据/个人信息安全/GB/T 43697等) | standard | 91 |
| 模板类 (标准合同/协议/自评估报告/PIPIA模板等) | template | 43 |
| 其他 (省级联系方式) | misc | 6 |

**核心问题**：

| 问题 | 数据 | 影响 |
|------|------|------|
| **检索结果高度重复** | assessment 模块检索到 98 条结果，其中 **73 条 (74.5%) 是同一部法律（个人信息保护法）的不同条款** | 检索偏向单一法律，其他 10 部法律仅各命中 1 次。多样性与覆盖率严重不足 |
| **chunk 过短** | 295/549 (53.7%) 条目 content < 100 字符 | 法律条款的单个句子被独立切块，缺少上下文，LLM 看到的是孤立的一句话而不是完整的条文逻辑链 |
| **模块配额失衡** | cn_diagnosis: 424 chunks (77.2%)，cn_assessment: 44 chunks (8.0%)，cn_review: 81 chunks (14.8%) | pipia 模块**在索引中无独立 partition**，其法规检索走的是 cn_assessment 的 44 条子集或跨模块检索。pipia 实际检索到的 `regulations=0`（在其 result.json 中法规数为 0） |
| **assessment 碎片化** | 仅 44 个 chunk，但散落在 7 个 sources 中 | 安全评估需要完整的法规体系支撑（8 章报告覆盖 5 部主要法律），44 个碎片远远不够 |

---

### 16.4 US 索引：CPRA 严重不足

**数量分布**：

| 来源 | 类型 | chunk 数 | 说明 |
|------|:---:|:---:|------|
| DOJ Rule implementing EO 14117 | regulation | 8 | EO14117 核心法规 —— 仅 8 条 |
| CA CPRA/CCPA | law | **7** | **整个加州隐私法仅有 7 个 chunk** |
| EU-U.S. DPF | regulation | 30 | 数据隐私框架全文 |
| FISA Section 702 | regulation | 30 | 外国情报监视法 |
| CLOUD Act | regulation | 30 | 云法案 |
| NIST Privacy Framework | regulation | 30 | NIST 隐私框架 |
| APEC Privacy Framework | regulation | 30 | APEC 隐私框架 |
| Digital Trade (USMCA) | regulation | 30 | 数字贸易章节 |
| FTC Act | regulation | 30 | FTC 法案 |
| EO 14086 增强 DPF 保障 | regulation | 30 | DPF 增强行政令 |
| DCPD 202200894 | regulation | 30 | 其他行政文件 |

**核心问题**：

| 问题 | 数据 | 影响 |
|------|------|------|
| **CPRA 近乎空白** | 仅 7 个 chunk 覆盖整部 CPRA/CCPA | cpra 模块需要全景检查 10 个 domain，但检索池中 CPRA 文本量不足以支持任何有意义的检索 |
| **EO14117 核心法规薄弱** | DOJ Rule 仅 8 个 chunk | us_14117 模块依赖 24 条 rule_hits 做判定，但核心法规索引中仅有 8 条文本碎片 |
| **大量regulation类文件是原始PDF转换** | FTC Act/FISA 702/CLOUD Act 等各 30 条 chunk，article_no 均为 "段落1"~"段落30" | 与 EU 同样的问题 —— 原始 PDF 被盲目切成固定数量段落，缺少法律感知的语义切分 |
| **模组分配集中** | us_14117: 278 chunks，us_cpra: **仅 7 chunks** | CPRA 模块在索引中几乎等于空集 |

---

### 16.5 检索链路的实际表现（逐模块对照）

| 模块 | 索引分配 | 实际检索结果数 | 引用注册数 | 脚注映射数 | 利用率 |
|------|:---:|:---:|:---:|:---:|:---:|
| assessment | cn_assessment: 44 chunks | `regulations=98` | citation_map: 10 | footnote_map: **0** | 10→0 (0%) |
| pipia | 无独立 partition | `regulations=0` | citation_map: 89 | footnote_map: 22 | 89→22 (24.7%) |
| dpia | eu_dpia: 13 chunks | `regulations=4` | citation_map: **0** | footnote_map: **0** | 4→0 (0%) |
| eu_scc | eu_scc: 854 chunks (750+ 噪音) | `regulations=0` | citation_map: 3 | footnote_map: 3 | 3→3 (100%) |
| bcr | eu_bcr: 15 chunks | `regulations=0` | citation_map: 2 | footnote_map: 2 | 2→2 (100%) |
| us_14117 | us_14117: 278 chunks | `regulations=0` | citation_map: **0** | footnote_map: **0** | — |
| cpra | us_cpra: **7 chunks** | `regulations=0` | citation_map: 3 | footnote_map: **0** | 3→0 (0%) |
| tia | eu_tia: 15 chunks | `regulations=0` | citation_map: 1 | footnote_map: 1 | 1→1 (100%) |

**关键发现**：

1. **只有 assessment 模块触发了检索**（`regulations=98`），其他 7 个模块的 `regulations` 全部为 0——说明大部分模块的法规不是在 pipeline 执行阶段临时检索的，而是通过 pre-built citation_map 预注册
2. **引用利用率极低**：assessment 检索了 98 条 → 只有 10 条被注册为 citation → 0 条映射到脚注。RAG 成本完全浪费
3. **dpia 检索 4 条但零注册**：4 条法规全部来自 GDPR 的 EU-LAW-001 段落4/5/6/7，引用注册 `assign_footnote_number()` 从未被触发（因为 LLM 写 `[1]` 而不是 `{{CIT-xxx}}`）

---

### 16.6 索引感知的质量问题

| 问题编号 | 问题 | 涉及索引 | 严重度 |
|:---:|------|:---:|:---:|
| IDX-1 | EU 索引 94% 条目为噪音 (839/897 段落盲切) | legal_index_eu | 🔴 P0 |
| IDX-2 | EU 索引 module 分配严重失衡 (854 scc : 13 dpia : 15 bcr : 15 tia) | legal_index_eu | 🔴 P0 |
| IDX-3 | US CPRA 索引仅 7 chunks (无法支撑全景合规检查) | legal_index_us | 🔴 P0 |
| IDX-4 | CN 索引 53.7% chunks < 100 字符 (过短，缺上下文) | legal_index_cn | 🟡 P1 |
| IDX-5 | CN 索引 pipia 模块无独立 partition | legal_index_cn | 🟡 P1 |
| IDX-6 | assessment 检索 98 条中 74.5% 为同一部法律 | 检索偏置 | 🟡 P1 |
| IDX-7 | 引用利用率: assessment 98→10→0，dpia 4→0→0 | citation 管线 | 🔴 P0 |
| IDX-8 | 18 份 CELEX 充分性认定 PDF 元数据未标注与模块的无关性 | 元数据 | 🟡 P1 |
| IDX-9 | GDPR 仅 52 chunks (应至少覆盖全部 99 条) | legal_index_eu | 🟡 P1 |
| IDX-10 | EO14117 DOJ Rule 仅 8 chunks (不足以支撑 24 条 rule_hit) | legal_index_us | 🟡 P1 |

---

### 16.7 修复优先级

| 优先级 | 修复项 | 影响 |
|:---:|------|------|
| P0 | EU 索引移除或降级 18 份 CELEX 噪音条目，或标记为 `authority_level=low` + `can_enter_external_report=False` | 减少检索噪音，让 GDPR/EDPB 01/2020 能排到前面 |
| P0 | 补全 US CPRA 索引——需要 CPRA/CCPA 全文的完整条款索引（至少 50+ chunks） | cpra 模块至少能检索到相关法律文本 |
| P0 | 补全 EU GDPR 索引——覆盖全部关键条款 (Art 5-9, 12-15, 24-25, 28, 30, 32-36, 44-49) | dpia/tia/bcr 模块有基本的法律索引可用 |
| P1 | CN 索引增加 pipia 独立 partition，将 assessment partition 从 44 扩到 150+ | pipia 和 assessment 都能检索到足够的法规依据 |
| P1 | 修复 chunk 策略——对 CN 索引中 < 100 字符的条目进行合并或上下文扩展 | 检索返回的文本片段有完整的法律推理上下文 |
| P1 | 修复 citation 管线——兼容 `[N]` 格式脚注（已在 12.中详述） | 检索→引用→脚注的端到端链路贯通 |

---

## 十七、索引修复结果（2026-08-10 执行验证）

> 执行方案：`status/todo/DataComplyFlow_知识库索引修复方案_20260810.md`
> 修复范围：`storage/rag/v3/` 全部 15 个子索引，CN/EU/US 三层法域

### 17.1 修复项与结果

| 优先级 | 修复项 | 修复前 | 修复后 | 状态 |
|:---:|------|------|------|:---:|
| P0-1 | EU 噪音（93.5% 盲切条目） | 897 条目，839 噪音 | **402 条目，0 噪音** | ✅ |
| P0-2 | CPRA 覆盖不足 | 12 条目 | **83 unique articles (90 条目)** | ✅ |
| P0-3 | GDPR 覆盖不足 | 13 条目 | **99 unique articles (396 条目跨4模块)** | ✅ |
| P1-1 | CN 短 chunk (<100字) 比例 | 50.7% | **11.6%** | ✅ |
| P1-2 | cn_pipia 独立分区 | 不存在 | **71 条目** | ✅ |
| P1-3 | cn_assessment 扩展 | 44 条目 | **254 条目** | ✅ |
| P1-4 | US 噪音移除 | 270/299 盲切噪音 | **0 噪音** | ✅ |
| P1-5/P1-6 | source diversity (source_cap=3) | 无限制，单法集中度高 | **source_cap=3 已实现** | ✅ |

### 17.2 修复后索引概况

```
Index                    Entries    Size
─────────────────────────────────────────
legal_index_cn              680    7,508 KB
legal_index_eu              402    3,581 KB
legal_index_us              197    1,382 KB
standard_clause_index_cn     51       30 KB
standard_clause_index_eu     16        9 KB
standard_clause_index_us     16       10 KB
template_index_cn            37       49 KB
template_index_eu             8        8 KB
template_index_us             4        6 KB
testcase_index_cn            18       23 KB
testcase_index_eu             9        9 KB
testcase_index_us             5        7 KB
workflow_index_cn            20       39 KB
workflow_index_eu            10       16 KB
workflow_index_us            36       51 KB
─────────────────────────────────────────
TOTAL (15 indexes)       1,509    12,738 KB
```

### 17.3 模块级分布

```
EU: eu_scc=101, eu_bcr=101, eu_dpia=99, eu_tia=101
US: us_cpra=90, us_vendor_review=90, us_14117=17（索引实际 module 字段）
CN: cn_diagnosis=289, cn_assessment=254, cn_pipia=71, cn_review=66
```

### 17.4 代码修改清单

| 文件 | 修改内容 |
|------|------|
| `resources/legal/catalog/sources.csv` | 28 EU + 9 US reference 条目 module 清空，CN/US 模块分配调整 |
| `resources/legal/catalog/module_catalog.v1.json` | 新增 `cn_pipia` 模块定义 |
| `resources/legal/registry/regulation_articles.jsonl` | GDPR 99 条目 (从 PDF 提取)，CPRA 拆分为 90 sub-section 条目 |
| `backend/common/knowledge/registry.py` | path=reference 早退，pipia support |
| `backend/common/knowledge/builders_v2.py` | CN multi-module loop，EU/US fallback 移除，短 chunk 合并函数，source_row 变量修复 |
| `backend/common/rag/orchestrator.py` | cn_pipia 路由 + 检索方法，source_cap=3 diversity 机制 |

---

## 十八、2026-08-10 阶段性模块产物交叉验核

> 验核时间：2026-08-10 13:16-13:18（当时各模块目录中的最新任务，不代表当前最新运行）
> 验核方法：取每个模块 outputs/ 下最新 UUID 任务目录，逐项比对审计报告 40 个问题
> 验核对象：assessment、pipia、dpia、us_14117、bcr、eu_scc、tia、cpra（当时仅 8 模块有 `outputs/` 产物）。本节不是“全模块同批重跑”：缺少 diagnosis、review、cn_flow 三个模块的同批产物，且这批结果已被 08-12/13 的部分实现和专项验收进一步更新。

### 18.1 交叉验核总表

| 审计编号 | 审计描述 | 2026-08-07 快照 | 2026-08-10 实际 | 状态 |
|---------|---------|----------------|----------------|------|
| **R1** | us_14117 DOCX 0B | ❌ 0 字节 | ✅ 38 KB, 有效 DOCX | ✅ 已修复 |
| **R2** | assessment footnote_map 空 | ❌ 0 键 | ⚠️ 14 items → 3 键 (21%) | 🔴 仍存在 |
| **R3** | pipia CIT 标记截断 | ❌ 未闭合 | ⚠️ 无 CIT 标记但整个模块损坏 | 🔴 恶化 |
| **R4** | dpia 7/7 章节占位 | ❌ 全占位 | ✅ 99 行, 2612 字符, 0 占位 | ✅ 已修复 |
| **R5** | cpra 3/4 章节占位 | ❌ 占位 | ✅ 61 行, 1674 字符, 0 占位 | ✅ 已修复 |
| **R6** | cn_flow 3/5 章节占位 | ❌ 占位 | ✅ 已清除（委托 us_14117） | ✅ 已修复 |
| **R7** | eu_scc Clause 截断 | ❌ 截断 | ⚠️ 94 行 6043 字符但 3 超长行 | 🟡 部分改善 |
| **R8** | us_14117 markdown 格式 | ❌ 格式坍塌 | ⚠️ 15 行 854 字符, 1 超长行 | 🟡 仍存在 |
| **F1** | dpia Agent 未执行 | ❌ 声称未执行 | ✅ trace_manifest 28 事件 | ✅ 审计误判 |
| **F2** | BCR 模板变量泄露 | ❌ [Company Name] | ✅ 清除 | ✅ 已修复 |
| **F3** | CPRA 脚注丢失 | ❌ 0 脚注 | ✅ 5/6 脚注 (83%) | ✅ 已修复 |
| **B1** | DPIA 占位 + 脚注 | ❌ 双重故障 | ⚠️ 占位清除但 8/99 脚注 | 🟡 脚注仍弱 |
| **C1** | DPIA Agent 链断裂 | 审计称 0 agent | ✅ 实际执行正常 | ✅ 审计误判 |
| **C2** | BCR 规则引擎失效 | ❌ 失效 | ✅ 99 items 解析正常 | ✅ 已修复 |
| **C-COMMON-1** | LLM 执行防护缺失 | ❌ 无 Guard | ❌ 代码无 ExecutionGuard | 🔴 未实现 |
| **C-COMMON-2** | CIT 标记后处理缺失 | ❌ 无后处理 | ❌ 代码无 CIT postprocessor | 🟡 未实现 |
| **C-COMMON-3** | evidence_chain 字段空 | ❌ 全空 | ❌ assessment 5/5, dpia 12/12, us_14117 5/5 全空 | 🔴 仍存在 |
| **C-COMMON-4** | 工程标注泄露 | ❌ 泄露 | ✅ assessment/dpia/us_14117 均清除 | ✅ 已修复 |
| **C-COMMON-5** | 虚假 COMPLETED 状态 | ❌ 二元枚举 | ❌ 仍未扩展（COMPLETED/FAILED） | 🟡 未实现 |
| **C-COMMON-6** | supporting_material_refs 空 | ❌ 全空 | ⚠️ 字段定义存在但填充未验证 | 🟡 未深入验证 |
| **C-COMMON-7** | document_ir 段落空 | ❌ 空 | ⚠️ assessment/dpia 均为 0 段落 | 🟡 仍空 |

### 18.2 跨模块脚注覆盖率排行（2026-08-10 阶段产物）

```
us_14117  ████████████████████ 100% (17/17)
eu_scc    ████████████████████ 100% (1/1)
tia       ████████████████████ 100% (4/4)   ← 审计报告后修复
cpra      ████████████████░░░░  83% (5/6)    ← 审计报告后修复
assessment ████░░░░░░░░░░░░░░░░  21% (3/14)
dpia      ██░░░░░░░░░░░░░░░░░░░   8% (8/99)
pipia     ░░░░░░░░░░░░░░░░░░░░░   0% (0/72)   ← 整个模块已损坏
bcr       ░░░░░░░░░░░░░░░░░░░░░   0% (0/99)
```

### 18.3 跨模块 Markdown 质量快照

| 模块 | 行数 | 字符数 | 占位符 | 超长行 | 状态 |
|------|------|--------|--------|--------|------|
| assessment | 79 | 3,226 | 0 | 0 | ✅ 正常 |
| dpia | 99 | 2,612 | 0 | 0 | ✅ 正常 |
| us_14117 | 15 | 854 | 0 | 1（整篇为 1 行） | 🔴 格式坍塌 |
| pipia | 41 | 500 | 14（"LLM未配置，此处为占位内容"） | 0 | 🔴 LLM 未启用 |
| bcr | 45 | 377 | 2 | 0 | 🔴 内容极度稀疏 |
| eu_scc | 94 | 6,043 | 0 | 3 | 🟡 格式问题 |
| tia | 94 | 1,303 | 0 | 0 | ✅ 正常 |
| cpra | 61 | 1,674 | 0 | 0 | ✅ 正常 |

### 18.4 evidence_chain 三字段填充率（C-COMMON-3 详细）

| 模块 | evidence 条目 | legal_basis 空 | document_refs 空 | rag_query_used 空 | 全空率 |
|------|-------------|---------------|-----------------|-------------------|--------|
| assessment | 5 | 5 (100%) | 5 (100%) | 5 (100%) | **100%** |
| dpia | 12 | 12 (100%) | 12 (100%) | 12 (100%) | **100%** |
| us_14117 | 5 | 5 (100%) | 5 (100%) | 5 (100%) | **100%** |

> 三个核心模块的 evidence_chain 中 `legal_basis`、`document_refs`、`rag_query_used` 三项字段均为 100% 空值。这意味着证据链的"法律依据溯源"和"文档引用"功能完全未生效。

### 18.5 PIPIA 专项：从 CIT 截断到 LLM 未启动

审计报告（2026-08-07）将 pipia 问题定位为 CIT 标记截断。2026-08-10 该次运行结果：

```markdown
# AsyncPIPIA PIPIA 报告草案

## 处理者与出境活动基础信息
（处理者与出境活动基础信息：LLM未配置，此处为占位内容）

## 个人信息出境处理活动说明
（个人信息出境处理活动说明：LLM未配置，此处为占位内容）
...
（共 7 个章节全部为占位文本）
```

**根因分析**：
- 后端代码有完整的 LLMClient 注入链路（`backend/domains/cn/pipia/service.py`）
- Router 接口有 `Depends(require_healthy_llm)` 防护
- 运行时 LLM 健康检查失败 → 所有章节降级为占位文本
- 结果：72 个引用项全未注册脚注，500 字符占位输出

### 18.6 当时的验核结论及当前更正

**以下是 2026-08-10 当时的阶段统计，不是 2026-08-13 当前完成率**。40 个问题中，
- **8 个已修复**（R1/R4/R5/R6/F2/F3/C2/C-COMMON-4）
- **2 个为审计误判**（F1/C1：dpia Agent 实际正常执行）
- **6 个部分改善但仍存在问题**（R2/R7/R8/B1/C-COMMON-6/C-COMMON-7）
- **5 个明确未修复**（C-COMMON-1/C-COMMON-2/C-COMMON-3/C-COMMON-5 代码级，R3 pipia 恶化）
- **1 个恶化**（R3 pipia：从 CIT 截断恶化为整个模块 LLM 无法启动）

这些数量不能继续累加为当前“已修复/未修复”总数：PIPIA 后续已有三共享案例确定性浏览器闭环；BCR 虽曾清除旧占位符，但三格式专业排版仍未修；区域知识库新增了独立索引；其余模块尚未在 task065 下完成同一基线的全链路复验。

**2026-08-10 当时的优先修复建议**（保留作历史追溯）：
1. 🔴 **C-COMMON-3 evidence_chain**：三个核心字段 100% 空值，影响所有模块的证据溯源能力
2. 🔴 **pipia LLM 健康检查**：整个模块无法生成有效输出，需要排查 LLM API 配置或降级策略
3. 🔴 **脚注分配断层**：assessment (21%)、dpia (8%)、BCR (0%) 的 citation_map 脚注覆盖率远低于 us_14117 (100%)/tia (100%)
4. 🟡 **us_14117 格式坍塌**：整篇报告为 1 行，需要修复 markdown 渲染的换行逻辑
5. 🟡 **C-COMMON-1 LLM 执行防护**：无降级防护机制，LLM 失败时静默输出占位文本

---

## 十九、2026-08-13 当前结论

### 19.1 已有充分证据确认的进展

1. `cn_flow` 已改为兼容适配并委托 `us_14117`，旧独立重复流水线不再代表当前实现。
2. 共享 Scenario 已形成 22 条、10 个独立业务模块的事实基线；`cn_flow` 作为第 11 个注册模块复用 `us_14117`。CLI/前端一致性门禁当前登记为 26 CLI cases、603 leaf checks、28 developer cases。
3. Seed 50 个原始 DOCX 已完成来源保真抽取和模块身份裁决，但 40 条被关键事实门禁拒绝、10 条为能力 gap，尚无一条可冒充已接入 Gold 的 Level B 案例。
4. PIPIA 三条共享场景已完成确定性本地浏览器链路验收，覆盖上传、HTTP、异步任务、SSE、报告、引用和 PDF canvas。
5. `resources/new` 已完成分层迁移并删除；区域知识库当前工作区已建立 51 条 registry、49 条 PDF 绑定和 1,035 条国际索引，并验证不会污染默认 CN/EU/US 模块池。
6. Review/SCC 的历史失败状态残留已有针对性修复，历史 FAIL 卡片不能再直接解释为当前任务仍失败。

### 19.2 当前仍不能宣称完成的事项

1. **当前 HEAD 的全模块同基线验收未完成**：已有 2026-08-11 的 11 模块 CLI/LLM 全量回归记录，但尚无覆盖当前代码版本、同一案例事实、真实 HTTP/SSE/浏览器/产物的统一验收包。
2. **生产模型报告质量未完成**：确定性测试 LLM 只证明链路，不证明真实模型内容的法律正确性、重复率、事实忠实度或专业表达。
3. **BCR 三格式排版未修复**：task067 仅完成 T00 基线冻结；DocumentIR v4、原生 DOCX/PDF renderer、网页结构化阅读和视觉门禁均未实施。
4. **区域数据仍有缺口**：VN 无结构化条文；JP-LAW-009、KR-GUIDE-006 缺 PDF；两份冗余 PDF 无 source 归属；JP/KR 部分 title 与 PDF 身份需法律专家签署；国际 chunk 的业务 `module` 主字段仍为空。
5. **Seed 不是 Gold**：50 条 input extraction 没有 `expected.json`，没有接入 runner，也没有法律专家确认，不能计入业务准确率。
6. **远程部署未执行**：本文所有后续结果均为本地代码、测试或验收证据。

### 19.3 本文的正确使用方式

- 查历史缺陷：读取第一至第十八章，并以对应文件日期为准。
- 查当前状态：优先读取开头“当前状态总览”和本章。
- 判定某项是否完成：必须同时存在代码/提交、可重复测试、真实运行产物和 `status/check/` 验收证据；todo 方案、静态计数或单个文件存在均不足以判定完成。
- 后续更新：新增事实应追加日期、Git 基线、运行 ID、案例 ID、测试命令和证据路径，不再覆盖或删除历史基线。
