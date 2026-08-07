# resources/new 处置方案补遗：RAG 链路缺口

> 文档性质：对 `DataComplyFlow_resources_new完整处置方案_20260807.md` 的强制补充
> 编制日期：2026-08-07
> 触发原因：以 `status/view/DataComplyFlow_RAG与知识库系统详解_20260807.md` 交叉核对处置方案，发现 5 个会导致「文件搬到位但检索链路无感」的静默失败缺口
> 核对方式：逐条回读代码，不采信文档自述

---

## 〇、结论

处置方案的**文件归位部分成立**，但**「新加坡 6 个 PDF → 影子索引」这一步按现状不可执行**。

原因不是工作量，而是链路断点：检索路径从来不读 `resources/legal/sources/*/`，它读 `regulation_articles.jsonl`。把 PDF 放进 `sources/sg/` 之后，检索侧完全无感——不会报错，只会永远召回 0 条。这是最危险的一类失败：门禁全绿，功能不存在。

因此本补遗做两件事：

1. 把 5 个缺口写成显式前置条件，缺一个就不允许声称「SG 已入库」；
2. 把处置方案的执行拆成 **A 组（无阻塞，立即可做）** 和 **B 组（需代码改动，须单独决策）**。

---

## 一、缺口清单（全部经代码核对）

### G-1 · PDF 不是法律知识的入口，`regulation_articles.jsonl` 才是

**代码证据**

```
backend/common/knowledge/builders_v2.py:15    NORMALIZED_JSONL = regulation_articles_jsonl_path()
backend/common/knowledge/paths.py:32-33       REGISTRY_DIR / "regulation_articles.jsonl"
backend/core/resource_paths.py:11             KNOWLEDGE_ROOT = PROJECT_ROOT / "resources" / "legal"
```

`build_legal_chunks_cn/eu/us()` 全部从 `resources/legal/registry/regulation_articles.jsonl` 逐行读条文，**没有任何一个 builder 打开 PDF**。

**处置方案的问题**

方案写「新加坡 6 个 PDF → `resources/legal/sources/sg/`」，止步于文件归位。但归位后：

- 不会进入 `build_chunk_sets()`
- 不会生成向量
- 不会被 orchestrator 检索到
- 不报错

**必须补的步骤**

```
SG 6 个 PDF
  → 文本抽取（PDF → raw_text）
  → 条款切分（Part / Section / Subsection 结构）
  → 逐条写入 regulation_articles.jsonl（新增 sg 行）
  → sources.csv 登记 source_id
  → 删除 source_registry.v1.json 缓存
  → 重建索引
```

缺少「PDF → JSONL 条文行」这一环，SG 入库为空操作。

---

### G-2 · `INDEX_NAMES` 是 15 个硬编码常量，不存在任何 `*_sg`

**代码证据**

```
backend/common/rag/orchestrator.py:32-48
INDEX_NAMES = (
    "legal_index_cn", "workflow_index_cn", "standard_clause_index_cn",
    "template_index_cn", "testcase_index_cn",
    "legal_index_eu", ... (5)
    "legal_index_us", ... (5)
)   # 共 15，仅 cn / eu / us
```

**处置方案的问题**

方案写「构建版本化 `legal_index_sg` 影子索引」。但 `legal_index_sg` 不在 `INDEX_NAMES` 里，orchestrator 的 `_ensure_multi_indexes()` 只遍历这 15 个名字，一个不在元组里的索引不会被构建、不会被检索、也不会被版本检查。

**另一个连带风险**

`orchestrator.py:447` 的 `_is_index_current()` 一旦任一索引不匹配就**重建全部 15 个**。往 `INDEX_NAMES` 加第 16 个名字，会触发现有 CN/EU/US 全量重建——这就要求 Phase 4 的「旧索引等价性验证」必须在加名字之前完成，而不是之后。

**必须补的步骤**

- 要么扩展 `INDEX_NAMES` + 补 `build_legal_chunks_sg()`，并先做全量等价性快照；
- 要么走独立影子机制（不进 `INDEX_NAMES`，单独构建目录 + 单独检索入口），生产别名切换时再并入。

两条路都是**代码改动**，不属于「资料处置」范畴。

---

### G-3 · `ChineseLegalChunker` 对所有法域无条件生效

**代码证据**

```
backend/common/knowledge/ingestion_pipeline.py:101-103
source_id = f"CN-{doc_type.upper()}-{doc.id:03d}" if jurisdiction == "cn" \
            else f"{jurisdiction.upper()}-{doc_type.upper()}-{doc.id:03d}"
chunker = ChineseLegalChunker(source_id=source_id, title=parsed.title)   # ← 无分支
legal_chunks = chunker.chunk(parsed.raw_text)
```

`source_id` 前缀按法域切换了，**分块器没有切换**。

**处置方案的问题**

新加坡 PDPA 的结构是 `Part I / Section 13 / Subsection (a)`，越南是 `Chương / Điều`，日本是 `第○条`，韩国是 `제○조`。`ChineseLegalChunker` 匹配的是 `章 / 节 / 条 / 款 / 项`。

