# DataComplyFlow 案例体系统一与强断言方案

> 文档性质：**v2（已实施版）**。v1 为实施前设计草案，其核心前提在动工前核对时已被证伪，本版按实测事实重写
> 编制日期：2026-08-06
> 适用分支：`new`
> 实施提交：`d8cfa3a`（断言引擎）、`f3995c0`（15 例强断言）、`d05d69f`（对等门禁 + CI）
> 关联文档：`status/errorLog/DataComplyFlow_Schema契约修复与复验_20260806.md`、`status/todo/DataComplyFlow_Schema契约防漂移实施方案_20260806.md`

---

## 〇、一句话结论

前后端案例**不需要合并成一套**，需要的是两件事：让断言真的能失败，让两套案例的覆盖面被机器盯住。二者均已实施——CLI 15 例的有效断言从约 20 条升至 **259 条**，新增 `config/case_inventory.json` 对等门禁并接入 CI。

---

## 一、v1 前提的事实核对

动工前逐条核对 v1 的前提，四条中有三条已不成立。这是本次改写的直接原因。

| v1 前提 | 核对结果 | 证据 |
|---|---|---|
| 前端 26 例中 17 例 Schema 漂移 | **已失效**。漂移在 `8e71f60`…`6c7333c` 系列提交中修完，现为 26/26 | `frontend/tests/contract/dev-test-cases.api.test.ts` 断言 `submittedCases === 26` |
| 无 CI 门禁，需新建 workflow | **已失效**。`8d5ec64` 已建 `dev-case-contract.yml`，26 例走真实 HTTP | `.github/workflows/dev-case-contract.yml` |
| 后端 15 例断言仅 `result_not_empty` | **成立且比 v1 描述更严重**（见第二节） | `backend/tests/*/cases/*.json` 修改前状态 |
| 用 `jsonschema` draft-07 校验案例文件 | **前提缺失**。`jsonschema` 不是本仓依赖 | `pyproject.toml` 依赖列表 |

v1 的断言词表（`citation_count`、`fact_count`、`llm_call_count`、`duration_ms`、`citation_exact_article_count`、`rag_min_hits`）**在 11 个模块的真实返回结构中均不存在**。逐例 dump 15 份 `result.json` 核对后确认：若照 v1 落地，约 40 条断言会因字段不存在而误报失败，或因比较逻辑不匹配而空转通过。

---

## 二、真实缺口

### 2.1 断言在最需要它的模式下被跳过

改造前 `runner._check()` 有一段硬编码跳过：

```python
if field in {"risk_level", "conclusion_source"} and no_llm:
    continue
```

CI 与本地回归一律用 `--no-llm`。因此 diagnosis 三例中最有价值的 `risk_level`、`conclusion_source` 断言**从未在任何自动化环境中被执行过**。而这两个字段来自规则引擎，不经模型，本就是确定性的——实测三例分别稳定产出 `MEDIUM/rule`、`HIGH/rule`、`LOW/rule`。

### 2.2 未知断言键静默通过

改造前的比较逻辑对未知字段走 `actual.get(field) == expected_value`。写错键名时行为取决于巧合：`recomended_path` 会失败（`None != "scc_or_certification"`），但任何 `*_min_count` 形态的键都会因为做等值比较而恒假，且失败信息指向错误方向。没有任何机制能区分"断言通过"与"断言不存在"。

### 2.3 八个模块只有一例，且弱断言

`bcr`、`cn_flow`、`cpra`、`eu_scc`、`pipia`、`review`、`tia`、`us_14117` 各仅 1 例，`expected` 内容为 `{"result_not_empty": true}`。这些模块的报告章节数、风险结论、产物格式全部无断言覆盖。

---

## 三、已实施架构

### 3.1 断言引擎

`backend/tests/harness/validators.py` —— 断言词表的唯一定义处。

**路径寻址**。9 个算子通过路径访问结果字段，一套小词表覆盖 11 个模块，无需按模块扩展键名：

```
risk_level                        顶层标量
need_assessment.dpia_required     嵌套标量
chapters[].title                  在每个章节上投影 title
```

**未知算子硬失败**。`expected` 中出现词表外的键即失败并列出全部合法算子。**路径解析不到也是失败，不是跳过**——这正是要抓的漂移：案例引用了模块已不再产出的字段。

**九个算子**：

| 算子 | 语义 |
|---|---|
| `result_not_empty` | 结果至少有一个非空字段 |
| `fields_equal` | 路径 → 精确值 |
| `min_counts` / `max_counts` | 路径 → 数量下限/上限 |
| `list_contains` | 路径 → 子串列表，每个子串至少命中一个元素 |
| `output_formats` | `output_files` 值的扩展名集合 |
| `output_roles_contains` | `output_files` 的角色键 |
| `profile_contains` | `fields_equal` 在 `profile.` 下的可读糖 |
| `legal_basis_contains` | `list_contains` 在 `legal_basis` 上的可读糖 |

