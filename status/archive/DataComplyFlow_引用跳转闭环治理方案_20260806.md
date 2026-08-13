# DataComplyFlow 引用跳转闭环治理方案

- 文档日期：2026-08-06
- 当前复核日期：2026-08-08
- 当前代码基线：`7182378`
- 问题来源：`status/CURRENT_DataComplyFlow_全功能运行验证与问题汇报_20260805.md` 第 8.f 节「引用跳转」
- 现行契约：`docs/standards/DataComplyFlow_引用跳转与CitationMap契约.md`
- 结论定位：这不是一个「跳转成功率低」的问题，而是**三条互不相通的引用链路同时存在**，加上**知识库条文抽取质量不足**，共同导致正文与 CitationMap 断链、条文级跳转覆盖率低。

> 实施说明：本文前半部分保留 2026-08-06 的原始诊断。当前执行时跳过已经完成的 RC-2、RC-3、CN-REG-004 重建和重复键清理；剩余工作以本文第 7 节的更新状态和 `DataComplyFlow_引用跳转机理详解_代码流程追踪_20260808.md` 第 〇 节为准。

## 0. 当前执行清单

| 顺序 | 工作 | 状态 | 验收要求 |
|---:|---|---|---|
| 1 | Marker 正则和 Citation ID 单一来源 | 已完成 | 正则与注册测试持续通过 |
| 2 | Citation API 禁止读取期合成、禁止写盘 | 已完成 | API 纯读取测试持续通过 |
| 3 | CN-REG-004 正式条文重建 | 已完成 | 第 1/13/20 条可查，第 21 条不可查 |
| 4 | 知识库重复键清理 | 已完成 | 完整性门禁重复键为 0 |
| 5 | URL、引用粒度和法规状态元数据统一 | 实施中 | 后端契约、API、前端类型一致 |
| 6 | 生成期只保留一种最终引用形态 | 待实施 | 最终报告只出现 `[n]`，旧入口零生产调用 |
| 7 | 前端路径 A/B 和失败状态闭环 | 待实施 | 组件测试覆盖成功与失败分支 |
| 8 | 本地浏览器真实点击验收 | 待实施 | Playwright、截图、网络记录齐全 |

实施期间不执行远端部署；全部本地验收完成后由用户决定是否部署。

---

## 1. 结论先行

验收报告描述的三个现象——正文写「（本报告未引用法规依据索引）」、citation_map 同时有 7 条、正文提到三部法律却标「待核验：缺少法规依据」——**不是三个 bug，而是同一条断链在三个位置的投影**。

断链链条：

```text
LLM 降级 / marker 正则不匹配
  → 正文没有任何 [n] 脚注
    → registry.assign_footnote_number 从未被调用
      → _global_numbering 为空
        → get_footnote_map() 返回 {}
          ├─ build_citation_map_section() → "（本报告未引用法规依据索引）"   ← 现象 1
          ├─ _write_citation_map_json() → footnote_map={} 落盘
          └─ apply_citation_policy 找不到有效【依据：】→ 追加「待核验：缺少法规依据」 ← 现象 3
            → API get_report_citations 发现 footnote_map 为空
              → 扫 trace 检索命中，凭空合成编号 1..N 并回写磁盘              ← 现象 2
```

也就是说：**那 7 条引用不是正文引用，是 API 在读取时用检索命中合成出来的**。它们和正文没有任何对应关系，编号 1..7 也不是正文脚注号。这是最需要先修的一点——它让「引用映射有 7 条」这个观察本身失去意义，也让磁盘上的 citation_map.json 不再是事实基线。

跨模块抽样进一步说明问题不是全局一致的，而是**分模块的三种不同病灶**：

| 模块 / 任务 | footnote_map | all_items | can_jump | source_url | 主要 failure_reason | 病灶类型 |
|---|---|---|---|---|---|---|
| `dpia/ffe5867e` | 4 | 4 | 4 | 0 | — | 健康（唯一 100% 条文级） |
| `pipia/7995b079` | 574 | 574 | 476 | 0 | not_unique 28 / missing 70 | 基本健康，受重复条文拖累 |
| `assessment/dc9b1db8` | **0** | 11 | 2 | 0 | not_found 8 / not_unique 1 | **A 类：脚注链断裂** |
| `cpra/a0dc677f` | **0** | 3 | 0 | 0 | not_found 3 | A 类 |
| `tia/7746ef56` | **0** | 2 | 0 | 0 | not_found 2 | A 类 |
| `cn_flow/7f327561` | 32 | 32 | 0 | 0 | **missing 32** | **B 类：全部无条号** |
| `bcr/90423b21` | 16 | 16 | 0 | 0 | **missing 16** | B 类 |

三类病灶要用不同手段修：

- **A 类（assessment / cpra / tia）**：正文脚注为 0，引用链根本没接通 → 修生成期 marker 链路（§4.1、§4.2）
- **B 类（cn_flow / bcr）**：脚注接通了，但引用全是「法规级」无条号 → 修引用构造粒度（§4.4）
- **C 类（全模块共性）**：知识库条文抽取质量 + source_url 从不回填 → 修数据层（§4.5、§4.6）

`source_url` 在**所有** 12 个抽样任务中都是空，这是唯一 100% 复现的缺陷，也是最便宜的修复项。

