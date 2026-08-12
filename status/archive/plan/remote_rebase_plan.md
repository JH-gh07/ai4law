# 远程规范化重构 → 本地功能接入方案

> 创建时间：2026-07-19
> 目标：基于远程工程化规范化版本（origin/new），将本地功能增量系统化接入

---

## 一、对远程重构的理解

远程 `origin/new` 是**工程化规范化版本**，不删功能，只改组织方式：

| 维度 | 旧形态 | 新形态 | 收益 |
|------|--------|--------|------|
| 模块组织 | `backend/modules/` 扁平11个目录 | `backend/domains/{cn,eu,us}/` 按法域分层 | 法域归属一目了然，CN/EU/US 模块各自闭环 |
| 模块注册 | 硬编码在 `main.py` 的 import + include_router | `config/module_registry.json` 声明式目录 | 新增模块只需加 JSON 条目，不碰启动代码 |
| RAG 检索 | 各模块各自调用 `retrieve_regulations()` | 统一走 `common/rag/` facade | 检索策略可全局切换、评测可集中执行 |
| 渲染管线 | 各模块各自写 render 逻辑，重复 11 次 | `common/render/` 统一 SSOT（ReportDocument → multi-format） | 一份规范约束全部 12 个模块输出一致性 |
| 评测体系 | `common/rag/eval.py` 散落 | `benchmarks/` 独立目录，Pydantic schema | 评测与业务代码解耦，可独立演进 |
| 前端 | 全量同步加载 | lazy-load + ErrorBoundary + PdfViewer 组件化 | 首屏快 + PDF 预览统一 |
| 资产归档 | `doc/` 下混杂旧设计文档 | `docs/archive/` 归档 + `plan/` + `resources/` | 活跃 vs 归档清晰分离 |
| 命名规范 | 中文文件名、混合命名 | 下划线规范化路径 | CI/CD 友好 |

**关键设计决策**：旧 `backend/modules/` **仍然保留**。`module_registry.json` 中每个条目同时声明了 `implementation_package`（指向新 domains 路径）和 `v1_api_prefix`。两个路径的代码内容对齐——新 domains 是重构副本，旧 modules 是过渡期保留的兼容路径。

---

## 二、两棵代码树的对照

```
archive/local-full（完整本地功能）          origin/new（远程规范化版本）
─────────────────────────────────         ──────────────────────────────
backend/modules/assessment/           ←→  backend/domains/cn/security_assessment/
backend/modules/diagnosis/            ←→  backend/domains/cn/transfer_diagnosis/
backend/modules/scc/                  ←→  backend/domains/cn/scc_review/
backend/modules/pipia/                ←→  backend/domains/cn/pipia/
backend/modules/dpia/                 ←→  backend/domains/eu/dpia/
backend/modules/bcr/                  ←→  backend/domains/eu/bcr_review/
backend/modules/eu_scc/               ←→  backend/domains/eu/scc_review/
backend/modules/tia/                  ←→  backend/domains/eu/tia/
backend/modules/cpra/                 ←→  backend/domains/us/cpra/
backend/modules/us_14117/             ←→  backend/domains/us/eo14117/
backend/modules/cn_flow/              ←→  backend/domains/us/eo14117_flow_review/
backend/modules/v0_task_gateway/      ←→  (保留在 modules/ — 路由层非法域模块)
backend/services/review_service/      ←→  backend/domains/cn/document_review/
```

---

## 三、本地需要接入的 5 个功能增量

分析 `archive/local-full` 相比 `origin/new` 多出的 15 个 commit，识别出 5 个需接入的功能：

### 增量 1：11 模块全覆盖 Test Harness（6 commits）

```
f749cbd feat(harness): full-coverage test harness — all 11 modules
02bc68c feat(harness): add DPIA module tests
a5d5dba feat(harness): add assessment module + modular validation
1ee83ac refactor(harness): modular runner + clean naming + explicit output path
31ffa06 feat(harness): new test harness wrapping service.evaluate() as black box
```

