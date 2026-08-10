# DataComplyFlow 知识库剩余问题闭环与可核验实施方案

> 版本：v1.0
> 日期：2026-08-10
> 当前分支：`new`
> 制定基线：`300a647`
> 方案状态：待执行
> 适用范围：除“浏览器真实截图验收”和“远程部署”之外的知识库剩余问题
> 前置材料：`status/todo/DataComplyFlow_知识库前端展示修复方案_20260810.md`、`status/todo/DataComplyFlow_知识库索引修复方案_20260810.md`

---

## 一、目标和完成标准

本方案不是继续堆补丁，而是把知识库数据、索引、检索、API、前端展示和验收证据统一为一条可追踪链路：

```text
权威来源目录
  → 规范化条文
  → 可重复构建的索引
  → 模块检索
  → 引用解析 API
  → 前端统一展示
  → 自动化验收证据
```

最终必须达到：

1. 同一个模块名在前端、领域服务、知识库 Schema、索引和检索器中语义一致。
2. 每条可引用内容都有真实、唯一、可解释的法律定位，不使用人为追加的假条号规避重复。
3. 每条允许对外引用的内容都有可追溯来源；项目内部模板不能伪装成法律原文。
4. 15 个索引能够从 Git 管理的数据源全量重建，结果有清单、指纹和统计，不依赖旧的 `storage/` 文件。
5. 每个业务模块都有固定查询和强断言，证明检索到的是预期法规，不只是“返回了若干结果”。
6. `LawViewerPage` 和 `EvidenceCenterPage` 使用同一渲染能力，不复制两套正文展示逻辑。
7. 状态文档只保留一个当前事实源，旧报告明确标记历史基线，禁止互相矛盾。

### 本方案明确不包含

- 浏览器真实截图验收；
- Playwright 视觉截图；
- 远程服务器连接；
- 远程部署和生产发布。

这些工作保持独立，必须在本方案本地门禁全部通过后，再由用户决定是否启动。

---

## 二、当前事实基线

以下数字均在 `300a647` 上重新核验，不沿用旧文档：

| 项目 | 当前事实 | 证据 |
|---|---:|---|
| canonical 条文 | 1973 条 | `resources/legal/registry/regulation_articles.jsonl` |
| canonical 来源数 | 56 个含条文来源 | `scripts/check_citation_source_integrity.py --json` |
| 来源目录 | 102 个来源 | `resources/legal/registry/source_registry.v1.json` |
| 重复定位 | 0 | 完整性脚本 |
| `段落N` 条文 | 0 | canonical JSONL 和重建后的三法域索引 |
| 条文解析率 | 100% | 1973/1973 |
| 条文行自身带 URL | 565/1973 | 完整性脚本 |
| 结合 `sources.csv` 后仍无 URL | 61 条、7 个来源 | 当前复核脚本 |
| legal index 模块分布 | CN 619、EU 402、US 193 | 重建后的 `storage/rag/v3/legal_index_*.jsonl` |
| case parity | 11 模块、20 CLI cases、424 leaf checks、28 developer cases | `scripts/check_case_parity.py` |
| 知识库/RAG 定向测试 | 25 passed | pytest 本地复核 |
| 前端 Markdown 测试 | 15 passed | Vitest 本地复核 |
| 前端 build | 通过 | `npm run build` |

说明：`storage/rag/v3/` 被 `.gitignore` 排除，它是可重建运行时产物，不是权威数据源。验收必须以“从干净临时目录重建”作为证据，不能只读取开发机上已有文件。

---

## 三、问题、现有错误逻辑和预期逻辑

### P0-1：EvidenceCenter 和 LawViewer 的渲染能力没有统一

#### 当前问题

`LawViewerPage` 已使用 `ReactMarkdown + remarkGfm`，但 `EvidenceCenterPage` 仍直接把正文放进 `<p>`：

