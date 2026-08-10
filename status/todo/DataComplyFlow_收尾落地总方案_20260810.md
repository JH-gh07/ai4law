# DataComplyFlow 收尾落地总方案

> **版本**: v1.0
> **日期**: 2026-08-10
> **分支**: `new`
> **HEAD**: `9853fc9`
> **方案性质**: 最终可执行收尾方案（非草案；每一步有命令/阈值/证据模板）

---

## 〇、基线快照（2026-08-10 测定）

本方案所有结论基于以下测定事实，非假设。

### 0.1 代码基线

```
测试:  888 passed / 1 failed（scc_review 预存失败）
前端:  npm run build 通过（~2.36s）
路由:  12 个前端页面路由全部 200
      POST /api/v1/auth/register → 200（注册/登录正常）
```

### 0.2 数据基线

```
regulation_articles.jsonl:  3211 rows, 102 source_ids, 0 duplicates
source_registry.v1.json:     69 entries
覆盖差异:                    33 个 orphan source_ids（在 articles 但不在 registry）
段落N 条目:                  1265 rows (39.4%) — 非正式条文
内容 <80 字符:                1215 rows
CN-REG-005:                  9 条目全部为"段落N"（新闻页噪音）
PDF 源:                      CN-REG-005 为扫描图片（0 可提取字符）
```

### 0.3 RAG 索引基线

```
storage/rag/v3/ 共 15 个子索引，总计 1333 rows

legal_index_cn:              680 rows, 28 sources,  44 noise (6.5%)
legal_index_eu:              402 rows,  2 sources,  93.5% 噪音（EU-SUP/EU-TPL 段落直切）
legal_index_us:              193 rows,  2 sources,   1 noise
standard_clause_index_*:      11 rows, 11 sources,  <5 chars/row 平均（metadata shells）
template_index_*:             17 rows,  6 sources,  大部分 <111 chars
testcase_index_*:             12 rows, 12 sources,  <112 chars 平均
workflow_index_*:             18 rows, 10 sources,  <144 chars 平均

模块分配:
  cn_assessment, cn_diagnosis, cn_pipia, cn_review → legal_index_cn
  eu_scc, eu_bcr, eu_dpia, eu_tia                 → legal_index_eu
  us_14117, us_cpra, us_vendor_review             → legal_index_us
```

### 0.4 模块状态矩阵（10 用户面模块 + 2 基础模块）

| # | 模块 | 后端 | 前端 | API 层 | 浏览器闭环 | 测试覆盖 |
|---|------|------|------|--------|------------|----------|
| 1 | diagnosis | ✅ | ✅ | ✅ | ⬜ | 7 test files |
| 2 | assessment | ✅ | ✅ | ✅ | ⬜ | 18 test files |
| 3 | pipia | ✅ | ✅ | ✅ | ✅ | 6 test files |
| 4 | review | ✅ | ✅ | ✅ | ⬜ | 19 test files (含 eo14117_flow) |
| 5 | eu_scc | ✅ | ✅ | ✅ | ✅ | 3 test files (1 预存失败) |
| 6 | bcr | ✅ | ✅ | ✅ | ✅ | 5 test files |
| 7 | dpia | ✅ | ✅ | ✅ | ✅ | 4 test files |
| 8 | tia | ✅ | ✅ | ✅ | ✅ | 6 test files |
| 9 | us_14117 | ✅ | ✅ | ✅ | ⬜ | 7 test files (eo14117_flow) |
| 10 | cpra | ✅ | ✅ | ✅ | ✅ | 12 test files |
| — | cn_flow | ✅ | ✅ | ✅ | ⬜ | 委托 us_14117 |
| — | knowledge | ✅ | ✅ | ✅ | ⬜ | 8 test files |

---

## 一、依赖图与执行阶段