---

## 2. 五个根因（含代码位置与证据）

### RC-1　双引用语法互斥，fallback 路径永不产生脚注

`backend/domains/cn/security_assessment/chapter_generator.py:419-421`：

```python
if citation_registry is not None:
    return convert_citation_markers(raw, citation_registry)
return ensure_paragraph_citations(raw, citations)
```

两个分支是**两套互不识别的语法**：

| 函数 | 识别 | 产出 | 是否登记脚注号 | 是否做 claim 校验 |
|---|---|---|---|---|
| `convert_citation_markers` (`postprocess.py:274`) | `{{CIT-...}}` | `[n]` | 是 | **否** |
| `apply_citation_policy` (`postprocess.py:191`) | `【依据：...】` | `【依据：...】` / `【待核验】` | **否** | 是 |

后果有三层：

1. **fallback 路径永不产生脚注**。`_build_fallback_chapter` 结尾走 `attach_citations`（`backend/common/render/summary.py:75`）→ `apply_citation_policy`，只可能产出【依据：】或【待核验】，**不可能产出 `[n]`**。LLM 一降级，脚注数必然为 0。
2. **LLM 路径丢失 claim 校验**。走 `convert_citation_markers` 时完全跳过 `apply_citation_policy`，法律规则/风险判断句缺依据也不会被标注——校验强度取决于走了哪个分支，这本身是不可接受的不确定性。
3. **两套语法混用时互相污染**。若 LLM 同时输出 `{{CIT-}}` 和【依据：】，前者被转成 `[n]`，后者进入 allowlist 校验；`[n]` 不被 `apply_citation_policy` 视作有效依据，于是同一句话可能既有 `[n]` 又被追加「待核验：缺少法规依据」。

实测 `outputs/assessment/a3f2f723.../V0GatewayCo_自评估报告正文_20260806.md`：残留 `{{CIT-}}` 0、`[n]` 0、【依据：】0、「待核验：缺少法规依据」**4** 处。典型 fallback 产物。

### RC-2　marker 正则与真实 citation_id 不匹配（55636 / 55727 ≈ 99.8%）

正则在两处重复定义且完全一致——`backend/common/citation/registry.py:8` 与 `backend/common/llm/postprocess.py:10`：

```python
_CIT_MARKER_RE = re.compile(r"\{\{(CIT-[A-Z]+-[A-Z0-9]+-(?:ART[A-Z0-9_]+|GEN)-P\d+)\}\}")
```

只允许 `CIT-` + 4 段。但 `generate_citation_id`（`id_generator.py:42`）用 `LAW_ABBREVIATIONS` 的键作缩写，其中 `EXPORT-ASSESSMENT`、`DATA-CLASSIFICATION`、`IMPORTANT-DATA`、`MULTI-LEVEL`、`EXPORT-GUIDE` **本身含连字符**，生成 5 段 ID：

```text
CIT-CN-EXPORT-ASSESSMENT-ART5-P01   ← 正则不匹配
```

对全量输出目录的 citation_id 做正则回归：

| 不匹配原因 | 数量 |
|---|---|
| 缩写含连字符导致段数 > 4 | 4772 |
| 非 ASCII 条号 token（`ART一` / `ART二十`） | 174 |
| 前缀不是 `CIT-`（`synthesize_citation_map` 造的 `assessment-{task}-reg-1` 等） | 50690 |
| **可匹配** | **91** |

`generate_citation_id` 的 `re.sub(r"[^A-Z0-9]+", "_", ...)` 不处理中文数字，上游 `_extract_article_number` 漏转时就产出 `ART一`。

这意味着：**即使 LLM 严格按 `build_marker_list()` 给出的 marker 原样输出，这些 marker 也不会被替换**。它们会以字面 `{{CIT-CN-EXPORT-ASSESSMENT-ART5-P01}}` 残留在正文（内部标记外泄），同时 registry 拿不到脚注号。这条路径目前只对 `PIPL` / `DSL` / `CSL` / `SCC` 这几个无连字符缩写且条号已转阿拉伯数字的引用有效——正好解释了为什么 assessment 的 11 条里只有 `CN-LAW-002:20`、`CN-LAW-001:31` 两条命中。

### RC-3　API 读时合成并回写，制造与正文无关的引用

`backend/api/v1/endpoints/citations.py:217-238`：

```python
if not footnote_map_raw and target_module:
    recovery_payload = _read_recovery_payload(target_module, task_id)
    ...
    synthesized_footnote_map, synthesized_all_items = synthesize_citation_map(...)
    if synthesized_footnote_map:
        footnote_map_raw = synthesized_footnote_map
        ...
        write_citation_map_json(...)   # ← 回写磁盘
```

`_read_recovery_payload` 扫 `trace/*.json` 的 `detail.hits`，把**检索命中**当引用（`citations.py:104-112`），`synthesize_citation_map` 再按列表顺序编号 1..N（`output.py:421-424`）。

三个问题：

