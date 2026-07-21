# DataComplyFlow 文档中心

`docs/` 是仓库文档的唯一根目录。活动文档只分为现行规范、事实快照和历史证据三类，避免多个规范目录并存。

## 文档分层

| 目录 | 职责 | 是否约束当前开发 |
|---|---|---:|
| `standards/` | 活动架构、开发规范、验证门禁和治理知识资产 | 是 |
| `handoff/` | 有明确审计日期的事实基线、实施记录和研究交接材料 | 有时间边界 |
| `archive/` | 已执行批次、被替代规范和设计来源证据 | 否 |

## 活动规范与知识资产

开发和验证使用以下活动规范：

1. [活动架构与权威源](standards/DataComplyFlow_活动架构与权威源.md)
2. [开发规范与验证门禁](standards/DataComplyFlow_开发规范与验证门禁.md)
3. [统一渲染与产物契约](standards/DataComplyFlow_统一渲染与产物契约.md)
4. [引用跳转与 CitationMap 契约](standards/DataComplyFlow_引用跳转与CitationMap契约.md)

治理经验只保留以下两份知识资产，后续经验在原文内增补，不再按批次新增活动文档：

1. [仓库治理原则与经验](standards/DataComplyFlow_仓库治理原则与经验.md)
2. [代码来源与软著治理](standards/DataComplyFlow_代码来源与软著治理.md)

有日期的项目状态从[事实与交接材料索引](handoff/README.md)进入。历史材料只能从[归档说明](archive/README.md)追溯。

## 事实优先级

当前可运行代码和测试结果 → 当前配置与真实调用链 → `standards/` 现行规范 → `handoff/` 有日期事实快照 → `archive/` 历史材料。

归档材料可能保留旧路径、旧模块名和过期决策，只能用于解释历史，不能据此恢复旧实现。业务法规、研究来源、Benchmark 数据和运行产物分别位于 `resources/`、`benchmarks/`、`storage/` 与 `outputs/`，不得重新放入 `docs/`。