```tsx
// frontend/src/pages/EvidenceCenterPage.tsx:803-806
<div className="knowledge-preview-block">
  <strong>{copy.articlesContentLabel}</strong>
  <p style={{ whiteSpace: "pre-wrap" }}>{selectedArticle.content}</p>
</div>
```

URL 指定条文同样使用普通 `<p>`：

```tsx
// frontend/src/pages/EvidenceCenterPage.tsx:860-863
<strong>{formatLegalLocator(urlArticleDetail.article_no)}</strong>
<p style={{ whiteSpace: "pre-wrap" }}>{urlArticleDetail.article_content}</p>
```

现有验收报告却声明两个页面已经统一，文档结论与代码事实不一致。

#### 错误逻辑

```text
同一份知识内容
  ├─ LawViewerPage → Markdown 解析
  └─ EvidenceCenterPage → 普通文本 + 局部 inline style
```

后果：标题、列表、表格、引用块在两个页面呈现不同；以后修复链接、换行或安全策略时需要改两套代码。

#### 预期逻辑

建立单一展示组件：

```text
KnowledgeContentRenderer
  ├─ 输入：content、variant、className
  ├─ 统一：ReactMarkdown + remarkGfm
  ├─ 禁止：rehypeRaw / dangerouslySetInnerHTML
  ├─ 统一：链接 target/rel、表格滚动、长词换行
  └─ 被 LawViewerPage、EvidenceCenterPage 共同调用
```

#### 验收标准

- [ ] 两个页面不再直接渲染法规正文 `<p>{content}</p>`。
- [ ] Markdown 标题、列表、表格、引用块在组件测试中结构一致。
- [ ] 原始 HTML 字符串只能作为文本显示，不能执行标签或脚本。
- [ ] 删除正文区域的重复 inline `whiteSpace` 样式。

---

### P0-2：`us_14117` 与 `us_eo14117` 模块名不一致

#### 当前问题

用户功能、API 和当前 legal index 使用 `us_14117`，但 RAG 请求契约和服务仍使用 `us_eo14117`：

```python
# backend/domains/us/eo14117/service.py:181-186
retrieve_legal_documents(
    query,
    module="us_eo14117",
    ...
)
```

```python
# backend/common/rag/orchestrator.py:108-109
if request.module in {"us_eo14117", "us_vendor_review", "us_cpra"}:
    return self._retrieve_us(request)
```

索引构建则继承来源目录中的 `us_14117`：

```python
# backend/common/knowledge/builders_v2.py:1018-1035
modules = [item for item in registry_entry.modules if item.startswith("us_")]
...
module=module
```

当前检索之所以还能返回 17 条，是 workflow rule 通过 `reference_ids=["US-FED-001"]` 绕过 module filter 补回全部条文，而不是直接 module 查询成功。

#### 错误逻辑

```text
服务查询 us_eo14117
  → legal_index_us 按 module=us_eo14117 查询 0 条
  → workflow rule 恰好命中
  → reference_ids 再补回 US-FED-001
```

这是偶然兜底，不是可靠主路径。workflow 查询、规则 ID 或引用配置变化时，法律检索可能静默归零。

#### 预期逻辑

采用单一 canonical key：`us_14117`。

```text
前端/API/领域服务/RAG Schema/registry/index = us_14117
旧 us_eo14117 = 仅在输入边界映射一次，并记录 deprecated alias
```

不得让公共层永久维护两个等价模块名。

#### 验收标准

- [ ] `RetrievalRequest(module="us_14117")` 通过 Schema 校验。
- [ ] legal index 直接按 `module=us_14117` 返回 17 条，不依赖 workflow fallback。
- [ ] 旧 `us_eo14117` 若仍需兼容，只在一个适配函数中出现。
- [ ] `rg 'us_eo14117' backend/common backend/domains` 的剩余结果均有明确兼容说明。
- [ ] 自动测试分别证明直接检索和 workflow 补充逻辑，禁止只测最终非空。

---

### P0-3：CPRA 使用人为后缀制造唯一键，法律定位仍不准确

#### 当前问题

