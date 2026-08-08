# DataComplyFlow 引用跳转机理详解 — 代码流程追踪

> 文档性质：问题机理分析 + 代码流程追踪
> 编制日期：2026-08-08
> 问题源头：三条互不相通的引用链路 + 知识库条文抽取质量不足
> 参考文档：`status/todo/DataComplyFlow_引用跳转闭环治理方案_20260806.md`
> 历史诊断基线：`1a3d0dd`（下文代码片段、数量和故障现象均以该基线为准）
> 当前复核基线：`7182378`（2026-08-08）
> 当前状态：**历史诊断保留，剩余问题继续实施；本文不得作为“全部完成”的验收报告。**

## 〇、当前落实状态与继续实施边界

本节是当前事实入口。第一节之后的内容保留为历史诊断证据，不再代表当前代码状态。

### 0.1 已完成、部分完成和未完成

| 问题 | 当前状态 | 当前证据 | 后续处理 |
|---|---|---|---|
| RC-2 Marker 正则与 ID 不一致 | 已完成 | `backend/common/citation/markers.py`；提交 `f81bfaf` | 保留阻断测试 |
| RC-3 API 读取期合成并回写 | 已完成 | `backend/api/v1/endpoints/citations.py`；提交 `870bd5c` | 保留 API 纯读取测试 |
| RC-5a CN-REG-004 网页噪声 | 已完成 | 已重建 20 条正式条文；提交 `979d714` | 纳入浏览器复验 |
| RC-5b 重复 `(source_id, article_no)` | 已完成 | 完整性检查重复键为 0；提交 `f7fc931` | 保留数据门禁 |
| `【依据：】` 条文验证 | 代码已接通、测试不足 | `CitationMarkdownRenderer.buildResolvedCitation()`；提交 `f2e0019` | 补组件测试和浏览器测试 |
| RC-5a 地区法规条文覆盖 | 部分完成 | 120 个来源中 102 个有条文、18 个零条文 | 补 OCR/切分或显式标记不可条文定位 |
| RC-1 双引用最终形态 | 未完成 | `convert_citation_markers` 与 `attach_citations/apply_citation_policy` 仍并存 | 统一生成期引用入口，迁移后删除旧调用 |
| RC-4 法规级引用语义 | 未完成 | 尚无 `citation_granularity` / `source_level_by_design` 契约 | 增加明确粒度和失败原因 |
| RC-5c 官网链接回填 | 未完成 | 3030 条文中 2620 条缺 `source_url`，当前规范化不回填 | 条文 URL 优先、来源 URL 兜底 |
| 浏览器端到端验收 | 未完成 | 现有 Playwright 用例未点击引用或验证条文定位 | 新增路径 A/B 点击测试和截图 |

### 0.2 本轮实施顺序

| 阶段 | 工作 | 完成标准 | Git 存档 |
|---:|---|---|---|
| 1 | 固化当前状态和测试基线 | 后端 723 项、前端 113 项和数据门禁可复现 | 文档提交 |
| 2 | 统一引用数据契约 | URL、粒度、状态元数据由公共层解析；API 与前端类型一致 | 后端契约提交 |
| 3 | 统一生成期引用入口 | 最终报告只交付 `[n]`；正文脚注集合等于 CitationMap；旧入口零生产调用 | 生成链路提交 |
| 4 | 完成前端引用交互 | 路径 A/B 均能打开抽屉；精确条文能继续阅读；失败状态给出明确说明 | 前端提交 |
| 5 | 本地浏览器验收 | Playwright 覆盖路径 A/B、精确跳转、不可跳转；保存截图和网络证据 | E2E 与验收文档提交 |

### 0.3 不允许用来宣称完成的证据

以下结果只能证明局部通过，不能代替浏览器端到端验收：

1. `pytest` 或 Vitest 全绿；
2. 直接调用知识库查询函数返回条文；
3. 只检查生成 URL 字符串含 `?article=`；
4. 只检查 CitationMap JSON 有数据；
5. 旧产物或旧提交中的成功截图。

最终验收必须在本地浏览器完成“正文引用 → 引用抽屉 → 对应条文 → 知识库定位”，并同时核对 API 响应、页面可见内容和截图。

---

## 一、期望流程 vs 实际断裂

### 1.1 正常流程（期望）

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: LLM 生成报告                                              │
│   输出: "用户应当遵守{{CIT-CN-LAW-001-ART20-P01}}的规定..."      │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: CitationRegistry 转换标记                                 │
│   backend/common/citation/registry.py                           │
│   - 识别 {{CIT-...}} 标记                                        │
│   - 调用 assign_footnote_number() 分配编号                       │
│   - 替换为 [1] 脚注                                              │
│   - _global_numbering 记录: {"1": "CN-LAW-001:20"}              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: 写入 citation_map.json                                   │
│   backend/common/citation/output.py                             │
│   - get_footnote_map() 读取 _global_numbering                   │
│   - build_citation_map_section() 构建映射                        │
│   - write_citation_map_json() 落盘                               │
│   产出: {"footnote_map": {"1": {source_id, article_no, ...}}}   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: 用户点击正文中的 [1]                                      │
│   frontend/src/components/citation/CitationMarkdownRenderer.tsx │
│   - 识别 [1] 标记                                                │
│   - 触发 Popover 显示简要信息                                     │
│   - 点击后打开 CitationArticleDrawer                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: API 查询引用详情                                          │
│   GET /api/v1/reports/{task_id}/citations                       │
│   backend/api/v1/endpoints/citations.py                         │
│   - 读取 citation_map.json 的 footnote_map                       │
│   - 查 regulation_articles.jsonl 获取条文内容                    │
│   - 返回 {article_no, article_content, source_url, can_jump}    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: 前端跳转到知识库条文                                       │
│   frontend/src/components/citation/CitationArticleDrawer.tsx    │
│   - 构造 knowledge_url: /knowledge/laws/{source_id}?article=20  │
│   - 打开新标签页或 Drawer 内嵌显示                                │
│   - 定位到具体条文，高亮引用片段                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 实际断裂的三个位置