对 SG 英文原文运行它，结果不是抛异常，而是**整篇文本落进一个巨型 chunk 或产生零条**——`citation_anchor` 和 `article_no` 全空，引用定位彻底失效。

这正是 475 行主方案 R8「OCR/多语言分块静默丢条款」预警的具体落点，处置方案没有把它写成阻塞条件。

**必须补的步骤**

`ChineseLegalChunker` 参数化为 `LegalStructureChunker(strategy=...)`，或按 `jurisdiction` 选策略。**在此之前，任何非 CN/EU/US 文档不得进入 IngestionPipeline。**

---

### G-4 · `Literal["cn","eu","us"]` 类型闸门会直接拒绝 sg

**代码证据**

```
backend/core/resource_paths.py:20   def report_template_path(jurisdiction: Literal["cn","eu","us"], ...)
backend/core/resource_paths.py:29   def rule_resource_path(jurisdiction: Literal["cn","eu","us"], ...)
```

新增法域会在类型层被卡住。这条是**好事**——它是现存的正确防护，说明代码对「只支持三法域」是自觉的。但它同时证明：新法域不是配数据就能上，是要改契约的。

**处置方案的问题**

方案把 SG 归入「Phase 4，5-7 天」。实际上光是打开这些类型闸门 + 补 SG 的 template/rule 资源，就不是资料处置的工作量。

---

### G-5 · `testcase_index_*` 确实存在，30 个规范化案例有泄漏入口

**代码证据**

```
backend/common/knowledge/builders_v2.py:461    def build_testcase_chunks_cn()
backend/common/knowledge/builders_v2.py:848    def build_testcase_chunks_eu()
backend/common/knowledge/builders_v2.py:1260   def build_testcase_chunks_us()
```

`testcase_index_cn/eu/us` 是 15 个生产索引中的 3 个，当前数据源是 `builders_v2.py` 里的硬编码用例。

**处置方案的问题**

方案把 30 个规范化种子案例放进 `benchmarks/datasets/seed-cases-v1/`，物理位置是对的。但方案只在文字上说「不进入 RAG」，**没有可执行的守卫**。

只要后续有人为了「提升 few-shot 效果」把 seed case 内容搬进 `build_testcase_chunks_cn()`，Gold 答案就进了生产检索索引——评测从此自证，且没有任何门禁会发现。

**必须补的步骤**

新增 `scripts/check_benchmark_leakage.py`：把 `benchmarks/datasets/seed-cases-v1/**` 的 `expected` 正文做指纹，扫 `storage/rag/v3/testcase_index_*.jsonl` 与 `builders_v2.py` 的 testcase 函数体，命中即 CI 失败。

这是主方案 R3 的具体实现，属于 A 组（不需要动 RAG 架构）。

---

### G-6 · RAG 文档自身的路径已漂移（文档缺陷，非代码缺陷）

`status/view/DataComplyFlow_RAG与知识库系统详解_20260807.md` 有 3 处写作 `resources/knowledge/catalog/…` 与 `resources/knowledge/registry/…`（第 116、197、795、800 行附近）。

实际路径是 `resources/legal/catalog/` 与 `resources/legal/registry/`，由 `backend/core/resource_paths.py:11` 的 `KNOWLEDGE_ROOT = resources/legal` 决定。

按此文档去找 `sources.csv` 会找不到文件。需要修正 RAG 文档，避免后续实施照抄错误路径。

---

### G-7 · `sources.csv` 改动后必须手工失效缓存，否则修改不生效

**代码证据**

```
backend/common/knowledge/registry.py:242-248
if REGISTRY_PATH.exists():
    raw = json.loads(REGISTRY_PATH.read_text(...))     # ← 优先读 JSON 缓存
    ...
entries = build_source_registry_from_sources_csv()      # ← 仅当 JSON 不存在才读 CSV
```

**处置方案的问题**

方案写「10 个目录索引 → 提取官方 URL → 整合到 `sources.csv`」，但没写下一步：`source_registry.v1.json`（102 KB，已存在）会继续被优先读取，**新写入 CSV 的行不会生效**。

**必须补的步骤**

任何 `sources.csv` 写入操作后，强制执行：

```bash
rm resources/legal/registry/source_registry.v1.json
```

并把这一步写进脚本，不依赖人记得。

---

## 二、执行分组（据上述缺口重排）

### A 组 · 无阻塞，立即执行

