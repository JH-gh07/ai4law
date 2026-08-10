# DataComplyFlow 知识库三层对齐与全链路修复方案

> 制定日期：2026-08-10
> 触发问题：前端知识库被 33 条国际空壳条目占领首屏，中国法规不可见
> 根因深度：registry → articles → V3 chunks 三层管道结构性断裂
> 目标：三层完全对齐，前端知识库只展示有实际可检索内容的条目

---

## 一、根因洞察

### 1.1 三层管道断裂全景

系统有三个独立的数据层，但彼此之间没有一致性校验：

```
sources.csv (编排清单)
    │
    ▼
source_registry.v1.json (元数据注册表, 102 条)
    │
    ├──→ regulation_articles.jsonl (条文级知识库, 56 source_ids, 1973 条)
    │       只覆盖了部分 registry 条目
    │
    └──→ storage/rag/v3/*.jsonl (向量检索层, 62 source_ids, 1272 chunks)
            只覆盖了 cn/eu/us 三法域
```

### 1.2 四类条目分析

| 类别 | 数量 | registry | articles | V3 chunks | 含义 |
|------|------|----------|----------|-----------|------|
| **has_both** | 23 | ✅ | ✅ | ✅ | 完全健康，三层对齐 |
| **has_articles_only** | 33 | ✅ | ✅ (1347条) | ❌ | 有实际条文但不可检索（全部国际法域） |
| **has_chunks_only** | 0 | ✅ | ❌ | ✅ | — |
| **registry_only** | 46 | ✅ | ❌ | ❌ | 纯元数据幽灵，零内容 |

### 1.3 前端污染的因果链

```
前端 EvidenceCenterPage
  → GET /api/v1/knowledge/index
    → build_user_source_catalog()
      → 遍历全部 102 条 registry 条目（含无内容条目）
        → 按 (jurisdiction_label, category, title) 排序
          → _JURISDICTION_LABELS 遗漏 hk/jp/kr 等 → 输出 ASCII "HK"/"JP"/"KR"
            → Python 排序: ASCII 字母 << CJK 汉字
              → 前33条全是国际空壳，中国法规在第34条
```

### 1.4 9 个 CN 幽灵条目的特殊性

以下 9 个 CN 条目在 `sources.csv` 中有活跃模块分配（path≠reference），但**既无 regulation_articles 也无 V3 chunks**：

| source_id | 标题 | 问题 |
|-----------|------|------|
| CN-GUIDE-009 | 数据出境安全评估申报指南（第三版） | 与 CN-REG-004 内容重叠，无独立文本 |
| CN-QA-011 | 《个人信息出境标准合同办法》答记者问 | 政策解读，无条文结构 |
| CN-OPS-014 | 各地省级网信部门申报/备案联系方式 | 纯操作信息，非法规 |
| CN-SUP-003 | 个人金融信息保护技术规范 | 行业标准，文本未采集 |
| CN-SUP-004 | 信息安全技术 个人信息安全规范 | 国标，文本未采集 |
| CN-SUP-005 | 数据出境申报系统使用手册 | 操作手册，非法规 |
| CN-SUP-006 | 汽车数据安全管理若干规定（试行） | 文本未采集 |
| CN-SUP-007 | 金融数据安全 数据安全分级指南 | 行业标准，文本未采集 |
| CN-TPL-022 | 隐私政策样例 | 参考模板，非法规 |

---

## 二、修复方案

### 阶段1：数据层清理（可并行）

#### 子任务 1.1: 清理 registry 中 9 个 CN 幽灵条目
- **操作**：将 sources.csv 中这 9 条的 `path` 改为 `reference`，使 `_modules_for_row()` 返回 `[]`
- **影响**：registry 重建后这 9 条将不再有活跃模块分配
- **验证**：`ensure_source_registry()` 后对应条目 `modules=[]`

#### 子任务 1.2: 增强 registry 构建的 content-aware 过滤
- **操作**：`build_source_registry_from_sources_csv()` 增加快照文件存在性检查
- **逻辑**：如果条目有 snapshot_path 但文件不存在，打印 warning
- **验证**：运行 registry 构建脚本，无 broken snapshot 报错

#### 子任务 1.3: 完善 _JURISDICTION_LABELS 映射表
- **操作**：已完成（提交 `f06d375`）
- **验证**：`build_user_source_catalog()` 输出全部为中文标签

