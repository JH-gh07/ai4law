
# v5 改进计划：RAG 知识库开放与知识库中心打通

## 背景

当前系统存在一个结构性断层：

- **后端 RAG 引擎**（`backend/common/rag/retriever.py`）持有完整的 1011 条法规条文向量索引，具备混合检索能力
- **后端 Knowledge API**（`backend/api/knowledge.py`）只操作 sources.csv（15条元数据），完全没有触及 RAG
- **React 前端知识库中心**（`frontend/src/pages/EvidenceCenterPage.tsx`）只展示 CSV 元数据，用户看不到任何法规条文内容

> **注**：项目同时存在 Streamlit 原型（`app_streamlit/`）和 React 前端（`frontend/`）两套界面。
> 主前端是 React，本次改动只针对 React 前端链路。Streamlit 原型暂不动。

---

## 当前知识库中心真实链路

```
用户浏览器
  → React: /evidence → EvidenceCenterPage.tsx
    → knowledge-api.ts
        fetchKnowledgeIndex()      → GET /api/v1/knowledge/index    → 读 sources.csv（15条）
        fetchKnowledgeSourceDetail → GET /api/v1/knowledge/sources/{id}
        fetchKnowledgeCaseDetail   → GET /api/v1/knowledge/cases/{id}
        fetchKnowledgeCitation     → GET /api/v1/knowledge/citation?query=
```

`retrieve_regulations()`（真正的 RAG 检索，操作 1011 条条文）没有任何对外 API，
`knowledge-api.ts` 里也没有对应的调用函数。

---

## 改动目标

**暴露 RAG 检索能力，在知识库中心新增"条文检索"tab，让用户能真正搜索和浏览 1011 条法规条文。**

---

## 涉及文件与改动内容（按实施顺序）

### Step 1 — `backend/schemas/knowledge.py`

新增两个 Schema：

```python
class KnowledgeSearchItem(BaseModel):
    id: str
    title: str
    article: str
    content: str
    jurisdiction: str = ""
    path: str = ""
    doc_type: str = ""
    usage_priority: str = ""
    source_url: str = ""
    keywords: list[str] = Field(default_factory=list)

class KnowledgeSearchResponse(BaseModel):
    query: str
    jurisdiction: str | None = None
    path: str | None = None
    mode: str = "hybrid"
    top_k: int = 8
    hit_count: int
    items: list[KnowledgeSearchItem] = Field(default_factory=list)
```

---

### Step 2 — `backend/api/knowledge.py`

新增端点：

```
GET /api/v1/knowledge/search
  ?q=标准合同备案流程
  &jurisdiction=cn        （可选，cn / eu / us）
  &path=scc               （可选，assessment / scc / all）
  &top_k=8                （可选，默认 8，上限 20）
  &mode=hybrid            （可选，hybrid / vector / lexical）
```

实现：调用 `retrieve_regulations()`，将返回的 `list[RegulationDoc]` 序列化为 `KnowledgeSearchResponse`。

---

### Step 3 — `frontend/src/lib/knowledge-api.ts`

新增类型与函数：

```typescript
export type KnowledgeSearchItem = { id, title, article, content, jurisdiction, path, doc_type, usage_priority, source_url, keywords }
export type KnowledgeSearchData = { query, jurisdiction, path, mode, top_k, hit_count, items }

export async function fetchKnowledgeSearch(params: {
  q: string;
  jurisdiction?: string;
  path?: string;
  top_k?: number;
  mode?: string;
}): Promise<KnowledgeSearchData>
```

---

### Step 4 — `frontend/src/pages/EvidenceCenterPage.tsx`

- `KnowledgeTab` 类型新增 `"articles"` 选项
- 顶部 tab chips 增加"条文检索"入口
- 新增 articles tab 状态：`articlesQuery`、`articlesJurisdiction`、`articlesPath`、`articlesResults`、`articlesLoading`
- 左栏：搜索框 + jurisdiction/path 筛选 chip + 检索结果列表（法规名 + 条款号 + 内容摘要）
- 右栏（detail 区）：选中条文的完整内容 + 来源链接
- 触发时机：输入框 debounce 300ms 后自动调用 `fetchKnowledgeSearch()`

---

## 涉及文件汇总

| 文件 | 改动类型 |
|------|---------|
| `backend/schemas/knowledge.py` | 新增 Schema |
| `backend/api/knowledge.py` | 新增 API 端点 |
| `frontend/src/lib/knowledge-api.ts` | 新增类型 + 函数 |
| `frontend/src/pages/EvidenceCenterPage.tsx` | 新增 tab |

不涉及数据库、报告渲染、任何业务模块（assessment/scc 等），改动完全隔离。

---

## P2 记录（暂不落实）

| 方向 | 说明 |
|------|------|
| HashingEmbedder → 语义向量 | 升级后检索召回率有根本性提升，但需重建全量索引，且依赖 Embedding API 可用性，暂缓 |
| 得理法搜双路并行 | 改为每次并行双路检索再归并，但需引入异步重构，暂缓 |
| app_streamlit 知识库中心同步更新 | 非主链路，待 React 侧稳定后再同步 |