```
❌ 断裂点 1: 正文里没有 [n] 脚注
   原因: RC-1 + RC-2 (两套语法互斥 + 正则不匹配)
   
❌ 断裂点 2: API 读取时伪造引用
   原因: RC-3 (从检索记录合成 + 回写磁盘)
   
❌ 断裂点 3: 即使脚注接通，也跳不到条文
   原因: RC-4 + RC-5 (无条号设计 + 数据质量差)
```

---

## 二、断裂点 1 详解：正文无脚注

### 2.1 根因 RC-1：双引用语法互斥

**代码位置**：`backend/domains/cn/security_assessment/chapter_generator.py:419-421`

```python
def _finalize_chapter_text(raw: str, ...) -> str:
    if citation_registry is not None:
        # 路径 A：LLM 正常输出时
        return convert_citation_markers(raw, citation_registry)
    # 路径 B：LLM 降级/失败时的 fallback
    return ensure_paragraph_citations(raw, citations)
```

**两条路径的行为差异**：

| 函数 | 位置 | 识别语法 | 产出 | 是否登记脚注号 | 是否做 claim 校验 |
|------|------|----------|------|---------------|------------------|
| `convert_citation_markers` | `postprocess.py:274` | `{{CIT-...}}` | `[n]` | ✓ 是 | ✗ **否** |
| `ensure_paragraph_citations` → `apply_citation_policy` | `postprocess.py:191` | `【依据：...】` | `【依据：...】` 或 `【待核验】` | ✗ **否** | ✓ 是 |

**问题分析**：

1. **fallback 路径永不产生脚注**
   - `_build_fallback_chapter`（各模块的降级逻辑）结尾调用 `attach_citations`
   - `attach_citations`（`backend/common/render/summary.py:75`）→ `apply_citation_policy`
   - `apply_citation_policy` 只会产出【依据：某某法 第X条】或【待核验：缺少法规依据】
   - **不会产出 `[n]` 脚注** → `registry.assign_footnote_number` 从未被调用
   - 结果：`_global_numbering = {}` → `get_footnote_map()` 返回 `{}`

2. **LLM 路径丢失 claim 校验**
   - 走 `convert_citation_markers` 时完全跳过 `apply_citation_policy`
   - 法律规则/风险判断句缺依据也不会被标注"待核验"
   - 校验强度取决于走哪个分支 → 不确定性

3. **两套语法混用时互相污染**
   - 若 LLM 同时输出 `{{CIT-}}` 和【依据：】
   - 前者被转成 `[n]`，后者进入 allowlist 校验
   - `[n]` 不被 `apply_citation_policy` 视作有效依据
   - 同一句话可能既有 `[n]` 又被追加"待核验：缺少法规依据"

**实测案例**：`outputs/assessment/a3f2f723.../V0GatewayCo_自评估报告正文_20260806.md`

- 残留 `{{CIT-}}`: 0
- `[n]` 脚注: 0
- 【依据：】: 0
- "待核验：缺少法规依据": **4 处**

→ 典型 fallback 产物

---

### 2.2 根因 RC-2：marker 正则与真实 citation_id 不匹配

**代码位置**：
- `backend/common/citation/registry.py:8`
- `backend/common/llm/postprocess.py:10`
- `backend/common/citation/id_generator.py:42`

**正则定义**（两处完全一致）：

```python
_CIT_MARKER_RE = re.compile(
    r"\{\{(CIT-[A-Z]+-[A-Z0-9]+-(?:ART[A-Z0-9_]+|GEN)-P\d+)\}\}"
)
```

**正则要求**：`CIT-` + 4 段，格式为 `CIT-{jurisdiction}-{law_abbr}-{article}-{para}`

**实际生成的 ID**（`generate_citation_id` 使用 `LAW_ABBREVIATIONS` 的键作缩写）：

```python
# LAW_ABBREVIATIONS 中的键
"EXPORT-ASSESSMENT": "数据出境安全评估办法"
"DATA-CLASSIFICATION": "数据分级分类指南"
"IMPORTANT-DATA": "重要数据识别指南"
"MULTI-LEVEL": "数据安全多层级保护"
"EXPORT-GUIDE": "数据出境申报指南"

# 生成的 citation_id（5 段，不是 4 段）
CIT-CN-EXPORT-ASSESSMENT-ART5-P01
#       ^^^^^^ ^^^^^^^^^^  ← 缩写本身含连字符，被当成 2 段
```

**全量回归统计**（55,727 个 citation_id）：

| 不匹配原因 | 数量 | 占比 |
|-----------|------|------|
| 缩写含连字符导致段数 > 4 | 4,772 | 8.6% |
| 非 ASCII 条号 token（`ART一` / `ART二十`） | 174 | 0.3% |
| 前缀不是 `CIT-`（`assessment-{task}-reg-1` 等，由 `synthesize_citation_map` 造） | 50,690 | 91.0% |
| **可匹配** | **91** | **0.16%** |

**问题分析**：

1. **缩写含连字符**
   - `generate_citation_id` 中 `re.sub(r"[^A-Z0-9]+", "_", ...)` 只替换非字母数字字符
   - 但缩写键本身是 `EXPORT-ASSESSMENT`（已含连字符）
   - 直接拼接后变成 `CIT-CN-EXPORT-ASSESSMENT-...`（5 段）
   - 正则匹配失败

2. **中文数字条号**
   - `_extract_article_number` 未转换中文数字时产出 `ART一`
   - 正则要求 `[A-Z0-9_]`，不包含中文
   - 匹配失败

3. **后果**
   - **即使 LLM 严格按 `build_marker_list()` 给出的 marker 原样输出**
   - 这些 marker 也不会被 `_CIT_MARKER_RE` 匹配
   - 它们会以字面 `{{CIT-CN-EXPORT-ASSESSMENT-ART5-P01}}` **残留在正文中**（内部标记外泄）
   - 同时 `registry.assign_footnote_number` 未被调用 → 拿不到脚注号

**为什么 assessment 只有 2/11 命中**：

