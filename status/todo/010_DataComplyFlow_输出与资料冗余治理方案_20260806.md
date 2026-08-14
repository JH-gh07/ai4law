# DataComplyFlow 输出与资料冗余治理方案

> 文档性质：待实施技术方案（TODO），不是当前实现描述
> 编制日期：2026-08-06
> 方案版本：v1
> 适用分支：`new`
> 问题来源：`status/CURRENT_DataComplyFlow_全功能运行验证与问题汇报_20260805.md` 第 3.a 节「目录、文件和输入输出冗余」
> 关联方案：`status/todo/DataComplyFlow_执行流成熟架构设计_20260806.md`（运行目录归属）、`status/todo/DataComplyFlow_Schema契约防漂移实施方案_20260806.md`（门禁复用）

---

## 一、事实核对：先修正问题定性

在设计方案前先复核了原始结论。**大部分数量级成立，但「仓库膨胀」这一定性不成立**，这直接改变治理优先级。

### 1.1 复核结果

| 原报告结论 | 本次实测 | 判定 |
|---|---|---|
| `outputs/` 约 1.1 GiB、42,022 个文件 | 1.2 GiB、45,688 个文件（9 个模块目录） | 成立，且已继续增长 |
| 本轮新增 1,960 个输出文件 | 未独立复核（无运行前快照） | 采信原报告 |
| 728 个 `__pycache__`、7,723 个 `.pyc` | 729 个目录、7,727 个 `.pyc` | 数量成立 |
| 这些文件「污染仓库」 | `git ls-files` 实测：`__pycache__`/`.pyc` 追踪数 **0**，`.DS_Store` 追踪数 **0** | **不成立** |
| ZIP 与散件双重存储 | 1,934 个 ZIP，其中 1,849 个内容被同目录散件完全覆盖，冗余 **119.3 MiB** | 成立 |
| 思诚三组资料 8 组重复哈希 | 实测 `resources/new` 218 个文件中 **11 组**重复哈希 | 低估，见 §1.3 |
| 模板 DOCX/MD 双源有漂移风险 | 成立，但**两者都被代码读取**，不是「一个权威源 + 一个副产物」 | 成立，且比原判断更严重 |

### 1.2 定性修正：这是磁盘与可维护性问题，不是仓库卫生问题

`.gitignore` 已覆盖 `**/__pycache__/`、`*.py[cod]`、`outputs/`、`runs/`、`.DS_Store`，且 `scripts/check_repository_hygiene.py` 已把 `__pycache__` / `.pyc` / `.DS_Store` 列为硬失败项并在 CI 执行。**Git 侧防线是完整的**。

因此：

- 「`.gitignore` + 定期清理」这条建议对 Git 无收益，只对本地磁盘和 IDE 索引速度有收益，**降为 P3**。
- 真正的成本集中在三处：**运行输出无生命周期**（P0）、**ZIP 双重存储**（P1）、**模板双源可静默漂移**（P1）。
- `outputs/` 不进 Git，也意味着**没有任何 CI 能发现它失控**。治理必须靠运行期约束，不能靠 lint。

### 1.3 `resources/new` 重复哈希实测清单（11 组）

按性质分四类：

**A. 跨目录重复（根目录副本 vs reference 库副本），3 组**

| 内容 | 副本位置 |
|---|---|
| `“合规路径诊断”功能说明与路径描述（标注Reference）.docx` | `resources/new/` 根 ＋ `…/中国数据出境路径/任务1：…/` |
| `数据安全技术敏感个人信息处理安全要求GBT+45574-2025.pdf` | `resources/new/` 根 ＋ `…/中国数据出境路径reference文件库/` |
| `数据分级分类指南GBT+43697-2024.pdf` | `resources/new/` 根 ＋ `…/中国数据出境路径reference文件库/` |

**B. 同目录内 `(1)` / `(2)` 下载副本，2 组**

- `个人信息保护影响评估报告（模板）.docx` ＝ `个人信息保护影响评估报告（模板） (1).docx`
- `数据出境安全评估申报指南（第三版） (1).docx` ＝ `数据出境安全评估申报指南（第三版） (2).docx`

**C. `.html` / `.md` 同内容异扩展名，5 组**（原报告记为 5 组中的一部分）