| 编号 | 工作 | 涉及文件 | 是否需代码改动 |
|---|---|---|:---:|
| A1 | 91 个 Reference 库重复副本按 SHA-256 核验后归档/删除 | `resources/new/**` | 否 |
| A2 | 6 个 `.DS_Store` + 1 个 Office 临时文件删除 | `resources/new/**` | 否 |
| A3 | 3 篇 Benchmark 论文 → `resources/research/benchmarks/` | 文件移动 | 否 |
| A4 | 1 份实务手册 + 2 份 GB/T → `resources/manuals/`、`resources/standards/` | 文件移动 | 否 |
| A5 | 10 个目录索引提取官方 URL → `sources.csv` **+ 强制删缓存（G-7）** | `sources.csv` | 否 |
| A6 | 30 个无冲突种子案例规范化为 JSON | `benchmarks/datasets/seed-cases-v1/` | 否 |
| A7 | 20 个冲突案例隔离到 `quarantined/` + 冲突登记 | 同上 | 否 |
| A8 | **新增泄漏门禁 `check_benchmark_leakage.py`（G-5）** | `scripts/` | 新增脚本 |
| A9 | **修正 RAG 文档 3 处路径漂移（G-6）** | `status/view/…md` | 否 |
| A10 | 45 个待晋级 PDF 保持隔离 + 候选清单登记 | `resources/new/` | 否 |

### B 组 · 被 G-1/G-2/G-3/G-4 阻塞，须单独决策

| 编号 | 工作 | 阻塞项 | 前置条件 |
|---|---|---|---|
| B1 | `ChineseLegalChunker` 参数化为多法域策略 | G-3 | 现有 CN/EU/US 分块等价性测试 |
| B2 | `INDEX_NAMES` 扩展机制 / 独立影子索引通道 | G-2 | 15 索引全量等价性快照 |
| B3 | PDF → `regulation_articles.jsonl` 条文抽取管线 | G-1 | B1 完成 |
| B4 | `Literal["cn","eu","us"]` 契约扩展 | G-4 | 产品确认 SG 进 v1.0 范围 |
| B5 | SG 6 个 PDF 实际入库 + 影子索引评测 | B1–B4 全部 | 法律复核签字 |

**B 组不是「资料处置」，是 RAG 架构改造。** 建议从本次处置方案中剥离，单独立项。

---

## 三、对处置方案的三处修订

### 修订 1 · SG 从「Phase 4 交付项」降为「B 组待立项」

原文：

> 新加坡 6 个 → Phase 4 影子试点（完整解析、评测、回滚演练），5-7 天

改为：

> 新加坡 6 个 → 保持隔离。入库前置条件为 B1–B4 四项代码改动，需单独立项评估。
> 本次处置只交付：SG 6 个 PDF 的 manifest 登记 + 官方来源 URL 登记 + 候选状态标记。

### 修订 2 · v0.2 交付定义去掉「新法域」

原定义含「1 个新法域影子试点」。据 G-1~G-4，此项在当前代码基线上不可达。

v0.2 修订为：

```
219 份资料全部有明确去向
+ 重复与噪声清零
+ 30 个种子案例可机器执行
+ 20 个冲突案例显式隔离且登记
+ Gold 泄漏门禁上线
+ 官方来源 URL 进入 sources.csv 且缓存已失效
+ RAG 文档路径修正
——— 不含任何新法域生产能力 ———
```

### 修订 3 · 新增两条硬性禁令

1. **禁止**在 B1 完成前让任何非 CN/EU/US 文档进入 `IngestionPipeline`（G-3 会静默产出空 chunk）。
2. **禁止**任何 `sources.csv` 写入操作不伴随 `source_registry.v1.json` 删除（G-7 会静默丢弃修改）。

---

## 四、验证命令

```bash
# G-1 确认 builder 不读 PDF
grep -rn "\.pdf" backend/common/knowledge/builders_v2.py    # 预期：无输出

# G-2 确认无 sg 索引
grep -n "_sg" backend/common/rag/orchestrator.py            # 预期：无输出

# G-3 确认分块器无分支
sed -n '100,104p' backend/common/knowledge/ingestion_pipeline.py

# G-5 泄漏门禁（A8 交付后）
uv run --frozen python scripts/check_benchmark_leakage.py

# G-7 缓存失效验证
ls -la resources/legal/registry/source_registry.v1.json     # sources.csv 改动后应不存在
```

---

## 附录 · 核对留痕

| 断言 | 证据位置 | 核对结果 |
|---|---|---|
| KNOWLEDGE_ROOT 指向 `resources/legal` | `backend/core/resource_paths.py:11` | 确认 |
| builders 读 JSONL 不读 PDF | `backend/common/knowledge/builders_v2.py:15` | 确认 |
| INDEX_NAMES 为 15 且无 sg | `backend/common/rag/orchestrator.py:32-48` | 确认 |
| 任一索引失效触发全量重建 | `backend/common/rag/orchestrator.py:447` | 确认 |
| ChineseLegalChunker 无法域分支 | `backend/common/knowledge/ingestion_pipeline.py:102` | 确认 |
| testcase_index 三个 builder 存在 | `builders_v2.py:461 / 848 / 1260` | 确认 |
| source_registry JSON 缓存优先 | `backend/common/knowledge/registry.py:242-248` | 确认 |
| Literal 类型限制三法域 | `backend/core/resource_paths.py:20, 29` | 确认 |

本补遗只做仓库层面的代码事实核对，未对任何法律文件的效力、版本或授权范围作出判断。
