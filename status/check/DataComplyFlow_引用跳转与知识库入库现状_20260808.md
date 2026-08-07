# 引用跳转流程与知识库入库现状

> 编制日期：2026-08-08
> 代码基线：`f800e54`
> 范围：前端路由 → CitationMarkdownRenderer → CitationArticleDrawer → LawViewerPage；后端 output.py → knowledge_index.py；knowledge base 入库现状
> **文档状态：P0–P2 已于 2026-08-08 当次会话全部修复，已归档至 `status/check/`。**

---

## 修复记录（2026-08-08 当次会话）

| 优先级 | 问题 | 修复提交 | 状态 |
|--------|------|----------|------|
| P0 | RC-2：Marker 正则 5 段 vs 4 段不匹配 | `f81bfaf` | ✅ 已修复 |
| P1a | CN-REG-004 条文全为网页噪声（9 条） | `979d714` | ✅ 已修复（20 条正式条文） |
| P1b | 路径 B `buildResolvedCitation` 硬编码 `can_jump=false` | `f2e0019` | ✅ 已修复（改为 async + 后端验证） |
| P2 | 地区法规（日韩/新加坡/越南/港澳台/马来西亚）全未入库 | `bc872c0` | ✅ 已修复（+51 个来源，+1347 条条文） |

**待完成：端到端验收**（路径 A/B 实际跳转、CN-REG-004 API 复验、P2 新入库条文抽查），验收报告另行记录于 `status/check/`。

---

## 一、知识库页面 URL 结构与架构（修正版）

> ⚠️ **初版结论有误，已修正。** 原文称"用户手动浏览的知识库页面与引用跳转目标是同一个页面"——经过代码核查，**两者是不同页面**，关系如下。

### 1.1 实际知识库浏览界面：EvidenceCenterPage（`/evidence`）

用户日常使用的"知识库"是 `EvidenceCenterPage`，路由为 `/evidence`（`frontend/src/pages/EvidenceCenterPage.tsx`）：

- 展示所有69个法规来源的目录，支持关键词搜索、筛选器（法域/类别/用途）
- 点击任意法律条目，**URL 永远不变**，始终停在 `/evidence`
- 切换法律靠的是 React state，而非路由跳转：

```tsx
// EvidenceCenterPage.tsx:221
const [selectedSourceId, setSelectedSourceId] = useState("");

// 第575行 — 点击法律条目：
<article onClick={() => setSelectedSourceId(sourceId)}>
```

右侧预览面板随 state 变化刷新，没有任何 `navigate()` 调用，也不生成任何含 `sourceId` 的 URL。

### 1.2 引用跳转目标：LawViewerPage（`/knowledge/laws/:sourceId`）

这是一个**单独的深链接页面**，不是知识库浏览界面，路由定义在 `frontend/src/App.tsx:272`：

```tsx
<Route path="/knowledge/laws/:sourceId" element={<LawViewerPage />} />
```

支持的 URL 格式：

```
/knowledge/laws/:sourceId            → 显示该法规的元数据概览（无条文列表）
/knowledge/laws/:sourceId?article=31 → 定位到第31条并高亮显示
```

`LawViewerPage.tsx` 从 URL 读取 `sourceId`（`useParams`）和 `article`（`useSearchParams`），调用后端 API 取条文内容，用 `ref.scrollIntoView` 滚动定位。页面头部有"← 返回"按钮（`navigate(-1)`），是独立的单法规视图，而非目录式浏览器。

### 1.3 两页面关系

| | EvidenceCenterPage（`/evidence`）| LawViewerPage（`/knowledge/laws/:sourceId`）|
|---|---|---|
| 定位 | 知识库目录浏览器 | 单法规深链接视图 |
| URL 是否变化 | **不变**（React state 控制） | **变化**（URL 驱动） |
| 条文列表 | 右侧预览面板（内嵌） | 仅显示目标条文上下文各1条 |
| 到达方式 | 导航栏点击知识库 | 引用跳转 / EvidenceCenterPage 内的条文链接 |
| 用户熟悉度 | 日常使用 | 较少主动访问 |