```
                    ┌─────────────────────┐
                    │ P0: 数据治理         │  (4 子任务，无上游依赖)
                    │  - CN-REG-005 录入   │
                    │  - orphan 分类       │
                    │  - 段落N 标注        │
                    │  - RAG 噪音清理      │
                    └──────┬──────────────┘
                           │
                    ┌──────▼──────────────┐
                    │ P1: RAG 索引重建     │  (依赖 P0 数据修正)
                    │  - 15 索引用新数据   │
                    │  - RAG 命中回归测试  │
                    └──────┬──────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
    ┌─────────▼──┐  ┌─────▼──────┐  ┌─▼──────────────┐
    │ P2a: 引用  │  │ P2b: 模块  │  │ P2c: 性能      │
    │ 跳转验证   │  │ 浏览器验   │  │ 横切验收       │
    │ (4 模块)   │  │ 收 (4 模块)│  │ (4 模块)       │
    └─────┬──────┘  └─────┬──────┘  └─────┬──────────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
                   ┌──────▼──────────────┐
                   │ P3: cn_flow 退出     │  (依赖 P2a+P2b+P2c 全通过)
                   │  - 删除旧入口        │
                   │  - 全量回归          │
                   └──────┬──────────────┘
                          │
                   ┌──────▼──────────────┐
                   │ P4: 远端部署         │  (需用户明确同意)
                   │  - 显式禁止                   │
                   └─────────────────────┘
```

**关键路径**：P0 → P1 → P2(a,b,c) → P3 → P4

**可并行组**：
- 组1（无依赖）：P0 全部 4 个子任务
- 组2（依赖 P0）：P1 全部子任务
- 组3（依赖 P1）：P2a, P2b, P2c 可同时执行
- 组4（依赖 P2）：P3

---

## 二、P0：数据治理（4 子任务，可并行）

### P0-1：CN-REG-005 原文录入

**当前状态**：`regulation_articles.jsonl` 中有 9 个"段落N"条目，实际为 CAC 新闻页内容，非法规正文。PDF 源文件为扫描图片（无文本层）。

**落地方案**：手工录入 13 条正式条文。《个人信息出境标准合同办法》条文量少，条文内容可从 PDF 截图逐条 OCR 或查阅法律数据库逐条复制。录入格式与 CN-REG-004 一致。

**执行步骤**：
```bash
# 1. 删除现有 9 条噪音条目
uv run python -c "
import json
rows = [json.loads(l) for l in open('resources/legal/registry/regulation_articles.jsonl') if l.strip()]
rows = [r for r in rows if r['source_id'] != 'CN-REG-005']
with open('resources/legal/registry/regulation_articles.jsonl', 'w') as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print(f'CN-REG-005 removed, {len(rows)} rows remain')
"

# 2. 新增 13 条正式条文（手工录入）
# 格式: {"source_id": "CN-REG-005", "article_id": "CN-REG-005-NNN",
#        "article_ref": "第N条", "content": "第N条 [条文正文]",
#        "jurisdiction": "cn", "doc_type": "administrative_regulation",
#        "law_name": "个人信息出境标准合同办法"}
# 条文清单见附录 A。
```

**验证命令**：
```bash
# 确认 13 条存在且可查
uv run python -c "
from backend.services.knowledge_index import get_article_detail
for n in range(1,14):
    r = get_article_detail('CN-REG-005', str(n))
    if r: print(f'  第{n}条: OK ({len(r[\"article_content\"])} chars)')
    else: print(f'  第{n}条: MISSING')
"

# 确认引用跳转可用（前次失败的 pipia CN-REG-005 第1条）
uv run pytest backend/common/citation/tests/test_citation_url_normalization.py -q
```

**通过标准**：13 条全部可查，citation_url_normalization 全通过。

---

### P0-2：33 个 orphan source_ids 分类治理

