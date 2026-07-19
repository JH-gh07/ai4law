# DataComplyFlow CN-DIAGNOSIS 诊断模块物理收敛契约

## 1. 目标

将同一中国数据出境路径诊断实现从 `backend/modules/diagnosis/` 与 `backend/domains/cn/transfer_diagnosis/` 两个互相依赖的包，收敛为唯一权威实现包 `backend/domains/cn/transfer_diagnosis/`。

本阶段只改变文件位置和 import，不改变诊断规则、法律依据、Prompt、Schema 字段、API、数据库、报告内容或前端协议。

## 2. 修改前事实

- `backend/domains/cn/transfer_diagnosis/` 保存 `DiagnosisFacts`、规则引擎和适配器；
- 适配器反向依赖 `backend.modules.diagnosis.schema.DiagnosisAnswers`；
- `backend/modules/diagnosis/` 保存 Schema、Service、Router、Renderer、Agents、规则表和测试；
- Service 再依赖领域包，因此两个包构成同一实现内的双向层级依赖；
- `backend/api/diagnosis.py` 是持久化会话 API，通过 `DiagnosisSessionService` 调用模块 Service；
- 模块 Router 暴露 `/diagnosis/evaluate` 和 `/diagnosis/report`，公共 API 暴露 `/diagnosis/sessions/...`，两组 Method + Path 不冲突。

## 3. 迁移规则

1. 将旧模块包中的 `schema.py`、`service.py`、`router.py`、`report_renderer.py`、`agents/`、`decision_tree.json`、`README.md` 和测试迁入权威领域包；
2. 将领域包根目录的两个测试归入统一 `tests/`；
3. 所有消费者直接引用权威领域包；
4. 更新模块注册表的 `implementation_package`，保留 module ID、frontend key 和 API prefix；
5. 删除旧实现包，不保留转发层；
6. 保留公共会话 API 与模块 evaluate/report API，不合并 URL。

## 4. 回退基线

- 专项测试：44 passed，1 个既有 Starlette/httpx 弃用警告；
- 备份：`.repo-backups/DataComplyFlow_pre_diagnosis_consolidation_20260716.zip`；
- 备份文件：21 个，源文件 115,131 bytes；
- 备份大小：39,111 bytes；
- SHA-256：`F873CE94F29D3FC65A6231BE8C74480F454EBFCF7C9B7B80F68B7B9FAAF5E1A5`。

## 5. 验收门禁

1. 旧 `backend/modules/diagnosis/` 不存在；
2. 活动源码和权威配置不再引用 `backend.modules.diagnosis`；
3. 21 个文件均能从备份追溯，除包名和测试位置外内容不变；
4. 104 条路由不新增、不删除、不重复；
5. Diagnosis 路由只允许 endpoint module 改变；
6. 专项测试仍为 44 passed；
7. 后端完整回归、前端测试与构建通过；
8. 仓库卫生、缓存和 `git diff --check` 通过。

## 6. 非目标

- 不合并公共会话 Schema 与模块诊断 Schema；
- 不修改路径阈值、豁免规则、unknown 处理或法律 Gold；
- 不重写 Agent；
- 不处理 `cn_flow`；
- 不处理 RAG 版本收敛。
## 7. 执行结果

2026-07-16 已完成物理收敛：

- `backend.modules.diagnosis` 已删除，唯一权威包为 `backend.domains.cn.transfer_diagnosis`；
- 活动代码和配置中的旧包引用为 0；
- 备份中的 20 个非重复文件在归一化包名后内容一致；旧包空 `__init__.py` 因与权威包入口重复而删除；
- 领域规则测试迁入 `tests/` 后，将规则表定位从旧物理目录改为权威包相邻的 `decision_tree.json`，未修改规则表或生产代码；
- 专项迁移前后均为 44 passed；
- 104 条路由无新增、删除或重复，Diagnosis 仅 `/evaluate` 与 `/report` 的 endpoint module 改变；
- 公共 `/diagnosis/sessions/...` 会话接口完整保留；
- 后端完整回归 376 passed；前端 5 passed，生产构建通过；
- 仓库卫生检查通过。