#### 子任务 1.4: registry → catalog 过滤策略固化
- **操作**：已完成（提交 `f06d375`）— `build_user_source_catalog()` 只返回有 V3 chunk 的条目
- **验证**：API `/api/v1/knowledge/index` 返回 23 条，法域选项仅 中国/欧盟/美国

### 阶段2：国际法域内容管线（按需）

#### 子任务 2.1: 为 33 个国际法域条目构建 V3 chunk 索引
- **前提**：1347 条 regulation_articles 已就绪
- **操作**：扩展 `builders_v2.py` 支持 intl 法域的 chunk 构建
- **注意**：国际法域暂不接入检索管线（`search_user_articles` 仍只搜 cn/eu/us），但知识库展示应标注"内容已收录，检索引擎开发中"

### 阶段3：evidence_chain 管线修复（C-COMMON-3）

#### 子任务 3.1: 定位 evidence_builder 空字段根因
- **现状**：assessment(5/5)、dpia(12/12)、us_14117(5/5) 三项字段 100% 为空
- **可能根因**：
  - a) evidence_builder 创建 EvidenceItem 时未调用 RAG 检索填充
  - b) RAG 检索结果为空（LLM 生成的 claim 无法匹配到条文）
  - c) LLM 生成 evidence 时未收到足够的上下文
- **排查方法**：在 `evidence_builder.py` 的 `build_evidence()` 中加 debug trace

#### 子任务 3.2: 实现 evidence 填充管线
- **目标**：每个 EvidenceItem 的 `legal_basis` 至少含 1 条 CitationBinding
- **实现**：在 evidence_builder 中 `build_evidence()` → `_enrich_with_citations()` → 对每个 claim 做 RAG 检索 → 取 top-1 匹配条文 → 填充 CitationBinding

### 阶段4：脚注覆盖率提升

#### 子任务 4.1: assessment/dpia/BCR 脚注分配管线修复
- **现状**：assessment 21%、dpia 8%、BCR 0% vs us_14117 100%
- **根因**：这些模块的 citation_map 由 `write_citation_map_json()` 生成，但 LLM 生成的正文中引用标记未被正确解析
- **修复**：统一所有模块的 footnote assignment 逻辑到 `assign_footnote_number()` 公共函数

### 阶段5：PIPIA LLM 恢复

#### 子任务 5.1: pipia LLM 健康检查修复
- **现状**：`require_healthy_llm` 拦截 → 所有章节降级为 "LLM未配置，此处为占位内容"
- **根因**：pipia router 的 `/generate` 和 `/generate_async` 都依赖 `Depends(require_healthy_llm)`，但 LLM 健康检查未通过
- **修复方案 A**（推荐）：在非 production 环境跳过健康检查 → pipia 本地可运行
- **修复方案 B**：修复 LLM 健康探测配置

---

## 三、可验核里程碑

| 阶段 | 验收标准 | 验核命令 |
|------|---------|---------|
| P1-1 | 9 CN 幽灵条目 path=reference | `python3 -c "from backend.common.knowledge.registry import ensure_source_registry; entries = [e for e in ensure_source_registry() if e.source_id in ghost_set]; assert all(e.modules==[] for e in entries)"` |
| P1-2 | `/api/v1/knowledge/index` 返回 23 条 | `curl localhost:8000/api/v1/knowledge/index \| jq '.summary.source_count'` → 23 |
| P1-3 | 前端知识库首页前三行为中国法规 | 浏览器访问 EvidenceCenter → 第一条为 CN-LAW-003 或 CN-REG-004 |
| P3-1 | evidence_chain legal_basis 非空率 > 80% | `python3 -c "assert sum(1 for e in evidence_items if e.legal_basis)/len(evidence_items) > 0.8"` |
| P4-1 | assessment/dpia footnote_map 覆盖率 > 60% | citation_map.json footnote_map keys / all_items > 0.6 |
| P5-1 | pipia 不再输出占位文本 | markdown.md 不含 "LLM未配置" |

---

## 四、附录：三层数据映射表

```
registry.source_id → regulation_articles.source_id → V3 chunk.source_id
    102条                  56 source_ids               62 source_ids
                             1973 rows                  1272 chunks
```

完整映射见 `status/check/DataComplyFlow_三层数据映射表_20260810.md`