1. **语义造假**。检索命中 ≠ 正文引用。合成出的编号声称是脚注号，正文里却没有对应 `[n]`。这正是「正文 0 索引 / map 7 条」的来源。
2. **污染事实基线**。回写覆盖 citation_map.json，下一次读取拿到的是合成结果，原始「footnote_map 为空」这个真相被抹掉，回归测试和事实基线文档都会读到被污染的数据。
3. **失败原因被放大**。合成项的 `article_no` 来自 `_citation_article_from_source` 对自由文本的切分（`output.py:316`），条号质量远低于 grounding 路径，`article_not_found` 比例随之升高。

契约文档 §4 写「找不到 CitationMap 时返回空集合，而不是伪造引用」——当前实现违反了自己的契约：CitationMap 存在但 footnote_map 为空时，走的正是伪造路径。

### RC-4　引用构造粒度不足：B 类模块全部无条号

`cn_flow` 32/32、`bcr` 16/16 全部 `article_missing`，即 `article_no` 为空。`_resolve_citation_target`（`output.py:200-210`）此时只能给 `source_overview`，`can_jump=False`。

根源在 `_MODULE_LEGAL_SOURCE_MAP`（`module_grounding.py`）里存在 `{"title": "EU 2021/914", "article": "", ...}` 这类**空条号映射**。空条号从设计上就注定不可跳转，却仍以「引用」身份进入 CitationMap，稀释了引用总体的可信度。

### RC-5　知识库条文抽取质量：not_found / not_unique 的真实来源

失败项**不是 URL 构造错误，而是知识库里根本没有可定位的条文**。

**(a) 整部法规缺条文切分。** `CN-REG-004`（数据出境安全评估办法）在 `resources/legal/registry/regulation_articles.jsonl` 里只有 9 行，`article_ref` 全是 `段落1..段落9`，内容是网页正文——含「中央网络安全和信息化委员会办公室 © 版权所有」「京ICP备1404」「Produced By CMS 网站群内容管理系统」。**这部法规一条正式条文都没有入库**，所以 assessment 那 6 条 `art=1..6` 必然全部 `article_not_found`。`CN-SUP-003`（个人金融信息保护技术规范）、`CN-SUP-004`（个人信息安全规范）同样只有「段落n」，内容是目录和起草单位名单。`CN-LAW-004` 更是 0 行。

**(b) 续行被误标成被引用的条号 → not_unique。** 全库 1672 行里 34 个 `(source_id, article_no)` 重复键，模式高度一致。以 `CN-LAW-003` 第十七条为例：

| article_id | article_ref | content 开头 |
|---|---|---|
| `CN-LAW-003-017` | 第十七条 | 第十七条 个人信息处理者在处理个人信息前，应当以显著方式… |
| `CN-LAW-003-029` | **第十七条** | 第十七条第一款规定的事项外，还应当向个人告知处理敏感个人信息的必要性… |

第二行实际是**第三十条**（「处理敏感个人信息的，除本法第十七条第一款规定的事项外…」），开头被截断后剩下一句交叉引用，抽取器据此把它标成「第十七条」。同类还有 `第四十条`（实为第三十八条条文项）、`第三条`（实为第五十三条）、`CN-LAW-001` 的 第二十三/二十五/二十六/二十七/二十八/二十九条。

**可判定特征**：`article_id` 的序号与 `article_ref` 的条号不一致。`CN-LAW-003-029` 序号 029 ↔ ref 第十七条，冲突；`CN-LAW-003-017` 序号 017 ↔ 第十七条，一致。**序号是抽取时的物理顺序，比正文首句的交叉引用更可信**——这给出一条确定性的去重规则（§4.5）。

**(c) source_url 从不回填。** `regulation_articles.jsonl` 有 `source_url` 字段（399/1672 非空），`sources.csv` 有 `url` 列（19/69 非空），但 `normalize_citation_item`（`output.py:269-270`）只读 item 自带的 `source_url`，从不查注册表回填。上游 `citation_builder` / `module_grounding` 也不写这个字段。结果：`source_url` 恒为空 → `_is_safe_external_url` 恒 False → `available_actions` 永不含 `open_official_source` → 前端「查看官方发布版本」按钮永不出现（`CitationArticleDrawer.tsx` 尾部条件渲染）。

### RC-6　前端闭环缺口

- **脚注渲染分支永不触发**。`CitationMarkdownRenderer.tsx:184-197` 已实现 `[n]` → Popover → Drawer 的完整链路，但正文里没有 `[n]`，代码是死的。这点要说清楚：前端不是没做，是**上游没给它输入**。
- **citation_map 以独立标签暴露原始 JSON**。`ResourcePanel.tsx:229` 把 `citation_map.json` 当普通产物列为「引用映射」标签。它是**内部契约文件，不是用户交付物**。
- **Drawer 缺三个控件**：复制引用、`quote_text` 在条文原文中的高亮、新规标签。数据其实已就绪——`sources.csv` 有 `effective_date` / `status`（6 部 ≥ 2025-01-01，含 `CN-LAW-001` 网络安全法 2025 修正，生效 2025-12-29），只是未进入引用响应。
- **失败项只给机器字段**。后端 `available_actions` 已给出 `search_within_source` / `queue_for_ingestion` / `retry_resolution` / `manual_review`，`FAILURE_LABELS` 也已有中文文案，但**没有任何按钮承接这些动作**。`/api/v1/knowledge/search` 已存在，足以支撑 `search_within_source`，属于「接线即可用」。

---

## 3. 目标与验收口径

