# DataComplyFlow CN-DOMAIN 中国法域第一批物理迁移契约

## 1. 目标

将边界清晰的中国安全评估、PIPIA 和中国 SCC 模块迁入 `backend/domains/cn/`。本批只修改实现包位置及引用，不修改业务逻辑、API、Schema 字段、规则、Prompt、RAG、数据库或前端协议。

## 2. 迁移映射

| 旧路径 | 权威新路径 | 文件数 |
|---|---|---:|
| `backend/modules/assessment/` | `backend/domains/cn/security_assessment/` | 52 |
| `backend/modules/pipia/` | `backend/domains/cn/pipia/` | 7 |
| `backend/modules/scc/` | `backend/domains/cn/scc_review/` | 22 |

目标包名与 `config/module_registry.json` 已登记的 `target_package` 一致。module ID、frontend key、任务模板 ID 和 API prefix 均不改变。

## 3. 明确排除

### Diagnosis

`backend/domains/cn/transfer_diagnosis/` 当前是确定性领域核心，只包含模型、适配器和规则引擎；`backend/modules/diagnosis/` 仍承担 Schema、Service、Agent、Renderer、Router 和下游兼容契约。两者不是可直接删除的重复实现，Diagnosis 必须单独合并。

### CN Flow

`backend/modules/cn_flow/` 的真实 module ID 是 `us.eo_14117_flow_review`，属于美国 EO 14117 兼容流。不得因目录名含 `cn` 而迁入中国法域。

## 4. 回退基线

- 迁移前专项：96 passed，1 个既有 Starlette/httpx 弃用警告；
- 备份：`.repo-backups/DataComplyFlow_pre_cn_domain_batch1_20260716.zip`；
- 备份大小：194,480 bytes；
- 备份 SHA-256：`FCC9973121BDBECA6A57927C4038E6B38C00B3C2AFC6ED7E77528FD4EDF9C3B5`；
- 源文件：81 个，617,090 bytes。

## 5. 验收门禁

1. 81 个迁移文件反向归一化 import 后内容一致；
2. 三个旧目录删除且不保留转发包；
3. 活动源码与权威配置不再引用三个旧实现包；
4. 相关路由仅允许 endpoint module 改变；
5. HTTP method、URL、route name 和 operation ID 不变；
6. 迁移后专项仍为 96 passed；
7. 后端完整回归、前端测试和构建通过；
8. 卫生、缓存、重复路由和 `git diff --check` 通过。

## 6. 非目标

- 不处理 Diagnosis 双层结构；
- 不移动或重命名 CN Flow；
- 不提取公共 Workflow、Fact 或 Citation DTO；
- 不修改法律结论和 Gold；
- 不处理 RAG v2/v3 合并。
## 7. 执行结果

2026-07-16 已完成第一批迁移：

- 权威包为 `backend.domains.cn.security_assessment`、`backend.domains.cn.pipia`、`backend.domains.cn.scc_review`；
- 三个旧实现目录已删除，没有保留转发包；
- 81 个文件反向归一化 import 后内容全部一致；
- 活动源码与配置中的三个旧包引用为 0；
- 专项迁移前后均为 96 passed；
- 当前 104 条路由无重复，新增 0、删除 0；相对 HEAD 的 36 项变化全部是 endpoint module，其中本批中国模块 12 项，method、path、route name 和 operation ID 均未变化；
- 后端全量首轮为 375 passed、1 failed，失败是知识搜索标题断言；该用例单独复跑通过，第二次全量为 376 passed。此非确定性现象应作为测试隔离债记录，不能认定为本批迁移回归；
- 前端 5 passed，生产构建通过；
- 仓库卫生检查通过。

Diagnosis 与 CN Flow 仍按第 3 节边界保留，未混入本批处理。