`min_counts` **拒绝字符串**。实施中一条测试抓到设计缺陷：对 `"HIGH"` 计数会得到 4 并通过。数字符串字符永远不是案例作者的意图，故字符串不可计数，改用 `fields_equal`。

### 3.2 取消硬编码跳过

以案例自身声明取代按字段名跳过：

- `expected` —— **无条件断言**，含 diagnosis 的规则派生 `risk_level`；
- `expected_llm_only` —— 仅当启用模型时断言，`--no-llm` 下计入 skipped 并在控制台显示。

规则派生结论因此在 CI 中真正生效。

---

## 四、四处偏离 v1 的设计决定

| # | v1 方案 | 实施方案 | 理由 |
|---|---|---|---|
| 1 | `_schema/test-case.schema.json` + `jsonschema` | Python `ASSERTION_OPERATORS` 为唯一真源 | 手维护的 JSON Schema 与验证器实现是**两个会互相漂移的真源**。引擎必须知道每个算子怎么比，Schema 只知道类型。单真源下写错键名必然失败，无需同步两份定义，也不新增依赖 |
| 2 | 约 25 个扁平命名键 | 4 个路径算子 + 5 个专用算子 | v1 词表里的字段大部分不存在；且每加一个模块字段就要加一个键。路径寻址下 `fields_equal` 一个算子覆盖 `recommended_path`、`rating`、`overall_rating`、`overall_traffic_light`、`route_type`、`filing_readiness.status`、`module_validation.expected_module` 等全部标量断言 |
| 3 | 新增 `GET /api/v1/test-cases/{module_key}` 运行时接口 | 不实现 | 该端点须用**用户可控的 `module_key` 拼接文件系统路径**（v1 示例代码即 `Path("resources/test-cases") / module_key`），是路径穿越面；且把测试夹具装进生产应用。相对"提交一份清单"没有任何收益 |
| 4 | 案例迁至 `resources/test-cases/`，前端改运行时加载 | 保留 `backend/tests/<module>/cases/`，前端 26 例不动 | 迁移会破坏 review 夹具相对路径与 harness 路径约定，功能收益为零。前端 26 例已被 HTTP 门禁保护且 `formDefaults` 是纯前端概念，为去重而重构会拿一个已经工作的门禁去换有限收益 |

### 4.1 对等改用"提交式清单"

真正的对等价值不在合并案例，而在**两套案例的覆盖面都被盯住**。`config/case_inventory.json` 记录每模块的 CLI 例数、逐例断言数、前端例数：

- Python 侧 `scripts/check_case_parity.py` 校验 CLI 现实与清单一致；
- TypeScript 侧 `frontend/tests/contract/case-inventory.test.ts` 读**同一份文件**校验前端现实。

两侧各自独立推导，无跨语言解析依赖，任一侧漂移在自己的门禁失败。此形态与本仓既有 `config/local_new_parity_manifest.json` + `scripts/check_local_new_parity.py` 一致。

---

## 五、断言现状

| 模块 | CLI 例 | 前端例 | 断言数 |
|---|---:|---:|---:|
| assessment | 2 | 2 | 42 |
| bcr | 1 | 3 | 15 |
| cn_flow | 1 | 2 | 19 |
| cpra | 1 | 3 | 18 |
| diagnosis | 3 | 3 | 35 |
| dpia | 2 | 2 | 50 |
| eu_scc | 1 | 3 | 18 |
| pipia | 1 | 2 | 16 |
| review | 1 | 2 | 9 |
| tia | 1 | 2 | 15 |
| us_14117 | 1 | 2 | 22 |
| **合计** | **15** | **26** | **259** |

全部断言值取自 15 份实测 `result.json`，非推测。易变量（RAG 检索条数、规则命中数）取下限，模板决定的固定量（章节数、产物角色）取精确值。

静态计数器（`count_leaf_checks`）独立算出的 259 与运行时实际执行的 259 逐模块吻合，构成交叉验证。

---

## 六、门禁

### 6.1 对等门禁强制的性质

`scripts/check_case_parity.py`（`--write` 刷新清单，默认校验）：

1. 11 个注册模块两侧均有案例；
2. 每例 `case_id` 与文件名一致、`description` 非空、`input` 非空；
3. `expected` / `expected_llm_only` 只用词表内算子；
4. **断言下限 8 条**——防止案例退化回裸 `result_not_empty`。下限取当前最弱案例（review 9 条），只可上调不可静默下调；
5. `known_defects` 每条须说明 `field` / `observed` / `reason`；
6. 清单与磁盘、前端注册表逐项对齐。

首次运行即抓出 5 个真实缺陷：3 例 diagnosis 的 `case_id` 与文件名不符、eu_scc 的 `known_defects` 结构不合规、review 缺 `description`，均已修。