`新加坡` / `越南` / `港澳台` / `日韩` / `马来西亚` 五份「相关法规目录」。注意 `马来西亚` 的 md 侧文件名为 `马来西亚相关法规目录md.md`（多余的 `md` 后缀），与其他四组命名不一致。

**D. `.DS_Store`，1 组**（3 个同内容文件）

原报告称 8 组，实测 11 组；差异主要来自 A 类跨目录副本未被计入。

### 1.4 空间构成实测（决定治理顺序）

```
模块         运行数  ZIP数  ZIP占用   trace目录  trace占用   模块总占用
assessment    861    708   69.3 MiB     626     325.2 MiB   785.5 MiB
dpia          244    244   21.2 MiB      93      12.4 MiB   158.6 MiB
pipia         184    199    7.9 MiB      89       3.8 MiB    94.1 MiB
us_14117      253    250    3.6 MiB      85      13.9 MiB    36.6 MiB
cn_flow       141    140    6.0 MiB      91       7.3 MiB    27.9 MiB
eu_scc        231      0        0        41       6.6 MiB    26.0 MiB
cpra          109    120    5.3 MiB      84      11.5 MiB    24.4 MiB
bcr           154    166    6.5 MiB      92       1.1 MiB    17.8 MiB
tia           100    107    4.2 MiB      81       4.4 MiB    14.2 MiB
```

文件类型分布：`json` 33,045、`md` 3,995、`xlsx` 2,964、`docx` 1,963、`zip` 1,934、`pdf` 1,680。

**三个可直接读出的结论：**

1. **占用大头是 `assessment`（785 MiB，占 65%），其中 trace 占 325 MiB。** 但文件数大头是 `json`（33,045 个，72%）。空间治理和文件数治理的目标对象不同，方案要分开处理。
2. **`eu_scc` 有 231 次运行但 0 个 ZIP**，其余模块几乎每次运行都产出 ZIP。输出包策略在模块间不一致，说明它不是产品契约，而是各模块自行实现的结果。
3. **`bcr` 有 154 次运行但 166 个 ZIP**（`pipia` 184/199、`cpra` 109/120、`tia` 100/107）。ZIP 多于运行数，因为 `bcr_review/service.py` 有两处 `bundle_files` 调用点（第 583、618 行）产出不同命名的包，同一次运行可能落两个。

---

## 二、根因：输出布局是散落的字符串字面量，没有生命周期概念

### 2.1 路径是硬编码字面量，共 11 处

```
backend/domains/cn/security_assessment/report_renderer.py:99   outputs/assessment/<task_id>/outputs
backend/domains/cn/pipia/service.py:589                        outputs/pipia/<task_id>/outputs
backend/domains/cn/document_review/service.py:449              outputs/review/<task_id>/outputs
backend/domains/eu/dpia/report_renderer.py:285                 outputs/dpia/<task_id>/outputs
backend/domains/eu/tia/service.py:450                          outputs/tia/<task_id>/outputs
backend/domains/eu/bcr_review/service.py:577,612               outputs/bcr/<task_id>/outputs
backend/domains/eu/scc_review/service.py:338                   outputs/eu_scc/<task_id>/outputs
backend/domains/us/eo14117/service.py:390                      outputs/us_14117/<task_id>/outputs
backend/domains/us/eo14117_flow_review/service.py:379          outputs/cn_flow/<task_id>/outputs
backend/domains/us/cpra/service.py:570                         outputs/cpra/<task_id>/outputs
```

消费侧另有 5 处独立重建同一路径：`api/v1/endpoints/me.py:136,424`、`api/v1/endpoints/citations.py:50,68-69,195,230`、`api/v1/endpoints/events.py:25`、`api/v1/endpoints/artifacts.py:21`、`services/artifact_registry.py:44-46`（靠 `parts.index("outputs") + 2` 反推 `task_id`）。

**后果：没有任何单点可以插入保留策略、分级或压缩。** 任何清理逻辑都得在 16 个地方各写一遍，或者绕过代码直接操作文件系统（当前只能这样，因此才积累到 1.2 GiB）。

注意 `eo14117_flow_review`（cn_flow 模块）写入 `outputs/cn_flow/`，而 `eo14117` 写入 `outputs/us_14117/`——目录名与代码目录名不对应，这类隐式映射也只能靠字面量维持。