- 只有 `PIPL`（个人信息保护法）/ `DSL`（数据安全法）/ `CSL`（网络安全法）/ `SCC` 这几个**无连字符缩写**且**条号已转阿拉伯数字**的引用能被匹配
- 正好是 `CN-LAW-002:20`、`CN-LAW-001:31` 这两条

---

### 2.3 断裂点 1 的实际表现

**链式反应**：

```
LLM 降级
  ↓
走 fallback 路径
  ↓
ensure_paragraph_citations 产出【依据：】形式
  ↓
没有调用 registry.assign_footnote_number
  ↓
_global_numbering = {}
  ↓
get_footnote_map() 返回 {}
  ↓
build_citation_map_section() 产出 "（本报告未引用法规依据索引）"  ← 现象 1
  ↓
_write_citation_map_json() 写入 footnote_map={}
  ↓
apply_citation_policy 找不到有效【依据：】
  ↓
追加 "待核验：缺少法规依据"  ← 现象 3
```

**或者**：

```
LLM 正常输出 {{CIT-EXPORT-ASSESSMENT-...}}
  ↓
_CIT_MARKER_RE 正则不匹配（5 段 vs 4 段）
  ↓
标记未被替换，原样残留在正文
  ↓
registry.assign_footnote_number 未被调用
  ↓
后续同上...
```

---

## 三、断裂点 2 详解：API 读取时伪造引用

### 3.1 根因 RC-3：读取期合成并回写

**代码位置**：`backend/api/v1/endpoints/citations.py:217-238`

```python
def get_report_citations(...):
    # 读取 citation_map.json
    footnote_map_raw = ...
    
    # ❌ 关键问题：footnote_map 为空时启动"救援"逻辑
    if not footnote_map_raw and target_module:
        # 读取检索 trace
        recovery_payload = _read_recovery_payload(target_module, task_id)
        
        # 从检索命中合成引用
        synthesized_footnote_map, synthesized_all_items = synthesize_citation_map(
            recovery_payload=recovery_payload,
            ...
        )
        
        if synthesized_footnote_map:
            footnote_map_raw = synthesized_footnote_map
            
            # ❌ 回写磁盘，污染事实基线
            write_citation_map_json(
                output_dir / "citation_map.json",
                footnote_map=synthesized_footnote_map,
                ...
            )
```

**`_read_recovery_payload` 做了什么**（`citations.py:104-112`）：

```python
def _read_recovery_payload(...):
    # 扫描 trace/*.json 文件
    for trace_file in trace_dir.glob("*.json"):
        trace_data = json.loads(trace_file.read_text())
        
        # 提取 RAG 检索命中
        if "detail" in trace_data and "hits" in trace_data["detail"]:
            # ❌ 把"检索到的文档"当成"正文引用"
            citations.extend(trace_data["detail"]["hits"])
    
    return {"citations": citations}
```

**`synthesize_citation_map` 做了什么**（`output.py:421-424`）：

```python
def synthesize_citation_map(recovery_payload, ...):
    citations = recovery_payload.get("citations", [])
    
    # ❌ 按列表顺序编号 1..N
    for idx, citation in enumerate(citations, 1):
        citation_id = f"{module}-{task_id}-reg-{idx}"  # 非标准 CIT- 格式
        footnote_map[str(idx)] = {
            "citation_id": citation_id,
            "source_id": citation.get("source_id"),
            "article_no": _citation_article_from_source(citation),  # 从自由文本切分
            ...
        }
    
    return footnote_map, all_items
```

**三个严重问题**：

1. **语义造假**
   - 检索命中 ≠ 正文引用
   - 系统检索时可能查到 20 部相关法规
   - 但正文实际只引用了 3 部
   - API 却把 20 部全编号为 [1]~[20]
   - **正文里根本没有对应的 [1]~[20] 标记**

2. **污染事实基线**
   - `write_citation_map_json` 回写覆盖原始文件
   - 下一次读取拿到的是合成结果
   - 原始"footnote_map 为空"这个真相被抹掉
   - 回归测试和事实基线文档都会读到被污染的数据

3. **失败原因被放大**
   - 合成项的 `article_no` 来自 `_citation_article_from_source` 对自由文本的切分（`output.py:316`）
   - 没有经过 grounding 的精确定位
   - 条号质量远低于正常路径
   - `article_not_found` 比例随之升高

**契约违反**：

`docs/standards/DataComplyFlow_引用跳转与CitationMap契约.md` §4 写道：

> 找不到 CitationMap 时返回空集合，而不是伪造引用

当前实现违反了自己的契约：
- CitationMap 文件存在但 `footnote_map` 为空时
- 走的正是伪造路径

---

### 3.2 断裂点 2 的实际表现

**以 `assessment/dc9b1db8` 为例**：

**阶段 1：生成期**
- LLM 降级 → fallback 路径 → 产出【依据：】
- 或 marker 正则不匹配 → 标记残留
- 结果：正文 0 个脚注，`footnote_map = {}`

**阶段 2：API 第一次读取**
```
GET /api/v1/reports/dc9b1db8/citations
  ↓
读取 citation_map.json: footnote_map = {}
  ↓
触发"救援"逻辑
  ↓
扫描 trace/*.json，找到 11 条检索命中
  ↓
合成 footnote_map = {"1": {...}, "2": {...}, ..., "11": {...}}
  ↓
write_citation_map_json() 写回磁盘
  ↓
返回给前端：citation_count = 11
```

**阶段 3：用户视角**
- 打开报告正文：看不到任何 [1]、[2] 脚注
- 顶部警告："本报告未引用法规依据索引"（`build_citation_map_section` 产出）
- 正文某句：提到了《数据安全法》《个人信息保护法》《网络安全法》
- 但被标注："待核验：缺少法规依据"（`apply_citation_policy` 产出）
- 打开引用面板：显示 11 条引用
- **矛盾**：正文说"未引用"，引用面板说"有 11 条"

**阶段 4：API 第二次读取**
```
GET /api/v1/reports/dc9b1db8/citations
  ↓
读取 citation_map.json: footnote_map = {"1": ..., "11": ...}  ← 被污染的数据
  ↓
不再触发"救援"逻辑（因为 footnote_map 非空）
  ↓
返回合成的 11 条
```

