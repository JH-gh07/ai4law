# 引用跳转流程与知识库入库现状

> 编制日期：2026-08-08
> 代码基线：`f800e54`
> 范围：前端路由 → CitationMarkdownRenderer → CitationArticleDrawer → LawViewerPage；后端 output.py → knowledge_index.py；knowledge base 入库现状

---

## 一、知识库页面 URL 结构（已确认）

用户手动点击可到达的法规条文页面，与引用跳转的目标页面是**同一个页面**：

```
/knowledge/laws/:sourceId            → 法规概览页（无具体条文）
/knowledge/laws/:sourceId?article=31 → 跳转到第31条并高亮显示
```

路由定义在 `frontend/src/App.tsx:272`：
```tsx
<Route path="/knowledge/laws/:sourceId" element={<LawViewerPage />} />
```

`LawViewerPage.tsx` 读取 `?article=` 参数，调用后端 API 取条文内容，并用 `ref.scrollIntoView` 滚动定位。**这就是用户说的"知识库里能靠点击到达的那个页面"。**

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

| 优先级 | 问题 | 影响范围 | 修复难度 |
|--------|------|---------|---------|
| **P0** | RC-2：Marker 正则不匹配（5段vs4段）| 所有模块的 [n] 脚注 | 低（改一个正则） |
| **P1** | CN-REG-004：未入库（仅有新闻稿噪声） | assessment 模块 60%+ 引用 | 中（重新提取20条条文） |
| **P1** | 路径 B 硬编码 can_jump=false | 所有 【依据：】标记 | 中（需前端改动 + 后端 API 支持条号验证） |
| **P2** | 补充地区法规（日韩/新加坡/越南等）未入库 | 扩展地区功能 | 高（每部法规需手工提取条文） |

**最小可见修复**：只修 P0（正则），assessment 模块的`CN-LAW-001`、`CN-LAW-002`、`CN-LAW-003` 引用就能出现 [n] 并跳转，因为这三部法规数据质量好（54-85条，无重复键）。
