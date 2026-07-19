# DataComplyFlow US-EO14117-FLOW 兼容流物理迁移契约

## 1. 目标

将历史命名为 `cn_flow`、真实法域和业务语义属于美国 EO 14117 的兼容模块，从 `backend/modules/cn_flow/` 迁入 `backend/domains/us/eo14117_flow_review/`。

本阶段只修改实现包位置与 import，不修改业务规则、Schema 字段、Prompt、RAG、报告模板、API、数据库或前端协议。

## 2. 与完整 EO 14117 模块的关系

`cn_flow` 与 `backend/domains/us/eo14117/` 不是重复实现：

- 兼容流使用 8 个 `CNFlow*` Schema、独立 4.1 模板、风险项和 XLSX/ZIP 输出；
- 完整模块使用 13 个 `US14117*` Schema、独立规则引擎、5 个 Agent、交通灯结论和 4.2 模板；
- 两者分别暴露 `/api/v1/cn-flow/*` 与 `/api/v1/us_14117/*`；
- 前端、v0 网关、评测脚本和 Trace 标识仍分别消费两种契约。

因此本阶段只纠正物理法域归属，不合并服务或接口。

## 3. 稳定兼容标识

- module ID：`us.eo_14117_flow_review`；
- frontend key：`cn_flow`；
- task template ID：`us_14117_flow`；
- API prefix：`/api/v1/cn-flow`；
- lifecycle：`legacy-compatible`。

以上标识本阶段均不改变。权威实现包和目标包统一为 `backend.domains.us.eo14117_flow_review`。

## 4. 回退基线

- 专项测试：52 passed，1 个既有 Starlette/httpx 弃用警告；
- 备份：`.repo-backups/DataComplyFlow_pre_eo14117_flow_review_migration_20260716.zip`；
- 备份：10 个文件，44,504 source bytes，压缩后 14,136 bytes；
- SHA-256：`E39B1C57A39387F70BA5BAE02EA58079BBB8B586B0C6C2FC172C6FB82352CD28`。

## 5. 验收门禁

1. 10 个文件归一化 import 后内容一致；
2. 旧 `backend/modules/cn_flow/` 删除且不保留转发包；
3. 活动源码和配置不再引用 `backend.modules.cn_flow`；
4. 104 条路由不新增、不删除、不重复；
5. `/cn-flow` 四条路由只允许 endpoint module 改变；
6. 专项迁移前后均为 52 passed；
7. 后端完整回归、前端测试和构建通过；
8. 仓库卫生、缓存和 `git diff --check` 通过。

## 6. 非目标

- 不把兼容流合并进完整 EO 14117 Service；
- 不修改历史 frontend key 或 URL；
- 不统一两套 Schema、模板、Trace 或输出格式；
- 不退役 v0 网关；
- 不修改法律判断或 Gold。
## 7. 执行结果

2026-07-16 已完成兼容流物理迁移：

- 唯一实现包为 `backend.domains.us.eo14117_flow_review`，旧 `backend.modules.cn_flow` 已删除；
- 10 个文件归一化 import 后内容全部一致；
- 注册表的 `implementation_package` 与 `target_package` 已统一；
- 历史 module ID、frontend key、task template ID、API prefix 和 lifecycle 均未改变；
- 专项迁移前后均为 52 passed；唯一中间失败是旧目录契约仍断言 `target_package is None`，已更新为当前实现等于目标实现；
- 104 条路由无新增、删除或重复，`/cn-flow` 四条路由仅 endpoint module 改变；
- 完整 EO 14117 模块未修改，兼容流和完整模块继续独立运行；
- 后端完整回归 376 passed；前端 5 passed，生产构建通过。
