# DataComplyFlow MODULE-CATALOG 重复权威源退役契约

## 1. 目标

退役无生产消费者的 `backend/modules/catalog.py`，让 `config/module_registry.json` 成为跨后端、前端和测试的唯一模块身份权威源，并删除空出的历史 `backend/modules/` 目录。

## 2. 修改前事实

- `catalog.py` 硬编码 12 个 `ModuleDefinition`；
- `config/module_registry.json` 同时保存相同模块身份，并额外包含 task template、lifecycle 和 note；
- 仓库中只有 `backend/modules/tests/test_catalog.py` 导入 Python Catalog；
- Router、Service、运行配置、前端和评测 Runner 均不消费 Python Catalog；
- 当前测试通过比较两份硬编码数据来发现漂移，但没有消除重复源。

最终认定：Python Catalog 是测试辅助副本，不是运行时注册表。原样迁入 `backend/core/` 只会延续重复，因此应删除。

## 3. 目标结构

- 唯一权威源：`config/module_registry.json`；
- 后端契约测试：`backend/core/tests/test_module_registry.py`；
- 前端读取：现有 `frontend/src/lib/module-registry.ts`；
- `backend/modules/`：删除，不再作为活动命名空间。

新测试直接验证：

1. 12 个 module ID 与 frontend key 唯一；
2. jurisdiction、API prefix、lifecycle 和 target package 合法；
3. implementation package 可导入；
4. 已完成迁移的模块实现包等于目标包；
5. `review` 的未迁移边界和 `cn_flow` 的 legacy-compatible 身份保持明确。

## 4. 回退基线

- 原 Catalog 专项：17 passed；
- 备份：`.repo-backups/DataComplyFlow_pre_module_catalog_retirement_20260716.zip`；
- 备份：3 个文件，7,313 source bytes，压缩后 2,505 bytes；
- SHA-256：`EF18D69A04789D25AEA9E645B619A42ECEF26165A03E85A43F77CFD837F45E31`。

## 5. 验收门禁

1. `backend/modules/` 不存在；
2. 活动源码和现行文档不再引用 `backend.modules.catalog`；
3. 新测试直接读取 JSON 权威源且覆盖原 17 项语义；
4. 12 个 implementation package 全部可导入；
5. 后端完整回归、前端模块注册表测试和生产构建通过；
6. API 路由基线无变化；
7. 仓库卫生、缓存和 `git diff --check` 通过。

## 6. 非目标

- 不修改任何 module ID、frontend key、task template ID 或 API prefix；
- 不移动仍位于公共 API 的 `review`；
- 不改变 `cn_flow` 的 legacy-compatible 生命周期；
- 不引入数据库型或动态插件注册表；
- 不修改业务逻辑。
## 7. 执行结果

2026-07-16 已完成重复 Catalog 退役：

- `backend/modules/catalog.py`、旧 Catalog 测试和历史 README 已删除；
- `backend/modules/` 已完全不存在，并加入仓库卫生禁止路径；
- `config/module_registry.json` 成为唯一模块身份权威源；
- 新增 `backend/core/tests/test_module_registry.py`，直接验证 12 个模块身份和实现包；
- 原 Catalog 专项为 17 passed；新注册表与路由专项为 19 passed，其中注册表测试 15 项；减少的 2 个 Catalog 测试计数来自重复断言合并，不是业务测试删除；
- 后端完整回归为 374 passed，较迁移前 376 减少 2 项的原因同上；
- 前端 5 passed，生产构建通过；API 路由没有变化。

## 8. 后续状态更新

2026-07-17 全部法域物理迁移已经完成，`target_package` 与 `implementation_package` 变为完全重复字段。当前静态契约已退役 `target_package`，并改为直接校验当前实现包可导入、登记的 API 前缀已挂载以及前端请求路径位于登记前缀之下。本节不改写 2026-07-16 的历史验收事实。