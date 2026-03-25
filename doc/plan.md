# AI4Law 模块化开发执行计划（v0.1）

更新时间：2026-03-26  
适用阶段：D06 区域初赛（2026年3月-6月）  
执行原则：先可验收结果，后体验优化；先模块解耦，后全链路联调

---

## 1. 计划目标（可验收定义）

在初赛阶段交付以下可验收产物：
1. 可访问 Demo（v0 用 Streamlit）
2. 可录制演示视频的稳定流程（路径诊断、报告生成、文档审查）
3. 可导出报告文件（诊断报告 / 自评估报告 / PIPIA / 审查报告）
4. 初赛文档包（已在 `doc/doc4comp/`）与系统实现一致

完成标准：
1. 三条演示路径一次性跑通成功率 >= 95%
2. 关键输出均有结构化中间态（JSON Schema 校验通过）
3. 关键风险项可触发门控“需人工复核”

---

## 2. 依据与口径

冲突时严格按优先级：
1. `doc/architecture.md`
2. `doc/principle.md`
3. `doc/principle4modal/`

其他文档只作补充，不覆盖以上三类文档。

---

## 3. 工程化与模块化硬约束（必须遵守）

## 3.1 目录与模块边界

```text
backend/
  api/
  modules/
    diagnosis/
    assessment/
    scc/
    general/
    review/
  common/
    schema/
    rag/
    llm/
    risk/
    render/
    storage/
  tests/

ai_engine/
  prompts/
  schemas/
  rag/

app_streamlit/
  pages/
  components/
  services/
```

## 3.2 每个业务模块最小文件集

每个模块至少包含：
1. `router.py`（接口路由）
2. `service.py`（核心业务）
3. `schema.py`（输入输出对象）
4. `README.md`（模块说明 + 调用示例）
5. `tests/`（单元测试）

## 3.3 模块依赖规则

1. 业务模块之间禁止直接互调内部实现（只能通过接口或 common 层）。
2. 共用能力（RAG/LLM/渲染/风控）统一放在 `common/`。
3. 所有 LLM 输出必须先过 Schema 校验，再进入渲染层。

## 3.4 质量门禁（每次合并前）

1. 代码风格：`ruff check .` 通过
2. 测试：`pytest` 通过（至少覆盖本次改动模块）
3. 接口冒烟：核心 API 路径可返回有效结果
4. 文档同步：变更涉及功能时，更新模块 README 与进度日志

---

## 4. 模块任务分解（Task ID 级别）

状态值：`TODO | DOING | BLOCKED | DONE`

### 4.1 模块1：合规路径诊断（Diagnosis）

| Task ID | 任务 | 交付物 | 依赖 | 预估 | 状态 |
|---|---|---|---|---|---|
| DGN-01 | 决策树配置文件定义 | `backend/modules/diagnosis/decision_tree.json` | 无 | 0.5d | DONE |
| DGN-02 | 决策树执行器实现 | `backend/modules/diagnosis/service.py` | DGN-01 | 1d | DONE |
| DGN-03 | 诊断 API 路由 | `backend/modules/diagnosis/router.py` | DGN-02 | 0.5d | DONE |
| DGN-04 | 诊断报告渲染 | `backend/modules/diagnosis/report_renderer.py` | DGN-02 | 0.5d | DONE |
| DGN-05 | Streamlit 诊断页 | `app_streamlit/pages/1_Diagnosis.py` | DGN-03 | 0.5d | DONE |
| DGN-06 | 诊断模块测试 | `backend/modules/diagnosis/tests/*` | DGN-03 | 0.5d | DONE |

验收：
1. 固定输入输出一致
2. 可导出《合规路径诊断报告》

### 4.2 模块2：安全评估（Assessment）

| Task ID | 任务 | 交付物 | 依赖 | 预估 | 状态 |
|---|---|---|---|---|---|
| ASM-01 | 任务模型与状态机 | `backend/modules/assessment/task_state.py` | 无 | 0.5d | DONE |
| ASM-02 | 文件解析接入 | `backend/common/storage/file_parser.py` | 无 | 1d | DONE |
| ASM-03 | 企业画像抽取 | `backend/modules/assessment/profile_extractor.py` | ASM-02 | 1d | DONE |
| ASM-04 | 检索调用封装 | `backend/modules/assessment/retriever.py` | RAG-01 | 1d | DONE |
| ASM-05 | 章节生成器 | `backend/modules/assessment/chapter_generator.py` | LLM-01, ASM-04 | 1d | DONE |
| ASM-06 | 一致性校验器 | `backend/modules/assessment/consistency_checker.py` | ASM-05 | 0.5d | DONE |
| ASM-07 | 报告渲染器 | `backend/modules/assessment/report_renderer.py` | RDR-01 | 0.5d | DONE |
| ASM-08 | Assessment API | `backend/modules/assessment/router.py` | ASM-01~07 | 0.5d | DONE |
| ASM-09 | Streamlit 页面 | `app_streamlit/pages/2_Assessment.py` | ASM-08 | 0.5d | DONE |
| ASM-10 | 模块测试 | `backend/modules/assessment/tests/*` | ASM-08 | 1d | DONE |