### 2.2 产物没有分级

同一个 `outputs/` 目录里混放三类语义完全不同的东西，以 `assessment` 单次运行为例（23 个文件）：

| 类别 | 文件 | 用户是否需要 | 应保留多久 |
|---|---|---|---|
| 交付物 | `…自评估报告_草案_*.md/.docx/.pdf`、`issue_list.xlsx`、`evidence_chain.xlsx` | 是 | 长期 |
| 证据链 | `citation_map.json`、`legal_grounding.json`、`evidence_chain.json`、`generation_basis_pack.json` | 审计时是 | 中期 |
| 调试中间态 | `facts.json`、`writing_strategy.json`、`compliance_reasoning.json/.md`、`material_checklist.json`、`internal_ai_review.md`、`path_judgment.json`、`trace_manifest.json` | 否 | 短期 |
| 重复包装 | `…输出包_草案_*.zip`（内容 ⊆ 上述散件） | 否 | 不应长期存在 |

`internal_ai_review.md`、`compliance_reasoning.md` 这类内部审查文本与用户交付物同级放在 `outputs/` 下，除了占空间，也是**误交付风险**——只要有人把整个目录打包给客户就会泄漏内部评审意见。

### 2.3 ZIP 是「同目录再复制一份」

`backend/common/render/artifacts.py:88`：

```python
def bundle_files(output_zip: Path, files: list[Path]) -> Path:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_zip, mode="w", compression=ZIP_DEFLATED) as zf:
        for file in files:
            if file.exists():
                zf.write(file, arcname=file.name)
    return output_zip
```

`output_zip` 与 `files` 落在同一目录，`arcname=file.name` 保证包内名与散件名一致。实测 1,934 个 ZIP 中 1,849 个（95.6%）的每一个条目都能在同目录找到同名散件。抽样确认覆盖全部模块：

```
dpia     2 条目  全部 DUP-SIBLING
tia      2 条目  全部 DUP-SIBLING
bcr      2 条目  全部 DUP-SIBLING
pipia    2 条目  全部 DUP-SIBLING
cpra     4 条目  全部 DUP-SIBLING
us_14117 9 条目  全部 DUP-SIBLING（含 issue_list.json / facts.json / trace_manifest.json）
```

`us_14117` 的包里含 `trace_manifest.json`、`facts.json` 这类调试产物，进一步说明打包成员是「顺手全塞」而非按交付语义挑选。

### 2.4 trace 是一事件一文件

`backend/common/trace/recorder.py` 的 `TraceRecorder` 每个事件写一个独立 JSON 文件（`_NAME_TO_EVENT_TYPE` 有 90+ 种事件名）。这是 33,045 个 `json` 文件的主要来源，也是 `assessment` 325 MiB trace 占用的来源。

同时 trace 目录是**可选存在**的：实测 `dpia` 244 次运行只有 93 个 `trace/` 目录，`eu_scc` 231 次运行只有 41 个。可观测性覆盖不完整，但这属于执行流方案（`DataComplyFlow_执行流成熟架构设计_20260806.md`）范畴，本方案只处理其存储形态。

### 2.5 布局本身已经不一致

`outputs/assessment/` 下有 862 个 `task_id` 目录，**另有 46 个直接躺在模块根目录的散件**（如 `outputs/assessment/华东云链科技（测试）_数据出境风险自评估报告_草案_20260422.docx`）。这些是早期布局的遗留，`artifact_registry.py` 的 `parts.index("outputs") + 2` 反推逻辑对它们会得出错误的 `owner_id`。清理脚本必须显式处理这批孤儿文件，不能假设 `outputs/<module>/<task_id>/` 布局成立。

### 2.6 删除必须同步数据库

`services/artifact_registry.py` 把每个 `output_files` 条目以绝对路径注册进 `report_service`；`api/v1/endpoints/me.py:424` 的删除流程会同时删 `outputs/<module>/<task_id>` 与 `settings.report_dir/<module>/<task_id>` 并清理数据库行。

**这意味着任何绕过应用直接 `rm -rf outputs/` 的清理都会留下悬空的数据库记录**，「我的报告」页面会出现点开即 404 的条目。保留策略必须走应用层或显式做 DB 对账，这是本方案最容易被忽略的约束。

