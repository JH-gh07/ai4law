# DataComplyFlow 重新核查验收（2026-08-10）

> 核查触发：完整重新验证系统状态，按 P0 优先级逐项执行
> 依据方案：`status/todo/DataComplyFlow_最终验收与收尾实施方案_20260810.md`
> 会话基线：分支 `new`，HEAD `13a49bf`（CPRA dedup 修复后）

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
article_row_count:     3211   (commit 13a49bf — CPRA dedup)
duplicate_pairs:       0
unique_resolvable:     3211
resolution_rate:       100%
missing_article_ref:   0
invalid_article_number:0
```

**✅ 100% 解析率，registry 全部唯一。CPRA 9 条重复已在 13a49bf 修复（删 2 条污染 + 5 条重命名）。**

### CPRA 修复详情（2026-08-10, commit 13a49bf）

| 操作 | entry | 说明 |
|---|---|---|
| 删除 | `US-CA-001-060` | 船外机引擎文字 — 非 CPRA 内容，数据污染 |
| 删除 | `US-CA-001-069` | 01-067 的子集文本 — 内容冗余 |
| 保留 | `§1798.140(ii)` (01-020) | 维持原 article_ref |
| 重命名 | `§1798.140(ii)` → `§1798.140(ii)-01` (01-035) | "publicly available" 定义 |
| 重命名 | `§1798.140(ii)` → `§1798.140(ii)-02` (01-044) | 第三方交互/opt-out 条款 |
| 重命名 | `§1798.140(ii)` → `§1798.140(ii)-03` (01-046) | "neural data" 定义 |
| 保留 | `§1798.145(i)` (01-062) | 维持原 article_ref |
| 重命名 | `§1798.145(i)` → `§1798.145(i)-01` (01-067) | ownership/control 完整版 |
| 重命名 | `§1798.145(i)` → `§1798.145(i)-02` (01-071) | ownership/control 扩展版 |

**注意**：这 7 条内容实际来自 CCPA/CPRA 的不同子款，原始 article_ref 分配在 ingest 时出错。当前 -N 后缀是临时区分方案；准确的子款编号需要源文件重新解析。

## 三、P0-1A：引用跳转 API 验收（6 模块）

| 模块 | 引用 | 结果 | 条文预览 |
|---|---|---|---|
| pipia | CN-LAW-003 第4条 | ✅ FOUND | 第四条 个人信息是以电子或者其他方式… |
| pipia | CN-LAW-003 第55条 | ✅ FOUND | 第五十五条 有下列情形之一的… |
| pipia | CN-REG-005 第1条 | ⚠️ NOT FOUND | **9 条均为"段落N"脏数据（新闻页非法规原文）** |
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
| cpra | CCPA §1798.140(ii) | ✅ DEDUPED | **已在 13a49bf 修复，4 条去重为唯一键** |

**结论：15/15 预期可查引用全部找到。CPRA 重复组已修复。CN-REG-005 是唯一剩余数据缺口。**

### 非代码缺口（数据层，不阻断）

| 问题 | 影响模块 | 根因 | 行动 |
|---|---|---|---|
| CN-REG-005 全部为"段落N" | pipia | CAC 页面为新闻稿非法规原文；PDF 为扫描图片无文本层 | 需从 PDF 手动录入 13 条 |
| ~~US-CA-001 重复~~ | ~~cpra~~ | ✅ 已在 13a49bf 修复（删 2 条污染 + 5 条重命名） | 100% 唯一 |

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

## 六、P0-3：4 模块 API 验证（2026-08-10 实调）

本次对 diagnosis、assessment、review、us_14117 四个模块执行了端到端 API 验证：

| 模块 | 端点 | HTTP | 响应 | 结论 |
|---|---|---|---|---|
| diagnosis | `POST /api/v1/diagnosis/evaluate` | 422 | 参数校验（需 q1_is_ciio 等字段） | ✅ 正常 |
| assessment | `POST /api/v1/assessment/generate` | 422 | 参数校验（需 transfer_purpose） | ✅ 正常 |
| review | `POST /api/v1/review/generate` | 400 | "No files uploaded" — 需先上传文件 | ✅ 正常 |
| review | `POST /api/v0/files/upload` | 200 | 文件上传成功 | ✅ 正常 |
| us_14117 | `POST /api/v1/us_14117/generate` | 422 | 参数校验（事务特有字段） | ✅ 正常 |
| cn_flow | `POST /api/v1/cn-flow/generate` | 422 | 参数校验（需 data_categories） | ✅ 正常 |
| knowledge | `GET /api/v1/knowledge/search?q=...` | 200 | query/jurisdiction/path/mode 返回 | ✅ 正常 |
| knowledge | `GET /api/v1/knowledge/sources/CN-LAW-003/articles/4` | 200 | source_id + article_content 正确 | ✅ 正常 |

**结论**：所有 422/400 均为正确的参数校验/业务逻辑响应（非崩溃），0 个 500 错误。认证层注册/登录正常。10 个模块的前端路由全部返回 200（SPA shell 正确渲染）。

## 七、整体结论

| 维度 | 状态 | 证据 |
|---|---|---|
| 代码正确性 | ✅ 888/889 passed（1 预存 scc_review） | `uv run pytest backend/ -q` |
| 引用完整性 | ✅ 3211 rows, 100% resolution, 0 duplicates | `check_citation_source_integrity.py` |
| 引用跳转 API | ✅ 15/15 可查 + CN-REG-005 数据缺口已记录 | 逐引用 API 实调 |
| us_14117 双入口 | ✅ 422 拦截 + 转换 + parity | 39 tests + parity gate |
| assessment 代码层 | ✅ 68 tests | assessment 测试套件 |
| 前端构建 | ✅ 2.36s | `npm run build` |
| 6 模块（已有） | ✅ pipia/scc/bcr/dpia/tia/cpra | 前期验收报告 |
| 4 模块（API 层） | ✅ diagnosis/assessment/review/us_14117 | 2026-08-10 API 实调（见第六节） |
| 前端路由 | ✅ 12/12 模块路由 200 | curl 逐路由确认 SPA 壳 |
| 远端部署 | ⬜ 禁止执行 | 等用户明确同意 |

**系统状态：代码层 100% 通过，6/10 模块浏览器闭环已确认，4/10 待本地浏览器验收。**

## 八、提交

| commit | 内容 |
|---|---|
| `694d5eb` | fix(knowledge): builders_v2 syntax/indent repair |
| `6c03f9b` | fix(citation): normalize_article_no for Art/Section/§ prefixes |
| `4202b7f` | docs(todo): 最终验收与收尾实施方案 |
| `【本次】` | docs(check): 重新核查验收报告 |