### 3.1 设计原则

1. **单一引用语法**。生成期只允许一种正文引用形式，其余形式在门禁处报错，不做兼容。
2. **不伪造引用**。引用只能来自生成期登记，读取期一律不得合成。读到空就是空。
3. **能力如实表达**。`can_jump` 只在条文唯一命中时为 true；不可跳转项必须给出用户可执行的下一步，而非机器字段。
4. **磁盘产物只写不改**。API 读取路径不得回写 citation_map.json。
5. **数据缺口显式化**。没有条文切分的法规不允许伪装成「条文级引用」。

### 3.2 验收口径

| 指标 | 当前 | 目标 | 判定方式 |
|---|---|---|---|
| 正文脚注数 / footnote_map 条数 | assessment 0 / 0（map 被合成为 7） | 严格相等且 > 0 | 门禁脚本比对正文 `[n]` 集合与 footnote_map 键集合 |
| marker 正则对真实 ID 覆盖率 | 0.16% | 100% | 全量 citation_id 回归断言 |
| 正文残留 `{{CIT-}}` | 未知（正则不匹配时会残留） | 0 | 交付物扫描门禁 |
| 「待核验：缺少法规依据」与已有脚注同句共存 | 存在 | 0 | 后处理不变式 |
| 条文级跳转率（有条号的引用） | assessment 2/11、cn_flow 0/32 | ≥ 90% | citation_map 统计 |
| `article_not_unique` | 全库 34 个重复键 | 0 | 注册表唯一性门禁 |
| `source_url` 非空率（注册表有 URL 的源） | 0% | 100% | 回填后统计 |
| API 读取期合成 | 存在且回写 | 0 次 | 单测断言不写盘 |
| citation_map.json 出现在用户产物标签 | 是 | 否 | 前端产物过滤 |

条文级跳转率的分母是「有条号的引用」。法规级引用（无条号）不计入分母，但需在 §4.4 收敛其占比。

---

## 4. 修复方案

### 4.1　P0-1　统一为单一引用语法（修 RC-1）

**决策：正文唯一合法引用形式为 `[n]` 脚注，唯一生成来源为 `{{CIT-...}}` marker 经 registry 转换。**

`【依据：法规名 第X条】` 降级为**纯校验中间态**，不再作为最终交付形态。理由：它是自由文本，无法承载 `citation_id`，因而无法与 CitationMap 建立稳定映射——这是当前断链的结构性原因。

改造 `postprocess.py`，新增单一入口取代互斥的两分支：

```python
def apply_citation_pipeline(
    text: str,
    *,
    registry: "CitationRegistry | None",
    allowed_citations: list[str] | None,
    max_items: int = 3,
) -> CitationPipelineResult:
    """引用后处理唯一入口：marker 转换 + claim 校验，顺序固定，两步都不可跳过。

    Step 1  {{CIT-x}} → [n]，并在 registry 登记全局脚注号
    Step 2  【依据：...】→ 解析为 citation_id 后同样转 [n]（兼容 LLM 退化输出）
    Step 3  对 LEGAL_RULE / RISK_JUDGMENT 句做 claim 校验，
            已有 [n] 视为有依据，不再追加【待核验】
    Step 4  结构规范化
    """
```

关键不变式（写成单测）：

- **I-1**　`[n]` 视为有效依据。Step 3 的 `has_verified_marker` 判定必须同时接受 `valid_citations` 与句内已存在的 `[n]`。当前 `postprocess.py:255` 只看 `valid_citations`，是「有脚注仍被标待核验」的直接原因。
- **I-2**　fallback 路径同样走本入口。`_build_fallback_chapter` 结尾的 `attach_citations` 改为 `apply_citation_pipeline(..., registry=registry)`，并在 fallback 文本内按 issue→citation 绑定写入 `{{CIT-}}` marker。fallback 是当前实际主路径，必须产出脚注。
- **I-3**　registry 为 None 时不静默降级。抛 `CitationPipelineError`，由调用方决定是否可无引用交付。静默降级正是问题被隐藏至今的原因。
- **I-4**　产出物零残留。返回前断言无 `{{`、无未登记 `[n]`。

`ensure_paragraph_citations` / `attach_citations` / `convert_citation_markers` 保留为**薄兼容层**并标注 deprecated，内部一律委托新入口，禁止新增调用点（门禁：调用点白名单只减不增）。

### 4.2　P0-2　修 marker 正则与 ID 生成（修 RC-2）

**a. 单一正则来源。** 新建 `backend/common/citation/markers.py`，`_CIT_MARKER_RE` 只在此定义并导出，`registry.py:8` 与 `postprocess.py:10` 改为 import。门禁：全仓 `_CIT_MARKER_RE = re.compile` 出现次数必须为 1。

**b. 放宽正则以匹配真实 ID：**

```python
CITATION_ID_RE = re.compile(r"CIT-[A-Z]{2}-[A-Z0-9-]+-(?:ART[A-Za-z0-9_一-鿿]+|GEN)-P\d+")
CIT_MARKER_RE  = re.compile(r"\{\{(" + CITATION_ID_RE.pattern + r")\}\}")
```

同时收紧 ID 生成侧，避免继续产出畸形 ID：