当前 registry 中存在：

```text
§1798.140(ii)-01
§1798.140(ii)-02
§1798.140(ii)-03
§1798.145(i)-01
§1798.145(i)-02
```

这些后缀用于绕过重复键，但内容实际来自不同 subdivision 或被错误切分的相邻段落。现状达到“数据库键唯一”，没有达到“法律定位正确”。

#### 错误逻辑

```text
原始解析重复
  → 不重新确认源条款边界
  → 在 article_ref 后追加 -01/-02
  → 完整性测试只检查唯一性
  → 错误定位被判定为通过
```

#### 预期逻辑

以 California Legislative Information 的正式层级为准，重新构建定位：

```text
section
  → subdivision
    → paragraph
      → subparagraph
```

建议将结构拆为：

```json
{
  "section": "1798.140",
  "subdivision": "ae",
  "paragraph": "1",
  "subparagraph": "G",
  "display_locator": "§1798.140(ae)(1)(G)"
}
```

`article_ref` 保存法律上真实、可展示的完整定位；不得继续使用无来源依据的序号后缀。

#### 验收标准

- [ ] 五个临时 `-NN` 定位全部消失或进入明确的 legacy alias 表。
- [ ] 每条内容可以在官方源中定位到对应 section/subdivision。
- [ ] 内容与定位至少做“开头文本 + 结尾文本 + 长度”三项对照。
- [ ] 旧链接有确定的迁移结果：跳转到新定位，或明确 410/不可解析，不得误跳。
- [ ] CPRA fixture 覆盖 `1798.100`、`1798.105`、`1798.140`、`1798.145`。

---

### P0-4：来源 URL 的检查口径错误，不能真实反映用户是否可追溯

#### 当前问题

`check_citation_source_integrity.py` 只检查 `regulation_articles.jsonl` 每行的 `source_url`：

```python
# scripts/check_citation_source_integrity.py:194-197
missing_url = [
    i for i, r in enumerate(rows)
    if not str(r.get("source_url", "")).strip()
]
```

实际 API 会回退到 `sources.csv.url`：

```python
# backend/services/knowledge_index.py:173-186
"source_url": str(target.get("source_url", "") or source.get("url", "")).strip()
```

因此脚本报告“1408 条缺 URL、覆盖率 28.6%”，但按真实 API 回退逻辑计算后，只剩 61 条、7 个项目内部资料来源没有 URL。

同时，URL 完整性目前不是阻断条件；脚本只阻断重复键和空条号。

#### 错误逻辑

```text
审计脚本口径 ≠ 运行时 API 口径
```

导致两种风险：一是把已有来源链接误报为缺失；二是允许真正缺链接且可对外引用的内容通过验收。

#### 预期逻辑

建立统一的 `effective_source_url`：

```text
article.source_url
  → sources.csv.url
  → registry.metadata.source_url（如后续保留）
  → 空
```

门禁按用途分类：

| 内容类型 | URL 要求 |
|---|---|
| `can_be_cited=true` 且可进入对外报告 | 必须有有效 URL |
| 项目内部模板/测试夹具 | 可无 URL，但必须 `can_be_cited=false` |
| 本地上传材料 | 使用 material URI，不冒充官方来源 URL |

#### 验收标准

- [ ] 审计脚本与 API 共用同一个 URL 解析函数。
- [ ] 输出 raw URL 覆盖率和 effective URL 覆盖率，禁止混为一谈。
- [ ] 7 个无 URL 来源逐一分类并记录原因。
- [ ] 所有 `can_be_cited=true` 的对外法规来源 effective URL 覆盖率为 100%。
- [ ] URL 必须是 `https/http`，禁止本地绝对路径和占位字符串。

---

### P1-1：索引可自动重建，但缺少独立、确定的验收产物

#### 当前问题

`RetrievalOrchestrator` 会根据 source fingerprint 自动重建索引：