---

## 三、目标与验收口径

### 3.1 要达到的状态

1. 运行输出有**声明式生命周期**：每个产物在代码里标注类别与保留期，清理由单一执行器完成。
2. 输出根目录、模块目录名、运行子目录**由单一模块产出**，不再有 16 处字面量。
3. ZIP **不再与散件同时长期存在**。
4. 模板有**唯一权威源**，非权威副本由构建产出并被门禁校验。
5. `resources/` 入库前**按 SHA-256 去重**，重复副本以指针替代。
6. `outputs/` 规模有**可观测上限**，超限会告警而不是静默增长。

### 3.2 验收标准

| 门禁 | 验收标准 | 失败是否阻止合入 |
|---|---|---|
| 路径单点门禁 | `backend/` 内除 `run_layout.py` 外不出现 `"outputs/"` 字面量拼接 | 是 |
| 产物分级门禁 | 每个 `output_files` 键在产物清单中有 `retention` 声明，缺失即失败 | 是 |
| ZIP 非双存门禁 | 运行结束后同目录不同时存在 ZIP 与其全部成员散件 | 是 |
| 模板单源门禁 | 由 MD/JSON 重新生成 DOCX，结构化比对与仓库副本一致 | 是 |
| 资料去重门禁 | `resources/` 内无重复内容哈希（`.DS_Store` 除外，直接删） | 是 |
| 清理安全门禁 | `prune_outputs.py --dry-run` 在 CI 固定夹具上输出稳定，且 DB 对账无悬空记录 | 是 |
| 规模看护 | `outputs/` 超过阈值时 CI/启动日志告警 | 否（告警） |

### 3.3 不作为验收依据

- 「本地 `du -sh outputs/` 变小」：手工删除不证明策略生效，重跑一次就会回到原样。
- 「`git status` 干净」：`outputs/` 本就不进 Git，见 §1.2。
- 「ZIP 数量变少」：必须同时确认下载入口仍可用，否则是功能回退。
- 「测试通过」：现有测试大量断言 ZIP 存在（`test_service.py` / `test_renderer_contracts.py` 共 15 个文件涉及 zip），必须同步改造断言，通过本身不说明设计正确。

---

## 四、方案设计

### 4.1 引入产物清单（Artifact Manifest）

新增 `backend/common/runtime/artifact_spec.py`，把「产物叫什么、属于哪一级、保留多久、是否入包」变成数据：

```python
from dataclasses import dataclass
from enum import Enum

class Tier(str, Enum):
    DELIVERABLE = "deliverable"   # 用户交付物，长期保留
    EVIDENCE    = "evidence"      # 证据链，审计需要，中期保留
    DEBUG       = "debug"         # 中间态，短期保留
    INTERNAL    = "internal"      # 内部评审，永不入交付包

@dataclass(frozen=True)
class ArtifactSpec:
    role: str          # output_files 的键，与 artifact_registry 对齐
    tier: Tier
    bundled: bool      # 是否作为输出包成员
    retention_days: int | None   # None = 跟随 deliverable 策略
```

每个模块声明自己的清单（就近放在 domain 内，避免中心化后又变成新的字面量集中地）。`assessment` 示例：

```python
ASSESSMENT_ARTIFACTS = (
    ArtifactSpec("report_md",            Tier.DELIVERABLE, bundled=True,  retention_days=None),
    ArtifactSpec("report_docx",          Tier.DELIVERABLE, bundled=True,  retention_days=None),
    ArtifactSpec("report_pdf",           Tier.DELIVERABLE, bundled=True,  retention_days=None),
    ArtifactSpec("issue_list_xlsx",      Tier.DELIVERABLE, bundled=True,  retention_days=None),
    ArtifactSpec("evidence_chain_xlsx",  Tier.DELIVERABLE, bundled=True,  retention_days=None),
    ArtifactSpec("citation_map",         Tier.EVIDENCE,    bundled=False, retention_days=180),
    ArtifactSpec("legal_grounding",      Tier.EVIDENCE,    bundled=False, retention_days=180),
    ArtifactSpec("generation_basis_pack",Tier.EVIDENCE,    bundled=False, retention_days=180),
    ArtifactSpec("facts",                Tier.DEBUG,       bundled=False, retention_days=14),
    ArtifactSpec("writing_strategy",     Tier.DEBUG,       bundled=False, retention_days=14),
    ArtifactSpec("compliance_reasoning", Tier.DEBUG,       bundled=False, retention_days=14),
    ArtifactSpec("material_checklist",   Tier.DEBUG,       bundled=False, retention_days=14),
    ArtifactSpec("path_judgment",        Tier.DEBUG,       bundled=False, retention_days=14),
    ArtifactSpec("internal_ai_review",   Tier.INTERNAL,    bundled=False, retention_days=30),
)
```

