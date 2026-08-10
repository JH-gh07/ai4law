# DataComplyFlow 全模块深度修复方案

> 制定日期：2026-08-10
> 触发问题：前端知识库被 33 条国际空壳条目占领首屏，中国法规不可见
> 问题层级：registry(102条) → articles(56源) → V3 chunks(62源) → catalog(102条) 四层管道结构性断裂
> 目标：一次性修复全部已发现断层，达成全模块可验核的最终状态

---

## 一、诊断全景：四层管道断裂矩阵

```
┌─────────────────────────────────────────────────────────────────┐
│  sources.csv （编排清单，顶层元数据）                              │
│      ↓                                                          │
│  source_registry.v1.json （102条注册表）                          │
│      ↓                           ↓                              │
│  regulation_articles.jsonl    storage/rag/v3/*.jsonl             │
│  （56 source_ids, 1973条）     （62 source_ids, 1272 chunks）      │
│      ↓                           ↓                              │
│  ┌─────────────────┐    ┌──────────────────┐                    │
│  │ citation 跳转层   │    │ evidence_chain   │                    │
│  │ （footnote_map）   │    │ （legal_basis）   │                    │
│  └─────────────────┘    └──────────────────┘                    │
│      ↓                           ↓                              │
│  ┌──────────────────────────────────────────┐                   │
│  │  build_user_source_catalog() → 前端知识库  │                   │
│  └──────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.1 四类条目断层分布

| 类别 | 数量 | registry | articles | V3 chunks | 状态 |
|------|------|----------|----------|-----------|------|
| **has_both** | 23 | ✅ | ✅ | ✅ | 健康，三层对齐 |
| **has_articles_only** | 33 | ✅ | ✅ (1347条) | ❌ | 国际法域，可引用不可检索 |
| **registry_only** | 46 | ✅ | ❌ | ❌ | 纯元数据幽灵，其中9条CN条目有活跃模块分配 |
| **has_chunks_only** | 0 | ✅ | ❌ | ✅ | — |

### 1.2 跨模块输出质量矩阵

| 模块 | 脚注覆盖率 | Markdown行数 | 占位符数 | 超长行 | 根因 |
|------|-----------|-------------|---------|--------|------|
| us_14117 | 100% | 15 | 0 | 1 | 格式坍塌（单行输出） |
| eu_scc | 100% | 94 | 0 | 3 | 内容完整但格式拼接 |
| tia | 100% | 94 | 0 | 0 | ✅ 完全健康 |
| cpra | 83% | 61 | 0 | 0 | 1条引用未注册 |
| assessment | 20% | 79 | 0 | 0 | CitationRegistry空启动 |
| dpia | 8% | 85 | 0 | 0 | 99条引用仅8条标记 |
| BCR | 0% | 45 | 2 | 0 | LLM表格输出无脚注标记 |
| pipia | 0% | 41 | 14 | 0 | LLM健康检查拦截 |
| cn_flow | 0% | 43 | 6 | 0 | LLM健康检查拦截 |

### 1.3 前端知识库污染因果链

```
_JURISDICTION_LABELS 仅定义 cn/eu/us 三个映射
    ↓
hk/jp/kr 等 7 个法域走 fallback → value.upper() → ASCII "HK"/"JP"/"KR"
    ↓
Python 字符串排序: 0x48 ("H") << 0x4E2D ("中")
    ↓
33 个国际空壳条目排在 CN/EU/US 前面
    ↓
build_user_source_catalog() 不过滤无 V3 chunk 的条目
    ↓