```python
# backend/common/rag/orchestrator.py:516-522
if all(self._is_index_current(name) for name in INDEX_NAMES):
    return
build_multi_index_v3(self.settings)
```

这能保证运行时更新，但也带来两个问题：

1. 测试过程中可能静默改写本地 `storage/rag/v3/`；
2. 验收报告可能引用旧索引统计，却没有记录 fingerprint 和构建输入。

#### 预期逻辑

将“运行时自动修复”和“验收重建”分开：

```text
开发运行：允许 auto_build
CI/验收：在 mktemp 临时目录显式 build
         → 输出 manifest.json
         → 运行质量门禁
         → 删除临时目录
```

manifest 至少包含：

- Git commit；
- source fingerprint；
- schema/embedding 版本；
- 每个索引条目数；
- 每个 module 条目数；
- `段落N`、空正文、重复 chunk 数；
- 构建时间；
- 验收命令和退出码。

#### 验收标准

- [ ] 从空临时目录成功构建 15 个 JSONL 和 vector index。
- [ ] 同一 commit 连续构建两次，manifest 中内容统计完全一致。
- [ ] 所有 legal index 的 `段落N=0`、空正文=0、重复 chunk_id=0。
- [ ] 源数据变化后 fingerprint 必须变化；非源文件变化不能触发错误重建。
- [ ] 验收不依赖开发机已有 `storage/rag/v3/`。

---

### P1-2：当前测试证明“可解析”，没有充分证明“检索正确”

#### 当前问题

当前强项是结构完整性：1973 条唯一、可解析。但这不能证明某个业务问题会检索到正确法规，也不能证明错误来源不会进入前几名。

#### 预期逻辑

建立模块级固定检索基准：

| 模块 | 固定问题示例 | 必须命中 |
|---|---|---|
| `cn_diagnosis` | 非 CIIO、人数阈值、豁免条件 | `CN-REG-006` 对应条款 |
| `cn_assessment` | 重要数据、100 万人、1 万敏感信息 | `CN-REG-004`/`CN-REG-006` |
| `cn_pipia` | 标准合同备案时限和材料 | `CN-REG-005` 第四至第七条 |
| `cn_review` | 标准合同责任和个人权利 | 个保法及标准合同来源 |
| `eu_scc` | Article 46 safeguards | GDPR Art 46 |
| `eu_bcr` | BCR enforceable rights | GDPR Art 47 |
| `eu_dpia` | 高风险处理 DPIA | GDPR Art 35/36 |
| `eu_tia` | 第三国传输和补充措施 | GDPR Art 44/46 + EDPB |
| `us_cpra` | 删除权、选择退出、敏感信息 | 对应 CCPA/CPRA section |
| `us_vendor_review` | service provider/contractor 义务 | CPRA 合同条款 |
| `us_14117` | prohibited/restricted transaction | 28 CFR 202.301/202.401 |

每条基准必须同时断言：

- expected source 在 top-k；
- expected locator 在 top-k；
- 禁止 source 不在 top-k；
- module、jurisdiction、can_be_cited 正确；
- 返回内容非空且不含 `段落N`。

#### 验收标准

- [ ] 11 个模块每个至少 3 条固定查询。
- [ ] 关键法规召回率 100%。
- [ ] 每条查询至少定义一个禁止命中的噪音来源。
- [ ] `us_14117` 测试必须证明直接 module filter 命中，不允许仅靠 workflow fallback。
- [ ] 失败输出包含 query、排名、source_id、locator、score，便于复盘。

---

### P1-3：状态文档互相矛盾，无法作为验收依据

#### 当前问题

- 前端方案文件头仍写“待执行”，末尾却写 12/15 已完成；
- 索引验收仍记录旧的 680/402/197；
- 重新核查报告基于 `13a49bf`，仍写 CN-REG-005 未修复；
- 最新实际基线已是 `300a647`、1973 条 canonical rows；
- 验收文件存在“表格有 NOT FOUND，但总结写 15/15 全部找到”的矛盾。

#### 预期逻辑