清单是后续所有机制的**唯一事实源**：打包成员来自 `bundled=True`，清理策略来自 `retention_days`，误交付防护来自 `Tier.INTERNAL`。

### 4.2 统一运行目录（`run_layout`）

新增 `backend/common/runtime/run_layout.py`，替换 §2.1 的 16 处字面量：

```python
class RunLayout:
    """<outputs_root>/<module>/<run_id>/{deliverables,evidence,debug,trace}/"""

    def __init__(self, outputs_root: Path, module: str, run_id: str): ...

    @property
    def root(self) -> Path: ...
    def dir_for(self, tier: Tier) -> Path: ...
    def path_for(self, spec: ArtifactSpec, filename: str) -> Path: ...
    @property
    def trace_dir(self) -> Path: ...
    @property
    def manifest_path(self) -> Path: ...   # run_manifest.json，与现有实现对齐
```

`outputs_root` 从 `Settings` 读取（新增 `outputs_dir: Path = Path("outputs")`，走既有 `AI4LAW_` 前缀），不再硬编码。模块目录名（含 `eo14117_flow_review → cn_flow` 这类映射）收敛为 `run_layout` 内的显式映射表，映射本身可被测试覆盖。

**兼容性是本项最大风险。** 现有 `outputs/<module>/<task_id>/outputs/` 已有 45,688 个文件，且路径以绝对路径形式写进了数据库。因此：

- `RunLayout` 提供 `legacy_flat_dir()`，读路径同时探测新旧两种布局，新布局优先。
- 消费侧（`me.py`、`citations.py`、`artifact_registry.py`、`events.py`、`artifacts.py`）改为调用 `RunLayout`，不再自行 `parts.index("outputs") + 2`。
- **不迁移历史数据**，历史运行按旧布局原样保留，由 §4.6 的清理脚本按保留期自然淘汰。迁移 45,688 个文件并回写数据库的收益低于风险。

### 4.3 ZIP 改为按需生成，不落盘长期保留

保留「一键下载输出包」的用户价值，去掉双重存储。改动分三步：

1. `bundle_files` 增加 `members` 来自清单 `bundled=True` 的约束，并显式拒绝 `Tier.INTERNAL`（防止 §2.2 的误交付）。
2. 新增下载端点 `GET /api/v1/artifacts/{module}/{run_id}/bundle`，流式生成 ZIP，`Content-Disposition` 用原命名规则，**不写磁盘**。
3. 运行期不再产出 ZIP 文件；`output_files` 里的 `bundle` 键改为指向该端点的相对 URL 而非文件路径。

`bcr_review` 的两处调用点（`service.py:583` 与 `:618`）合并为一个包，命名统一为 `<name>_<module>_输出包_草案_<date>.zip`；`eu_scc` 首次获得输出包能力，消除 §1.4 结论 2 的模块间不一致。

**需要同步改的测试**：15 个涉及 zip 的测试文件断言从「文件存在」改为「端点返回 200 且包内成员集合等于清单 `bundled=True` 集合」。这比原断言更强——它同时锁住了包内容契约。

若判断「按需生成」改动面过大需要分期，退化方案是**保留落盘 ZIP 但把成员散件移入 `debug/` 并缩短保留期**。这解决不了双存储，只是把 119 MiB 的重复期限从无限压到 14 天，作为过渡可接受，不作为终态。

### 4.4 trace 落盘形态改为单文件 JSONL

`TraceRecorder` 从「一事件一 JSON」改为**追加写单个 `trace/events.jsonl`**：