前端首屏 33 条全是 HK/JP/KR 空壳，CN 在第 34 条
```

---

## 二、修复矩阵（一次性全部执行）

### 已修复项（提交 58d9b26）

**A1. 法域标签补全** ✅
- 文件：`backend/services/knowledge_projection.py`
- 内容：_JURISDICTION_LABELS 新增 hk/jp/kr/mo/my/sg/tw → "中国香港"/"日本"/"韩国"等

**A2. Catalog 过滤** ✅
- 文件：`backend/services/knowledge_projection.py`
- 内容：`build_user_source_catalog()` 只返回 `entry.source_id in by_source`（有 V3 chunk 的条目）
- 效果：102 → 23 条，法域过滤选项 中国/欧盟/美国

**A3. CN 幽灵条目清理** ✅
- 文件：`resources/legal/catalog/sources.csv`
- 内容：9 条 CN 条目 path→reference, module 清空
- 涉及：CN-GUIDE-009, CN-QA-011, CN-OPS-014, CN-SUP-003~007, CN-TPL-022

**A4. Registry 重建** ✅
- 文件：`resources/legal/registry/source_registry.v1.json`
- 内容：从修复后的 sources.csv 重建 + 保留 33 intl 条目（有真实 regulation_articles 但无 V3）

**A5. CitationBinding 字段映射修复** ✅
- 文件：`backend/common/workflow/evidence.py`
- 问题：evidence_builder 构造 CitationBinding 时用了错误字段名（source_id→source_title, article_no→article）
- 修复：新增 `regulation_to_citation()` 共享转换函数，接受 dict/object，正确映射字段名

**A6. evidence_chain legal_basis 填充** ✅
- 文件：`backend/domains/cn/security_assessment/evidence_builder.py`
- 文件：`backend/domains/eu/dpia/evidence_builder.py`
- 文件：`backend/domains/us/eo14117/evidence_builder.py`
- 内容：三个 builder 的 EvidenceItem 构造均调用 `build_citation_bindings(regulations)`

---

### 待修复项（按数据类型分组，无依赖项可并行）

#### B组：脚注覆盖率修复（三个独立子问题）

**B1. assessment CitationRegistry 预填充**

- 文件：`backend/domains/cn/security_assessment/service.py`
- 问题：第 334 行创建空 `CitationRegistry()`，然后等 LLM 生成引用标记才注册。LLM 生成 10 个引用但仅 2 个带正确标记格式。
- 修复：
  ```python
  # 第 334 行，从：
  citation_registry = CitationRegistry()
  # 改为：
  citation_registry = registry_from_documents(
      [{"source_id": r.source_id, "title": r.title, "article_no": r.article, "quote_text": r.snippet}
       for r in regulations],
      jurisdiction="CN",
  )
  ```
- 验证：重跑 assessment 后 `citation_map.json` footnote_map 键数 ≥ all_items 的 60%

**B2. BCR/DPIA/Cpra 脚注注入后处理**

- 问题：这些模块的 CitationRegistry 已预填充（`registry_from_documents`），但 LLM 生成表格/纯文本时不插入 `[^N]` 标记。`_footnote_numbers()` 从 markdown 中正则提取，找不到任何标记则 footnote_map 为空。
- 修复：在 markdown 渲染完成后，对所有已注册 citation_id 但未出现在正文的引用，在报告末尾追加"引用依据"段落：
  ```python
  def _inject_footnote_appendix(markdown: str, registry: CitationRegistry) -> str:
      """Append a reference appendix for citations registered but not cited inline."""
      used_numbers = _footnote_numbers(markdown)
      all_items = registry.get_footnote_map()
      orphan = {n: item for n, item in all_items.items() if n not in used_numbers}
      if not orphan:
          return markdown
      lines = ["\n\n## 引用依据\n"]
      for num, item in sorted(orphan.items()):
          lines.append(f"[^{num}]: {item.source_title} {item.article_no}")
      return markdown + "\n".join(lines)
  ```
- 涉及文件：`backend/domains/eu/bcr_review/service.py`、`backend/domains/eu/dpia/service.py`、`backend/domains/us/cpra/service.py`
- 验证：重跑后 footnote_map 键数匹配 all_items 数

**B3. cn_flow 委托链路修复**

- 问题：cn_flow 已委托 us_14117，但委托时未正确传递输出目录和 citation_registry
- 文件：`backend/domains/cn/cn_flow/`（确认委托代码路径）
- 验证：cn_flow 重跑后 markdown 不含 `LLM未配置` 占位

---

#### C组：LLM 健康检查修复

**C1. PIPIA require_healthy_llm 非生产环境豁免**

- 文件：`backend/services/runtime_health.py` 第 54 行
- 问题：
  ```python
  if str(settings.app_env or "").strip().lower() != "production":
      return  # ← 这条只在 production 时检查
  ```
  但在非 production 环境下，`LLMClient.enabled` 仍然可能为 False（API key 未配置或 provider 未初始化），导致：
  ```python
  # backend/domains/cn/pipia/service.py:131
  if self.llm_client and self.llm_client.enabled:
      # 正常生成
  else:
      # 降级为 "（{title}：LLM未配置，此处为占位内容）"
  ```
- 修复方案：
  ```python
  # service.py:131 改为在非 production 环境也尝试初始化 LLM
  if self.llm_client and self.llm_client.enabled:
      ...
  elif str(self.settings.app_env or "").strip().lower() != "production":
      # 非生产环境：允许带警告的降级输出，使用 rule_engine 基础逻辑
      content = _fallback_sections(title, facts, rules)
  else:
      content = f"（{title}：LLM未配置，此处为占位内容）"
  ```
- 验证：pipia 重跑后 markdown 不含 `LLM未配置`，至少 2000 字符

---

#### D组：Markdown 格式修复

**D1. us_14117 格式坍塌**

- 问题：整篇报告仅 1 个 H1 行（854 字符），所有脚注标记 `[1][2]...[17]` 内联拼接
- 根因：`_render_conclusion_markdown()` 或章节渲染器未插入换行
- 文件：`backend/domains/us/eo14117/service.py` 第 690-700 行附近 `_render_risk_matrix` / `_render_markdown`
- 修复：确保每行结论后追加 `\n\n`，每个脚注标记单独一行
- 验证：us_14117 重跑后 > 30 行，无超长行

**D2. eu_scc 格式拼接**

- 问题：3 个超长行（300+ 字符），条款内容拼接
- 文件：`backend/domains/eu/scc_review/service.py`（确认渲染逻辑）
- 修复：条款级渲染确保每条款后 `\n\n`
- 验证：eu_scc 重跑后无超长行

---

#### E组：数据层最终清理

**E1. 46 个 reference-only 条目审计**

- 问题：registry 中 46 条 path=reference 条目有快照文件（snapshot_path 存在），但从未解析为 regulation_articles
- 操作：对每条执行 `read_text_preview(snapshot_path)`，判断：
  - 有可提取文本 → 标记为 `needs_parsing`
  - 纯图片/PDF无文本/空文件 → 保留 reference 状态
- 输出：`status/check/DataComplyFlow_reference条目审计_20260810.md`
- 验证：所有 `needs_parsing` 条目在后续可被解析

**E2. 33 个国际法域 V3 索引构建脚本**

- 前提：1347 条 regulation_articles 已就绪
- 实现：扩展 `backend/common/rag/orchestrator.py` 的 `build_chunk_sets()` 支持 `intl_*` 索引名
- 注意：`search_user_articles()` 仍只搜 cn/eu/us，intl 索引仅供 citation 跳转和知识库展示
- 验证：`storage/rag/v3/intl_legal_*` 索引文件存在且可加载

---

## 三、执行顺序

```
并行组1（无依赖）：
  B1  assessment CitationRegistry预填充
  C1  PIPIA LLM健康检查修复
  D1  us_14117格式修复
  D2  eu_scc格式修复
  E1  reference条目审计
  E2  intl V3索引脚本

