# Config 静态契约

本目录只保存需要被多个技术栈共同读取、适合提交到 Git 的静态契约。它不是后端运行配置目录，也不得存放密钥、本地路径或运行产物。

## 目录总览

```
config/
├── README.md                       本文件
├── module_registry.json            模块稳定身份的跨语言权威清单（11 模块）
├── case_inventory.json             案例盘库（CLI 案例数 + 叶断言数 + 前端案例数）
├── dev_case_catalog.json           开发者案例目录（28 条，溯源到来源材料）
└── local_new_parity_manifest.json  本地 new 分支迁移台账（56 条归置记录）
```

| 文件 | 作用 | 消费方 |
|------|------|------|
| `module_registry.json` | 模块稳定身份与法域契约的**权威清单** | 前端 `module-registry.ts`、后端契约测试、harness、治理脚本 |
| `case_inventory.json` | 案例盘库的**基准快照**（断言数门禁） | `check_case_parity.py`、前端契约测试、seed 构建脚本 |
| `dev_case_catalog.json` | 开发者案例 → 来源材料的**溯源目录** | `check_case_parity.py`、`build_case_disposition.py` |
| `local_new_parity_manifest.json` | 本地 `new` 分支相对权威源的**迁移台账** | `check_local_new_parity.py`、仓库卫生测试 |

---

## `module_registry.json`

该文件是模块稳定身份的跨语言权威清单，供前端映射、后端契约测试和治理工具读取。后端 Router 仍由 `backend/api/v1/router.py` 显式装配；前端不得通过本文件生成或控制后端路由。

**结构**：11 个模块条目组成的数组，每个条目字段：

| 字段 | 说明 |
|------|------|
| `module_id` | 跨前后端、Trace 与 Benchmark 使用的稳定业务身份 |
| `jurisdiction` | `cn`、`eu` 或 `us` 法域 |
| `frontend_key` | 现有前端兼容键 |
| `task_template_id` | 前端任务模板身份 |
| `implementation_package` | 当前可导入的后端实现包 |
| `v1_api_prefix` | 已发布的 v1 业务路径前缀 |
| `lifecycle` | `active` 或 `legacy-compatible` |
| `note`（可选） | 仅用于解释无法从字段本身表达的兼容边界 |

**模块清单**：

| module_id | 法域 | frontend_key | lifecycle |
|-----------|:---:|:---:|:---:|
| `cn.transfer_diagnosis` | cn | diagnosis | active |
| `cn.security_assessment` | cn | assessment | active |
| `cn.document_review` | cn | review | active |
| `cn.pipia` | cn | pipia | active |
| `us.eo_14117_flow_review` | us | cn_flow | **legacy-compatible** |
| `eu.scc_review` | eu | eu_scc | active |
| `eu.bcr_review` | eu | bcr | active |
| `eu.dpia` | eu | dpia | active |
| `eu.tia` | eu | tia | active |
| `us.eo_14117` | us | us_14117 | active |
| `us.cpra` | us | cpra | active |

> 唯一 `legacy-compatible` 项为 `us.eo_14117_flow_review`（frontend_key=`cn_flow`），其 `note` 说明历史键为兼容而保留，当前检索、规则与输出均为 EO 14117 / US 导向。

修改本文件后必须运行：

```bash
uv run --frozen pytest -q backend/core/tests/test_module_registry.py
cd frontend && npm test -- src/lib/module-registry.test.ts
```

禁止将运行时 LLM、数据库或外部服务凭据写入本目录；相关变量样例只允许以空值形式出现在仓库根目录 `.env.example`。

---

## `case_inventory.json`

案例盘库的基准快照，被 `scripts/check_case_parity.py` 门禁用于检测「案例数 / 断言数漂移」。顶层结构：

- `schema_version`: `1.0`
- `assertion_floor`: 每个案例断言数的下限（当前 `8`）
- `modules`: 11 个模块的盘库，每个模块含 `module_id`、`cli_cases`（每案例的 `case_id` + `assertions`）、`frontend_cases`（前端案例数）

