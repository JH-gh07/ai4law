# DataComplyFlow 模块身份与法域契约

## 目的

本文件记录仓库收束阶段的模块身份规则。治理顺序固定为：先确认业务身份和兼容边界，再移动目录或删除旧实现，最后开展能力和安全补强。

跨前后端机器可读唯一权威源为 `config/module_registry.json`。后端 `backend/core/tests/test_module_registry.py` 直接验证该文件及实现包；前端模块法域和任务恢复映射直接读取同一注册表。重复的 Python Catalog 已退役。

## 标识职责

| 标识 | 职责 | 稳定性 |
|---|---|---|
| `module_id` | 跨前后端、Trace、Benchmark 使用的稳定业务身份 | 新代码应使用 |
| `frontend_key` | 当前前端状态及兼容调用键 | 保持兼容，不因目录迁移修改 |
| `v1_api_prefix` | 已发布接口路径 | 本阶段保持不变 |
| `implementation_package` | 当前真实实现位置 | 可随受控迁移更新 |

| `lifecycle` | `active`或`legacy-compatible` | 删除前必须先消除调用者 |

## 本阶段确认

- `scc`是中国个人信息出境标准合同审查；`eu_scc`是欧盟SCC审查，两者不得共用任务模板身份。
- `review`是活动公共API，当前实现以中国法域材料和规则为主；在通用化边界确认前不做物理法域迁移。
- `cn_flow`保留历史键和URL，但当前检索、规则依据与输出均属于美国EO 14117语义，因此登记为`us.eo_14117_flow_review`兼容模块。
- `cn_flow`与`us_14117`暂不合并或删除；两者的输入、输出和调用依赖须在后续专项中完成差异审计。

## 变更门槛

任何模块改名、移动、合并或删除前必须同时满足：

1. 注册表身份和法域已经确认；
2. API完整路径及HTTP方法保持或有明确版本迁移；
3. 前端任务模板、恢复映射和模块适配器测试通过；
4. RAG、Trace、Citation使用的标识已有迁移方案；
5. 模块测试、路由完整性测试和前端构建通过；
6. 每个模块单独提交，能够独立回退。

## 暂缓事项

- 不在本阶段全量移动`backend/modules/`；
- 不直接删除RAG v2/v3或fallback；
- 不强制所有模块迁移到统一Workflow；
- 不把`review`或`cn_flow`凭名称塞入中国法域目录；
- 不改变现有API、Schema和前端调用协议。

## 2026-07-15 执行记录

- 新增跨前后端注册表并接入前端模块适配器和任务恢复逻辑；
- 新增中国SCC与EO 14117兼容流任务模板，避免恢复时跨模块串线；
- 后端完整测试360项通过，路由完整性4项通过；
- 前端测试5项通过，生产构建通过；
- API路径、请求响应Schema及业务处理函数均未修改。

## 2026-07-16 美国法域物理迁移

CPRA 与 EO 14117 已按独立迁移契约完成物理收敛：

- `us.cpra`：`backend.domains.us.cpra`；
- `us.eo_14117`：`backend.domains.us.eo14117`；
- 模块 ID、frontend key、v1 API prefix 和生命周期均未变化；
- 原 `backend.modules.cpra` 与 `backend.modules.us_14117` 不再是兼容入口，也不得重新创建；
- `cn_flow` 仍是独立的 EO 14117 兼容流模块，本批没有合并；
- EU SCC/TIA 暂时继续从 CPRA Schema 复用 `CPRACitationRef`，该跨法域耦合需在后续公共 Citation Schema 专项处理，不阻塞物理迁移。
## 2026-07-16 欧盟法域物理迁移

欧盟四个模块已迁入权威目标包：

- `eu.scc_review`：`backend.domains.eu.scc_review`；
- `eu.bcr_review`：`backend.domains.eu.bcr_review`；
- `eu.dpia`：`backend.domains.eu.dpia`；
- `eu.tia`：`backend.domains.eu.tia`。

稳定业务标识、前端键、任务模板 ID 和 API prefix 均未改变。原四个 `backend.modules.*` 实现包已删除。EU SCC/TIA 对 `CPRACitationRef` 的跨法域依赖仍保留，后续应提取公共 Citation DTO，但不得与本次物理迁移混为业务重构。
## 2026-07-16 中国法域第一批物理迁移

中国安全评估、PIPIA 和中国 SCC 已迁入权威目标包：

- `cn.security_assessment`：`backend.domains.cn.security_assessment`；
- `cn.pipia`：`backend.domains.cn.pipia`；
- `cn.scc_review`：`backend.domains.cn.scc_review`。

稳定业务标识、前端键、任务模板 ID 和 API prefix 均未改变，三个旧 `backend.modules.*` 实现包已删除。`backend.modules.diagnosis` 与 `backend.domains.cn.transfer_diagnosis` 是应用层和领域核心的双层结构，必须另开专项合并；`backend.modules.cn_flow` 的真实身份是美国 EO 14117 兼容流，不得因旧目录名迁入中国法域。
## 2026-07-16 中国路径诊断实现包收敛

`cn.transfer_diagnosis` 的应用层与领域核心已收敛到 `backend.domains.cn.transfer_diagnosis`。原 `backend.modules.diagnosis` 已删除，不再是兼容入口；模块注册表的 `implementation_package` 已指向唯一活动实现。

模块 Router 的 `/diagnosis/evaluate`、`/diagnosis/report` 与公共会话 API 的 `/diagnosis/sessions/...` 是同一诊断能力的两种接口契约，Method + Path 不冲突，本阶段均保留。后续如需统一 Schema 或退役其中一组接口，必须单独完成前端、持久化会话和下游 Assessment/SCC 消费者审计。
## 2026-07-16 EO 14117 兼容流物理归位

`us.eo_14117_flow_review` 已从误导性的 `backend.modules.cn_flow` 迁入 `backend.domains.us.eo14117_flow_review`。历史 `cn_flow` 仅作为 frontend key、Trace/module key 和 `/api/v1/cn-flow` 兼容协议继续保留，不再代表中国法域。

专项确认兼容流与 `backend.domains.us.eo14117` 并非重复实现：两者 Schema、规则深度、模板、输出和前端入口均不同，因此未合并。物理归属待确认的状态由本节终结。“物理归属待确认”的状态由本节终结。

## 2026-07-17 静态契约收敛

全部模块物理迁移完成后，`target_package` 与 `implementation_package` 已完全重复，因此从注册表退役。当前注册表只描述稳定身份、当前实现和兼容边界；目标迁移位置不再作为永久字段保存。