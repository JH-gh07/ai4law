# CLI 输入 / 输出详解（harness runner）

> 本文档解释 `python -m backend.tests.harness.runner ...` 这条命令**吃了什么、吐了什么、落盘在哪里**。
> 配套阅读：`status/view/20260813_各模块CLI功能代码流程逻辑原理与数据运行真实情况.md`（讲「流程逻辑」），本文只讲「输入输出」。

---

## 0. 一句话总览

```
命令行参数 + 案例定义文件 + 共享基准场景(scenario/expected)
                          │
                          ▼
              harness runner（白盒执行器）
                          │
                          ▼
        runs/<module>/<run_id>/   ← 每次运行的「证据包」
        outputs/<module>/<task_id>/outputs/  ← 真正的报告产物文件
        tmp/<module>/             ← 独立的便捷重跑输出（另一个脚本）
```

**核心区分**：
- **输入** = 案例定义（case.json）+ 共享场景（scenario.json 的 `request`）+ 期望（expected.json）。
- **输出** = `runs/` 运行证据包（输入快照 + 结果 + trace + 运行清单）与 `outputs/` 真实报告文件。
- `tmp/` 是**另一个脚本**（`scripts/rerun_all_modules.py`）的产物，**不是** harness 的直接输出。

---

## 1. 输入（CLI 吃了什么）

### 1.1 命令行参数（argv）

```bash
python -m backend.tests.harness.runner <module> [case_id] [--no-llm] [--quiet] [--verbose-trace]
```

| 参数 | 必填 | 含义 |
|---|---|---|
| `module` | ✅ | 模块别名，`choices=["all", *11 个模块]`，如 `eu_scc`、`assessment`、`all` |
| `case_id` | ❌ | 只跑该模块下某个案例，如 `03_module_mismatch`；缺省跑该模块全部案例 |
| `--no-llm` | ❌ | 服务注入 `_DisabledLLM` / `llm_client=None`，走确定性规则/模板路径 |
| `--quiet` | ❌ | 静默模式（与 `--verbose-trace` 互斥） |
| `--verbose-trace` | ❌ | 逐事件打印 trace 到终端 |

> 模块别名 → 包/类的映射在 `runner.py:97` 的 `_ADAPTER_DEFINITIONS`（11 项）。

### 1.2 案例定义文件（case.json）

位置：`backend/tests/<module>/cases/<case_id>.json`

它是**薄薄的「指针」**，自己不存输入数据，只指向共享基准场景：

```json
{
  "case_id": "02_india_health_uploaded",
  "description": "EU SCC正式案例二—…",
  "scenario_path": "benchmarks/cases/eu_scc/germany_c2p_india_health/scenario.json",
  "expected_path": "benchmarks/cases/eu_scc/germany_c2p_india_health/expected.json",
  "source_doc_path": "benchmarks/source-materials/eu/legacy-docx/“SCC审查”测试案例及预期输出.docx"
}
```

| 键 | 含义 |
|---|---|
| `case_id` | 案例唯一标识（= 文件名，缺 `.json`） |
| `description` | 人类可读说明 |
| `scenario_path` | 指向共享场景文件（真实输入） |
| `expected_path` | 指向期望文件（断言） |
| `source_doc_path` | 可选，原始来源文档（docx，用于溯源/上传） |

> 加载逻辑（`runner.py`）：`_resolve_case_input()` 读 `scenario_path` 里的 `request` 字段作为输入；`_resolve_case_expected()` 读 `expected_path`。二者都用 `resolve()` 且强制 `is_relative_to(REPO_ROOT)` 防越界。

### 1.3 共享场景文件（scenario.json）—— 真正的输入

位置：`benchmarks/cases/<module>/<scenario>/scenario.json`

```json
{
  "schema_version": "1.0",
  "case_id": "germany_c2p_india_health",
  "module": "eu_scc",
  "classification": "source_exact",
  "display": { "name": "…", "description": "…", "jurisdiction": "EU" },
  "source": { "file": "…docx", "case": "测试案例二…" },
  "request": {
    "project_name": "德国医疗研究数据向印度统计分析传输SCC审查",
    "scc_text": "MODULE TWO: Transfer controller to processor\n\n…",
    "declared_module_type": "Module Two",
    "exporter_role": "controller",
    "importer_role": "processor",
    "has_tia": false,
    "company_name": "Gesundheitsforschung GmbH"
  }
}
```

