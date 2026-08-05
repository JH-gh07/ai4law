# DataComplyFlow Schema 契约修复与复验

> 日期：2026-08-06  
> 分支：`new`  
> 范围：开发测试案例、浏览器一键体验、Review 文件预设、HTTP Schema 契约  
> 关联原始审计：`status/DataComplyFlow_全功能运行验证与问题汇报_20260805.md`

## 1. 核心结论

本轮问题已经修复。26 个开发案例的真实 HTTP 调用由 **9/26 提升为 26/26**；原先失败的 7 条浏览器路径全部恢复并产出结果。

原结论“17 例全部是 Pydantic 第一关拦截”方向接近，但不够精确：

| 失败位置 | 原失败数 | 准确归类 | 是否进入核心业务 |
|---|---:|---|---|
| HTTP Pydantic 校验 | 15 | 字段名、枚举、类型、必填项漂移，HTTP 422 | 否 |
| Review 服务前置条件 | 2 | 已通过 Pydantic，但缺少文件，HTTP 400/403 | 否 |
| 浏览器 Payload Builder | 7 条路径 | 旧请求结构、非法附件扩展名、预设未注入文件或字段 | 否 |

因此更准确的一句话是：**故障主体是测试资产与适配层相对当前后端契约发生漂移，不是 Agent、RAG、规则引擎或报告生成逻辑故障；但失败并非全部发生在 Pydantic 层。**

## 2. 修复内容

| 模块 | 修复前 | 修复动作 | 代码证据 |
|---|---|---|---|
| Diagnosis | 旧枚举直接 POST 得到 422 | 对齐当前 `TransferScenario` 和接收方类型枚举 | `frontend/src/lib/dev-test-cases.ts` |
| Assessment | 字符串传给结构化子模型 | 改为结构化对象 | `frontend/src/lib/dev-test-cases.ts` |
| BCR | `review_items` 缺 `finding/legal_basis/recommendation` | 统一补全每个审查项 | `frontend/src/lib/dev-test-cases.ts:594` |
| TIA | 附件角色和扩展名过期 | 改为 `country_law_analysis` 和 DOCX | `frontend/src/lib/dev-presets.ts:201` |
| PIPIA | 缺 `company_uscc` | 两个案例补齐统一社会信用代码 | `frontend/src/lib/dev-test-cases.ts` |
| US 14117 | 数据项、实体、人员、措施沿用旧字段 | 全量对齐当前嵌套 Schema，并补齐四步表单预设 | `frontend/src/lib/dev-test-cases.ts` |
| CN Flow | `country` 漂移；浏览器没有文件状态 | 改为 `country_region`，测试案例注入数据清单和实体清单 | `frontend/src/lib/dev-test-cases.ts:1261`、`frontend/src/components/workspace/ModuleRunPanel.tsx:1066` |
| Review | Payload 只有元数据；新资源目录被安全边界拒绝 | 案例提供真实文件；只将受信任 `resources/legal/sources` 加入预设复制白名单 | `backend/domains/cn/document_review/service.py:693` |
| EU SCC | 浏览器 Builder 仍生成旧字段 | Builder 改为当前 `project_name/scc_text/declared_module_type` 契约 | `frontend/src/components/workspace/ModuleRunPanel.tsx:746` |
| BCR/DPIA/TIA 一键体验 | 预设 `.txt` 被 Builder 的扩展名校验拦截 | 替换为仓库内真实、受支持的 DOCX 模板 | `frontend/src/lib/dev-presets.ts:130` |

Review 的修复没有放宽为“任意本地路径可读”。服务仍先接受 storage 内文件；外部开发预设只允许 `doc/` 和 `resources/legal/sources/`，其他路径继续返回 403。对应安全回归测试见 `backend/api/v1/tests/test_review_async.py:152`。

## 3. 复验结果

### 3.1 HTTP 开发案例

在新启动的当前代码后端上注册独立测试用户，逐条执行 `DEV_TEST_CASES` 中 26 个 payload：

| 模块 | 结果 |
|---|---:|
| CPRA | 3/3 |
| Diagnosis | 3/3 |
| Assessment | 2/2 |
| EU SCC | 3/3 |
| BCR | 3/3 |
| DPIA | 2/2 |
| TIA | 2/2 |
| PIPIA | 2/2 |
| Review | 2/2 |
| CN Flow | 2/2 |
| US 14117 | 2/2 |
| **合计** | **26/26** |

