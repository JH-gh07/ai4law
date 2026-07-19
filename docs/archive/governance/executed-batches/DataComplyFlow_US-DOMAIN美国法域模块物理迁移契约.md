# DataComplyFlow US-DOMAIN 美国法域模块物理迁移契约

## 1. 目标

将边界明确的美国法域业务模块从扁平 `backend/modules/` 迁入 `backend/domains/us/`，形成法域级物理目录。本批只迁移 CPRA 与 EO 14117，不修改 API、Schema、规则、Prompt、RAG、数据库或前端协议。

## 2. 迁移映射

| 旧路径 | 权威新路径 | 文件数 |
|---|---|---:|
| `backend/modules/cpra/` | `backend/domains/us/cpra/` | 24 |
| `backend/modules/us_14117/` | `backend/domains/us/eo14117/` | 17 |

`eo14117` 作为 Python 包名统一使用无前导 `us_` 的法域内名称；外部 API 路径、模块 ID `4.2`/`4.3` 和用户可见名称保持不变。

## 3. 已确认消费者

- `backend/api/v1/router.py`：两套 v1 Router；
- `backend/core/runtime_settings.py`：CPRA Router 级 Service 的运行配置注入；
- `backend/modules/v0_task_gateway/service.py`：CPRA v0 兼容任务入口；
- `backend/modules/catalog.py`：模块实现包身份；
- `backend/modules/eu_scc/` 与 `backend/modules/tia/`：复用 `CPRACitationRef`；
- 模块内部实现和测试；
- `backend/api/tests/route_baseline.json`：记录 endpoint module 的路由基线。

本批只改 import 和实现包元数据。跨法域复用 `CPRACitationRef` 属于后续公共 Schema 收敛事项，不在物理迁移中顺带重构。

## 4. 回退基线

- 迁移前专项：63 passed，1 个既有 Starlette/httpx 弃用警告；
- 备份：`.repo-backups/DataComplyFlow_pre_us_domain_migration_20260716.zip`；
- 备份大小：91,033 bytes；
- 备份 SHA-256：`D61234F308FE5FE80C628F59302C5635C1196DA2AE8A6B4BCE8C723F6D86F515`；
- 源文件：41 个，329,754 bytes。

## 5. 验收门禁

1. 41 个文件迁移前后内容 Hash 不变，import 机械改写除外；
2. 旧目录不保留兼容复制或转发包；
3. 活动源码不再 import `backend.modules.cpra` 或 `backend.modules.us_14117`；
4. HTTP method、完整 URL、operation ID 和 route name 不变；
5. OpenAPI 正常生成且无重复 Method + Path；
6. 迁移前 63 项专项测试全部通过；
7. 后端完整回归、前端测试和构建通过；
8. 仓库卫生检查与 `git diff --check` 通过。

## 6. 非目标

- 不移动中国或欧盟模块；
- 不移动 `v0_task_gateway`；
- 不统一重写公共 Workflow 或 Citation Schema；
- 不改变 v0/v1 生命周期；
- 不修改法律结论或 Gold。


## 7. 执行结果

本批迁移已完成：

- `backend/domains/us/cpra/` 与 `backend/domains/us/eo14117/` 成为唯一实现位置；
- 旧 `backend/modules/cpra/` 和 `backend/modules/us_14117/` 已删除，没有保留转发包；
- `config/module_registry.json`、后端模块目录、v1 Router、运行配置注入、v0 兼容网关、EU SCC/TIA 跨模块引用和全部测试已切换到新包；
- 迁移前 41 个文件与迁移后文件做反向 import 归一化比较，41/41 内容一致；
- 路由基线仅 8 个 `endpoint_module` 改变，HTTP method、URL、route name 和 operation ID 均未变化；
- `backend/modules/conftest.py` 提升为 `backend/conftest.py`，使 modules 与 domains 共享同一鉴权测试 fixture；该变化不影响生产代码；
- 卫生检查禁止重新引入两套旧模块路径，并扩展为同时检查已跟踪和未暂存文件以及 `config/` 权威注册表。

验证结果：迁移前后专项均为 63 passed；后端六组共 376 passed；前端 5 passed；前端生产构建成功；仓库卫生检查覆盖 1,372 个文件并通过。首次专项中的 fixture 缺失已通过提升公共 conftest 解决；EO 14117 的一次 `MemoryError` 单独及完整重跑均通过，认定为当时 Windows 内存压力下的瞬态环境错误。