| 键 | 含义 |
|---|---|
| `schema_version` | 场景 schema 版本 |
| `case_id` | 场景标识（可能与 case.json 的 case_id 不同，用**场景名**） |
| `module` | 模块别名 |
| `classification` | 案例分类（`source_exact` = 来源精确复现） |
| `display` | 展示元信息（名称/描述/法域） |
| `source` | 溯源信息（原始 docx + 案例标题） |
| **`request`** | **真正的输入负载**，会被 `XxxRequest.model_validate()` 解析成 Pydantic 请求对象 |

> `request` 就是「喂给服务主方法的那个对象」：`EU_SCCService.generate_report(SCCReviewRequest(**request))`。它被原样写进 `runs/<module>/<run_id>/input/request.json` 并做 sha256 哈希。

### 1.4 期望文件（expected.json）—— 断言

位置：`benchmarks/cases/<module>/<scenario>/expected.json`

```json
{
  "schema_version": "1.0",
  "case_id": "germany_c2p_india_health",
  "overall_rating": "HIGH",
  "required_findings": [ "Clause 15 … weakened…", "health data misclassified…", "…TIA missing…" ],
  "legal_basis": [ "EU 2021/914 Recital 3", "Clause 15 standard text", "GDPR Article 9", "Recital 159" ],
  "harness": {
    "result_not_empty": true,
    "fields_equal": {
      "company_name": "Gesundheitsforschung GmbH",
      "overall_rating": "HIGH",
      "module_validation.actual_module": "Module Two",
      "module_validation.expected_module": "Module Two",
      "module_validation.is_correct": true
    },
    "min_counts": { "chapters": 4, "findings": 5, "attachment_notes": 1, "output_files": 7 },
    "list_contains": {
      "findings[].issue_type": ["clause_weakened", "special_category_misclassified", "tia_missing"],
      "findings[].location": ["Clause 15", "Annex I.B"]
    },
    "output_roles_contains": ["markdown", "docx", "pdf", "findings_json", "rule_engine_result_json", "citation_map_json", "annotated_docx"],
    "output_formats": ["md", "docx", "pdf", "json"]
  }
}
```

| 键 | 含义 |
|---|---|
| `overall_rating` | 期望的整体风险等级（HIGH/MEDIUM/LOW） |
| `required_findings` | 必须出现的关键发现（语义清单，用于交叉验证） |
| `legal_basis` | 期望的法律依据清单 |
| **`harness`** | **断言器配置**，由 `validators.py` 的 11 个操作符逐条执行 |

`harness` 里出现的操作符即断言操作符：`result_not_empty`、`fields_equal`、`min_counts`/`max_counts`、`list_contains`/`list_excludes`、`output_roles_contains`、`output_formats`、`fields_present`、`profile_contains`、`legal_basis_contains`。点路径如 `module_validation.actual_module` 用 `.` 下钻嵌套字段，`findings[].location` 表示「findings 列表每一项的 location」。

### 1.5 隐式输入：SQLite schema

`runner.py` 的 `_ensure_database_schema()` 在每次运行前初始化 SQLite（`review` 等模块需要 `ReviewTaskModel`/`UploadedFileModel` 等表）。

---

## 2. 输出（CLI 吐了什么）

### 2.1 运行证据包：`runs/<module>/<run_id>/`

`run_id` 形如 `20260812_022755_144350_03_module_mismatch`（时间戳 + 微秒 + case_id）。**每次运行一个目录**。

```
runs/eu_scc/20260812_022755_144350_03_module_mismatch/
├── input/
│   ├── request.json      # 解析后的输入负载（原样）
│   └── hash.txt          # 输入 sha256 哈希
├── output/
│   ├── result.json       # 序列化后的结果对象（model_dump）
│   └── error.json        # 仅失败时存在（type/message/traceback）
├── trace/
│   ├── 001_status.json
│   ├── 002_… .json       # 逐事件 trace（名字 = 事件名）
│   ├── 036_final.json
│   └── manifest.json     # trace 索引（seq/name/path/created_at）
└── run_manifest.json     # ★ 运行总清单（下详）
```

