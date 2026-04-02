# AI4Law v2 开发计划（执行版）

更新时间：`2026-04-02`  
适用范围：`2.2 / 2.3 / 3.2 / 3.3 / 3.4 / 4.1 / 4.2` 与公共底座

## 1. 目标与约束

1. 目标：先交付可验收的 v0，再迭代到 v1。  
2. 核心约束：规则先行、引用可追溯、模板收口、全链路可审计。  
3. 输出要求：每个模块至少产出 1 份可下载文档，并有对应验收记录。

## 2. 进度标记规范（强制）

### 2.1 状态枚举
- `todo`：未开始
- `in_progress`：开发中
- `blocked`：阻塞中（必须写阻塞原因）
- `review`：待验收
- `done`：已验收通过

### 2.2 优先级枚举
- `P0`：当前迭代必须完成
- `P1`：下一迭代完成
- `P2`：可后置

### 2.3 任务看板字段
- `task_id`
- `module`
- `owner`
- `priority`
- `status`
- `start_date`
- `due_date`
- `acceptance_id`
- `evidence_path`
- `blocked_reason`
- `last_update`

## 3. 验收方式（强制）

### 3.1 通用验收条件（所有任务都要满足）
1. 输入校验通过：schema 校验 + 附件校验均通过。  
2. 规则可解释：返回规则命中结果（含命中项）。  
3. 结果可追溯：输出文档含法规依据与来源标识。  
4. 文件可下载：输出文件可访问且命名符合规范。  
5. 审计可复核：任务日志可回放（输入、规则、检索、输出）。

### 3.2 验收记录模板
```text
acceptance_id:
task_id:
验收人:
验收日期:
输入样例:
预期输出:
实际输出:
检查项:
结论: pass / fail
证据路径:
备注:
```

## 4. 任务分解（v0）

### 4.1 公共底座（P0）
| task_id | 任务 | priority | status | acceptance_id |
|---|---|---|---|---|
| T-BASE-01 | 统一任务引擎（create/status/cancel/artifacts） | P0 | done | A-BASE-01 |
| T-BASE-02 | 文件上传与附件管理 | P0 | done | A-BASE-02 |
| T-BASE-03 | schema 校验与规则执行框架 | P0 | in_progress | A-BASE-03 |
| T-BASE-04 | 模板渲染服务（docx/pdf/xlsx/zip） | P0 | in_progress | A-BASE-04 |
| T-BASE-05 | 审计日志（规则命中/检索来源/模型版本） | P0 | done | A-BASE-05 |

### 4.2 模块开发（P0/P1）
| task_id | 模块 | 任务 | priority | status | acceptance_id |
|---|---|---|---|---|---|
| T-22-01 | 2.2 | 端到端打通（输入->规则->生成->docx+zip） | P0 | done | A-22-01 |
| T-23-01 | 2.3 | PIPIA 草案生成链路 | P0 | done | A-23-01 |
| T-33-01 | 3.3 | DPIA 草案生成链路 | P0 | done | A-33-01 |
| T-34-01 | 3.4 | TIA 草案生成链路 | P0 | done | A-34-01 |
| T-32-01 | 3.2 | BCR 审查评分与报告 | P1 | done | A-32-01 |
| T-42-01 | 4.2 | CPRA 全景报告与路线图 | P1 | todo | A-42-01 |
| T-41-01 | 4.1 | 输入链路与风险清单（输出章节待补） | P1 | todo | A-41-01 |

### 4.3 测试与发布（P0）
| task_id | 任务 | priority | status | acceptance_id |
|---|---|---|---|---|
| T-QA-01 | 模块冒烟测试与回归清单 | P0 | todo | A-QA-01 |
| T-QA-02 | 样例数据集与基准输出对比 | P0 | todo | A-QA-02 |
| T-REL-01 | v0 打包发布与演示脚本 | P0 | todo | A-REL-01 |

