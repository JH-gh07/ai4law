# DataComplyFlow EU-DOMAIN 欧盟法域模块物理迁移契约

## 1. 目标

将欧盟法域四个业务模块从扁平 `backend/modules/` 迁入 `backend/domains/eu/`。本批只改变实现包位置和相关引用，不修改业务逻辑、API、Schema 字段、规则、Prompt、RAG、数据库或前端协议。

## 2. 迁移映射

| 旧路径 | 权威新路径 | 文件数 |
|---|---|---:|
| `backend/modules/eu_scc/` | `backend/domains/eu/scc_review/` | 18 |
| `backend/modules/bcr/` | `backend/domains/eu/bcr_review/` | 33 |
| `backend/modules/dpia/` | `backend/domains/eu/dpia/` | 30 |
| `backend/modules/tia/` | `backend/domains/eu/tia/` | 17 |

新包名遵循 `config/module_registry.json` 已登记的 `target_package`。稳定 module ID、frontend key、任务模板 ID 和 v1 API prefix 均保持不变。

## 3. 已确认消费者

- `backend/api/v1/router.py`：四个 v1 Router；
- `backend/core/runtime_settings.py`：BCR、DPIA、TIA Router Service 配置注入；
- `backend/modules/v0_task_gateway/service.py`：BCR、DPIA、TIA 兼容任务入口；
- `backend/modules/catalog.py` 与 `config/module_registry.json`：实现包身份；
- 模块内部实现与测试；
- `backend/api/tests/route_baseline.json`：16 个欧盟 endpoint module 记录。

EU SCC 与 TIA 暂时复用美国 CPRA 包中的 `CPRACitationRef`。这是跨法域 Schema 耦合，但迁移本身不改变该契约，后续再单独提取公共 Citation DTO。

## 4. 回退基线

- 迁移前专项：62 passed，1 个既有 Starlette/httpx 弃用警告；
- 首次运行的 4 个 setup error 来自系统临时目录权限，指定仓库内 basetemp 后全部通过，不属于代码失败；
- 备份：`.repo-backups/DataComplyFlow_pre_eu_domain_migration_20260716.zip`；
- 备份大小：227,734 bytes；
- 备份 SHA-256：`1260D9A2705EAB39E2C6C07873BFB81D1EBD59A7D24CC3C9C6125054D1A877DB`；
- 源文件：98 个，705,022 bytes。

## 5. 验收门禁

1. 98 个文件反向归一化 import 后内容一致；
2. 四个旧目录删除，不保留转发包；
3. 活动源码与权威配置不再引用旧实现包；
4. 16 条相关路由仅允许 endpoint module 变化；
5. HTTP method、URL、route name 和 operation ID 不变；
6. 迁移后专项仍为 62 passed；
7. 后端完整回归、前端测试和构建通过；
8. 卫生、缓存、重复路由与 `git diff --check` 通过。

## 6. 非目标

- 不迁移中国模块或共享 v0 网关；
- 不提取公共 Citation Schema；
- 不修改欧盟法律规则或 Gold；
- 不合并四个业务模块；
- 不开展 RAG v2/v3 合并。


## 7. 执行结果

本批迁移已完成：

- `backend/domains/eu/scc_review/`、`bcr_review/`、`dpia/`、`tia/` 成为唯一实现位置；
- 四个 `backend/modules/` 旧目录已删除，没有保留兼容转发包；
- 权威模块注册表、Python 目录、v1 Router、运行设置注入、v0 兼容网关、模块内部实现和测试均切换到新包；
- 98 个迁移文件反向归一化 import 后 98/98 内容一致；
- 欧盟 16 条路由只改变 endpoint module；合并美国迁移后与 HEAD 比较共 24 个 endpoint module 变化，其他路由字段变化为 0；
- 活动源码与配置中的旧包引用为 0，卫生脚本只保留旧名称作为禁止规则；
- 旧目录重新引入和旧 import 已加入仓库卫生门禁。

验证结果：迁移前后专项均为 62 passed；后端六组共 376 passed；前端 5 passed；前端生产构建成功；104 条路由无 Method+Path 重复。首次迁移前运行的 4 个 setup error 由系统临时目录拒绝访问导致，指定仓库内 basetemp 后全部通过。