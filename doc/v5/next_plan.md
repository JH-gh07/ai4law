# v5 下一步详细计划：RAG 检索质量提升

> 基于 status_report.md 实测结论制定  
> 时间：2026-04-12

---

## 问题优先级回顾

| # | 问题 | 严重 | 修复成本 |
|---|------|------|----------|
| 1 | 语义同义词无法召回（哈希向量） | 🔴 | 高（需换模型+重建索引） |
| 2 | 中英文跨语言检索失败 | 🔴 | 高（同上） |
| 3 | Off-topic 中文误召回 | 🟠 | 低（加词表即可） |
| 4 | 得理法搜永远不触发 | 🟠 | 低（改触发逻辑） |
| 5 | US 法域部分查询返回 0 | 🟠 | 低（补充中文法域 hints） |
| 6 | 欧盟 TIA/BCR 检索偏离 | 🟡 | 低（优化查询重写） |

---

## 实施分三个阶段

---

## Phase 1 — 规则层快速修复（不涉及模型，改动小）

**目标**：不换 Embedding，先把规则层的明显缺陷补上，提升当前系统可用性。

### 1-A. 扩充 `OFF_TOPIC_HINTS` 中文词表

**文件**：`backend/common/rag/retriever.py`

当前 `OFF_TOPIC_HINTS` 只有英文词（docker、nginx 等），完全没有中文非合规词。

补充内容：
```python
OFF_TOPIC_HINTS = (
    # 原有英文词
    "weather", "python", "docker", "mysql", "nginx",
    "laptop", "battery", "steak", "cake", "macbook",
    # 新增中文非合规领域词
    "违约金", "公司注册", "税务申报", "劳动合同", "社保",
    "知识产权", "专利", "商标", "著作权", "股权",
    "融资", "ipo", "上市", "财务报表", "审计",
    "刑事", "行政处罚", "诉讼", "仲裁", "律师费",
)
```

---

### 1-B. 补充 `JURISDICTION_STRONG_HINTS` 中文法域词

**文件**：`backend/common/rag/retriever.py`

当前 US 法域 hints 全是英文（"cpra"、"california"等），导致"消费者隐私权利**加州**"无法被识别为 US 查询，查询重写不生效，最终返回 0 条。

补充内容：
```python
JURISDICTION_STRONG_HINTS = {
    "cn": (
        # 原有
        "数据出境", "个人信息", "重要数据", "网信", "标准合同", "安全评估", "认证", "pipl",
        # 新增
        "网络安全法", "数据安全法", "个人信息保护法", "跨境流动", "CAC", "网信办",
    ),
    "eu": (
        # 原有
        "gdpr", "edpb", "bcr", "dpia", "tia", "article 35", "article 47",
        # 新增
        "欧盟", "欧洲", "GDPR", "数据保护官", "DPO", "标准合同条款", "充分性决定",
    ),
    "us": (
        # 原有
        "cpra", "ccpa", "california", "eo 14117", "covered person", "restricted transaction",
        # 新增
        "加州", "美国", "隐私权", "消费者隐私", "联邦", "DOJ", "敏感个人数据",
    ),
}
```

---

### 1-C. 重构得理法搜触发逻辑

**文件**：`backend/common/rag/retriever.py`

**当前问题**：触发条件 `len(docs) < min_local(3)` 只看数量，不看质量。哈希向量总能凑出 5 条低质量结果，得理法搜永远不触发。

**新逻辑**：改为双重条件触发——数量不足 **或** 最高分低于质量阈值：

```python
# 当前
if effective_legal_service and len(docs) < min_local:
    ...

# 改为
TOP_SCORE_THRESHOLD = 0.3   # 最高分低于此值认为质量不足

def _needs_external_search(docs: list[RegulationDoc], min_local: int) -> bool:
    if len(docs) < min_local:
        return True
    # 暂时通过 usage_priority 判断质量（P2 条目视为低质量）
    high_quality = [d for d in docs if d.usage_priority in ("P0", "P1")]
    return len(high_quality) == 0

if effective_legal_service and _needs_external_search(docs, min_local):
    ...
```

---

### 1-D. 优化欧盟路径查询重写

**文件**：`backend/common/rag/retriever.py`

当前 `PATH_STRONG_HINTS` 的 "review" 路径 hints 与 EU 法域条文标签不匹配，导致 BCR/TIA 相关查询偏离。

补充 eu 专项 path hints：
```python
PATH_STRONG_HINTS = {
    "assessment": ("安全评估", "assessment", "重要数据", "100万", "10万敏感"),
    "scc": ("标准合同", "认证", "scc", "备案", "个人信息出境", "standard contractual"),
    "review": ("合同审查", "条款", "协议", "合规审查", "review"),
    # 新增
    "bcr": ("binding corporate rules", "BCR", "约束性企业规则", "集团内部"),
    "tia": ("transfer impact assessment", "TIA", "传输影响评估", "补充措施"),
    "dpia": ("data protection impact", "DPIA", "数据保护影响评估", "高风险处理"),
}
```