**内容**：通过 `scripts/eval_runner.py` + `scripts/eval_checkers/` 实现的 11 模块黑盒测试框架。

**接入策略**：需要路径映射——harness 引用 `backend/modules/assessment/service.py`，需同时兼容新路径 `backend/domains/cn/security_assessment/service.py`。最优方案是 harness 改为引用 `module_registry.json` 的 `implementation_package` 动态导入。

### 增量 2：统一渲染管线阶段 A-D（4 commits）

```
92ebcc7 feat(render): P0 — jit-pdf-sdk 集成
5e80b55 feat(render): 阶段B+C+D — ReportDocument + SSOT规则 + PDF/MD双视图
34de06a feat(render): 阶段A — 统一PDF渲染器，12/12模块PDF全覆盖
e8e3d66 feat(render): D-1/D-2 artifact_registry + render_profile + diagnosis迁移
```

**内容**：`common/render/` 下的 ReportDocument SSOT、统一 PDF 渲染器、规范化规则、前端 PdfViewer。

**接入策略**：远程的 `common/render/` 已有相同结构（A 阶段渲染器 + B 阶段 ReportDocument + D 阶段规范化规则）。需对比本地版本是否多了功能（如 `render_profile.py`、jinja2 模板等），只接入增量部分。

### 增量 3：测试验收 + 引用修复（2 commits）

```
d74c06f test: 引用跳转 URL 修复验收 — 33 个用例全部通过
6b72d88 fix: 全模块覆盖——所有 citation_map 写入路径统一走 normalize_citation_item 流水线
```

**内容**：引用系统修复 + 33 个测例。

**接入策略**：远程的 `common/citation/` 也已重构。需对比 citation 目录差异，将 33 个测例和 normalize 流水线纳入新结构下的测试。

### 增量 4：清理操作（1 commit）

```
9fd4165 chore: clean up old harness run artifacts, gitignore runs/
```

**内容**：gitignore 忽略 runs/、清理旧 harness 产物。

**接入策略**：远程已有 `bf719ec chore: remove runtime and generated assets from source control` 做了同样的事。只需确认 runs/ 和 storage/traces/ 确实被忽略。

### 增量 5：架构文档（1 commit）

```
ab4be94 docs: add CODE_MODULE_ARCHITECTURE.md — complete 11-module logic flow documentation
```

**内容**：根目录 CODE_MODULE_ARCHITECTURE.md。

**接入策略**：直接复制到新分支，但需更新模块路径为 `domains/` 结构。可生成 v2 版本。

---

## 四、接入执行方案（5 步，2-3 天可完成）

### 第 1 步：环境就绪（15 分钟）

```bash
# ✅ 已完成
git branch archive/local-full new    # 存档完整本地功能

# 待执行
git checkout new
git reset --hard origin/new          # 将 new 指向纯远程版本
git checkout -b feature/port-local-to-domains  # 新建接入分支
```

### 第 2 步：差异审计（30 分钟）

```bash
# 对比本地 full 版本 vs 远程干净版本的核心文件差异
git diff archive/local-full..origin/new --stat > plan/diff_full_vs_remote.txt

# 逐个模块对比新老路径对应关系
diff -rq backend/modules/assessment/ backend/domains/cn/security_assessment/
# ... 重复 11 个模块

# 检查远程是否有模块缺失
# 重点：v0_task_gateway 在新 domains 中是否有对应
```

产出 `plan/module_path_mapping.md`——每个模块的新老路径精确对照表。

### 第 3 步：Test Harness 接入（半天）

这是最大的增量。接入步骤：

1. **复制 harness 文件到新结构**：
   ```
   scripts/eval_runner.py           → 保留（位置不变）
   scripts/eval_checkers/           → 保留（位置不变）
   ```