**当前状态**：`regulation_articles.jsonl` 中有 33 个 source_id 不在 `source_registry.v1.json` 中。这些来自历史批量 ingest（JP/HK/MY/KR/TW/MO/SG/VN 等区域法律），但从未被纳入 registry，导致：
- `get_article_detail()` 对这些 source 的 registry 查找路径无效，回退到快照解析
- 这些 source 无 authority_level/binding_force/module 分配
- 1331 行的 article_ref 是"段落N"（非结构化提取）

**执行步骤**：
```bash
# 1. 列出所有 orphan source_ids
uv run python -c "
import json
reg_srcs = set()
with open('resources/legal/registry/source_registry.v1.json') as f:
    for e in json.load(f).get('entries', []):
        reg_srcs.add(e['source_id'])
art_srcs = set()
counts = {}
for l in open('resources/legal/registry/regulation_articles.jsonl'):
    if l.strip():
        r = json.loads(l)
        sid = r['source_id']
        art_srcs.add(sid)
        counts[sid] = counts.get(sid, 0) + 1
for sid in sorted(art_srcs - reg_srcs):
    print(f'{sid}: {counts[sid]} rows, prep={sum(1 for l in open(\"resources/legal/registry/regulation_articles.jsonl\") if json.loads(l)[\"source_id\"]==sid and str(json.loads(l).get(\"article_ref\",\"\")).startswith(\"段落\"))}')
"

# 2. 按策略分类：
#    - 有用：区域法律正文提取（需补充 registry entry）
#    - 不可用：段落直切噪音（移除或降级为 reference-only）
#    - 待定：需人工判定
```

**通过标准**：
- 列出 33 个 orphan 的分类结果（有用/不可用/待定）
- 有用的补充 registry entry
- 不可用的从 articles 移除或标记 `quality=low`
- 最终 regulation_articles.jsonl 与 source_registry.v1.json 的 source_id 集合一致（0 orphan）

---

### P0-3：段落N 条目标注与降噪

**当前状态**：3211 条中 1265 条 article_ref 为"段落N"（39.4%），其中 1215 条内容 < 80 字符。这些不是法律条文，而是直切段落（每 N 段一刀）。

**执行步骤**：
```bash
# 1. 按 source_id 统计段落N比例
uv run python -c "
import json
rows = [json.loads(l) for l in open('resources/legal/registry/regulation_articles.jsonl') if l.strip()]
by_src = {}
for r in rows:
    sid = r['source_id']
    is_para = str(r.get('article_ref','')).startswith('段落')
    by_src.setdefault(sid, {'total':0, 'para':0})
    by_src[sid]['total'] += 1
    if is_para: by_src[sid]['para'] += 1
for sid in sorted(by_src):
    d = by_src[sid]
    pct = d['para']*100//d['total'] if d['total'] else 0
    if d['para'] > 0:
        print(f'{sid}: {d[\"para\"]}/{d[\"total\"]} = {pct}% paragraph-only')
"

# 2. 对 100% paragraph 的 source_id:
#    - 有 snapshot 且有可解析结构 → 重新 ingest（用新的 multi-jurisdiction parser）
#    - 无 snapshot 或 image-only PDF → 降级为 reference-only
```

**通过标准**：
- 对每个 100% paragraph source 生成处理决定（re-ingest / degrade / remove）
- 最终段落N占比 < 5%（仅保留确实无结构化条文的 source）
- 内容 < 80 字符条目 < 10%（不含短条款）

---

### P0-4：RAG 索引噪音层清理（EU legal_index）

**当前状态**：`legal_index_eu.jsonl` 中存在大量 EU-SUP/EU-TPL 的段落直切噪音，且模块分配可能不精确。