- `generate_citation_id` 在构造 `ART` token 前先调 `normalize_article_no`（`locators.py:27`），把中文数字转阿拉伯数字，杜绝 `ART一`。
- 缩写内连字符统一替换为 `_`：`EXPORT-ASSESSMENT` → `EXPORT_ASSESSMENT`。段数回到 4，兼容旧 ID 由放宽后的正则兜住。
- 新增 `is_valid_citation_id(cid) -> bool`，`CitationRegistry.register` 对非法 ID 抛错而非静默接收。

**c. 全量回归断言。** 门禁脚本对 `outputs/**/citation_map.json` 全部 citation_id 断言 `CITATION_ID_RE.fullmatch` 通过，当前基线 55727 个 ID 必须 100% 匹配（`synthesize_citation_map` 造的非 `CIT-` 前缀 ID 随 §4.3 删除而消失）。

### 4.3　P0-3　禁止读取期合成与回写（修 RC-3）

**a. 删除读取期合成。** `citations.py:187-210`（data 为 None 时）与 `citations.py:217-238`（footnote_map 为空时）两处合成分支全部移除。`get_report_citations` 回归为纯读取 + 规范化。

**b. 禁止读取期写盘。** `get_report_citations` 中 `write_citation_map_json` 与 `output_dir.mkdir` 调用全部删除。单测断言：调用该接口后 citation_map.json 的 mtime 与内容 hash 不变。

**c. 空态如实上报。** 扩展 `CitationMapResponse`：

```python
class CitationMapResponse(BaseModel):
    task_id: str
    module: str = ""
    footnote_map: dict[str, CitationDetailResponse]
    citation_count: int
    # 新增
    map_status: Literal["ok", "empty_no_file", "empty_no_footnotes", "degraded"] = "ok"
    map_status_detail: str = ""
    unmapped_item_count: int = 0   # all_items 有但 footnote_map 无 → 检索到但正文未引用
```

`empty_no_footnotes` + `unmapped_item_count=11` 正是 assessment 的真实状态。前端据此显示「本报告未在正文引用法规依据；检索到 11 条候选依据未被引用」——**这是诚实且可诊断的表述**，远优于凭空给 7 条。

**d. 保留合成能力但移出读路径。** `synthesize_citation_map` 不删除，改为仅供**离线补录脚本**（`scripts/backfill_citation_map.py`）使用，需显式 `--allow-synthesize` 且在产物写入 `"provenance": "synthesized_from_trace"` 标记，规范化时该标记强制 `can_jump=False`。合成引用永远不得声称可精确跳转。

**e. 清理已污染产物。** 现存 citation_map.json 中，凡 citation_id 为 `{module}-{task}-{reg|chapter|result}-{n}` 形态者均为合成污染。补录脚本提供 `--mark-synthesized` 模式为其补 provenance 标记，不静默删除历史产物。

### 4.4　P1-1　收敛法规级引用（修 RC-4）

- `_MODULE_LEGAL_SOURCE_MAP` 中 `article: ""` 的条目改为显式 `citation_granularity: "source_level"`，构造时 `citation_type` 记为 `standard_clause` 或 `official_guide`，**不再混入 `law_article`**。
- `_resolve_citation_target` 对 `source_level` 引用返回新 `resolution_type: "source_level_by_design"`，与「本该有条号但查不到」的 `article_missing` 区分开。前者是设计选择，后者是缺陷——当前两者混在同一个 `article_missing` 桶里，掩盖了 cn_flow/bcr 的真实问题。
- 对 `EU 2021/914` 这类可细化到附件/模块的来源，补 `section_id`（如 `Module Two Clause 8.1`）；`build_knowledge_url` 已支持 `section` 参数（`output.py:245-248`），无需改动。

### 4.5　P1-2　知识库条文抽取治理（修 RC-5a、RC-5b）

**a. 条文唯一性去重（确定性规则）。** 新增 `scripts/dedupe_regulation_articles.py`：

```text
对每个重复的 (source_id, normalize_article_no(article_ref)):
  1. 计算每行 article_id 尾部序号 ordinal
  2. 若某行 ordinal == article_ref 条号 → 该行为正条，保留
  3. 其余行判定为「续行误标」：
     - content 以「第X条」开头且紧随「第.款」「的规定」「规定的」等交叉引用词 → 确认续行
     - 按 ordinal 反查正确条号并改写 article_ref
     - 无法确定则 article_ref 置空、article_id 保留，标 needs_review: true
  4. 输出 dedupe_report.json：改写项、待复核项、无法判定项
```

对 34 个重复键的人工抽验（`CN-LAW-003` 第十七条 / 第四十条 / 第三条，`CN-LAW-001` 第二十三…二十九条）全部符合该模式，规则可覆盖。修复后 `pipia` 的 28 个 `article_not_unique` 直接转为可跳转。

**b. 未切分法规显式标记。** `CN-REG-004` / `CN-SUP-003` / `CN-SUP-004` / `CN-LAW-004` 的「段落n」不是条文。在 `sources.csv` 增列 `article_granularity ∈ {article, paragraph, none}`：