- 事件数不变，文件数从 33,045 量级降到「每次运行 1 个」。
- 保留 `manifest.json` 作为索引（`run_manifest.py` 的 `summarize_trace` 已按 `trace_dir / "manifest.json"` 读取，接口不变）。
- 现有 `_events` 内存列表与 `TraceEvent.path` 字段语义调整为 `<jsonl>#<行号>`，`summarize_trace` 中逐文件 `json.loads(Path(event.path).read_text())` 的实现改为按行号读取。
- 超过阈值（建议 30 天）的 `events.jsonl` 由清理脚本 gzip，`manifest.json` 保留不压缩以便索引。

`assessment` 的 325 MiB trace 在 JSONL + gzip 后预期降到 40-60 MiB 量级（JSON 事件文本压缩比通常 6-10 倍），这是单项收益最大的改动。

### 4.5 保留策略配置

放入 `config/`，与既有配置目录一致：

```yaml
# config/output_retention.yaml
version: 1
defaults:
  deliverable_days: 365
  evidence_days: 180
  debug_days: 14
  internal_days: 30
  trace_days: 30
  trace_gzip_after_days: 7
overrides:
  assessment:
    trace_days: 14        # 单模块 325 MiB，压缩期更激进
thresholds:
  warn_total_gib: 2.0
  warn_file_count: 60000
protect:
  - runs_referenced_by_db: true    # 数据库仍持有引用的运行不删交付物
  - runs_newer_than_hours: 24      # 24 小时内的运行完全不动
```

`protect` 两条是安全阀：前者防止「我的报告」出现 404 条目（§2.6），后者防止误删正在进行或刚完成的运行。

### 4.6 清理执行器 `scripts/prune_outputs.py`

单一执行入口，默认 dry-run：

```
用法：
  python scripts/prune_outputs.py --dry-run              # 默认，只报告
  python scripts/prune_outputs.py --apply                # 实际执行
  python scripts/prune_outputs.py --module assessment    # 限定模块
  python scripts/prune_outputs.py --report status/errorLog/prune_<date>.json

执行顺序（每步独立可跳过）：
  1. 扫描 outputs/，按 RunLayout 解析出 (module, run_id, tier, path)
  2. 收集无法解析的孤儿文件（含 §2.5 的 46 个 assessment 散件）→ 单独列出，不自动删
  3. 与数据库对账：标记仍被 report_service 引用的路径为 protected
  4. 按 config/output_retention.yaml 计算待删集合
  5. 对 trace：先 gzip 再按期删除
  6. 对 ZIP：若成员散件齐全，删 ZIP（过渡期行为，§4.3 落地后此步失效）
  7. 输出 JSON 报告：删除数/释放字节/protected 数/孤儿数
  8. --apply 时才真正删除，且先移入 .trash/ 再统一清空（可回滚窗口）
```

**必须有的性质：**

- **幂等**：连续两次 `--apply` 第二次应为空操作。
- **DB 对账前置**：第 3 步失败则整体中止，绝不在数据库不可达时删交付物。
- **孤儿不自动删**：只报告，由人确认。46 个 assessment 散件可能是有价值的历史输出。
- **可回滚**：`.trash/` 中转，避免不可逆误删。

配套 CI：在固定夹具目录上跑 `--dry-run` 并对比期望报告，防止策略回归。

### 4.7 模板单源

现状比原判断严重：`resources/templates/` 下的 DOCX 与 MD **都被代码读取**（`TEMPLATE_PATH` 取 `.docx`、`TEMPLATE_MD` 取 `.md`，共 8 组 domain 各持一对），所以不能简单地说「MD 权威、DOCX 是副产物」。

**同时发现一处待核实的缺口**：`backend/domains/cn/pipia/service.py:37-38` 引用 `2.3_pipia_template_v0.docx` / `.md`，但 `resources/templates/cn/` 实际只有 `2.2_risk_assessment_template_v0.*`、`official_risk_self_assessment_template.md`、`official_template_schema.json`。需要先确认 `report_template_path` 是否有其他解析根或回退逻辑，再决定这是缺失文件还是查找路径差异。**这一项先核实，不要按缺失文件直接补。**

方案：