状态分成三类，禁止混写：

```text
todo/   = 尚未完成的计划，只写任务和 DoD
check/  = 一次验收快照，必须写 commit、时间、命令和原始结果
view/   = 当前系统说明，只引用最新有效 check，不复制统计
```

每份旧验收文件必须在文件头增加：

```text
状态：历史快照
适用 commit：...
已被：最新验收文件路径 替代
```

#### 验收标准

- [ ] 只有一份文件声明“当前状态”。
- [ ] 所有统计都带 commit 和生成时间。
- [ ] 旧结论不删除，但明确标注已过时。
- [ ] 文档中的模块名、条目数由 manifest 自动生成或引用，禁止手抄。
- [ ] `rg '全部通过|100%|已完成' status/check` 中每项均能找到命令和结果证据。

---

## 四、预期整体设计

### 4.1 分层和职责

```text
resources/legal/catalog/sources.csv
  职责：来源目录、官方 URL、用途和模块映射
          │
          ▼
resources/legal/registry/source_registry.v1.json
  职责：运行时来源契约；由 sources.csv 确定性生成
          │
          ▼
resources/legal/registry/regulation_articles.jsonl
  职责：规范化条文、真实定位、正文和来源 ID
          │
          ▼
backend/common/knowledge/builders_v2.py
  职责：把来源契约和条文编译成 KnowledgeChunkV2
          │
          ▼
backend/common/rag/ingest.py
  职责：构建 15 个索引并写入 manifest/fingerprint
          │
          ▼
backend/common/rag/orchestrator.py
  职责：按 canonical module 和任务阶段检索
          │
          ▼
backend/api/v1/endpoints/knowledge.py
  职责：稳定 API，不暴露内部索引细节
          │
          ▼
KnowledgeContentRenderer
  职责：统一、安全地展示知识正文
```

### 4.2 单向依赖

```text
领域服务 → RAG 公共接口 → KnowledgeChunk 契约 → 来源数据
前端页面 → 前端知识 API → 后端响应契约
```

禁止：

- builder 反向依赖具体领域 service；
- UI 自己重新解释条文编号；
- 多个页面复制 Markdown 渲染逻辑；
- 验收脚本使用不同于生产 API 的 URL/定位规则；
- 运行时索引反向成为 canonical 数据源。

### 4.3 共性下沉与差异配置

| 共性能力 | 公共实现 |
|---|---|
| 模块名归一化 | canonical module registry + legacy alias adapter |
| 法律定位 | locator parser/formatter contract |
| URL 回退 | `resolve_effective_source_url()` |
| Markdown 展示 | `KnowledgeContentRenderer` |
| 索引统计 | build manifest |
| 检索验收 | 参数化 benchmark fixtures |

法域差异通过配置表达：

- CN：`第X条/第X条之Y`；
- EU：`Article X`；
- US：`§section(subdivision)(paragraph)`；
- 模块所需来源、必须命中定位和禁止来源写入 fixture，不复制检索器。

---

## 五、实施顺序和任务卡

### Phase 0：保存基线

#### Task 0.1 建立本轮事实清单

**改动范围**：仅 `status/check/` 新建基线文件。
**依赖**：无。
**规模**：S。

验收：

- [ ] 记录 commit、Git 状态、Python/Node 版本。
- [ ] 记录 canonical、source registry、15 索引实际统计。
- [ ] 记录当前测试命令和退出码。

提交建议：

```text
docs(check): record knowledge closure baseline
```

### Phase 1：统一契约

#### Task 1.1 统一 `us_14117` 模块名

**可能修改**：`backend/common/knowledge/v2.py`、`backend/common/knowledge/registry.py`、`backend/common/knowledge/builders_v2.py`、`backend/common/rag/orchestrator.py`、`backend/domains/us/eo14117/service.py`、相关测试。
**依赖**：Task 0.1。
**规模**：M，需拆成“契约/调用方”和“兼容清理”两个提交。

验收命令：