**数据污染链条**：

```
原始真相: footnote_map = {}
  ↓ API 第一次读取
合成数据写回磁盘
  ↓ 后续所有读取
基于合成数据工作
  ↓
原始问题被永久掩埋
```

---

## 四、断裂点 3 详解：跳不到具体条文

### 4.1 根因 RC-4：引用构造粒度不足

**代码位置**：`backend/common/citation/module_grounding.py`

```python
_MODULE_LEGAL_SOURCE_MAP = {
    "cn_flow": [
        {
            "title": "个人信息保护法",
            "source_id": "CN-LAW-001",
            "article": "",  # ❌ 空条号！
            ...
        },
        # ... 32 条全部 article=""
    ],
    "bcr": [
        {
            "title": "EU 2021/914",
            "article": "",  # ❌ 空条号！
            ...
        },
        # ... 16 条全部 article=""
    ],
}
```

**问题分析**：

1. **设计上就是法规级引用**
   - `article=""` 表示这些引用从设计上就没有条号
   - 不是"应该有条号但丢了"，而是"压根没打算定位到条文"
   - 这种引用应该被标记为 `citation_granularity: "source_level"`

2. **与条文级引用混在一起**
   - `_resolve_citation_target`（`output.py:200-210`）发现 `article=""` 时
   - 只能返回 `source_overview`，`can_jump=False`
   - 但 `failure_reason` 是 `article_missing`（听起来像缺陷）
   - 实际应该是 `source_level_by_design`（设计选择）

3. **实际影响**
   - `cn_flow`: 32/32 全部 `article_missing`
   - `bcr`: 16/16 全部 `article_missing`
   - 这 48 条引用**从设计上就不可跳转到条文**

---

### 4.2 根因 RC-5a：整部法规缺条文切分

**数据位置**：`resources/legal/registry/regulation_articles.jsonl`

**问题案例 1：CN-REG-004（数据出境安全评估办法）**

```jsonl
{"source_id": "CN-REG-004", "article_id": "CN-REG-004-001", "article_ref": "段落1", "content": "中央网络安全和信息化委员会办公室 © 版权所有"}
{"source_id": "CN-REG-004", "article_id": "CN-REG-004-002", "article_ref": "段落2", "content": "京ICP备1404 Produced By CMS 网站群内容管理系统"}
{"source_id": "CN-REG-004", "article_id": "CN-REG-004-003", "article_ref": "段落3", "content": "..."}
...
{"source_id": "CN-REG-004", "article_id": "CN-REG-004-009", "article_ref": "段落9", "content": "..."}
```

**问题分析**：

1. **整部法规没有正式条文**
   - 只有 9 行，`article_ref` 全是 `段落1..段落9`
   - 内容是网页正文 + 页脚噪声：
     * "© 版权所有"
     * "京ICP备1404"
     * "Produced By CMS 网站群内容管理系统"
     * 目录
     * 起草单位名单

2. **后果**
   - 任何引用"第5条"的请求
   - 在知识库中查找 `(CN-REG-004, "第五条")` 或 `(CN-REG-004, "5")`
   - 查不到 → `article_not_found`
   - `can_jump = false`

3. **契约矛盾**
   - `sources.csv` 中 `CN-REG-004` 的 `report_usage` 标注为"可直接引用条文号"
   - 但知识库中**一条正式条文都没有**
   - 这是契约与数据的直接矛盾

**问题案例 2-4：同类问题**

- `CN-SUP-003`（个人金融信息保护技术规范）：只有"段落n"，内容是目录和起草单位名单
- `CN-SUP-004`（个人信息安全规范）：同上
- `CN-LAW-004`：0 行（完全未入库）

---

### 4.3 根因 RC-5b：条文重复标记

**数据位置**：`resources/legal/registry/regulation_articles.jsonl`

**全库统计**：1,672 行中有 34 个 `(source_id, article_no)` 重复键

**典型案例：CN-LAW-003（个人信息保护法）第十七条**

```jsonl
{"source_id": "CN-LAW-003", "article_id": "CN-LAW-003-017", "article_ref": "第十七条", "content": "第十七条 个人信息处理者在处理个人信息前，应当以显著方式..."}

{"source_id": "CN-LAW-003", "article_id": "CN-LAW-003-029", "article_ref": "第十七条", "content": "第十七条第一款规定的事项外，还应当向个人告知处理敏感个人信息的必要性..."}
```

**问题分析**：

1. **第二行实际是第三十条**
   - 第三十条原文："处理敏感个人信息的，除**本法第十七条第一款规定的事项外**，还应当..."
   - 抽取器截断了"处理敏感个人信息的，除本法"这部分
   - 剩下"第十七条第一款规定的事项外..."
   - 据此把它标记为"第十七条"

2. **可判定特征**
   - `article_id` 的序号：`CN-LAW-003-029`（029 表示第 29 个提取的条文）
   - `article_ref` 的条号：`第十七条`
   - **序号 029 ↔ 条号 第十七条，不一致** → 错误
   - **序号 017 ↔ 条号 第十七条，一致** → 正确

3. **同类错误**
   - CN-LAW-003: 第四十条（实为第三十八条的条文项）、第三条（实为第五十三条）
   - CN-LAW-001: 第二十三/二十五/二十六/二十七/二十八/二十九条
   - 共 34 对重复键

4. **后果**
   - 系统查询"第十七条"时找到 2 条记录
   - 不知道用哪条 → `article_not_unique`
   - `can_jump = false`

**`pipia` 模块的影响**：

- 574 条引用中有 28 条 `article_not_unique`
- 修复重复键后这 28 条可直接转为 `can_jump = true`
- 跳转率从 83% (476/574) 提升到 88% (504/574)

---

### 4.4 根因 RC-5c：source_url 从不回填

**代码位置**：`backend/common/citation/output.py:269-270`

