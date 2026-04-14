# v5 当前实际情况（截至 2026-04-14）

> 范围：`doc/v5` 下本轮评测与计划文件  
> 参考文件：`eval_baseline_hashing.md/json`、`eval_baseline_semantic.md/json`、`plan.md`

---

## 1. 数据与评测资产现状

- RAG 条文库：`doc/knowledge/normalized/regulation_articles.jsonl` 共 **1011** 条
- 法域分布：**CN 394 / EU 398 / US 219**
- 路径分布（主要）：`all 517 / cpra 183 / bcr 95 / scc 63 / scc|tia 37 / cn_flow 32 / assessment 23`
- 索引文件：`storage/rag/regulation_index_v2.json` 已存在
- 元数据文件：
  - `doc/knowledge/index/sources.csv`：**19** 条
  - `doc/knowledge/index/practice_cases.csv`：**12** 条
- v5 评测产物已生成：
  - `doc/v5/eval_baseline_hashing.md` + `.json`
  - `doc/v5/eval_baseline_semantic.md` + `.json`

---

## 2. 核心结果：Hashing vs Semantic（总体）

### Vector 模式

| 指标 | Hashing | Semantic | 变化 |
|---|---:|---:|---:|
| Recall@5 | 0.258 | **0.487** | **+0.229** |
| Top1 Acc | 0.117 | **0.304** | **+0.187** |
| Precision@5 | 0.073 | **0.245** | **+0.172** |
| MRR | 0.177 | **0.368** | **+0.191** |
| nDCG@5 | 0.157 | **0.314** | **+0.157** |
| SafeReject（负例） | 0.264 | 0.257 | -0.007 |
| 标题泄漏率 | 0.062 | 0.062 | 0 |

### Hybrid 模式

| 指标 | Hashing | Semantic | 变化 |
|---|---:|---:|---:|
| Recall@5 | 0.258 | **0.458** | **+0.200** |
| Top1 Acc | 0.117 | **0.283** | **+0.166** |
| Precision@5 | 0.072 | **0.233** | **+0.161** |
| MRR | 0.177 | **0.342** | **+0.165** |
| nDCG@5 | 0.154 | **0.292** | **+0.138** |
| SafeReject（负例） | 0.264 | 0.257 | -0.007 |
| 标题泄漏率 | 0.062 | 0.062 | 0 |

**结论**：语义向量版本相比 hashing 基线，正例检索质量有显著提升；但负例拒答能力未同步提升。

---

## 3. 模块层现状（Semantic）

### 表现较好（Vector Recall@5）
- `assessment`: **0.875**
- `general`: **0.833**
- `diagnosis`: **0.750**

### 仍明显薄弱
- `bcr`: **0.000**（仍为 0）
- `cn_flow`: **0.125**（且相比 hashing 下降）
- `tia`: **0.250**
- `dpia`: **0.292**（hybrid 下仅 0.125）

---

## 4. 与 plan.md 对照的真实进度

`doc/v5/plan.md` 的核心目标是“打通知识库中心与 RAG 条文检索能力”。  
目前实际状态：

- ✅ 已完成：v5 基线评测（hashing / semantic）并沉淀结果文件
- ✅ 已完成：质量问题可量化（召回、top1、拒答、泄漏率）
- ⏳ 待完成：`/api/v1/knowledge/search` 对外接口（plan 的 Step 2）
- ⏳ 待完成：前端知识库中心新增“条文检索”Tab 并接真实检索接口（plan 的 Step 4）
- ⏳ 待完成：拒答与 off-topic 策略增强（当前 safe reject 仍偏低）

---

## 5. 当前主要风险（按优先级）

1. **BCR / CN_FLOW 召回过低**：对应模块会直接影响生成质量与可追溯性。  
2. **负例拒答能力不足**：非相关问题仍可能返回“看似相关”条文。  
3. **知识库中心仍偏元数据展示**：用户尚不能直接稳定检索 1011 条正文并联动预览。  

---

## 6. 下一步建议（v5）

1. 先落地 `knowledge/search` API + 前端 “条文检索” Tab（按 `plan.md` Step1~Step4）。  
2. 单独补 `bcr/cn_flow/tia/dpia` 的查询模板与 rerank 规则，先把模块底线拉起来。  
3. 强化负例拒答（中文 off-topic 词表 + 低分阈值双判定），再跑一轮同数据集复测。  