1. **确定权威源**：结构化内容以 `*.md` ＋ `official_template_schema.json` 为权威（已有先例：`security_assessment/report_renderer.py:212` 明确要求 MD 模板存在）。
2. **DOCX 降级为生成物**：新增 `scripts/build_templates.py`，从 MD/JSON 渲染 DOCX，复用既有 `backend/common/render/docx_comments.py` 能力。
3. **仓库仍提交 DOCX**（避免运行期依赖构建步骤），但由门禁 `scripts/check_template_sync.py` 做结构化比对（章节标题序列、占位符集合），而非字节比对——DOCX 含时间戳，字节比对必然失败。
4. `report_template_path` 的模板清单集中声明并被测试覆盖，防止再出现 §4.7 那类「代码引用了不存在的模板」。

### 4.8 `resources/` 去重与规范

按 §1.3 的四类分别处理：

| 类别 | 处理 | 是否需人工确认 |
|---|---|---|
| D. `.DS_Store` | 直接删，`.gitignore` 已覆盖 | 否 |
| B. `(1)` / `(2)` 下载副本 | 保留无后缀者，删副本 | 否 |
| A. 跨目录副本 | **保留 reference 库内的副本**（有目录语义），删 `resources/new/` 根副本，在根目录留 `README.md` 说明去向 | 是（确认根目录副本无独立引用） |
| C. `.html` / `.md` 同内容 | 保留 `.md`（可 diff、可检索），删 `.html`；顺带把 `马来西亚相关法规目录md.md` 改名为 `马来西亚相关法规目录.md` | 是（确认无代码按 `.html` 路径读取） |

新增 `scripts/check_resource_dedup.py`：扫描 `resources/`，对重复内容哈希报错。**只对 `resources/` 生效**，不扫 `outputs/`（那里重复是正常的运行产物）。

关于原报告「ZIP + 解压目录双层同名目录，解压时去除一层包装」：`resources/` 下实测已无 ZIP 文件（资料已解压入库），三组资料的目录结构是 `resources/new/<资料包名>/<法域>/<任务>/`，**没有外层/内层同名嵌套**。这一条已在此前的入库过程中解决，本方案不再处理；但 `scripts/check_resource_dedup.py` 应顺带拒绝新出现的 `X/X/` 形式路径，防止回归。

### 4.9 本地缓存清理（P3，仅磁盘收益）

`729` 个 `__pycache__` / `7,727` 个 `.pyc` / 20 个 `.DS_Store` 均未进 Git，无仓库风险。提供一条便利命令即可，不设门禁：

```
make clean-local   # 清 __pycache__ / .pyc / .DS_Store / .pytest_cache / .ruff_cache
```

`scripts/check_repository_hygiene.py` 已覆盖 Git 侧，不需扩展。

---

## 五、实施顺序

按「先止血、再重构」排列。每个 PR 独立可合、可回滚。

```
PR 1：止血（不改架构，纯收益）
  ├─ scripts/prune_outputs.py（dry-run 优先，含 DB 对账 + .trash 回滚）
  ├─ config/output_retention.yaml
  ├─ resources/ 去重（§4.8 A/B/C/D 四类）+ check_resource_dedup.py + CI
  └─ make clean-local
  ↓ 释放 119 MiB ZIP + 部分 trace，资料重复被门禁锁住

PR 2：trace 单文件化（单项空间收益最大）
  ├─ TraceRecorder → events.jsonl
  ├─ summarize_trace 按行号读取
  ├─ prune_outputs 增加 gzip 步骤
  └─ 更新 common/trace/tests/ 与 test_recorder_stream.py
  ↓ 文件数从 45,688 降到万级，assessment trace 预期降 80%

PR 3：产物清单 + 运行布局（架构改动，改动面最大）
  ├─ artifact_spec.py + 各 domain 清单声明
  ├─ run_layout.py + Settings.outputs_dir
  ├─ 替换 11 处写入字面量 + 5 处消费侧路径重建
  ├─ legacy_flat_dir 兼容旧布局（不迁移历史数据）
  └─ 路径单点门禁 lint
  ↓ 保留策略有了单一插入点

PR 4：ZIP 按需生成
  ├─ /api/v1/artifacts/{module}/{run_id}/bundle 流式端点
  ├─ 运行期停止落盘 ZIP，output_files.bundle 改为 URL
  ├─ bundle 成员来自清单 bundled=True，拒绝 Tier.INTERNAL
  └─ 15 个 zip 相关测试文件断言改为端点契约断言
  ↓ 双重存储彻底消除

PR 5：模板单源
  ├─ 先核实 pipia 2.3 模板缺口（§4.7）
  ├─ scripts/build_templates.py
  ├─ scripts/check_template_sync.py（结构化比对）+ CI
  └─ report_template_path 模板清单集中声明 + 测试
  ↓ 模板漂移被门禁锁住

PR 6：规模看护
  ├─ 启动/CI 检查 outputs 总量与文件数，超阈值告警
  └─ prune_outputs --dry-run 定时任务 + 报告归档到 status/errorLog/
```