```python
def normalize_citation_item(item: dict, ...) -> dict:
    # ❌ 只读 item 自己的 source_url 字段
    source_url = item.get("source_url")
    
    # ❌ 从不查 sources.csv 或 regulation_articles.jsonl 回填
    # 即使这两个文件有 URL，也不会用上
    
    return {
        ...
        "source_url": source_url,  # 恒为空
        ...
    }
```

**可用数据源**：

1. **`regulation_articles.jsonl`**
   - 1,672 行中有 399 行（23.9%）的 `source_url` 非空
   - 这是**条文级精确 URL**（直接定位到具体条文）

2. **`sources.csv`**
   - 69 行中有 19 行（27.5%）的 `url` 列非空
   - 这是**法规级 URL**（指向法规全文）

**问题分析**：

1. **上游从不写入**
   - `citation_builder`（构造引用时）不写 `source_url`
   - `module_grounding`（模块映射时）不写 `source_url`
   - 所以 `item.get("source_url")` 恒为空

2. **下游从不回填**
   - `normalize_citation_item` 只读不填
   - 明明 `regulation_articles.jsonl` 和 `sources.csv` 有数据
   - 就是不去查

3. **后果**
   - `source_url` 恒为空
   - `_is_safe_external_url(source_url)` 恒为 False
   - `available_actions` 永不包含 `open_official_source`
   - 前端"查看官方发布版本"按钮永不显示（`CitationArticleDrawer.tsx` 尾部条件渲染）

**全量统计**：

12 个抽样任务 × N 条引用 = **100% 的 `source_url` 为空**

这是唯一 100% 复现的缺陷。

---

### 4.5 断裂点 3 的实际表现

**以 `assessment/dc9b1db8` 的 11 条引用为例**（合成的）：

| citation_id | source_id | article_no | can_jump | failure_reason | 根因 |
|-------------|-----------|------------|----------|----------------|------|
| assessment-dc9b1db8-reg-1 | CN-REG-004 | 第1条 | false | article_not_found | RC-5a（法规未入库） |
| assessment-dc9b1db8-reg-2 | CN-REG-004 | 第2条 | false | article_not_found | RC-5a |
| assessment-dc9b1db8-reg-3 | CN-REG-004 | 第3条 | false | article_not_found | RC-5a |
| assessment-dc9b1db8-reg-4 | CN-REG-004 | 第4条 | false | article_not_found | RC-5a |
| assessment-dc9b1db8-reg-5 | CN-REG-004 | 第5条 | false | article_not_found | RC-5a |
| assessment-dc9b1db8-reg-6 | CN-REG-004 | 第6条 | false | article_not_found | RC-5a |
| assessment-dc9b1db8-reg-7 | CN-LAW-002 | 第20条 | **true** | - | ✓ 正常（少数幸存者） |
| assessment-dc9b1db8-reg-8 | CN-LAW-001 | 第31条 | **true** | - | ✓ 正常 |
| assessment-dc9b1db8-reg-9 | CN-SUP-003 | - | false | article_not_found | RC-5a（只有目录） |
| assessment-dc9b1db8-reg-10 | CN-LAW-003 | 第17条 | false | article_not_unique | RC-5b（重复键） |
| assessment-dc9b1db8-reg-11 | CN-SUP-004 | - | false | article_not_found | RC-5a |

**统计**：
- 总计 11 条（合成的，与正文无关）
- `can_jump = true`: 2 条（18.2%）
- `article_not_found`: 8 条（72.7%）— 主要是 CN-REG-004 未入库
- `article_not_unique`: 1 条（9.1%）— CN-LAW-003 第17条重复
- `source_url` 非空: 0 条（0%）— RC-5c 恒为空

**即使那 2 条能跳转的**：
- 跳到知识库页面 `/knowledge/laws/CN-LAW-002?article=20`
- 但：
  * 没有 `source_url` → 看不到"查看官方版本"按钮
  * 没有高亮引用片段 → 用户要自己翻找
  * 没有新规标签 → 看不出是新法还是旧法
  * 没有复制引用按钮 → 手动抄写

---

## 五、三个断裂点的叠加效应

### 5.1 典型案例流程图