```bash
uv run pytest backend/common/rag/tests backend/common/knowledge/tests backend/domains/us/eo14117/tests -q
```

#### Task 1.2 统一 effective source URL

**可能修改**：知识来源公共模块、`knowledge_index.py`、builders、完整性脚本和测试。
**依赖**：Task 0.1。
**规模**：M。

验收命令：

```bash
uv run python scripts/check_citation_source_integrity.py --json
uv run pytest backend/services/tests/test_knowledge_index.py backend/api/v1/tests/test_knowledge.py -q
```

### Checkpoint A：契约门禁

- [ ] `us_14117` 直接 legal filter 命中 17 条。
- [ ] 所有对外可引用来源 effective URL 100%。
- [ ] 旧 alias 行为有测试，无静默兼容。
- [ ] Git 工作区干净并完成原子提交。

### Phase 2：修正法律定位

#### Task 2.1 重解析 CPRA 临时定位

**可能修改**：CPRA snapshot/解析脚本、`regulation_articles.jsonl`、locator 测试、引用兼容表。
**依赖**：Task 1.2。
**规模**：M。

执行原则：

1. 先保存当前五条临时 locator 到迁移表；
2. 从官方源重建准确 subdivision；
3. 运行内容对照；
4. 更新引用测试；
5. 最后删除临时 locator。

禁止直接全局字符串替换。

验收命令：

```bash
uv run pytest backend/services/tests/test_knowledge_index.py backend/common/citation/tests -q
uv run python scripts/check_citation_source_integrity.py --verbose
```

### Checkpoint B：法律定位门禁

- [ ] duplicate=0。
- [ ] missing/invalid locator=0。
- [ ] 临时 `§...-NN`=0。
- [ ] CPRA 关键条款内容与官方来源抽样一致。

### Phase 3：统一前端展示

#### Task 3.1 抽取 `KnowledgeContentRenderer`

**可能修改**：新增一个前端组件、两个页面、样式文件和组件测试。
**依赖**：无，可与 Phase 2 分开进行，但提交必须独立。
**规模**：M。

验收命令：

```bash
cd frontend
npm test -- --run KnowledgeContentRenderer
npm run build
```

### Checkpoint C：展示门禁

- [ ] 两个页面共用一个 renderer。
- [ ] Markdown 表格和长链接不溢出。
- [ ] HTML/脚本不能执行。
- [ ] TypeScript build 通过。

### Phase 4：可重复索引和业务检索门禁

#### Task 4.1 增加临时目录重建命令和 manifest

**可能修改**：`scripts/` 构建/校验脚本、`backend/common/rag/ingest.py`、测试。
**依赖**：Phase 1、2。
**规模**：M。

#### Task 4.2 建立 11 模块检索 benchmark

**可能修改**：新增结构化 fixture、参数化 pytest、CI 命令。
**依赖**：Task 4.1。
**规模**：M。

建议 fixture：

```json
{
  "module": "eu_dpia",
  "query": "high risk profiling data protection impact assessment",
  "must_include": ["EU-LAW-001::35", "EU-LAW-001::36"],
  "must_exclude_sources": ["EU-TPL-001"],
  "top_k": 8
}
```

### Checkpoint D：索引和检索门禁

- [ ] 空目录构建 15/15 索引。
- [ ] 两次构建统计一致。
- [ ] 11 模块关键法规召回率 100%。
- [ ] 禁止噪音来源命中率 0%。
- [ ] case parity 继续通过。

### Phase 5：文档收口

#### Task 5.1 建立唯一当前状态文件

**可能修改**：`status/check/`、`status/todo/`、`status/view/` 中相关知识库文档。
**依赖**：Checkpoint D。
**规模**：S。

要求：

- 当前报告只引用 manifest，不手写索引统计；
- 旧报告标注历史快照和适用 commit；
- todo 只勾选有测试/产物证据的项；
- 不删除有审计价值的旧报告。

### Phase 6：本地最终门禁（不含浏览器和远程）