2. **修改导入路径适配新旧两种路径**：
   ```python
   # 旧代码
   from backend.modules.assessment.service import AssessmentService
   
   # 新代码：先尝试新路径，fallback 旧路径
   try:
       from backend.domains.cn.security_assessment.service import AssessmentService
   except ImportError:
       from backend.modules.assessment.service import AssessmentService
   ```

3. **验证 11 模块在新结构下全部通过**：
   ```bash
   python scripts/eval_runner.py --module all --smoke
   ```

### 第 4 步：渲染管线增量接入（半天）

1. **对比 `common/render/` 差异**：
   ```bash
   diff -rq archive/local-full/backend/common/render/ backend/common/render/
   ```

2. **接入本地独有的文件**（如 `render_profile.py`、特定 jinja2 模板等）

3. **前端 PdfViewer 确认**：检查远程是否已有 `PdfViewer.tsx`（commit `92ebcc7` 已将 P0 部分接入远程），确认无功能缺失

4. **SSOT 规范化规则验证**：运行 `normalization_test_cases.json` 确保新旧规则一致

### 第 5 步：验证 + 提交（半天）

1. **运行 12 模块 smoke test**：
   ```bash
   python benchmarks/smoke_eval.py
   ```

2. **运行 RAG 检索评测**：
   ```bash
   python benchmarks/rag_retrieval_eval.py
   ```

3. **运行 citation 33 测例**：将本地测例文件复制到 `benchmarks/` 下执行

4. **生成 CODE_MODULE_ARCHITECTURE_v2.md**：基于 domains 结构重新生成架构文档

5. **提交**：
   ```
   feat(port): migrate test harness to domains structure
   feat(port): reconcile render pipeline incrementals
   fix(port): merge citation normalization fix
   docs: add CODE_MODULE_ARCHITECTURE v2 for domains structure
   ```

---

## 五、风险点与应对

| 风险 | 概率 | 应对 |
|------|------|------|
| domains 下某模块缺少 modules 下的文件（重构遗漏） | 中 | 第2步 diff 审计逐模块对比，发现缺失则从 archive 补回 |
| v0_task_gateway 在新结构中无对应 | 高 | gateway 是路由层，本质不依赖模块路径——不需迁移，保留在 modules/ 即可 |
| 远程 render 管线比本地版本更新（pull request #2 合并了新的 render 改动） | 中 | 第4步 diff 确认，优先用远程更新版本，本地增量择优补充 |
| 旧 modules/ 路径在新 main.py 中不再 import | 低 | main.py 现在通过 module_registry.json 动态加载，旧 import 已移除。harness 需同步改为动态导入 |
| 数据库 schema 变化 | 低 | 远程未改模型，但 `d5624ca` 统一了 RAG v3 索引路径，需重建索引 |

---

## 六、最终目录结构预期

```
ai4law/
├── backend/
│   ├── domains/                    ★ 新：按法域的 12 模块
│   │   ├── cn/  (security_assessment, transfer_diagnosis, scc_review, pipia, document_review)
│   │   ├── eu/  (dpia, bcr_review, scc_review, tia)
│   │   └── us/  (cpra, eo14117, eo14117_flow_review)
│   ├── modules/                    ★ 保留：向后兼容
│   │   └── v0_task_gateway/       ← 唯一保留在 modules 的（路由层，非法域模块）
│   ├── common/                     ★ 统一基础设施
│   ├── services/                   ★ 逐步迁移到 domains/cn/document_review/
│   ├── core/
│   └── api/
├── benchmarks/                     ★ 新：标准化评测体系
├── config/                         ★ 新：模块注册表
├── scripts/                        ★ 保留：eval_runner + eval_checkers
├── docs/                           ★ 新：治理文档 + 归档
├── plan/                           ★ 当前迁移方案
├── resources/                      ★ 新：法律/研究/规则/模板
└── CODE_MODULE_ARCHITECTURE.md     ★ 接入后更新为 v2
```