```
┌─────────────────────────────────────────────────────────────────┐
│ 用户请求：生成 V0GatewayCo 的数据出境安全评估报告                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ LLM 生成                                                          │
│   - 可能正常输出 {{CIT-CN-EXPORT-ASSESSMENT-ART5-P01}}           │
│   - 也可能降级 fallback                                          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                    ┌───────┴───────┐
                    ↓               ↓
        ┌───────────────────┐   ┌───────────────────┐
        │ 路径 A: LLM 输出   │   │ 路径 B: fallback   │
        │ {{CIT-...}}        │   │ 降级逻辑          │
        └───────────────────┘   └───────────────────┘
                    ↓               ↓
        ┌───────────────────┐   ┌───────────────────┐
        │ 正则不匹配 (RC-2) │   │ 产出【依据：】    │
        │ 5段 vs 4段         │   │ (RC-1)            │
        └───────────────────┘   └───────────────────┘
                    ↓               ↓
        ┌───────────────────┐   ┌───────────────────┐
        │ 标记残留在正文     │   │ 未产生 [n] 脚注   │
        │ {{CIT-...}}        │   │                   │
        └───────────────────┘   └───────────────────┘
                    ↓               ↓
                    └───────┬───────┘
                            ↓
        ┌─────────────────────────────────────────┐
        │ 共同结果：                               │
        │ - 正文 0 个 [n] 脚注                     │
        │ - _global_numbering = {}                │
        │ - footnote_map =                      │
        └─────────────────────────────────────────┘
                            ↓
        ┌─────────────────────────────────────────┐
        │ 写入产物：                               │
        │ - 正文：无 [n]，有 4 处"待核验"标记      │
        │ - citation_map.json: footnote_map = {}  │
        └─────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 用户打开报告，点击"引用"标签                                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ API: GET /api/v1/reports/{task_id}/citations                     │
│   - 读取 citation_map.json                                       │
│   - footnote_map = {}                                            │
│   - 触发"救援"逻辑 (RC-3)                                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 扫描 trace/*.json                                                 │
│   - 找到 11 条 RAG 检索命中                                       │
│   - 合成 footnote_map = {"1": {...}, ..., "11": {...}}          │
│   - citation_id = assessment-{task}-reg-{n} (非标准格式)         │
│   - article_no 从自由文本切分（质量差）                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 查知识库 (RC-5)                                                   │
│   - CN-REG-004 第1-6条: article_not_found (未入库)               │
│   - CN-LAW-002 第20条: ✓ 找到                                    │
│   - CN-LAW-001 第31条: ✓ 找到                                    │
│   - CN-SUP-003: article_not_found (只有目录)                     │
│   - CN-LAW-003 第17条: article_not_unique (重复键)               │
│   - CN-SUP-004: article_not_found                                │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 规范化 (RC-5c)                                                    │
│   - source_url 恒为空 (不回填)                                   │
│   - can_jump: 2/11 = 18.2%                                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 回写磁盘 (RC-3)                                                   │
│   - write_citation_map_json() 覆盖原文件                         │
│   - 污染事实基线                                                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 返回前端                                                          │
│   - citation_count = 11                                          │
│   - can_jump_count = 2                                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 用户视角：                                                        │
│   ✗ 正文：无任何 [n] 脚注                                         │
│   ✗ 顶部：显示"本报告未引用法规依据索引"                           │
│   ✗ 正文某句：提到三部法律，标注"待核验：缺少法规依据"             │
│   ✗ 引用面板：显示 11 条引用                                      │
│   ✗ 点击引用：只有 2 条能跳转，9 条失败                            │
│   ✗ 即使能跳转：无官方链接、无高亮、无标签、无复制按钮            │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 矛盾现象解释

| 用户观察到的现象 | 背后的根因 | 涉及代码位置 |
|----------------|-----------|-------------|
| **现象 1**：正文顶部写"本报告未引用法规依据索引" | RC-1: fallback 路径永不产脚注 → `footnote_map = {}` → `build_citation_map_section` 判断为空 | `output.py:build_citation_map_section` |
| **现象 2**：引用面板同时显示 7 条或 11 条引用 | RC-3: API 读取时从 trace 检索记录合成并回写 | `citations.py:217-238` |
| **现象 3**：正文提到三部法律却标"待核验：缺少法规依据" | RC-1: `[n]` 不被 `apply_citation_policy` 视作有效依据 + fallback 产出【依据：】后仍触发校验 | `postprocess.py:apply_citation_policy` |
| **现象 4**：点击引用后大部分显示"无法跳转" | RC-5a: 法规未做条文切分（CN-REG-004 只有网页噪声） | `regulation_articles.jsonl` 数据质量 |
| **现象 5**：部分引用显示"条文不唯一" | RC-5b: 续行被误标为被引用条号（34 对重复键） | `regulation_articles.jsonl` 数据质量 |
| **现象 6**：所有引用都没有"查看官方版本"按钮 | RC-5c: `source_url` 从不回填 | `output.py:normalize_citation_item` |
| **现象 7**：正文里看到 `{{CIT-CN-EXPORT-ASSESSMENT-...}}` 残留 | RC-2: 正则不匹配（5 段 vs 4 段） | `registry.py` / `postprocess.py` 正则定义 |

### 5.3 为什么问题能长期存在

1. **三条链路互不相通，断了谁也不知道**
   ```
   生成期（convert_citation_markers / ensure_paragraph_citations）
         ↓ 断开
   写入期（build_citation_map_section / write_citation_map_json）
         ↓ 断开
   读取期（get_report_citations）
   ```
   每一层各管各的，中间某一层断了，其他层还在工作，看起来"正常"。

2. **API 的"救援"逻辑掩盖了真相**
   - 本来应该报告 `footnote_map = {}`（暴露问题）
   - 结果伪造了一个看起来正常的映射文件（掩盖问题）
   - 后续所有读取都基于伪造的数据
   - 原始问题（生成期断链）被永久埋住

3. **数据质量问题没有门禁**
   - 网页噪声能入库（版权页、ICP 备案号、CMS 页脚）
   - 条文重复能存在（34 对重复键，半年以上）
   - `source_url` 全空也没人管（0%，100% 复现）
   - 没有 CI 检查这些基础不变式

4. **正则错误被正常案例掩盖**
   - 只有 0.16% 的 ID 能匹配（91/55727）
   - 但恰好 `PIPL`、`DSL`、`CSL` 这几个高频法规能匹配
   - 所以部分模块（`dpia`、`pipia`）看起来"正常"
   - 掩盖了 99.84% 的 ID 不匹配的事实

5. **两套语法互斥，fallback 成为实际主路径**
   - 设计上：LLM 正常输出 → 路径 A（`convert_citation_markers`）
   - 实际上：LLM 经常降级 → 路径 B（`ensure_paragraph_citations`）
   - 路径 B 永不产生脚注，但它是**高频路径**
   - 路径 A 正则又不匹配，所以**两条路都断**

---

## 六、完整数据流追踪

### 6.1 生成期：从 LLM 到正文文件

```python
# 1. LLM 生成原始文本
# backend/domains/cn/security_assessment/orchestrator.py
raw_text = await llm_client.generate(...)
# 输出示例：
# "用户应当遵守{{CIT-CN-EXPORT-ASSESSMENT-ART5-P01}}的规定..."

# 2. 经过后处理
# backend/domains/cn/security_assessment/chapter_generator.py:419
if citation_registry is not None:
    text = convert_citation_markers(raw_text, citation_registry)
else:
    text = ensure_paragraph_citations(raw_text, citations)

# 3a. 路径 A：convert_citation_markers
# backend/common/llm/postprocess.py:274
def convert_citation_markers(text, registry):
    # 正则匹配 {{CIT-...}}
    matches = _CIT_MARKER_RE.findall(text)
    # ❌ 问题：正则只匹配 4 段，5 段的 ID 匹配失败
    # 结果：55636/55727 的 marker 残留原样
    
    for match in matches:
        # 为匹配到的 marker 分配脚注号
        footnote_num = registry.assign_footnote_number(match)
        # 替换为 [n]
        text = text.replace(f"{{{{{match}}}}}", f"[{footnote_num}]")
    
    return text