并行组2（依赖B1）：
  B2  BCR/DPIA/Cpra 脚注注入后处理
  B3  cn_flow委托链路修复
```

---

## 四、可验核里程碑

| 编号 | 验证目标 | 验核命令/方法 |
|------|---------|-------------|
| V1 | 前端知识库仅 23 条，首位 CN | `curl localhost:8000/api/v1/knowledge/index \| jq '.sources[0].jurisdiction'` → "中国" |
| V2 | assessment footnote_map ≥ 60% | 重跑 assessment → `jq '.footnote_map \| length' citation_map.json` |
| V3 | BCR footnote_map = all_items | 重跑 BCR → `jq '.footnote_map \| length' citation_map.json` |
| V4 | pipia 无"LLM未配置"占位 | 重跑 pipia → `grep -c "LLM未配置" markdown.md` → 0 |
| V5 | us_14117 > 30行，无超长行 | 重跑 → `wc -l` > 30, 无行 > 300 字符 |
| V6 | eu_scc 无超长行 | 重跑 → 无行 > 300 字符 |
| V7 | evidence_chain legal_basis 非空 | 重跑后 → 每个 EvidenceItem.legal_basis 至少 1 条 CitationBinding |
| V8 | 9 CN 幽灵条目不出现在 catalog | `build_user_source_catalog()` 结果中无 CN-GUIDE-009 等 |
| V9 | 全模块测例全部通过 | `uv run pytest backend/ -x -q` |

---

## 五、附录

### A. 9 条 CN 幽灵条目清单

| source_id | 标题 | 原 path | 原 module | 快照存在 |
|-----------|------|---------|-----------|---------|
| CN-GUIDE-009 | 数据出境安全评估申报指南（第三版） | assessment | cn-assessment | ✅ |
| CN-QA-011 | 《个人信息出境标准合同办法》答记者问 | scc | cn-review | ✅ |
| CN-OPS-014 | 各地省级网信部门申报/备案联系方式 | assessment\|scc | cn-assessment | ✅ |
| CN-SUP-003 | 个人金融信息保护技术规范 | all | cn-diagnosis | ✅ |
| CN-SUP-004 | 信息安全技术 个人信息安全规范 | all | cn-diagnosis | ✅ |
| CN-SUP-005 | 数据出境申报系统使用手册 | all | cn-diagnosis | ✅ |
| CN-SUP-006 | 汽车数据安全管理若干规定（试行） | all | cn-diagnosis | ✅ |
| CN-SUP-007 | 金融数据安全 数据安全分级指南 | all | cn-diagnosis | ✅ |
| CN-TPL-022 | 隐私政策样例 | review | cn-review | ✅ |

### B. 脚注覆盖率根因对照表

| 模块 | 预填充 | LLM标记 | 后注入 | 覆盖率 | 修复方式 |
|------|--------|---------|--------|--------|---------|
| us_14117 | ✅ registry_from_documents | ✅ 生成 `[^N]` | — | 100% | 无需修复 |
| eu_scc | ✅ | ✅ | — | 100% | 无需修复 |
| tia | ✅ | ✅ | — | 100% | 无需修复 |
| cpra | ✅ | 部分 | — | 83% | B2 |
| assessment | ❌ 空启动 | 部分 | — | 20% | B1 |
| dpia | ✅ | ❌ 表格无标记 | — | 8% | B2 |
| BCR | ✅ | ❌ 表格无标记 | — | 0% | B2 |
| pipia | ✅ | ❌ LLM停摆 | — | 0% | C1 |
| cn_flow | ✅ | ❌ LLM停摆 | — | 0% | B3 |

### C. 已提交修复清单（58d9b26）

| 编号 | 修复内容 | 涉及文件 |
|------|---------|---------|
| A1-A4 | 法域标签+Catalog过滤+幽灵清理+Registry重建 | `knowledge_projection.py`, `sources.csv`, `source_registry.v1.json` |
| A5-A6 | CitationBinding映射+evidence_chain填充 | `evidence.py`, `__init__.py`, 3个`evidence_builder.py` |
| — | PIPIA 附件测试声明过滤 | `pipia/service.py` |