- `_resolve_citation_target` 对 `article_granularity != "article"` 的源，跳过条文匹配，直接返回 `source_overview` + `failure_reason="source_not_article_indexed"`，并给出 `available_actions: ["view_source_overview", "search_within_source", "queue_for_reingestion"]`。
- 前端文案改为「该法规尚未完成条文级入库，暂只能定位到法规全文」——**指向数据缺口，而非暗示引用错误**。这比现在的 `article_not_found`（听起来像引用编错了条号）准确。

**c. 重新入库优先级。** 按引用频次排序，`CN-REG-004`（数据出境安全评估办法，安全评估路径核心规范，`usage_priority=P0`，`report_usage=可直接引用条文号`）最高。当前它被声明为「可直接引用条文号」却一条未入库，是契约与数据的直接矛盾。同时清理入库管道里的网页噪声（版权页、备案号、CMS 页脚、目录、起草单位名单）。

**d. 唯一性门禁。** `scripts/check_regulation_articles.py`：`(source_id, normalize_article_no(article_ref))` 全库唯一；声明 `article_granularity=article` 的源必须有 ≥ 1 行匹配 `第X条` 的 `article_ref`。入 CI。

### 4.6　P1-3　source_url 回填（修 RC-5c）

在 `normalize_citation_item` 中，`source_url` 为空时按优先级回填：

1. `regulation_articles.jsonl` 中 `(source_id, article_no)` 行的 `source_url`（条文级精确，399 行可用）
2. `sources.csv` 中 `source_id` 行的 `url`（法规级，19 行可用）
3. 仍为空 → 保持空，`available_actions` 不含 `open_official_source`

约束：回填值必须过 `_is_safe_external_url`；**回填只影响 `source_url`，不得影响 `knowledge_url` 或 `can_jump`**（契约 §3 的字段语义边界）。为避免每次规范化都读文件，与 `_load_article_counts` 共用 `lru_cache` 索引，一次加载同时构建 count 与 url 两张表。

### 4.7　P1-4　前端闭环（修 RC-6）

**a. 正文 → 脚注 → 条文原文闭环。** `CitationMarkdownRenderer` 的 `[n]` 链路已就绪，§4.1 修好后自然接通。补两点：

- 脚注角标 hover 显示 `法规名 第X条`（`shortenCitationLabel` 已有），点击开 Drawer。
- 正文命中引用的句子加 `data-citation-ref` 属性，Drawer 打开时对应句轻高亮，建立视觉对应关系。

**b. 引用片段在条文原文中高亮。** Drawer 已通过 `fetchArticleDetail` 拿到 `article_content` 与前后条文。新增：将 `citation.quote_text` 在 `article_content` 中做归一化子串匹配（复用 `compactText` 的标点/空白归一），命中则 `<mark>` 高亮，未命中则在原文上方显示「引用摘录与条文原文不完全一致」提示。这一提示本身是有价值的质量信号——它暴露 grounding 摘录漂移。

**c. 复制引用按钮。** Drawer footer 增加，提供两种格式：

```text
规范引用：《中华人民共和国数据安全法》第二十条
完整引用：《中华人民共和国数据安全法》第二十条：「<条文原文>」（来源：CN-LAW-002，https://...）
```

用 `navigator.clipboard`，失败回退 `document.execCommand`（仓库已有 clipboard 用法可参考 `ReportCenterPage.tsx`）。

**d. 新规标签。** `CitationDetailResponse` 增字段，由 `normalize_citation_item` 从 `sources.csv` 读取：

```python
effective_date: str = ""
publish_date: str = ""
source_status: str = ""          # effective / reference
is_recent: bool = False          # effective_date 距今 ≤ 12 个月
amendment_note: str = ""         # 标题含「修正」「修订」时提取，如「2025修正」
```

Drawer 与 Popover 显示：`is_recent` → 「新规」徽标 + 生效日期；`amendment_note` 非空 → 「2025修正」徽标；`source_status == "reference"` → 「参考性文件」徽标（区别于强制性规范）。当前 6 部法规 `effective_date ≥ 2025-01-01`，`CN-LAW-001`（网络安全法 2025 修正，2025-12-29 生效）会同时命中「新规」与「2025修正」。

**e. 失败项给可执行动作。** 按 `available_actions` 渲染按钮，取代裸机器字段：

| action | 控件 | 行为 |
|---|---|---|
| `view_article` | 在知识库中继续阅读 | 已实现 |
| `view_source_overview` | 查看法规概览 | 已实现 |
| `search_within_source` | **在本法规内搜索** | 新增，调 `/api/v1/knowledge/search?q={quote_text}&source={source_id}` 展示候选条文，用户可确认后修正引用 |
| `open_official_source` | 查看官方发布版本 | 已实现，待 §4.6 供数 |
| `queue_for_ingestion` / `queue_for_reingestion` | **申请补录该法规** | 新增，写入知识库复核队列（`knowledge_review.py` 已有基础设施） |
| `retry_resolution` / `manual_review` | **提交人工复核** | 新增，同上 |

`search_within_source` 是投入产出比最高的一项：后端接口已存在，能把「不可跳转」从死胡同变成用户可自助修正的入口。

**f. citation_map.json 移出用户产物标签。** `ResourcePanel.tsx:229` 的映射删除，改为在产物列表过滤 `citation_map.json`（与其他内部契约文件同等对待）。引用信息只通过正文脚注和 Drawer 呈现。若需调试视图，放到开发者面板而非用户交付区。