# 3b. 路径 B：ensure_paragraph_citations → apply_citation_policy
# backend/common/llm/postprocess.py:191
def apply_citation_policy(text, allowed_citations, max_items):
    # 查找【依据：...】标记
    # 检查法律规则/风险判断句是否有依据
    # ❌ 问题：[n] 不被视作有效依据
    # 结果：有 [n] 的句子仍被追加"待核验"
    
    if sentence_needs_citation and not has_valid_marker:
        text += "【待核验：缺少法规依据】"
    
    return text

# 4. 写入正文文件
# backend/common/render/report_writer.py
report_path.write_text(text)
# 结果：
# - 路径 A: 残留 {{CIT-...}} 或少量 [n]
# - 路径 B: 【依据：某某法 第X条】或【待核验】
```

### 6.2 写入期：从内存到 citation_map.json

```python
# 1. 获取脚注映射
# backend/common/citation/output.py
footnote_map = registry.get_footnote_map()
# ❌ 问题：若路径 B 或正则不匹配，_global_numbering = {}
# 结果：footnote_map = {}

# 2. 构建引用映射章节
# backend/common/citation/output.py:build_citation_map_section
if not footnote_map:
    return "（本报告未引用法规依据索引）"  # ← 现象 1
else:
    # 构建引用列表
    return citation_section

# 3. 构建详细引用信息
# backend/common/citation/output.py:_build_all_citation_items
all_items = []
for footnote_num, citation_id in footnote_map.items():
    # 查知识库获取条文详情
    item = _resolve_citation_target(citation_id)
    # ❌ 问题：source_url 恒为空 (RC-5c)
    # ❌ 问题：article_not_found / article_not_unique (RC-5a/5b)
    all_items.append(item)

# 4. 写入 JSON 文件
# backend/common/citation/output.py:write_citation_map_json
citation_map_path.write_text(json.dumps({
    "footnote_map": footnote_map,  # {} 或有内容
    "all_items": all_items,
    ...
}))
```

### 6.3 读取期：从文件到 API 响应

```python
# 1. API 端点
# backend/api/v1/endpoints/citations.py:get_report_citations
@router.get("/reports/{task_id}/citations")
async def get_report_citations(task_id: str):
    # 读取 citation_map.json
    citation_map_path = output_dir / "citation_map.json"
    data = json.loads(citation_map_path.read_text())
    footnote_map_raw = data.get("footnote_map", {})
    
    # ❌ 关键问题：footnote_map 为空时启动"救援"
    if not footnote_map_raw and target_module:
        # 2. 读取检索 trace
        recovery_payload = _read_recovery_payload(target_module, task_id)
        
        # 3. 从检索命中合成引用
        synthesized_footnote_map, synthesized_all_items = \
            synthesize_citation_map(recovery_payload, ...)
        
        if synthesized_footnote_map:
            footnote_map_raw = synthesized_footnote_map
            
            # ❌ 回写磁盘，污染事实基线
            write_citation_map_json(...)
    
    # 4. 规范化并返回
    return CitationMapResponse(
        footnote_map=footnote_map_raw,
        citation_count=len(footnote_map_raw),
        ...
    )

# _read_recovery_payload 实现
# backend/api/v1/endpoints/citations.py:104-112
def _read_recovery_payload(module, task_id):
    citations = []
    trace_dir = outputs_dir / module / task_id / "trace"
    
    for trace_file in trace_dir.glob("*.json"):
        trace_data = json.loads(trace_file.read_text())
        
        # ❌ 把"检索到的文档"当成"正文引用"
        if "detail" in trace_data and "hits" in trace_data["detail"]:
            citations.extend(trace_data["detail"]["hits"])
    
    return {"citations": citations}

# synthesize_citation_map 实现
# backend/common/citation/output.py:421-424
def synthesize_citation_map(recovery_payload, module, task_id):
    citations = recovery_payload.get("citations", [])
    footnote_map = {}
    
    # ❌ 按列表顺序编号 1..N
    for idx, citation in enumerate(citations, 1):
        # ❌ 非标准 citation_id 格式
        citation_id = f"{module}-{task_id}-reg-{idx}"
        
        footnote_map[str(idx)] = {
            "citation_id": citation_id,
            "source_id": citation.get("source_id"),
            # ❌ 从自由文本切分，质量差
            "article_no": _citation_article_from_source(citation),
            ...
        }
    
    return footnote_map, all_items
```

### 6.4 前端渲染：从 API 到用户界面

```python
# 1. Markdown 渲染器
# frontend/src/components/citation/CitationMarkdownRenderer.tsx:184-197
function CitationMarkdownRenderer({content, citations}) {
    // 查找正文中的 [n] 标记
    const footnoteMatches = content.match(/\[(\d+)\]/g);
    
    // ❌ 问题：正文里没有 [n]，这段代码永不触发
    if (footnoteMatches) {
        // 渲染 Popover + 可点击跳转
        return <span onClick={() => openDrawer(n)}>...</span>
    }
    
    // 否则原样渲染
    return <div dangerouslySetInnerHTML={{__html: content}} />
}

# 2. 引用面板
# frontend/src/components/report/ResourcePanel.tsx:229
function ResourcePanel({taskId}) {
    // 获取引用列表
    const {data: citations} = useQuery(
        ['citations', taskId],
        () => fetch(`/api/v1/reports/${taskId}/citations`)
    );
    
    // 显示引用数量和列表
    // ❌ 问题：显示的是合成的数据，与正文无关
    return (
        <Tab label={`引用 (${citations.citation_count})`}>
            {citations.items.map(item => (
                <CitationCard 
                    citation={item}
                    onClick={() => openDrawer(item)}
                />
            ))}
        </Tab>
    )
}