**执行步骤**：
```bash
# 1. 列出 legal_index_eu 的所有 source_id 及其 chunk 数
uv run python -c "
import json
from collections import Counter
srcs = Counter()
for l in open('storage/rag/v3/legal_index_eu.jsonl'):
    if l.strip():
        r = json.loads(l)
        sid = r.get('source_id','') or r.get('metadata',{}).get('source_id','')
        if sid: srcs[sid] += 1
for sid, cnt in srcs.most_common():
    print(f'  {sid}: {cnt} chunks')
"

# 2. 确认 EU-SUP-*/EU-TPL-* 的 modules 分配是否正确
#    (sources.csv 中 module=eu-scc → 应仅进入 eu_scc，不应扩散到 bcr/dpia/tia)

# 3. 重建命令（P1 执行）：
uv run python backend/scripts/rebuild_rag_index.py --jurisdiction eu --force
```

**通过标准**：
- EU 索引仅包含 EU-LAW-001 (GDPR) 和 EU-GUIDE-002 (EDPB 01/2020) 的结构化 chunk
- 不再有 EU-SUP-*/EU-TPL-* 的"段落N"直切
- 每个模块可检索到 >= 5 条真实法律 chunk
- RAG 命中回归通过

---

## 三、P1：RAG 索引重建

**前提**：P0 全部完成（CN-REG-005 新数据、orphan 清理、段落N 降噪、EU 噪音清理）

### P1-1：15 索引全量重建

```bash
# 重建全部 15 个索引（从 regulation_articles.jsonl + sources.csv 重新 chunk + vectorize）
uv run python backend/scripts/rebuild_rag_index.py --all --force

# 验证索引行数
uv run python -c "
import json, os
for f in sorted(os.listdir('storage/rag/v3')):
    if f.endswith('.jsonl'):
        rows = [json.loads(l) for l in open(os.path.join('storage/rag/v3',f)) if l.strip()]
        print(f'{f}: {len(rows)} rows')
" | column -t
```

**通过标准**：
- 15 个 `.jsonl` 和 15 个 `.vector.json` 成对存在
- legal_index_* 每个至少有法律 source 的结构化 chunk（非"段落N"）
- 前台模块（12 个）每个在对应索引中有 >= 3 个 chunk

### P1-2：RAG 命中回归

```bash
# 对每个模块的典型查询，验证检索返回有意义结果
uv run python -c "
from backend.common.rag.orchestrator import RagOrchestrator
orchestrator = RagOrchestrator()

tests = [
    ('cn_assessment', '数据出境安全评估的触发条件是什么'),
    ('cn_diagnosis', '个人信息出境的三种路径'),
    ('cn_pipia', '个人信息保护影响评估的重点内容'),
    ('cn_review', '标准合同的备案要求'),
    ('eu_scc', 'GDPR transfer impact assessment requirements'),
    ('eu_bcr', 'BCR approval criteria under GDPR'),
    ('eu_dpia', 'When is a DPIA required under GDPR'),
    ('eu_tia', 'Transfer impact assessment EDPB recommendations'),
    ('us_14117', 'EO 14117 prohibited data brokerage transactions'),
    ('us_cpra', 'Consumer right to opt out of sale CPRA'),
]

for module, query in tests:
    results = orchestrator.search(
        query=query, module=module, top_k=3,
        jurisdictions=[module.split('_')[0]]
    )
    hit_count = len(results)
    good = sum(1 for r in results if len(r.get('content','')) > 80)
    print(f'{module:20s} {hit_count} hits, {good} with content>80 chars')
" 2>&1

# 预期: 至少 10/10 模块有 >=1 条 chunk 长度 >80 chars
```

**通过标准**：10/10 模块至少返回 1 条内容 >80 chars 的有效结果。0 个模块返回空集或仅返回 metadata shells。

### P1-3：引用利用率验收

```bash
# 计算每个模块的引用中可 match 到知识库的比例
uv run python scripts/check_citation_source_integrity.py 2>&1

# 预期: source_count 与 registry 一致, resolution_rate > 95%
```

**通过标准**：resolution_rate >= 95%（允许少量已知数据缺口）。

---

## 四、P2a：引用跳转验收（4 未闭环模块）

**范围**：diagnosis, assessment, review, us_14117

**前提**：P1 完成（知识库重建后引用可解析）