验收：
1. 生成《数据出境风险自评估报告》docx
2. 输出含引用链与风险等级

### 4.3 模块3：认证/标准合同（SCC/PIPIA）

| Task ID | 任务 | 交付物 | 依赖 | 预估 | 状态 |
|---|---|---|---|---|---|
| SCC-01 | SCC 输入/输出 Schema | `ai_engine/schemas/scc/*` | 无 | 0.5d | DONE |
| SCC-02 | SCC Prompt 模板 | `ai_engine/prompts/scc/*` | 无 | 0.5d | DONE |
| SCC-03 | SCC 服务实现 | `backend/modules/scc/service.py` | ASM 通用链路 | 1d | DONE |
| SCC-04 | SCC API | `backend/modules/scc/router.py` | SCC-03 | 0.5d | DONE |
| SCC-05 | Streamlit 页面 | `app_streamlit/pages/3_SCC_PIPIA.py` | SCC-04 | 0.5d | DONE |
| SCC-06 | 模块测试 | `backend/modules/scc/tests/*` | SCC-04 | 0.5d | DONE |

验收：
1. 可生成《PIPIA 报告》docx
2. 与 Assessment 共享底座但配置隔离

### 4.4 模块4：通用服务（General）

| Task ID | 任务 | 交付物 | 依赖 | 预估 | 状态 |
|---|---|---|---|---|---|
| GEN-01 | 文书注册中心 | `backend/modules/general/registry.py` | 无 | 0.5d | TODO |
| GEN-02 | 生成基类 | `backend/modules/general/base_generator.py` | ASM 通用链路 | 0.5d | TODO |
| GEN-03 | TIA 示例接入 | `backend/modules/general/tia_generator.py` | GEN-01, GEN-02 | 0.5d | TODO |
| GEN-04 | General API | `backend/modules/general/router.py` | GEN-03 | 0.5d | TODO |
| GEN-05 | Streamlit 页面（可选） | `app_streamlit/pages/general.py` | GEN-04 | 0.5d | TODO |

验收：
1. 至少 1 种文书可配置化生成

### 4.5 模块5：文档智能审查（Review）

| Task ID | 任务 | 交付物 | 依赖 | 预估 | 状态 |
|---|---|---|---|---|---|
| RVW-01 | 条款切分器 | `backend/modules/review/clause_segmenter.py` | ASM-02 | 1d | TODO |
| RVW-02 | 条款分类器 | `backend/modules/review/clause_classifier.py` | LLM-01 | 0.5d | TODO |
| RVW-03 | 条款审查器 | `backend/modules/review/clause_reviewer.py` | RAG-01, RVW-02 | 1d | TODO |
| RVW-04 | 审查聚合器 | `backend/modules/review/review_aggregator.py` | RVW-03 | 0.5d | TODO |
| RVW-05 | 审查报告渲染 | `backend/modules/review/report_renderer.py` | RDR-01 | 0.5d | TODO |
| RVW-06 | Review API | `backend/modules/review/router.py` | RVW-01~05 | 0.5d | TODO |
| RVW-07 | Streamlit 页面 | `app_streamlit/pages/review.py` | RVW-06 | 0.5d | TODO |
| RVW-08 | 模块测试 | `backend/modules/review/tests/*` | RVW-06 | 0.5d | TODO |

验收：
1. 输出条款级问题清单（定位/依据/等级/建议）
2. 可导出审查报告

### 4.6 共用底座任务

| Task ID | 任务 | 交付物 | 依赖 | 预估 | 状态 |
|---|---|---|---|---|---|
| RAG-01 | RAG 最小链路 | `backend/common/rag/*` | 无 | 1.5d | DONE |
| LLM-01 | LLM 适配层 | `backend/common/llm/adapter.py` | 无 | 1d | DONE |
| SCH-01 | Schema 校验器 | `backend/common/schema/validator.py` | 无 | 0.5d | DONE |
| RSK-01 | 风险分级与门控 | `backend/common/risk/*` | SCH-01 | 1d | DONE |
| RDR-01 | 统一渲染器 | `backend/common/render/*` | SCH-01 | 1d | DONE |
| OBS-01 | 日志与追踪 | `backend/common/observability/*` | 无 | 0.5d | DONE |

