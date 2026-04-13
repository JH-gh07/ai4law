# AI4Law 文档总览与当前状态

更新时间：2026-03-26

本文件用于记录项目文档全景、口径优先级、当前开发状态与交付材料位置，作为团队统一入口。

---

## 1. 项目当前状态（摘要）

1. 项目阶段：D06 区域初赛开发阶段（v0）
2. 主策略：后端优先 + Streamlit 轻前端，先可验收结果再优化体验
3. 已完成文档：
   - 初赛提交材料首版（`doc/doc4comp/00~02`）
   - 模块化执行计划（`doc/plan.md`）
   - 进度日志模板（`doc/progress.md`）

---

## 2. 文档口径优先级（冲突处理规则）

冲突时按以下优先级执行：
1. `doc/architecture.md`
2. `doc/principle.md`
3. `doc/principle4modal/`
   - `doc/principle4modal/user.md`
   - `doc/principle4modal/principle4smallpart.md`

说明：
- 以上文档是当前“正式口径与实现依据”。
- 需求、架构、流程、模块定义如有差异，统一以以上三类文档为准。

---

## 3. 比赛提交文档目录（初赛）

目录：`doc/doc4comp/`

当前已生成：
1. `00-D06-区域初赛-提交材料总清单.md`
2. `01-D06-区域初赛-项目简介.md`
3. `02-D06-区域初赛-项目Demo与演示视频说明.md`
4. `04-第十七届中国大学生服务外包创新创业大赛D类赛题手册.pdf`（参考原始手册）

---

## 4. 开发执行文档

1. `doc/plan.md`：模块化开发执行计划（Task ID、依赖、验收标准）
2. `doc/progress.md`：开发进度日志（每日更新、阻塞升级）

---

## 5. 参考/草稿文档（非主口径）

以下文档保留用于回溯或补充，不作为冲突时主依据：
1. `doc/raw.md`
2. `doc/prd.md`
3. `doc/pipeline.md`
4. `doc/advice.md`
5. `doc/competition.md`

---

## 6. 维护规则

1. 新增或修改关键功能后，必须同步更新：
   - `doc/plan.md`（任务状态）
   - `doc/progress.md`（执行记录）
   - `doc/doc4comp/`（若影响提交内容）
2. 任何“口径变更”必须先更新本文件再通知团队。
3. 所有开发变更必须按计划中的 Git 存档规则执行（见 `doc/plan.md`）。