这里验证的是 HTTP 路由、Pydantic、服务前置条件和结果生成，不再是绕开 HTTP 层的 `service.generate_report()` 直调。

### 3.2 浏览器回归

对原先失败的 7 个模块，在修复后的前后端中重新创建项目、选择/注入预设并运行：

| 浏览器路径 | 修复后材料数 | 修复后结果数 | 结论 |
|---|---:|---:|---|
| Document Review | 2 | 2 | PASS |
| EU SCC | 2 | 6 | PASS |
| BCR | 8 | 4 | PASS |
| DPIA | 4 | 14 | PASS |
| TIA | 4 | 5 | PASS |
| US 14117 | 2 | 10 | PASS |
| CN Flow | 5 | 9 | PASS |
| **合计** | - | **50 项结果** | **7/7 PASS** |

原先已经通过的 Diagnosis、Assessment、PIPIA、CPRA 未出现对应契约变更；本轮重点复验的是原失败路径。不能仅凭这张表把执行流 Token、RAG 命中和外部 LLM 能力一并判定为正常。

![CN Flow 修复后生成 9 项结果](assets/DataComplyFlow_Schema修复验证_20260806/01_CN_Flow_修复后生成9项结果.png)

![修复后浏览器测试项目清单](assets/DataComplyFlow_Schema修复验证_20260806/02_修复后浏览器项目清单.png)

### 3.3 自动化回归

| 验证项 | 命令/方式 | 结果 |
|---|---|---:|
| 前端测试 | `npm --prefix frontend test -- --run` | 17 files / 61 tests PASS |
| 前端构建 | `npm --prefix frontend run build` | PASS，342 modules transformed |
| 后端测试 | `uv run --frozen pytest -q --disable-warnings` | 530 PASS / 1 warning |
| CLI harness | `uv run --frozen python -m backend.tests.harness.runner all --no-llm --quiet` | 15 PASS / 0 FAIL / 11 modules |
| 新增契约测试 | `dev-test-cases.test.ts`、`dev-presets.test.ts` | 13 PASS |
| Review 白名单测试 | `test_review_async.py` 新增 2 项 | 2 PASS |

CLI 仍输出 `socksio` 缺失并使用 fallback；因为命令显式使用 `--no-llm`，15/15 只能证明离线服务链没有回归，不能证明真实模型、Token 计量或外部 Provider 正常。

## 4. 为什么会反复漂移

当前仓库实际上维护了三套相互独立的输入真相：

1. 后端 Pydantic Schema；
2. `dev-test-cases.ts` 的直接 Payload；
3. `formDefaults` 经 `ModuleRunPanel` Builder 转换后的浏览器 Payload。

Schema 改动后，后两套资产不会自动失败或自动迁移，直到人工运行才暴露。CLI harness 又使用另一套 JSON 且绕开 HTTP，因此 CLI 全绿无法覆盖这种漂移。

本轮增加的契约测试先把最容易复发的字段、枚举和扩展名固定下来。中期应继续做两件事：

| 优先级 | 建议 | 目的 |
|---|---|---|
| P0 | CI 启动真实 API，逐条 POST 26 个开发案例 | 直接阻止 Schema 漂移再次合入 |
| P1 | 把各模块 Builder 抽成无 UI 依赖的纯函数，让 `formDefaults` 和浏览器共用 | 消除“直投成功、浏览器失败”或反向失败 |
| P1 | 给 Review 这类有文件状态的模块声明专用测试策略 | 不再伪装成普通单次 JSON POST |
| P2 | 从 OpenAPI/类型生成或共享契约中派生前端类型 | 降低手写字段和枚举的重复维护成本 |

## 5. 总结表

| 指标 | 修复前 | 修复后 | 状态 |
|---|---:|---:|---|
| 开发案例 HTTP 通过率 | 9/26（34.6%） | 26/26（100%） | 已修复 |
| 原失败浏览器路径 | 0/7 | 7/7 | 已修复 |
| 前端测试 | 无针对漂移的门禁 | 61/61，含 13 项新增契约测试 | 已补门禁 |
| 后端测试 | Review 新资源目录无回归测试 | 530/530，含 2 项白名单测试 | 已补门禁 |
| CLI harness | 15/15 | 15/15 | 无回归 |
| 真实 LLM / Token / RAG | 本轮未作为修复目标 | 仍不能由上述 PASS 推导 | 保留原审计结论 |