**EvidenceCenterPage 自身也包含指向 LawViewerPage 的链接**（`EvidenceCenterPage.tsx:754`）：

```tsx
href={`/knowledge/laws/${sourceId}?article=${articleNo}`}
```

说明两者是"目录→详情"的配合关系：`/evidence` 是入口，`/knowledge/laws/:sourceId` 是从特定条文入口打开的精准视图。

### 1.4 引用跳转落地位置

`CitationArticleDrawer` 里"在知识库中继续阅读"调用的是：

```tsx
navigate(`/knowledge/laws/${sourceId}?article=${articleNo}`)
```

用户点击后**离开当前工作台，进入 LawViewerPage**，而非熟悉的 `/evidence` 知识库浏览界面。从功能上看这是正确的（确实定位到了具体条文），但 UX 落点与用户预期有偏差。

若希望跳转后落地在 `/evidence`（保持知识库浏览上下文），需要给 `/evidence` 加 query param 支持（如 `?source=CN-LAW-001&article=31`）并在 `EvidenceCenterPage` 里读取初始化 state，**当前代码未实现**。

---

## 二、完整跳转流程

### 2.1 两条触发路径

报告正文里存在两种引用标记，走完全不同的路径：

| 标记形式 | 例子 | 谁处理 | 最终能否跳到具体条文 |
|---------|------|--------|---------------------|
| `[n]` 脚注 | `[1]` `[2]` | 后端 CitationRegistry → API → 前端 | **能**（条件：后端 resolution_type = exact_article） |
| `【依据：...】` | `【依据：个人信息保护法 第31条】` | 前端 fetchKnowledgeCitation | **不能**（前端只能定位到法规来源，不验证条号） |

### 2.2 路径 A：[n] 脚注全流程

```
生成期（chapter_generator.py）
    LLM 输出 {{CIT-CN-LAW-003-ART31-P01}}
    ↓ convert_citation_markers() 正则匹配
    ↓ CitationRegistry.assign_footnote_number()
    → 正文出现 [1]，citation_map.json 写入 footnote_map

API 读取期（citations.py）
    GET /api/v1/reports/{task_id}/citations
    → 读 citation_map.json 的 footnote_map
    → 调 output._resolve_citation_target()
    → 返回 CitationDetail（含 resolution_type / knowledge_url / can_jump）

前端渲染（CitationMarkdownRenderer.tsx:186-204）
    发现 [1] → 查 citationMap["1"]
    → 渲染为可点击的 <CitationPopover>

用户点击（CitationArticleDrawer.tsx）
    if resolution_type === "exact_article":
        fetchArticleDetail(source_id, article_no)
        → 展示条文内容（上文 / 当前条 / 下文）
        → footer 显示 "在知识库中继续阅读" 按钮
              ↓ onClick
              navigate(`/knowledge/laws/${sourceId}?article=${articleNo}`)
              → 跳转到 LawViewerPage，定位到具体条文 ✓
```

### 2.3 路径 B：【依据：】全流程

```
生成期（chapter_generator.py fallback 路径）
    LLM 降级或走 ensure_paragraph_citations()
    → 正文出现 【依据：个人信息保护法 第31条】

前端渲染（CitationMarkdownRenderer.tsx:208-237）
    发现 【依据：...】 → 先查 citationMap（按标题模糊匹配）
    → 若没找到，调 fetchKnowledgeCitation(rawBasis)
         → GET /api/v1/knowledge/citation?query=个人信息保护法+第31条
         → 返回 matched: {source_id, title, authority_level, ...}
    → buildResolvedCitation()（CitationMarkdownRenderer.tsx:126-169）
         knowledge_url = `/knowledge/laws/${sourceId}`   ← 无 ?article= 参数
         can_jump = false                                ← 硬编码
         resolution.resolution_type = "source_overview" ← 固定

用户点击（CitationArticleDrawer.tsx:142-146）
    resolution_type ≠ "exact_article"
    → 显示 "当前为法规来源级定位"
    → footer 显示 "查看法规概览" 按钮
          ↓ onClick
          navigate(`/knowledge/laws/${sourceId}`)   ← 无条文定位
          → 跳转到 LawViewerPage，只显示法规概览，看不到第31条 ✗
```