### 执行步骤

```bash
# 1. 启动前后端
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
cd frontend && npm run dev &     # 监听 5173（或 5174）
```

**对每个模块**：
```text
a. 在前端填写表单 → 提交 → 等待报告生成
b. 打开报告页 → 在正文中定位所有 [n] 脚注
c. 逐一点击 [n]，验证：
   - Popover 展示条文标题/条文号/法规名 → 截图
   - can_jump=true → 跳转 /evidence?source=XXX&article=N → 页面加载，条文高亮
   - Prev/Next 按钮可用
   - 控制台无 JS 错误
d. 逐一点击【依据：法规 第X条】，重复 c
e. 记录：脚注数、跳转成功数、跳转失败数、失败原因
```

### 验收矩阵

| 模块 | 脚注数 | 跳转成功 | 失败原因 | 截图 |
|------|--------|----------|----------|------|
| diagnosis | | | | |
| assessment | | | | |
| review | | | | |
| us_14117 | | | | |

**通过标准**：
- 每个模块的所有引用可跳转或可读失败原因
- 0 个 JS 报错、白屏、404
- 已知数据缺口（CN-REG-005 等）记录为"非代码原因"
- 每个模块 >= 1 张截图

---

## 五、P2b：模块浏览器验收（4 模块）

**范围**：diagnosis, assessment, review, us_14117

### 逐模块检查清单

```
diagnosis:
  [ ] 表单页面正常渲染（/diagnosis）
  [ ] 选择问卷类型 → 逐一回答问题 → 提交
  [ ] 结果页展示诊断结论 + 路径推荐
  [ ] 报告内容完整（结论、分析、依据）
  [ ] DOCX/PDF 可下载
  [ ] 引用跳转正常（P2a）
  [ ] 控制台 0 错误

assessment:
  [ ] 表单页面正常渲染（/assessment）
  [ ] 填写公司+数据类型+接收国 → 提交
  [ ] 报告 8 章生产形态（前次验收已确认结构）
  [ ] DOCX/PDF 可下载
  [ ] 引用跳转正常（P2a）
  [ ] 控制台 0 错误

review:
  [ ] 上传文档（PDF/DOCX/TXT）
  [ ] 选择文档类型 → 提交审查
  [ ] 审查结果页展示 issues
  [ ] 逐条 issue 可查看详细分析
  [ ] DOCX 主报告可下载
  [ ] 引用跳转正常（P2a）
  [ ] 控制台 0 错误

us_14117:
  [ ] 表单页面正常渲染（/us-14117）
  [ ] 填写 entity + person_count + transaction_type + description + DOJ → 提交
  [ ] 报告展示红/黄/绿判定 + 规则命中
  [ ] RAG 引用正常展示
  [ ] DOCX 可下载
  [ ] 引用跳转正常（P2a）
  [ ] 控制台 0 错误

cn_flow (旧入口兼容):
  [ ] 缺 us_person_count → 422 + 3 条补充问题
  [ ] 缺 transaction_type → 422 + 含"例如 vendor_agreement 或 data_brokerage"
  [ ] 完整请求 → 200，报告 = us_14117 产出
```

**通过标准**：全部 [ ] 打勾。

---

## 六、P2c：性能横切验收（4 模块）

**阈值表**：

| 指标 | 记录条件 | 阻断条件 |
|------|----------|----------|
| 总 token | < 500 或 > 50,000 | = 0（LLM 未参与） |
| 总耗时 | > 15min | > 30min |
| 事件数 | ≤ 5 | = 0 |
| agent 调用 | — | = 0 |
| error 事件 | — | > 0 |

**验证方式**：调 EventStream API，提取 token/time/event 统计。