**关键：`runs/` 里存的不是「成品报告」，而是「运行过程证据」**（输入快照 + 结果快照 + trace + 可观测性摘要）。真正的报告文件在 `outputs/`（见 §2.3）。

### 2.2 运行总清单：`run_manifest.json`（★ 核心输出）

```json
{
  "schema_version": "1.0",
  "run_id": "20260812_013550_709281_02_structured",
  "module": "assessment",
  "module_id": "cn.security_assessment",
  "case_id": "02_structured",
  "status": "PASS",                      // PASS / FAIL
  "duration_ms": 400059.4,
  "attempts": 1, "max_attempts": 1,
  "input_hash": "03f2e3cf9158",
  "provider_snapshot": {                 // 用了哪个 LLM
    "mode": "live",                      // live / no_llm
    "provider_id": "siliconflow",
    "model": "deepseek-ai/DeepSeek-V3.2",
    "api_key_configured": true
  },
  "input": {                             // 输入摘要（脱敏）
    "sha256": "2a05499…",
    "fields": ["company_name", "industry", "…"],
    "artifacts": [ /* 上传附件的 file_name/file_role/storage_uri */ ]
  },
  "output": {                            // 输出摘要
    "fields": ["chapters", "output_files", "report_path", "…"],
    "artifacts": [ {"role": "markdown", "path": "outputs/…"}, … ]
  },
  "observability": {                     // 可观测性
    "event_count": 36,
    "trace_manifest": "…/trace/manifest.json",
    "llm_calls": 10,
    "tokens": { "prompt_tokens": 43099, "completion_tokens": 7207, "total_tokens": 50306 },
    "fallback_count": 0,
    "error_count": 0
  },
  "checks_passed": 18, "checks_failed": 0, "checks_skipped": 0,
  "recommended_path": "", "risk_level": "", "error": null
}
```

| 键组 | 含义 |
|---|---|
| 头部 | run_id / module / module_id / case_id / status / duration_ms / attempts |
| `provider_snapshot` | LLM 模式（live vs no_llm）与模型指纹 |
| `input` | 输入摘要：`sha256` + 顶层字段名 `fields` + 附件清单 `artifacts`（**不存完整正文**） |
| `output` | 输出摘要：顶层字段名 `fields` + 产物清单 `artifacts`（含 `output_files` 的 role→path） |
| `observability` | 事件数 / trace 清单路径 / LLM 调用次数 / token 用量 / fallback 次数 / 错误数 |
| checks_* | 断言通过/失败/跳过条数 |
| `error` | 失败时的 `{type, message, traceback}` |

> `input`/`output` 由 `backend/common/runtime/run_manifest.py` 的 `summarize_input()` / `summarize_output()` 生成，只保留「字段名 + 产物路径」，避免把敏感正文塞进清单。token 统计由 `summarize_trace()` 遍历 `trace/*.json` 里 `tool_result` 事件的 `usage` 累加。

### 2.3 真正的报告产物：`outputs/<module>/<task_id>/outputs/`

运行产生的**成品文件**（markdown/docx/pdf/json/xlsx/zip）落在这里，路径由服务内部的 `task_id`（uuid）决定，而非 harness 的 `run_id`。

```
outputs/assessment/<uuid>/outputs/
├── 跨境优品科技有限公司_数据出境风险自评估报告_草案_20260812.md
├── 跨境优品科技有限公司_数据出境风险自评估报告_草案_20260812.docx
├── 跨境优品科技有限公司_数据出境风险自评估报告_草案_20260812.pdf
├── 跨境优品科技有限公司_内部风险分析报告_20260812.md
├── issue_list.json / issue_list.xlsx
├── evidence_chain.json / evidence_chain.xlsx
└── …（含 zip 打包）
```

> 这些路径会回填进 `result.output_files`（role→path 映射），进而出现在 `run_manifest.json` 的 `output.artifacts` 里。`output_roles_contains` 断言就是校验这些 role 是否齐全。

### 2.4 trace 逐事件：`trace/`

