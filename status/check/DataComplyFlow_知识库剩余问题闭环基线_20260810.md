# DataComplyFlow 知识库剩余问题闭环 — 基线快照

> 状态：当前基线
> 记录日期：2026-08-10
> Git commit：`5fe0c52`
> 分支：`new`
> 类型：Task 0.1 产物

---

## 环境

| 项目 | 版本 |
|---|---:|
| Python | 3.11.9 |
| Node | 23.11.0 |
| npm | 10.9.2 |
| uv | 0.11.2 |
| OS | macOS (x86_64) |

---

## Git 状态

```
M "status/view/DataComplyFlow_RAG与知识库系统详解_20260807.md"
```

`git diff --check`：通过（无空白错误）。

---

## Canonical 条文 (`regulation_articles.jsonl`)

| 指标 | 数值 |
|---|---:|
| 总条文数 | 1973 |
| 段落N 条文 | 0 |
| 空 article_ref | 0 |
| 空 content | 0 |
| 解析率 | 1973/1973 (100%) |
| 行自带 source_url | 565/1973 (28.6%) |
| CPRA 人工 -NN 后缀 | 5 (`§1798.140(ii)-01/02/03`, `§1798.145(i)-01/02`) |

### 来源类型分布

| 类型 | 数量 | 标签 |
|---|---:|---|
| LAW | 1129 | 法律 |
| REG | 513 | 法规/规章 |
| GUIDE | 146 | 指南 |
| CA | 88 | 州法律 |
| TPL | 42 | 模板 |
| SUP | 19 | 补充资料 |
| FED | 17 | 联邦法律 |
| GOV | 13 | 政府文件 |
| QA | 6 | 问答 |

---

## 来源注册表 (`source_registry.v1.json`)

| 指标 | 数值 |
|---|---:|
| 版本 | v1 |
| 来源数 | 102 |
| 生成源 | resources/legal/catalog/sources.csv |

---

## 完整性校验 (`check_citation_source_integrity.py --json`)

| 指标 | 数值 |
|---|---:|
| duplicate_keys | 0 |
| missing_article_ref | 0 |
| missing_url (脚本原始口径) | 0 |

---

## 索引 (`storage/rag/v3/`)

| 指标 | 数值 |
|---|---:|
| 索引文件总数 | 15 |
| 全索引总行数 | 1257 |

### 法律索引模块分布

| 法域 | 索引文件 | 行数 | 模块分布 |
|---|---|---|---|
| CN | legal_index_cn.jsonl | 618 | cn_assessment:250, cn_diagnosis:242, cn_pipia:71, cn_review:56 |
| EU | legal_index_eu.jsonl | 401 | eu_tia:101, eu_scc:101, eu_bcr:101, eu_dpia:99 |
| US | legal_index_us.jsonl | 192 | us_cpra:88, us_vendor_review:88, us_14117:17 |

### 其他索引

| 索引 | CN | EU | US |
|---|---|---|---|
| standard_clause | 4 | 2 | 2 |
| template | 9 | 3 | 2 |
| testcase | 4 | 3 | 2 |
| workflow | 6 | 3 | 6 |

---

## Case Parity

```
Case parity check passed (11 modules, 20 CLI cases carrying 424 leaf checks, 28 developer cases).
```

---

## 测试结果

### Backend

```
888 passed, 1 failed, 1 warning
FAILED backend/domains/eu/scc_review/tests/test_service.py::test_uploaded_scc_document_drives_core_review
```

### Frontend

```
Test Files: 25 passed | 1 skipped (26)
Tests:      129 passed | 2 skipped (131)
```