### 4.4 当前进度看板（实时）
| task_id | module | owner | priority | status | start_date | due_date | acceptance_id | evidence_path | blocked_reason | last_update |
|---|---|---|---|---|---|---|---|---|---|---|
| T-BASE-01 | BASE | codex | P0 | done | 2026-04-02 | 2026-04-02 | A-BASE-01 | `outputs/acceptance/A-BASE-01/` |  | 2026-04-02 |
| T-BASE-02 | BASE | codex | P0 | done | 2026-04-02 | 2026-04-02 | A-BASE-02 | `outputs/acceptance/A-BASE-01/` |  | 2026-04-02 |
| T-BASE-03 | BASE | codex | P0 | in_progress | 2026-04-02 | 2026-04-03 | A-BASE-03 | `outputs/acceptance/A-BASE-01/` | 多模块规则项尚未统一化 | 2026-04-02 |
| T-BASE-04 | BASE | codex | P0 | in_progress | 2026-04-02 | 2026-04-03 | A-BASE-04 | `outputs/acceptance/A-22-01/` | 2.3/3.x/4.x 渲染尚未接入统一出口 | 2026-04-02 |
| T-BASE-05 | BASE | codex | P0 | done | 2026-04-02 | 2026-04-02 | A-BASE-05 | `outputs/acceptance/A-BASE-05/` |  | 2026-04-02 |
| T-22-01 | 2.2 | codex | P0 | done | 2026-04-02 | 2026-04-02 | A-22-01 | `outputs/acceptance/A-22-01/` |  | 2026-04-02 |
| T-23-01 | 2.3 | codex | P0 | done | 2026-04-02 | 2026-04-02 | A-23-01 | `outputs/acceptance/A-23-01/` |  | 2026-04-02 |
| T-33-01 | 3.3 | codex | P0 | done | 2026-04-02 | 2026-04-02 | A-33-01 | `outputs/acceptance/A-33-01/` |  | 2026-04-02 |
| T-34-01 | 3.4 | codex | P0 | done | 2026-04-02 | 2026-04-02 | A-34-01 | `outputs/acceptance/A-34-01/` |  | 2026-04-02 |
| T-32-01 | 3.2 | codex | P1 | done | 2026-04-02 | 2026-04-02 | A-32-01 | `outputs/acceptance/A-32-01/` |  | 2026-04-02 |

## 5. 模块级验收标准（DoD）

### 5.1 2.2 / 2.3 / 3.3 / 3.4（草案生成类）
1. 给定样例输入，30 分钟内可生成目标 `docx`。  
2. 输出文档章节完整，字段不为空（允许显式“待补充”但不可漏章）。  
3. 引用区至少包含 3 条法规或模板依据。  
4. 同一输入重复运行，关键章节差异可控（语义一致，不出现冲突结论）。

### 5.2 3.2（审查评分类）
1. 覆盖 `3.2-C1~C10` 审查项。  
2. 输出包含：评级、问题列表、优先级、整改建议。  
3. 每个问题包含定位与依据。

### 5.3 4.2（合规评估类）
1. 输入字段覆盖 `4.2-1.1~4.2-4.4`。  
2. 输出章节覆盖 5 章映射（依据 `module_output_structure.csv`）。  
3. 产出 docx 与整改路线图（xlsx）。

### 5.4 4.1（当前阶段）
1. 输入数据清单与实体清单可解析并入库。  
2. 输出风险清单（xlsx）可用。  
3. 报告章节模板缺口必须在交付说明中显式标注。

## 6. 证据与存档要求（强制）

1. 每个 `task_id` 必须有 `evidence_path`（示例：`outputs/acceptance/A-22-01/`）。  
2. 每次开发完成必须提交 Git（最少一条 commit），提交信息格式：  
`[task_id] <scope>: <summary>`  
示例：`[T-22-01] module-2.2: wire schema validation and report render`
3. 验收通过后，更新状态为 `done` 并补全验收记录。

## 7. 周期与节奏

1. 日更：每天更新一次任务看板（`last_update` 必填）。  
2. 周更：每周产出一次里程碑报告（已完成、阻塞、下周计划）。  
3. 里程碑判定：
- `M1`：公共底座 + 2.2 通过验收
- `M2`：2.3/3.3/3.4 通过验收
- `M3`：3.2/4.2 通过验收，4.1 完成阶段目标

## 8. 当前行动（下一步）

1. 推进 `T-BASE-04`：抽出统一渲染出口，补齐 `pdf/xlsx` 产物链路。  
2. 开工 `T-41-01`：实现 4.1 输入链路与风险清单（xlsx）可下载。  
3. 开工 `T-42-01`：实现 4.2 CPRA 全景报告与路线图产物。  
