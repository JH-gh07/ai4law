# DataComplyFlow CONFIG 静态契约与凭据边界治理契约

## 1. 目标与原则

本契约只治理两类配置问题，按独立批次执行：

1. `CONFIG-IDENTITY`：收敛跨语言模块身份清单；
2. `CONFIG-SECRET`：修复运行设置接口的鉴权、脱敏和空值覆盖风险。

治理顺序遵循“先正确、再简洁、最后补强”。本轮不动态生成 Router，不迁移业务模块，不改业务 API 路径，也不引入新的密钥管理基础设施。

## 2. 配置边界

| 配置类型 | 权威源 | 是否提交 Git | 消费者 |
|---|---|---:|---|
| 模块稳定身份 | `config/module_registry.json` | 是 | 前端、后端契约测试、治理工具 |
| 后端配置定义 | `backend/core/settings.py` | 是 | 后端运行时 |
| 环境变量示例 | `.env.example` | 是，仅空值 | 开发与部署人员 |
| 本地环境变量 | `.env`、操作系统环境 | 否 | 后端运行时 |
| UI 运行覆盖 | `storage/runtime_settings.json` | 否 | 后端运行时 |

`module_registry.json` 只是静态身份契约。FastAPI 路由仍由 `backend/api/v1/router.py` 显式装配，前端接口仍由 `frontend/src/lib/module-adapter.ts` 显式调用。

## 3. CONFIG-IDENTITY 基线与执行范围

修改前 12 个模块的 `target_package` 均与 `implementation_package` 相同，物理迁移已经完成。该字段不再表达目标状态，只形成重复数据源。

本批：

- 删除 `target_package`；
- 保留 `module_id`、法域、前端键、任务模板、当前实现包、v1 前缀和生命周期；
- 新增后端“实现包可导入且 v1 前缀已挂载”校验；
- 新增前端“实际请求路径属于登记前缀”校验；
- 不改变任何 Router、HTTP 方法、URL、Schema 或业务行为。

## 4. CONFIG-SECRET 基线与执行范围

修改前运行设置接口存在以下确定性问题：

- GET、PUT 与 Provider 测试接口未要求登录；
- GET 响应包含实际 LLM API Key 与得理法搜 Secret；
- 前端读取后将密钥保存在页面状态；
- 脱敏后若直接提交空值，旧实现会覆盖已有凭据；
- Provider 测试无法在不回传旧密钥的情况下复用已配置凭据。

本批目标：

- 三个接口至少要求已认证用户；当前系统无管理员角色模型，因此不伪造管理员权限；
- 所有响应只返回空的密钥字段与 `*_configured` 状态；
- PUT 中空密钥表示“保持现有值”，非空密钥表示替换；
- Provider 测试在请求密钥为空时按 Provider ID 使用后端已有密钥；
- 前端请求附带现有 Bearer Token，并以配置状态而不是明文判断密钥是否存在；
- 本地覆盖文件仍为忽略的运行产物，迁移到系统密钥环或云 Secret Manager 属于后续部署专项。

## 5. 验收门禁

- 模块身份后端与前端定向测试通过；
- 设置接口未认证访问返回 401；
- 响应 JSON 不含实际 API Key 或 Secret；
- 保存空密钥不删除已有凭据；
- 保存新密钥能够替换已有凭据；
- 测试 Provider 可复用后端已配置密钥；
- `.env.example` 只包含空的凭据示例；
- 不读取、不修改、不提交现有 `storage/runtime_settings.json`。

## 6. 明确暂缓

- 管理员 RBAC；
- 密钥加密落盘、操作系统密钥环或云 Secret Manager；
- 显式“清除密钥”协议；
- 用注册表动态生成后端路由；
- 统一重写前后端配置系统。

## 7. 2026-07-17 执行结果

`CONFIG-IDENTITY` 已完成：

- 12 个重复的 `target_package` 字段已退役；
- 新增 `config/README.md`，明确静态身份契约与运行配置边界；
- 后端模块身份测试 15 项通过；
- 前端模块身份测试 5 项通过。

`CONFIG-SECRET` 已完成：

- 运行设置读取、保存和 Provider 测试三个接口均接入现有登录鉴权；
- LLM API Key 与得理法搜 Secret 不再出现在响应明文中；
- 空凭据保存会保留同 ID Provider 或得理法搜的已有凭据；
- Provider 测试可在请求密钥为空时复用后端已有密钥；
- 前端三个请求均携带现有 Bearer Token，设置页依据 `api_key_configured` 显示状态；
- `.env.example` 已补充空值 LLM 配置范例；
- 路由、模块身份和凭据边界联合回归 32 项通过；
- 前端生产构建通过；
- 当前忽略的 `storage/runtime_settings.json` 未被本轮读取、修改或纳入 Git。

已知非阻断事项：

- Pytest 因本机 `.pytest_cache` 权限产生缓存警告，不影响测试结果；
- 当前环境未安装 Ruff 可执行文件，因此未执行 Ruff；`git diff --check` 无空白错误；
- 前端构建保留既有大 chunk 警告，与本轮配置治理无关；
- 管理员 RBAC、密钥加密落盘和显式清除密钥仍按本契约第 6 节暂缓。