#### Task 6.1 全量自动化验收

```bash
git diff --check
uv run python scripts/check_citation_source_integrity.py --verbose
uv run python scripts/check_case_parity.py
uv run pytest backend -q
cd frontend && npm test
cd frontend && npm run build
```

另需使用 FastAPI `TestClient` 覆盖：

- `/api/v1/knowledge/index`；
- `/api/v1/knowledge/search`；
- `/api/v1/knowledge/citation`；
- `/api/v1/knowledge/sources/{source_id}`；
- `/api/v1/knowledge/sources/{source_id}/articles/{article_no}`。

#### Task 6.2 生成最终验收包

放入 `status/check/`：

```text
DataComplyFlow_知识库剩余问题最终验收_YYYYMMDD.md
knowledge-index-manifest.json
knowledge-retrieval-benchmark.json
knowledge-test-summary.txt
```

运行时 JSONL/vector 文件仍留在 `storage/`，不提交 Git。

---

## 六、最终验收总表

| 验收维度 | 通过条件 | 证据 |
|---|---|---|
| 模块契约 | canonical module 只有 `us_14117` | rg + Schema/检索测试 |
| CPRA 定位 | 无人工 `-NN` 假定位 | registry 扫描 + 官方源对照 |
| 来源追溯 | 对外可引用来源 effective URL 100% | 完整性报告 |
| 数据唯一 | duplicate/missing/invalid 均为 0 | integrity JSON |
| 索引可重建 | 空目录构建 15/15，重复构建一致 | manifest |
| 索引无噪音 | `段落N=0`、空正文=0 | manifest |
| 检索正确 | 11 模块关键法规召回率 100% | benchmark JSON |
| 前端一致 | 两页面共用 renderer | 组件测试 + 代码搜索 |
| 安全渲染 | HTML/脚本不执行 | 前端安全测试 |
| API 契约 | 五类 knowledge API 全通过 | TestClient 测试 |
| 回归 | backend、frontend、case parity 全通过 | test summary |
| 文档一致 | 单一当前状态，无矛盾统计 | 文档复核 |

任何一项未满足，方案状态保持“进行中”，不得标记归档。

---

## 七、风险和防护措施

| 风险 | 影响 | 防护 |
|---|---|---|
| CPRA 重解析改变已有链接 | 旧报告引用失效 | legacy alias 迁移表 + 回归 fixture |
| 模块名统一影响旧调用 | 14117 检索失败 | 单一边界 adapter + 双路径测试 |
| URL 门禁误伤内部模板 | 模板无法使用 | 按 can_be_cited/usage 分类，不一刀切 |
| 索引自动重建污染本地状态 | 统计不可复现 | 验收使用临时目录，输出 manifest |
| Markdown 组件允许原始 HTML | XSS | 不启用 rehypeRaw，不使用 dangerouslySetInnerHTML |
| 为提高召回重新引入噪音 | 报告引用低质量来源 | must_include + must_exclude 双断言 |
| 文档再次漂移 | 错误汇报 | 统计由 manifest 生成，旧报告标 commit |

---

## 八、Git 存档规则

每个任务完成后立即本地提交，禁止把数据、前端、文档混成一个大提交：

```text
test: add knowledge closure baseline gates
refactor: unify EO 14117 knowledge module key
fix: resolve effective citation source URLs
fix(data): restore canonical CPRA locators
refactor(frontend): share knowledge content renderer
test(rag): add reproducible index and retrieval benchmarks
docs(check): record final local knowledge verification
```

提交前必须执行：

```bash
git diff --check
git diff --cached --stat
git diff --cached
```

只暂存本任务文件，不使用 `git add -A`，不提交 `storage/`、`tmp/`、`outputs/` 和截图产物。

---

## 九、一句话策略

**先统一模块、定位和来源契约，再从权威数据重建索引，用模块级强断言证明检索正确，最后让两个前端页面复用同一安全渲染组件，并以自动生成的验收清单替代手写状态。**