---

## 三、resolution_type = exact_article 的判定条件

后端 `output.py:_resolve_citation_target()`（约第155-225行）：

```python
if source_known and article_no:
    match_count = _load_article_counts().get((source_id, article_no), 0)
    if match_count == 1:
        return {"resolution_type": "exact_article", ...}   # ← 只有这里 can_jump = true
    if match_count > 1:
        return {"resolution_type": "source_overview", "failure_reason": "article_not_unique"}
    # match_count == 0:
    return {"resolution_type": "source_overview", "failure_reason": "article_not_found"}

if source_known and not article_no:
    return {"resolution_type": "source_overview", "failure_reason": "article_missing"}
```

`match_count` 来自 `regulation_articles.jsonl` 里 `(source_id, article_ref)` 的出现次数。

**结论：要能跳转到具体条文，必须同时满足：**
1. source_id 在 `sources.csv` 中已登记
2. article_no 非空（即 LLM 或脚注系统提供了条号）
3. `regulation_articles.jsonl` 中该 `(source_id, article_no)` 恰好出现**1次**（不重不漏）

---

## 四、当前知识库条文数据状态

### 4.1 sources.csv 登记的 69 个来源，全部有条文索引

```
sources.csv 来源数：69
regulation_articles.jsonl 条文行数：1672
有条文索引的来源数：69（全覆盖，无空洞）
```

主要法规的条文数：

| source_id | 条文数 | 说明 |
|-----------|--------|------|
| CN-LAW-001 | 85 | 网络安全法（2025修正） |
| CN-LAW-003 | 73 | 个人信息保护法 |
| CN-REG-008 | 65 | 网络数据安全管理条例 |
| CN-LAW-002 | 54 | 数据安全法 |
| CN-REG-004 | **9** | ⚠️ 见下方 |

### 4.2 CN-REG-004 数据质量问题（数据出境安全评估办法）

> ✅ **已修复（commit `979d714`）**：已删除 9 条噪声记录，通过 `scripts/reingest_cn_reg_004.py` 写入 20 条正式条文。待完成：API 第 1/13/20/21 条复验 + 浏览器截图。以下为修复前原始诊断，供参考。

这是评估模块（assessment）最核心的法规依据，但其9条索引全是**网站新闻稿的段落**，不是法条原文：

```
段落1 | 国家互联网信息办公室公布《数据出境安全评估办法》_中央网络安全...
段落2 | 7月7日，国家互联网信息办公室公布《数据出境安全评估办法》…
段落5 | 《办法》规定了应当申报数据出境安全评估的情形，包括…
段落7 | 中央网络安全和信息化委员会办公室 © 版权所有 联系我们
段落8 | 京ICP备14042428号 京公网安备110401027
段落9 | Produced By CMS 网站群内容管理系统 publishdate:2024/01/05
```

- `article_ref` 为 "段落1"..."段落9"，不是 "第1条"..."第20条"
- 任何形如 `第X条` 的查询，`match_count = 0` → `article_not_found` → 无法跳转
- 该法规实际共 **20 条**，均未入库

---

## 五、知识库补充文档入库情况

### 5.1 现有入库状态

> ✅ **已修复（commit `bc872c0`）**：51 个来源已登记至 sources.csv，1347 条条文已写入 regulation_articles.jsonl。18 个 PDF 被跳过（越南 6 个图片型 PDF 为设计预期；另有 12 个韩国/香港指引因格式不匹配或文件缺失跳过）。以下为修复前原始诊断，供参考。