**当前盘库汇总**：

| 模块 | CLI 案例 | 叶断言 | 前端案例 |
|------|:---:|:---:|:---:|
| assessment | 2 | 42 | 2 |
| bcr | 2 | 47 | 3 |
| cn_flow | 2 | 38 | 2 |
| cpra | 1 | 28 | 3 |
| diagnosis | 3 | 35 | 3 |
| dpia | 2 | 50 | 2 |
| eu_scc | 3 | 78 | 3 |
| pipia | 5 | 140 | 3 |
| review | 1 | 9 | 2 |
| tia | 2 | 70 | 2 |
| us_14117 | 3 | 66 | 3 |
| **合计** | **26** | **603** | **28** |

> 该文件由脚本在案例变更后同步刷新；若新增/删除 CLI 案例或调整断言数而未同步本文件，`check_case_parity.py` 会报 inventory 漂移。

---

## `dev_case_catalog.json`

开发者案例目录，记录每个开发者案例到其**来源材料**的溯源关系，供 `check_case_parity.py` 与 `build_case_disposition.py` 使用。

- `schema_version`: `1.0`
- `source_directories`: 来源材料根目录（`benchmarks/source-materials`、`benchmarks/datasets/seed-cases-v1`）
- `cases`: 28 条记录，每条含：
  - `case_id`（如 `cpra-01`）
  - `module`（如 `cpra`）
  - `classification`：`source_exact` / `compatibility_adapter` / `product_extension`
  - `source_file`：来源材料路径
  - `source_case`：来源案例名称

**classification 分布**：`source_exact` 25 条、`compatibility_adapter` 2 条、`product_extension` 1 条。

**按模块分布**：cn_flow 2、cpra 3、review 2、us_14117 3、其余模块（assessment/bcr/diagnosis/dpia/eu_scc/pipia/tia）各 2–3 条。

> 该目录是「开发者案例 → 来源」的登记台账，不直接参与运行时；来源文件是否真实存在由 `check_case_parity.py` 门禁校验。

---

## `local_new_parity_manifest.json`

本地 `new` 分支相对权威源的迁移台账，冻结了迁移决策，供 `scripts/check_local_new_parity.py` 与仓库卫生测试校验。

- `schema_version`: `1`
- `source_ref` / `source_sha`: 权威源分支 `archive/local-original`（`ab4be948…`）
- `target_ref` / `target_sha`: 目标分支 `origin/new`（`a0f26fe6…`）
- `common_ancestor_sha`: 共同祖先 `398e8acd…`
- `forbidden_source_refs`: `["archive/local-full"]`
- `excluded_runtime_paths`: `storage/`、`runs/`、`**/.DS_Store`、`frontend/tmp.zip`
- `source_delta_summary`: 相对源分支的增量（added 34 / modified 21 / deleted 1 / total 56）
- `module_ids`: 11 个模块身份
- `items`: 56 条归置记录，每条含 `source_path`、`source_change`（A/M/D）、`target_path`、`disposition`、`evidence`

**disposition 分布**：`rewrite` 24、`migrate` 17、`archive` 5、`keep-target` 5、`reject-with-evidence` 5。

| disposition | 含义 |
|------|------|
| `migrate` | 原样迁移到 target |
| `rewrite` | 迁移但需重写（保留语义，修正实现） |
| `archive` | 归档，不进入活动路径 |
| `keep-target` | 保留 target 侧版本 |
| `reject-with-evidence` | 拒绝迁移并附证据 |

> 该台账是迁移决策的**冻结快照**，由 `check_local_new_parity.py` 对照 Git 历史校验一致性。

---

## 治理约束

- 本目录**只存静态契约**，禁止存放运行时 LLM / 数据库 / 外部服务凭据。
- 禁止把本地路径、密钥或运行产物（`storage/`、`runs/`、`outputs/` 内容）写入本目录。
- `module_registry.json` 修改后必须跑后端契约测试与前端单测；`case_inventory.json` 修改后必须跑 `scripts/check_case_parity.py` 确认无漂移。
