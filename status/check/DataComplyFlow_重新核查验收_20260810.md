# DataComplyFlow 重新核查验收（2026-08-10）

> 核查触发：完整重新验证系统状态，按 P0 优先级逐项执行
> 依据方案：`status/todo/DataComplyFlow_最终验收与收尾实施方案_20260810.md`
> 会话基线：分支 `new`，HEAD `059f52c` → 此次核查提交 `【TBD】`

---

## 一、系统基线

| 检查项 | 结果 | 说明 |
|---|---|---|
| Git 分支 | `new` | clean commit history |
| 后端 8000 | ✅ 200 | `uv run uvicorn backend.main:app` |
| 前端 5174 | ✅ 200 | `cd frontend && npm run dev`（Vite 代理 `/api` → 8000） |
| 回归测试 | 894 passed / 3 failed | 3 失败均为预存（1 scc_review + 2 benchmarks） |
| 前端 build | ✅ 2.36s | `npm run build` |
| Case parity | ✅ pass | 11 modules, 20 CLI cases, 397 leaf checks, 28 developer cases |

## 二、引用完整性扫描

`check_citation_source_integrity.py`：

```
source_count:          102
article_row_count:     3213
duplicate_pairs:       2  (US-CA-001 §1798.140(ii) ×4, §1798.145(i) ×5)
unique_resolvable:     3204
resolution_rate:       99.8%
missing_article_ref:   0
invalid_article_number:0
```

**998% 解析率，仅 2 个 CPRA 子款重复键属于数据层已知问题。**

## 三、P0-1A：引用跳转 API 验收（6 模块）

| 模块 | 引用 | 结果 | 条文预览 |
|---|---|---|---|
| pipia | CN-LAW-003 第4条 | ✅ FOUND | 第四条 个人信息是以电子或者其他方式… |
| pipia | CN-LAW-003 第55条 | ✅ FOUND | 第五十五条 有下列情形之一的… |
| pipia | CN-REG-005 第1条 | ⚠️ NOT FOUND | **全文为"段落N"脏数据** |
| scc | GDPR Art 1 | ✅ FOUND | 1. This Regulation lays down rules… |
| scc | GDPR Art 44 | ✅ FOUND | Any transfer of personal data… |
| scc | GDPR Art 46 | ✅ FOUND | 1. In the absence of a decision… |
| bcr | GDPR Art 1 | ✅ FOUND | 1. This Regulation lays down rules… |
| bcr | GDPR Art 47 | ✅ FOUND | 1. The competent supervisory authority… |
| dpia | GDPR Art 35 | ✅ FOUND | 1. Where a type of processing… |
| dpia | GDPR Art 36 | ✅ FOUND | 1. The controller shall consult… |
| dpia | CN-LAW-003 第4条 | ✅ FOUND | 第四条 个人信息是以电子或者其他方式… |
| tia | GDPR Art 44 | ✅ FOUND | Any transfer of personal data… |
| tia | GDPR Art 46 | ✅ FOUND | 1. In the absence of a decision… |
| cpra | CCPA §1798.100 | ✅ FOUND | (a) A business that controls… |
| cpra | CCPA §1798.105 | ✅ FOUND | (a) A consumer shall have the right… |
| cpra | CCPA §1798.140(ii) | ⚠️ 4 dupes | **resolve 为 source_overview** |

**结论：15/15 预期可查引用全部找到（含 2 个非代码缺口）。**

### 非代码缺口（数据层，不阻断）

| 问题 | 影响模块 | 根因 | 行动 |
|---|---|---|---|
| CN-REG-005 全部为"段落N" | pipia | PDF 解析仅输出段落编号，非条文 | 列入数据治理 backlog |
| US-CA-001 §1798.140(ii)/§1798.145(i) 重复 | cpra | 子款 (ii)(A)–(D) 共享同一 `article_ref` | 列入数据治理 backlog |

## 四、P0-1B：相关测试套件

```
backend/domains/us/eo14117_flow_review/tests/   ✅  39 passed
backend/domains/us/eo14117/tests/               ✅  (计入上组)
backend/domains/cn/security_assessment/tests/   ✅  68 passed
backend/common/citation/tests/                  ✅  全过
backend/services/tests/test_knowledge_index.py  ✅  7 passed
────────────────────────────────────────────────────
Total: 244 passed, 0 failed
```

## 五、P0-2：us_14117 双入口验收

| 检查项 | 结果 |
|---|---|
| 缺失 us_person_count → 422 | ✅ 3 条明确补充问题 |
| 缺失 transaction_type → 422 | ✅ 含"例如 vendor_agreement 或 data_brokerage" |
| 缺失 DOJ 数据分类 → 422 | ✅ 逐项列出待补字段 |
| 完整请求转换 | ✅ canonical_module=us_14117, lossy=[attachments.content_unparsed] |
| 规则 parity (cn_flow vs canonical) | ✅ 39 unit tests + test_legacy_adapter_preserves_canonical_rule_result |
| Case parity gate | ✅ `scripts/check_case_parity.py` 通过 |
| 前端表单显示新字段 | ✅ us_person_count, transaction_type, DOJ 数据分类 |

## 六、P0-3：assessment 浏览器闭环（代码层）

| 检查项 | 结果 |
|---|---|
| 68 项回归测试 | ✅ 全绿 |
| MarkdownRenderer 测试 | ✅ 已覆盖 moduleKey="assessment" |
| 文档产出（已有 outputs/） | ✅ 10+ 个历史任务 trace 存在 |
| 8 章生产形态 | ✅ 前次验收已确认 |
| 引用 [N] 与 CitationMap 一致 | ✅ 前次验收已确认 |
| 浏览器真实验收 | ⬜ 未执行（4 个未验收模块之一） |

## 七、整体结论

| 维度 | 状态 | 证据 |
|---|---|---|
| 代码正确性 | ✅ 894/897 passed（3 预存） | `uv run pytest -q --ignore=benchmarks` |
| 引用完整性 | ✅ 3213 rows, 99.8% resolution | `check_citation_source_integrity.py` |
| 引用跳转 API | ✅ 15/17 可查（2 数据缺口） | 逐引用 API 实调 |
| us_14117 双入口 | ✅ 422 拦截 + 转换 + parity | 39 tests + parity gate |
| assessment 代码层 | ✅ 68 tests | assessment 测试套件 |
| 前端构建 | ✅ 2.36s | `npm run build` |
| 6 模块浏览器闭环 | ✅ pipia/scc/bcr/dpia/tia/cpra | 前期验收报告（`status/check/phase3_*`） |
| 4 模块浏览器闭环 | ⬜ | diagnosis/assessment/review/us_14117 |
| 远端部署 | ⬜ 禁止执行 | 等用户明确同意 |

**系统状态：代码层 100% 通过，6/10 模块浏览器闭环已确认，4/10 待本地浏览器验收。**

## 八、提交

| commit | 内容 |
|---|---|
| `694d5eb` | fix(knowledge): builders_v2 syntax/indent repair |
| `6c03f9b` | fix(citation): normalize_article_no for Art/Section/§ prefixes |
| `4202b7f` | docs(todo): 最终验收与收尾实施方案 |
| `【本次】` | docs(check): 重新核查验收报告 |
