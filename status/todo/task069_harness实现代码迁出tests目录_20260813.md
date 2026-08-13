# task069 — harness 实现代码迁出 tests 目录实施方案

> 日期：2026-08-13
> 范围：本地开发/测试/验收；未连接远程、未部署、未修改远程数据
> 关联：issue（无）——用户指出 `backend/tests/harness/` 中实现代码与测试文件混放，且 `scripts/check_case_parity.py` 反向依赖 `backend/tests/`

## 一、问题

`backend/tests/harness/` 混放了两类文件：

| 类别 | 文件 | 性质 |
|---|---|---|
| 实现（工具/CLI 入口） | `runner.py` / `validators.py` / `viewer.py` / `terminal_trace.py` | 均有 `__main__` + `argparse` |
| 测试 | `test_harness.py` / `test_case_parity.py` / `test_seed_case_inputs.py` / `test_seed_case_requests.py` / `test_terminal_trace.py` / `test_validators.py` | `test_*.py` |

倒置依赖（根本原因）：

```python
# scripts/check_case_parity.py:43
from backend.tests.harness.validators import ASSERTION_OPERATORS
```

生产侧 `scripts/` import 测试侧 `backend/tests/`，违背 `tests/` 只放测试的约定。

## 二、目标结构

```
backend/harness/                 # 新增：实现（生产级工具包，与 core/domains/schemas 并列）
    __init__.py                  # 新增
    runner.py
    validators.py
    viewer.py
    terminal_trace.py

backend/tests/harness/           # 只留测试
    test_harness.py
    test_case_parity.py
    test_seed_case_inputs.py
    test_seed_case_requests.py
    test_terminal_trace.py
    test_validators.py
```

放 `backend/harness/`（而非 `backend/common/harness/`）理由：`runner.py` 依赖 `backend.core.*`、`backend.schemas.*`、`backend.domains.*`；`backend/common/` 约定是纯基础设施、不依赖 core/domains。`backend/harness/` 作为上层集成工具，依赖 core/domains/schemas/common 方向正确。

## 三、改动清单

### 3.1 移动 4 个实现文件

| 从 | 到 |
|---|---|
| `backend/tests/harness/runner.py` | `backend/harness/runner.py` |
| `backend/tests/harness/validators.py` | `backend/harness/validators.py` |
| `backend/tests/harness/viewer.py` | `backend/harness/viewer.py` |
| `backend/tests/harness/terminal_trace.py` | `backend/harness/terminal_trace.py` |

新增 `backend/harness/__init__.py`。

### 3.2 改 import（7 处）

| 文件:行 | 改前 | 改后 |
|---|---|---|
| `runner.py:30` | `from backend.tests.harness.validators import validate_expected` | `from backend.harness.validators import validate_expected` |
| `runner.py:86` | `from backend.tests.harness.terminal_trace import TerminalTraceSubscriber` | `from backend.harness.terminal_trace import TerminalTraceSubscriber` |
| `test_case_parity.py:16` | `from backend.tests.harness import runner, validators` | `from backend.harness import runner, validators` |
| `test_harness.py:10` | `from backend.tests.harness import runner, viewer` | `from backend.harness import runner, viewer` |
| `test_terminal_trace.py:146` | `from backend.tests.harness.terminal_trace import TerminalTraceSubscriber` | `from backend.harness.terminal_trace import TerminalTraceSubscriber` |
| `test_validators.py:3` | `from backend.tests.harness.validators import (...)` | `from backend.harness.validators import (...)` |
| `scripts/check_case_parity.py:43` | `from backend.tests.harness.validators import ASSERTION_OPERATORS` | `from backend.harness.validators import ASSERTION_OPERATORS` |

### 3.3 改 `__file__` 相对路径（2 处，关键坑）

`runner.py:19` 与 `viewer.py:11`：

```python
REPO_ROOT = Path(__file__).resolve().parents[3]
```

文件从 `backend/tests/harness/`（backend 下两级）移到 `backend/harness/`（backend 下一级）后，必须改成 `parents[2]`，否则 `REPO_ROOT` 漂移到仓库父目录，`RUNS_DIR`/`TESTS_DIR`/`config/module_registry.json` 全部错位。

`test_case_parity.py:18` 的 `parents[3] / "scripts"` 不改（测试文件深度未变）。