```bash
# 对每个模块：
# 1. 提交异步任务
curl -s -X POST http://localhost:8000/api/v1/assessment/generate_async \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'

# 2. 监听事件流
curl -s http://localhost:8000/api/v1/events/task/{task_id}/stream \
  -H "Authorization: Bearer $TOKEN"

# 3. 提取统计
curl -s http://localhost:8000/api/v1/events/task/{task_id}/manifest \
  -H "Authorization: Bearer $TOKEN" | jq '{tokens, duration, events, agents}'
```

**通过标准**：4/4 模块均在阈值范围内。有异常则记录不阻断（除非阻断条件触发）。

---

## 七、P3：cn_flow 旧入口退出

**前提**：P2a + P2b + P2c 全部通过

**退出范围**：
- `backend/domains/us/eo14117_flow_review/compatibility.py` → 保留（兼容边界）
- `backend/domains/us/eo14117_flow_review/router.py` 中 `cn_flow_*` 路由 → 标记 `deprecated`
- 前端 `/cn-flow` 路由 → 重定向到 `/us-14117`（或显示迁移提示）

**不删除（保留兼容接口）**：
- `adapt_cn_flow_request()` — 旧数据可能仍需兼容

**回归验证**：
```bash
uv run pytest backend/ -q --ignore=benchmarks
# 预期: 888 passed / 1 failed (scc_review, 无新增失败)
```

---

## 八、P4：远端部署

**状态**：🔴 **显式禁止**，待 P3 通过且用户明确同意后方可执行。

---

## 九、验收总结模板（收尾时填入）

```markdown
# DataComplyFlow 全量收尾验收总结

## 数据质量
- regulation_articles.jsonl: NNNN rows, NN sources, 0 orphans, < N% 段落N
- CN-REG-005: 13 条正式条文 (已录入)
- RAG 索引: 15 对 (.jsonl + .vector.json), NNNN 总 chunks

## 模块闭环
- 浏览器闭环: 10/10 (diagnosis, assessment, review, us_14117 全部完成)
- 引用跳转: 10/10 全可跳转或可读失败原因
- 性能: 4/4 模块在阈值内
- cn_flow 退出: 完成

## 测试基线
- 测试: XXXX passed / 1 failed (scc_review 预存)
- 前端 build: 通过

## 截图证据
- (每模块至少 1 张截图路径)

## 未完成项
- (如有，列出原因和影响)
```

---

## 十、执行优先级排序

```
P0-1  CN-REG-005 文字录入          [阻塞 pipia 引用，先做]
P0-3  段落N 降噪                    [影响 39.4% 数据质量]
P0-2  orphan 分类                   [影响 33 个 source 的可追溯性]
P0-4  EU RAG 噪音清理               [影响 4 个 EU 模块检索质量]
│
├─ P1-1  15 索引重建                [CPU 密集，可后台运行]
├─ P1-2  RAG 命中回归               [P1-1 完成后执行]
└─ P1-3  引用利用率                  [P1-1 完成后执行]
│
├─ P2a  引用跳转（4 模块）           [手动浏览器操作]
├─ P2b  模块闭环（4 模块）           [手动浏览器操作]
└─ P2c  性能横切（4 模块）           [自动化脚本]

总预计时间：P0(~2h) + P1(~1h 重建 + ~0.5h 验证) + P2(~1h 浏览器操作) = ~4.5h
```

---

## 附录 A：CN-REG-005 条文清单

《个人信息出境标准合同办法》（2023年6月1日施行）共 13 条（注：条文号以官方正式公布的法规原文为准）：

| 条文 | 内容概要 |
|------|----------|
| 第一条 | 立法目的与依据 |
| 第二条 | 适用范围（个人信息处理者通过标准合同方式出境） |
| 第三条 | 基本原则（自主缔约+备案管理，保护权益+防范风险） |
| 第四条 | 适用条件（非CIIO、<100万人、<10万人/年、<1万敏感/年） |
| 第五条 | 个人信息保护影响评估义务 |
| 第六条 | 备案义务（合同生效后10个工作日内备案） |
| 第七条 | 重新评估与补充/重新订立合同的情形 |
| 第八条 | 监督管理 |
| 第九条 | 法律责任 |
| 第十条 | 施行日期（2023年6月1日） |
| 第十一条 | 合规整改过渡期（施行之日起6个月内） |
| 第十二条 | 解释权（国家互联网信息办公室） |
| 第十三条 | 附则 |