### 6.2 门禁自身的变异测试

`backend/tests/harness/test_case_parity.py` 逐项破坏后断言门禁必须失败：算子拼写错误、断言数低于下限、清单漏记案例、前端例数漂移、模块整体缺失。

其中"前端例数漂移"一项**在编写时即抓到门禁自身的漏洞**：`inventory_violations` 当时未比较 `frontend_cases`，删除一个前端案例不会让 Python 门禁失败。已修。

### 6.3 CI

`dev-case-contract.yml` 新增 `harness` job（与既有 `contract` job 并行）：对等门禁 → 引擎与门禁测试 → 15 例离线断言 → 上传 run 产物。

已验证 **CI 可复现**：清空 storage 目录、无预建索引的条件下 assessment 仍 24/24 通过、耗时 5 秒——法条 JSONL 已入版本库，7 MB 索引运行时本地重建，不需要网络。

---

## 七、实施中发现的产品缺陷（需你决策）

`backend/domains/eu/scc_review/scc_rule_engine.py:181`

```python
is_correct = _normalize(actual) == _normalize(expected)
```

`expected` 是英文标签 `"Module Two"`，`actual` 是调用方原样传入的 `declared_module_type`。逐字比较导致：

| 调用方 | 传入值 | `is_correct` |
|---|---|---|
| CLI 案例 | `"2"` | false |
| 前端 3 例 | `"C2P"` | false |
| 现有单测 | `"Module Two"` | true |

**任何真实调用方都拿不到 true**，每次 SCC 审查都会产出一条虚假的"模块选择错误"发现，并进入 `issues`、`findings`、报告正文与整体评级。现有单测之所以全绿，是因为它们传的值没有任何真实客户端会传。

前端 HTTP 门禁也抓不到：它只断言请求被接受，不校验结果内容。

我未擅自修改——这是合规规则引擎的判定逻辑，且"哪个是规范输入格式"是产品决定。案例中以 `known_defects` 记录并暂缓该条断言，同时断言了确实正确的部分（角色 → 模块推导）。两个选项：

- **A**：在 `validate_module_selection` 内做输入归一化，接受 `"2"` / `"C2P"` / `"Module Two"` 三种写法映射到同一模块。改动小，但要同步修 3 处现有单测的期望值。
- **B**：把 `declared_module_type` 收紧为闭合枚举，前后端统一送标准值，规则引擎不变。契约更干净，但要改前端 3 例与表单 Builder。

倾向 A：现有两种真实写法都已在生产数据里，收紧枚举会让历史任务的重放失败。

---

## 八、待办

| 优先级 | 事项 | 说明 |
|---|---|---|
| P0 | eu_scc `declared_module_type` 归一化 | 见第七节，需你选 A 或 B |
| P1 | 8 个单例模块补第二例 | `bcr`、`cn_flow`、`cpra`、`eu_scc`、`pipia`、`review`、`tia`、`us_14117`。前端已有 2-3 例可作输入来源，边界场景（高风险、结构缺失、受限方）尚无 CLI 覆盖 |
| P1 | 启用 `expected_llm_only` | 引擎已支持，当前 0 例使用。真实 LLM 模式下的章节内容、引用条文准确性需要这一层，但须先有一次可信的联网基线跑 |
| P2 | 断言下限从 8 上调 | review 补强到 15 条以上后可提升下限，形成棘轮 |
| P2 | 报告正文内容断言 | 现有断言覆盖结构化字段与产物，未读取 `.md` 正文。`chapters[].title` 已覆盖标题层，正文关键句断言待评估必要性 |

---

## 九、验收证据

| 验证项 | 命令 | 结果 |
|---|---|---|
| 断言引擎 + 门禁测试 | `uv run --frozen pytest -q backend/tests/harness/` | 37 passed |
| 后端全量 | `uv run --frozen pytest -q` | **579 passed**（改造前 563） |
| 前端全量 | `npm --prefix frontend test -- --run` | 20 files / 71 passed, 1 skipped |
| CLI 15 例离线 | `uv run --frozen python -m backend.tests.harness.runner all --no-llm` | **15 PASS / 0 FAIL，259 断言全通过** |
| 对等门禁 | `uv run --frozen python scripts/check_case_parity.py` | passed（11 模块 / 15 CLI 例 / 259 leaf checks / 26 前端例） |
| 仓库卫生 | `uv run --frozen python scripts/check_repository_hygiene.py` | passed（1273 files） |
| CI 可复现性 | 空 storage 目录跑 assessment | 24/24 passed，5 秒，无网络 |

15/15 与 259 条断言均在 `--no-llm` 下取得，只能证明离线服务链、规则引擎与渲染链正确，**不能证明真实模型、Token 计量或外部 Provider 正常**。真实 LLM 模式的断言覆盖是第八节 P1 事项。