**g. 空态诚实呈现。** 依 §4.3c 的 `map_status`：

- `empty_no_footnotes` + `unmapped_item_count > 0` → 「本报告正文未引用法规依据；系统检索到 N 条候选依据但未被正文引用，建议人工复核」
- `empty_no_file` → 「本报告未生成引用映射」
- `degraded` → 显示降级原因

---

## 5. 契约文档更新

`docs/standards/DataComplyFlow_引用跳转与CitationMap契约.md` 需同步（避免文档与实现再次分叉）：

1. **§1 全链路** 增加「生成期唯一入口 `apply_citation_pipeline`」；标注 API 读取期**不再**有合成/回写环节。
2. **新增「引用语法契约」章节**：`{{CIT-}}` 为生成期唯一 marker，`[n]` 为正文唯一交付形态，`【依据：】` 为 deprecated 中间态；`citation_id` 形态与 `CITATION_ID_RE` 单一来源。
3. **§2 写入契约** 增加「footnote_map 的键集合必须等于正文 `[n]` 集合」；合成产物必须带 `provenance`。
4. **§3 URL 字段语义** 增加 `source_url` 回填优先级与「回填不影响 `can_jump`」的边界。
5. **§4 API 读取契约** 明确「读取期禁止合成、禁止写盘」，补 `map_status` 语义表。
6. **新增「条文级定位能力矩阵」**：`article_granularity` 与 `resolution_type` / `failure_reason` / `available_actions` 的完整映射，含新增的 `source_not_article_indexed`、`source_level_by_design`。
7. **§6 验证门禁** 补入下列新增门禁脚本。

---

## 6. 测试与门禁

### 6.1 新增单测

| 文件 | 覆盖 |
|---|---|
| `backend/common/citation/tests/test_markers.py` | `CITATION_ID_RE` 对 5 段 ID / 中文条号 ID / 旧 4 段 ID 全匹配；非法 ID 被 `register` 拒绝；正则单一定义 |
| `backend/common/llm/tests/test_citation_pipeline.py` | I-1 至 I-4 四条不变式；`[n]` 存在时不追加【待核验】；registry 为 None 抛错；产物零残留 |
| `backend/api/v1/tests/test_citations_api.py`（扩展） | 读取期不合成（footnote_map 空时返回空 + `map_status=empty_no_footnotes` + `unmapped_item_count`）；读取期不写盘（mtime + hash 不变） |
| `backend/common/citation/tests/test_source_url_backfill.py` | 三级回填优先级；不安全 URL 被拒；回填不改 `can_jump`；幂等 |
| `backend/common/citation/tests/test_resolution_matrix.py` | `article_granularity` × `resolution_type` × `available_actions` 全矩阵 |
| `backend/domains/cn/security_assessment/tests/test_chapter_citations.py` | fallback 路径产出 `[n]`；正文 `[n]` 集合 == footnote_map 键集合 |
| `frontend/src/components/citation/CitationArticleDrawer.test.tsx`（扩展） | 复制引用、quote 高亮、quote 不匹配提示、新规/修正/参考徽标、失败项动作按钮 |
| `frontend/src/components/citation/CitationMarkdownRenderer.test.tsx`（扩展） | 空态三种 `map_status` 文案；句子高亮联动 |

### 6.2 新增 CI 门禁

```bash
# 引用 ID 全量正则回归
uv run python scripts/check_citation_id_format.py --scan outputs

# 正文脚注 ↔ footnote_map 一致性
uv run python scripts/check_citation_footnote_parity.py --scan outputs

# 交付物零内部标记（{{CIT-}}、ISSUE-、【待核验】未进附录）
uv run python scripts/check_report_no_internal_markers.py

# 知识库条文唯一性 + granularity 声明一致
uv run python scripts/check_regulation_articles.py

# marker 正则单一定义 + deprecated 调用点白名单只减不增
uv run python scripts/check_citation_single_source.py
```

### 6.3 回归基线

```bash
uv run --frozen pytest -q backend/common/citation/tests
uv run --frozen pytest -q backend/common/llm/tests
uv run --frozen pytest -q backend/api/v1/tests/test_citations_api.py
uv run --frozen pytest -q backend/domains/cn/security_assessment/tests
uv run --frozen pytest -q backend/domains/eu/dpia/tests backend/domains/eu/tia/tests
cd frontend && npm test -- citation
```

`dpia` 与 `pipia` 目前是健康基线（100% / 83% 条文级跳转），改造后**不得回退**——这两个模块是本次改造的对照组。

---

## 7. 分阶段实施

按「先止血、再修数据、后做体验」排序。每阶段前后各一次 git 提交，保持 before/after 边界。

### 阶段 0　基线固化（无功能变更）

- 落地 §6.2 五个门禁脚本，**先只报告不阻断**，产出当前真实基线数字
- 用 `--mark-synthesized` 标记已污染的历史 citation_map.json
- 提交：`test: add citation integrity gates (report-only baseline)`

### 阶段 1　P0 止血（断链修复）