---

## 附录 B：模块-API-证据交叉引用

| 模块 | 后端路由器 | API 端点（生成） | 前端页面 | 测试覆盖 |
|------|-----------|-----------------|---------|---------|
| diagnosis | `domains/cn/transfer_diagnosis/router.py` | `POST /api/v1/diagnosis/evaluate` | `/diagnosis` | 7 files |
| assessment | `domains/cn/security_assessment/router.py` | `POST /api/v1/assessment/generate` | `/assessment` | 18 files |
| pipia | `domains/cn/pipia/router.py` | `POST /api/v1/pipia/generate` | `/pipia` | 6 files |
| review | `domains/cn/document_review/router.py` | `POST /api/v1/review/generate` | `/review` | 19 files |
| eu_scc | `domains/eu/scc_review/router.py` | `POST /api/v1/eu_scc/generate` | `/scc` | 3 files |
| bcr | `domains/eu/bcr_review/router.py` | `POST /api/v1/bcr/generate` | `/bcr` | 5 files |
| dpia | `domains/eu/dpia/router.py` | `POST /api/v1/dpia/generate` | `/dpia` | 4 files |
| tia | `domains/eu/tia/router.py` | `POST /api/v1/tia/generate` | `/tia` | 6 files |
| us_14117 | `domains/us/eo14117/router.py` | `POST /api/v1/us_14117/generate` | `/us-14117` | 7 files |
| cpra | `domains/us/cpra/router.py` | `POST /api/v1/cpra/generate` | `/cpra` | 12 files |
| cn_flow | `domains/us/eo14117_flow_review/router.py` | `POST /api/v1/cn-flow/generate` | `/cn-flow` | 委托 us_14117 |
| knowledge | `api/v1/endpoints/knowledge.py` | `GET /api/v1/knowledge/search` | `/evidence` | 8 files |

---

## 附录 C：未提交变更处理

当前工作区存在以下未提交变更：

| 文件 | 变更性质 | 处置建议 |
|------|----------|----------|
| `backend/services/knowledge_index.py` | `_parse_articles_from_text` 新增 EU/US 多法域解析器 | 待 P1-1 重建索引后提交（需测试验证） |
| 5 个 `resources/legal/sources/*/snapshots/*reference.md` | 删除（来自历史 commit 7fe7ac9） | 单独 commit 说明清理原因 |
| `status/todo/DataComplyFlow_知识库前端展示修复方案_20260810.md` | 修改 | 已纳入本方案 |
| `status/check/DataComplyFlow_知识库前端展示修复验收_20260810.md` | 新增（untracked） | 已纳入本方案 |

处理: 按执行阶段逐个 commit，每个阶段完成后 commit 一次，保持 git 历史清晰。

---

## 附录 D：与已有方案的整合关系

| 已有方案 | 本方案的定位 |
|----------|-------------|
| `DataComplyFlow_最终验收与收尾实施方案_20260810.md` | 本方案替代（原方案过于乐观，无视 P0 数据缺口） |
| `DataComplyFlow_知识库索引修复方案_20260810.md` | 本方案 P0+P1 是其执行层（继承问题诊断，追加执行步骤） |
| `DataComplyFlow_知识库前端展示修复方案_20260810.md` | 已部分提交（25793f1），剩余前端工作纳入 P2a/P2b |
| `DataComplyFlow_引用跳转闭环治理方案_20260806.md` | P2a 引用其验收标准，不重复分析 |
| `DataComplyFlow_架构统一迁移与可核验实施方案_20260808.md` | 已执行完毕（cn_flow → us_14117），P3 是其退出步骤 |