# 3. 引用详情抽屉
# frontend/src/components/citation/CitationArticleDrawer.tsx
function CitationArticleDrawer({citation}) {
    // ❌ 问题：can_jump 为 false 时只显示错误信息
    if (!citation.can_jump) {
        return <Alert severity="error">{citation.failure_reason}</Alert>
    }
    
    // 即使能跳转
    const knowledgeUrl = `/knowledge/laws/${citation.source_id}?article=${citation.article_no}`;
    
    return (
        <>
            <Typography>{citation.article_content}</Typography>
            <Button onClick={() => window.open(knowledgeUrl)}>
                查看知识库全文
            </Button>
            {/* ❌ 问题：以下功能全部缺失 */}
            {/* 1. 无"查看官方版本"按钮（source_url 恒为空） */}
            {/* 2. 无引用片段高亮（没有传 quote 参数） */}
            {/* 3. 无"复制引用"按钮 */}
            {/* 4. 无"新规标签"（没有 effective_date 字段） */}
        </>
    )
}
```

---

## 七、总结与诊断结论

### 7.1 问题本质

引用跳转功能的失效，**不是单一缺陷，而是三个断裂点叠加的系统性失败**：

1. **生成期断链**（RC-1 + RC-2）
   - 两套互斥语法 + 正则不匹配
   - 导致正文无脚注标记
   - 覆盖率：99.84% 的 citation_id 无法匹配

2. **读取期造假**（RC-3）
   - API 从检索记录合成引用
   - 并回写磁盘污染基线
   - 掩盖了生成期的真实问题

3. **数据层缺失**（RC-4 + RC-5）
   - 法规级引用无条号设计（48 条）
   - 整部法规未做条文切分（CN-REG-004 等）
   - 34 对重复条号键
   - source_url 100% 缺失

### 7.2 影响范围

**模块覆盖**：
- `assessment`: 2/11 能跳转（18.2%）
- `pipia`: 476/574 能跳转（83.0%）
- `cn_flow`: 0/32 能跳转（0%，设计上无条号）
- `bcr`: 0/16 能跳转（0%，设计上无条号）

**用户体验矛盾**：
- 正文说"未引用"，面板说"有 N 条引用"
- 点击引用多数失败
- 即使成功跳转也缺少关键功能（官方链接、高亮、复制）

### 7.3 为什么能长期存在

1. **三层各自工作**：生成/写入/读取三层互不相通，某一层断了其他层仍在运行
2. **API 救援掩盖**：合成逻辑让系统"看起来正常"，实际埋住了原始问题
3. **正常案例掩护**：0.16% 能匹配的 ID 恰好是高频法规，掩盖了 99.84% 的失败
4. **无数据门禁**：网页噪声、重复键、全空 URL 都能入库且长期存在
5. **Fallback 成主路径**：设计上的降级路径实际成为高频路径，且永不产生脚注

### 7.4 修复优先级

按 `DataComplyFlow_引用跳转闭环治理方案_20260806.md` 的建议：

**P0（先决条件）**：
- RC-2：修正 marker 正则（扩展到 5 段或重构缩写生成）
- RC-3：移除 API 合成逻辑，违反时返回空集合

**P1（核心功能）**：
- RC-5a：补全 CN-REG-004 等法规的条文切分
- RC-5b：清理 34 对重复条号键
- RC-1：统一引用语法，废弃双语法并存

**P2（增强功能）**：
- RC-5c：回填 source_url（399/1672 条文级 + 19/69 法规级）
- RC-4：为法规级引用显式标注 `citation_granularity: "source_level"`

**P3（体验优化）**：
- 前端 Drawer 增加复制引用、高亮片段、新规标签等功能

### 7.5 下一步

1. **立即验证**：运行 `scripts/check_citation_integrity.py`（如果存在）检查现有数据完整性
2. **选择修复路线**：P0 → P1 → P2 的顺序，还是先修 P0 + RC-5a 让部分模块先通
3. **建立门禁**：
   - marker 正则与 citation_id 生成的一致性测试
   - regulation_articles.jsonl 的唯一键约束
   - source_url 非空率监控
   - API 禁止回写磁盘的单元测试

4. **参考治理方案**：
   - 完整实施计划见 `/Users/oujiazhan/Desktop/实验室/社团/代码/ai4law/status/todo/DataComplyFlow_引用跳转闭环治理方案_20260806.md`
   - 7 个阶段、23 个任务、预估 8–12 个工作日

---

## 附录：关键代码位置速查

| 问题 | 文件 | 行数 | 说明 |
|------|------|------|------|
| RC-1 双语法分支 | `backend/domains/cn/security_assessment/chapter_generator.py` | 419-421 | `if citation_registry` 分支点 |
| RC-2 正则定义 | `backend/common/citation/registry.py` | 8 | `_CIT_MARKER_RE` 只匹配 4 段 |
| RC-2 正则定义 | `backend/common/llm/postprocess.py` | 10 | 同上（重复定义） |
| RC-2 ID 生成 | `backend/common/citation/id_generator.py` | 42 | `generate_citation_id` 用 `LAW_ABBREVIATIONS` |
| RC-3 API 合成 | `backend/api/v1/endpoints/citations.py` | 217-238 | `if not footnote_map_raw` 启动救援 |
| RC-3 trace 读取 | `backend/api/v1/endpoints/citations.py` | 104-112 | `_read_recovery_payload` |
| RC-3 合成逻辑 | `backend/common/citation/output.py` | 421-424 | `synthesize_citation_map` |
| RC-4 法规级映射 | `backend/common/citation/module_grounding.py` | - | `_MODULE_LEGAL_SOURCE_MAP` |
| RC-5a 数据源 | `resources/legal/registry/regulation_articles.jsonl` | - | 1672 行，34 对重复键 |
| RC-5c URL 回填 | `backend/common/citation/output.py` | 269-270 | `normalize_citation_item` |
| 前端渲染器 | `frontend/src/components/citation/CitationMarkdownRenderer.tsx` | 184-197 | 查找 `[n]` 标记 |
| 前端 Drawer | `frontend/src/components/citation/CitationArticleDrawer.tsx` | - | 跳转逻辑 |

---

*本文档主体基于代码基线 `1a3d0dd`（2026-08-07）编制，用于保留原始问题证据；当前落实状态以文首第 〇 节和后续 `status/check/` 验收文件为准。详细修复方案见配套治理方案文档。*