- §4.2 marker 正则与 ID 生成 → §4.1 统一引用入口 → §4.3 移除读取期合成与回写
- 顺序不可颠倒：先修正则，否则统一入口后 marker 仍不被识别，只会把断链换个位置
- 门禁转为阻断
- 验收：assessment / cpra / tia 三个 A 类模块正文脚注数 > 0 且与 footnote_map 严格相等
- 提交：`fix: unify citation pipeline and stop read-time synthesis`

### 阶段 2　P1 数据层（跳转率提升）

- §4.5 条文去重 + granularity 标记 + `CN-REG-004` 重新入库
- §4.6 source_url 回填
- §4.4 法规级引用收敛
- 验收：`article_not_unique` 归零；条文级跳转率 ≥ 90%；`source_url` 非空率 100%（注册表有 URL 的源）
- 提交：`fix: dedupe regulation articles and backfill citation source urls`

### 阶段 3　P1 前端闭环（体验）

- §4.7 a→g 全部
- 验收：正文句 → 脚注 → 条文原文闭环可走通；复制引用、高亮、新规标签、失败项动作齐备；citation_map.json 不再出现在用户产物标签
- 提交：`feat: complete citation drawer interaction loop`

### 阶段 4　契约与基线同步

- §5 契约文档更新
- 更新 `status/CURRENT_DataComplyFlow_全功能运行验证与问题汇报_20260805.md` 第 8.f 节结论与 `status/todo/DataComplyFlow_预期与实际对照分析_20260806.md` 对应行
- 重跑安全评估全流程，用真实数字替换本文档 §1 的现状表
- 提交：`docs: sync citation contract and verification baseline`

---

## 8. 风险与显式不做的事

### 风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 放宽 marker 正则后误匹配正文中形似 ID 的文本 | 错误替换 | `fullmatch` + `is_valid_citation_id` 双重校验；仅在 `{{}}` 包裹内替换 |
| 条文去重规则误判非「续行误标」的重复 | 丢失正条 | `dedupe_report.json` 全量留痕；无法确定项标 `needs_review` 不自动改写；34 项人工抽验后再批量执行 |
| 移除读取期合成后，历史任务引用变空 | 用户观感倒退 | 这是**如实**表达，非倒退；配 §4.3d 离线补录脚本 + §4.7g 诚实空态文案 |
| 统一引用入口触及 dpia / pipia 健康路径 | 现有 100% / 83% 跳转率回退 | 两模块纳入阶段 1 回归必跑；跳转率不得下降 |
| `CN-REG-004` 重新入库涉及外部抓取 | 阻塞阶段 2 | 先用已有 snapshot（`resources/legal/sources/cn/snapshots/cac`）重抽，避免新增网络依赖 |

### 显式不做

1. **不做引用自动纠错**。`article_not_found` 时不猜相近条号，只给 `search_within_source` 让用户确认。法律引用错误的代价高于不可跳转。
2. **不把检索命中当引用**。这是 RC-3 的成因，不以任何形式保留在读路径。
3. **不为提高跳转率放宽 `can_jump`**。`can_jump=true` 严格等价于「条文唯一命中」，`article_not_unique` 修好前该项一律 false。
4. **不保留 `【依据：】` 作为交付形态**。仅作 deprecated 中间态兼容 LLM 退化输出，不新增支持。
5. **不在本轮做人工复核冻结队列**（对照分析第 211 行提到的六类条件冻结）。§4.7e 只把动作按钮接到已有 `knowledge_review` 基础设施，完整审批状态机单列议题。
6. **不改 `knowledge_url` 的 URL 形态**。`/knowledge/laws/{source_id}?article=` 现行契约稳定，本轮不动。

---

## 9. 附：问题—根因—修复对照

| 验收报告观察 | 根因 | 修复 |
|---|---|---|
| 正文写「未引用法规依据索引」 | RC-1 fallback 永不产脚注 → footnote_map 空 | §4.1 |
| citation map 同时有 7 条 | RC-3 API 读时用检索命中合成并回写 | §4.3 |
| 正文提三部法律却标「待核验：缺少法规依据」 | RC-1 `[n]` 不被视作有效依据 + fallback 走 policy | §4.1 I-1 |
| can_jump 仅 1/7（14.3%） | RC-5a `CN-REG-004` 零条文入库 + RC-5b 条文重复 | §4.5 |
| 失败原因多为 `article_not_found` | RC-5a 法规未做条文切分 | §4.5b、§4.5c |
| 失败原因含 `article_not_unique` | RC-5b 续行被误标为被引条号 | §4.5a |
| `source_url` 均为空 | RC-5c 从不回填 | §4.6 |
| 正文脚注 0 条 | RC-1 + RC-2 双重阻断 | §4.1、§4.2 |
| 引用映射以原始 JSON 独立标签呈现 | RC-6 citation_map.json 被当用户产物 | §4.7f |
| 未完成「正文句 → 脚注 → 条文原文」闭环 | RC-1 正文无 `[n]`，前端链路空转 | §4.1 + §4.7a |
| 失败项只给机器字段 | RC-6 `available_actions` 无控件承接 | §4.7e |
| 法规标题、条号、引用片段未在正文高亮 | RC-6 缺高亮实现 | §4.7a、§4.7b |
| 缺「复制引用」按钮 | RC-6 未实现 | §4.7c |
| 缺新规标签 | RC-6 `effective_date` / `status` 未进引用响应 | §4.7d |