`resources/new/知识库补充/` 目录下存放了5个地区的法规文档（PDF），**全部未入库**：

| 地区 | 文件数 | 是否在 sources.csv | 是否有 regulation_articles.jsonl 条目 |
|------|--------|--------------------|-----------------------------------------|
| 日韩 | 子目录（日本/韩国各若干PDF）| ❌ 未登记 | ❌ 无 |
| 越南 | 6个PDF | ❌ 未登记 | ❌ 无 |
| 新加坡 | 6个PDF | ❌ 未登记 | ❌ 无 |
| 港澳台 | 子目录（港/澳/台各若干PDF）| ❌ 未登记 | ❌ 无 |
| 马来西亚 | 8个PDF | ❌ 未登记 | ❌ 无 |

这些文件处于"已收到、放进 resources/new/"的状态，但未经过入库流程（未在 sources.csv 登记 source_id，未提取条文写入 regulation_articles.jsonl）。

### 5.2 入库所需的步骤

完整入库需要：
1. **sources.csv**：为每部法规新增一行（分配 source_id，填写 jurisdiction/title/authority_level/url 等）
2. **regulation_articles.jsonl**：逐条提取条文，每条一行（source_id/article_ref/content/keywords）
3. **sources/snapshots/**（可选）：存放 HTML 快照用于条文预览
4. **同步 knowledge cache**：调 `POST /api/v1/knowledge/sync` 刷新缓存

---

## 六、跳转现状诊断

### 6.1 当前能跳转到具体条文的路径

- **只有路径 A**（`[n]` 脚注）能到达 `LawViewerPage?article=X`
- **路径 B**（`【依据：】`）只能到达法规概览页，无条文定位

### 6.2 路径 A 的前置障碍（导致正文大多没有 [n]）

参见 `DataComplyFlow_引用跳转机理详解_代码流程追踪_20260808.md` 的断裂点 1（RC-2 正则不匹配）：
- Marker 正则期望 4 段 ID，实际 ID 有 5 段
- 99.84% 的 citation_id 无法匹配 → 正文无脚注 → 跳转链未建立

### 6.3 路径 B 的结构性限制

`buildResolvedCitation()`（CitationMarkdownRenderer.tsx:126-169）：
- `can_jump` 硬编码为 `false`
- `resolution_type` 硬编码为 `"source_overview"`
- `knowledge_url` 没有 `?article=` 参数

要让路径 B 也能跳转到具体条文，需要在前端解析出 article_no 后，**通过后端 API 验证唯一性**，再填入 `?article=` 参数，当前代码未实现。

---

## 七、结论与优先级建议

**跳转到具体条文的核心路径已存在**（LawViewerPage + `?article=` 支持），但被两个主要因素阻断：

| 优先级 | 问题 | 影响范围 | 修复提交 | 状态 |
|--------|------|---------|----------|------|
| **P0** | RC-2：Marker 正则不匹配（5段vs4段）| 所有模块的 [n] 脚注 | `f81bfaf` | ✅ 已修复 |
| **P1a** | CN-REG-004：未入库（仅有新闻稿噪声） | assessment 模块 60%+ 引用 | `979d714` | ✅ 已修复（20条正式条文） |
| **P1b** | 路径 B 硬编码 can_jump=false | 所有 【依据：】标记 | `f2e0019` | ✅ 已修复（async + 后端验证） |
| **P2** | 补充地区法规（日韩/新加坡/越南等）未入库 | 扩展地区功能 | `bc872c0` | ✅ 已修复（+51来源，+1347条） |

**最小可见修复**：只修 P0（正则），assessment 模块的`CN-LAW-001`、`CN-LAW-002`、`CN-LAW-003` 引用就能出现 [n] 并跳转，因为这三部法规数据质量好（54-85条，无重复键）。