### 3.4 改 CI（1 处）

`.github/workflows/dev-case-contract.yml:152`：

```yaml
uv run --frozen python -m backend.tests.harness.runner all
# →
uv run --frozen python -m backend.harness.runner all
```

## 四、关键坑（避免静默失败）

1. `parents[3] → parents[2]`（runner + viewer）。
2. `backend/common/` 是 namespace package（无 `__init__.py`），`backend/harness/` 必须带 `__init__.py`。
3. CI `-m` 入口同步，否则 `ModuleNotFoundError`。
4. 文档边界：只更新活跃文档，不改 `docs/archive/` 与历史 `status/` 旧命令记录（当时事实快照）。

活跃文档（更新）：
- `CODE_CURRENT_STATUS_AND_GAPS.md`
- `docs/template/DataComplyFlow_代码仓库事实基线与系统理解_20260804.md`
- `status/view/20260813_各模块CLI功能代码流程逻辑原理与数据运行真实情况.md`

## 五、验证清单

```bash
uv run --frozen python -m backend.harness.runner all --no-llm      # 15 PASS / 11 modules
uv run --frozen python scripts/check_case_parity.py                 # 生产门禁
uv run --frozen pytest backend/tests/harness/ -q                    # 6 个测试文件
uv run --frozen pytest backend/ -q                                  # 全量回归
uv run --frozen ruff check backend/harness/ scripts/check_case_parity.py backend/tests/harness/
```

## 六、不做的事

- 不把 6 个 `test_*.py` 再往下拆一层 `tests/`（它们已在测试目录内，问题在实现混入）。
- 不在 `backend/tests/harness/` 留兼容 shim（会重新制造 tests 被当库 import 的反模式）。
- 不改 `docs/archive/` 与历史 `status/` 旧命令记录。

---

## 七、落实记录（2026-08-13 已完成）

### 已执行

1. `git mv` 迁移 4 个实现文件：`runner.py`/`validators.py`/`viewer.py`/`terminal_trace.py` → `backend/harness/`；新增 `backend/harness/__init__.py`。
2. 改 import 7 处 + `__file__` 相对路径 2 处（`parents[3]→parents[2]`，runner + viewer）。
3. 改 CI 1 处：`.github/workflows/dev-case-contract.yml` 的 `-m backend.harness.runner`。
4. 更新 3 份活跃文档（`CODE_CURRENT_STATUS_AND_GAPS.md`、`docs/template/..._20260804.md`、`status/view/..._真实情况.md`），历史 `status/`、`docs/archive/` 未改。
5. 补修 1 处测试硬编码路径：`test_terminal_trace.py` 的 `RUNNER` 指向 `backend/harness/runner.py`。

### 验证结果

| 项 | 结果 |
|---|---|
| `python -m backend.harness.runner all --no-llm --quiet` | 24 PASS / 2 FAIL（26 案例） |
| `python scripts/check_case_parity.py` | EXIT=0（11 模块 / 26 CLI 案例 / 603 leaf checks） |
| `pytest backend/tests/harness/ -q` | 88 passed |
| 代码/CI 旧 `backend.tests.harness` 引用 | 无残留 |
| 全量 `pytest backend/ -q` | 1092 passed / 4 failed |

### 全量回归 4 个失败（与本任务无关，既存）

失败测试均**不 import harness**，位于 task068/BCR/pipia 在改文件中：

1. `backend/common/reporting/tests/test_docx_renderer.py::test_render_is_hash_stable`（task068 新增文件）
2. `backend/domains/cn/pipia/tests/test_service.py::test_scc_evidence_drives_source_findings`
3. `backend/domains/cn/pipia/tests/test_service.py::test_certification_evidence_drives_path_findings`
4. `backend/domains/eu/scc_review/tests/test_service.py::test_uploaded_scc_document_drives_core_review`

（2、3 与 runner smoke 中 `pipia/02`、`pipia/05` 的 FAIL 同源，属此前 pipia 整改在途工作，非本次迁移引入。）

### 未做（按方案边界）

- 未在 `backend/tests/harness/` 留兼容 shim。
- 未改 `docs/archive/` 与历史 `status/` 旧命令记录。
- 未 `git add .`（迁移用 `git mv` 按文件暂存；`backend/harness/__init__.py` 为新增未暂存，待归属确认）。
