# DataComplyFlow `resources/new` 全量资源分层迁移执行记录

> 日期：2026-08-12
> 方案：`status/todo/DataComplyFlow_resources_new全量资源分层迁移与登记方案_20260812.md`
> 状态：Phase 0-4 执行完成，Phase 5（退出）待执行

## 执行摘要

207 个文件已全部分类并迁移到规范目标目录。89 个 COPIED_HASHED 文件已完成消费者路径切换；118 个 PENDING 文件已完成物理迁移（副本到目标目录），源文件保留等待 Phase 5 退出。

## Phase 0：冻结与新台账 ✅

- **manifest.v2.json**：`status/manifest/resources_new_v2_phase0.json`，207/207 文件均有 SHA-256、MIME、asset_class、target、status
- 3 份旧台账已复制到 `resources/research/migration-ledger/resources-new-20260807/`
- 诊断说明 Hash 裁决：根目录与嵌套版本同 Hash（117a0267），与 benchmarks 版本不同（4c42b337），均已版本化保留

## Phase 1：规范副本引用切换 ✅

### 已切换的消费者路径

| 消费者 | 数量 | 操作 |
|---|---|---|
| 共享 Scenario `source.file` | 22 | `resources/new/…` → `benchmarks/source-materials/…` |
| CLI case `source_doc_path` | 13 | 同上 |
| PIPIA Scenario attachments | 3 | `storage_uri` 切换 |
| `config/dev_case_catalog.json` | 1 | `source_directories` + 25 个 `source_file` |
| 前端 E2E fixture | 1 | 路径切换 |
| 前端 dev-test-cases.ts 注释 | 16 | 来源路径已更新 |

### 验证

```
Case parity + semantic check passed (11 modules, 26 CLI cases, 603 leaf checks, 28 developer cases)
32/32 harness tests passed
```

## Phase 2：区域法规原件归位 ✅

### 51 个 PDF 原件

| 法域 | 数量 | 目标目录 | Hash |
|---|---:|---|---|
| sg（新加坡） | 6 | `resources/legal/sources/sg/references/` | ✅ |
| vn（越南） | 6 | `resources/legal/sources/vn/references/` | ✅ |
| my（马来西亚） | 8 | `resources/legal/sources/my/references/` | ✅ |
| jp（日本） | 9 | `resources/legal/sources/jp/references/` | ✅ |
| kr（韩国） | 7 | `resources/legal/sources/kr/references/` | ✅ |
| hk（香港） | 7 | `resources/legal/sources/hk/references/` | ✅ |
| mo（澳门） | 3 | `resources/legal/sources/mo/references/` | ✅ |
| tw（台湾） | 5 | `resources/legal/sources/tw/references/` | ✅ |

### 10 个目录文件

- 5 HTML → `resources/legal/catalog/source-packets/regional/{sg,vn,my,jp_kr,hk_mo_tw}.html`
- 5 MD 确认与 HTML 同内容 → Phase 5 DEDUP_DROP

### 脚本更新

- `scripts/ingest_regional_laws.py`：PDF_BASE → `resources/legal/sources`，编译通过

### 待后续

- sources.csv snapshot_path/origin_path 逐文件更新
- registry builder 扩展 8 个区域法域
- 区域条文 article_id 补齐
- V3 legal_index_intl 建立

## Phase 3：Gold 与 50 个种子案例 ✅

- Gold Standard：1/1 → `benchmarks/datasets/seed-cases-v1/_source/`
- 种子案例：50/50 → `task01/`~`task10/`，各 5 例
- `benchmarks/datasets/seed-cases-v1/manifest.json` 已生成
- `scripts/build_seed_case_inputs.py`：SRC_DIR 已切换，编译通过

### 待后续

- [ ] `build_seed_case_inputs.py --write` 生成 50 个 input JSON
- [ ] 法律专家审核 expected
- [ ] 任务 4/6/7/8 module_id 冲突裁决
- [ ] rubric.v1.json 生成

## Phase 4：PRD、研究材料和 Review 附件 ✅

- PRD → `resources/research/product-design-sources/00_index/`
- 根目录诊断 → `benchmarks/source-materials/cn/legacy-docx/`（版本化）
- Review 附件 4 个 → `benchmarks/source-materials/cn/review/fixtures/`
- `resources/research/module-specs/` 12 模块 README 已创建

### 待后续

- [ ] `docs/handoff/DataComplyFlow_需求基线与当前实现映射_20260812.md`
- [ ] module-specs Markdown 转换
- [ ] `source-materials-manifest.csv`（30 份）

## Phase 5：退出（待执行 ⬜）

- [ ] `rg "resources/new"` 活动代码为 0（当前 scripts/ 保留注释性引用）
- [ ] `phase1_generate/analyze` 脚本归档
- [ ] 越南网络安全法 17.2MB LFS 确认
- [ ] 删除 .DS_Store、重复 MD、空目录
- [ ] `resources/new` 为空后删除

## 验证矩阵

| 层 | 状态 |
|---|---|
| 207 文件全量分类 | ✅ |
| manifest v2 | ✅ |
| Case parity (603 checks) | ✅ |
| 32 harness tests | ✅ |
| CLI LLM 26/26 | ✅ |
| 前端构建 | 待验证 |
| RAG 区域检索 | 待重建索引 |
| Phase 5 退出 | ⬜ |

---

## Phase 5 执行更新（2026-08-12）

### 已执行清理

| 操作 | 数量 | 状态 |
|---|---|---|
| 删除同内容重复 MD 目录文件 | 5 | ✅ |
| DS_Store 清除 | 0（此前已清除） | ✅ |
| 空目录清理 | 2 | ✅ |
| phase1 脚本废除 | 2（generate + analyze） | ✅ |
| PIPIA case 03 storage_uri 残留修复 | 1 | ✅ |
| 全量 rg 活动代码扫描 | 0 功能性依赖 | ✅ |

### 当前 `resources/new` 状态

- 保留 202 个原始文件作为安全副本
- 活动代码、配置、测试零功能性依赖
- `resources/new` 尚未删除（按方案要求：目录为空后才允许删除）

### Git 提交

```
992ef07 feat(resources): Phase 0-4 — 全量资源分层迁移执行
d4ca2fe feat(resources): Phase 5 — 旧目录安全清理完成
```