**PR 1 与 PR 2 可并行**，两者都不依赖架构改动。**PR 4 强依赖 PR 3**（需要清单和布局）。**PR 5 完全独立**，可随时插入。

---

## 六、风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 清理删掉数据库仍引用的产物 | 「我的报告」出现 404 条目，用户可见故障 | §4.6 第 3 步 DB 对账前置，失败即中止；`protect.runs_referenced_by_db` |
| 清理误删有价值的历史输出 | 不可逆数据丢失 | `.trash/` 中转 + 默认 dry-run + 孤儿文件只报告不删 |
| `run_layout` 改造遗漏某个消费侧 | 下载 404、引用页面空白 | 路径 lint 门禁扫全 `backend/`；新旧布局双探测；11 模块逐一人工验收 |
| ZIP 改按需后前端未同步 | 「下载输出包」按钮失效 | `output_files.bundle` 保留同名键，值从路径改 URL；前端下载逻辑统一走 URL 分支 |
| trace JSONL 改造破坏现有 trace 消费 | 可观测性回退，事件流页面异常 | `manifest.json` 契约不变；`test_recorder_stream.py`、`test_client_trace.py`、`test_events_api.py` 先改测试再改实现 |
| 模板 DOCX 结构化比对误报 | CI 长期红灯被忽略 | 只比对章节标题序列与占位符集合，明确排除时间戳/修订元数据 |
| `resources/` 去重删了被引用的 `.html` | 资料检索失效 | 删前全仓 grep 路径引用；A/C 两类需人工确认 |
| 保留期设定过激进 | 调试信息在需要时已不存在 | `debug_days: 14` 起步，先观察一个月再收紧；`protect.runs_newer_than_hours: 24` |

---

## 七、预期收益（基于 §1.4 实测推算）

| 项 | 当前 | 预期 | 依据 |
|---|---|---|---|
| ZIP 占用 | 124 MiB | 0 | 1,849/1,934 为完全冗余，PR 4 后不落盘 |
| trace 占用（assessment） | 325 MiB | 40-60 MiB | JSONL + gzip，JSON 文本压缩比 6-10× |
| 文件总数 | 45,688 | 万级 | 33,045 个 json 中绝大部分是 trace 单事件文件 |
| `outputs/` 总量 | 1.2 GiB | 300-450 MiB | 上述三项叠加，且 debug 层按 14 天淘汰 |
| `resources/new` 重复 | 11 组 | 0 | 去重 + 门禁 |
| 误交付风险 | 内部评审文本与交付物同级 | 隔离 | `Tier.INTERNAL` + 打包拒绝 |

**注意**：上述是稳态预期，不是一次清理的结果。没有 PR 3-4 的架构改动，PR 1 的清理只能反复手工执行，几周后回到原状——这也是当前积累到 1.2 GiB 的原因。

---

## 八、待确认事项

实施前需要决策或核实，未定项不应阻塞 PR 1：

1. **`pipia` 2.3 模板缺口**（§4.7）：`report_template_path` 是否有其他解析根？属缺失文件还是路径差异？
2. **46 个 `outputs/assessment/` 孤儿散件**（§2.5）：是否有保留价值？若有，归档到何处？
3. **保留期数值**：`config/output_retention.yaml` 的默认值需业务确认，尤其 `deliverable_days: 365` 是否满足合规留存要求（数据出境评估报告可能有法定留存期，这是本方案唯一可能受外部法规约束的参数）。
4. **`resources/new/` 根目录三份跨目录副本**（§1.3 A 类）：是否有独立引用？删除前需全仓 grep 确认。
5. **ZIP 按需生成 vs 过渡方案**（§4.3）：若 PR 4 改动面被判定过大，是否接受「散件移入 debug + 短保留期」的过渡形态？