---

## Phase 2 — 向量检索升级（核心工程）

**目标**：用真实语义 Embedding 替换哈希向量，从根本上解决同义词和跨语言召回问题。

### 2-A. 接入本地语义 Embedding 模型

**推荐模型**：`moka-ai/m3e-base`（中文优化，支持中英双语，MIT 协议，可本地运行）

**优点**：
- 无需 API Key，完全本地
- 专门针对中文语义优化，中英文双语支持
- 768 维，语义质量远超哈希向量
- 模型文件约 400MB，一次下载后缓存

**备选方案**：混元 Embedding API（已有 Key，无需额外成本，但依赖网络）

**新文件**：`backend/common/rag/semantic_embedder.py`

```python
class SemanticEmbedder:
    """基于 sentence-transformers 的语义 Embedding"""
    
    def __init__(self, model_name: str = "moka-ai/m3e-base"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    def embed(self, text: str) -> list[float]:
        return self.model.encode(text, normalize_embeddings=True).tolist()
    
    @staticmethod
    def similarity(v1: list[float], v2: list[float]) -> float:
        return sum(a * b for a, b in zip(v1, v2))
```

### 2-B. 重建向量索引

**文件**：`backend/common/rag/ingest.py`、`backend/common/rag/vector_store.py`

- 向量存储格式从稀疏 dict 改为 dense list（与 sentence-transformers 输出对齐）
- 索引文件路径加版本后缀区分：`regulation_index_v3.json`
- 提供 `scripts/build_rag_vector_index.py` 一键重建脚本

### 2-C. Settings 新增 Embedding 选项

**文件**：`backend/core/settings.py`

```python
rag_embedding_backend: str = "hashing"   # "hashing" | "semantic" | "hunyuan"
rag_semantic_model: str = "moka-ai/m3e-base"
```

运行时根据配置选择 Embedder，保持向后兼容（默认仍用 hashing，手动切换）。

---

## Phase 3 — 检索架构优化

**目标**：得理法搜真正并行发力，检索链路更健壮。

### 3-A. 得理法搜改并行双路

**文件**：`backend/common/rag/retriever.py`

当前串行：本地检索 → 质量不足时串行调得理。  
改为并行：本地检索和得理法搜同时发起，结果归并去重排序。

```python
# 伪代码
async def retrieve_regulations_async(query, ...):
    local_task = asyncio.create_task(_local_retrieve(query, ...))
    deli_task  = asyncio.create_task(_deli_retrieve(query, ...))
    local_docs, deli_docs = await asyncio.gather(local_task, deli_task)
    return _merge_and_dedup(local_docs, deli_docs, top_k=top_k)
```

对同步调用场景保持兼容（用 `asyncio.run` 或 ThreadPoolExecutor 包装）。

### 3-B. 评测基线建立

**文件**：`scripts/qa_rag_eval_v2.py`（已有，补充执行）

执行 Recall@K 评测，建立 Phase 2 升级前后的对比基准。

---

## 涉及文件汇总

| 文件 | 改动 | 阶段 |
|------|------|------|
| `backend/common/rag/retriever.py` | OFF_TOPIC_HINTS / JURISDICTION_STRONG_HINTS / PATH_STRONG_HINTS 扩充；得理法搜触发逻辑重构 | Phase 1 |
| `backend/common/rag/semantic_embedder.py` | 新建，SemanticEmbedder 实现 | Phase 2 |
| `backend/common/rag/ingest.py` | 支持 dense 向量索引格式 | Phase 2 |
| `backend/common/rag/vector_store.py` | 支持 dense 向量搜索 | Phase 2 |
| `backend/core/settings.py` | 新增 rag_embedding_backend 配置 | Phase 2 |
| `backend/common/rag/retriever.py` | 并行双路检索架构 | Phase 3 |

---

## 实施优先级建议

```
立即可做（1天内）:
  Phase 1-A  OFF_TOPIC_HINTS 中文扩充
  Phase 1-B  JURISDICTION_STRONG_HINTS 中文法域词
  Phase 1-C  得理法搜触发逻辑重构
  Phase 1-D  欧盟路径查询重写优化

需要准备（确认环境后）:
  Phase 2-A  确认 sentence-transformers 可安装 / 或确认混元 Embedding API 可用
  Phase 2-B  重建索引（耗时约 10-20 分钟，1011 条 × embed 时间）

后续:
  Phase 3-A  得理法搜并行双路（需异步改造）
  Phase 3-B  评测基线对比
```
