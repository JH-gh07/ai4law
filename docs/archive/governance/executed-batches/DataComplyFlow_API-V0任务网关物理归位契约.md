# DataComplyFlow API-V0 任务网关物理归位契约

## 1. 目标

将不属于任何法律法域的 v0 兼容任务网关，从 `backend/modules/v0_task_gateway/` 迁入 `backend/api/v0/task_gateway/`，使 API 版本适配代码归属其真实层级。

本阶段只修改实现包位置和 import，不修改 API、Schema、任务状态、上传协议、文件存储、模块分发、鉴权或前端调用。

## 2. 修改前事实

- `backend/app.py` 在 `/api/v0` 下挂载 `backend/api/v0/router.py`；
- v0 Router 再从 `backend.modules.v0_task_gateway.router` 装配 7 条接口；
- Gateway Service 将统一 v0 请求适配到 Assessment、PIPIA、BCR、DPIA、TIA、EO 14117 兼容流和 CPRA；
- `backend/core/runtime_settings.py` 对 Router 中的 Gateway 单例注入 LLM Client；
- 前端当前直接使用 `POST /api/v0/files/upload`；其余接口仍被测试和 QA 脚本消费；
- 该包是 API 兼容适配器，不是法律业务模块，也不是可直接删除的废弃版本。

## 3. 目标结构

```text
backend/api/v0/
├── router.py
└── task_gateway/
    ├── router.py
    ├── schema.py
    ├── service.py
    └── tests/
```

API 版本前缀继续只由 `backend/app.py` 提供，Gateway Router 不新增 `/api/v0` 前缀。

## 4. 回退基线

- 专项测试：11 passed，1 个既有 Starlette/httpx 弃用警告；
- 备份：`.repo-backups/DataComplyFlow_pre_v0_task_gateway_relocation_20260716.zip`；
- 备份：5 个文件，45,828 source bytes，压缩后 9,783 bytes；
- SHA-256：`02624635AAFD59A237F5EFB27C7BF8C1E1FBA690C1AABF7B66089A9CF47E2310`。

## 5. 验收门禁

1. 5 个文件归一化 import 后内容一致；
2. 旧 `backend/modules/v0_task_gateway/` 删除且不保留转发包；
3. 活动源码不再引用 `backend.modules.v0_task_gateway`；
4. 104 条路由不新增、不删除、不重复；
5. 7 条 v0 路由只允许 endpoint module 改变；
6. 专项迁移前后均为 11 passed；
7. 后端完整回归、前端测试和构建通过；
8. 仓库卫生、缓存和 `git diff --check` 通过。

## 6. 非目标

- 不将 v0 接口复制为 v1；
- 不删除当前前端使用的上传接口；
- 不处理 owner、鉴权、任意本地路径、上传大小或持久化安全债；
- 不重构七个下游业务 Service；
- 不移动 `backend/modules/catalog.py`。
## 7. 执行结果

2026-07-16 已完成 v0 任务网关物理归位：

- 唯一实现包为 `backend.api.v0.task_gateway`，旧 `backend.modules.v0_task_gateway` 已删除；
- 5 个文件归一化 import 后内容全部一致；
- 专项迁移前后均为 11 passed；
- 104 条路由无新增、删除或重复，7 条 v0 路由仅 endpoint module 改变；
- 前端仍通过 `POST /api/v0/files/upload` 使用相同协议；
- 后端完整回归 376 passed；前端 5 passed，生产构建通过；
- 已知 v0 安全与生命周期问题未在本次目录迁移中修改。