`trace/` 是 `TraceRecorder` 逐事件落盘的过程证据，事件名即流水线步骤：

```
trace/001_status.json              # 状态开始
trace/003_profile_extracted.json   # 画像抽取
trace/008_facts_built.json         # 事实构建
trace/010_issues_built.json        # 问题构建
trace/011_evidence_built.json      # 证据构建
trace/030_chapters_generated.json  # 章节生成
trace/036_final.json               # 结束
trace/manifest.json                # 事件索引
```

每个 `NNN_name.json` 是单个事件（含 `name`、`payload`、`detail` 等）。`manifest.json` 汇总 `event_count` 与每个事件的 seq/name/path/created_at。

---

## 3. 数据流全景（一次运行的生命周期）

```
[1] argv: eu_scc 03_module_mismatch
        │
[2] 读 backend/tests/eu_scc/cases/03_module_mismatch.json
        │  (scenario_path / expected_path / source_doc_path)
[3] _resolve_case_input() ──► 读 benchmarks/.../scenario.json 的 request
[4] _resolve_case_expected() ──► 读 benchmarks/.../expected.json
        │
[5] _ensure_database_schema()          # SQLite 建表
[6] 建 run_dir = runs/eu_scc/<时间戳>_03_module_mismatch/
        │
[7] 写 input/request.json + input/hash.txt
        │
[8] adapter.invoke(case, no_llm, trace_dir)
        │   ├─ _generic_invoke: XxxRequest.model_validate(request) → service.generate_report()
        │   ├─ _diagnosis_invoke: DiagnosisService.evaluate()
        │   └─ _review_invoke: review_service.generate_from_request()
        │   （过程中 TraceRecorder 逐事件写 trace/*.json，
        │    服务内部把成品报告写 outputs/<module>/<uuid>/outputs/）
        │
[9] 写 output/result.json（或 output/error.json）
        │
[10] _check() 跑 validators.py 的断言 ──► passed/failed/skipped
        │
[11] 写 run_manifest.json（status + observability + checks + 摘要）
        │
[12] 打印一行结果：eu_scc/03_module_mismatch: PASS (163362 ms, 23 passed, 0 failed, …)
```

---

## 4. `tmp/` 是什么（易混淆，单独说明）

`tmp/` 是**另一个脚本** `scripts/rerun_all_modules.py` 的输出，**不是** harness runner 的产物。

| 路径 | 来源 | 内容 |
|---|---|---|
| `tmp/<module>/` | `rerun_all_modules.py` | 把成品 markdown 复制成 `markdown.md` + 精简的 `_result.json`（章节内容截断到 500 字），便于快速人工查看 |
| `tmp/<module>/*.md/*.docx/*.pdf/*.json` | 同上 | 复制的成品文件 |
| `tmp/verify/` | 交叉验证脚本 | `cross_verification_*.json`、最终验证报告 |

> 记忆：**harness → `runs/` + `outputs/`；`rerun_all_modules.py` → `tmp/`**。两者目的不同：harness 跑「断言验收」，rerun 脚本跑「人工抽查产物」。

---

## 5. 输入输出速查表

| 项 | 路径 | 类型 |
|---|---|---|
| 命令行参数 | `argv` | 模块 + case_id + 开关 |
| 案例定义 | `backend/tests/<module>/cases/<case_id>.json` | 输入（指针） |
| 共享场景（真实输入） | `benchmarks/cases/<module>/<scenario>/scenario.json` 的 `request` | 输入 |
| 期望/断言 | `benchmarks/cases/<module>/<scenario>/expected.json` 的 `harness` | 输入 |
| 来源文档 | `benchmarks/source-materials/...` | 输入（溯源/上传） |
| 运行证据包 | `runs/<module>/<run_id>/` | 输出 |
| 运行总清单 | `runs/<module>/<run_id>/run_manifest.json` | 输出（★） |
| 逐事件 trace | `runs/<module>/<run_id>/trace/` | 输出 |
| 真实报告文件 | `outputs/<module>/<task_id>/outputs/` | 输出 |
| 便捷重跑产物 | `tmp/<module>/` | 输出（另一脚本） |
| 交叉验证 | `tmp/verify/` | 输出（另一脚本） |