---

## 5. 迭代节奏（周计划）

1. 第1周：共用底座 + 模块1
2. 第2周：模块2主链路
3. 第3周：模块3 + 模块2稳定性
4. 第4周：模块5
5. 第5周：模块4最小接入 + 全链路联调
6. 第6周：演示打磨 + 初赛材料封版

---

## 6. 进度记录机制（必须执行）

## 6.1 记录文件

1. `doc/plan.md`：任务状态（TODO/DOING/BLOCKED/DONE）
2. `doc/progress.md`：每日进度日志（新增）

## 6.2 记录频率

1. 每天至少 2 次更新（中午 / 晚上）
2. 每完成一个 Task ID，立即记录一次
3. 遇到 BLOCKED 超过 4 小时必须记录并升级

## 6.3 每条进度记录必填项

1. 日期与时间
2. Task ID
3. 当前状态
4. 产出文件路径
5. 验证命令与结果
6. 下一个动作

## 6.4 完成定义（任务级）

Task 从 DOING -> DONE 必须同时满足：
1. 代码完成并通过自测
2. 至少 1 条测试通过记录
3. 相关文档/README 已同步
4. `doc/progress.md` 已登记

---

## 7. 联调与验收

## 7.1 模块联调顺序

1. 模块1 -> 模块2 -> 模块3
2. 模块5 接入共用底座后联调
3. 模块4 最后接入，不阻塞主流程

## 7.2 全链路验收场景

1. 场景A：路径诊断 -> 安全评估报告导出
2. 场景B：路径诊断 -> SCC(PIPIA) 报告导出
3. 场景C：上传文档 -> 条款级审查报告导出

---

## 8. 初赛提交物映射

1. 项目简介：`doc/doc4comp/01-D06-区域初赛-项目简介.md`
2. Demo说明：`doc/doc4comp/02-D06-区域初赛-项目Demo与演示视频说明.md`
3. 总清单：`doc/doc4comp/00-D06-区域初赛-提交材料总清单.md`
4. Demo 链接：Streamlit 公网地址
5. Demo 视频：按场景A/B/C录制

---

## 9. 风险与预案

1. 第三方接口波动：准备降级路径（本地知识库 + 缓存结果）
2. 输出不稳定：Schema 校验 + 重试 + 门控
3. 并行开发冲突：统一按 Task ID + 模块边界开发
4. 前端耗时风险：v0 固定 Streamlit，不引入复杂前端

---

## 10. v1 迁移（初赛后）

1. 在不改动后端契约的前提下，逐步从 Streamlit 迁移到 Next.js
2. 迁移顺序：Diagnosis -> Assessment/SCC -> Review -> General

---

## 11. Git 存档规则（强制）

为保证可追溯、可回滚、可协作，v0 开发阶段每次开发必须进行 Git 存档。

### 11.1 触发时机

满足任一条件必须提交一次：
1. 完成 1 个 Task ID 并达到 DONE
2. 一个功能点可独立演示或独立测试通过
3. 当日开发结束（即使任务未完成，也要提交 WIP）

### 11.2 提交粒度

1. 一次提交只对应一个模块或一个共用底座任务
2. 不允许把多个无关模块改动混在同一个提交
3. 文档变更需与对应代码提交同批或紧随其后提交

### 11.3 提交信息规范

推荐格式：
`<type>(<scope>): <summary> [<TaskID>]`

示例：
1. `feat(diagnosis): add rule engine and result schema [DGN-02]`
2. `feat(assessment): add chapter generator and validator [ASM-05]`
3. `docs(plan): update task status and progress log [ASM-05]`

类型建议：
1. `feat`：新增能力
2. `fix`：缺陷修复
3. `refactor`：重构
4. `test`：测试
5. `docs`：文档
6. `chore`：杂项

### 11.4 推送规则

1. 每日至少推送一次到远程分支
2. 里程碑完成（M1/M2/M3/M4）后必须立即推送
3. 推送失败要在 `doc/progress.md` 记录失败原因和重试结果

### 11.5 存档核对清单

每次提交前检查：
1. `git status` 仅包含本任务相关文件
2. 对应测试命令已执行并记录结果
3. `doc/progress.md` 已登记 Task ID 与产出路径
4. 提交后已执行 `git push`
